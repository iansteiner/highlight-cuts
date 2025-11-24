# Highlight Cuts

**Highlight Cuts** is a command-line tool designed to automate the creation of sports highlight videos. It takes a full game recording and a CSV of timestamps, and produces individual video files for each player featuring their best moments.

## Key Features
- 🚀 **Blazing Fast**: Uses FFmpeg stream copying to slice videos without re-encoding.
- 🧠 **Smart Merging**: Automatically combines overlapping or adjacent clips into smooth sequences.
- 🎯 **Player-Centric**: Generates a dedicated video file for every player found in your data.
- 🔧 **Flexible**: Supports padding adjustments and dry-run previews.

## Documentation
- [Usage Guide](docs/usage.md): How to install and run the tool.
- [Background & Design](docs/background.md): Context on why this tool exists and how it works.

## Quick Start

```bash
# Install dependencies
uv sync

# Run a dry run to see what would happen
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run
```