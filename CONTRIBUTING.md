# Contributing to Highlight Cuts

Thank you for your interest in contributing to **Highlight Cuts**! This document provides guidelines for developers who want to contribute to the project.

## Development Setup

### Prerequisites

- **Python 3.13+**
- **FFmpeg** installed and available in your PATH
- **uv** package manager (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/highlight-cuts.git
   cd highlight-cuts
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

3. Verify FFmpeg is installed:
   ```bash
   ffmpeg -version
   ```

### Running the Tool Locally

```bash
# Run from source
uv run highlight-cuts --help

# Run with development dependencies
uv run highlight-cuts --input-video test.mp4 --csv-file test.csv --game Game1 --dry-run
```

## Development Workflow

When making changes to this project, **you MUST follow these steps**:

### 1. Lint & Format

Ensure code is clean and properly formatted:

```bash
# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### 2. Write Tests

- Write unit tests for new functionality
- Ensure all tests pass before submitting
- Maintain or improve code coverage (currently 96%)

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_core.py -v
```

### 3. Update Documentation

- Update `docs/` files if features change
- Update `README.md` if high-level information changes
- Add entries to `docs/CHANGELOG.md` for significant changes
- Follow [Keep a Changelog](https://keepachangelog.com/) format

### 4. Test Integration

Run integration tests to verify end-to-end functionality:

```bash
# Run integration tests
uv run pytest tests/test_integration.py -v
```

## Code Style Guidelines

### Python Style

- Follow PEP 8 conventions (enforced by `ruff`)
- Use type hints for function signatures
- Write descriptive docstrings for public functions
- Keep functions focused and single-purpose

### Example:

```python
def parse_time(time_str: str) -> float:
    """
    Parse a time string in HH:MM:SS or MM:SS format to seconds.
    
    Args:
        time_str: Time string to parse
        
    Returns:
        Time in seconds as a float
        
    Raises:
        ValueError: If time_str format is invalid
    """
    # Implementation...
```

### Module Organization

- `src/highlight_cuts/core.py`: Core business logic (CSV processing, interval merging)
- `src/highlight_cuts/ffmpeg.py`: FFmpeg wrapper functions
- `src/highlight_cuts/cli.py`: Command-line interface
- `src/highlight_cuts/utils.py`: Utility functions (time parsing, etc.)

## Testing Guidelines

### Unit Tests

- Mock external dependencies (FFmpeg, file system)
- Test edge cases and error conditions
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`

### Integration Tests

- Test with real FFmpeg commands
- Verify output file creation and correctness
- Clean up temporary files after tests

### Test Coverage

- Aim for 95%+ code coverage
- Focus on critical paths and error handling
- Don't sacrifice test quality for coverage percentage

## Submitting Changes

### Pull Request Process

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the workflow above

3. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: description of what you added"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request** with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots/examples if applicable

### Commit Message Format

Use clear, descriptive commit messages:

- `feat: Add support for batch processing multiple games`
- `fix: Resolve Google Sheets URL parsing issue`
- `docs: Update installation instructions`
- `test: Add integration tests for xfade transitions`
- `refactor: Simplify interval merging logic`

## Project Structure

```
highlight-cuts/
├── src/
│   └── highlight_cuts/
│       ├── __init__.py
│       ├── cli.py          # Command-line interface
│       ├── core.py         # Core business logic
│       ├── ffmpeg.py       # FFmpeg wrappers
│       └── utils.py        # Utility functions
├── tests/
│   ├── test_cli.py         # CLI tests
│   ├── test_core.py        # Core logic tests
│   ├── test_ffmpeg.py      # FFmpeg wrapper tests
│   ├── test_utils.py       # Utility tests
│   └── test_integration.py # End-to-end tests
├── docs/                   # Documentation
├── ai/                     # AI context and planning
└── pyproject.toml          # Project configuration
```

## Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check `docs/` for detailed guides

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other contributors

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for contributing to Highlight Cuts! 🎬✨
