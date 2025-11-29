# Computer Vision Player Tracking - Prototype Plan

**Date**: 2025-11-28
**Status**: Ready to Execute - Awaiting Test Video

## Objective

Validate core assumptions before building web infrastructure:

1. ✅ **YOLO11 accurately detects players** in sports footage
2. ✅ **BoT-SORT tracking maintains correct player** through typical occlusions
3. ✅ **Performance meets targets** (~1-2 min to generate 15-sec preview on CPU)
4. ✅ **OpenCV rendering produces acceptable visual quality**

## Prototype Scope

### What It Does
- Takes a 30-second test video as input
- Extracts first frame, runs YOLO11 detection
- Saves annotated image showing all detected bounding boxes with labels
- Accepts manual bbox selection (user input or hardcoded)
- Tracks selected player through entire clip
- Renders simple dot indicator above player's head
- Outputs 720p @ 30fps preview video
- Reports performance metrics

### What It Doesn't Do
- ❌ No web UI (pure Python script)
- ❌ No database/state management
- ❌ No high-quality encoding (preview only)
- ❌ No concatenation
- ❌ No error recovery/retry logic

## Deliverables

1. **Script**: `spike/cv_prototype.py`
2. **Output Artifacts**:
   - `spike/output/first_frame_detections.jpg` - Annotated frame with all bboxes
   - `spike/output/preview_tracked.mp4` - 720p preview with dot tracking
   - `spike/output/metrics.json` - Performance data
3. **Report**: Summary of findings (detection accuracy, tracking quality, timing)

## Prerequisites

### User Provides
- [ ] Test video: `spike/test_video.mp4` (30 seconds, typical sports footage)
  - Should contain: Multiple players, some occlusions, camera movement
  - Format: MP4, any resolution (4K preferred for realism)

### Environment
- Python 3.13+
- FFmpeg installed
- uv package manager
- CPU-only (no GPU required for prototype)

## Implementation

### Step 1: Environment Setup

```bash
# Install CV dependencies
uv add ultralytics opencv-python torch torchvision pillow

# Create spike directory
mkdir -p spike/output

# Download YOLO11 model (happens automatically on first run)
# Will download yolo11n.pt (~6 MB) to ~/.ultralytics/
```

### Step 2: Core Functions

**File**: `spike/cv_prototype.py`

#### Detection Module

