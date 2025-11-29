"""
Bulk testing framework for CV player tracking.

Tests multiple combinations of:
- YOLO models (nano, small, medium)
- Trackers (BoT-SORT, ByteTrack) with parameter sweeps
- Confidence thresholds
- Players (top N detected)
- Videos

Generates comprehensive metrics for analysis.
"""

from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path
import json
import time
import csv
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import sys
import tempfile
import yaml
import os
from datetime import datetime
from numbers import Number
import torch
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
import math

try:
    import psutil
except ImportError:  # psutil is optional; skip memory metrics if unavailable
    psutil = None


@dataclass
class TrackingFrame:
    """Per-frame tracking data."""
    frame: int
    time_sec: float
    tracked: bool
    bbox: Optional[List[float]]
    confidence: Optional[float]
    track_id: Optional[int]


@dataclass
class TestConfig:
    """Configuration for a single test run."""
    video_path: str
    model_name: str
    tracker: str
    tracker_params: Dict[str, float | int | bool]
    conf_threshold: float
    player_idx: int
    run_id: str


@dataclass
class TestResults:
    """Results from a single test run."""
    # Metadata
    run_id: str
    video: str
    model: str
    tracker: str
    tracker_params: Dict[str, float | int | bool]
    conf: float
    player_idx: int
    run_start_ts: str
    run_end_ts: str
    run_elapsed_sec: float

    # Primary metrics (for recruiter use case: first 5-10 seconds)
    continuous_tracking_from_start_sec: float
    first_loss_time_sec: Optional[float]
    success_first_5sec: bool
    success_first_10sec: bool

    # Overall metrics
    total_frames: int
    tracked_frames: int
    success_rate: float
    max_consecutive_loss_frames: int
    max_consecutive_loss_sec: float
    max_consecutive_tracked_frames: int
    longest_tracked_streak_sec: float
    id_switches: int

    # Quality indicators
    avg_confidence: float
    bbox_variance: float
    bbox_size_variance: float
    position_jumps: int
    max_center_drift_px: float
    median_center_drift_px: float
    center_drift_ratio: float
    suspicious_frames: int
    likely_wrong_player: bool
    quality_score: int

    # Performance
    processing_time_sec: float
    processing_speed_x_realtime: float
    avg_frame_latency_sec: float
    peak_rss_mb: Optional[float]
    detection_count_first_frame: int
    target_initial_confidence: Optional[float]

    # Frame-by-frame log (for detailed analysis)
    frame_log: List[TrackingFrame]


def find_closest_box(boxes, target_bbox):
    """Find box with closest center to target bbox."""
    if len(boxes) == 0:
        return None

    target_center = np.array([
        (target_bbox[0] + target_bbox[2]) / 2,
        (target_bbox[1] + target_bbox[3]) / 2
    ])

    min_dist = float('inf')
    best_box = None

    for box in boxes:
        box_center = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
        dist = np.linalg.norm(box_center - target_center)

        if dist < min_dist:
            min_dist = dist
            best_box = box

    return best_box


