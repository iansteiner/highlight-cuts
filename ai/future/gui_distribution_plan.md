# Future Plan: GUI & Distribution

## Objective
Create a user-friendly version of `highlight-cuts` for non-technical users on Windows and Mac, avoiding the command line.

## Selected Approach
**Streamlit + PyInstaller**

### 1. The Interface (Streamlit)
Create a local web interface using `streamlit`.
-   **File**: `src/highlight_cuts/app.py`
-   **Features**:
    -   File uploader for CSV and Video.
    -   Dropdown to select "Game" (parsed from CSV).
    -   Slider for "Padding".
    -   "Generate" button.
-   **Mechanism**: The script launches a local web server and opens the user's default browser.

### 2. The Executable (PyInstaller)
Bundle the Python environment and dependencies into a single executable file.
-   **Windows**: `.exe` file.
-   **Mac**: `.app` bundle or Unix executable.

### 3. Handling FFmpeg
Users will not have FFmpeg installed.
-   **Strategy**: Bundle the `ffmpeg` binary *inside* the PyInstaller package.
-   **Code Change**: Update `ffmpeg.py` to check `sys._MEIPASS` (PyInstaller's temp folder) for the binary when running in frozen mode.

### 4. Cross-Platform Build Strategy
PyInstaller cannot cross-compile (e.g., cannot build Windows .exe on Mac).
-   **Solution**: Use **GitHub Actions** to automate builds.
    -   Workflow triggers on tag/push.
    -   Job 1 (Runs on `ubuntu-latest` or `macos-latest`): Builds Mac binary.
    -   Job 2 (Runs on `windows-latest`): Builds Windows binary.
    -   Uploads artifacts as "Releases".

## Implementation Steps
1.  **Prototype UI**: Create `app.py` and verify it works locally with `uv run streamlit run app.py`.
2.  **Update Core**: Modify `ffmpeg.py` to support bundled binaries.
3.  **Local Build**: Test `pyinstaller` build process on the local Mac.
4.  **CI/CD**: Set up GitHub Actions for Windows builds.
