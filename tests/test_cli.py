import pytest
from click.testing import CliRunner
from unittest.mock import patch
from highlight_cuts.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@patch("highlight_cuts.cli.process_csv")
def test_cli_csv_error(mock_process, runner):
    mock_process.side_effect = Exception("CSV Error")
    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("v")
        with open("data.csv", "w") as f:
            f.write("c")
        result = runner.invoke(
            main, ["--input-video", "vid.mp4", "--csv-file", "data.csv", "--game", "G1"]
        )
        assert result.exit_code != 0
        # Click might print the exception or just abort.
        # Since we raise click.Abort(), exit code should be 1.


@patch("highlight_cuts.cli.process_csv")
def test_cli_no_clips(mock_process, runner, caplog):
    mock_process.return_value = {}
    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("v")
        with open("data.csv", "w") as f:
            f.write("c")
        result = runner.invoke(
            main, ["--input-video", "vid.mp4", "--csv-file", "data.csv", "--game", "G1"]
        )
        assert result.exit_code == 0
        assert "No clips found" in caplog.text


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
def test_cli_dry_run(mock_merge, mock_process, runner, caplog):
    import logging

    caplog.set_level(logging.INFO)
    mock_process.return_value = {"Player1": [(0, 10)]}
    mock_merge.return_value = [(0, 10)]

    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("v")
        with open("data.csv", "w") as f:
            f.write("c")
        result = runner.invoke(
            main,
            [
                "--input-video",
                "vid.mp4",
                "--csv-file",
                "data.csv",
                "--game",
                "G1",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Player: Player1" in caplog.text
        assert "Clip 1: 0.00s - 10.00s" in result.output


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
@patch("highlight_cuts.cli.extract_clip")
@patch("highlight_cuts.cli.concat_clips")
def test_cli_success(mock_concat, mock_extract, mock_merge, mock_process, runner):
    mock_process.return_value = {"Player1": [(0, 10)]}
    mock_merge.return_value = [(0, 10)]

    with runner.isolated_filesystem():
        # Create dummy input files
        with open("vid.mp4", "w") as f:
            f.write("video")
        with open("data.csv", "w") as f:
            f.write("csv")

        result = runner.invoke(
            main, ["--input-video", "vid.mp4", "--csv-file", "data.csv", "--game", "G1"]
        )

        assert result.exit_code == 0
        mock_extract.assert_called()
        mock_concat.assert_called()


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
@patch("highlight_cuts.cli.extract_clip")
def test_cli_extraction_error(mock_extract, mock_merge, mock_process, runner):
    mock_process.return_value = {"Player1": [(0, 10)]}
    mock_merge.return_value = [(0, 10)]
    mock_extract.side_effect = Exception("Extract Error")

    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("video")
        with open("data.csv", "w") as f:
            f.write("csv")

        result = runner.invoke(
            main, ["--input-video", "vid.mp4", "--csv-file", "data.csv", "--game", "G1"]
        )

        assert result.exit_code != 0
