# Docker Enabling Context

**Date**: 2025-11-24
**Purpose**: Context transfer for testing Docker deployment on a new VM.

## Project Status
- **Web Interface**: Fully implemented prototype using FastAPI (`src/highlight_cuts/web.py`).
- **Frontend**: HTML template with TailwindCSS and HTMX (`src/highlight_cuts/templates/index.html`).
- **Infrastructure**: Docker support added (`Dockerfile`, `docker-compose.yml`).
- **Testing**: Unit tests for web endpoints and config verification passed (`tests/test_web.py`, `tests/test_docker_config.py`).

## Instructions for New VM

1.  **Prerequisites**:
    -   Install [Docker](https://docs.docker.com/get-docker/) and Docker Compose.
    -   Ensure `git` is installed if cloning.

2.  **Setup**:
    -   Clone or copy the repository to the new VM.
    -   Ensure the directory structure is preserved.

3.  **Run the Service**:
    ```bash
    docker-compose up --build
    ```
    -   This will build the image `highlight-cuts-web` and start the container on port 8000.

4.  **Verification Steps**:
    -   **Access UI**: Open `http://localhost:8000` in a browser.
    -   **Add Data**: Place a test video (e.g., `.mp4`) in the `data/` directory on the host. It should appear in the dropdown.
    -   **Test Processing**:
        -   Use a public Google Sheet URL (or one with "Anyone with the link" access).
        -   Select a Game and Player.
        -   Click "Generate Highlights".
    -   **Check Output**: Verify the generated file appears in the "Generated Files" list and can be downloaded. The file should also exist in `output/` on the host.

## Key Configuration
-   **Ports**: Maps host `8000` to container `8000`.
-   **Volumes**:
    -   `./data` -> `/app/data` (Source videos)
    -   `./output` -> `/app/output` (Generated clips)
-   **Environment Variables**:
    -   `HIGHLIGHT_CUTS_DATA_DIR`: `/app/data`
    -   `HIGHLIGHT_CUTS_OUTPUT_DIR`: `/app/output`

## Recent Changes
-   **Dependencies**: Added `fastapi`, `uvicorn`, `jinja2`, `python-multipart` (runtime) and `httpx`, `beautifulsoup4` (dev).
-   **Docs**: See `docs/web_interface.md` for detailed usage.
