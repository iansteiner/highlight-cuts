from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from highlight_cuts.web import app
from highlight_cuts.core import Clip

client = TestClient(app)


@patch("highlight_cuts.web.get_video_structure")
def test_read_root(mock_get_structure):
    mock_get_structure.return_value = {
        "TeamA": {"Tourney1": [{"name": "Game1", "path": "TeamA/Tourney1/Game1.mp4"}]}
    }
    response = client.get("/")
    assert response.status_code == 200
    assert "Highlight Cuts" in response.text
    assert "Video Selection" in response.text
    assert "TeamA" in response.text


@patch("highlight_cuts.web.process_csv")
@patch("requests.get")
def test_parse_sheet(mock_get, mock_process_csv):
    # Mock requests.get to return a CSV string
    mock_response = MagicMock()
    mock_response.text = (
        "videoName,playerName,startTime,stopTime,notes\nGame1,Player1,00:00,00:10,note"
    )
    mock_get.return_value = mock_response

    response = client.post(
        "/parse-sheet", data={"sheet_url": "https://docs.google.com/spreadsheets/d/123"}
    )

    assert response.status_code == 200
    assert "Game1" in response.text
    assert "Player1" in response.text
    assert "Select Game & Player" in response.text
    assert "onclick=\"selectSelection(this, 'Game1', 'Player1')\"" in response.text


@patch("highlight_cuts.web.process_csv")
@patch("highlight_cuts.web.extract_clip")
@patch("highlight_cuts.web.concat_clips")
@patch("highlight_cuts.web.BackgroundTasks.add_task")
def test_process_endpoint(mock_add_task, mock_concat, mock_extract, mock_process):
    # Mock return value with Clip objects
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
    mock_extract.return_value = {"command": "cmd", "stdout": "", "stderr": ""}
    mock_concat.return_value = {"command": "cmd", "stdout": "", "stderr": ""}

    response = client.post(
        "/process",
        data={
            "video_filename": "TeamA/Tourney1/Game1.mp4",
            "sheet_url": "http://example.com/sheet",
            "game": "Game1",
            "player": "Player1",
            "padding": "0.0",
        },
    )

    assert response.status_code == 200
    assert "Processing" in response.text
    # Check that the response includes the status polling trigger
    assert 'hx-get="/status-check"' in response.text
    assert 'hx-trigger="load"' in response.text

    # Verify that add_task was called with correct arguments
    # This test would have caught the missing 'game' parameter bug
    mock_add_task.assert_called_once()
    call_args = mock_add_task.call_args
    assert call_args[0][0].__name__ == "process_video_task"
    # Verify all 5 required arguments are passed: video_filename, sheet_url, game, player, output_filename
    assert len(call_args[0]) == 6  # function + 5 args
    assert call_args[0][1] == "TeamA/Tourney1/Game1.mp4"  # video_filename
    assert call_args[0][2] == "http://example.com/sheet"  # sheet_url
    assert call_args[0][3] == "Game1"  # game
    assert call_args[0][4] == "Player1"  # player
    assert (
        "Player1_TeamA/Tourney1_Game1_" in call_args[0][5]
    )  # output_filename with timestamp


@patch("highlight_cuts.web.Path")
def test_status_check_processing(mock_path):
    """Test status-check endpoint when processing is still ongoing"""
    # Mock completion file doesn't exist
    mock_completion_file = MagicMock()
    mock_completion_file.exists.return_value = False
    mock_path.return_value = mock_completion_file

    response = client.get("/status-check")

    assert response.status_code == 200
    assert "Processing highlights..." in response.text
    # Should have polling trigger to keep checking
    assert 'hx-get="/status-check"' in response.text
    assert 'hx-trigger="load delay:2s"' in response.text


@patch("highlight_cuts.web.Path")
def test_status_check_complete(mock_path):
    """Test status-check endpoint when processing is complete"""
    # Mock completion file exists and has content
    mock_completion_file = MagicMock()
    mock_completion_file.exists.return_value = True
    mock_completion_file.read_text.return_value = (
        "Clara|Game1|2025-11-26T23:05:57.200039"
    )
    mock_path.return_value = mock_completion_file

    response = client.get("/status-check")

    assert response.status_code == 200
    assert "Done!" in response.text
    assert "Clara" in response.text
    # Should NOT have polling trigger (processing complete)
    assert 'hx-trigger="load delay:2s"' not in response.text
    # Verify completion file was deleted
    mock_completion_file.unlink.assert_called_once()


@patch("highlight_cuts.web.read_cache")
def test_cached_sheets_endpoint_empty(mock_read_cache):
    """Test /cached-sheets endpoint with no cached entries."""
    mock_read_cache.return_value = []

    response = client.get("/cached-sheets")

    assert response.status_code == 200
    assert response.json() == []


@patch("highlight_cuts.web.read_cache")
def test_cached_sheets_endpoint_with_entries(mock_read_cache):
    """Test /cached-sheets endpoint with cached entries."""
    mock_read_cache.return_value = [
        {
            "timestamp": 1234567890,
            "sheet_id": "sheet1",
            "gid": "0",
            "original_url": "https://docs.google.com/spreadsheets/d/sheet1/edit",
            "sheet_name": "Game 1",
        },
        {
            "timestamp": 1234567891,
            "sheet_id": "sheet2",
            "gid": "5",
            "original_url": "https://docs.google.com/spreadsheets/d/sheet2/edit#gid=5",
            "sheet_name": "Game 2",
        },
    ]

    response = client.get("/cached-sheets")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["url"] == "https://docs.google.com/spreadsheets/d/sheet1/edit"
    assert data[0]["name"] == "Game 1"
    assert data[0]["sheet_id"] == "sheet1"
    assert data[0]["gid"] == "0"


@patch("highlight_cuts.web.get_video_structure")
@patch("highlight_cuts.web.read_cache")
def test_root_with_cached_sheets(mock_read_cache, mock_get_structure):
    """Test that root page includes cached sheets in template context."""
    mock_get_structure.return_value = {}
    mock_read_cache.return_value = [
        {
            "timestamp": 1234567890,
            "sheet_id": "test",
            "gid": "0",
            "original_url": "https://docs.google.com/spreadsheets/d/test/edit",
            "sheet_name": "Test Game",
        }
    ]

    response = client.get("/")

    assert response.status_code == 200
    # Check that datalist is present
    assert 'id="cached-sheets"' in response.text
    # Check that option is present
    assert "Test Game" in response.text
    assert "https://docs.google.com/spreadsheets/d/test/edit" in response.text


@patch("highlight_cuts.web.append_to_cache")
@patch("requests.get")
def test_parse_sheet_updates_cache(mock_requests_get, mock_append_cache):
    """Test that parse_sheet adds to cache after successful parse."""
    # Mock the CSV response
    mock_response = MagicMock()
    mock_response.text = (
        "videoName,playerName,startTime,stopTime,notes\nGame1,Player1,00:00,00:10,note"
    )
    mock_requests_get.return_value = mock_response

    response = client.post(
        "/parse-sheet",
        data={"sheet_url": "https://docs.google.com/spreadsheets/d/test123/edit"},
    )

    assert response.status_code == 200
    # Verify append_to_cache was called with None for auto-title fetch
    mock_append_cache.assert_called_once()
    call_args = mock_append_cache.call_args
    assert call_args[0][1] == "https://docs.google.com/spreadsheets/d/test123/edit"
    assert call_args[1]["sheet_name"] is None  # Should auto-fetch
