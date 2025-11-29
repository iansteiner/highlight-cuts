# Computer Vision Player Tracking - Implementation Plan

**Date**: 2025-11-28
**Status**: Planning - Awaiting Prototype Validation

## Architecture Overview

### System Design

```
Existing Pipeline (Phase 1 - unchanged):
CSV → merge_intervals() → extract_clips() → concat_clips()
Output: clips/Game_PlayerName.mp4

New CV Pipeline (Phase 2 - new code):
Phase 2a (Interactive):
  clip → detect_players() → user_selects() → track_player() → render_preview()
  Output: previews/clip_001_preview.mp4

Phase 2b (Batch):
  all_approved_clips → track_and_render_high_quality() → batch
  Output: tracked/Game_PlayerName_clip_001.mp4, ...

Phase 2c (Concatenation):
  tracked_clips → concat_tracked_clips()
  Output: final/Game_PlayerName_tracked.mp4
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Interface (web.py)                  │
│  Routes: /cv/detect, /cv/preview, /cv/status, /cv/finalize │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              CV Tracking Module (cv_tracking.py)            │
│  - detect_players()    - track_player()                     │
│  - render_indicator()  - concat_tracked_clips()             │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│  YOLO11 Model   │    │  OpenCV Renderer │
│  (detection &   │    │  (draw indicators)│
│   tracking)     │    │                  │
└─────────────────┘    └──────────────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │  FFmpeg (encoding)  │
         └─────────────────────┘
```

## New Components

### 1. Core CV Module

**File**: `src/highlight_cuts/cv_tracking.py`

**Functions**:

```python
def detect_players(video_path: str, frame_index: int = 0) -> tuple[np.ndarray, List[BoundingBox]]:
    """
    Extract frame and detect all persons (players).

    Args:
        video_path: Path to video file
        frame_index: Frame number to analyze (default: first frame)

    Returns:
        (frame_image, list of bounding boxes with confidence scores)
    """

def track_player(
    video_path: str,
    bbox: BoundingBox,
    tracker: str = 'botsort'
) -> List[TrackingFrame]:
    """
    Track selected player through entire video.

    Args:
        video_path: Path to video file
        bbox: Initial bounding box of target player
        tracker: Tracker type ('botsort', 'bytetrack', etc.)

    Returns:
        List of tracking data per frame (bbox, confidence, etc.)
    """

def render_indicator(
    video_path: str,
    tracking_data: List[TrackingFrame],
    output_path: str,
    quality: str = 'preview',
    indicator_type: str = 'dot'
) -> None:
    """
    Render tracking indicator on video.

    Args:
        video_path: Source video
        tracking_data: Tracking info per frame
        output_path: Output video path
        quality: 'preview' (720p/1080p fast) or 'final' (4K slow)
        indicator_type: 'dot', 'circle', 'glow', etc.
    """

def concat_tracked_clips(
    clip_paths: List[str],
    output_path: str
) -> None:
    """
    Concatenate tracked clips into final video.

    Args:
        clip_paths: List of tracked clip files
        output_path: Final concatenated output
    """
```

### 2. Data Models

**File**: `src/highlight_cuts/models.py`

```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class BoundingBox:
    """Bounding box coordinates."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float = 1.0

    @property
    def center(self) -> Tuple[int, int]:
        """Center point of bbox."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def top_center(self) -> Tuple[int, int]:
        """Top-center point (for head indicator)."""
        return ((self.x1 + self.x2) // 2, self.y1)

@dataclass
class TrackingFrame:
    """Tracking data for a single frame."""
    frame_index: int
    bbox: BoundingBox
    confidence: float
    lost: bool = False  # True if tracking lost this frame

@dataclass
class ClipTrackingState:
    """State for a single clip's tracking workflow."""
    clip_id: str
    source_path: str
    bbox: BoundingBox | None = None
    preview_status: str = 'pending'  # pending, processing, completed, failed
    preview_path: str | None = None
    final_status: str = 'pending'
    final_path: str | None = None
    tracking_data: List[TrackingFrame] | None = None

@dataclass
class SessionState:
    """State for entire CV tracking session."""
    session_id: str
    game: str
    player: str
    clips: List[ClipTrackingState]
    created_at: str
    updated_at: str
```

### 3. Web Routes

**File**: `src/highlight_cuts/web.py` (additions)