```python
"""
Prototype for computer vision player tracking.

This script validates:
1. YOLO11 detection accuracy on sports footage
2. BoT-SORT tracking quality through occlusions
3. Encoding performance (720p preview generation)
4. OpenCV rendering visual quality

Usage:
    python spike/cv_prototype.py
"""

from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path
import json
import time
import subprocess


def detect_players(video_path: str, frame_index: int = 0):
    """
    Extract frame and detect all persons (players).

    Args:
        video_path: Path to video file
        frame_index: Frame number to analyze (default: 0)

    Returns:
        (frame_image, list of detection dicts)
        Each detection: {'bbox': [x1,y1,x2,y2], 'confidence': float}
    """
    print(f"\n=== Detecting players in frame {frame_index} ===")

    # Load YOLO model (downloads on first run)
    model = YOLO('yolo11n.pt')

    # Extract specified frame
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Could not read frame {frame_index} from {video_path}")

    # Run detection
    results = model(frame, verbose=False)

    # Filter for persons (class 0 in COCO dataset)
    detections = []
    for box in results[0].boxes:
        if int(box.cls[0]) == 0:  # Person class
            detections.append({
                'bbox': box.xyxy[0].cpu().numpy().tolist(),  # [x1, y1, x2, y2]
                'confidence': float(box.conf[0])
            })

    print(f"Detected {len(detections)} players")
    for i, det in enumerate(detections):
        print(f"  Player {i}: confidence={det['confidence']:.2f}")

    return frame, detections


def annotate_frame(frame, detections):
    """
    Draw bounding boxes on frame with labels.

    Args:
        frame: Image array
        detections: List of detection dicts

    Returns:
        Annotated frame
    """
    annotated = frame.copy()

    for i, det in enumerate(detections):
        x1, y1, x2, y2 = map(int, det['bbox'])
        conf = det['confidence']

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)

        # Draw label background
        label = f"Player {i}: {conf:.2f}"
        (label_w, label_h), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        cv2.rectangle(
            annotated,
            (x1, y1 - label_h - 10),
            (x1 + label_w, y1),
            (0, 255, 0),
            -1
        )

        # Draw label text
        cv2.putText(
            annotated,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            2
        )

    return annotated


def find_closest_box(boxes, target_bbox):
    """
    Find box with closest center to target bbox.

    Simple heuristic for tracking - finds bbox whose center
    is nearest to the target bbox center.

    Args:
        boxes: Array of boxes [[x1,y1,x2,y2], ...]
        target_bbox: Reference box [x1,y1,x2,y2]

    Returns:
        Closest box or None if no boxes
    """
    if len(boxes) == 0:
        return None

    # Calculate target center
    target_center = np.array([
        (target_bbox[0] + target_bbox[2]) / 2,
        (target_bbox[1] + target_bbox[3]) / 2
    ])

    # Find box with minimum distance to target
    min_dist = float('inf')
    best_box = None

    for box in boxes:
        box_center = np.array([
            (box[0] + box[2]) / 2,
            (box[1] + box[3]) / 2
        ])
        dist = np.linalg.norm(box_center - target_center)

        if dist < min_dist:
            min_dist = dist
            best_box = box

    return best_box


def track_player(video_path: str, target_bbox: list, output_path: str):
    """
    Track player from initial bbox through video.
    Renders dot above head in 720p @ 30fps preview.

    Args:
        video_path: Source video
        target_bbox: Initial bounding box [x1, y1, x2, y2]
        output_path: Output preview video path

    Returns:
        Performance metrics dict
    """
    print(f"\n=== Tracking player through video ===")
    print(f"Target bbox: {target_bbox}")

    start_time = time.time()

    # Load YOLO model
    model = YOLO('yolo11n.pt')

    # Get video properties
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print(f"Video: {width}x{height} @ {fps}fps, {total_frames} frames")

    # Output settings (720p @ 30fps)
    out_width = 1280
    out_height = 720
    out_fps = 30

    # Temporary output (raw frames)
    temp_output = output_path.replace('.mp4', '_temp.avi')
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_output, fourcc, out_fps, (out_width, out_height))

    # Run tracking with BoT-SORT
    print("Running YOLO tracking (this may take a while)...")
    tracking_start = time.time()

    frame_idx = 0
    tracked_frames = 0
    frame_skip = max(1, fps // out_fps)  # Sample frames for output fps

    # Track through video
    for result in model.track(
        source=video_path,
        stream=True,
        tracker='botsort.yaml',  # BoT-SORT tracker config
        persist=True,
        verbose=False,
        conf=0.3  # Lower confidence threshold for sports
    ):
        frame = result.orig_img.copy()

        # Find tracked box closest to our target
        best_box = None
        if result.boxes is not None and len(result.boxes) > 0:
            # Filter for persons
            person_boxes = []
            for box in result.boxes:
                if int(box.cls[0]) == 0:  # Person class
                    person_boxes.append(box.xyxy[0].cpu().numpy())

            if len(person_boxes) > 0:
                best_box = find_closest_box(person_boxes, target_bbox)

        # Draw indicator if tracking successful
        if best_box is not None:
            x1, y1, x2, y2 = map(int, best_box)

            # Calculate head position (top-center of bbox, 20px above)
            head_x = (x1 + x2) // 2
            head_y = y1 - 20

            # Draw green dot (8px radius)
            cv2.circle(frame, (head_x, head_y), 8, (0, 255, 0), -1)
            # Draw black outline for visibility
            cv2.circle(frame, (head_x, head_y), 8, (0, 0, 0), 2)

            tracked_frames += 1

        # Write frame to output (with fps conversion)
        if frame_idx % frame_skip == 0:
            frame_resized = cv2.resize(frame, (out_width, out_height))
            out.write(frame_resized)

        frame_idx += 1

        # Progress indicator
        if frame_idx % 30 == 0:
            progress = (frame_idx / total_frames) * 100
            print(f"  Progress: {progress:.1f}% ({frame_idx}/{total_frames} frames)")

    out.release()

    tracking_time = time.time() - tracking_start
    print(f"Tracking complete: {tracking_time:.1f}s")
    print(f"Tracked {tracked_frames}/{total_frames} frames ({tracked_frames/total_frames*100:.1f}%)")

    # Re-encode with FFmpeg for better quality/compatibility
    print("\nRe-encoding with FFmpeg...")
    encode_start = time.time()

    result = subprocess.run([
        'ffmpeg', '-y',
        '-i', temp_output,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        output_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("FFmpeg error:", result.stderr)
        raise RuntimeError("FFmpeg encoding failed")

    # Clean up temp file
    Path(temp_output).unlink()

    encode_time = time.time() - encode_start
    total_time = time.time() - start_time

    print(f"Encoding complete: {encode_time:.1f}s")
    print(f"Total time: {total_time:.1f}s")

    # Calculate metrics
    video_duration = total_frames / fps
    processing_speed = video_duration / total_time

    return {
        'total_frames': total_frames,
        'tracked_frames': tracked_frames,
        'tracking_success_rate': tracked_frames / total_frames,
        'video_duration_sec': video_duration,
        'tracking_time_sec': tracking_time,
        'encoding_time_sec': encode_time,
        'total_time_sec': total_time,
        'processing_speed_x_realtime': processing_speed
    }


def main():
    """Main prototype execution."""
    print("=" * 60)
    print("Computer Vision Player Tracking - Prototype")
    print("=" * 60)

    # Configuration
    video_path = "spike/test_video.mp4"
    output_dir = Path("spike/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify test video exists
    if not Path(video_path).exists():
        print(f"\nERROR: Test video not found at {video_path}")
        print("Please provide a test video and try again.")
        return

    # Phase 1: Player Detection
    print("\n" + "=" * 60)
    print("PHASE 1: Player Detection")
    print("=" * 60)

    frame, detections = detect_players(video_path)

    if len(detections) == 0:
        print("\nERROR: No players detected in first frame")
        print("This could indicate:")
        print("  - No people visible in first frame (try different frame)")
        print("  - YOLO model not suitable for this footage")
        return

    # Save annotated frame
    annotated = annotate_frame(frame, detections)
    detection_img_path = output_dir / "first_frame_detections.jpg"
    cv2.imwrite(str(detection_img_path), annotated)
    print(f"\nSaved annotated frame to {detection_img_path}")

    # Print detections for user selection
    print("\nDetected players:")
    for i, det in enumerate(detections):
        x1, y1, x2, y2 = det['bbox']
        print(f"  [{i}] Confidence: {det['confidence']:.2f}, "
              f"Position: ({int(x1)}, {int(y1)}) to ({int(x2)}, {int(y2)})")

    # Get user input for player selection
    print("\n" + "=" * 60)
    while True:
        try:
            player_idx = int(input(f"Select player to track [0-{len(detections)-1}]: "))
            if 0 <= player_idx < len(detections):
                break
            else:
                print(f"Please enter a number between 0 and {len(detections)-1}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nAborted by user")
            return

    target_bbox = detections[player_idx]['bbox']
    print(f"Selected Player {player_idx}")

    # Phase 2: Tracking
    print("\n" + "=" * 60)
    print("PHASE 2: Player Tracking")
    print("=" * 60)

    preview_path = output_dir / "preview_tracked.mp4"
    metrics = track_player(video_path, target_bbox, str(preview_path))

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Tracking success rate: {metrics['tracking_success_rate']*100:.1f}%")
    print(f"Video duration: {metrics['video_duration_sec']:.1f}s")
    print(f"Tracking time: {metrics['tracking_time_sec']:.1f}s")
    print(f"Encoding time: {metrics['encoding_time_sec']:.1f}s")
    print(f"Total processing time: {metrics['total_time_sec']:.1f}s")
    print(f"Processing speed: {metrics['processing_speed_x_realtime']:.2f}x realtime")

    # Evaluation
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)

    success_criteria = {
        'Detection accuracy': (len(detections) > 0, "✅ Players detected" if len(detections) > 0 else "❌ No players detected"),
        'Tracking success': (metrics['tracking_success_rate'] >= 0.9, f"{'✅' if metrics['tracking_success_rate'] >= 0.9 else '⚠️'} {metrics['tracking_success_rate']*100:.1f}% (target: ≥90%)"),
        'Processing speed': (metrics['processing_speed_x_realtime'] >= 0.5, f"{'✅' if metrics['processing_speed_x_realtime'] >= 0.5 else '⚠️'} {metrics['processing_speed_x_realtime']:.2f}x (target: ≥0.5x)")
    }

    for criterion, (passed, message) in success_criteria.items():
        print(f"{message}")

    # Save metrics
    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\nMetrics saved to {metrics_path}")

    print("\n" + "=" * 60)
    print("OUTPUTS")
    print("=" * 60)
    print(f"Annotated frame: {detection_img_path}")
    print(f"Tracked preview: {preview_path}")
    print(f"Metrics: {metrics_path}")
    print("\nPlease review the preview video to verify visual quality.")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

## Success Criteria

The prototype is **successful** if:

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Detection Accuracy** | ≥80% of visible players detected | Manual count vs. detections |
| **Tracking Success Rate** | ≥90% of frames | `tracked_frames / total_frames` |
| **Processing Speed** | ≥0.5x realtime | `video_duration / total_time` |
| **Visual Quality** | Dot clearly follows player | Manual review of output video |
| **No Crashes** | Script completes successfully | Exit code 0 |

### Evaluation Rubric

**🟢 Excellent (Proceed to implementation)**:
- Detection: 90-100% of players detected
- Tracking: ≥95% success rate
- Speed: ≥0.75x realtime
- Visual: Dot stays centered on player's head

**🟡 Acceptable (Proceed with adjustments)**:
- Detection: 80-90% of players detected
- Tracking: 85-95% success rate
- Speed: 0.5-0.75x realtime
- Visual: Dot mostly follows player, minor drift

**🔴 Needs work (Adjust approach)**:
- Detection: <80% of players detected → Try larger model (yolo11s.pt)
- Tracking: <85% success rate → Research alternative trackers
- Speed: <0.5x realtime → Lower preview resolution (480p) or require GPU
- Visual: Dot frequently lost/wrong player → Improve tracking algorithm

## Potential Issues & Mitigations

| Issue | Likelihood | Mitigation |
|-------|-----------|------------|
| **Low detection accuracy** | Medium | Try `yolo11s.pt` (larger, more accurate) or lower confidence threshold |
| **Tracking switches to wrong player** | High | Expected with occlusions - document for future upgrade |
| **Processing too slow** | Medium | Drop to 480p preview or acknowledge GPU needed |
| **Model download fails** | Low | Manual download from Ultralytics, place in `~/.ultralytics/` |
| **FFmpeg encoding fails** | Low | Check FFmpeg installation, try different codec |
| **Out of memory** | Low | Reduce batch size in YOLO (default should be fine) |
| **Wrong player selected** | Medium | Re-run with different player index |

## Timeline

- **Environment setup**: 5 minutes
- **Script implementation**: 15 minutes (copy from plan)
- **Test execution**: 5-10 minutes (depends on video length)
- **Review outputs**: 10 minutes (watch preview, check metrics)
- **Report findings**: 10 minutes

**Total: ~45-60 minutes**

## Outputs & Next Steps

### After Prototype Completion

1. **Review Outputs**:
   - Watch `spike/output/preview_tracked.mp4` - Does dot follow player?
   - Check `spike/output/first_frame_detections.jpg` - Are all players detected?
   - Read `spike/output/metrics.json` - Performance acceptable?

2. **Decision Points**:

   **If all success criteria met**:
   → ✅ Proceed to Milestone 1 (Core CV Module implementation)

   **If detection is poor (<80% accuracy)**:
   → Try larger model: Change `yolo11n.pt` to `yolo11s.pt` or `yolo11m.pt`
   → Adjust confidence threshold: `model(..., conf=0.2)` (lower = more detections)
   → Re-run prototype

   **If tracking fails frequently (<85% success)**:
   → Research alternative trackers (DeepSORT, custom re-ID)
   → Consider fine-tuning YOLO on sports footage
   → May need to adjust MVP expectations

   **If too slow (<0.5x realtime)**:
   → Lower preview resolution to 480p in `track_player()`
   → Accept slower performance for CPU-only
   → Document GPU requirement for production use

   **If visual quality poor**:
   → Adjust indicator size/color/position
   → Try different rendering approach (glow instead of dot)
   → Increase preview resolution to 1080p

3. **Report Template**:

```markdown
# Prototype Results - [Date]

