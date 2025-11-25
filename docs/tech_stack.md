# Technology Stack

This document outlines the technology stack used in the Highlight Cuts project and the reasoning behind these choices.

## Core Backend

*   **Language:** **Python 3.13+**
    *   *Why:* Python offers a vast ecosystem for data manipulation and video processing integration. It is the primary language for the core logic of slicing and dicing video clips.
*   **Web Framework:** **FastAPI**
    *   *Why:* FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+. It provides automatic validation, excellent editor support (autocompletion), and is easy to use for both API endpoints and serving HTML templates. Its async capabilities are beneficial for handling web requests efficiently.
*   **Server:** **Uvicorn**
    *   *Why:* A lightning-fast ASGI server implementation, required to run FastAPI applications.

## Frontend

*   **Templating:** **Jinja2**
    *   *Why:* The standard templating engine for Python web frameworks. It allows for server-side rendering of HTML, which is simple and effective for this application.
*   **Interactivity:** **HTMX**
    *   *Why:* HTMX allows us to access AJAX, CSS Transitions, WebSockets and Server Sent Events directly in HTML, using attributes. It enables a dynamic, Single Page Application (SPA) feel without the complexity and build steps of a full JavaScript framework (like React or Vue). This keeps the codebase simple and Python-centric.
*   **Styling:** **Tailwind CSS**
    *   *Why:* A utility-first CSS framework that allows for rapid UI development directly in the HTML markup. It ensures a modern and consistent look with minimal custom CSS.

## Data & Video Processing

*   **Video Processing:** **FFmpeg**
    *   *Why:* The industry standard for recording, converting, and streaming audio and video. It is the engine under the hood that performs the actual cutting and concatenation of video clips.
*   **Data Manipulation:** **Pandas**
    *   *Why:* A powerful data analysis and manipulation library. It is used to parse the Google Sheets/CSV data containing game logs and timestamps, making it easy to filter and organize clips by player and game.

## Development & Deployment

*   **Dependency Management:** **uv**
    *   *Why:* An extremely fast Python package installer and resolver. It replaces `pip` and `pip-tools` for a faster and more reliable development workflow.
*   **Build System:** **Hatchling**
    *   *Why:* A modern, extensible build backend for Python projects, compliant with PEP 517.
*   **Containerization:** **Docker**
    *   *Why:* Ensures a consistent environment across different machines. This is particularly important for dependencies like FFmpeg, which can have varying versions and configurations on different OSs.
*   **Testing:** **Pytest**
    *   *Why:* The most popular and feature-rich testing framework for Python.
*   **Linting/Formatting:** **Ruff**
    *   *Why:* An extremely fast Python linter and formatter, written in Rust. It replaces multiple tools (Flake8, Black, isort) with a single, faster tool.
