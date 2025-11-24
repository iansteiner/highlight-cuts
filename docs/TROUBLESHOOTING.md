# Troubleshooting Guide

This guide covers common issues and solutions when using `highlight-cuts`.

## Table of Contents

- [Installation Issues](#installation-issues)
- [FFmpeg Errors](#ffmpeg-errors)
- [CSV/Data Issues](#csvdata-issues)
- [Google Sheets Issues](#google-sheets-issues)
- [Video Processing Issues](#video-processing-issues)
- [Performance Issues](#performance-issues)
- [Output Issues](#output-issues)

---

## Installation Issues

### Python Version Error

**Error**: `requires-python >=3.13`

**Solution**: Ensure you have Python 3.13 or later installed:

```bash
# Check Python version
python --version

# Install Python 3.13+ using your package manager
# macOS:
brew install python@3.13

# Ubuntu/Debian:
sudo apt install python3.13
```

### FFmpeg Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**Cause**: FFmpeg is not installed or not in your system PATH.

**Solution**:

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH environment variable

**Verify installation**:
```bash
ffmpeg -version
```

### uv Command Not Found

**Error**: `command not found: uv`

**Solution**: Install `uv` package manager:

```bash
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip:
pip install uv
```

---

## FFmpeg Errors

### Exit Code 1: Invalid Duration

**Error**: `FFmpeg exited with code 1`

**Cause**: Clip timestamps extend beyond the video duration.

**Solution**:
1. Check your video duration:
   ```bash
   ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 your_video.mp4
   ```
2. Verify CSV timestamps are within the video duration
3. Use `--dry-run` to preview clips before processing

### Codec Not Supported

**Error**: `Codec 'xyz' is not supported`

**Cause**: Video uses an uncommon codec that FFmpeg doesn't support in copy mode.

**Solution**:
- Re-encode the source video to a common format (H.264/AAC):
  ```bash
  ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
  ```
- Use the re-encoded video with `highlight-cuts`

### Keyframe Issues

**Symptom**: Clips start/end at slightly different times than specified.

**Cause**: FFmpeg's `-c copy` mode snaps to the nearest keyframe (I-frame).

**Explanation**: This is expected behavior for fast stream copying. Clips may start up to a few seconds earlier than requested.

**Solutions**:
- Accept the minor timing variance (recommended for speed)
- Increase `--padding` to ensure important moments are captured
- Future: Re-encoding mode for frame-accurate cuts (slower)

### Permission Denied

**Error**: `Permission denied` when writing output files

**Solution**:
- Check write permissions on the output directory
- Use `--output-dir` to specify a directory you have write access to
- Avoid system directories (e.g., `/usr`, `C:\Windows`)

---

## CSV/Data Issues

### No Clips Found

**Error**: `No clips found for game 'GameName'`

**Causes**:
1. Game name mismatch (case-sensitive)
2. Wrong CSV file
3. Incorrect column names

**Solutions**:

**Check game name**:
```bash
# Use --dry-run to see what's in the CSV
uv run highlight-cuts --input-video video.mp4 --csv-file clips.csv --game "Game1" --dry-run
```

**Verify CSV format**:
```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,John Doe
```

**Required columns**:
- `videoName` (matches `--game` argument exactly)
- `startTime` (HH:MM:SS or MM:SS)
- `stopTime` (HH:MM:SS or MM:SS)
- `playerName`

### Invalid Time Format

**Error**: `ValueError: time data 'XX:XX' does not match format`

**Cause**: Time format is incorrect.

**Supported formats**:
- `HH:MM:SS` (e.g., `01:23:45`)
- `MM:SS` (e.g., `23:45`)

**Invalid formats**:
- ❌ `1:23:45` (missing leading zero)
- ❌ `1:23` (ambiguous - use `01:23`)
- ❌ `85` (seconds only - use `00:01:25`)

**Solution**: Ensure all times use two-digit format with colons.

### CSV Encoding Issues

**Error**: `UnicodeDecodeError` or garbled player names

**Cause**: CSV file is not UTF-8 encoded.

**Solution**:
1. Open CSV in a text editor (VS Code, Notepad++)
2. Save with UTF-8 encoding
3. Alternatively, export from Excel/Google Sheets as "CSV UTF-8"

### Empty CSV or Missing Data

**Error**: `KeyError: 'videoName'` or similar

**Cause**: CSV is missing required columns or is empty.

**Solution**:
- Verify the CSV has a header row with correct column names
- Check that there are data rows below the header
- Ensure no extra blank rows at the top of the file

---

## Google Sheets Issues

### HTTP 403 Forbidden

**Error**: `Failed to read CSV: HTTP Error 403`

**Cause**: Sheet is not publicly accessible.

**Solution**:

1. Open your Google Sheet
2. Click **Share** button (top-right)
3. Click **"Change to anyone with the link"**
4. Set permission to **Viewer**
5. Click **Done**
6. Copy the sharing URL

> [!IMPORTANT]
> You do NOT need to use "Publish to web" - simple link sharing is sufficient!

### HTTP 404 Not Found

**Error**: `Failed to read CSV: HTTP Error 404`

**Causes**:
1. Incorrect sheet ID in URL
2. Sheet was deleted
3. URL is malformed

**Solution**:
- Verify the URL is correct
- Try opening the URL in a browser to confirm it exists
- Copy the URL directly from the browser address bar

### Wrong Sheet Tab

**Symptom**: Data from wrong tab is being used.

**Cause**: Spreadsheet has multiple tabs, and the wrong one is being accessed.

**Solution**:

Include the `gid` (sheet ID) in the URL:

```bash
# Click on the sheet tab you want
# The URL will show: ...edit#gid=123456789
# Use that full URL:
uv run highlight-cuts \
  --input-video video.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=123456789" \
  --game Game1
```

### Rate Limiting

**Symptom**: Intermittent failures when downloading from Google Sheets.

**Cause**: Google may rate-limit excessive requests.

**Solution**:
- Add delays between runs if processing many games
- Download CSV locally for repeated testing:
  ```bash
  # Download once
  curl "https://docs.google.com/spreadsheets/d/SHEET_ID/gviz/tq?tqx=out:csv" -o clips.csv
  
  # Use local file
  uv run highlight-cuts --input-video video.mp4 --csv-file clips.csv --game Game1
  ```

---

## Video Processing Issues

### Video File Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'video.mp4'`

**Solution**:
- Use absolute paths: `/full/path/to/video.mp4`
- Or use relative paths from your current directory: `./videos/game.mp4`
- Verify the file exists: `ls -la video.mp4`

### Unsupported Video Format

**Error**: FFmpeg errors about unsupported format or codec.

**Cause**: Video format is not compatible with stream copying.

**Common compatible formats**:
- ✅ MP4 (H.264 video, AAC audio)
- ✅ MOV (H.264 video, AAC audio)
- ✅ MKV (H.264 video)

**Solution**:
Convert to MP4 with H.264:
```bash
ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4
```

### Corrupted Output Files

**Symptom**: Output videos won't play or have artifacts.

**Causes**:
1. Source video is corrupted
2. Disk space ran out during processing
3. FFmpeg was interrupted

**Solutions**:
- Verify source video plays correctly
- Check available disk space: `df -h`
- Re-run the command
- Try with a different source video to isolate the issue

---

## Performance Issues

### Slow Processing

**Expected**: Stream copying should be very fast (seconds, not minutes).

**If slow**:

1. **Check if re-encoding is happening**:
   - Look for FFmpeg output showing encoding progress
   - Should see "speed=100x" or higher for stream copy
   - If speed is <10x, re-encoding is occurring

2. **Disk I/O bottleneck**:
   - Use SSD instead of HDD for output
   - Avoid network drives for output directory

3. **Large number of clips**:
   - Processing 100+ clips will take longer
   - Consider batch processing in smaller groups

### High Memory Usage

**Symptom**: System runs out of memory.

**Cause**: Processing very large video files or many clips simultaneously.

**Solutions**:
- Process one game at a time
- Close other applications
- Increase system swap/page file

### Disk Space Issues

**Error**: `No space left on device`

**Solution**:
- Check available space: `df -h`
- Clean up old output files
- Use `--output-dir` to specify a drive with more space
- Estimate space needed: (source video size) × (number of players) × 0.5

---

## Output Issues

### Output Files Not Created

**Checklist**:
1. Did FFmpeg exit successfully? (Check terminal output)
2. Do you have write permissions? (Try `--output-dir ~/Desktop`)
3. Is there disk space available? (`df -h`)
4. Did you use `--dry-run`? (Remove it to actually process)

### Wrong Output Location

**Issue**: Can't find generated files.

**Solution**:
- By default, files are saved to the current directory
- Check where you ran the command: `pwd`
- Use `--output-dir` to specify exact location:
  ```bash
  uv run highlight-cuts --input-video video.mp4 --csv-file clips.csv --game Game1 --output-dir ~/highlights
  ```

### Filename Issues

**Symptom**: Output filenames have special characters or spaces.

**Cause**: Player names in CSV contain special characters.

**Current behavior**: Filenames use player names as-is.

**Workaround**:
- Use simple player names in CSV (e.g., "John_Doe" instead of "John Doe Jr.")
- Rename files after processing if needed

---

## Getting More Help

### Enable Verbose Output

Currently not implemented, but you can see FFmpeg output by default.

### Check FFmpeg Output

FFmpeg prints detailed information. Look for:
- Error messages (usually at the end)
- Warnings about codec compatibility
- Duration and timing information

### Dry Run Mode

Always test with `--dry-run` first:

```bash
uv run highlight-cuts --input-video video.mp4 --csv-file clips.csv --game Game1 --dry-run
```

This shows:
- Which clips will be created
- Total duration per player
- No actual processing occurs

### Report Issues

If you encounter a bug:

1. Check this troubleshooting guide
2. Search existing [GitHub Issues](https://github.com/yourusername/highlight-cuts/issues)
3. Open a new issue with:
   - Command you ran
   - Error message (full output)
   - Video format (`ffprobe video.mp4`)
   - CSV sample (first few rows)
   - Operating system and Python version

---

## Common Workflows

### Testing with New CSV

```bash
# 1. Dry run to verify data
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run

# 2. Process one player's clips (modify CSV to test)
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1

# 3. If successful, process all players
# (Already done in step 2 - it processes all players automatically)
```

### Debugging FFmpeg Issues

```bash
# 1. Check video info
ffprobe game.mp4

# 2. Test manual FFmpeg extraction
ffmpeg -i game.mp4 -ss 00:01:00 -to 00:01:30 -c copy test_clip.mp4

# 3. If manual extraction works, issue is with highlight-cuts
# 4. If manual extraction fails, issue is with video file or FFmpeg
```

### Working with Google Sheets

```bash
# 1. Share sheet with "Anyone with the link"
# 2. Test URL in browser first
# 3. Copy full URL from browser
# 4. Run with URL:
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_ID/edit?usp=sharing" \
  --game Game1 \
  --dry-run
```

---

**Still having issues?** Open an issue on [GitHub](https://github.com/yourusername/highlight-cuts/issues) with details!