```python
from fastapi import BackgroundTasks, UploadFile
from fastapi.responses import FileResponse
import uuid

# In-memory state storage (migrate to database later)
sessions: dict[str, SessionState] = {}

@app.post("/cv/detect")
async def detect_players_endpoint(clip_id: str, session_id: str):
    """
    Detect all players in first frame of clip.

    Returns: {
        "frame_image": "base64_encoded_jpg",
        "detections": [{"bbox": [x1,y1,x2,y2], "confidence": 0.95}, ...]
    }
    """
    session = sessions[session_id]
    clip = next(c for c in session.clips if c.clip_id == clip_id)

    frame, bboxes = detect_players(clip.source_path)

    # Encode frame as base64 for web display
    _, buffer = cv2.imencode('.jpg', frame)
    frame_b64 = base64.b64encode(buffer).decode()

    return {
        "frame_image": frame_b64,
        "detections": [
            {"bbox": [b.x1, b.y1, b.x2, b.y2], "confidence": b.confidence}
            for b in bboxes
        ]
    }

@app.post("/cv/preview")
async def start_preview(
    clip_id: str,
    session_id: str,
    bbox: dict,
    background_tasks: BackgroundTasks
):
    """
    Start preview encoding in background.

    Args:
        bbox: {"x1": int, "y1": int, "x2": int, "y2": int}

    Returns: {"task_id": str, "status": "started"}
    """
    session = sessions[session_id]
    clip = next(c for c in session.clips if c.clip_id == clip_id)

    # Store bbox
    clip.bbox = BoundingBox(**bbox)
    clip.preview_status = 'processing'

    # Start background task
    background_tasks.add_task(
        generate_preview_task,
        session_id, clip_id
    )

    return {"task_id": clip_id, "status": "started"}

async def generate_preview_task(session_id: str, clip_id: str):
    """Background task for preview generation."""
    try:
        session = sessions[session_id]
        clip = next(c for c in session.clips if c.clip_id == clip_id)

        # Track player
        tracking_data = track_player(clip.source_path, clip.bbox)
        clip.tracking_data = tracking_data

        # Render preview
        preview_path = f"outputs/previews/{session_id}_{clip_id}_preview.mp4"
        render_indicator(
            clip.source_path,
            tracking_data,
            preview_path,
            quality='preview'
        )

        clip.preview_path = preview_path
        clip.preview_status = 'completed'

    except Exception as e:
        clip.preview_status = 'failed'
        # Log error

@app.get("/cv/preview/{session_id}/{clip_id}/status")
async def preview_status(session_id: str, clip_id: str):
    """
    Poll for preview generation status.

    Returns: {
        "status": "processing|completed|failed",
        "progress": 0.75,  # Optional
        "preview_url": "/cv/download/preview_abc123.mp4"  # If completed
    }
    """
    session = sessions[session_id]
    clip = next(c for c in session.clips if c.clip_id == clip_id)

    response = {"status": clip.preview_status}

    if clip.preview_status == 'completed':
        response["preview_url"] = f"/cv/download/{session_id}_{clip_id}_preview.mp4"

    return response

@app.post("/cv/preview/{session_id}/{clip_id}/approve")
async def approve_preview(session_id: str, clip_id: str):
    """Mark preview as approved for final encoding."""
    session = sessions[session_id]
    clip = next(c for c in session.clips if c.clip_id == clip_id)
    clip.preview_status = 'approved'
    return {"status": "approved"}

@app.post("/cv/finalize-all")
async def finalize_all(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """
    Start batch high-quality encoding for all approved clips.

    Returns: {"task_id": str, "status": "started", "total_clips": int}
    """
    session = sessions[session_id]
    approved_clips = [c for c in session.clips if c.preview_status == 'approved']

    background_tasks.add_task(
        finalize_all_task,
        session_id
    )

    return {
        "task_id": session_id,
        "status": "started",
        "total_clips": len(approved_clips)
    }

async def finalize_all_task(session_id: str):
    """Background task for batch final encoding."""
    session = sessions[session_id]
    approved_clips = [c for c in session.clips if c.preview_status == 'approved']

    for i, clip in enumerate(approved_clips):
        try:
            clip.final_status = 'processing'

            # Render at high quality
            final_path = f"outputs/tracked/{session_id}_{clip.clip_id}_final.mp4"
            render_indicator(
                clip.source_path,
                clip.tracking_data,
                final_path,
                quality='final'
            )

            clip.final_path = final_path
            clip.final_status = 'completed'

        except Exception as e:
            clip.final_status = 'failed'
            # Log error

    # Concatenate all tracked clips
    final_clips = [c.final_path for c in approved_clips if c.final_status == 'completed']
    concat_output = f"outputs/final/{session.game}_{session.player}_tracked.mp4"
    concat_tracked_clips(final_clips, concat_output)

    session.final_output = concat_output

@app.get("/cv/finalize/{session_id}/status")
async def finalize_status(session_id: str):
    """
    Poll for batch encoding status.

    Returns: {
        "status": "processing|completed|failed",
        "progress": 3,
        "total": 6,
        "final_url": "/cv/download/Game1_JohnDoe_tracked.mp4"
    }
    """
    session = sessions[session_id]
    approved_clips = [c for c in session.clips if c.preview_status == 'approved']
    completed_clips = [c for c in approved_clips if c.final_status == 'completed']

    response = {
        "progress": len(completed_clips),
        "total": len(approved_clips)
    }

    if len(completed_clips) == len(approved_clips):
        response["status"] = "completed"
        response["final_url"] = f"/cv/download/{session.game}_{session.player}_tracked.mp4"
    else:
        response["status"] = "processing"

    return response

@app.get("/cv/download/{filename}")
async def download_file(filename: str):
    """Serve preview/final video files."""
    # Security: validate filename, prevent path traversal
    # Check in outputs/previews/ or outputs/final/
    file_path = find_safe_file_path(filename)
    return FileResponse(file_path, media_type="video/mp4")
```

