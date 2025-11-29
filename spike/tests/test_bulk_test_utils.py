from pathlib import Path
import pytest
import numpy as np

import yaml

from spike import bulk_test
import numpy as np


def test_build_tracker_config_overrides(monkeypatch, tmp_path):
    base_cfg = {
        "track_buffer": 25,
        "with_reid": True,
        "some_other_key": 123,
    }
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.safe_dump(base_cfg))

    monkeypatch.setattr(bulk_test, "get_tracker_cfg_path", lambda tracker: base_path)

    out_path = bulk_test.build_tracker_config("botsort", {"track_buffer": 50, "with_reid": False})
    cfg = yaml.safe_load(Path(out_path).read_text())

    assert cfg["track_buffer"] == 50
    assert cfg["with_reid"] is False
    # Ensure unrelated keys are preserved
    assert cfg["some_other_key"] == 123


def test_build_tracker_config_none_override_leaves_default(monkeypatch, tmp_path):
    base_cfg = {
        "track_buffer": 25,
        "track_low_thresh": 0.05,
    }
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.safe_dump(base_cfg))

    monkeypatch.setattr(bulk_test, "get_tracker_cfg_path", lambda tracker: base_path)

    out_path = bulk_test.build_tracker_config("bytetrack", {"track_buffer": None})
    cfg = yaml.safe_load(Path(out_path).read_text())

    # None should not override existing values
    assert cfg["track_buffer"] == 25
    assert cfg["track_low_thresh"] == 0.05


def test_summarize_frame_log_basic():
    fps = 10
    frame_log = [
        bulk_test.TrackingFrame(frame=0, time_sec=0.0, tracked=True, bbox=None, confidence=None, track_id=1),
        bulk_test.TrackingFrame(frame=1, time_sec=0.1, tracked=True, bbox=None, confidence=None, track_id=1),
        bulk_test.TrackingFrame(frame=2, time_sec=0.2, tracked=False, bbox=None, confidence=None, track_id=None),
        bulk_test.TrackingFrame(frame=3, time_sec=0.3, tracked=True, bbox=None, confidence=None, track_id=1),
        bulk_test.TrackingFrame(frame=4, time_sec=0.4, tracked=True, bbox=None, confidence=None, track_id=1),
        bulk_test.TrackingFrame(frame=5, time_sec=0.5, tracked=False, bbox=None, confidence=None, track_id=None),
    ]

    stats = bulk_test.summarize_frame_log(frame_log, fps)

    assert stats["continuous_from_start_frames"] == 2
    assert stats["continuous_from_start_sec"] == 0.2
    assert stats["first_loss_time_sec"] == 0.2
    assert stats["max_consecutive_loss_frames"] == 1
    assert stats["max_consecutive_loss_sec"] == 0.1
    assert stats["max_consecutive_tracked_frames"] == 2
    assert stats["longest_tracked_streak_sec"] == 0.2


def test_summarize_frame_log_all_tracked():
    fps = 30
    frame_log = [
        bulk_test.TrackingFrame(frame=i, time_sec=i / fps, tracked=True, bbox=None, confidence=None, track_id=1)
        for i in range(10)
    ]
    stats = bulk_test.summarize_frame_log(frame_log, fps)

    assert stats["continuous_from_start_frames"] == 10
    assert stats["continuous_from_start_sec"] == 10 / fps
    assert stats["first_loss_time_sec"] is None
    assert stats["max_consecutive_loss_frames"] == 0
    assert stats["max_consecutive_tracked_frames"] == 10
    assert stats["longest_tracked_streak_sec"] == 10 / fps


def test_summarize_frame_log_zero_fps_raises():
    with pytest.raises(ValueError):
        bulk_test.summarize_frame_log([], 0)


def test_ensure_jsonable_converts_numpy_and_path(tmp_path):
    data = {
        "a": np.float32(1.5),
        "b": np.bool_(True),
        "c": Path(tmp_path),
        "d": [np.int64(3), np.array([1.0, 2.0])],
    }
    cleaned = bulk_test.ensure_jsonable(data)

    assert cleaned["a"] == 1.5 and isinstance(cleaned["a"], float)
    assert cleaned["b"] is True and isinstance(cleaned["b"], bool)
    assert isinstance(cleaned["c"], str)
    assert cleaned["d"][0] == 3 and isinstance(cleaned["d"][0], int)
    assert cleaned["d"][1] == [1.0, 2.0]


def test_run_single_test_tracks_movement(monkeypatch, tmp_path):
    """Ensure tracking uses per-frame boxes (not frozen to first frame)."""

    class DummyTensor:
        def __init__(self, data):
            self._data = np.array(data)

        def cpu(self):
            return self

        def numpy(self):
            return self._data

        def __getitem__(self, idx):
            return DummyTensor(self._data[idx])

        def __int__(self):
            return int(self._data.item())

        def __float__(self):
            return float(self._data.item())

    class DummyBox:
        def __init__(self, bbox, track_id):
            self.cls = DummyTensor([0])
            self.id = DummyTensor([track_id])
            self.xyxy = DummyTensor([bbox])
            self.conf = DummyTensor([0.9])

    class DummyBoxes(list):
        def __init__(self, boxes):
            super().__init__(boxes)
            self.id = np.array([b.id[0] for b in boxes])

    class DummyResult:
        def __init__(self, boxes):
            self.boxes = DummyBoxes(boxes)

    class DummyModel:
        def __init__(self, *_args, **_kwargs):
            pass

        def track(self, *_, **__):
            # Two frames: same track id, different centers
            return iter([
                DummyResult([DummyBox([0, 0, 10, 10], track_id=1)]),
                DummyResult([DummyBox([5, 0, 15, 10], track_id=1)]),
            ])

    class DummyCap:
        def __init__(self, *_args, **_kwargs):
            pass

        def get(self, prop):
            if prop == bulk_test.cv2.CAP_PROP_FPS:
                return 30
            if prop == bulk_test.cv2.CAP_PROP_FRAME_COUNT:
                return 2
            if prop == bulk_test.cv2.CAP_PROP_FRAME_WIDTH:
                return 1920
            if prop == bulk_test.cv2.CAP_PROP_FRAME_HEIGHT:
                return 1080
            return 0

        def release(self):
            return None

    # Patch dependencies
    monkeypatch.setattr(bulk_test, "YOLO", DummyModel)
    monkeypatch.setattr(bulk_test.cv2, "VideoCapture", DummyCap)
    monkeypatch.setattr(bulk_test, "detect_players",
                        lambda *_args, **_kwargs: [{"bbox": [0, 0, 10, 10], "confidence": 0.9}])

    tracker_cfg = tmp_path / "tracker.yaml"
    tracker_cfg.write_text("track_buffer: 25\n")
    monkeypatch.setattr(bulk_test, "build_tracker_config", lambda *_: str(tracker_cfg))

    config = bulk_test.TestConfig(
        video_path=str(tmp_path / "vid.mp4"),
        model_name="yolo11s",
        tracker="botsort",
        tracker_params={},
        conf_threshold=0.2,
        player_idx=0,
        run_id="t1",
    )

    results = bulk_test.run_single_test(config)

    assert results.tracked_frames == 2
    assert results.total_frames == 2
    # Movement occurred between frames
    assert results.max_center_drift_px > 0.1
    assert results.center_drift_ratio > 0.0
