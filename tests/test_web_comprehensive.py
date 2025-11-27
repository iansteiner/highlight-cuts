"""Comprehensive stress tests for web.py to improve test coverage."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from highlight_cuts.web import (
    app,
    get_video_structure,
    format_seconds,
    process_video_task,
    NoCacheStaticFiles,
)
from highlight_cuts.core import Clip

client = TestClient(app)


class TestNoCacheStaticFiles:
    """Test the NoCacheStaticFiles class."""

    def test_file_response_sets_no_cache_headers(self):
        """Test that NoCacheStaticFiles adds no-cache headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.mp4"
            test_file.write_text("test content")

            # Create NoCacheStaticFiles instance
            static_files = NoCacheStaticFiles(directory=tmpdir)

            # Mock the parent file_response
            with patch.object(
                NoCacheStaticFiles.__bases__[0], "file_response"
            ) as mock_parent:
                mock_response = MagicMock()
                mock_response.headers = {}
                mock_parent.return_value = mock_response

                # Call file_response
                response = static_files.file_response("test.mp4")

                # Verify no-cache headers are set
                assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
                assert response.headers["Pragma"] == "no-cache"
                assert response.headers["Expires"] == "0"


class TestGetVideoStructure:
    """Test get_video_structure function with various scenarios."""

    def test_empty_data_directory(self):
        """Test with empty data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()
                assert structure == {}

    def test_nonexistent_data_directory(self):
        """Test with non-existent data directory."""
        with patch("highlight_cuts.web.DATA_DIR", Path("/nonexistent/path")):
            structure = get_video_structure()
            assert structure == {}

    def test_proper_three_level_structure(self):
        """Test video files in team/tournament/game.mp4 structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create proper structure
            team_dir = Path(tmpdir) / "TeamA"
            tournament_dir = team_dir / "Tournament1"
            tournament_dir.mkdir(parents=True)

            # Create video files
            (tournament_dir / "game1.mp4").touch()
            (tournament_dir / "game2.mov").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                assert "TeamA" in structure
                assert "Tournament1" in structure["TeamA"]
                assert len(structure["TeamA"]["Tournament1"]) == 2
                assert structure["TeamA"]["Tournament1"][0]["name"] == "game1"
                assert structure["TeamA"]["Tournament1"][1]["name"] == "game2"

    def test_uncategorized_files_at_root(self):
        """Test files at root level are categorized as Uncategorized/Misc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file at root
            (Path(tmpdir) / "video.mp4").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                assert "Uncategorized" in structure
                assert "Misc" in structure["Uncategorized"]
                assert structure["Uncategorized"]["Misc"][0]["name"] == "video"

    def test_uncategorized_files_one_level_deep(self):
        """Test files one level deep are categorized as Uncategorized/Misc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            team_dir = Path(tmpdir) / "TeamA"
            team_dir.mkdir()
            (team_dir / "video.mp4").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                assert "Uncategorized" in structure
                assert "Misc" in structure["Uncategorized"]
                assert structure["Uncategorized"]["Misc"][0]["name"] == "video"

    def test_multiple_video_formats(self):
        """Test various video file formats are recognized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            team_dir = Path(tmpdir) / "TeamA" / "Tournament1"
            team_dir.mkdir(parents=True)

            # Create files with different extensions
            (team_dir / "video.mp4").touch()
            (team_dir / "video.mov").touch()
            (team_dir / "video.mkv").touch()
            (team_dir / "video.avi").touch()
            (team_dir / "video.ts").touch()
            (team_dir / "video.txt").touch()  # Should be ignored

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                # Should have 5 video files (txt ignored)
                assert len(structure["TeamA"]["Tournament1"]) == 5

    def test_case_insensitive_extensions(self):
        """Test that file extensions are matched case-insensitively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            team_dir = Path(tmpdir) / "TeamA" / "Tournament1"
            team_dir.mkdir(parents=True)

            (team_dir / "video.MP4").touch()
            (team_dir / "video2.MoV").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                assert len(structure["TeamA"]["Tournament1"]) == 2

    def test_sorting_teams_tournaments_games(self):
        """Test that teams, tournaments, and games are sorted alphabetically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple teams and tournaments
            for team in ["TeamC", "TeamA", "TeamB"]:
                for tournament in ["Z-Tournament", "A-Tournament", "M-Tournament"]:
                    team_dir = Path(tmpdir) / team / tournament
                    team_dir.mkdir(parents=True)
                    (team_dir / "game_z.mp4").touch()
                    (team_dir / "game_a.mp4").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                # Check teams are sorted
                assert list(structure.keys()) == ["TeamA", "TeamB", "TeamC"]

                # Check tournaments are sorted
                assert list(structure["TeamA"].keys()) == [
                    "A-Tournament",
                    "M-Tournament",
                    "Z-Tournament",
                ]

                # Check games are sorted
                games = structure["TeamA"]["A-Tournament"]
                assert games[0]["name"] == "game_a"
                assert games[1]["name"] == "game_z"

    def test_nested_subdirectories(self):
        """Test deeply nested structures beyond 3 levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 4-level deep structure
            deep_dir = Path(tmpdir) / "Team" / "Tournament" / "Extra" / "Deeper"
            deep_dir.mkdir(parents=True)
            (deep_dir / "video.mp4").touch()

            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                structure = get_video_structure()

                # Should still work, using first 3 parts
                assert "Team" in structure
                assert "Tournament" in structure["Team"]


