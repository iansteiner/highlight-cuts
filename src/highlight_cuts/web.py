import logging
import os
import shutil
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Dict
import glob

from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import yaml

from .core import process_csv, merge_intervals
from .ffmpeg import extract_clip, concat_clips, generate_hls
from .cache import read_cache, append_to_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Highlight Cuts Web")

# Directories
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = Path(os.getenv("HIGHLIGHT_CUTS_DATA_DIR", "data"))
OUTPUT_DIR = Path(os.getenv("HIGHLIGHT_CUTS_OUTPUT_DIR", "output"))

MAX_OUTPUT_TOTAL = int(os.getenv("HIGHLIGHT_CUTS_MAX_OUTPUT_TOTAL", "50"))
MAX_OUTPUT_PER_PLAYER_GAME = int(
    os.getenv("HIGHLIGHT_CUTS_MAX_OUTPUT_PER_PLAYER_GAME", "5")
)
HLS_SEGMENT_TIME = float(os.getenv("HIGHLIGHT_CUTS_HLS_SEGMENT_TIME", "6.0"))
HLS_REENCODE = os.getenv("HIGHLIGHT_CUTS_HLS_REENCODE", "false").lower() == "true"

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


def hls_dir_for(mp4_path: Path) -> Path:
    """Return the HLS directory for a given MP4."""
    return mp4_path.parent / f"{mp4_path.stem}_hls"


def remove_hls_artifacts(mp4_path: Path) -> None:
    """Delete HLS playlist/segments associated with an MP4."""
    hls_dir = hls_dir_for(mp4_path)
    if hls_dir.exists():
        shutil.rmtree(hls_dir, ignore_errors=True)


def enforce_output_limits(
    output_dir: Path,
    max_total: int = MAX_OUTPUT_TOTAL,
    max_per_player_game: int = MAX_OUTPUT_PER_PLAYER_GAME,
) -> None:
    """Apply retention limits and keep HLS+MP4 in sync."""
    files = []
    for f in output_dir.rglob("*.mp4"):
        if not f.is_file():
            continue
        rel = f.relative_to(output_dir)
        player_dir = rel.parts[0] if len(rel.parts) > 1 else "Unknown"
        base_pattern = f.stem.rsplit("_", 2)[0]
        mtime = os.path.getmtime(f)
        files.append(
            {
                "path": f,
                "key": f"{player_dir}|{base_pattern}",
                "mtime": mtime,
            }
        )

    # Per player/game limit
    to_delete = set()
    groups = {}
    for entry in files:
        groups.setdefault(entry["key"], []).append(entry)

    for entries in groups.values():
        entries.sort(key=lambda x: x["mtime"], reverse=True)
        for extra in entries[max_per_player_game:]:
            to_delete.add(extra["path"])

    # Total limit
    remaining = sorted(
        [f for f in files if f["path"] not in to_delete],
        key=lambda x: x["mtime"],
        reverse=True,
    )
    for extra in remaining[max_total:]:
        to_delete.add(extra["path"])

    for path in to_delete:
        try:
            path.unlink(missing_ok=True)
            remove_hls_artifacts(path)
            logger.info(f"Deleted old output due to limits: {path}")
        except Exception as e:
            logger.warning(f"Could not delete {path}: {e}")


