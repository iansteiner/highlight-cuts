"""
Tests for cache module.
"""

import tempfile
from pathlib import Path

import pytest

from highlight_cuts.cache import (
    append_to_cache,
    clear_cache,
    delete_cache_entry,
    extract_sheet_info,
    get_sheet_title,
    read_cache,
)
from unittest.mock import patch, MagicMock


def test_extract_sheet_info_basic():
    """Test extracting sheet_id and gid from basic URL."""
    url = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/edit"
    sheet_id, gid = extract_sheet_info(url)
    assert sheet_id == "1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM"
    assert gid == "0"  # Default when not specified


def test_extract_sheet_info_with_gid():
    """Test extracting sheet_id and gid from URL with gid parameter."""
    url = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/edit#gid=123"
    sheet_id, gid = extract_sheet_info(url)
    assert sheet_id == "1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM"
    assert gid == "123"


def test_extract_sheet_info_export_url():
    """Test extracting from export URL."""
    url = "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=456"
    sheet_id, gid = extract_sheet_info(url)
    assert sheet_id == "abc123"
    assert gid == "456"


def test_extract_sheet_info_invalid_url():
    """Test that invalid URL raises ValueError."""
    with pytest.raises(ValueError, match="Invalid Google Sheets URL"):
        extract_sheet_info("https://example.com/not-a-sheet")


def test_read_cache_empty():
    """Test reading cache when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        entries = read_cache(output_dir)
        assert entries == []


def test_append_to_cache_creates_file():
    """Test that appending to cache creates the file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        cache_file = output_dir / ".sheet_cache.txt"

        assert not cache_file.exists()

        append_to_cache(
            output_dir,
            "https://docs.google.com/spreadsheets/d/test123/edit",
            "Test Sheet",
        )

        assert cache_file.exists()


def test_append_and_read_cache():
    """Test appending to and reading from cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        url1 = "https://docs.google.com/spreadsheets/d/sheet1/edit"
        url2 = "https://docs.google.com/spreadsheets/d/sheet2/edit#gid=5"

        append_to_cache(output_dir, url1, "Game 1")
        append_to_cache(output_dir, url2, "Game 2")

        entries = read_cache(output_dir)

        assert len(entries) == 2
        # Most recent first
        assert entries[0]["sheet_name"] == "Game 2"
        assert entries[0]["original_url"] == url2
        assert entries[0]["gid"] == "5"

        assert entries[1]["sheet_name"] == "Game 1"
        assert entries[1]["original_url"] == url1
        assert entries[1]["gid"] == "0"


def test_cache_deduplication():
    """Test that duplicate (sheet_id, gid) pairs are deduplicated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        url = "https://docs.google.com/spreadsheets/d/test123/edit"

        # Add same URL twice with different names
        append_to_cache(output_dir, url, "First Name")
        append_to_cache(output_dir, url, "Second Name")

        entries = read_cache(output_dir)

        # Should only have 1 entry (the newest)
        assert len(entries) == 1
        assert entries[0]["sheet_name"] == "Second Name"


def test_cache_deduplication_different_gids():
    """Test that same sheet_id but different gids are kept separately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        url1 = "https://docs.google.com/spreadsheets/d/test123/edit"
        url2 = "https://docs.google.com/spreadsheets/d/test123/edit#gid=5"

        append_to_cache(output_dir, url1, "Tab 1")
        append_to_cache(output_dir, url2, "Tab 2")

        entries = read_cache(output_dir)

        # Should have 2 entries (different gids)
        assert len(entries) == 2


def test_cache_max_entries():
    """Test that cache respects MAX_CACHE_ENTRIES limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Add 25 entries (max is 20)
        for i in range(25):
            url = f"https://docs.google.com/spreadsheets/d/sheet{i}/edit"
            append_to_cache(output_dir, url, f"Game {i}")

        entries = read_cache(output_dir)

        # Should only have 20 entries (most recent)
        assert len(entries) == 20
        # Should have the newest entries
        assert entries[0]["sheet_name"] == "Game 24"
        assert entries[19]["sheet_name"] == "Game 5"


def test_read_cache_malformed_lines():
    """Test that malformed lines are skipped gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        cache_file = output_dir / ".sheet_cache.txt"

        # Write some malformed data
        cache_file.write_text(
            "invalid line\n"
            "1234567890|sheet1|0|https://example.com|Good Entry\n"
            "missing|pipes\n"
            "1234567891|sheet2|0|https://example.com|Another Good\n"
        )

        entries = read_cache(output_dir)

        # Should have 2 valid entries
        assert len(entries) == 2
        assert entries[0]["sheet_name"] == "Another Good"
        assert entries[1]["sheet_name"] == "Good Entry"


def test_clear_cache():
    """Test clearing the cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        cache_file = output_dir / ".sheet_cache.txt"

        append_to_cache(
            output_dir, "https://docs.google.com/spreadsheets/d/test/edit", "Test"
        )
        assert cache_file.exists()

        clear_cache(output_dir)
        assert not cache_file.exists()


