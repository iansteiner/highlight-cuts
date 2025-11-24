# Highlight Cuts Usage Guide

`highlight-cuts` is a command-line tool to slice sports game videos into player highlights using FFmpeg.

## Installation

### Prerequisites

1. **Python 3.13+**
   
   Check your version:
   ```bash
   python --version
   ```
   
   If you need to install or upgrade:
   - **macOS**: `brew install python@3.13`
   - **Ubuntu/Debian**: `sudo apt install python3.13`
   - **Windows**: [Download from python.org](https://www.python.org/downloads/)

2. **FFmpeg**
   
   Verify FFmpeg is installed:
   ```bash
   ffmpeg -version
   ```
   
   If not installed:
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Windows**: [Download from ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

3. **uv (recommended)**
   
   Fast Python package manager:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Install Highlight Cuts

```bash
# Clone the repository
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts

# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Usage

The basic command structure is:

```bash
uv run highlight-cuts --input-video <VIDEO_PATH> --csv-file <CSV_PATH> --game <GAME_NAME> [OPTIONS]
```

### Arguments

- `--input-video`: Path to the source video file (e.g., `game_footage.mp4`).
- `--csv-file`: Path to a local CSV file **or** a Google Sheets URL (see [Google Sheets Guide](google_sheets.md)).
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

**Use a Google Sheets URL instead of a local CSV:**
```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing" \
  --game Game1
```

See the [Google Sheets Guide](google_sheets.md) for setup instructions.

## Common Workflows

### First-Time Setup

```bash
# 1. Verify prerequisites
python --version  # Should be 3.13+
ffmpeg -version   # Should show FFmpeg version

# 2. Install the tool
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts
uv sync

# 3. Test with dry run
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run

# 4. Generate highlights
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1
```

### Weekly Game Processing

```bash
# Process each week's game with consistent settings
uv run highlight-cuts \
  --input-video "Week1_Game.mp4" \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" \
  --game "Week1" \
  --padding 2.0 \
  --output-dir ~/highlights/week1

uv run highlight-cuts \
  --input-video "Week2_Game.mp4" \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" \
  --game "Week2" \
  --padding 2.0 \
  --output-dir ~/highlights/week2
```

### Testing New CSV Data

```bash
# 1. Always dry-run first to verify data
uv run highlight-cuts --input-video game.mp4 --csv-file new_clips.csv --game Game1 --dry-run

# 2. Review the output - check player names and clip counts

# 3. If everything looks good, run for real
uv run highlight-cuts --input-video game.mp4 --csv-file new_clips.csv --game Game1
```

### Collaborative Workflow with Google Sheets

```bash
# 1. Create Google Sheet with team
# 2. Share with "Anyone with the link" (Viewer)
# 3. Team members add timestamps during/after game
# 4. Coach runs the tool with the sheet URL
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_ID/edit?usp=sharing" \
  --game "Game1" \
  --padding 2.0 \
  --output-dir ~/team_highlights

# 5. Share generated videos with team
```

### Converting Unsupported Video Formats

```bash
# If your video format isn't supported, convert to MP4 first
ffmpeg -i input.avi -c:v libx264 -c:a aac -preset fast output.mp4

# Then use the converted video
uv run highlight-cuts --input-video output.mp4 --csv-file clips.csv --game Game1
```

## Tips & Best Practices

### Padding Recommendations

- **No padding** (`--padding 0.0`): Use when timestamps are very precise
- **2 seconds** (`--padding 2.0`): **Recommended default** - provides good buffer
- **5 seconds** (`--padding 5.0`): Use for context-heavy sports (basketball, soccer)

### CSV Organization

**Single game per CSV**:
```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,Alice
Game1,00:05:10,00:05:20,Bob
```

**Multiple games in one CSV** (recommended for season tracking):
```csv
videoName,startTime,stopTime,playerName
Week1,00:01:30,00:01:40,Alice
Week1,00:05:10,00:05:20,Bob
Week2,00:02:00,00:02:15,Alice
Week2,00:03:00,00:03:10,Bob
```

### Performance Tips

- Use SSD for output directory (faster than HDD)
- Avoid network drives for output
- Process one game at a time for large videos
- Use `--dry-run` to verify before processing

### Quality Tips

- Use high-quality source videos (1080p recommended)
- Ensure source video uses H.264 codec for best compatibility
- Add padding to compensate for keyframe snapping
- Review dry-run output to verify clip timing

## Next Steps

- Check the [FAQ](FAQ.md) for common questions
- See [Troubleshooting](TROUBLESHOOTING.md) if you encounter issues
- Read [Architecture](architecture.md) to understand how it works