def summarize_frame_log(frame_log: List["TrackingFrame"], fps: int) -> Dict[str, float | int | None]:
    """
    Compute streak and loss metrics from a frame log.

    Returns a dict with:
        continuous_from_start_frames, continuous_from_start_sec,
        first_loss_time_sec, max_consecutive_loss_frames,
        max_consecutive_loss_sec, max_consecutive_tracked_frames,
        longest_tracked_streak_sec
    """
    if fps <= 0:
        raise ValueError("fps must be positive")

    continuous_from_start_frames = 0
    for frame in frame_log:
        if frame.tracked:
            continuous_from_start_frames += 1
        else:
            break
    continuous_from_start_sec = continuous_from_start_frames / fps

    first_loss_time_sec = None
    for frame in frame_log:
        if not frame.tracked:
            first_loss_time_sec = frame.time_sec
            break

    max_consecutive_loss = 0
    current_loss_streak = 0
    max_consecutive_tracked = 0
    current_tracked_streak = 0

    for frame in frame_log:
        if frame.tracked:
            current_tracked_streak += 1
            current_loss_streak = 0
        else:
            current_loss_streak += 1
            current_tracked_streak = 0

        max_consecutive_loss = max(max_consecutive_loss, current_loss_streak)
        max_consecutive_tracked = max(max_consecutive_tracked, current_tracked_streak)

    return {
        "continuous_from_start_frames": continuous_from_start_frames,
        "continuous_from_start_sec": continuous_from_start_sec,
        "first_loss_time_sec": first_loss_time_sec,
        "max_consecutive_loss_frames": max_consecutive_loss,
        "max_consecutive_loss_sec": max_consecutive_loss / fps,
        "max_consecutive_tracked_frames": max_consecutive_tracked,
        "longest_tracked_streak_sec": max_consecutive_tracked / fps,
    }


def detect_players(video_path: str, model_name: str, frame_index: int = 0):
    """Detect all players in first frame."""
    model = YOLO(f'{model_name}.pt')

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Could not read frame {frame_index} from {video_path}")

    results = model(frame, verbose=False)

    detections = []
    for box in results[0].boxes:
        if int(box.cls[0]) == 0:  # Person class
            detections.append({
                'bbox': box.xyxy[0].cpu().numpy().tolist(),
                'confidence': float(box.conf[0])
            })

    return detections


def get_tracker_cfg_path(tracker: str) -> Path:
    """Return path to the default tracker YAML shipped with ultralytics."""
    tracker_name = tracker.lower()
    import ultralytics  # Imported here to avoid circular imports in type checkers

    pkg_root = Path(ultralytics.__file__).parent
    cfg_path = pkg_root / 'cfg' / 'trackers' / f'{tracker_name}.yaml'
    if not cfg_path.exists():
        raise FileNotFoundError(f"Tracker config not found for {tracker}")
    return cfg_path


def build_tracker_config(tracker: str, overrides: Dict[str, float | int | bool]) -> str:
    """
    Create a temporary tracker YAML with overrides applied.

    Args:
        tracker: Tracker name (botsort or bytetrack)
        overrides: Dict of tracker-specific parameters to override

    Returns:
        Path to temporary YAML file
    """
    base_cfg_path = get_tracker_cfg_path(tracker)
    with open(base_cfg_path, 'r') as f:
        cfg = yaml.safe_load(f)

    for key, value in overrides.items():
        if value is not None:
            cfg[key] = value

    tmp = tempfile.NamedTemporaryFile(prefix=f"{tracker}_", suffix=".yaml", delete=False, mode='w')
    yaml.safe_dump(cfg, tmp)
    tmp_path = tmp.name
    tmp.close()
    return tmp_path


