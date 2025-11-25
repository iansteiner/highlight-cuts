# Docker Setup Guide

This guide describes how to set up and run the Highlight Cuts application using Docker.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Included with Docker Desktop/Plugin, or install separately.

## Setup Instructions

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd highlight-cuts
    ```

2.  **Create Required Directories**
    The application requires `data` (input) and `output` (results) directories on the host machine.
    ```bash
    mkdir -p data output
    ```

3.  **Build and Run**
    Start the application container in detached mode:
    ```bash
    docker compose up --build -d
    ```

4.  **Verify Installation**
    - Check if the container is running:
      ```bash
      docker compose ps
      ```
    - Access the web interface at [http://localhost:8000](http://localhost:8000).

## Usage

1.  **Add Video Files**
    - Place your source video files (e.g., `.mp4`) in the `data/` directory.
    - Refresh the web page; the files should appear in the "Video File" dropdown.

2.  **Generate Highlights**
    - Select the video file.
    - Enter the Google Sheet URL containing the game logs.
    - Select the Game and Player.
    - Click "Generate Highlights".

3.  **Retrieve Results**
    - Generated highlight videos will appear in the `output/` directory.
    - You can also download them directly from the "Generated Files" section on the web interface.

## Troubleshooting

-   **Build Failures**: Ensure `README.md` exists in the root directory, as it is required for the build.
-   **Permission Issues**: Ensure the user running Docker has read/write permissions for `data` and `output` directories.
-   **Port Conflicts**: If port 8000 is in use, modify the ports mapping in `docker-compose.yml` (e.g., `"8080:8000"`).
