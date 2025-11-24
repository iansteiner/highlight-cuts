# Google Sheets Integration Testing

## Setup Instructions

### 1. Create Test Google Sheet

1. Open the test CSV file: [`tests/fixtures/test_clips.csv`](../fixtures/test_clips.csv)
2. Upload to Google Sheets:
   - Go to [Google Sheets](https://sheets.google.com)
   - Click **File → Import**
   - Upload `test_clips.csv`
   - Choose **Replace spreadsheet** and **Import data**

### 2. Share the Sheet

> [!NOTE]
> Simple link sharing is all you need - no "Publish to web" required!

1. Click the **Share** button
2. Change access to **"Anyone with the link"** → **Viewer**
3. Copy the sharing URL

### 3. Update Test Configuration

1. Open [`tests/config/integration_test_config.yaml`](../config/integration_test_config.yaml)
2. Paste the Google Sheets URL into the `test_sheet_url` field
3. Save the file

### 4. Run Integration Tests

```bash
pytest tests/test_core.py::TestGoogleSheetsIntegration -v
```

## Test Data

The test CSV contains:
- **TestGame**: 3 clips for Alice, 3 for Bob, 2 for Charlie
- **TestGame2**: 1 clip for Alice, 1 for Bob

This allows testing:
- Multiple players
- Multiple clips per player
- Multiple games in same sheet
- Clip merging logic
