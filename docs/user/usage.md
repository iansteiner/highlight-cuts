# CLI Usage Guide

This guide covers using `highlight-cuts` from the command line for more control and automation.

> **New to Highlight Cuts?** Try the [Quick Start Guide](quickstart.md) with Docker first.

## Installation

### Prerequisites

You'll need:

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

3. **uv** (recommended)

   Fast Python package manager:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Install Highlight Cuts

```bash
# Clone the repository
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts

# Install dependencies
uv sync
```

## Basic Usage

The basic command structure:

```bash
uv run highlight-cuts --input-video <VIDEO_PATH> --csv-file <CSV_PATH> --game <GAME_NAME>
```

### Example

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1
```

This creates one video file per player with all their highlights merged together.

## CSV Format

Your CSV must have these columns:

```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,Alice
Game1,00:05:10,00:05:20,Alice
Game1,00:02:00,00:02:15,Bob
```

**Column details**:
- `videoName`: Game identifier (matches `--game` argument)
- `startTime`: Clip start time (`HH:MM:SS` or `MM:SS`)
- `stopTime`: Clip end time (`HH:MM:SS` or `MM:SS`)
- `playerName`: Player's name

See [Google Sheets Guide](google_sheets.md) to use Google Sheets instead of CSV files.

## Options

### Padding

Add time before and after each clip:

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1 \
  --padding 2.0
```

**Recommended**: Use `--padding 2.0` (2 seconds) to ensure important moments aren't cut off.

### Output Directory

Specify where to save generated videos:

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1 \
  --output-dir ~/highlights
```

Default: Current directory

### Dry Run

Preview what will be generated without actually processing:

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1 \
  --dry-run
```

**Always run this first** to verify your CSV data is correct!

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
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1 \
  --dry-run

# 4. Generate highlights
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file clips.csv \
  --game Game1
```

### Weekly Game Processing

Process each week's game with consistent settings:

```bash
uv run highlight-cuts \
  --input-video "Week1_Game.mp4" \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" \
  --game "Week1" \
  --padding 2.0 \
  --output-dir ~/highlights/week1
```

### Using Google Sheets

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing" \
  --game Game1
```

The tool automatically downloads and processes Google Sheets URLs. See [Google Sheets Guide](google_sheets.md) for setup.

### Testing New CSV Data

```bash
# 1. Always dry-run first
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file new_clips.csv \
  --game Game1 \
  --dry-run

# 2. Review the output - check player names and clip counts

# 3. If everything looks good, run for real
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file new_clips.csv \
  --game Game1
```

## Output

### File Naming

Generated files follow this pattern:

```
{OriginalVideoName}_{PlayerName}.{Extension}
```

**Example**:
- Input video: `game_footage.mp4`
- Player: `John Doe`
- Output: `game_footage_John_Doe.mp4`

### What Gets Created

**One video per player** containing all their clips merged together.

**Example**:
If your CSV has clips for Alice (3 clips) and Bob (2 clips), you'll get:
- `game_footage_Alice.mp4` (all 3 clips merged)
- `game_footage_Bob.mp4` (both clips merged)

Overlapping clips are automatically merged into continuous sequences.

## Tips & Best Practices

### Padding Recommendations

- **No padding** (`--padding 0.0`): When timestamps are very precise
- **2 seconds** (`--padding 2.0`): **Recommended default** - good buffer
- **5 seconds** (`--padding 5.0`): For context-heavy sports (basketball, soccer)

### Performance Tips

- Use SSD for output directory (faster than HDD)
- Avoid network drives for output
- Process one game at a time for large videos
- Always use `--dry-run` to verify before processing

### Quality Tips

- Use high-quality source videos (1080p recommended)
- Ensure source video uses H.264 codec for best compatibility
- Add padding to compensate for keyframe snapping
- Review dry-run output to verify clip timing

## Understanding Keyframe Snapping

Highlight Cuts uses **stream copying** for speed, which means clips snap to the nearest keyframe in the video.

**Result**: Clips may start/end 1-2 seconds earlier/later than requested.

**Why?** Stream copying is 100x faster than re-encoding and preserves 100% quality.

**Solution**: Use `--padding` to add buffer time.

See [Background & Design](../dev/background.md#keyframe-snapping) for technical details.

## Next Steps

- Check the [FAQ](faq.md) for common questions
- See [Troubleshooting](troubleshooting.md) if you encounter issues
- Learn about [Google Sheets integration](google_sheets.md)
- For developers: Read the [Architecture Guide](../dev/architecture.md)

## Command Reference

```
uv run highlight-cuts [OPTIONS]

Options:
  --input-video PATH      Path to source video file [required]
  --csv-file PATH         Path to CSV file or Google Sheets URL [required]
  --game TEXT             Game name to filter in CSV [required]
  --padding FLOAT         Seconds to add before/after clips [default: 0.0]
  --output-dir PATH       Output directory [default: current directory]
  --dry-run               Preview clips without processing
  --help                  Show help message
```

---

**Need more help?** Check the [Troubleshooting Guide](troubleshooting.md) or open an issue on [GitHub](https://github.com/yourusername/highlight-cuts/issues).
