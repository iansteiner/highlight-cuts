import pytest
from highlight_cuts.core import merge_intervals, process_csv
import tempfile
import os


def test_merge_intervals_no_overlap():
    intervals = [(0, 10), (20, 30)]
    merged = merge_intervals(intervals)
    assert merged == [(0, 10), (20, 30)]


def test_merge_intervals_overlap():
    intervals = [(0, 10), (5, 15)]
    merged = merge_intervals(intervals)
    assert merged == [(0, 15)]


def test_merge_intervals_adjacent():
    intervals = [(0, 10), (10, 20)]
    merged = merge_intervals(intervals)
    assert merged == [(0, 20)]


def test_merge_intervals_padding():
    intervals = [(10, 20)]
    merged = merge_intervals(intervals, padding=1.0)
    assert merged == [(9.0, 21.0)]


def test_merge_intervals_padding_overlap():
    # (10, 20) -> (9, 21)
    # (22, 30) -> (21, 31)
    # Should merge because 21 == 21
    intervals = [(10, 20), (22, 30)]
    merged = merge_intervals(intervals, padding=1.0)
    assert merged == [(9.0, 31.0)]


def test_process_csv():
    csv_content = """videoName,startTime,stopTime,playerName
game1,00:01:00,00:01:10,PlayerA
game1,00:02:00,00:02:10,PlayerA
game1,00:01:00,00:01:10,PlayerB
game2,00:05:00,00:05:10,PlayerA
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        # Test game1
        clips = process_csv(csv_path, "game1")
        assert "PlayerA" in clips
        assert len(clips["PlayerA"]) == 2
        assert clips["PlayerA"][0] == (60.0, 70.0)

        assert "PlayerB" in clips
        assert len(clips["PlayerB"]) == 1

        # Test game2
        clips2 = process_csv(csv_path, "game2")
        assert "PlayerA" in clips2
        assert len(clips2["PlayerA"]) == 1
        assert "PlayerB" not in clips2

    finally:
        os.remove(csv_path)


def test_process_csv_missing_columns():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("col1,col2\n1,2")
        csv_path = f.name

    try:
        with pytest.raises(ValueError, match="CSV missing required columns"):
            process_csv(csv_path, "game")
    finally:
        os.remove(csv_path)


def test_process_csv_invalid_file():
    with pytest.raises(Exception):
        process_csv("non_existent.csv", "game")


def test_process_csv_bad_timestamps():
    csv_content = "videoName,startTime,stopTime,playerName\ngame,bad,time,p1"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        with pytest.raises(Exception):
            process_csv(csv_path, "game")
    finally:
        os.remove(csv_path)


class TestNormalizeSheetsUrl:
    """Tests for Google Sheets URL normalization."""

    def test_normalize_regular_share_url(self):
        """Test conversion of regular sharing URL."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = "https://docs.google.com/spreadsheets/d/ABC123/edit?usp=sharing"
        expected = (
            "https://docs.google.com/spreadsheets/d/ABC123/gviz/tq?tqx=out:csv&gid=0"
        )
        assert normalize_sheets_url(input_url) == expected

    def test_normalize_url_with_gid(self):
        """Test conversion of URL with specific sheet ID."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = "https://docs.google.com/spreadsheets/d/ABC123/edit#gid=456"
        expected = (
            "https://docs.google.com/spreadsheets/d/ABC123/gviz/tq?tqx=out:csv&gid=456"
        )
        assert normalize_sheets_url(input_url) == expected

    def test_normalize_url_with_gid_in_query(self):
        """Test conversion of URL with gid in query string."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = (
            "https://docs.google.com/spreadsheets/d/ABC123/edit?usp=sharing&gid=789"
        )
        expected = (
            "https://docs.google.com/spreadsheets/d/ABC123/gviz/tq?tqx=out:csv&gid=789"
        )
        assert normalize_sheets_url(input_url) == expected

    def test_normalize_already_export_url(self):
        """Test that export URLs are converted to gviz format."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = (
            "https://docs.google.com/spreadsheets/d/ABC123/export?format=csv&gid=0"
        )
        # Even export URLs get normalized to gviz format
        expected = (
            "https://docs.google.com/spreadsheets/d/ABC123/gviz/tq?tqx=out:csv&gid=0"
        )
        assert normalize_sheets_url(input_url) == expected

    def test_normalize_local_file_path(self):
        """Test that local file paths pass through unchanged."""
        from highlight_cuts.core import normalize_sheets_url

        input_path = "./data/clips.csv"
        assert normalize_sheets_url(input_path) == input_path

    def test_normalize_absolute_file_path(self):
        """Test that absolute file paths pass through unchanged."""
        from highlight_cuts.core import normalize_sheets_url

        input_path = "/Users/test/data/clips.csv"
        assert normalize_sheets_url(input_path) == input_path

    def test_normalize_other_url(self):
        """Test that non-Sheets URLs pass through unchanged."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = "https://example.com/data.csv"
        assert normalize_sheets_url(input_url) == input_url

    def test_normalize_complex_sheet_id(self):
        """Test with complex sheet ID containing hyphens and underscores."""
        from highlight_cuts.core import normalize_sheets_url

        input_url = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/edit?usp=sharing"
        expected = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/gviz/tq?tqx=out:csv&gid=0"
        assert normalize_sheets_url(input_url) == expected


@pytest.mark.integration
class TestGoogleSheetsIntegration:
    """Integration tests for Google Sheets URL support."""

    def test_process_csv_local_file(self):
        """Test that local CSV files still work."""
        result = process_csv("tests/fixtures/test_clips.csv", "TestGame")

        assert "Alice" in result
        assert "Bob" in result
        assert "Charlie" in result

        assert len(result["Alice"]) == 3
        assert len(result["Bob"]) == 3
        assert len(result["Charlie"]) == 2

    def test_process_csv_google_sheets_url(self):
        """Test reading from Google Sheets URL."""
        # This is a real integration test - requires network access
        url = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/edit?usp=sharing"
        result = process_csv(url, "TestGame")

        assert "Alice" in result
        assert "Bob" in result
        assert "Charlie" in result

        assert len(result["Alice"]) == 3
        assert len(result["Bob"]) == 3
        assert len(result["Charlie"]) == 2

    def test_process_csv_google_sheets_matches_local(self):
        """Test that Google Sheets data matches local CSV file."""
        local_result = process_csv("tests/fixtures/test_clips.csv", "TestGame")

        url = "https://docs.google.com/spreadsheets/d/1rydB9tbIIL-CsTYPSPwWzabxe_CRKXeCfH7HCcCFoxM/edit?usp=sharing"
        sheets_result = process_csv(url, "TestGame")

        # Should have same players
        assert set(local_result.keys()) == set(sheets_result.keys())

        # Should have same number of clips per player
        for player in local_result:
            assert len(local_result[player]) == len(sheets_result[player])

            # Should have same clip times
            for local_clip, sheets_clip in zip(
                local_result[player], sheets_result[player]
            ):
                assert local_clip == sheets_clip
