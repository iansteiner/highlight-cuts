# Frequently Asked Questions (FAQ)

## General Questions

### What is Highlight Cuts?

Highlight Cuts is a command-line tool that automatically creates sports highlight videos. It takes a full game recording and a CSV file with timestamps, then generates individual highlight videos for each player.

### Who is this tool for?

- **Coaches**: Create highlight reels for player development and recruiting
- **Parents**: Make shareable videos of their kids' best moments
- **Players**: Build personal highlight reels for college applications
- **Team managers**: Distribute highlights to the team after games

### Do I need to know how to code?

Basic command-line knowledge is helpful, but not required. If you can open a terminal and copy-paste commands, you can use this tool.

**Future**: A GUI version is planned to make it even easier for non-technical users.

### How much does it cost?

Highlight Cuts is **completely free** and open-source. There are no subscriptions, licenses, or hidden fees.

---

## Installation & Setup

### What do I need to install?

1. **Python 3.13+** (programming language)
2. **FFmpeg** (video processing software)
3. **highlight-cuts** (this tool)

See the [Usage Guide](usage.md) for detailed installation instructions.

### Do I need a powerful computer?

No! Highlight Cuts uses stream copying, which is very fast and doesn't require much CPU power. Any modern computer (even a laptop) will work fine.

**Typical performance**: Process a 1-hour game video in under a minute.

### Can I use this on Windows/Mac/Linux?

Yes! Highlight Cuts works on all three platforms. FFmpeg and Python are available for all operating systems.

---

## Video Processing

### What video formats are supported?

Most common formats work:
- ✅ MP4 (H.264 video, AAC audio) - **recommended**
- ✅ MOV (H.264 video, AAC audio)
- ✅ MKV (H.264 video)
- ⚠️ AVI, WMV, FLV - may need conversion

**Tip**: If you have issues, convert your video to MP4 first:
```bash
ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4
```

### Why are my clips slightly longer/shorter than specified?

This is expected behavior! Highlight Cuts uses **stream copying** for speed, which means clips snap to the nearest "keyframe" (I-frame) in the video.

**Result**: Clips may start up to 1-2 seconds earlier than requested.

**Solution**: Use `--padding 2.0` to add buffer time and ensure important moments are captured.

### Can I get frame-perfect cuts?

Not currently. Frame-perfect cuts require re-encoding the video, which is 100x slower.

**Future**: A `--re-encode` option is planned for users who need exact timing.

### How long does processing take?

**Very fast!** Stream copying processes video at ~100x real-time speed.

**Examples**:
- 30-minute game → ~20 seconds
- 1-hour game → ~40 seconds
- 2-hour game → ~80 seconds

**Note**: Time varies based on disk speed and number of clips.

### Will the video quality be reduced?

**No!** Stream copying preserves 100% of the original quality. There is zero generation loss.

---

## CSV & Data

### What format should my CSV be?

Your CSV must have these columns:

```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,John Doe
Game1,00:05:10,00:05:20,John Doe
```

**Required columns**:
- `videoName`: Name of the game (matches `--game` argument)
- `startTime`: Start time in `HH:MM:SS` or `MM:SS` format
- `stopTime`: End time in `HH:MM:SS` or `MM:SS` format
- `playerName`: Player's name

### Can I use Excel?

Yes! Create your spreadsheet in Excel, then save as CSV:
1. File → Save As
2. Choose "CSV UTF-8 (Comma delimited)"

### Can I use Google Sheets?

**Yes!** This is actually recommended for collaborative editing.

1. Create your sheet in Google Sheets
2. Share it with "Anyone with the link" (Viewer permission)
3. Copy the URL
4. Use the URL directly with `--csv-file`

See the [Google Sheets Guide](google_sheets.md) for details.

### How do I log timestamps during a game?

**Option 1: Live logging**
- Use a stopwatch app on your phone
- Record times in a notes app during the game
- Transfer to CSV/Google Sheets after

**Option 2: Post-game review**
- Watch the game recording
- Note timestamps for highlights
- Enter into spreadsheet

**Tip**: Use Google Sheets on a tablet during the game for real-time collaborative logging.

### Can I have multiple games in one CSV?

Yes! Use the `videoName` column to distinguish games:

```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,Alice
Game1,00:05:10,00:05:20,Bob
Game2,00:02:00,00:02:15,Alice
Game2,00:03:00,00:03:10,Bob
```

Then process each game separately:
```bash
highlight-cuts --input-video game1.mp4 --csv-file clips.csv --game Game1
highlight-cuts --input-video game2.mp4 --csv-file clips.csv --game Game2
```

---

## Output & Results

### Where are the output files saved?

By default, files are saved to your **current directory** (where you ran the command).

**To specify a different location**:
```bash
highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --output-dir ~/highlights
```

### What are the output filenames?

Format: `{OriginalVideoName}_{PlayerName}.{Extension}`

**Example**:
- Input video: `game_footage.mp4`
- Player: `John Doe`
- Output: `game_footage_John_Doe.mp4`

### Can I customize the output filenames?

Not currently. This is a planned feature.

**Workaround**: Rename files after processing or use simple player names in your CSV.

### How many files will be created?

**One file per player** found in the CSV for the specified game.

**Example**:
- CSV has 3 players (Alice, Bob, Charlie)
- Game1 has clips for all 3 players
- Result: 3 output files

### Can I preview before processing?

**Yes!** Use the `--dry-run` flag:

