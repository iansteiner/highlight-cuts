# Web Interface

`highlight-cuts` now includes a web interface for easier use, deployed via Docker.

## Features
- **Simple UI**: Select video files, paste Google Sheet URLs, and generate highlights.
- **Dockerized**: Easy to deploy and manage.
- **Background Processing**: Generates clips without blocking the UI.
- **File Management**: Download generated highlights directly from the browser.

## Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose.

## Running the Web Interface

1.  **Start the Service**:
    ```bash
    docker-compose up -d --build
    ```

2.  **Access the UI**:
    Open your browser and navigate to [http://localhost:8000](http://localhost:8000).

3.  **Add Video Files**:
    Place your source video files (e.g., `.mp4`) in the `data/` directory. They will automatically appear in the dropdown menu.

4.  **Generate Highlights**:
    - Select a video file.
    - Paste a Google Sheet URL (must be accessible to "Anyone with the link").
    - Select a Game and Player.
    - Click "Generate Highlights".

5.  **Download**:
    Once processing is complete, the file will appear in the "Generated Files" list for download.

## Configuration
- **Port**: Defaults to `8000`. Change in `docker-compose.yml`.
- **Directories**:
    - `data/`: Source videos (mounted to `/app/data`).
    - `output/`: Generated highlights (mounted to `/app/output`).

## Development
To run the web interface locally without Docker (for development):

```bash
uv run uvicorn highlight_cuts.web:app --reload
```
*Note: You will need to set `HIGHLIGHT_CUTS_DATA_DIR` and `HIGHLIGHT_CUTS_OUTPUT_DIR` environment variables or ensure `data/` and `output/` exist in the current directory.*
