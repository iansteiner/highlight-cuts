"""
Prototype for computer vision player tracking.

This script validates:
1. YOLO11 detection accuracy on sports footage
2. BoT-SORT tracking quality through occlusions
3. Encoding performance (720p preview generation)
4. OpenCV rendering visual quality

Usage:
    python spike/cv_prototype.py

Prerequisites:
    - Test video at spike/test_video.mp4
    - Dependencies: uv add ultralytics opencv-python torch torchvision pillow
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
    # Using yolo11s (small) for better accuracy in challenging conditions
    model = YOLO("yolo11s.pt")

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
            detections.append(
                {
                    "bbox": box.xyxy[0].cpu().numpy().tolist(),  # [x1, y1, x2, y2]
                    "confidence": float(box.conf[0]),
                }
            )

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
        x1, y1, x2, y2 = map(int, det["bbox"])
        conf = det["confidence"]

        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)

        # Draw label background
        label = f"Player {i}: {conf:.2f}"
        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(
            annotated, (x1, y1 - label_h - 10), (x1 + label_w, y1), (0, 255, 0), -1
        )

        # Draw label text
        cv2.putText(
            annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
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
    target_center = np.array(
        [(target_bbox[0] + target_bbox[2]) / 2, (target_bbox[1] + target_bbox[3]) / 2]
    )

    # Find box with minimum distance to target
    min_dist = float("inf")
    best_box = None

    for box in boxes:
        box_center = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
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
    print("\n=== Tracking player through video ===")
    print(f"Target bbox: {target_bbox}")

    start_time = time.time()

    # Load YOLO model
    # Using yolo11s (small) for better accuracy in challenging conditions
    model = YOLO("yolo11s.pt")

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
    temp_output = output_path.replace(".mp4", "_temp.avi")
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(temp_output, fourcc, out_fps, (out_width, out_height))

    # Run tracking with BoT-SORT
    print("Running YOLO tracking (this may take a while)...")
    tracking_start = time.time()

    frame_idx = 0
    tracked_frames = 0
    frame_skip = max(1, fps // out_fps)  # Sample frames for output fps
    target_track_id = None  # Will be set on first frame

    # Smoothing for dot position (reduces flickering)
    smoothed_x = None
    smoothed_y = None
    smoothing_factor = 0.3  # 0 = no smoothing, 1 = no memory

    # Track through video
    for result in model.track(
        source=video_path,
        stream=True,
        tracker="botsort.yaml",  # BoT-SORT tracker config
        persist=True,
        verbose=False,
        conf=0.2,  # Lower confidence threshold for challenging backgrounds
    ):
        frame = result.orig_img.copy()

        # Find tracked box using YOLO tracking IDs
        best_box = None
        if (
            result.boxes is not None
            and len(result.boxes) > 0
            and result.boxes.id is not None
        ):
            # On first frame, identify which tracking ID corresponds to our target player
            if target_track_id is None and frame_idx == 0:
                # Find person bbox closest to target on first frame
                person_boxes_with_ids = []
                for box in result.boxes:
                    if int(box.cls[0]) == 0:  # Person class
                        person_boxes_with_ids.append(
                            {
                                "bbox": box.xyxy[0].cpu().numpy(),
                                "track_id": int(box.id[0]),
                            }
                        )

                if len(person_boxes_with_ids) > 0:
                    # Find closest to initial target
                    person_boxes = [p["bbox"] for p in person_boxes_with_ids]
                    closest_bbox = find_closest_box(person_boxes, target_bbox)

                    # Get tracking ID for this bbox
                    for p in person_boxes_with_ids:
                        if np.allclose(p["bbox"], closest_bbox):
                            target_track_id = p["track_id"]
                            best_box = closest_bbox
                            print(f"Locked onto tracking ID: {target_track_id}")
                            break

            # On subsequent frames, follow the same tracking ID
            elif target_track_id is not None:
                for box in result.boxes:
                    if int(box.cls[0]) == 0 and int(box.id[0]) == target_track_id:
                        best_box = box.xyxy[0].cpu().numpy()
                        break

        # Draw indicator if tracking successful
        if best_box is not None:
            x1, y1, x2, y2 = map(int, best_box)

            # Draw full bounding box for debugging
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # Draw tracking ID label
            label = f"ID: {target_track_id}"
            cv2.putText(
                frame, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2
            )

            # Calculate head position (top-center of bbox, 20px above)
            head_x = (x1 + x2) // 2
            head_y = y1 - 20

            # Apply exponential moving average smoothing to reduce flickering
            if smoothed_x is None:
                smoothed_x = head_x
                smoothed_y = head_y
            else:
                smoothed_x = (
                    smoothing_factor * head_x + (1 - smoothing_factor) * smoothed_x
                )
                smoothed_y = (
                    smoothing_factor * head_y + (1 - smoothing_factor) * smoothed_y
                )

            # Draw green dot (8px radius) at smoothed position
            cv2.circle(frame, (int(smoothed_x), int(smoothed_y)), 12, (0, 255, 0), -1)
            # Draw black outline for visibility
            cv2.circle(frame, (int(smoothed_x), int(smoothed_y)), 12, (0, 0, 0), 2)

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
    print(
        f"Tracked {tracked_frames}/{total_frames} frames ({tracked_frames / total_frames * 100:.1f}%)"
    )

    # Re-encode with FFmpeg for better quality/compatibility
    print("\nRe-encoding with FFmpeg...")
    encode_start = time.time()

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            temp_output,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ],
        capture_output=True,
        text=True,
    )

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
        "total_frames": total_frames,
        "tracked_frames": tracked_frames,
        "tracking_success_rate": tracked_frames / total_frames,
        "video_duration_sec": video_duration,
        "tracking_time_sec": tracking_time,
        "encoding_time_sec": encode_time,
        "total_time_sec": total_time,
        "processing_speed_x_realtime": processing_speed,
    }


def main():
    """Main prototype execution."""
    print("=" * 60)
    print("Computer Vision Player Tracking - Prototype")
    print("=" * 60)

    # Configuration
    output_dir = Path("spike/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find test video (check for both .mp4 and .mov)
    video_path = None
    for ext in [".mp4", ".mov", ".MOV", ".MP4"]:
        candidate = Path(f"spike/test_video{ext}")
        if candidate.exists():
            video_path = str(candidate)
            break

    if video_path is None:
        print("\nERROR: Test video not found")
        print("Please provide a test video at one of:")
        print("  - spike/test_video.mp4")
        print("  - spike/test_video.mov")
        return

    print(f"Using test video: {video_path}")

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
        x1, y1, x2, y2 = det["bbox"]
        print(
            f"  [{i}] Confidence: {det['confidence']:.2f}, "
            f"Position: ({int(x1)}, {int(y1)}) to ({int(x2)}, {int(y2)})"
        )

    # Get user input for player selection
    print("\n" + "=" * 60)
    while True:
        try:
            player_idx = int(
                input(f"Select player to track [0-{len(detections) - 1}]: ")
            )
            if 0 <= player_idx < len(detections):
                break
            else:
                print(f"Please enter a number between 0 and {len(detections) - 1}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nAborted by user")
            return

    target_bbox = detections[player_idx]["bbox"]
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
    print(f"Tracking success rate: {metrics['tracking_success_rate'] * 100:.1f}%")
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
        "Detection accuracy": (
            len(detections) > 0,
            "✅ Players detected" if len(detections) > 0 else "❌ No players detected",
        ),
        "Tracking success": (
            metrics["tracking_success_rate"] >= 0.9,
            f"{'✅' if metrics['tracking_success_rate'] >= 0.9 else '⚠️'} {metrics['tracking_success_rate'] * 100:.1f}% (target: ≥90%)",
        ),
        "Processing speed": (
            metrics["processing_speed_x_realtime"] >= 0.5,
            f"{'✅' if metrics['processing_speed_x_realtime'] >= 0.5 else '⚠️'} {metrics['processing_speed_x_realtime']:.2f}x (target: ≥0.5x)",
        ),
    }

    for criterion, (passed, message) in success_criteria.items():
        print(f"{message}")

    # Save metrics
    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w") as f:
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
