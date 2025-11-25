# Highlight Cuts

**Highlight Cuts** is a command-line tool designed to automate the creation of sports highlight videos. It takes a full game recording and a CSV of timestamps, and produces individual video files for each player featuring their best moments.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Key Features

- 🚀 **Blazing Fast**: Uses FFmpeg stream copying to slice videos without re-encoding (~100x real-time speed)
- 🧠 **Smart Merging**: Automatically combines overlapping or adjacent clips into smooth sequences
- 🎯 **Player-Centric**: Generates a dedicated video file for every player found in your data
- 📊 **Google Sheets Support**: Use Google Sheets URLs directly - no need to download CSV files
- 🔧 **Flexible**: Supports padding adjustments and dry-run previews
- 💎 **Quality Preservation**: Zero generation loss - maintains 100% original video quality

## System Requirements

### Required

- **Python 3.13+** - [Download](https://www.python.org/downloads/)
- **FFmpeg** - Video processing engine
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: [Download from ffmpeg.org](https://ffmpeg.org/download.html)

### Recommended

- **uv** - Fast Python package manager
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Disk Space

- Minimal for the tool itself (~50MB with dependencies)
- Output videos: Approximately (source video size) × (number of players) × 0.5

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts

# Install dependencies
uv sync

# Verify FFmpeg is installed
ffmpeg -version

# Run a dry run to see what would happen
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run

# Generate highlights
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1
```

## Documentation

### Getting Started
- 📖- [Web Interface](docs/web_interface.md): Run the tool in a browser using Docker.
- [Usage Guide](docs/usage.md): Detailed instructions for the CLI.basic usage
- 📊 [Google Sheets Guide](docs/google_sheets.md) - Using Google Sheets instead of CSV files
- ❓ [FAQ](docs/FAQ.md) - Frequently asked questions

### Technical Documentation
- 🏗️ [Architecture & Design](docs/architecture.md) - Technical design and implementation details
- 📝 [Background](docs/background.md) - Why this tool exists and how it works
- 🔧 [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

### Contributing
- 🤝 [Contributing Guide](CONTRIBUTING.md) - How to contribute to the project
- 🔒 [Security Policy](SECURITY.md) - Security considerations and reporting
- 📋 [Changelog](docs/CHANGELOG.md) - Version history and changes

## Example Workflow

1. **Record your game** with any camera or recording device
2. **Log timestamps** during or after the game in a spreadsheet:
   ```csv
   videoName,startTime,stopTime,playerName
   Game1,00:01:30,00:01:40,Alice
   Game1,00:05:10,00:05:20,Alice
   Game1,00:02:00,00:02:15,Bob
   ```
3. **Run the tool** to generate individual highlight videos:
   ```bash
   uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1
   ```
4. **Share** the generated videos with players, parents, or coaches!

## Performance

- **Speed**: ~100x real-time (process a 1-hour game in ~40 seconds)
- **Quality**: Zero generation loss - maintains original video quality
- **Efficiency**: Minimal CPU usage, dominated by disk I/O

## Use Cases

- 🏀 **Coaches**: Create recruiting highlight reels for players
- 👨‍👩‍👧 **Parents**: Share memorable moments from games
- 🎓 **Players**: Build highlight reels for college applications
- 📊 **Analysts**: Extract specific plays for review and analysis

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Bug Reports**: [Open an issue](https://github.com/yourusername/highlight-cuts/issues)
- 💡 **Feature Requests**: [Open an issue](https://github.com/yourusername/highlight-cuts/issues)
- 💬 **Questions**: Check the [FAQ](docs/FAQ.md) or [open a discussion](https://github.com/yourusername/highlight-cuts/discussions)

---

**Made with ❤️ for coaches, players, and sports enthusiasts**