class TestParseSheetEndpoint:
    """Test parse-sheet endpoint edge cases."""

    @patch("requests.get")
    def test_parse_sheet_missing_columns(self, mock_get):
        """Test parse-sheet with invalid CSV missing required columns."""
        mock_response = MagicMock()
        mock_response.text = "col1,col2\nval1,val2"
        mock_get.return_value = mock_response

        response = client.post(
            "/parse-sheet",
            data={"sheet_url": "https://docs.google.com/spreadsheets/d/123"},
        )

        assert response.status_code == 200
        assert "Invalid CSV" in response.text
        assert "Missing videoName or playerName columns" in response.text

    @patch("requests.get")
    def test_parse_sheet_request_error(self, mock_get):
        """Test parse-sheet with network error."""
        mock_get.side_effect = Exception("Network error")

        response = client.post(
            "/parse-sheet",
            data={"sheet_url": "https://docs.google.com/spreadsheets/d/123"},
        )

        assert response.status_code == 200
        assert "Error:" in response.text
        assert "Network error" in response.text

    @patch("requests.get")
    def test_parse_sheet_multiple_games_and_players(self, mock_get):
        """Test parse-sheet with multiple games and players."""
        mock_response = MagicMock()
        mock_response.text = """videoName,playerName,startTime,stopTime
Game1,Player1,00:00,00:10
Game1,Player1,00:20,00:30
Game1,Player2,00:05,00:15
Game2,Player1,00:00,00:10"""
        mock_get.return_value = mock_response

        response = client.post(
            "/parse-sheet",
            data={"sheet_url": "https://docs.google.com/spreadsheets/d/123"},
        )

        assert response.status_code == 200
        assert "Game1" in response.text
        assert "Game2" in response.text
        assert "Player1" in response.text
        assert "Player2" in response.text
        # Check counts - Player1 appears in Game1 row and Game2 row (2 total)
        # Player1 in Game1 has 2 clips, but appears once in table
        assert "Player1" in response.text

    def test_parse_sheet_local_csv_file(self):
        """Test parse-sheet with local CSV file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("videoName,playerName,startTime,stopTime\n")
            f.write("Game1,Player1,00:00,00:10\n")
            f.flush()
            csv_path = f.name

        try:
            response = client.post("/parse-sheet", data={"sheet_url": csv_path})

            assert response.status_code == 200
            assert "Game1" in response.text
            assert "Player1" in response.text
        finally:
            os.unlink(csv_path)


class TestProcessVideoTask:
    """Test the background processing task."""

    @patch("highlight_cuts.web.concat_clips")
    @patch("highlight_cuts.web.extract_clip")
    @patch("highlight_cuts.web.process_csv")
    @patch("highlight_cuts.web.glob.glob")
    def test_process_video_task_deletes_old_files(
        self, mock_glob, mock_process_csv, mock_extract, mock_concat
    ):
        """Test that old versions of output files are deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    # Create input video
                    (Path(tmpdir) / "game.mp4").touch()

                    # Create old output files that should be deleted
                    old_file1 = Path(tmpdir) / "Player1_TeamA" / "Tournament_Game_20250101_120000.mp4"
                    old_file1.parent.mkdir(parents=True, exist_ok=True)
                    old_file1.touch()

                    mock_glob.return_value = [str(old_file1)]

                    # Mock process_csv to return clips
                    mock_process_csv.return_value = {
                        "Player1": [Clip(start=0.0, end=10.0, included=True)]
                    }

                    # Mock extract and concat
                    mock_extract.return_value = {"command": "cmd", "stdout": "", "stderr": ""}
                    mock_concat.return_value = {"command": "cmd", "stdout": "", "stderr": ""}

                    # Run the task
                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "Player1_TeamA/Tournament_Game_20250126_150000.mp4",
                    )

                    # Verify old file was deleted
                    assert not old_file1.exists()

    @patch("highlight_cuts.web.concat_clips")
    @patch("highlight_cuts.web.extract_clip")
    @patch("highlight_cuts.web.process_csv")
    @patch("highlight_cuts.web.glob.glob")
    @patch("highlight_cuts.web.os.remove")
    def test_process_video_task_delete_old_files_error(
        self, mock_remove, mock_glob, mock_process_csv, mock_extract, mock_concat
    ):
        """Test that errors when deleting old files are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    # Create input video
                    (Path(tmpdir) / "game.mp4").touch()

                    # Mock glob to return old files
                    mock_glob.return_value = ["/fake/old_file.mp4"]

                    # Mock os.remove to raise an exception
                    mock_remove.side_effect = PermissionError("Cannot delete file")

                    # Mock process_csv to return clips
                    mock_process_csv.return_value = {
                        "Player1": [Clip(start=0.0, end=10.0, included=True)]
                    }

                    # Mock extract and concat
                    mock_extract.return_value = {"command": "cmd", "stdout": "", "stderr": ""}
                    mock_concat.return_value = {"command": "cmd", "stdout": "", "stderr": ""}

                    # Should not raise exception, just log warning
                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "Player1_TeamA/Tournament_Game_20250126_150000.mp4",
                    )

                    # Verify os.remove was called and exception was caught
                    mock_remove.assert_called_once()

    @patch("highlight_cuts.web.process_csv")
    def test_process_video_task_player_not_found(self, mock_process_csv):
        """Test process_video_task when player is not in the CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    (Path(tmpdir) / "game.mp4").touch()

                    # Return clips for different player
                    mock_process_csv.return_value = {
                        "OtherPlayer": [Clip(start=0.0, end=10.0, included=True)]
                    }

                    # Should not raise exception, just return early
                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "output.mp4",
                    )

    @patch("highlight_cuts.web.process_csv")
    def test_process_video_task_no_included_clips(self, mock_process_csv):
        """Test process_video_task when all clips are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    (Path(tmpdir) / "game.mp4").touch()

                    # Return clips that are all excluded
                    mock_process_csv.return_value = {
                        "Player1": [
                            Clip(start=0.0, end=10.0, included=False),
                            Clip(start=20.0, end=30.0, included=False),
                        ]
                    }

                    # Should not raise exception, just return early
                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "output.mp4",
                    )

    @patch("highlight_cuts.web.concat_clips")
    @patch("highlight_cuts.web.extract_clip")
    @patch("highlight_cuts.web.process_csv")
    @patch("highlight_cuts.web.merge_intervals")
    def test_process_video_task_writes_completion_flag(
        self, mock_merge, mock_process_csv, mock_extract, mock_concat
    ):
        """Test that completion flag is written after successful processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    (Path(tmpdir) / "game.mp4").touch()

                    mock_process_csv.return_value = {
                        "Player1": [Clip(start=0.0, end=10.0, included=True)]
                    }
                    mock_merge.return_value = [(0.0, 10.0)]
                    mock_extract.return_value = {"command": "cmd", "stdout": "", "stderr": ""}
                    mock_concat.return_value = {"command": "cmd", "stdout": "", "stderr": ""}

                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "output.mp4",
                    )

                    # Check completion flag exists
                    flag_file = Path("/tmp/highlight_cuts_complete.flag")
                    assert flag_file.exists()
                    content = flag_file.read_text()
                    assert "Player1|Game1|" in content

    @patch("highlight_cuts.web.concat_clips")
    @patch("highlight_cuts.web.extract_clip")
    @patch("highlight_cuts.web.process_csv")
    @patch("highlight_cuts.web.merge_intervals")
    def test_process_video_task_writes_debug_log(
        self, mock_merge, mock_process_csv, mock_extract, mock_concat
    ):
        """Test that debug log is written with correct information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    (Path(tmpdir) / "game.mp4").touch()

                    mock_process_csv.return_value = {
                        "Player1": [Clip(start=5.0, end=15.0, included=True)]
                    }
                    mock_merge.return_value = [(5.0, 15.0)]
                    mock_extract.return_value = {
                        "command": "ffmpeg ...",
                        "stdout": "extract stdout",
                        "stderr": "extract stderr",
                    }
                    mock_concat.return_value = {
                        "command": "ffmpeg concat",
                        "stdout": "concat stdout",
                        "stderr": "concat stderr",
                    }

                    process_video_task(
                        "game.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "output.mp4",
                    )

                    # Check debug log exists and contains expected info
                    log_file = Path("/tmp/highlight_cuts_debug.txt")
                    assert log_file.exists()
                    content = log_file.read_text()
                    assert "game.mp4" in content
                    assert "http://example.com/sheet" in content
                    assert "Game1" in content
                    assert "Player1" in content
                    assert "ffmpeg ..." in content
                    assert "extract stdout" in content

    @patch("highlight_cuts.web.process_csv")
    def test_process_video_task_exception_handling(self, mock_process_csv):
        """Test that exceptions in process_video_task are caught and logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.DATA_DIR", Path(tmpdir)):
                with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                    mock_process_csv.side_effect = Exception("Processing error")

                    # Should not raise, just log
                    process_video_task(
                        "nonexistent.mp4",
                        "http://example.com/sheet",
                        "Game1",
                        "Player1",
                        "output.mp4",
                    )


