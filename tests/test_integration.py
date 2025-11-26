import pytest
import subprocess
import os
import json
from click.testing import CliRunner
from highlight_cuts.cli import main

TEST_VIDEO = "integration_test_video.mp4"
TEST_CSV = "integration_test.csv"


def generate_test_video(path: str, duration: int = 30):
    """Generates a test video using ffmpeg if it doesn't exist."""
    if os.path.exists(path):
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=640x360:rate=30",
        "-c:v",
        "libx264",
        "-g",
        "30",  # Force keyframe every 30 frames (1 second) for precise cutting
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def get_video_duration(path: str) -> float:
    """Returns the duration of a video file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        path,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


@pytest.fixture(scope="module")
def setup_media():
    """Fixture to create test media once per session."""
    generate_test_video(TEST_VIDEO)
    yield
    # Cleanup is optional, keeping it helps debugging.
    # But let's clean up the CSV and outputs, keep the big video.
    if os.path.exists(TEST_CSV):
        os.remove(TEST_CSV)


def test_end_to_end_workflow(setup_media):
    """
    Integration test that runs the full CLI against a real (generated) video.
    """
    # 1. Create a CSV with known timestamps
    # Video is 30s long.
    # Clip 1: 00:00:05 - 00:00:10 (5s)
    # Clip 2: 00:00:20 - 00:00:25 (5s)
    csv_content = """videoName,startTime,stopTime,playerName,notes,include
TestGame,00:00:05,00:00:10,TestPlayer,note1,TRUE
TestGame,00:00:20,00:00:25,TestPlayer,note2,TRUE
"""
    with open(TEST_CSV, "w") as f:
        f.write(csv_content)

    # 2. Run the CLI
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--input-video", TEST_VIDEO, "--csv-file", TEST_CSV, "--game", "TestGame"],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # 3. Verify Output
    # Expected filename: integration_test_video_TestPlayer.mp4
    # (stem + _ + safe_player + suffix)
    expected_output = "integration_test_video_TestPlayer.mp4"

    assert os.path.exists(expected_output), "Output video was not created"

    try:
        # 4. Verify Duration
        # We expect 2 clips of 5s each = 10s total.
        # Note: Keyframe snapping might cause slight variance, so we use approx.
        duration = get_video_duration(expected_output)
        assert abs(duration - 10.0) < 1.0, f"Expected ~10s, got {duration}s"
    finally:
        # Cleanup output
        if os.path.exists(expected_output):
            os.remove(expected_output)