def get_video_structure() -> Dict:
    """
    Scan data directory for video files in format: team/tournament/game.mp4
    Returns a nested dict: {team: {tournament: [{name, path, title, stream_url, suffix}]}}
    """
    extensions = {".mp4", ".mov", ".mkv", ".avi", ".ts"}
    structure = {}

    def load_metadata(dir_path: Path) -> dict:
        for candidate in ("games.yaml", "games.yml"):
            metadata_file = dir_path / candidate
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        data = yaml.safe_load(f) or {}
                        return data.get("games", {})
                except Exception as e:
                    logger.warning(f"Failed to read metadata {metadata_file}: {e}")
        return {}

    if DATA_DIR.exists():
        # Preload metadata per tournament dir
        metadata_cache = {}

        for f in DATA_DIR.rglob("*"):
            if f.is_file() and f.suffix.lower() in extensions:
                rel_path = f.relative_to(DATA_DIR)
                parts = rel_path.parts

                # Expected: team/tournament/game.mp4
                if len(parts) >= 3:
                    team = parts[0]
                    tournament = parts[1]
                    tournament_dir = DATA_DIR / team / tournament
                    if tournament_dir not in metadata_cache:
                        metadata_cache[tournament_dir] = load_metadata(tournament_dir)
                    meta = metadata_cache[tournament_dir].get(f.stem, {})

                    game_name = f.stem
                    title = meta.get("title") or game_name
                    stream_url = meta.get("stream_url")
                    poster = meta.get("poster")
                    notes = meta.get("notes")

                    if team not in structure:
                        structure[team] = {}
                    if tournament not in structure[team]:
                        structure[team][tournament] = []

                    structure[team][tournament].append(
                        {
                            "name": game_name,
                            "title": title,
                            "path": str(rel_path),
                            "suffix": f.suffix.lower(),
                            "stream_url": stream_url,
                            "poster": poster,
                            "notes": notes,
                        }
                    )
                else:
                    # Handle files not in expected structure (e.g. root or 1 level deep)
                    # Put them in "Uncategorized" -> "Misc"
                    team = "Uncategorized"
                    tournament = "Misc"
                    game_name = f.stem

                    if team not in structure:
                        structure[team] = {}
                    if tournament not in structure[team]:
                        structure[team][tournament] = []

                    structure[team][tournament].append(
                        {
                            "name": game_name,
                            "title": game_name,
                            "path": str(rel_path),
                            "suffix": f.suffix.lower(),
                            "stream_url": None,
                            "poster": None,
                            "notes": None,
                        }
                    )

    # Sort keys
    sorted_structure = {}
    for team in sorted(structure.keys()):
        sorted_structure[team] = {}
        for tournament in sorted(structure[team].keys()):
            # Sort games by name
            sorted_structure[team][tournament] = sorted(
                structure[team][tournament], key=lambda x: x["name"]
            )

    return sorted_structure


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    video_structure = get_video_structure()
    cached_sheets = read_cache(OUTPUT_DIR)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "video_structure": video_structure,
            "cached_sheets": cached_sheets,
        },
    )