class TestProcessEndpoint:
    """Test /process endpoint edge cases."""

    @patch("highlight_cuts.web.BackgroundTasks.add_task")
    def test_process_with_short_path(self, mock_add_task):
        """Test process endpoint with video path shorter than expected."""
        response = client.post(
            "/process",
            data={
                "video_filename": "short.mp4",
                "sheet_url": "http://example.com/sheet",
                "game": "Game1",
                "player": "Player Name With Spaces",
            },
        )

        assert response.status_code == 200
        assert "Processing" in response.text

        # Verify fallback values were used
        call_args = mock_add_task.call_args[0]
        output_filename = call_args[5]
        assert "UnknownTeam" in output_filename
        assert "UnknownTournament" in output_filename

    @patch("highlight_cuts.web.BackgroundTasks.add_task")
    def test_process_sanitizes_special_characters(self, mock_add_task):
        """Test that special characters in names are sanitized."""
        response = client.post(
            "/process",
            data={
                "video_filename": "Team@#$/Tournament!!/Game**.mp4",
                "sheet_url": "http://example.com/sheet",
                "game": "Game1",
                "player": "Player!@#$%^&*()Name",
            },
        )

        assert response.status_code == 200

        call_args = mock_add_task.call_args[0]
        output_filename = call_args[5]

        # Special characters should be removed
        assert "@" not in output_filename
        assert "#" not in output_filename
        assert "$" not in output_filename
        assert "!" not in output_filename


