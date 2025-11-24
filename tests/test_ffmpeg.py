import pytest
import subprocess
from unittest.mock import patch, MagicMock
from highlight_cuts.ffmpeg import extract_clip, concat_clips


@patch("subprocess.run")
def test_extract_clip_success(mock_run):
    extract_clip("input.mp4", 10.0, 20.0, "output.mp4")

    expected_cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "10.000",
        "-i",
        "input.mp4",
        "-t",
        "10.000",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "1",
        "output.mp4",
    ]
    mock_run.assert_called_once_with(expected_cmd, check=True, capture_output=True)


@patch("subprocess.run")
def test_extract_clip_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr=b"Error")

    with pytest.raises(subprocess.CalledProcessError):
        extract_clip("input.mp4", 10.0, 20.0, "output.mp4")


@patch("subprocess.run")
def test_concat_clips_success(mock_run):
    clips = ["clip1.mp4", "clip2.mp4"]
    output = "final.mp4"

    # We need to mock open() as well since concat_clips writes a file
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        concat_clips(clips, output)

        # Check if list file was written
        mock_open.assert_called()

        # Check ffmpeg command
        expected_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "final.mp4.txt",
            "-c",
            "copy",
            "final.mp4",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=True, capture_output=True)


@patch("subprocess.run")
def test_concat_clips_empty(mock_run):
    concat_clips([], "out.mp4")
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_concat_clips_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr=b"Error")
    with patch("builtins.open"):
        with pytest.raises(subprocess.CalledProcessError):
            concat_clips(["c1.mp4"], "out.mp4")
