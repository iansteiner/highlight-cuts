import subprocess
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def extract_clip(input_path: str, start: float, end: float, output_path: str) -> dict:
    """
    Extracts a clip from the input video using stream copy.

    Args:
        input_path: Path to source video.
        start: Start time in seconds.
        end: End time in seconds.
        output_path: Path to save the clip.
    """
    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        input_path,
        "-t",
        f"{duration:.3f}",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "1",
        output_path,
    ]

    logger.debug(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        return {
            "command": " ".join(cmd),
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr.decode()}")
        raise


def concat_clips(clip_paths: List[str], output_path: str) -> dict:
    """
    Concatenates multiple clips into a single video file.

    Args:
        clip_paths: List of paths to clip files.
        output_path: Path to save the final video.
    """
    if not clip_paths:
        return

    # Create a temporary file list for ffmpeg concat demuxer
    list_file = output_path + ".txt"
    with open(list_file, "w") as f:
        for path in clip_paths:
            abs_path = os.path.abspath(path)
            f.write(f"file '{abs_path}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        output_path,
    ]

    logger.debug(f"Running concat command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        return {
            "command": " ".join(cmd),
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg concat failed: {e.stderr.decode()}")
        raise
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)


def generate_hls(
    input_path: str, output_dir: str, segment_time: float = 6.0, reencode: bool = False
) -> dict:
    """
    Generates HLS playlist and segments for the given input.

    Args:
        input_path: Path to the MP4 to segment.
        output_dir: Directory to write playlist and segments.
        segment_time: Target segment duration in seconds.
        reencode: If True, re-encode video for cleaner GOP/keyframes.
    """
    os.makedirs(output_dir, exist_ok=True)
    playlist_path = os.path.join(output_dir, "playlist.m3u8")
    segment_pattern = os.path.join(output_dir, "segment_%03d.ts")

    if reencode:
        video_codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    else:
        video_codec = ["-codec", "copy"]

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        *video_codec,
        "-start_number",
        "0",
        "-hls_time",
        f"{segment_time}",
        "-hls_playlist_type",
        "vod",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        segment_pattern,
        playlist_path,
    ]

    logger.debug(f"Running HLS command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        return {
            "command": " ".join(cmd),
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg HLS generation failed: {e.stderr.decode()}")
        raise