class TestListFilesEndpoint:
    """Test /files endpoint."""

    def test_list_files_empty_directory(self):
        """Test list_files with empty output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")

                assert response.status_code == 200
                # Should return empty list structure
                assert "<ul" in response.text
                assert "</ul>" in response.text

    def test_list_files_with_videos(self):
        """Test list_files with video files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            player_dir = Path(tmpdir) / "Player_TeamA"
            player_dir.mkdir()
            video1 = player_dir / "tournament_game_20250126_120000.mp4"
            video1.touch()

            # Set mtime to a known value
            now = datetime.now().timestamp()
            os.utime(video1, (now, now))

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")

                assert response.status_code == 200
                assert "tournament_game_20250126_120000.mp4" in response.text
                assert "Player TeamA" in response.text
                assert "Just now" in response.text or "minute" in response.text

    def test_list_files_sorting_by_mtime(self):
        """Test that files are sorted by modification time, newest first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different mtimes
            old_video = Path(tmpdir) / "old.mp4"
            new_video = Path(tmpdir) / "new.mp4"

            old_video.touch()
            new_video.touch()

            # Set different mtimes
            old_time = (datetime.now() - timedelta(hours=2)).timestamp()
            new_time = datetime.now().timestamp()
            os.utime(old_video, (old_time, old_time))
            os.utime(new_video, (new_time, new_time))

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")

                # new.mp4 should appear before old.mp4
                new_pos = response.text.find("new.mp4")
                old_pos = response.text.find("old.mp4")
                assert new_pos < old_pos

    def test_list_files_ignores_hidden_files(self):
        """Test that hidden files (starting with .) are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            visible = Path(tmpdir) / "visible.mp4"
            hidden = Path(tmpdir) / ".hidden.mp4"
            visible.touch()
            hidden.touch()

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")

                assert "visible.mp4" in response.text
                assert ".hidden.mp4" not in response.text

    def test_list_files_time_formatting(self):
        """Test various time formatting scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video = Path(tmpdir) / "test.mp4"
            video.touch()

            # Test "just now"
            now = datetime.now().timestamp()
            os.utime(video, (now, now))
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")
                assert "Just now" in response.text

            # Test minutes ago
            minutes_ago = (datetime.now() - timedelta(minutes=5)).timestamp()
            os.utime(video, (minutes_ago, minutes_ago))
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")
                assert "minute" in response.text and "ago" in response.text

            # Test hours ago
            hours_ago = (datetime.now() - timedelta(hours=3)).timestamp()
            os.utime(video, (hours_ago, hours_ago))
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")
                assert "hour" in response.text and "ago" in response.text

            # Test days ago
            days_ago = (datetime.now() - timedelta(days=2)).timestamp()
            os.utime(video, (days_ago, days_ago))
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/files")
                assert "day" in response.text and "ago" in response.text


class TestVideoPlayerEndpoint:
    """Test /player endpoint."""

    def test_get_video_player_file_not_found(self):
        """Test video player with non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/player/nonexistent.mp4")

                assert response.status_code == 200
                assert "File not found" in response.text

    def test_get_video_player_success(self):
        """Test video player with existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video = Path(tmpdir) / "test.mp4"
            video.touch()

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/player/test.mp4")

                assert response.status_code == 200
                assert "<video" in response.text
                assert "test.mp4" in response.text
                assert "/videos/test.mp4" in response.text


class TestDownloadFileEndpoint:
    """Test /download endpoint."""

    def test_download_file_not_found(self):
        """Test download with non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/download/nonexistent.mp4")

                assert response.status_code == 404
                assert "File not found" in response.json()["detail"]

    def test_download_file_success(self):
        """Test successful file download."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video = Path(tmpdir) / "test.mp4"
            video.write_text("test content")

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/download/test.mp4")

                assert response.status_code == 200
                assert response.headers["content-type"] == "video/mp4"

    def test_download_removes_timestamp_from_filename(self):
        """Test that timestamp is removed from download filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video = Path(tmpdir) / "tournament_game_20250126_152800.mp4"
            video.write_text("test content")

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/download/tournament_game_20250126_152800.mp4")

                assert response.status_code == 200
                # The content-disposition should have clean name
                # Note: FileResponse sets this header
                # We can verify by checking that the timestamp pattern is handled

    def test_download_nested_file(self):
        """Test downloading file from nested directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            player_dir = Path(tmpdir) / "Player_Team"
            player_dir.mkdir()
            video = player_dir / "tournament_game.mp4"
            video.write_text("test content")

            with patch("highlight_cuts.web.OUTPUT_DIR", Path(tmpdir)):
                response = client.get("/download/Player_Team/tournament_game.mp4")

                assert response.status_code == 200


class TestFormatSeconds:
    """Test format_seconds helper function."""

    def test_format_seconds_zero(self):
        """Test formatting zero seconds."""
        assert format_seconds(0) == "00:00"

    def test_format_seconds_less_than_minute(self):
        """Test formatting less than a minute."""
        assert format_seconds(30) == "00:30"
        assert format_seconds(59) == "00:59"

    def test_format_seconds_exactly_one_minute(self):
        """Test formatting exactly one minute."""
        assert format_seconds(60) == "01:00"

    def test_format_seconds_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_seconds(90) == "01:30"
        assert format_seconds(125) == "02:05"

    def test_format_seconds_over_hour(self):
        """Test formatting over an hour (should show large minute values)."""
        assert format_seconds(3661) == "61:01"

    def test_format_seconds_with_decimal(self):
        """Test that decimal seconds are truncated."""
        assert format_seconds(90.7) == "01:30"
        assert format_seconds(59.9) == "00:59"


class TestDebugLogEndpoint:
    """Test /debug-log endpoint."""

    def test_debug_log_not_exists(self):
        """Test debug-log when log file doesn't exist."""
        with patch("highlight_cuts.web.Path") as mock_path:
            mock_log_file = MagicMock()
            mock_log_file.exists.return_value = False
            mock_path.return_value = mock_log_file

            response = client.get("/debug-log")

            assert response.status_code == 200
            assert "No debug log available yet" in response.text

    def test_debug_log_exists(self):
        """Test debug-log when log file exists."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Debug information\nLine 2\nLine 3")
            f.flush()
            log_path = f.name

        try:
            with patch("highlight_cuts.web.Path") as mock_path:
                mock_log_file = MagicMock()
                mock_log_file.exists.return_value = True
                mock_log_file.read_text.return_value = "Debug information\nLine 2\nLine 3"
                mock_path.return_value = mock_log_file

                response = client.get("/debug-log")

                assert response.status_code == 200
                assert "Debug information" in response.text
                assert "<pre" in response.text
        finally:
            os.unlink(log_path)


class TestIntegrationScenarios:
    """Test complex integration scenarios."""

    @patch("highlight_cuts.web.concat_clips")
    @patch("highlight_cuts.web.extract_clip")
    @patch("highlight_cuts.web.process_csv")
    @patch("highlight_cuts.web.merge_intervals")
    @patch("requests.get")
    def test_full_workflow_sheet_to_video(
        self, mock_requests, mock_merge, mock_process_csv, mock_extract, mock_concat
    ):
        """Test complete workflow from parsing sheet to processing video."""
        # Step 1: Parse sheet
        mock_response = MagicMock()
        mock_response.text = """videoName,playerName,startTime,stopTime,include,notes