def test_clear_cache_when_not_exists():
    """Test clearing cache when file doesn't exist (should not error)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        clear_cache(output_dir)  # Should not raise


def test_delete_cache_entry():
    """Test deleting a specific cache entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        url1 = "https://docs.google.com/spreadsheets/d/sheet1/edit"
        url2 = "https://docs.google.com/spreadsheets/d/sheet2/edit"

        append_to_cache(output_dir, url1, "Game 1")
        append_to_cache(output_dir, url2, "Game 2")

        # Delete first entry
        deleted = delete_cache_entry(output_dir, "sheet1", "0")
        assert deleted is True

        entries = read_cache(output_dir)
        assert len(entries) == 1
        assert entries[0]["sheet_id"] == "sheet2"


def test_delete_cache_entry_specific_gid():
    """Test deleting entry with specific gid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        url1 = "https://docs.google.com/spreadsheets/d/test/edit"
        url2 = "https://docs.google.com/spreadsheets/d/test/edit#gid=5"

        append_to_cache(output_dir, url1, "Tab 0")
        append_to_cache(output_dir, url2, "Tab 5")

        # Delete only gid=5
        deleted = delete_cache_entry(output_dir, "test", "5")
        assert deleted is True

        entries = read_cache(output_dir)
        assert len(entries) == 1
        assert entries[0]["gid"] == "0"


def test_delete_cache_entry_not_found():
    """Test deleting entry that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        append_to_cache(
            output_dir, "https://docs.google.com/spreadsheets/d/test/edit", "Test"
        )

        deleted = delete_cache_entry(output_dir, "nonexistent", "0")
        assert deleted is False


def test_invalid_url_handling():
    """Test that invalid URLs are handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Should not crash, just log error
        append_to_cache(output_dir, "https://example.com/invalid", "Invalid")

        entries = read_cache(output_dir)
        assert len(entries) == 0  # Invalid URL not added


def test_cache_file_format():
    """Test the exact format of cache file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        cache_file = output_dir / ".sheet_cache.txt"

        append_to_cache(
            output_dir,
            "https://docs.google.com/spreadsheets/d/test123/edit#gid=5",
            "Test Game",
        )

        content = cache_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 1
        parts = lines[0].split("|")
        assert len(parts) == 5
        assert parts[1] == "test123"  # sheet_id
        assert parts[2] == "5"  # gid
        assert parts[3] == "https://docs.google.com/spreadsheets/d/test123/edit#gid=5"
        assert parts[4] == "Test Game"


@patch("highlight_cuts.cache.requests.get")
def test_get_sheet_title_success(mock_get):
    """Test successfully extracting sheet title from HTML."""
    mock_response = MagicMock()
    mock_response.text = (
        "<html><head><title>My Game Sheet - Google Sheets</title></head></html>"
    )
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = get_sheet_title("https://docs.google.com/spreadsheets/d/test123/edit")
    assert title == "My Game Sheet"


@patch("highlight_cuts.cache.requests.get")
def test_get_sheet_title_without_suffix(mock_get):
    """Test extracting title without Google Sheets suffix."""
    mock_response = MagicMock()
    mock_response.text = "<html><head><title>Tournament Data</title></head></html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = get_sheet_title("https://docs.google.com/spreadsheets/d/abc/edit")
    assert title == "Tournament Data"


@patch("highlight_cuts.cache.requests.get")
def test_get_sheet_title_network_error(mock_get):
    """Test handling network errors when fetching title."""
    mock_get.side_effect = Exception("Network error")

    title = get_sheet_title("https://docs.google.com/spreadsheets/d/test123/edit")
    assert title is None


def test_get_sheet_title_invalid_url():
    """Test getting title from invalid URL returns None."""
    title = get_sheet_title("https://example.com/not-a-sheet")
    assert title is None


@patch("highlight_cuts.cache.get_sheet_title")
def test_append_to_cache_with_auto_title(mock_get_title):
    """Test that append_to_cache fetches title when not provided."""
    mock_get_title.return_value = "Auto Fetched Title"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Don't provide sheet_name - should auto-fetch
        append_to_cache(
            output_dir, "https://docs.google.com/spreadsheets/d/test123/edit"
        )

        entries = read_cache(output_dir)
        assert len(entries) == 1
        assert entries[0]["sheet_name"] == "Auto Fetched Title"
        mock_get_title.assert_called_once()


@patch("highlight_cuts.cache.get_sheet_title")
def test_append_to_cache_title_fetch_fails(mock_get_title):
    """Test fallback when title fetch fails."""
    mock_get_title.return_value = None  # Simulate fetch failure

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        append_to_cache(
            output_dir, "https://docs.google.com/spreadsheets/d/test123abc/edit"
        )

        entries = read_cache(output_dir)
        assert len(entries) == 1
        # Should use fallback with truncated sheet_id
        assert entries[0]["sheet_name"] == "Sheet test123a"


def test_append_to_cache_with_explicit_name():
    """Test that explicit sheet_name is used over auto-fetch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Provide explicit name
        append_to_cache(
            output_dir,
            "https://docs.google.com/spreadsheets/d/test123/edit",
            sheet_name="Explicit Name",
        )

        entries = read_cache(output_dir)
        assert len(entries) == 1
        assert entries[0]["sheet_name"] == "Explicit Name"
