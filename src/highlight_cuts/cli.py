import click
import logging
import os
import tempfile
from pathlib import Path
from .core import process_csv, merge_intervals
from .ffmpeg import extract_clip, concat_clips

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--input-video",
    required=True,
    type=click.Path(exists=True),
    help="Path to the source video file.",
)
@click.option(
    "--csv-file",
    required=True,
    type=str,
    help="Path to CSV file or Google Sheets URL (must be publicly shared).",
)
@click.option(
    "--game", required=True, help="Name of the game/video in the CSV to process."
)
@click.option(
    "--padding", default=0.0, help="Seconds to add to the start and end of each clip."
)
@click.option(
    "--output-dir",
    default=".",
    type=click.Path(),
    help="Directory where output videos will be saved. Defaults to current directory.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be generated without running FFmpeg.",
)
def main(input_video, csv_file, game, padding, output_dir, dry_run):
    """
    Slices a sports game video into player highlights based on a CSV of timestamps.
    """
    logger.info(f"Starting highlight generation for game: {game}")

    try:
        player_clips = process_csv(csv_file, game)
    except Exception as e:
        logger.error(f"Failed to process CSV: {e}")
        raise click.Abort()

    if not player_clips:
        logger.warning("No clips found for the specified game.")
        return

    input_path = Path(input_video)
    video_stem = input_path.stem
    video_suffix = input_path.suffix

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_path.absolute()}")

    for player, intervals in player_clips.items():
        merged = merge_intervals(intervals, padding)
        total_duration = sum(end - start for start, end in merged)
        clip_count = len(merged)

        logger.info(
            f"Player: {player} | Clips: {clip_count} | Total Duration: {total_duration:.2f}s"
        )

        if dry_run:
            for i, (start, end) in enumerate(merged):
                print(
                    f"  Clip {i + 1}: {start:.2f}s - {end:.2f}s (Duration: {end - start:.2f}s)"
                )
            continue

        # Create temporary directory for this player's clips
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_clips = []
            logger.info(f"Generating clips for {player}...")

            for i, (start, end) in enumerate(merged):
                clip_name = f"clip_{i:03d}{video_suffix}"
                clip_path = os.path.join(temp_dir, clip_name)
                try:
                    extract_clip(str(input_path), start, end, clip_path)
                    temp_clips.append(clip_path)
                except Exception as e:
                    logger.error(f"Failed to extract clip {i} for {player}: {e}")
                    # Continue or abort? Let's abort for now to avoid partial videos
                    raise click.Abort()

            # Output filename: original_name_PlayerName.ext (Wait, user asked for: remove suffix, add player name, add suffix back)
            # Actually user said: "take the original filename. remove the suffix. add the playerName. add the suffix back on to the end."
            # Example: game1.mp4 -> game1_PlayerName.mp4
            # I should probably sanitize the player name to be safe for filenames
            safe_player_name = (
                "".join(c for c in player if c.isalnum() or c in (" ", "_", "-"))
                .strip()
                .replace(" ", "_")
            )
            output_filename = f"{video_stem}_{safe_player_name}{video_suffix}"
            output_file_path = os.path.join(output_dir, output_filename)

            logger.info(f"Concatenating clips into {output_file_path}...")
            try:
                concat_clips(temp_clips, output_file_path)
                logger.info(f"Successfully created {output_file_path}")
            except Exception as e:
                logger.error(f"Failed to create final video for {player}: {e}")


if __name__ == "__main__":
    main()
