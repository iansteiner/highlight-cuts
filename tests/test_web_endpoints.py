from fastapi.testclient import TestClient
from highlight_cuts.web import app
from unittest.mock import patch

client = TestClient(app)

@patch("highlight_cuts.web.process_csv")
def test_get_clips_success(mock_process_csv):
    # Mock the process_csv return value
    mock_process_csv.return_value = {
        "Player1": [(10.0, 20.0), (30.0, 40.0)]
    }

    response = client.post(
        "/get-clips",
        data={
            "sheet_url": "http://example.com/sheet",
            "game": "Game1",
            "player": "Player1"
        }
    )

    assert response.status_code == 200
    assert "Player1" not in response.text  # The player name isn't in the table, but the clips are
    assert "10.00s" in response.text
    assert "20.00s" in response.text
    assert "10.00s" in response.text # Duration

@patch("highlight_cuts.web.process_csv")
def test_get_clips_no_player(mock_process_csv):
    mock_process_csv.return_value = {
        "Player1": [(10.0, 20.0)]
    }

    response = client.post(
        "/get-clips",
        data={
            "sheet_url": "http://example.com/sheet",
            "game": "Game1",
            "player": "Player2"
        }
    )

    assert response.status_code == 200
    assert "No clips found for player Player2" in response.text

@patch("highlight_cuts.web.process_csv")
def test_get_clips_error(mock_process_csv):
    mock_process_csv.side_effect = Exception("CSV Error")

    response = client.post(
        "/get-clips",
        data={
            "sheet_url": "http://example.com/sheet",
            "game": "Game1",
            "player": "Player1"
        }
    )

    assert response.status_code == 200
    assert "Error loading clips: CSV Error" in response.text