@app.get("/cached-sheets")
async def get_cached_sheets():
    """Returns JSON list of cached Google Sheets URLs."""
    cached = read_cache(OUTPUT_DIR)
    return [
        {
            "url": entry["original_url"],
            "name": entry["sheet_name"],
            "sheet_id": entry["sheet_id"],
            "gid": entry["gid"],
        }
        for entry in cached
    ]


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
        summary = (
            df.groupby(["videoName", "playerName"]).size().reset_index(name="count")
        )

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

        # Add to cache with document title (async, don't wait for it)
        # This happens on successful parse, so user gets immediate feedback
        append_to_cache(OUTPUT_DIR, sheet_url, sheet_name=None)

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

        # Delete old versions of this file (keep only the newest generation)
        output_dir = output_path.parent
        base_pattern = output_path.stem.rsplit("_", 2)[
            0
        ]  # Remove timestamp from pattern
        pattern = str(output_dir / f"{base_pattern}_*.mp4")
        old_files = glob.glob(pattern)
        for old_file in old_files:
            try:
                os.remove(old_file)
                remove_hls_artifacts(Path(old_file))
                logger.info(f"Deleted old version: {old_file}")
            except Exception as e:
                logger.warning(f"Could not delete {old_file}: {e}")

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
        debug_logs = []
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_clips = []
            for i, (start, end) in enumerate(merged):
                clip_name = f"clip_{i:03d}{input_path.suffix}"
                clip_path = os.path.join(temp_dir, clip_name)
                logger.info(f"Extracting clip {i}: start={start}, end={end}")

                result = extract_clip(str(input_path), start, end, clip_path)
                result["type"] = "extract"
                result["clip_index"] = i
                result["start"] = start
                result["end"] = end
                debug_logs.append(result)

                temp_clips.append(clip_path)

            result = concat_clips(temp_clips, str(output_path))
            if result:
                result["type"] = "concat"
                debug_logs.append(result)

            # 3. Generate HLS playlist/segments for streaming
            try:
                hls_dir = hls_dir_for(output_path)
                hls_result = generate_hls(
                    str(output_path),
                    str(hls_dir),
                    segment_time=HLS_SEGMENT_TIME,
                    reencode=HLS_REENCODE,
                )
                if hls_result:
                    hls_result["type"] = "hls"
                    debug_logs.append(hls_result)
            except Exception as e:
                logger.warning(f"HLS generation failed for {output_path}: {e}")

            logger.info(f"Created {output_path}")

        enforce_output_limits(OUTPUT_DIR)

        # Write completion flag
        completion_file = Path("/tmp/highlight_cuts_complete.flag")
        with open(completion_file, "w") as f:
            f.write(f"{player}|{game}|{datetime.now().isoformat()}")

        # Write debug log to /tmp (not in output directory)
        log_file = Path("/tmp/highlight_cuts_debug.txt")
        with open(log_file, "w") as f:
            f.write(f"Debug Log generated at {datetime.now()}\n")
            f.write(f"Video: {video_filename}\n")
            f.write(f"Sheet: {sheet_url}\n")
            f.write(f"Game: {game}, Player: {player}\n")
            f.write("-" * 80 + "\n\n")

            for entry in debug_logs:
                f.write(f"[{entry['type'].upper()}] {entry.get('clip_index', '')}\n")
                f.write(f"Command: {entry['command']}\n")
                if "start" in entry:
                    f.write(f"Time: {entry['start']} -> {entry['end']}\n")
                f.write(f"Stdout: {entry['stdout']}\n")
                f.write(f"Stderr: {entry['stderr']}\n")
                f.write("-" * 80 + "\n\n")

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
    # Validate that game and player are not empty
    if not game or not game.strip():
        return """
        <div class="p-4 bg-red-50 rounded-lg border border-red-200">
            <div class="flex items-center gap-2">
                <svg class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span class="text-red-700 font-medium">Error: No game selected. Please select a game and player from the table above.</span>
            </div>
        </div>
        """

    if not player or not player.strip():
        return """
        <div class="p-4 bg-red-50 rounded-lg border border-red-200">
            <div class="flex items-center gap-2">
                <svg class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span class="text-red-700 font-medium">Error: No player selected. Please select a game and player from the table above.</span>
            </div>
        </div>
        """

    # Generate output filename
    # Format: player_team_tournament_game.mp4
    input_path = DATA_DIR / video_filename

    # Parse parts from video_filename (relative path)
    # Expected: team/tournament/game.mp4
    parts = Path(video_filename).parts
    if len(parts) >= 3:
        team = parts[0]
        tournament = parts[1]
        game_name = Path(parts[-1]).stem
    else:
        # Fallback
        team = "UnknownTeam"
        tournament = "UnknownTournament"
        game_name = Path(video_filename).stem

    safe_player = (
        "".join(c for c in player if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )

    # Sanitize other parts
    safe_team = (
        "".join(c for c in team if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )
    safe_tournament = (
        "".join(c for c in tournament if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )
    safe_game = (
        "".join(c for c in game_name if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )

    # Create player_team directory
    # Format: player_team
    player_team_dir_name = f"{safe_player}_{safe_team}"
    player_dir = OUTPUT_DIR / player_team_dir_name
    player_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: tournament_game.ext
    # Output filename: tournament_game_timestamp.ext
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{safe_tournament}_{safe_game}_{timestamp}{input_path.suffix}"

    # Run in background
    background_tasks.add_task(
        process_video_task,
        video_filename,
        sheet_url,
        game,
        player,
        str(player_team_dir_name + "/" + output_filename),  # Pass relative path
    )

    # Return status indicator that triggers polling
    return """
    <div hx-get="/status-check" hx-trigger="load" hx-swap="outerHTML">
        <div class="flex items-center justify-center p-4 bg-blue-50 rounded-lg border border-blue-200">
            <svg class="animate-spin h-5 w-5 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-blue-700 font-medium">Processing highlights...</span>
        </div>
    </div>
    """


@app.get("/files", response_class=HTMLResponse)
async def list_files():
    """Returns a list of generated files in the output directory."""
    files = []
    if OUTPUT_DIR.exists():
        # Find all video files recursively (filter for .mp4)
        for f in OUTPUT_DIR.rglob("*.mp4"):
            if f.is_file() and not f.name.startswith("."):
                files.append(f)
        # Sort by modification time, newest first
        files = sorted(files, key=os.path.getmtime, reverse=True)

    def time_ago(timestamp):
        """Format timestamp as human-readable time ago."""
        from datetime import datetime, timedelta

        diff = datetime.now() - datetime.fromtimestamp(timestamp)
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"

    html = "<ul class='divide-y divide-gray-100 bg-white rounded-md border border-gray-200 shadow-sm'>"
    for f in files:
        # Determine relative path and display info
        rel_path = f.relative_to(OUTPUT_DIR)
        mtime = os.path.getmtime(f)
        time_str = time_ago(mtime)

        parent_parts = rel_path.parts[:-1]
        dir_display = "/".join(parent_parts) if parent_parts else "Root"
        dir_display = dir_display.replace("_", " ")

        base_stem = f.stem
        base_stem = re.sub(r"_\d{8}_\d{6}$", "", base_stem)
        game_display = base_stem.replace("_", " ")
        display_name = f.name

        html += f"""
        <li class="flex items-center justify-between p-2 hover:bg-gray-50 transition">
            <div class="min-w-0 flex-1 flex items-center gap-3 mr-4">
                <!-- Video Icon -->
                <svg class="h-6 w-6 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <div class="min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{dir_display} | {game_display}</p>
                    <p class="text-xs text-gray-500 truncate" title="{display_name}">{display_name}</p>
                    <p class="text-xs text-gray-400 italic">{time_str}</p>
                </div>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
                <button 
                    hx-get="/player/{rel_path}" 
                    hx-target="#video-player-container" 
                    class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-full text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition">
                    Play
                </button>
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

    hls_playlist = None
    hls_dir = hls_dir_for(full_path)
    if hls_dir.exists():
        playlist = hls_dir / "playlist.m3u8"
        if playlist.exists():
            hls_playlist = playlist.relative_to(OUTPUT_DIR)

    return f"""
    <div class="bg-black rounded-lg overflow-hidden shadow-lg">
        <div class="bg-gray-800 text-white px-4 py-2 flex justify-between items-center">
            <span class="font-medium">{Path(file_path).name}</span>
            <button onclick="this.closest('#video-player-container').innerHTML=''" class="text-gray-400 hover:text-white">&times;</button>
        </div>
        <video id="hc-video-player" controls autoplay class="w-full max-h-[80vh]" preload="metadata">
            <source src="/videos/{file_path}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@1"></script>
    <script>
        (function() {{
            const video = document.getElementById('hc-video-player');
            const hlsUrl = {f"'/videos/{hls_playlist}'" if hls_playlist else "null"};
            if (!hlsUrl) {{
                return;
            }}
            if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                video.src = hlsUrl;
                video.play();
            }} else if (window.Hls) {{
                const hls = new Hls({{debug: false}});
                hls.loadSource(hlsUrl);
                hls.attachMedia(video);
                hls.on(Hls.Events.ERROR, function (event, data) {{
                    if (data.fatal) {{
                        hls.destroy();
                        video.src = "/videos/{file_path}";
                    }}
                }});
            }}
        }})();
    </script>
    """


@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    full_path = OUTPUT_DIR / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Remove timestamp from download filename for cleaner user experience
    # File on disk: tournament_game_20251126_152800.mp4
    # Download as: tournament_game.mp4
    original_name = Path(file_path).name
    # Remove timestamp pattern _YYYYMMDD_HHMMSS before extension
    import re

    clean_name = re.sub(r"_\d{8}_\d{6}(\.[^.]+)$", r"\1", original_name)

    return FileResponse(full_path, filename=clean_name)


def format_seconds(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


@app.post("/get-clips", response_class=HTMLResponse)
async def get_clips(
    request: Request,
    sheet_url: str = Form(...),
    game: str = Form(...),
    player: str = Form(...),
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
        rows = ""
        for clip in clips:
            bg_class = (
                "bg-red-50 text-red-800" if not clip.included else "hover:bg-gray-50"
            )
            opacity_class = "opacity-50" if not clip.included else ""

            # Format timestamps
            start_str = format_seconds(clip.start)
            end_str = format_seconds(clip.end)

            rows += f"""
            <tr class="border-b {bg_class} {opacity_class} transition-colors">
                <td class="py-1 px-4 font-mono text-sm">{start_str}</td>
                <td class="py-1 px-4 font-mono text-sm">{end_str}</td>
                <td class="py-1 px-4 text-center text-sm text-gray-600">{clip.notes}</td>
            </tr>
            """

        return f"""
        <div class="overflow-x-auto border rounded-lg">
            <table class="min-w-full bg-white">
                <thead class="bg-gray-100 text-gray-600 uppercase text-xs leading-normal">
                    <tr>
                        <th class="py-1 px-4 text-left">Start</th>
                        <th class="py-1 px-4 text-left">End</th>
                        <th class="py-1 px-4 text-center">Notes</th>
                    </tr>
                </thead>
                <tbody class="text-gray-600 text-sm font-light">
                    {rows}
                </tbody>
            </table>
        </div>
        """
    except Exception as e:
        logger.error(f"Error getting clips: {e}")
        return f"<div class='text-red-600'>Error loading clips: {str(e)}</div>"


@app.get("/debug-log", response_class=HTMLResponse)
async def get_debug_log():
    """Returns the content of the debug log."""
    log_file = Path("/tmp/highlight_cuts_debug.txt")
    if not log_file.exists():
        return "<div class='text-gray-500 italic'>No debug log available yet.</div>"

    content = log_file.read_text()
    return f"<pre class='text-xs font-mono bg-gray-900 text-green-400 p-4 rounded overflow-x-auto whitespace-pre-wrap'>{content}</pre>"


@app.get("/status-check", response_class=HTMLResponse)
async def check_status():
    """Check if processing is complete and return appropriate status message."""
    completion_file = Path("/tmp/highlight_cuts_complete.flag")
    if completion_file.exists():
        content = completion_file.read_text()
        player, game, timestamp = content.split("|")
        # Delete the flag file so it doesn't show up again
        completion_file.unlink()
        # Return Done message WITHOUT polling trigger (stops the polling)
        return f"""
        <div class="flex items-center justify-center p-4 bg-green-50 rounded-lg border border-green-200">
            <svg class="h-5 w-5 text-green-600 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            <span class="text-green-700 font-medium">✓ Done! Highlights for {player} completed.</span>
        </div>
        """
    # Return div with polling trigger to keep checking (wraps content to maintain structure)
    return """
    <div hx-get="/status-check" hx-trigger="load delay:2s" hx-swap="outerHTML">
        <div class="flex items-center justify-center p-4 bg-blue-50 rounded-lg border border-blue-200">
            <svg class="animate-spin h-5 w-5 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-blue-700 font-medium">Processing highlights...</span>
        </div>
    </div>
    """
