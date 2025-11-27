# Using Google Sheets with highlight-cuts

## Overview

Instead of maintaining a local CSV file, you can use a Google Sheets spreadsheet and provide the URL directly to `highlight-cuts`. The tool will automatically download and process the data.

## Setup Instructions

### 1. Create or Open Your Google Sheet

Your sheet should have the same format as the CSV file:

| videoName | startTime | stopTime | playerName | include | notes |
|-----------|-----------|----------|------------|---------|-------|
| Game1     | 00:01:00  | 00:01:15 | Alice      | TRUE    | Nice play |
| Game1     | 00:05:30  | 00:05:45 | Alice      | FALSE   | Skipped |
| Game1     | 00:02:00  | 00:02:10 | Bob        |         | Defaults to TRUE |

*   **include**: (Optional) Set to `FALSE` to skip this clip. Blanks or `TRUE` are included.
*   **notes**: (Optional) Any notes about the clip.

### 2. Share the Sheet

> [!IMPORTANT]
> You only need to share with "Anyone with the link" - you do NOT need to use "Publish to web"

1. Click the **Share** button in the top-right corner
2. Click **"Change to anyone with the link"**
3. Ensure the permission is set to **Viewer**
4. Click **Done**
5. Copy the sharing URL

### 3. Use the URL with highlight-cuts

You can paste the URL directly - the tool accepts any of these formats:

```bash
# Regular sharing URL (most common)
highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing" \
  --game Game1

# URL with specific sheet tab
highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit#gid=123" \
  --game Game1

# Already-converted export URL
highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv" \
  --game Game1
```

The tool automatically converts any Google Sheets URL to the proper CSV export format.

## Multiple Sheets (Tabs)

If your spreadsheet has multiple tabs:

- **Default behavior**: Uses the first sheet (gid=0)
- **Specific tab**: Include `#gid=SHEET_ID` in the URL
  - You can find the gid by clicking on the sheet tab - it appears in the browser URL
  - Example: `...edit#gid=456` will use that specific sheet

## Benefits

✅ **Collaborative editing**: Multiple people can update the timestamps  
✅ **No file syncing**: Always uses the latest data  
✅ **Easy updates**: Edit in Google Sheets, re-run the command  
✅ **Backward compatible**: Local CSV files still work exactly as before

## Security Note

> [!WARNING]
> Sharing a sheet with "Anyone with the link" makes it publicly accessible. Don't share sheets containing sensitive information.

If you need to keep your data private, use a local CSV file instead.

## Troubleshooting

### "Failed to read CSV: HTTP Error 400/403/404"

This means the sheet isn't publicly accessible. Make sure you've:
1. Clicked **Share** → **"Anyone with the link"**
2. Set permission to **Viewer** (not Editor)
3. Clicked **Done**

> [!NOTE]
> You do NOT need to use "Publish to web" - simple link sharing is sufficient!

### "No clips found for the specified game"

Check that:
- The `videoName` column matches the `--game` parameter exactly (case-sensitive)
- You're using the correct sheet tab if you have multiple tabs

### Local CSV files stopped working

Local files still work! Just provide the file path as before:
```bash
highlight-cuts --input-video game.mp4 --csv-file ./clips.csv --game Game1
```
