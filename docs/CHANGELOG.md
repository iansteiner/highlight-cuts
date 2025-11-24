# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-   `--output-dir` option to specify where generated highlight videos should be saved (defaults to current directory).
-   Automatic creation of output directory if it doesn't exist.

## [0.1.0] - 2025-11-23

### Added
-   Initial release of `highlight-cuts` CLI tool.
-   Core logic for parsing time (`HH:MM:SS`, `MM:SS`) and merging overlapping intervals.
-   FFmpeg integration for fast stream copying (`-c copy`).
-   CLI with options: `--input-video`, `--csv-file`, `--game`, `--padding`, `--dry-run`.
-   Comprehensive unit tests with 95% code coverage.
-   Documentation: Usage guide (`docs/usage.md`) and Background (`docs/background.md`).
-   Development tooling: `uv` for dependency management, `ruff` for linting/formatting.
