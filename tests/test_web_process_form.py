"""Test the /process endpoint form submission."""

from fastapi.testclient import TestClient
from highlight_cuts.web import app
from unittest.mock import patch

client = TestClient(app)


@patch("highlight_cuts.web.BackgroundTasks.add_task")
def test_process_form_submission_with_all_fields(mock_add_task):
    """Test that /process endpoint accepts all required form fields."""
    response = client.post(
        "/process",
        data={
            "video_filename": "TeamA/Tournament1/Game1.mp4",
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit",
            "game": "Game1",
            "player": "Player1",
        },
    )

    assert response.status_code == 200
    assert "Processing highlights" in response.text
    assert 'hx-get="/status-check"' in response.text

    # Verify background task was added
    mock_add_task.assert_called_once()


@patch("highlight_cuts.web.BackgroundTasks.add_task")
def test_process_form_missing_game(mock_add_task):
    """Test that /process endpoint rejects missing game."""
    response = client.post(
        "/process",
        data={
            "video_filename": "TeamA/Tournament1/Game1.mp4",
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit",
            "game": "",  # Empty game
            "player": "Player1",
        },
    )

    assert response.status_code == 200
    assert "Error: No game selected" in response.text

    # Should NOT call background task
    mock_add_task.assert_not_called()


@patch("highlight_cuts.web.BackgroundTasks.add_task")
def test_process_form_missing_player(mock_add_task):
    """Test that /process endpoint rejects missing player."""
    response = client.post(
        "/process",
        data={
            "video_filename": "TeamA/Tournament1/Game1.mp4",
            "sheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit",
            "game": "Game1",
            "player": "",  # Empty player
        },
    )

    assert response.status_code == 200
    assert "Error: No player selected" in response.text

    # Should NOT call background task
    mock_add_task.assert_not_called()


def test_process_form_missing_all_fields():
    """Test that /process endpoint handles completely missing form fields."""
    # FastAPI will return 422 for missing required fields
    response = client.post("/process", data={})

    assert response.status_code == 422  # Unprocessable Entity
