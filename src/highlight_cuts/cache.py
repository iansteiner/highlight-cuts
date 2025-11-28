"""
Google Sheets URL cache management.

Provides simple text-file-based caching of recently used Google Sheets URLs
for easy selection in the web interface.
"""

import fcntl
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CACHE_FILE = ".sheet_cache.txt"
MAX_CACHE_ENTRIES = 20


def get_sheet_title(url: str) -> Optional[str]:
    """
    Extract the Google Sheets document title from the sheet.

    Attempts to fetch the title from the Google Sheets HTML page.
    Falls back to None if unable to retrieve.

    Args:
        url: Google Sheets URL in any format

    Returns:
        Document title or None if unable to retrieve
    """
    try:
        # Extract sheet_id from URL
        sheet_id_match = re.search(
            r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)", url
        )
        if not sheet_id_match:
            return None

        sheet_id = sheet_id_match.group(1)

        # Fetch the HTML page to extract title
        # Use the /edit page as it has the title in the HTML
        fetch_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

        response = requests.get(fetch_url, timeout=5)
        response.raise_for_status()

        # Look for title in HTML - it's typically in <title> tag
        # Format: "Document Title - Google Sheets"
        title_match = re.search(
            r"<title>(.+?)(?: - Google Sheets)?</title>", response.text
        )
        if title_match:
            title = title_match.group(1).strip()
            # Remove " - Google Sheets" suffix if present
            title = re.sub(r"\s*-\s*Google Sheets$", "", title)
            return title

        return None

    except Exception as e:
        logger.debug(f"Could not fetch sheet title: {e}")
        return None


def extract_sheet_info(url: str) -> tuple[str, str]:
    """
    Extract sheet_id and gid from Google Sheets URL.

    Args:
        url: Google Sheets URL in any format

    Returns:
        Tuple of (sheet_id, gid)

    Raises:
        ValueError: If URL is not a valid Google Sheets URL
    """
    # Match any Google Sheets URL format
    pattern = r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)

    if not match:
        raise ValueError(f"Invalid Google Sheets URL: {url}")

    sheet_id = match.group(1)

    # Extract gid (sheet tab ID) - defaults to 0 if not present
    gid_match = re.search(r"[#&]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"

    return sheet_id, gid


def read_cache(output_dir: Path) -> List[Dict[str, str]]:
    """
    Read recent Google Sheets from cache file.

    Args:
        output_dir: Directory containing cache file

    Returns:
        List of dicts with keys: original_url, sheet_name, sheet_id, gid, timestamp
        Sorted by timestamp (most recent first)
    """
    cache_path = output_dir / CACHE_FILE

    if not cache_path.exists():
        return []

    try:
        lines = cache_path.read_text().strip().split("\n")
        entries = []

        for line in lines:
            if not line or line.count("|") != 4:
                if line:  # Only warn for non-empty malformed lines
                    logger.warning(f"Skipping malformed cache entry: {line}")
                continue

            try:
                timestamp_str, sheet_id, gid, original_url, sheet_name = line.split("|")
                entries.append(
                    {
                        "timestamp": int(timestamp_str),
                        "sheet_id": sheet_id,
                        "gid": gid,
                        "original_url": original_url,
                        "sheet_name": sheet_name,
                    }
                )
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing cache line '{line}': {e}")
                continue

        # Sort by timestamp, most recent first
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return entries

    except Exception as e:
        logger.error(f"Error reading cache file: {e}")
        return []


def append_to_cache(
    output_dir: Path, original_url: str, sheet_name: Optional[str] = None
) -> None:
    """
    Add or update Google Sheets URL in cache file.

    Deduplicates by (sheet_id, gid) pair - keeps only newest entry.
    Limits cache to MAX_CACHE_ENTRIES.
    Thread-safe using file locking.

    Args:
        output_dir: Directory containing cache file
        original_url: Original Google Sheets URL
        sheet_name: User-friendly name for the sheet (if None, attempts to fetch from Google)
    """
    cache_path = output_dir / CACHE_FILE

    try:
        # Extract sheet info for deduplication
        sheet_id, gid = extract_sheet_info(original_url)
        timestamp = int(datetime.now().timestamp())

        # If sheet_name not provided, try to fetch from Google Sheets
        if sheet_name is None:
            sheet_name = get_sheet_title(original_url)
            if sheet_name is None:
                # Fallback to sheet_id if we can't get the title
                sheet_name = f"Sheet {sheet_id[:8]}"
                logger.info(
                    f"Could not fetch sheet title, using fallback: {sheet_name}"
                )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create cache file if it doesn't exist
        if not cache_path.exists():
            cache_path.touch()

        # Use file locking for thread safety
        with open(cache_path, "r+") as f:
            try:
                # Acquire exclusive lock (blocking)
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)

                # Read existing entries
                content = f.read()
                existing_lines = [line for line in content.strip().split("\n") if line]

                # Parse existing entries and remove duplicates
                seen_keys = set()
                kept_entries = []

                # Add new entry first
                new_key = (sheet_id, gid)
                seen_keys.add(new_key)
                new_entry = f"{timestamp}|{sheet_id}|{gid}|{original_url}|{sheet_name}"
                kept_entries.append(new_entry)

                # Keep existing entries that aren't duplicates
                for line in existing_lines:
                    if line.count("|") != 4:
                        continue

                    try:
                        parts = line.split("|")
                        entry_key = (parts[1], parts[2])  # (sheet_id, gid)

                        if entry_key not in seen_keys:
                            seen_keys.add(entry_key)
                            kept_entries.append(line)
                    except (ValueError, IndexError):
                        continue

                # Limit to MAX_CACHE_ENTRIES
                kept_entries = kept_entries[:MAX_CACHE_ENTRIES]

                # Write back to file
                f.seek(0)
                f.truncate()
                f.write("\n".join(kept_entries) + "\n")

            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        logger.info(f"Added to cache: {sheet_name} ({sheet_id})")

    except ValueError as e:
        logger.error(f"Invalid URL for caching: {e}")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")


def clear_cache(output_dir: Path) -> None:
    """
    Clear all entries from cache file.

    Args:
        output_dir: Directory containing cache file
    """
    cache_path = output_dir / CACHE_FILE

    try:
        if cache_path.exists():
            cache_path.unlink()
            logger.info("Cache cleared")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")


def delete_cache_entry(output_dir: Path, sheet_id: str, gid: str = "0") -> bool:
    """
    Delete a specific entry from cache.

    Args:
        output_dir: Directory containing cache file
        sheet_id: Google Sheets ID
        gid: Sheet tab ID (defaults to "0")

    Returns:
        True if entry was deleted, False otherwise
    """
    cache_path = output_dir / CACHE_FILE

    if not cache_path.exists():
        return False

    try:
        with open(cache_path, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                content = f.read()
                lines = [line for line in content.strip().split("\n") if line]

                # Filter out the entry to delete
                kept_lines = []
                deleted = False

                for line in lines:
                    if line.count("|") != 4:
                        continue

                    parts = line.split("|")
                    if parts[1] == sheet_id and parts[2] == gid:
                        deleted = True
                        continue

                    kept_lines.append(line)

                if deleted:
                    # Write back
                    f.seek(0)
                    f.truncate()
                    if kept_lines:
                        f.write("\n".join(kept_lines) + "\n")
                    logger.info(f"Deleted cache entry: {sheet_id} (gid={gid})")

                return deleted

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    except Exception as e:
        logger.error(f"Error deleting cache entry: {e}")
        return False
