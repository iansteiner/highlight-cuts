# Example Files

This directory contains example files to help you get started with `highlight-cuts`.

## Sample CSV Files

### `sample_clips.csv`

A basic example showing the required CSV format:

```csv
videoName,startTime,stopTime,playerName
SampleGame,00:01:30,00:01:45,Alice Johnson
SampleGame,00:03:20,00:03:35,Alice Johnson
SampleGame,00:07:10,00:07:25,Alice Johnson
SampleGame,00:02:15,00:02:30,Bob Smith
SampleGame,00:05:45,00:06:00,Bob Smith
SampleGame,00:09:30,00:09:45,Bob Smith
SampleGame,00:04:00,00:04:15,Charlie Davis
SampleGame,00:08:20,00:08:35,Charlie Davis
```

**Features demonstrated**:
- Multiple clips per player
- Standard time format (HH:MM:SS)
- Three players in one game

**Usage**:
```bash
uv run highlight-cuts --input-video your_game.mp4 --csv-file docs/examples/sample_clips.csv --game SampleGame --dry-run
```

### `multi_game_season.csv`

Example showing multiple games in one CSV file:

```csv
videoName,startTime,stopTime,playerName
Week1,00:01:30,00:01:45,Alice Johnson
Week1,00:03:20,00:03:35,Bob Smith
Week2,00:02:15,00:02:30,Alice Johnson
Week2,00:05:45,00:06:00,Charlie Davis
Week3,00:04:00,00:04:15,Bob Smith
Week3,00:08:20,00:08:35,Alice Johnson
```

**Features demonstrated**:
- Multiple games in one file
- Season-long tracking
- Filtering by game name

**Usage**:
```bash
# Process Week 1
uv run highlight-cuts --input-video week1.mp4 --csv-file docs/examples/multi_game_season.csv --game Week1

# Process Week 2
uv run highlight-cuts --input-video week2.mp4 --csv-file docs/examples/multi_game_season.csv --game Week2
```

## Creating Your Own CSV

### Method 1: Excel/Google Sheets

1. Create a spreadsheet with these columns:
   - `videoName`
   - `startTime`
   - `stopTime`
   - `playerName`

2. Fill in your data

3. Export as CSV:
   - **Excel**: File → Save As → CSV UTF-8
   - **Google Sheets**: File → Download → CSV

### Method 2: Text Editor

Create a plain text file with `.csv` extension:

```csv
videoName,startTime,stopTime,playerName
YourGame,00:01:00,00:01:15,Player Name
```

**Important**:
- First row must be the header
- Use commas to separate columns
- Times in `HH:MM:SS` or `MM:SS` format
- Save with UTF-8 encoding

## Tips for Logging Timestamps

### During the Game

Use a stopwatch app and note app on your phone:
1. Start stopwatch when video recording starts
2. When a highlight happens, note the time and player
3. After the game, transfer to CSV

### After the Game

Watch the recording and note timestamps:
1. Open video in a player that shows timestamps
2. Pause at highlight moments
3. Record time and player in spreadsheet
4. Export to CSV

### Collaborative Logging

Use Google Sheets for team collaboration:
1. Create shared Google Sheet
2. Multiple people can log during the game
3. Share the URL directly with `highlight-cuts`
4. No need to download CSV

See [Google Sheets Guide](../google_sheets.md) for details.

## Common Patterns

### Overlapping Clips

The tool automatically merges overlapping clips:

```csv
videoName,startTime,stopTime,playerName
Game1,00:01:00,00:01:15,Alice
Game1,00:01:10,00:01:25,Alice
```

Result: One merged clip from `00:01:00` to `00:01:25`

### Using Padding

Add buffer time with `--padding`:

```bash
# Original clip: 00:01:00 to 00:01:15
# With --padding 2.0: 00:00:58 to 00:01:17
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --padding 2.0
```

### Short Time Format

You can use `MM:SS` for times under 1 hour:

```csv
videoName,startTime,stopTime,playerName
Game1,01:30,01:45,Alice
Game1,05:20,05:35,Bob
```

Equivalent to `00:01:30` and `00:05:20`.

---

For more examples and use cases, see the [Usage Guide](../usage.md) and [FAQ](../FAQ.md).
