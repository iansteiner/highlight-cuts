# Background & Design

## The Problem
In amateur sports (and professional levels), coaches, players, and parents often have access to full game footage but lack the time or resources to edit individual highlight reels. Manually scrubbing through hours of video to extract 10-15 second clips for specific players is tedious and error-prone.

## The Solution
`highlight-cuts` automates this process. By using a simple CSV file containing timestamps (which can be logged during the game or during a review session), the tool automatically generates separate highlight videos for every player listed.

## Technical Approach

### 1. Stream Copying (No Re-encoding)
The core design philosophy of this tool is **speed** and **quality preservation**.
- **Traditional Editing**: Decodes the video, edits it, and re-encodes it. This takes a long time and degrades quality (generation loss).
- **Highlight Cuts**: Uses FFmpeg's `-c copy` mode. It extracts the raw video/audio streams directly.
    - **Pros**: Blazing fast (seconds instead of minutes/hours), 100% original quality.
    - **Cons**: Cuts must snap to the nearest "keyframe" (i-frame). This means a clip might start a fraction of a second earlier or later than requested.

### 2. Smart Interval Merging
Players often have back-to-back highlights.
- *Example*: A player makes a steal at 1:00 and a layup at 1:05.
- If we ask for clips `1:00-1:05` and `1:04-1:10`, a naive tool would create two files or repeat the action.
- `highlight-cuts` intelligently **merges** these overlapping intervals into a single continuous sequence (`1:00-1:10`) before processing.

### 3. Data-Driven Workflow
The tool is designed to fit into a data-driven workflow:
1.  **Log**: Record timestamps in a spreadsheet (Excel, Google Sheets) during the game.
2.  **Export**: Save as CSV or share the Google Sheets URL directly.
3.  **Process**: Run `highlight-cuts` to generate all videos in one batch.
