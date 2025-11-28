# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Highlight Cuts** is a Python CLI and web tool that automates sports highlight video creation. It takes a full game recording and a CSV of timestamps, producing individual video files for each player featuring their best moments. The tool uses FFmpeg stream copying for blazing-fast processing (~100x real-time speed) with zero quality loss.

## Common Development Commands

### Package Management
```bash
# Install all dependencies (uses uv package manager)
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

### Running the Application
```bash
# CLI usage
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1

# CLI with dry run (preview without creating files)
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1 --dry-run

# Start web server (FastAPI/Uvicorn)
uv run python -m uvicorn highlight_cuts.web:app --reload
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_core.py -v

# Run single test
uv run pytest tests/test_core.py::test_function_name -v
```

### Code Quality
```bash
# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Docker
```bash
# Build Docker image
docker build -t highlight-cuts .

# Run Docker container
docker run -p 8000:8000 highlight-cuts

# Build and run with docker-compose
docker-compose up --build
```

## Architecture & Code Structure

### Module Organization

The codebase follows a **separation of concerns** principle with distinct layers:

```
src/highlight_cuts/
├── cli.py          # Click-based command-line interface
├── core.py         # Pure business logic (CSV processing, interval merging)
├── ffmpeg.py       # FFmpeg wrapper (process execution, file I/O)
├── utils.py        # Pure utility functions (time parsing)
├── web.py          # FastAPI web interface
├── templates/      # Jinja2 HTML templates
└── static/         # CSS, JS, images
```

### Core Design Principles

1. **Pure Core Logic**: `core.py` contains no I/O or side effects - all functions are deterministic and easily testable
2. **Isolated Dependencies**: FFmpeg, file system, and network operations are isolated in wrapper modules (`ffmpeg.py`, `cli.py`)
3. **Stream Copy First**: Uses FFmpeg `-c copy` mode for maximum speed (no re-encoding)
4. **Testability**: Unit tests mock I/O, integration tests use real FFmpeg

### Key Algorithms

#### Interval Merging (`core.py`)
Overlapping or adjacent time intervals are merged to create smooth highlight reels:

1. Apply padding to each interval: `(start - padding, end + padding)`
2. Sort intervals by start time
3. Iterate and merge overlapping intervals
4. Extract merged clips with FFmpeg

**Example**:
```python
intervals = [(10, 20), (15, 25), (30, 40)]
padding = 2.0
# After padding: [(8, 22), (13, 27), (28, 42)]
# After merging: [(8, 27), (28, 42)]
```

#### Google Sheets URL Normalization (`core.py`)
Converts any Google Sheets URL format to CSV export endpoint:
- Sharing URLs: `...edit?usp=sharing`
- Edit URLs: `...edit#gid=123`
- Export URLs: `...export?format=csv`

Output: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}`

### Data Flow

```
User Input (CLI/Web)
  → process_csv() - Read and filter CSV by game
  → Group clips by player
  → merge_intervals() - Combine overlapping clips
  → extract_clip() - FFmpeg stream copy for each interval
  → concat_clips() - FFmpeg concat for each player
  → Output: Game_PlayerName.mp4
```

## Testing Strategy

### Unit Tests (96% coverage)
- Mock all I/O operations (FFmpeg, file system, network)
- Fast execution (< 1 second)
- Located in `tests/test_*.py`

### Integration Tests
- Use real FFmpeg with generated test videos
- Verify end-to-end functionality
- Located in `tests/test_integration.py`

### Web Tests
- Use FastAPI `TestClient` + `BeautifulSoup4`
- Test HTML rendering and form handling
- Located in `tests/test_web*.py`

### Docker Tests
- Build and run container
- Verify FFmpeg installation and app health
- Located in `tests/test_docker_config.py`

### Running Specific Test Categories
```bash
# Core logic tests
uv run pytest tests/test_core.py tests/test_utils.py

# Web interface tests
uv run pytest tests/test_web*.py