def ensure_jsonable(obj):
    """Recursively convert numpy/Path/bool-ish objects to JSON-serializable Python types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, np.generic):  # numpy scalar types
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Number):  # numpy numeric types
        return obj.item()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): ensure_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [ensure_jsonable(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return ensure_jsonable(obj.__dict__)
    return str(obj)


def run_single_test(config: TestConfig) -> TestResults:
    """Run a single tracking test and collect all metrics."""
    run_start = time.time()
    run_start_ts = datetime.utcnow().isoformat() + "Z"

    print(f"\n[{config.run_id}] Starting test at {time.strftime('%H:%M:%S')}...")
    print(f"  Video: {Path(config.video_path).name}")
    print(f"  Model: {config.model_name}, Conf: {config.conf_threshold}")
    print(f"  Tracker: {config.tracker}, Params: {config.tracker_params}")
    print(f"  Player: {config.player_idx}")

    start_time = time.time()

    # Load model
    model = YOLO(f'{config.model_name}.pt')

    # Get video properties
    cap = cv2.VideoCapture(config.video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    video_duration_sec = total_frames / fps
    frame_diag = math.hypot(width, height) if width and height else 1.0

    # Get initial detection
    detections = detect_players(config.video_path, config.model_name)
    if config.player_idx >= len(detections):
        raise ValueError(f"Player {config.player_idx} not found (only {len(detections)} detected)")

    target_bbox = detections[config.player_idx]['bbox']
    target_confidence = detections[config.player_idx]['confidence']
    detection_count_first_frame = len(detections)

    tracker_cfg_path = build_tracker_config(config.tracker, config.tracker_params)

    # Track through video
    frame_log = []
    target_track_id = None
    tracked_frames = 0

    prev_bbox = None
    position_jumps = 0
    confidences = []
    bbox_centers = []
    bbox_sizes = []
    center_drifts = []
    id_switches = 0
    prev_track_id = None
    initial_center = [
        (target_bbox[0] + target_bbox[2]) / 2,
        (target_bbox[1] + target_bbox[3]) / 2,
    ]

    try:
        for result in model.track(
            source=config.video_path,
            stream=True,
            tracker=tracker_cfg_path,
            persist=True,
            verbose=False,
            conf=config.conf_threshold
        ):
            frame_idx = len(frame_log)
            time_sec = frame_idx / fps

            # Find tracked box using YOLO tracking IDs
            best_box = None
            best_conf = None
            best_id = None

            if result.boxes is not None and len(result.boxes) > 0 and result.boxes.id is not None:
                person_boxes_with_ids = []
                for box in result.boxes:
                    if int(box.cls[0]) == 0:
                        person_boxes_with_ids.append({
                            'bbox': box.xyxy[0].cpu().numpy(),
                            'track_id': int(box.id[0]),
                            'conf': float(box.conf[0])
                        })

                if target_track_id is None and len(person_boxes_with_ids) > 0:
                    # On first frame, pick the closest bbox to the user-selected target
                    person_boxes = [p['bbox'] for p in person_boxes_with_ids]
                    closest_bbox = find_closest_box(person_boxes, target_bbox)

                    for p in person_boxes_with_ids:
                        if np.allclose(p['bbox'], closest_bbox):
                            target_track_id = p['track_id']
                            best_box = closest_bbox
                            best_conf = p['conf']
                            best_id = target_track_id
                            break
                elif target_track_id is not None:
                    # Follow the same track ID on subsequent frames
                    for p in person_boxes_with_ids:
                        if p['track_id'] == target_track_id:
                            best_box = p['bbox']
                            best_conf = p['conf']
                            best_id = target_track_id
                            break

            # Record frame data
            if best_box is not None:
                bbox_list = best_box.tolist()
                tracked_frames += 1
                confidences.append(best_conf)
                if prev_track_id is not None and best_id is not None and best_id != prev_track_id:
                    id_switches += 1
                if best_id is not None:
                    prev_track_id = best_id

                # Calculate bbox center and size
                center = [(bbox_list[0] + bbox_list[2]) / 2, (bbox_list[1] + bbox_list[3]) / 2]
                size = (bbox_list[2] - bbox_list[0]) * (bbox_list[3] - bbox_list[1])
                bbox_centers.append(center)
                bbox_sizes.append(size)
                drift = float(np.linalg.norm(np.array(center) - np.array(initial_center)))
                center_drifts.append(drift)

                # Detect position jumps
                if prev_bbox is not None:
                    prev_center = [(prev_bbox[0] + prev_bbox[2]) / 2, (prev_bbox[1] + prev_bbox[3]) / 2]
                    jump_dist = np.linalg.norm(np.array(center) - np.array(prev_center))
                    if jump_dist > 200:  # >200px jump between frames
                        position_jumps += 1

                prev_bbox = bbox_list

                frame_log.append(TrackingFrame(
                    frame=frame_idx,
                    time_sec=time_sec,
                    tracked=True,
                    bbox=bbox_list,
                    confidence=best_conf,
                    track_id=best_id
                ))
            else:
                frame_log.append(TrackingFrame(
                    frame=frame_idx,
                    time_sec=time_sec,
                    tracked=False,
                    bbox=None,
                    confidence=None,
                    track_id=None
                ))
                prev_bbox = None
    finally:
        # Clean up temp tracker config
        try:
            Path(tracker_cfg_path).unlink(missing_ok=True)
        except Exception:
            pass

    processing_time = time.time() - start_time
    run_end = time.time()
    run_end_ts = datetime.utcnow().isoformat() + "Z"
    run_elapsed_sec = run_end - run_start

    # Calculate metrics
    success_rate = tracked_frames / len(frame_log) if len(frame_log) > 0 else 0.0
    avg_confidence = np.mean(confidences) if confidences else 0.0

    # Bbox variance (stability)
    bbox_variance = 0.0
    if len(bbox_centers) > 1:
        centers_array = np.array(bbox_centers)
        bbox_variance = float(np.var(centers_array[:, 0]) + np.var(centers_array[:, 1]))

    # Bbox size variance
    bbox_size_variance = float(np.var(bbox_sizes)) if len(bbox_sizes) > 1 else 0.0

    streaks = summarize_frame_log(frame_log, fps)
    continuous_from_start_sec = streaks["continuous_from_start_sec"]
    first_loss_time_sec = streaks["first_loss_time_sec"]
    max_consecutive_loss = streaks["max_consecutive_loss_frames"]
    max_consecutive_loss_sec = streaks["max_consecutive_loss_sec"]
    max_consecutive_tracked_frames = streaks["max_consecutive_tracked_frames"]
    longest_tracked_streak_sec = streaks["longest_tracked_streak_sec"]

    # Success at 5 and 10 seconds
    success_first_5sec = continuous_from_start_sec >= 5.0
    success_first_10sec = continuous_from_start_sec >= 10.0

    # Quality indicators
    suspicious_frames = position_jumps
    max_center_drift_px = max(center_drifts) if center_drifts else 0.0
    median_center_drift_px = float(np.median(center_drifts)) if center_drifts else 0.0
    center_drift_ratio = max_center_drift_px / frame_diag if frame_diag else 0.0
    # Flag frozen tracks (no movement across frames) which likely indicate bad tracking or static detections
    frozen_track = len(frame_log) > 30 and max_center_drift_px < 1.0

    # Heuristic: likely wrong player if lots of jumps or high variance
    likely_wrong_player = (
        position_jumps > 5 or
        bbox_variance > 10000 or
        (len(bbox_sizes) > 1 and bbox_size_variance / np.mean(bbox_sizes) > 0.5) or
        center_drift_ratio > 0.25 or
        (frame_diag > 0 and median_center_drift_px / frame_diag > 0.15) or
        frozen_track
    )

    # Quality score (0-100)
    quality_score = 100
    quality_score -= min(position_jumps * 5, 30)  # -5 per jump, max -30
    quality_score -= min(int(bbox_variance / 100), 30)  # Variance penalty, max -30
    quality_score -= min(int(center_drift_ratio * 200), 40)  # Penalize large drifts
    if frozen_track:
        quality_score -= 30  # Heavily penalize if the track never moves
    if likely_wrong_player:
        quality_score -= 40
    quality_score = max(0, quality_score)

    processing_speed = video_duration_sec / processing_time if processing_time > 0 else 0.0
    avg_frame_latency_sec = processing_time / len(frame_log) if len(frame_log) > 0 else 0.0

    peak_rss_mb = None
    if psutil is not None:
        try:
            peak_rss_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        except Exception:
            peak_rss_mb = None

    results = TestResults(
        run_id=config.run_id,
        video=Path(config.video_path).name,
        model=config.model_name,
        tracker=config.tracker,
        tracker_params=config.tracker_params,
        conf=config.conf_threshold,
        player_idx=config.player_idx,
        run_start_ts=run_start_ts,
        run_end_ts=run_end_ts,
        run_elapsed_sec=run_elapsed_sec,
        continuous_tracking_from_start_sec=continuous_from_start_sec,
        first_loss_time_sec=first_loss_time_sec,
        success_first_5sec=success_first_5sec,
        success_first_10sec=success_first_10sec,
        total_frames=len(frame_log),
        tracked_frames=tracked_frames,
        success_rate=success_rate,
        max_consecutive_loss_frames=max_consecutive_loss,
        max_consecutive_loss_sec=max_consecutive_loss_sec,
        max_consecutive_tracked_frames=max_consecutive_tracked_frames,
        longest_tracked_streak_sec=longest_tracked_streak_sec,
        id_switches=id_switches,
        avg_confidence=avg_confidence,
        bbox_variance=bbox_variance,
        bbox_size_variance=bbox_size_variance,
        position_jumps=position_jumps,
        max_center_drift_px=max_center_drift_px,
        median_center_drift_px=median_center_drift_px,
        center_drift_ratio=center_drift_ratio,
        suspicious_frames=suspicious_frames,
        likely_wrong_player=likely_wrong_player,
        quality_score=quality_score,
        processing_time_sec=processing_time,
        processing_speed_x_realtime=processing_speed,
        avg_frame_latency_sec=avg_frame_latency_sec,
        peak_rss_mb=peak_rss_mb,
        detection_count_first_frame=detection_count_first_frame,
        target_initial_confidence=target_confidence,
        frame_log=frame_log
    )

    print(f"[{config.run_id}] Complete at {time.strftime('%H:%M:%S')}!")
    print(f"  Continuous from start: {continuous_from_start_sec:.1f}s")
    print(f"  Success rate: {success_rate*100:.1f}%")
    print(f"  Quality score: {quality_score}/100")

    return results


def configure_threads(thread_count: int):
    """Configure threading env vars and torch thread counts."""
    thread_count = max(1, int(thread_count))
    thread_str = str(thread_count)
    os.environ["OMP_NUM_THREADS"] = thread_str
    os.environ["MKL_NUM_THREADS"] = thread_str
    os.environ["NUMEXPR_MAX_THREADS"] = thread_str
    os.environ["PYTORCH_NUM_THREADS"] = thread_str
    torch.set_num_threads(thread_count)
    # set_num_interop_threads can only be called before any parallel work starts
    try:
        torch.set_num_interop_threads(max(1, thread_count // 2))
    except RuntimeError:
        pass


def save_results(results_list: List[TestResults], output_dir: Path):
    """Save all results in multiple formats."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual run JSON files (with frame logs)
    runs_dir = output_dir / 'runs'
    runs_dir.mkdir(exist_ok=True)

    for result in results_list:
        run_file = runs_dir / f"{result.run_id}.json"
        with open(run_file, 'w') as f:
            # Convert dataclasses to dict and sanitize types
            result_dict = ensure_jsonable(asdict(result))
            json.dump(result_dict, f, indent=2)

    # Save consolidated CSV (summary stats only, no frame logs)
    csv_file = output_dir / 'bulk_test_results.csv'
    with open(csv_file, 'w', newline='') as f:
        if results_list:
            # Get all fields except frame_log
            fields = [field for field in asdict(results_list[0]).keys() if field != 'frame_log']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for result in results_list:
                row = ensure_jsonable(asdict(result))
                row.pop('frame_log')  # Remove frame log from CSV
                writer.writerow(row)

    # Save raw data archive (JSONL - one JSON object per line)
    jsonl_file = output_dir / 'bulk_test_data.jsonl'
    with open(jsonl_file, 'w') as f:
        for result in results_list:
            json.dump(ensure_jsonable(asdict(result)), f)
            f.write('\n')

    # Generate summary report
    generate_summary_report(results_list, output_dir)

    print(f"\n✅ Results saved to {output_dir}/")
    print(f"   - Individual runs: {runs_dir}/")
    print(f"   - CSV summary: {csv_file}")
    print(f"   - JSONL archive: {jsonl_file}")
    print(f"   - Summary report: {output_dir}/bulk_test_summary.md")


