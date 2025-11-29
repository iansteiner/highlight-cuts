"""Test old file deletion in process_video_task."""

import tempfile
from pathlib import Path
from unittest.mock import patch
import time

from highlight_cuts.web import process_video_task
from highlight_cuts.core import Clip


@patch("highlight_cuts.web.generate_hls")
@patch("highlight_cuts.web.concat_clips")
@patch("highlight_cuts.web.extract_clip")
@patch("highlight_cuts.web.merge_intervals")
@patch("highlight_cuts.web.process_csv")
def test_old_mp4_files_deleted(
    mock_process_csv, mock_merge, mock_extract, mock_concat, mock_hls
):
    """Test that old .mp4 files are deleted when creating new ones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create input video
        (tmpdir_path / "game.mp4").touch()

        # Create player directory
        player_dir = tmpdir_path / "output" / "Player1_TeamA"
        player_dir.mkdir(parents=True)

        # Create old file
        old_file = player_dir / "Tournament1_Game1_20251127_120000.mp4"
        old_file.touch()
        time.sleep(0.01)  # Ensure different mtime

        # Mock returns
        mock_process_csv.return_value = {
            "Player1": [Clip(start=10.0, end=20.0, included=True)]
        }
        mock_merge.return_value = [(10.0, 20.0)]
        mock_extract.return_value = {"command": "", "stdout": "", "stderr": ""}

        # Make concat_clips create the output file
        def create_output_file(clips, output_path):
            Path(output_path).touch()
            return {"command": "", "stdout": "", "stderr": ""}

        mock_concat.side_effect = create_output_file
        mock_hls.return_value = {"command": "", "stdout": "", "stderr": ""}

        with patch("highlight_cuts.web.DATA_DIR", tmpdir_path):
            with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path / "output"):
                # Process with new timestamp
                process_video_task(
                    video_filename="game.mp4",
                    sheet_url="http://example.com/sheet",
                    game="Game1",
                    player="Player1",
                    output_filename="Player1_TeamA/Tournament1_Game1_20251128_120000.mp4",
                )

        # Old file should be deleted
        assert not old_file.exists()
        # New file should exist
        new_file = player_dir / "Tournament1_Game1_20251128_120000.mp4"
        assert new_file.exists()


@patch("highlight_cuts.web.generate_hls")
@patch("highlight_cuts.web.concat_clips")
@patch("highlight_cuts.web.extract_clip")
@patch("highlight_cuts.web.merge_intervals")
@patch("highlight_cuts.web.process_csv")
def test_old_mov_files_deleted(
    mock_process_csv, mock_merge, mock_extract, mock_concat, mock_hls
):
    """Test that old .mov files are deleted when creating new ones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create input video
        (tmpdir_path / "game.mov").touch()

        # Create player directory
        player_dir = tmpdir_path / "output" / "Player1_TeamA"
        player_dir.mkdir(parents=True)

        # Create old file
        old_file = player_dir / "Tournament1_Game1_20251127_120000.mov"
        old_file.touch()
        time.sleep(0.01)  # Ensure different mtime

        # Mock returns
        mock_process_csv.return_value = {
            "Player1": [Clip(start=10.0, end=20.0, included=True)]
        }
        mock_merge.return_value = [(10.0, 20.0)]
        mock_extract.return_value = {"command": "", "stdout": "", "stderr": ""}

        # Make concat_clips create the output file
        def create_output_file(clips, output_path):
            Path(output_path).touch()
            return {"command": "", "stdout": "", "stderr": ""}

        mock_concat.side_effect = create_output_file
        mock_hls.return_value = {"command": "", "stdout": "", "stderr": ""}

        with patch("highlight_cuts.web.DATA_DIR", tmpdir_path):
            with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path / "output"):
                # Process with new timestamp
                process_video_task(
                    video_filename="game.mov",
                    sheet_url="http://example.com/sheet",
                    game="Game1",
                    player="Player1",
                    output_filename="Player1_TeamA/Tournament1_Game1_20251128_120000.mov",
                )

        # Old file should be deleted
        assert not old_file.exists()
        # New file should exist
        new_file = player_dir / "Tournament1_Game1_20251128_120000.mov"
        assert new_file.exists()


@patch("highlight_cuts.web.generate_hls")
@patch("highlight_cuts.web.concat_clips")
@patch("highlight_cuts.web.extract_clip")
@patch("highlight_cuts.web.merge_intervals")
@patch("highlight_cuts.web.process_csv")
def test_old_files_different_extensions_not_deleted(
    mock_process_csv, mock_merge, mock_extract, mock_concat, mock_hls
):
    """Test that old files with different extensions are NOT deleted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create input video
        (tmpdir_path / "game.mp4").touch()

        # Create player directory
        player_dir = tmpdir_path / "output" / "Player1_TeamA"
        player_dir.mkdir(parents=True)

        # Create old .mov file (should NOT be deleted when processing .mp4)
        old_mov_file = player_dir / "Tournament1_Game1_20251127_120000.mov"
        old_mov_file.touch()

        # Mock returns
        mock_process_csv.return_value = {
            "Player1": [Clip(start=10.0, end=20.0, included=True)]
        }
        mock_merge.return_value = [(10.0, 20.0)]
        mock_extract.return_value = {"command": "", "stdout": "", "stderr": ""}

        # Make concat_clips create the output file
        def create_output_file(clips, output_path):
            Path(output_path).touch()
            return {"command": "", "stdout": "", "stderr": ""}

        mock_concat.side_effect = create_output_file
        mock_hls.return_value = {"command": "", "stdout": "", "stderr": ""}

        with patch("highlight_cuts.web.DATA_DIR", tmpdir_path):
            with patch("highlight_cuts.web.OUTPUT_DIR", tmpdir_path / "output"):
                # Process .mp4 file
                process_video_task(
                    video_filename="game.mp4",
                    sheet_url="http://example.com/sheet",
                    game="Game1",
                    player="Player1",
                    output_filename="Player1_TeamA/Tournament1_Game1_20251128_120000.mp4",
                )

        # Old .mov file should still exist (different extension)
        assert old_mov_file.exists()
        # New .mp4 file should exist
        new_mp4_file = player_dir / "Tournament1_Game1_20251128_120000.mp4"
        assert new_mp4_file.exists()
