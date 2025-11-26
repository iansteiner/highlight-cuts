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
    # Check for new output filename format: player_team/tournament_game.mp4
    # Player1, TeamA -> Player1_TeamA directory
    # Tourney1, Game1 -> Tourney1_Game1.mp4 filename
    assert "Player1_TeamA/Tourney1_Game1.mp4" in response.text
