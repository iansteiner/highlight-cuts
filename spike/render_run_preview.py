"""
Render a tracking preview for a saved bulk_test run JSON by overlaying the
tracked box/center onto the source video. Useful to spot-check if tracking
is actually following the player.
"""

import argparse
import json
from pathlib import Path
from typing import Optional

import cv2


def load_run(run_path: Path):
    data = json.loads(run_path.read_text())
    return data


def render(run_json: Path, video_path: Path, output_path: Path, max_frames: Optional[int], show_bbox: bool):
    run = load_run(run_json)
    frame_log = run["frame_log"]

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    limit = min(total_frames, len(frame_log))
    if max_frames is not None:
        limit = min(limit, max_frames)

    for idx in range(limit):
        ret, frame = cap.read()
        if not ret:
            break
        log = frame_log[idx]
        if log.get("tracked") and log.get("bbox"):
            x1, y1, x2, y2 = log["bbox"]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            if show_bbox:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 12, (0, 0, 255), thickness=-1)
            label = f"id={log.get('track_id')}"
            cv2.putText(frame, label, (cx + 10, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            cv2.putText(frame, "NO TRACK", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        writer.write(frame)
        if idx % 100 == 0 and idx > 0:
            print(f"Rendered {idx}/{limit} frames...")

    cap.release()
    writer.release()
    print(f"✅ Preview written to {output_path} ({limit} frames)")


def main():
    parser = argparse.ArgumentParser(description="Render tracking preview for a saved bulk_test run JSON.")
    parser.add_argument("--run", required=True, type=Path, help="Path to run JSON (from spike/bulk_test_output/runs)")
    parser.add_argument("--video", type=Path, help="Path to source video. Defaults to spike/<video name in JSON>")
    parser.add_argument("--out", type=Path, help="Output mp4 path. Defaults to spike/output/<run>.mp4")
    parser.add_argument("--max-frames", type=int, default=None, help="Limit number of frames rendered (optional)")
    parser.add_argument("--show-bbox", action="store_true", help="Also draw bbox rectangle (not just center dot)")
    args = parser.parse_args()

    run = load_run(args.run)
    video_name = run["video"]
    video_path = args.video or Path("spike") / video_name
    output_path = args.out or Path("spike/output") / f"{args.run.stem}_preview.mp4"

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found at {video_path}. Pass --video to override.")

    render(args.run, video_path, output_path, args.max_frames, args.show_bbox)


if __name__ == "__main__":
    main()
