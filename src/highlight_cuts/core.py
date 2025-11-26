import pandas as pd
import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass
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


@dataclass
class Clip:
    start: float
    end: float
    notes: str = ""
    included: bool = True


def process_csv(csv_source: str, game_name: str) -> Dict[str, List[Clip]]:
    """
    Reads CSV from file path or URL, filters by game name, and groups clips by player.

    Args:
        csv_source: Path to CSV file, Google Sheets URL, or direct CSV URL.
        game_name: Name of the video/game to filter by.

    Returns:
        Dictionary mapping player name to a list of Clip objects.
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
    # "notes" and "include" are optional in the sense that we can handle them if missing,
    # but the requirements say "read in the include column", implying it should be there.
    # However, for backward compatibility, maybe we should allow it to be missing?
    # The user said "I have now updated the source docs to have an include column".
    # So we should expect it.

    # Let's handle "include" being optional for backward compat if possible,
    # but strictly validate if present.
    # Actually, let's enforce it if the user says they updated the docs.
    # But wait, existing CSVs might break.
    # Let's check if "include" is in columns. If not, assume True for all?
    # The user said "please update the code to read in the include column".
    # I'll add it to required_cols if I want to enforce it.
    # But to be safe, I'll check if it exists.

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

    # Parse include column
    if "include" in game_df.columns:

        def parse_include(val):
            s = str(val).strip().lower()
            if s in ("true", "yes", "1"):
                return True
            if s in ("false", "no", "0"):
                return False
            if s == "" or s == "nan" or pd.isna(val):
                return True  # Blank means True
            # Detect anything that is not true or false or blank
            raise ValueError(f"Invalid value for 'include': {val}")

        try:
            game_df["included"] = game_df["include"].apply(parse_include)
        except ValueError as e:
            logger.error(f"Validation error in include column: {e}")
            raise
    else:
        game_df["included"] = True

    # Handle notes
    if "notes" not in game_df.columns:
        game_df["notes"] = ""
    else:
        game_df["notes"] = game_df["notes"].fillna("")

    # Group by player
    player_clips = {}
    for player, group in game_df.groupby("playerName"):
        clips = []
        for _, row in group.iterrows():
            clips.append(
                Clip(
                    start=row["start_seconds"],
                    end=row["end_seconds"],
                    notes=str(row["notes"]),
                    included=row["included"],
                )
            )
        player_clips[player] = clips

    return player_clips
