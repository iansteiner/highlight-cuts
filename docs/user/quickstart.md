# Quick Start Guide

Get `highlight-cuts` running in 5 minutes using Docker.

## What You'll Need

- [Docker](https://docs.docker.com/get-docker/) installed on your computer
- A game video file (MP4, MOV, or similar)
- Timestamps for highlights (we'll show you how)

## Step 1: Get the Code

```bash
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts
```

## Step 2: Create Required Folders

```bash
mkdir -p data output
```

## Step 3: Start the Web Interface

```bash
docker compose up --build -d
```

This builds and starts the application. It takes about 1-2 minutes the first time.

## Step 4: Add Your Video

Copy your game video into the `data/` folder:

```bash
# Example: copy your video file
cp ~/Videos/game1.mp4 data/
```

## Step 5: Open the Web Interface

Open your browser and go to:

**[http://localhost:8000](http://localhost:8000)**

You should see the Highlight Cuts interface!

## Step 6: Create Your Timestamps

You need a list of when highlights happen. You have two options:

### Option A: Use Google Sheets (Recommended)

1. Create a new Google Sheet
2. Add these columns:

| videoName | startTime | stopTime | playerName |
|-----------|-----------|----------|------------|
| Game1     | 00:01:30  | 00:01:40 | Alice      |
| Game1     | 00:05:10  | 00:05:20 | Alice      |
| Game1     | 00:02:00  | 00:02:15 | Bob        |

3. Share it: Click **Share** → **"Anyone with the link"** → **Viewer**
4. Copy the URL

See the [Google Sheets Guide](google_sheets.md) for more details.

### Option B: Use a Local CSV File

Create a file called `clips.csv`:

```csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,Alice
Game1,00:05:10,00:05:20,Alice
Game1,00:02:00,00:02:15,Bob
```

## Step 7: Generate Highlights

In the web interface:

1. **Select your video** from the dropdown
2. **Paste your Google Sheets URL** (or upload CSV)
3. **Enter the game name** (e.g., "Game1")
4. **Select a player** (e.g., "Alice")
5. Click **"Generate Highlights"**

Processing takes just a few seconds!

## Step 8: Download Your Highlights

Generated videos appear in two places:

1. **On the web page** - Download directly from the "Generated Files" section
2. **In the `output/` folder** - Find them on your computer

## That's It!

You've created your first highlight reel. The output video contains all of Alice's clips merged into one smooth video.

## Next Steps

- [Add more timestamps](google_sheets.md) for more players
- [Use the CLI](usage.md) for advanced options
- Check the [FAQ](faq.md) for common questions
- See [Troubleshooting](troubleshooting.md) if you run into issues

## Need Help?

- **Web interface not loading?** Make sure Docker is running: `docker ps`
- **Video not in dropdown?** Refresh the page after adding videos to `data/`
- **Processing failed?** Check the [Troubleshooting Guide](troubleshooting.md)

---

**Prefer the command line?** Check out the [CLI Usage Guide](usage.md) for more control and options.
