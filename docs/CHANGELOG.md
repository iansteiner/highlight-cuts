# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-   **Google Sheets URL support**: `--csv-file` now accepts Google Sheets URLs in addition to local CSV files. The tool automatically converts sharing URLs to CSV export format.
-   `--output-dir` option to specify where generated highlight videos should be saved (defaults to current directory).
-   Automatic creation of output directory if it doesn't exist.
-   **Web Interface**: A FastAPI-based web UI for generating highlights (`src/highlight_cuts/web.py`).
-   **Docker Support**: `Dockerfile` and `docker-compose.yml` for easy deployment.
-   **Testing Infrastructure**: Added `docs/testing_infrastructure.md` and tests for web/docker components.
-   **Documentation**: Added `docs/web_interface.md`.
-   **Comprehensive documentation**:
    -   `CONTRIBUTING.md`: Developer guidelines and workflow
    -   `SECURITY.md`: Security policy and best practices
    -   `docs/TROUBLESHOOTING.md`: Comprehensive troubleshooting guide
    -   `docs/architecture.md`: Technical design and architecture documentation
    -   `docs/FAQ.md`: Frequently asked questions

### Enhanced
-   **Documentation**: Improved project documentation robustness (CONTRIBUTING, SECURITY, etc.).
-   **Enhanced existing documentation**:
    -   `README.md`: Added badges, system requirements, installation instructions, and use cases
    -   `docs/usage.md`: Added detailed installation steps, common workflows, and best practices
    -   `docs/background.md`: Added limitations, comparisons, and technical background sections

## [0.1.0] - 2025-11-23

### Added
-   Initial release of `highlight-cuts` CLI tool.
-   Core logic for parsing time (`HH:MM:SS`, `MM:SS`) and merging overlapping intervals.
-   FFmpeg integration for fast stream copying (`-c copy`).
-   CLI with options: `--input-video`, `--csv-file`, `--game`, `--padding`, `--dry-run`.
-   Comprehensive unit tests with 95% code coverage.
-   Documentation: Usage guide (`docs/usage.md`) and Background (`docs/background.md`).
-   Development tooling: `uv` for dependency management, `ruff` for linting/formatting.