def generate_summary_report(results_list: List[TestResults], output_dir: Path):
    """Generate human-readable summary report."""
    report_file = output_dir / 'bulk_test_summary.md'

    with open(report_file, 'w') as f:
        f.write("# Bulk CV Tracking Test Results\n\n")
        f.write(f"**Total runs**: {len(results_list)}\n\n")

        # Best/worst overall
        f.write("## Overall Results (All Runs)\n\n")
        best = max(results_list, key=lambda x: x.continuous_tracking_from_start_sec)
        worst = min(results_list, key=lambda x: x.continuous_tracking_from_start_sec)

        f.write(f"**Best**: {best.model}/{best.tracker} @ conf={best.conf} (player {best.player_idx}, {best.video})\n")
        f.write(f"  - Continuous from start: {best.continuous_tracking_from_start_sec:.1f}s\n")
        f.write(f"  - Success rate: {best.success_rate*100:.1f}%\n")
        f.write(f"  - Quality score: {best.quality_score}/100\n\n")

        f.write(f"**Worst**: {worst.model}/{worst.tracker} @ conf={worst.conf} (player {worst.player_idx}, {worst.video})\n")
        f.write(f"  - Continuous from start: {worst.continuous_tracking_from_start_sec:.1f}s\n")
        f.write(f"  - Success rate: {worst.success_rate*100:.1f}%\n")
        f.write(f"  - Quality score: {worst.quality_score}/100\n\n")

        # High quality only
        high_quality = [r for r in results_list if r.quality_score > 70]
        if high_quality:
            f.write("## High Quality Results Only (Quality Score > 70)\n\n")
            best_hq = max(high_quality, key=lambda x: x.continuous_tracking_from_start_sec)
            f.write(f"**Best**: {best_hq.model} @ conf={best_hq.conf} (player {best_hq.player_idx}, {best_hq.video})\n")
            f.write(f"  - Continuous from start: {best_hq.continuous_tracking_from_start_sec:.1f}s\n")
            f.write(f"  - Success rate: {best_hq.success_rate*100:.1f}%\n\n")

            f.write(f"**Runs filtered out**: {len(results_list) - len(high_quality)} / {len(results_list)} ")
            f.write(f"({(len(results_list)-len(high_quality))/len(results_list)*100:.1f}%)\n\n")

        # Success at 5 seconds
        success_5sec = [r for r in results_list if r.success_first_5sec]
        f.write(f"## First 5 Seconds Success\n\n")
        f.write(f"**Runs with ≥5 seconds continuous tracking**: {len(success_5sec)} / {len(results_list)} ")
        f.write(f"({len(success_5sec)/len(results_list)*100:.1f}%)\n\n")

        # By model
        f.write("## Results by Model\n\n")
        models = set(r.model for r in results_list)
        for model in sorted(models):
            model_results = [r for r in results_list if r.model == model]
            avg_continuous = np.mean([r.continuous_tracking_from_start_sec for r in model_results])
            success_5_count = len([r for r in model_results if r.success_first_5sec])

            f.write(f"### {model}\n")
            f.write(f"- Avg continuous from start: {avg_continuous:.1f}s\n")
            f.write(f"- Success at 5sec: {success_5_count}/{len(model_results)} ")
            f.write(f"({success_5_count/len(model_results)*100:.1f}%)\n\n")

        # By confidence
        f.write("## Results by Confidence Threshold\n\n")
        confs = sorted(set(r.conf for r in results_list))
        for conf in confs:
            conf_results = [r for r in results_list if r.conf == conf]
            avg_continuous = np.mean([r.continuous_tracking_from_start_sec for r in conf_results])
            success_5_count = len([r for r in conf_results if r.success_first_5sec])

            f.write(f"### conf={conf}\n")
            f.write(f"- Avg continuous from start: {avg_continuous:.1f}s\n")
            f.write(f"- Success at 5sec: {success_5_count}/{len(conf_results)} ")
            f.write(f"({success_5_count/len(conf_results)*100:.1f}%)\n\n")

        # By tracker
        f.write("## Results by Tracker\n\n")
        trackers = set(r.tracker for r in results_list)
        for tracker in sorted(trackers):
            tracker_results = [r for r in results_list if r.tracker == tracker]
            avg_continuous = np.mean([r.continuous_tracking_from_start_sec for r in tracker_results])
            avg_quality = np.mean([r.quality_score for r in tracker_results])

            f.write(f"### {tracker}\n")
            f.write(f"- Avg continuous from start: {avg_continuous:.1f}s\n")
            f.write(f"- Avg quality score: {avg_quality:.1f}/100\n")
            f.write(f"- Runs: {len(tracker_results)}\n\n")