### 4. Frontend Components

**File**: `src/highlight_cuts/templates/cv_tracking.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Player Tracking - Highlight Cuts</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Player Tracking</h1>

    <!-- Clip Selection -->
    <div id="clip-list">
        <h2>Select Clip to Track</h2>
        <ul id="clips">
            <!-- Populated via JavaScript -->
        </ul>
    </div>

    <!-- Player Detection -->
    <div id="detection-panel" style="display: none;">
        <h2>Select Target Player</h2>
        <canvas id="detection-canvas"></canvas>
        <div id="bbox-list">
            <!-- Populated with clickable player bboxes -->
        </div>
    </div>

    <!-- Preview -->
    <div id="preview-panel" style="display: none;">
        <h2>Preview Tracking</h2>
        <div id="progress">Generating preview...</div>
        <video id="preview-video" controls width="800"></video>
        <div id="preview-actions">
            <button id="approve-btn">Approve</button>
            <button id="retry-btn">Retry</button>
        </div>
    </div>

    <!-- Final Encoding -->
    <div id="finalize-panel" style="display: none;">
        <h2>Generate Final Videos</h2>
        <p>Approved clips: <span id="approved-count">0</span></p>
        <button id="finalize-btn">Start Final Encoding</button>
        <div id="finalize-progress" style="display: none;">
            Progress: <span id="finalize-count">0</span> / <span id="finalize-total">0</span>
        </div>
        <a id="download-link" style="display: none;">Download Final Video</a>
    </div>

    <script src="/static/cv_tracking.js"></script>
</body>
</html>
```

**File**: `src/highlight_cuts/static/cv_tracking.js`

