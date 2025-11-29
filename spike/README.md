# CV Tracking Prototype

This directory contains the prototype validation script for computer vision player tracking.

## Purpose

Validate core assumptions before building the full web integration:
1. YOLO11 accurately detects players in sports footage
2. BoT-SORT tracking maintains correct player through occlusions
3. Performance meets targets (~1-2 min to generate 15-sec preview on CPU)
4. OpenCV rendering produces acceptable visual quality

## Setup

### 1. Install Dependencies

```bash
# From repository root
uv add ultralytics opencv-python torch torchvision pillow
```

### 2. Provide Test Video

Place a ~30 second test video at `spike/test_video.mp4`:
- Should contain: Multiple players, some occlusions, typical camera movement
- Format: MP4, any resolution (4K preferred for realism)

### 3. Run Prototype

```bash
# From repository root
python spike/cv_prototype.py
```

## What It Does

1. **Detection Phase**:
   - Extracts first frame from video
   - Runs YOLO11 detection to find all players
   - Saves annotated image with bounding boxes
   - Prompts you to select target player

2. **Tracking Phase**:
   - Tracks selected player through entire video using BoT-SORT
   - Renders green dot above player's head
   - Outputs 720p @ 30fps preview video
   - Reports performance metrics

## Outputs

All outputs are saved to `spike/output/`:

- `first_frame_detections.jpg` - First frame with all detected players labeled
- `preview_tracked.mp4` - 720p preview video with tracking indicator
- `metrics.json` - Performance metrics (timing, success rate, etc.)

## Success Criteria

✅ **Excellent** (Proceed to implementation):
- Detection: 90-100% of players detected
- Tracking: ≥95% success rate
- Speed: ≥0.75x realtime
- Visual: Dot stays centered on player's head

⚠️ **Acceptable** (Proceed with adjustments):
- Detection: 80-90% of players detected
- Tracking: 85-95% success rate
- Speed: 0.5-0.75x realtime
- Visual: Dot mostly follows player, minor drift

❌ **Needs work** (Adjust approach):
- Detection: <80% → Try larger model (yolo11s.pt)
- Tracking: <85% → Research alternative trackers
- Speed: <0.5x → Lower preview resolution or require GPU
- Visual: Dot frequently lost → Improve tracking algorithm

## Troubleshooting

### No players detected
- Try a different starting frame: Edit `detect_players(video_path, frame_index=30)`
- Lower confidence threshold: Edit `conf=0.3` to `conf=0.2` in `track_player()`
- Use larger model: Change `yolo11n.pt` to `yolo11s.pt` or `yolo11m.pt`

### Tracking switches to wrong player
- Expected with occlusions - this is what we're testing!
- Document when/why it happens for future improvements

### Too slow
- Try 480p preview: Change `out_width = 1280, out_height = 720` to `out_width = 854, out_height = 480`
- Accept slower performance for CPU-only MVP
- Consider GPU passthrough for production

### FFmpeg encoding fails
- Ensure FFmpeg is installed: `ffmpeg -version`
- Try different codec: Change `'libx264'` to `'mpeg4'`

## Next Steps

After running the prototype:

1. Review all three output files
2. Watch the preview video - does the dot follow your selected player?
3. Check metrics.json - are performance targets met?
4. Document findings using the template in [ai/cv_tracking_prototype_plan.md](../ai/cv_tracking_prototype_plan.md)

**If successful**: Proceed to Milestone 1 (Core CV Module implementation)

**If issues**: See troubleshooting section or consult the implementation plan for alternative approaches

## Model Information

- **YOLO11n** (nano): ~6 MB, fast, good accuracy
- Downloads automatically on first run to `~/.ultralytics/`
- Can upgrade to larger models (s, m, l, x) for better accuracy at cost of speed

## Performance Notes

Expected processing time for 30-second video on typical CPU:
- Detection: <1 second
- Tracking: 30-60 seconds
- Encoding: 10-20 seconds
- **Total: ~40-80 seconds** (0.4-0.8x realtime)

GPU would be 5-10x faster, but not required for prototype validation.
