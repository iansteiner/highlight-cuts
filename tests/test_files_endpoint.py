"""Test the /files endpoint."""

from fastapi.testclient import TestClient
from highlight_cuts.web import app
from pathlib import Path
from unittest.mock import patch
import tempfile
import time

client = TestClient(app)


def test_files_endpoint_empty_directory():
    """Test /files endpoint with no files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
            response = client.get("/files")

            assert response.status_code == 200
            # Should return an empty list
            assert "<ul" in response.text
            assert "</ul>" in response.text


def test_files_endpoint_with_files():
    """Test /files endpoint with some MP4 files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a player directory and a file
        player_dir = tmpdir_path / "Player1_TeamA"
        player_dir.mkdir()

        file1 = player_dir / "Tournament1_Game1_20251128_120000.mp4"
        file1.touch()

        # Wait a moment to ensure different mtimes
        time.sleep(0.01)

        file2 = player_dir / "Tournament1_Game2_20251128_130000.mp4"
        file2.touch()

        with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path):
            response = client.get("/files")

            assert response.status_code == 200
            assert "<ul" in response.text
            # Should contain both files
            assert "Tournament1" in response.text
            assert "Game1" in response.text or "Game2" in response.text
            # Should have Player1 TeamA in the display
            assert "Player1" in response.text or "TeamA" in response.text
            # Should have Play and Download buttons
            assert "Play" in response.text
            assert "Download" in response.text or "download" in response.text


def test_files_endpoint_sorts_by_mtime():
    """Test that /files endpoint sorts files by modification time (newest first)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        player_dir = tmpdir_path / "Player1_TeamA"
        player_dir.mkdir()

        # Create files with deliberate timing
        file1 = player_dir / "old_file_20251127_120000.mp4"
        file1.touch()

        time.sleep(0.1)

        file2 = player_dir / "new_file_20251128_120000.mp4"
        file2.touch()

        with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path):
            response = client.get("/files")

            assert response.status_code == 200
            # Newer file should appear before older file in HTML
            new_idx = response.text.find("new_file")
            old_idx = response.text.find("old_file")

            # Both should be found
            assert new_idx != -1
            assert old_idx != -1

            # Newer should come first (smaller index)
            assert new_idx < old_idx


def test_files_endpoint_ignores_hidden_files():
    """Test that /files endpoint ignores hidden files (starting with .)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        player_dir = tmpdir_path / "Player1_TeamA"
        player_dir.mkdir()

        # Create a normal file and a hidden file
        normal_file = player_dir / "normal.mp4"
        normal_file.touch()

        hidden_file = player_dir / ".hidden.mp4"
        hidden_file.touch()

        with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path):
            response = client.get("/files")

            assert response.status_code == 200
            assert "normal.mp4" in response.text
            assert ".hidden.mp4" not in response.text


def test_files_endpoint_supports_multiple_video_formats():
    """Test that /files endpoint supports .mp4, .mov, .mkv, .avi (but not .ts)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        player_dir = tmpdir_path / "Player1_TeamA"
        player_dir.mkdir()

        # Create files with different extensions
        main_video_extensions = [".mp4", ".mov", ".mkv", ".avi"]
        for ext in main_video_extensions:
            file = player_dir / f"video{ext}"
            file.touch()

        # Create .ts file (HLS segment) - should NOT be listed
        ts_file = player_dir / "video.ts"
        ts_file.touch()

        with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path):
            response = client.get("/files")

            assert response.status_code == 200
            # Main video formats should be listed
            for ext in main_video_extensions:
                assert f"video{ext}" in response.text
            # .ts files should NOT be listed (they are HLS segments)
            assert "video.ts" not in response.text