```javascript
// State
let sessionId = null;
let currentClipId = null;
let detections = [];

// Initialize
async function init() {
    // Load session from URL or create new
    const urlParams = new URLSearchParams(window.location.search);
    sessionId = urlParams.get('session') || await createSession();

    loadClips();
}

// Load clips for tracking
async function loadClips() {
    const response = await fetch(`/cv/session/${sessionId}/clips`);
    const data = await response.json();

    const clipsList = document.getElementById('clips');
    clipsList.innerHTML = '';

    data.clips.forEach(clip => {
        const li = document.createElement('li');
        li.textContent = `Clip ${clip.clip_id} - ${clip.preview_status}`;
        li.onclick = () => startDetection(clip.clip_id);
        clipsList.appendChild(li);
    });
}

// Start player detection
async function startDetection(clipId) {
    currentClipId = clipId;

    const response = await fetch('/cv/detect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({clip_id: clipId, session_id: sessionId})
    });

    const data = await response.json();
    detections = data.detections;

    // Display frame with bboxes
    const canvas = document.getElementById('detection-canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        // Draw bboxes
        detections.forEach((det, i) => {
            const [x1, y1, x2, y2] = det.bbox;
            ctx.strokeStyle = 'green';
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2-x1, y2-y1);
            ctx.fillStyle = 'green';
            ctx.fillText(`Player ${i}`, x1, y1-5);
        });
    };
    img.src = 'data:image/jpeg;base64,' + data.frame_image;

    document.getElementById('detection-panel').style.display = 'block';

    // Add click handler for bbox selection
    canvas.onclick = (e) => selectPlayer(e, canvas, detections);
}

// Select player by clicking bbox
function selectPlayer(event, canvas, detections) {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Find bbox containing click
    const selected = detections.find(det => {
        const [x1, y1, x2, y2] = det.bbox;
        return x >= x1 && x <= x2 && y >= y1 && y <= y2;
    });

    if (selected) {
        startPreview(selected.bbox);
    }
}

// Start preview generation
async function startPreview(bbox) {
    const response = await fetch('/cv/preview', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            clip_id: currentClipId,
            session_id: sessionId,
            bbox: {x1: bbox[0], y1: bbox[1], x2: bbox[2], y2: bbox[3]}
        })
    });

    document.getElementById('preview-panel').style.display = 'block';
    document.getElementById('progress').style.display = 'block';

    // Poll for completion
    pollPreviewStatus();
}

// Poll preview status
async function pollPreviewStatus() {
    const response = await fetch(`/cv/preview/${sessionId}/${currentClipId}/status`);
    const data = await response.json();

    if (data.status === 'completed') {
        document.getElementById('progress').style.display = 'none';
        const video = document.getElementById('preview-video');
        video.src = data.preview_url;
        video.style.display = 'block';
        document.getElementById('preview-actions').style.display = 'block';
    } else if (data.status === 'failed') {
        alert('Preview generation failed. Please retry.');
    } else {
        // Still processing, poll again in 2 seconds
        setTimeout(pollPreviewStatus, 2000);
    }
}

// Approve preview
document.getElementById('approve-btn').onclick = async () => {
    await fetch(`/cv/preview/${sessionId}/${currentClipId}/approve`, {
        method: 'POST'
    });

    // Move to next clip
    document.getElementById('preview-panel').style.display = 'none';
    loadClips();
    updateFinalizePanel();
};

// Update finalize panel
async function updateFinalizePanel() {
    const response = await fetch(`/cv/session/${sessionId}/clips`);
    const data = await response.json();
    const approved = data.clips.filter(c => c.preview_status === 'approved');

    document.getElementById('approved-count').textContent = approved.length;

    if (approved.length > 0) {
        document.getElementById('finalize-panel').style.display = 'block';
    }
}

// Start final encoding
document.getElementById('finalize-btn').onclick = async () => {
    const response = await fetch('/cv/finalize-all', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: sessionId})
    });

    const data = await response.json();
    document.getElementById('finalize-total').textContent = data.total_clips;
    document.getElementById('finalize-progress').style.display = 'block';

    pollFinalizeStatus();
};

// Poll finalize status
async function pollFinalizeStatus() {
    const response = await fetch(`/cv/finalize/${sessionId}/status`);
    const data = await response.json();

    document.getElementById('finalize-count').textContent = data.progress;

    if (data.status === 'completed') {
        const link = document.getElementById('download-link');
        link.href = data.final_url;
        link.textContent = 'Download Final Tracked Video';
        link.style.display = 'block';
    } else {
        setTimeout(pollFinalizeStatus, 3000);
    }
}

// Initialize on page load
init();
```

## File Structure

```
src/highlight_cuts/
├── cv_tracking.py          # NEW - CV core logic
├── models.py               # NEW - Data models (BBox, TrackingFrame, etc.)
├── cli.py                  # Unchanged
├── core.py                 # Unchanged
├── ffmpeg.py               # Minor additions (quality presets)
├── utils.py                # Unchanged
├── web.py                  # NEW routes added
├── templates/
│   ├── index.html          # Unchanged
│   └── cv_tracking.html    # NEW - CV workflow UI
└── static/
    ├── style.css           # Minor updates
    └── cv_tracking.js      # NEW - Frontend logic

tests/
├── test_cv_tracking.py     # NEW - CV unit tests
├── test_cv_web.py          # NEW - CV web route tests
└── test_cv_integration.py  # NEW - End-to-end CV tests

outputs/                    # Already exists
├── clips/                  # Phase 1 output (existing)
├── previews/               # NEW - Phase 2a output
├── tracked/                # NEW - Phase 2b output (individual clips)
├── final/                  # NEW - Phase 2c output (concatenated)
└── sessions/               # NEW - JSON state files

spike/                      # NEW - Prototype code
├── cv_prototype.py         # Standalone prototype script
├── test_video.mp4          # User-provided test footage
└── output/                 # Prototype outputs
    ├── first_frame_detections.jpg
    ├── preview_tracked.mp4
    └── metrics.json
```

## Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
# Existing dependencies...
ultralytics = "^8.3.0"      # YOLO11
opencv-python = "^4.10.0"   # Video processing
torch = "^2.5.0"            # PyTorch (CPU version)
torchvision = "^0.20.0"     # Vision utils
numpy = "^2.0.0"            # Array operations
pillow = "^11.0.0"          # Image processing
```

## Implementation Milestones

### Milestone 0: Prototype (CURRENT)
**Goal**: Validate core assumptions

**Tasks**:
- [ ] Create `spike/cv_prototype.py`
- [ ] Test YOLO11 detection on real sports footage
- [ ] Test BoT-SORT tracking through occlusions
- [ ] Measure encoding performance (preview quality)
- [ ] Report findings

**Deliverables**: Prototype script, performance metrics, validation report

**Estimated time**: 1 hour

**Success criteria**:
- Detection accuracy ≥80%
- Tracking success ≥90%
- Preview generation ≤2 min for 15-sec clip

---

### Milestone 1: Core CV Module
**Goal**: Implement pure CV logic (no web integration)

**Tasks**:
- [ ] Create `src/highlight_cuts/cv_tracking.py`
- [ ] Implement `detect_players()`
- [ ] Implement `track_player()` with BoT-SORT
- [ ] Implement `render_indicator()` with quality presets
- [ ] Implement `concat_tracked_clips()`
- [ ] Unit tests in `tests/test_cv_tracking.py`

**Deliverables**: Working CV module with 90%+ test coverage

**Estimated time**: 2-3 days

**Dependencies**: Milestone 0 completion

---

### Milestone 2: Data Models & State Management
**Goal**: Define data structures and session persistence

**Tasks**:
- [ ] Create `src/highlight_cuts/models.py`
- [ ] Define `BoundingBox`, `TrackingFrame`, `ClipTrackingState`, `SessionState`
- [ ] Implement JSON serialization/deserialization
- [ ] Add session storage (in-memory for MVP)
- [ ] Unit tests for models

**Deliverables**: Data models with serialization

**Estimated time**: 1 day

**Dependencies**: None (parallel with M1)

---

### Milestone 3: Web Routes - Detection
**Goal**: Endpoint for player detection

**Tasks**:
- [ ] Add `/cv/detect` route to `web.py`
- [ ] Integrate with `detect_players()` from M1
- [ ] Return base64-encoded frame + bbox list
- [ ] Add error handling
- [ ] Web route tests in `tests/test_cv_web.py`

**Deliverables**: Working detection endpoint

**Estimated time**: 1 day

**Dependencies**: M1, M2

---

### Milestone 4: Web Routes - Preview
**Goal**: Background preview generation with polling

**Tasks**:
- [ ] Add `/cv/preview` route (starts background task)
- [ ] Add `/cv/preview/{id}/status` route (polling)
- [ ] Implement `generate_preview_task()` background function
- [ ] Add `/cv/preview/{id}/approve` route
- [ ] Web route tests

**Deliverables**: Working preview workflow (backend)

**Estimated time**: 2 days

**Dependencies**: M1, M2, M3

---

### Milestone 5: Web Routes - Finalization
**Goal**: Batch high-quality encoding

**Tasks**:
- [ ] Add `/cv/finalize-all` route (starts batch task)
- [ ] Add `/cv/finalize/{id}/status` route (polling)
- [ ] Implement `finalize_all_task()` background function
- [ ] Add `/cv/download/{filename}` route (file serving)
- [ ] Security: prevent path traversal in downloads
- [ ] Web route tests

**Deliverables**: Working batch encoding workflow

**Estimated time**: 2 days

**Dependencies**: M1, M2, M4

---

### Milestone 6: Frontend UI
**Goal**: Complete web interface

**Tasks**:
- [ ] Create `templates/cv_tracking.html`
- [ ] Create `static/cv_tracking.js`
- [ ] Implement clip selection UI
- [ ] Implement detection display with clickable canvas
- [ ] Implement preview player with approve/retry
- [ ] Implement finalize progress display
- [ ] CSS styling
- [ ] Browser testing (Chrome, Firefox, Safari)

**Deliverables**: Complete web UI

**Estimated time**: 3-4 days

**Dependencies**: M3, M4, M5

---

### Milestone 7: Integration Testing
**Goal**: End-to-end validation

**Tasks**:
- [ ] Create integration tests in `tests/test_cv_integration.py`
- [ ] Test full workflow: upload → detect → track → preview → approve → finalize
- [ ] Test with multiple clips
- [ ] Test error scenarios (tracking fails, encoding fails, etc.)
- [ ] Performance benchmarking

**Deliverables**: Integration test suite

**Estimated time**: 2 days

**Dependencies**: M1-M6

---

### Milestone 8: Documentation & Polish
**Goal**: Production-ready release

**Tasks**:
- [ ] Update `docs/user/web_interface.md` with CV tracking instructions
- [ ] Update `docs/dev/architecture.md` with CV components
- [ ] Update `CHANGELOG.md`
- [ ] Update `README.md` with CV features
- [ ] Create session summary in `ai/session_summaries/`
- [ ] Code cleanup (ruff check/format)
- [ ] Docker image with CV dependencies

**Deliverables**: Complete documentation, polished codebase

**Estimated time**: 2-3 days

**Dependencies**: M1-M7

---

## Total Estimated Timeline

- **Milestone 0**: 1 hour
- **Milestones 1-2**: 3-4 days (parallel)
- **Milestones 3-5**: 5 days (sequential)
- **Milestone 6**: 3-4 days
- **Milestone 7**: 2 days
- **Milestone 8**: 2-3 days

**Total: ~15-18 days** of focused development

## Risk Mitigation

### Technical Risks

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| YOLO detection poor on sports footage | M0 validates early | Fine-tune model or use larger variant |
| Tracking fails frequently | Start with BoT-SORT (better than ByteTrack) | Upgrade to custom re-ID model |
| CPU encoding too slow | 720p previews, accept slow final encode | Document GPU requirement, add passthrough |
| Browser video playback issues | Use standard H.264 baseline profile | Provide download-only option |
| State management breaks | Simple JSON files for MVP | Migrate to SQLite/PostgreSQL later |

### Process Risks

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| Scope creep | Strict MVP definition, defer advanced features | Cut features if behind schedule |
| Testing takes longer than expected | Parallel testing during development | Reduce coverage target to 80% |
| Dependencies conflict | Lock versions in pyproject.toml | Use virtual environment isolation |

## Performance Targets

### Preview Generation (Phase 2a)
- **Input**: 15-second clip at 4K @ 60fps (~250 MB)
- **Output**: 15-second preview at 720p @ 30fps (~5 MB)
- **Target time**: 60-120 seconds
- **Breakdown**:
  - Tracking: 20-30 seconds
  - Rendering: 10-20 seconds
  - Encoding: 30-70 seconds

### Final Encoding (Phase 2b)
- **Input**: 15-second clip at 4K @ 60fps
- **Output**: 15-second final at 4K @ 60fps with indicators (~200 MB)
- **Target time**: 5-10 minutes
- **Acceptable**: Background process, user can wait

### Full Session Example
- 1 player with 6 clips (90 seconds total)
- Phase 2a: 6 × 2 min = 12 minutes (interactive)
- Phase 2b: 6 × 7 min = 42 minutes (background)
- Total: ~54 minutes

## Quality Presets

### Preview Quality
```python
PREVIEW_PRESET = {
    'resolution': (1280, 720),  # 720p
    'fps': 30,
    'codec': 'libx264',
    'preset': 'ultrafast',
    'crf': 28,
    'pix_fmt': 'yuv420p'
}
```

### Final Quality
```python
FINAL_PRESET = {
    'resolution': 'source',  # Preserve original
    'fps': 'source',
    'codec': 'libx264',
    'preset': 'medium',
    'crf': 18,
    'pix_fmt': 'yuv420p'
}
```

## Next Steps

1. **Await user-provided test video** (30-second clip)
2. **Run Milestone 0 prototype**
3. **Review prototype results**
4. **Decision point**:
   - If successful → Proceed to M1
   - If issues → Adjust approach (model, tracker, quality targets)
5. **Begin milestone implementation**