```bash
highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run
```

This shows:
- Which clips will be created
- Total duration per player
- No actual processing occurs

---

## Advanced Usage

### What is padding?

Padding adds extra time before and after each clip.

**Example**:
- Clip: `00:01:00` to `00:01:10` (10 seconds)
- With `--padding 2.0`: `00:00:58` to `00:01:12` (14 seconds)

**Why use padding?**
- Ensure important moments aren't cut off
- Compensate for keyframe snapping
- Add context to highlights

**Recommended**: `--padding 2.0` (2 seconds)

### What happens to overlapping clips?

They are **automatically merged** into one continuous clip.

**Example**:
- Clip 1: `00:01:00` to `00:01:10`
- Clip 2: `00:01:08` to `00:01:20`
- Result: One merged clip `00:01:00` to `00:01:20`

**Why?** Avoids duplicate content and creates smoother highlight reels.

### Can I add transitions between clips?

Not yet. This is a planned feature using FFmpeg's `xfade` filter.

See `ai/future/xfade_transitions.md` for the implementation plan.

### Can I add music or commentary?

Not currently. The tool preserves the original audio from the source video.

**Workaround**: Use a video editor (iMovie, DaVinci Resolve) to add music to the generated highlights.

### Can I process multiple games at once?

Not currently. You need to run the command separately for each game.

**Future**: Batch processing is planned.

**Workaround**: Use a shell script:
```bash
#!/bin/bash
highlight-cuts --input-video game1.mp4 --csv-file clips.csv --game Game1
highlight-cuts --input-video game2.mp4 --csv-file clips.csv --game Game2
highlight-cuts --input-video game3.mp4 --csv-file clips.csv --game Game3
```

---

## Troubleshooting

### The tool says "FFmpeg not found"

FFmpeg is not installed or not in your system PATH.

**Solution**: Install FFmpeg:
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

See [Troubleshooting Guide](TROUBLESHOOTING.md#ffmpeg-not-found) for details.

### "No clips found for game 'GameName'"

**Causes**:
1. Game name mismatch (case-sensitive)
2. Wrong CSV file
3. Typo in `--game` argument

**Solution**: Use `--dry-run` to see what games are in your CSV.

### Google Sheets URL not working

**Most common issue**: Sheet is not publicly shared.

**Solution**:
1. Click **Share** → **"Anyone with the link"**
2. Set permission to **Viewer**
3. Click **Done**

See [Google Sheets Guide](google_sheets.md#troubleshooting) for more help.

### Output videos won't play

**Causes**:
1. Source video is corrupted
2. Incompatible codec
3. Processing was interrupted

**Solution**:
- Verify source video plays correctly
- Try converting to MP4 with H.264
- Re-run the command

See [Troubleshooting Guide](TROUBLESHOOTING.md) for comprehensive solutions.

---

## Comparison with Other Tools

### How is this different from manual editing?

| Manual Editing | Highlight Cuts |
|----------------|----------------|
| 30-60 minutes per player | Seconds for all players |
| Requires video editing skills | Simple CSV + command |
| Prone to human error | Automated, consistent |
| Expensive software | Free and open-source |

### How is this different from online highlight services?

| Online Services | Highlight Cuts |
|-----------------|----------------|
| Monthly subscription ($10-50) | Free |
| Upload limits | No limits |
| Privacy concerns | Your data stays local |
| Limited customization | Full control |
| Requires internet | Works offline |

### Can this replace a professional editor?

For **basic highlight reels**: Yes!

For **advanced editing** (slow-motion, effects, music, graphics): No. Use this tool to create the base highlights, then enhance in a professional editor if needed.

---

## Privacy & Security

### Is my data safe?

**Yes!** All processing happens locally on your computer. No data is uploaded to any servers (except Google Sheets if you use that feature).

### What about Google Sheets?

If you use Google Sheets URLs:
- The sheet must be publicly shared (anyone with the link can view)
- Don't include sensitive information in shared sheets
- Use local CSV files for private data

See [SECURITY.md](../SECURITY.md) for more details.

---

## Contributing & Support

### How can I report a bug?

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Search [existing issues](https://github.com/yourusername/highlight-cuts/issues)
3. Open a new issue with:
   - Command you ran
   - Error message
   - Video format and CSV sample

### How can I request a feature?

Open a [GitHub issue](https://github.com/yourusername/highlight-cuts/issues) with:
- Description of the feature
- Use case / why it's needed
- Example of how it would work

### Can I contribute code?

**Yes!** Contributions are welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Where can I get help?

- **Documentation**: Check `docs/` folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/highlight-cuts/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/highlight-cuts/discussions)

---

## Future Plans

### What features are planned?

**High Priority**:
- GUI (Streamlit web interface)
- Batch processing multiple games
- Configuration file support
- Better logging and progress tracking

**Medium Priority**:
- Transitions between clips (xfade)
- Re-encoding mode for frame-accurate cuts
- Custom output filename templates

**Future**:
- Automatic highlight detection (AI-based)
- Slow-motion effects
- Watermarking support

See `ai/future/` for detailed plans.

### When will the GUI be available?

No specific timeline yet. It's documented in `ai/future/gui_distribution_plan.md` and will be implemented based on user demand.

**Want it sooner?** Let us know by opening a GitHub issue or contributing!

---

**Have a question not answered here?** Open an issue on [GitHub](https://github.com/yourusername/highlight-cuts/issues)!
