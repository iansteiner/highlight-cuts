# Highlight Cuts Usage Guide

`highlight-cuts` is a command-line tool to slice sports game videos into player highlights using FFmpeg.

## Installation

Ensure you have Python 3.13+ and `ffmpeg` installed on your system.

```bash
# Install using uv (recommended)
uv sync
```

## Usage

The basic command structure is:

```bash
uv run highlight-cuts --input-video <VIDEO_PATH> --csv-file <CSV_PATH> --game <GAME_NAME> [OPTIONS]
```

### Arguments

- `--input-video`: Path to the source video file (e.g., `game_footage.mp4`).
- `--csv-file`: Path to the CSV file containing timestamps.
- `--game`: The name of the game/video to filter for in the CSV.

### Options

- `--padding <FLOAT>`: Seconds to add to the start and end of each clip (default: 0.0).
- `--output-dir <PATH>`: Directory where output videos will be saved (default: current directory).
- `--dry-run`: Print the planned clips and total duration without running FFmpeg.
- `--help`: Show the help message.

### CSV Format

The CSV file must contain the following columns:
- `videoName`: Identifier for the game (matches `--game` argument).
- `startTime`: Start time of the clip (HH:MM:SS or MM:SS).
- `stopTime`: End time of the clip (HH:MM:SS or MM:SS).
- `playerName`: Name of the player for this clip.

**Example CSV:**
```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,John Doe
Game1,00:05:10,00:05:20,John Doe
Game1,00:02:00,00:02:15,Jane Smith
Game2,00:10:00,00:10:15,John Doe
```

### Output

The tool generates a video file for each player found in the CSV for the specified game.
The output filename format is: `{OriginalVideoName}_{PlayerName}.{Extension}`.

Files are saved to the current directory by default, or to the directory specified with `--output-dir`.

Example: `game_footage_John_Doe.mp4`

## Examples

**Dry run to see what will be generated:**
```bash
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run
```

**Generate clips with 2 seconds of padding:**
```bash
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --padding 2.0
```

**Save clips to a specific directory:**
```bash
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --output-dir highlights
```