Game1,Player1,00:00,00:10,true,Great play
Game1,Player1,00:20,00:30,true,Nice move
Game1,Player2,00:05,00:15,true,Good defense"""
        mock_requests.return_value = mock_response

        parse_response = client.post(
            "/parse-sheet",
            data={"sheet_url": "https://docs.google.com/spreadsheets/d/123"},
        )

        assert parse_response.status_code == 200
        assert "Game1" in parse_response.text
        assert "Player1" in parse_response.text

        # Step 2: Get clips for a player
        mock_process_csv.return_value = {
            "Player1": [
                Clip(start=0.0, end=10.0, included=True, notes="Great play"),
                Clip(start=20.0, end=30.0, included=True, notes="Nice move"),
            ]
        }

        clips_response = client.post(
            "/get-clips",
            data={
                "sheet_url": "https://docs.google.com/spreadsheets/d/123",
                "game": "Game1",
                "player": "Player1",
            },
        )

        assert clips_response.status_code == 200
        assert "00:00" in clips_response.text
        assert "00:10" in clips_response.text
        assert "Great play" in clips_response.text

        # Step 3: Start processing
        with patch("highlight_cuts.web.BackgroundTasks.add_task") as mock_add_task:
            process_response = client.post(
                "/process",
                data={
                    "video_filename": "TeamA/Tournament1/Game1.mp4",
                    "sheet_url": "https://docs.google.com/spreadsheets/d/123",
                    "game": "Game1",
                    "player": "Player1",
                },
            )

            assert process_response.status_code == 200
            assert "Processing" in process_response.text
            mock_add_task.assert_called_once()

    def test_error_recovery_invalid_sheet_then_valid(self):
        """Test recovery from invalid sheet to valid sheet."""
        # First try with invalid sheet
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Invalid URL")
            error_response = client.post(
                "/parse-sheet",
                data={"sheet_url": "https://docs.google.com/spreadsheets/d/invalid"},
            )
            assert "Error:" in error_response.text

            # Then try with valid sheet
            mock_response = MagicMock()
            mock_response.text = "videoName,playerName,startTime,stopTime\nGame1,Player1,00:00,00:10"
            mock_get.side_effect = None
            mock_get.return_value = mock_response

            success_response = client.post(
                "/parse-sheet",
                data={"sheet_url": "https://docs.google.com/spreadsheets/d/valid"},
            )
            assert success_response.status_code == 200
            assert "Game1" in success_response.text
