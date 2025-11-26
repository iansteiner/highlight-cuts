import logging
import os
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd

from .core import process_csv, merge_intervals
from .ffmpeg import extract_clip, concat_clips

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Highlight Cuts Web")

# Directories
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = Path(os.getenv("HIGHLIGHT_CUTS_DATA_DIR", "data"))
OUTPUT_DIR = Path(os.getenv("HIGHLIGHT_CUTS_OUTPUT_DIR", "output"))

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not DATA_DIR.exists():
    # In docker this should be mounted, but locally we might need it
    DATA_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# Mount output for streaming with no-cache to help Cloudflare
app.mount("/videos", NoCacheStaticFiles(directory=str(OUTPUT_DIR)), name="videos")


def get_video_files() -> List[str]:
    """List supported video files in the data directory."""
    extensions = {".mp4", ".mov", ".mkv", ".avi", ".ts"}
    files = []
    if DATA_DIR.exists():
        for f in DATA_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in extensions:
                files.append(f.name)
    return sorted(files)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    video_files = get_video_files()
    return templates.TemplateResponse(
        "index.html", {"request": request, "video_files": video_files}
    )


@app.post("/parse-sheet", response_class=HTMLResponse)
async def parse_sheet(request: Request, sheet_url: str = Form(...)):
    """
    Parses the Google Sheet and returns HTMX partials for Game and Player dropdowns.
    """
    try:
        # We need to get all unique games and players
        # process_csv filters by game, so we can't use it directly to find games.
        # We need a new function in core or just use pandas here.
        # For now, I'll duplicate the reading logic slightly to get the full DF
        # or better, refactor core. But to avoid breaking changes, I'll use process_csv's normalize
        # and then read it.

        from .core import normalize_sheets_url
        import requests
        import io

        url = normalize_sheets_url(sheet_url)

        if url.startswith("https://docs.google.com/spreadsheets"):
            response = requests.get(url)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
        else:
            # Assume local path (testing) or direct CSV url
            df = pd.read_csv(url)

        if "videoName" not in df.columns or "playerName" not in df.columns:
            return "<div class='error'>Invalid CSV: Missing videoName or playerName columns</div>"

        # Group by game and player and count clips
        # We can also check for 'include' column to count only included clips?
        # For now, let's count all clips to match the "clip_count" requirement.
        summary = df.groupby(["videoName", "playerName"]).size().reset_index(name="count")
        
        # Sort by Game then Player
        summary = summary.sort_values(["videoName", "playerName"])

        rows = ""
        for _, row in summary.iterrows():
            game = row["videoName"]
            player = row["playerName"]
            count = row["count"]
            
            rows += f"""
            <tr onclick="selectSelection(this, '{game}', '{player}')"
                hx-post="/get-clips"
                hx-vals='{{"game": "{game}", "player": "{player}"}}'
                hx-include="[name='sheet_url']"
                hx-target="#clips-table"
                class="cursor-pointer hover:bg-gray-50 transition border-b border-gray-100 last:border-b-0">
                <td class="px-6 py-1 whitespace-nowrap text-sm font-medium text-gray-900">{game}</td>
                <td class="px-6 py-1 whitespace-nowrap text-sm text-gray-500">{player}</td>
                <td class="px-6 py-1 whitespace-nowrap text-sm text-gray-500">{count}</td>
            </tr>
            """

        table_html = f"""
        <div id="selection-table-container" hx-swap-oob="true" class="mt-4 col-span-2">
            <label class="block text-sm font-semibold text-gray-700 mb-2">Select Game & Player</label>
            <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
                <table class="min-w-full divide-y divide-gray-300">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Game</th>
                            <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Player</th>
                            <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Clips</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
        <div id="sheet-status" hx-swap-oob="true" class="text-green-600">Sheet loaded successfully!</div>
        """

        return table_html

    except Exception as e:
        logger.error(f"Error parsing sheet: {e}")
        return f"<div id='sheet-status' hx-swap-oob='true' class='text-red-600'>Error: {str(e)}</div>"


def process_video_task(
    video_filename: str,
    sheet_url: str,
    game: str,
    player: str,
    output_filename: str,
):
    """Background task to process the video."""
    try:
        input_path = DATA_DIR / video_filename
        output_path = OUTPUT_DIR / output_filename

        # 1. Get clips
        player_clips = process_csv(sheet_url, game)

        if player not in player_clips:
            logger.error(f"Player {player} not found in game {game}")
            return

        all_clips = player_clips[player]
        # Filter for included clips
        intervals = [(c.start, c.end) for c in all_clips if c.included]

        if not intervals:
            logger.warning(f"No included clips for player {player}")
            # Should we create an empty video or just return?
            # For now, let's return to avoid errors in extract/concat
            return

        merged = merge_intervals(intervals)

        # 2. Extract and Concat
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_clips = []
            for i, (start, end) in enumerate(merged):
                clip_name = f"clip_{i:03d}{input_path.suffix}"
                clip_path = os.path.join(temp_dir, clip_name)
                extract_clip(str(input_path), start, end, clip_path)
                temp_clips.append(clip_path)

            concat_clips(temp_clips, str(output_path))
            logger.info(f"Created {output_path}")

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        # In a real app we'd update a status database


