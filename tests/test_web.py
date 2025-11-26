from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from highlight_cuts.web import app
from highlight_cuts.core import Clip

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Highlight Cuts" in response.text
    assert "Video File" in response.text


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
    assert "<option value='Game1'>Game1</option>" in response.text


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
            "video_filename": "test.mp4",
            "sheet_url": "http://example.com/sheet",
            "game": "Game1",
            "player": "Player1",
            "padding": "0.0",
        },
    )

    assert response.status_code == 200
    assert "Processing" in response.text
    assert "test.mp4" in response.text