## Test Video
- Duration: X seconds
- Resolution: AxB @ Cfps
- Content: [Brief description - e.g., "Soccer game, 10 players visible, some occlusions"]

## Detection Results
- Players detected: X / Y visible (Z%)
- False positives: X (non-players detected)
- Average confidence: X%

## Tracking Results
- Success rate: X%
- Frames tracked: X / Y
- Lost tracking: [Description of when/why tracking failed]

## Performance
- Total processing time: Xs
- Processing speed: Xx realtime
- Tracking time: Xs
- Encoding time: Xs

## Visual Quality
[Subjective assessment - does dot follow player smoothly?]

## Evaluation
- Detection: ✅/⚠️/❌
- Tracking: ✅/⚠️/❌
- Performance: ✅/⚠️/❌
- Visual: ✅/⚠️/❌

## Recommendation
[Proceed / Adjust approach / Need more testing]

## Next Steps
[Specific actions based on results]
```

## Questions for User

Before executing the prototype:

1. **Test video location**: Please place test video at `spike/test_video.mp4`
   - Recommended: 30-second clip from actual game footage
   - Should show: Multiple players, some occlusions, typical camera movement

2. **Player selection method**: For the prototype, prefer:
   - **Option A** (Recommended): Interactive - script shows detections, you type player index
   - **Option B**: Auto-select first detected player (no interaction)
   - **Option C**: Hardcode specific bbox coordinates in script

3. **Multiple test runs**: Should I prepare the script to support:
   - Single run (manual re-execution if needed)
   - Loop for testing multiple players
   - Batch mode for multiple videos

**Current plan: Option A (interactive), single run. User can re-execute for additional tests.**

## Ready to Execute

Once test video is provided at `spike/test_video.mp4`, run:

```bash
# Create and run prototype
python spike/cv_prototype.py
```

Expected output:
```
==========================================================
Computer Vision Player Tracking - Prototype
==========================================================

=== Detecting players in frame 0 ===
Detected 8 players
  Player 0: confidence=0.92
  Player 1: confidence=0.88
  ...

Saved annotated frame to spike/output/first_frame_detections.jpg

Detected players:
  [0] Confidence: 0.92, Position: (100, 150) to (200, 400)
  ...

Select player to track [0-7]: 2

=== Tracking player through video ===
Running YOLO tracking...
  Progress: 33.3% (300/900 frames)
  ...
Tracking complete: 45.2s

Re-encoding with FFmpeg...
Encoding complete: 12.3s
Total time: 57.5s

==========================================================
RESULTS
==========================================================
Tracking success rate: 94.2%
Processing speed: 0.52x realtime
...

OUTPUTS:
  Annotated frame: spike/output/first_frame_detections.jpg
  Tracked preview: spike/output/preview_tracked.mp4
  Metrics: spike/output/metrics.json
```

**Waiting for test video to proceed.**