def main():
    """Main bulk testing entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Bulk CV tracking tests')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation (6 runs, ~5 mins)')
    parser.add_argument('--full', action='store_true',
                       help='Run full test matrix (216 runs, ~3-4 hours)')
    parser.add_argument('--sample-size', type=int, default=None,
                       help='Randomly sample this many configs from the generated matrix (for exploratory sweeps)')
    parser.add_argument('--random-seed', type=int, default=42,
                       help='Random seed for sampling')
    parser.add_argument('--threads', type=int, default=None,
                       help='Override torch/OMP thread count (defaults to a moderate value based on CPU cores)')
    parser.add_argument('--jobs', type=int, default=1,
                       help='Number of parallel processes for running configs')
    args = parser.parse_args()

    if not args.quick and not args.full:
        print("Error: Must specify --quick or --full")
        sys.exit(1)

    # Find test videos
    test_videos = []
    for ext in ['.mp4', '.mov', '.MOV', '.MP4']:
        test_videos.extend(Path('spike').glob(f'test_video*{ext}'))

    if not test_videos:
        print("Error: No test videos found in spike/ directory")
        print("Expected: spike/test_video.mov and/or spike/test_video2.mov")
        sys.exit(1)

    test_videos = [str(v) for v in sorted(test_videos)]
    print(f"Found {len(test_videos)} test video(s):")
    for v in test_videos:
        print(f"  - {Path(v).name}")

    # Define test matrix
    if args.quick:
        models = ['yolo11s']
        confs = [0.20, 0.25]
        num_players = 3
        videos = test_videos[:1]  # Just first video
        trackers = ['botsort', 'bytetrack']
        print("\n🚀 Running QUICK validation test")
    else:
        models = ['yolo11n', 'yolo11s', 'yolo11m']
        confs = [0.15, 0.20, 0.25, 0.30]
        num_players = 9
        videos = test_videos[:2]  # Both videos
        trackers = ['botsort', 'bytetrack']
        print("\n🚀 Running FULL test matrix")

    print(f"  Models: {models}")
    print(f"  Confidence thresholds: {confs}")
    print(f"  Trackers: {trackers}")
    print(f"  Players per video: top {num_players}")
    print(f"  Videos: {len(videos)}")

    # Generate test configurations
    configs = []
    def tracker_param_sets(tracker_name: str, quick: bool) -> List[Dict[str, float | int | bool]]:
        """Return list of parameter combinations per tracker."""
        if tracker_name == 'botsort':
            buffers = [25] if quick else [25, 50]
            reid_flags = [True, False] if not quick else [True, False]
            return [{'track_buffer': tb, 'with_reid': reid} for tb in buffers for reid in reid_flags]
        if tracker_name == 'bytetrack':
            buffers = [25] if quick else [25, 50]
            low_thresh = [0.05] if quick else [0.05, 0.1]
            return [{'track_buffer': tb, 'track_low_thresh': lt} for tb in buffers for lt in low_thresh]
        return [{}]

    def build_run_id(video_path: str, model: str, tracker_name: str, conf: float,
                     player_idx: int, params: Dict[str, float | int | bool]) -> str:
        parts = [
            Path(video_path).stem,
            model,
            tracker_name,
            f"conf{conf}",
            f"p{player_idx}"
        ]
        for key in sorted(params.keys()):
            parts.append(f"{key}{params[key]}")
        return "_".join(parts)

    for video in videos:
        for model in models:
            # Get detections for this video/model
            try:
                detections = detect_players(video, model)
                max_players = min(num_players, len(detections))

                for conf in confs:
                    for tracker in trackers:
                        param_grid = tracker_param_sets(tracker, args.quick)
                        for params in param_grid:
                            for player_idx in range(max_players):
                                run_id = build_run_id(video, model, tracker, conf, player_idx, params)
                                configs.append(TestConfig(
                                    video_path=video,
                                    model_name=model,
                                    tracker=tracker,
                                    tracker_params=params,
                                    conf_threshold=conf,
                                    player_idx=player_idx,
                                    run_id=run_id
                                ))
            except Exception as e:
                print(f"Warning: Could not detect players in {Path(video).name} with {model}: {e}")

    original_count = len(configs)
    if args.sample_size is not None and args.sample_size < len(configs):
        random.seed(args.random_seed)
        configs = random.sample(configs, args.sample_size)
        print(f"\n🔎 Sampling {len(configs)} of {original_count} configs (seed={args.random_seed})")
    elif args.sample_size is not None and args.sample_size >= len(configs):
        print(f"\n🔎 Sample size >= total configs; running all {len(configs)}")

    print(f"\n📋 Total test runs: {len(configs)}")
    est_minutes = len(configs)  # assumes ~60s per run
    print(f"⏱️  Estimated time: {est_minutes:.1f} minutes (assuming ~60s/run)\n")

    # Let the tracker use a configurable number of threads without oversubscribing
    cpu_count = os.cpu_count() or 4
    jobs = max(1, args.jobs)
    # Default threads scales down per process when using multiple jobs
    default_threads = max(1, min(12, cpu_count // jobs if jobs > 1 else cpu_count))
    thread_count = args.threads or default_threads
    configure_threads(thread_count)
    print(f"🧵 Using up to {thread_count} threads for torch/OMP per process")
    print(f"🤹 Running with {jobs} parallel job(s)")

    # Run tests sequentially
    results = []
    if jobs == 1:
        for idx, config in enumerate(configs, start=1):
            try:
                result = run_single_test(config)
                results.append(result)
                print(f"✅ Progress: {idx}/{len(configs)} complete")
            except Exception as e:
                print(f"❌ Test failed for {config.run_id}: {e}")
    else:
        executor = ProcessPoolExecutor(
            max_workers=jobs,
            mp_context=get_context("spawn"),
            initializer=configure_threads,
            initargs=(thread_count,),
        )
        try:
            future_map = {executor.submit(run_single_test, cfg): cfg.run_id for cfg in configs}
            for idx, future in enumerate(as_completed(future_map), start=1):
                run_id = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"✅ Progress: {idx}/{len(configs)} complete ({run_id})")
                except Exception as e:
                    print(f"❌ Test failed for {run_id}: {e}")
        except KeyboardInterrupt:
            print("\n⚠️  KeyboardInterrupt received, terminating workers...")
            executor.shutdown(wait=False, cancel_futures=True)
            for p in executor._processes.values():
                try:
                    p.kill()
                except Exception:
                    pass
            raise
        finally:
            executor.shutdown(cancel_futures=True)

    # Save all results
    output_dir = Path('spike/bulk_test_output')
    save_results(results, output_dir)

    print(f"\n🎉 All tests complete!")
    print(f"📊 View summary: spike/bulk_test_output/bulk_test_summary.md")
    print(f"📈 Analyze data: spike/bulk_test_output/bulk_test_results.csv")


if __name__ == '__main__':
    main()
