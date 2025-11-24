# Google Sheets Integration - Setup Guide

## ✅ Solution Implemented

The Google Sheets integration is **fully working** using the `/gviz/tq?tqx=out:csv` endpoint.

## Setup Instructions

### 1. Share Your Google Sheet

You only need to share with "Anyone with the link" - **no "Publish to web" required!**

1. Open your Google Sheet
2. Click the **Share** button
3. Change to **"Anyone with the link"**
4. Set permission to **Viewer**
5. Click **Done**
6. Copy the sharing URL

### 2. Use the URL

```bash
uv run highlight-cuts \
  --input-video game.mp4 \
  --csv-file "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing" \
  --game Game1
```

The tool automatically converts any Google Sheets URL format to the correct endpoint.

## Technical Details

- Uses Google Sheets **gviz API endpoint**: `/gviz/tq?tqx=out:csv`
- Works with simple "Share with link" permission
- No authentication required
- No "Publish to web" needed

## Troubleshooting

### "Failed to read CSV: HTTP Error 403/404"

Make sure the sheet is shared with "Anyone with the link can view":
1. Click **Share** → **"Anyone with the link"**
2. Set permission to **Viewer** (not Editor)
3. Click **Done**

### Integration Tests

To run the integration tests:
1. Ensure the test sheet is shared publicly (see above)
2. Run: `uv run pytest tests/test_core.py::TestGoogleSheetsIntegration -v`

All tests should pass if the sheet is properly shared.

