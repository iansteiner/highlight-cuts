import pandas as pd
import logging
from typing import List, Tuple, Dict
from .utils import parse_time

logger = logging.getLogger(__name__)


def normalize_sheets_url(url: str) -> str:
    """
    Converts any Google Sheets URL to CSV export format.

    Handles:
    - Regular share URLs: .../edit?usp=sharing
    - Direct edit URLs: .../edit#gid=123
    - Already-converted export URLs (returns as-is)
    - Non-Sheets URLs (returns as-is)

    Args:
        url: Google Sheets URL or regular file path

    Returns:
        CSV export URL or original input
    """
    import re

    # Not a Google Sheets URL, return as-is
    if "docs.google.com/spreadsheets" not in url:
        return url

    # Extract sheet ID
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        return url

    sheet_id = match.group(1)

    # Extract gid (sheet tab ID) if present
    gid_match = re.search(r"[#&]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"

    # Build export URL using gviz endpoint
    # This works with "Anyone with the link" sharing without needing "Publish to web"
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

    logger.debug(f"Converted Sheets URL to CSV export: {export_url}")
    return export_url


def merge_intervals(
    intervals: List[Tuple[float, float]], padding: float = 0.0
) -> List[Tuple[float, float]]:
    """
    Merges overlapping intervals and adds padding.

    Args:
        intervals: List of (start, end) tuples in seconds.
        padding: Seconds to add to both start and end of each interval.

    Returns:
        List of merged (start, end) tuples.
    """
    if not intervals:
        return []

    # Add padding and ensure non-negative start
    padded = []
    for start, end in intervals:
        s = max(0.0, start - padding)
        e = end + padding
        padded.append((s, e))

    # Sort by start time
    padded.sort(key=lambda x: x[0])

    merged = []
    current_start, current_end = padded[0]

    for next_start, next_end in padded[1:]:
        if next_start <= current_end:
            # Overlap or adjacent, merge
            current_end = max(current_end, next_end)
        else:
            # No overlap, push current and start new
            merged.append((current_start, current_end))
            current_start, current_end = next_start, next_end

    merged.append((current_start, current_end))
    return merged


def process_csv(
    csv_source: str, game_name: str
) -> Dict[str, List[Tuple[float, float]]]:
    """
    Reads CSV from file path or URL, filters by game name, and groups clips by player.

    Args:
        csv_source: Path to CSV file, Google Sheets URL, or direct CSV URL.
        game_name: Name of the video/game to filter by.

    Returns:
        Dictionary mapping player name to a list of (start, end) intervals.
    """
    # Normalize Google Sheets URLs to CSV export format
    csv_source = normalize_sheets_url(csv_source)

    logger.info(f"Reading CSV from {csv_source}")
    try:
        # Use requests for Google Sheets URLs to handle redirects properly
        # urllib has issues with Google's redirect pattern containing wildcards
        if csv_source.startswith("https://docs.google.com/spreadsheets"):
            import requests
            import io

            response = requests.get(csv_source)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
        else:
            # Use pandas directly for local files and other URLs
            df = pd.read_csv(csv_source)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        raise

    # Expected columns: videoName, startTime, stopTime, playerName
    required_cols = {"videoName", "startTime", "stopTime", "playerName"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"CSV missing required columns. Found: {df.columns}, Expected: {required_cols}"
        )

    # Filter by game
    game_df = df[df["videoName"] == game_name].copy()
    if game_df.empty:
        logger.warning(f"No clips found for game '{game_name}'")
        return {}

    # Parse times
    try:
        game_df["start_seconds"] = game_df["startTime"].apply(str).apply(parse_time)
        game_df["end_seconds"] = game_df["stopTime"].apply(str).apply(parse_time)
    except Exception as e:
        logger.error(f"Error parsing timestamps: {e}")
        raise

    # Group by player
    player_clips = {}
    for player, group in game_df.groupby("playerName"):
        intervals = list(zip(group["start_seconds"], group["end_seconds"]))
        player_clips[player] = intervals

    return player_clips
