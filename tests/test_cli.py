import pytest
from click.testing import CliRunner
from unittest.mock import patch
from highlight_cuts.cli import main
from highlight_cuts.core import Clip


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
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
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
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
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
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
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


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
@patch("highlight_cuts.cli.extract_clip")
@patch("highlight_cuts.cli.concat_clips")
def test_cli_output_dir(mock_concat, mock_extract, mock_merge, mock_process, runner):
    """Test that --output-dir creates files in the specified directory."""
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
    mock_merge.return_value = [(0, 10)]

    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("video")
        with open("data.csv", "w") as f:
            f.write("csv")

        result = runner.invoke(
            main,
            [
                "--input-video",
                "vid.mp4",
                "--csv-file",
                "data.csv",
                "--game",
                "G1",
                "--output-dir",
                "output",
            ],
        )

        assert result.exit_code == 0
        # Verify concat_clips was called with the output directory path
        call_args = mock_concat.call_args
        assert call_args is not None
        output_path = call_args[0][1]  # Second argument to concat_clips
        assert output_path.startswith("output/") or output_path.startswith("output\\")


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
@patch("highlight_cuts.cli.extract_clip")
@patch("highlight_cuts.cli.concat_clips")
def test_cli_output_dir_created(
    mock_concat, mock_extract, mock_merge, mock_process, runner
):
    """Test that --output-dir creates the directory if it doesn't exist."""
    import os

    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
    mock_merge.return_value = [(0, 10)]

    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("video")
        with open("data.csv", "w") as f:
            f.write("csv")

        # Verify directory doesn't exist before
        assert not os.path.exists("new_output_dir")

        result = runner.invoke(
            main,
            [
                "--input-video",
                "vid.mp4",
                "--csv-file",
                "data.csv",
                "--game",
                "G1",
                "--output-dir",
                "new_output_dir",
            ],
        )

        assert result.exit_code == 0
        # Verify directory was created
        assert os.path.exists("new_output_dir")
        assert os.path.isdir("new_output_dir")


@patch("highlight_cuts.cli.process_csv")
@patch("highlight_cuts.cli.merge_intervals")
@patch("highlight_cuts.cli.extract_clip")
@patch("highlight_cuts.cli.concat_clips")
def test_cli_default_output_dir(
    mock_concat, mock_extract, mock_merge, mock_process, runner
):
    """Test that without --output-dir, files are created in current directory."""
    mock_process.return_value = {"Player1": [Clip(start=0.0, end=10.0, included=True)]}
    mock_merge.return_value = [(0, 10)]

    with runner.isolated_filesystem():
        with open("vid.mp4", "w") as f:
            f.write("video")
        with open("data.csv", "w") as f:
            f.write("csv")

        result = runner.invoke(
            main, ["--input-video", "vid.mp4", "--csv-file", "data.csv", "--game", "G1"]
        )

        assert result.exit_code == 0
        # Verify concat_clips was called with current directory path
        call_args = mock_concat.call_args
        assert call_args is not None
        output_path = call_args[0][1]
        # Should be in current directory (starts with ./ or just filename)
        assert not output_path.startswith("/") or output_path.startswith("./")