# Integration tests (requires FFmpeg)
uv run pytest tests/test_integration.py
```

## Workflow Requirements

**CRITICAL**: When making code changes, you **MUST** follow this workflow:

1. **Lint & Format**
   ```bash
   uv run ruff check --fix .
   uv run ruff format .
   ```

2. **Test**: Ensure ALL tests pass
   ```bash
   uv run pytest --cov=src
   ```

3. **Document**: Update relevant documentation
   - `docs/user/` for end-user features
   - `docs/dev/` for technical/contributor docs
   - `docs/CHANGELOG.md` for significant changes
   - `README.md` if high-level info changes
   - See `ai/doc_instructions.md` for detailed guidelines

4. **Session Summary**: Create `ai/session_summaries/YYYY-MM-DD_session_N.md`
   - Describe what was done, why, and outcome
   - See `ai/doc_instructions.md` for structure

## Important Implementation Details

### FFmpeg Usage
- **Stream Copy Mode**: All clips use `-c copy` for speed (no re-encoding)
- **Keyframe Snapping**: Clips may start/end ±1-2 seconds from exact timestamps
- **Concat Demuxer**: Multiple clips are joined using FFmpeg concat with a temporary filelist
- **Error Handling**: FFmpeg stderr is captured and raised as exceptions

### CSV Format
Required columns:
- `videoName`: Game identifier (must match `--game` argument)
- `startTime`: HH:MM:SS or MM:SS format
- `stopTime`: HH:MM:SS or MM:SS format
- `playerName`: Player identifier (used in output filename)

### Web Interface
- Built with FastAPI + Jinja2 templates
- Single-page upload interface at `/`
- Form submission to `/process` endpoint
- Returns JSON with download URLs
- Static files served from `src/highlight_cuts/static/`

### Dependencies
- **Runtime**: click, pandas, requests, pyyaml, fastapi, uvicorn, jinja2, python-multipart
- **Dev**: pytest, pytest-cov, ruff, beautifulsoup4, httpx
- **External**: FFmpeg (must be installed separately, not a Python package)

### Python Version
Requires **Python 3.13+** for modern type hints and features.

## Common Tasks

### Adding a New CLI Flag
1. Add to `cli.py` using `@click.option()`
2. Pass to core logic functions
3. Update `docs/user/usage.md`
4. Add tests to `tests/test_cli.py`
5. Update `CHANGELOG.md`

### Adding a New Core Function
1. Implement pure logic in `core.py` (no I/O)
2. Add comprehensive unit tests in `tests/test_core.py`
3. Document in `docs/dev/architecture.md`
4. Import and use in `cli.py` or `web.py`

### Modifying FFmpeg Commands
1. Update wrapper functions in `ffmpeg.py`
2. Test with integration tests in `tests/test_integration.py`
3. Document behavior changes in `docs/dev/architecture.md`
4. Consider backward compatibility

### Adding Web Interface Features
1. Update `web.py` (routes, business logic)
2. Update templates in `src/highlight_cuts/templates/`
3. Add tests to `tests/test_web*.py`
4. Update `docs/user/web_interface.md`

## File Locations

### Source Code
- `src/highlight_cuts/` - Main package

### Tests
- `tests/` - All test files
- `tests/fixtures/` - Test data (CSVs, videos)
- `tests/config/` - Configuration for external tests (Google Sheets)

### Documentation
- `docs/user/` - End-user guides
- `docs/dev/` - Developer/contributor docs
- `docs/CHANGELOG.md` - Version history
- `README.md` - Project landing page

### AI Context
- `ai/session_summaries/` - Session logs (create one per chat session)
- `ai/future/` - Future feature plans
- `ai/instructions.md` - Workflow rules
- `ai/doc_instructions.md` - Documentation standards

### Configuration
- `pyproject.toml` - Python project config, dependencies, test settings
- `Dockerfile` - Docker container definition
- `docker-compose.yml` - Multi-container setup
- `.vscode/` - VS Code settings

## Documentation Philosophy

### Two-Tier Documentation
- **User Docs** (`docs/user/`): Simple, deployment-focused for coaches/parents/players
- **Developer Docs** (`docs/dev/`): Technical, contribution-focused for contributors

### AI-Friendly Documentation
- Use hierarchical headings
- Front-load key information
- Prefer structured lists over prose
- Include code examples with syntax highlighting
- Use Mermaid diagrams (not ASCII art)
- Link to specific code locations with file:line references

See `ai/doc_instructions.md` for comprehensive documentation standards.

## Performance Characteristics

- **Speed**: ~100x real-time (1-hour video processes in ~36 seconds)
- **Quality**: Zero generation loss (stream copy preserves original)
- **Memory**: < 100 MB typical usage
- **Bottlenecks**: Disk I/O, number of clips, network latency for Google Sheets

## Known Limitations

- Clips snap to keyframes (±1-2 seconds accuracy) due to stream copy
- Requires compatible video codecs for stream copy
- No transitions between clips (future feature)
- Single game processing only (no batch mode yet)

## Security Considerations

- No shell injection: FFmpeg commands use `subprocess.run()` without `shell=True`
- CSV validation via pandas
- Google Sheets URLs are normalized and validated
- File uploads are validated by extension and content type (web interface)

See `SECURITY.md` for detailed security policy.

## Future Features (In Planning)

- Cross-fade transitions (requires re-encoding)
- Batch processing for multiple games
- GUI/Streamlit interface
- Config file support (`.highlight-cuts.yaml`)
- Server-side Google Sheets tracking
- Interactive clip editing

See `ai/future/` for detailed planning documents.

---

**Last Updated**: 2025-11-27