@app.post("/process", response_class=HTMLResponse)
async def process(
    background_tasks: BackgroundTasks,
    video_filename: str = Form(...),
    sheet_url: str = Form(...),
    game: str = Form(...),
    player: str = Form(...),
):
    """
    Initiates the processing.
    """
    # Generate output filename
    # game_Player.ext
    input_path = DATA_DIR / video_filename
    safe_player = (
        "".join(c for c in player if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )
    # Create player directory
    player_dir = OUTPUT_DIR / safe_player
    player_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: video_stem.ext
    output_filename = f"{Path(video_filename).stem}{input_path.suffix}"

    # Run in background
    background_tasks.add_task(
        process_video_task,
        video_filename,
        sheet_url,
        game,
        player,
        str(safe_player + "/" + output_filename),  # Pass relative path
    )

    # Return a "Processing started" message with a polling trigger or download link
    # Since we don't have a DB, we can't easily poll status.
    # For this prototype, we'll just say "Processing started. Check back in a minute."
    # and list the file in a "Recent Files" section (which we can implement via polling).

    return f"""
    <div class="p-4 bg-blue-100 text-blue-800 rounded">
        Processing <strong>{player}</strong> in <strong>{game}</strong>...<br>
        Output will be: {output_filename}<br>
        <button hx-get="/files" hx-target="#file-list" class="mt-2 underline">Refresh File List</button>
    </div>
    """


@app.get("/files", response_class=HTMLResponse)
async def list_files():
    """Returns a list of generated files in the output directory."""
    files = []
    if OUTPUT_DIR.exists():
        # Find all video files recursively
        for f in OUTPUT_DIR.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                files.append(f)
        # Sort by modification time, newest first
        files = sorted(files, key=os.path.getmtime, reverse=True)

    html = "<ul class='divide-y divide-gray-100 bg-white rounded-md border border-gray-200 shadow-sm'>"
    for f in files:
        # Determine relative path and display info
        rel_path = f.relative_to(OUTPUT_DIR)

        # If in a subdirectory, use that as Player Name
        if len(rel_path.parts) > 1:
            player_name = rel_path.parts[0].replace("_", " ")
            display_name = f.name
        else:
            player_name = "Unknown Player"
            display_name = f.name

        html += f"""
        <li class="flex items-center justify-between p-2 hover:bg-gray-50 transition">
            <div class="min-w-0 flex-1 flex items-center gap-3 mr-4">
                <!-- Video Icon -->
                <svg class="h-6 w-6 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <div class="min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{player_name}</p>
                    <p class="text-xs text-gray-500 truncate" title="{display_name}">{display_name}</p>
                </div>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
                <!--
                <button 
                    hx-get="/player/{rel_path}" 
                    hx-target="#video-player-container" 
                    class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-full text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition">
                    Play
                </button>
                -->
                <a href='/download/{rel_path}' 
                   class="text-gray-400 hover:text-gray-600 transition p-1 rounded-full hover:bg-gray-100" 
                   title="Download">
                   <!-- Download Icon -->
                   <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                   </svg>
                </a>
            </div>
        </li>
        """
    html += "</ul>"
    return html


@app.get("/player/{file_path:path}", response_class=HTMLResponse)
async def get_video_player(file_path: str):
    """Returns an HTML fragment with the video player."""
    full_path = OUTPUT_DIR / file_path
    if not full_path.exists():
        return "<div class='text-red-600'>File not found</div>"

    return f"""
    <div class="bg-black rounded-lg overflow-hidden shadow-lg">
        <div class="bg-gray-800 text-white px-4 py-2 flex justify-between items-center">
            <span class="font-medium">{Path(file_path).name}</span>
            <button onclick="this.closest('#video-player-container').innerHTML=''" class="text-gray-400 hover:text-white">&times;</button>
        </div>
        <video controls autoplay class="w-full max-h-[80vh]" preload="metadata">
            <source src="/videos/{file_path}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </div>
    """


@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    full_path = OUTPUT_DIR / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path, filename=Path(file_path).name)


@app.post("/get-clips", response_class=HTMLResponse)
async def get_clips(
    sheet_url: str = Form(...), game: str = Form(...), player: str = Form(...)
):
    """
    Returns an HTML table of clips for the selected player.
    """
    try:
        player_clips = process_csv(sheet_url, game)

        if player not in player_clips:
            return f"<div class='text-red-600'>No clips found for player {player} in game {game}</div>"

        clips = player_clips[player]

        # Create table rows
        # Create table rows
        rows = ""
        for i, clip in enumerate(clips):
            if clip.included:
                row_class = "hover:bg-gray-50"
            else:
                row_class = "bg-gray-50 text-gray-400"

            rows += f"""
            <tr class="{row_class}">
                <td class="px-6 py-1 whitespace-nowrap text-sm">{int(clip.start)}s</td>
                <td class="px-6 py-1 whitespace-nowrap text-sm">{int(clip.end)}s</td>
                <td class="px-6 py-1 whitespace-nowrap text-sm">{clip.notes}</td>
            </tr>
            """

        return f"""
        <div class="overflow-x-auto border rounded-lg">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start</th>
                        <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">End</th>
                        <th scope="col" class="px-6 py-1 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {rows}
                </tbody>
            </table>
        </div>
        """
    except Exception as e:
        logger.error(f"Error getting clips: {e}")
        return f"<div class='text-red-600'>Error loading clips: {str(e)}</div>"
