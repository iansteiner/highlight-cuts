import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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

# Mount output for downloads (optional, or use a specific endpoint)
# app.mount("/downloads", StaticFiles(directory=OUTPUT_DIR), name="downloads")


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

        games = sorted(df["videoName"].unique().tolist())
        players = sorted(df["playerName"].unique().tolist())

        # Return HTML options for the dropdowns
        # We'll return a snippet that updates both select boxes if possible,
        # or just the games, and let the user pick a game?
        # Actually, the user flow is: Enter URL -> Select Game -> Select Player (filtered by game?)
        # For simplicity, let's just list all games and all players found in the sheet.
        
        game_options = "".join([f"<option value='{g}'>{g}</option>" for g in games])
        player_options = "".join([f"<option value='{p}'>{p}</option>" for p in players])
        
        # We use OOB swaps or just return a block containing both selects?
        # HTMX is best with returning the specific element to replace.
        # But we need to update TWO elements.
        # We can use hx-swap-oob.
        
        return f"""
        <select id="game-select" name="game" hx-swap-oob="true">
            <option value="" disabled selected>Select Game</option>
            {game_options}
        </select>
        <select id="player-select" name="player" hx-swap-oob="true">
            <option value="" disabled selected>Select Player</option>
            {player_options}
        </select>
        <div id="sheet-status" hx-swap-oob="true" class="text-green-600">Sheet loaded successfully!</div>
        """

    except Exception as e:
        logger.error(f"Error parsing sheet: {e}")
        return f"<div id='sheet-status' hx-swap-oob='true' class='text-red-600'>Error: {str(e)}</div>"


def process_video_task(
    video_filename: str,
    sheet_url: str,
    game: str,
    player: str,
    padding: float,
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

        intervals = player_clips[player]
        merged = merge_intervals(intervals, padding)
        
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
    padding: float = Form(0.0),
):
    """
    Initiates the processing.
    """
    # Generate output filename
    # game_Player.ext
    input_path = DATA_DIR / video_filename
    safe_player = "".join(c for c in player if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    output_filename = f"{Path(video_filename).stem}_{safe_player}{input_path.suffix}"
    
    # Check if file already exists? Overwrite for now.
    
    # Run in background
    background_tasks.add_task(
        process_video_task,
        video_filename,
        sheet_url,
        game,
        player,
        padding,
        output_filename
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
        # Sort by modification time, newest first
        files = sorted(OUTPUT_DIR.iterdir(), key=os.path.getmtime, reverse=True)
    
    html = "<ul class='list-disc pl-5'>"
    for f in files:
        if f.is_file() and not f.name.startswith("."):
            html += f"<li><a href='/download/{f.name}' class='text-blue-600 hover:underline'>{f.name}</a></li>"
    html += "</ul>"
    return html


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)
