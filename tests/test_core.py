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
