# Computer Vision Player Tracking - Discussion Summary

**Date**: 2025-11-28
**Status**: Planning Phase

## Vision

We're adding a **two-phase computer vision feature** to enable player tracking with visual indicators in highlight videos:

**Phase 1 (existing)**: Fast clip extraction using stream-copy (no changes needed)

**Phase 2 (new CV workflow)**:
- **2a - Interactive Preview**: User processes clips one-by-one
  - System detects all players in first frame (bounding boxes)
  - User selects target player (via ID/bbox)
  - System generates low-resolution preview (720p or 1080p @ 30fps) with tracking indicator
  - User approves or rejects each preview
  - Target: ~1-2 minutes per 15-second clip

- **2b - Batch Finalization**: Once all previews approved
  - System encodes all clips at high quality (4K @ 60fps with indicators)
  - Background process, can take 30-60 minutes total

- **2c - Concatenation**: Combine tracked clips into final video per player

## Key Decisions

### Technology Stack
- **YOLO11** for player detection and tracking
- **BoT-SORT** tracker (handles occlusions better than ByteTrack)
- **OpenCV** for rendering indicators (dot above player's head)
- **FastAPI BackgroundTasks** for async processing (no job queue initially)
- **JSON/JSONnet** for state management

### Architecture Approach
- No branching needed - Phase 2 is completely separate from Phase 1
- Build incrementally on `main` branch
- New module (`cv_tracking.py`) and new web routes
- Polling pattern for long-running tasks (Cloudflare-friendly)

### Technical Constraints
- CPU-only initially (GPU passthrough deferred)
- Preview at 720p/1080p @ 30fps (fast encoding, validates tracking)
- Final encode at source resolution (4K @ 60fps)
- Single-user for MVP (concurrent users deferred)
- Direct file downloads (no streaming)

### Scope Decisions
- Start with simple dot indicator (circle below feet deferred)
- Basic tracking (advanced failure handling deferred)
- Web-only (CLI deferred - unclear UX for interactive bbox selection)
- Clean up intermediate files after concatenation

### Scale Parameters
- ~2 teams × 8 players = 16 people in frame
- ~4-6 clips per player highlight
- ~10-15 seconds per clip
- ~1 minute total video per player

## User Workflow

### Phase 2a: Interactive Preview (One Clip at a Time)
```
1. User clicks "Add Player Tracking" on a clip
2. System shows first frame with bounding boxes around all detected players
3. User selects target player (click bbox or enter ID)
4. System generates low-res preview (~1-2 minutes processing)
5. User reviews preview video:
   - ✓ "Looks good" → Mark approved, move to next clip
   - ✗ "Wrong player" → Return to step 3
   - ✗ "Tracking failed" → Return to step 3 or skip clip
6. Repeat for all clips
```

### Phase 2b: Batch High-Quality Encode
```
7. User clicks "Finalize All Approved Clips"
8. System encodes all approved clips at full quality (30-60 min total)
9. Background process - user can wait or come back later
10. System polls for completion status
```

### Phase 2c: Concatenation
```
11. System concatenates all tracked clips into final video
12. User downloads: "Game_PlayerName_tracked.mp4"
```

## Performance Targets

### Preview Encoding (Phase 2a)
- **Input**: 15-second clip at 4K @ 60fps
- **Output**: 720p or 1080p @ 30fps
- **Target**: 1-2 minutes per clip (acceptable for interactive use)
- **Encoding preset**: `ultrafast`, `crf=28`

### Final Encoding (Phase 2b)
- **Input**: Tracking data from preview
- **Output**: 4K @ 60fps with indicators
- **Target**: ~5-10 minutes per 15-second clip (background process)
- **Encoding preset**: `medium` or `slow`, `crf=18`

### Total Processing Time Example
- 1 player with 6 clips (1 minute total video)
- Phase 2a: 6 clips × 2 min = ~12 minutes (interactive)
- Phase 2b: 6 clips × 7 min = ~42 minutes (background)
- Total: ~54 minutes from start to final download

## Known Risks/Gotchas

### High Priority
1. **YOLO accuracy on sports footage** - YOLO trained on general images, might struggle with:
   - Players in piles/clusters
   - Distinguishing referees from players
   - Players partially out of frame
   - **Mitigation**: Validate early with real footage (prototype)

2. **Tracking through occlusions** - Player goes behind referee/other player
   - ByteTrack: Handles ~1-2 second occlusions
   - BoT-SORT: Better re-identification, handles longer occlusions
   - **Mitigation**: Start with BoT-SORT, document upgrade path for advanced trackers

3. **Encoding performance on CPU** - 4K video is compute-intensive
   - Even "ultrafast" preset might struggle
   - **Mitigation**: Use 720p/1080p previews, accept slower final encode

### Medium Priority
4. **Cloudflare timeouts** - Long HTTP connections timeout at 100-600 seconds
   - **Mitigation**: Use FastAPI BackgroundTasks + polling pattern (no long-lived connections)

5. **Multiple concurrent users** - Two users processing simultaneously
   - CPU contention, processing slows down
   - **Mitigation**: Document "single user" for MVP, add queue later if needed

6. **Storage space** - Three copies of video content
   - Original clips (Phase 1)
   - Preview clips (Phase 2a)
   - Final tracked clips (Phase 2b)
   - **Mitigation**: Clean up previews after finalization

### Low Priority
7. **Browser memory** - 4K video playback in browser
   - **Mitigation**: Use 720p/1080p previews

8. **Model download** - YOLO11 models are 6-50 MB
   - First run downloads model files
   - **Mitigation**: Pre-download in Docker image, document in setup

## Design Decisions - Detailed Rationale

### Why YOLO11 vs YOLO8?
- YOLO11 released late 2024 with better accuracy
- Same API as YOLO8
- Similar performance characteristics
- More recent training data

### Why BoT-SORT over ByteTrack?
- Better re-identification after occlusions
- Handles longer disappearances (player behind referee)
- Slightly slower but more robust for sports footage
- Easy to swap later if needed (same API)

### Why OpenCV over FFmpeg filters?
- Pixel-perfect control for experiments
- Easy to adjust indicator design (dot size, color, position)
- FFmpeg filters require text files with frame-by-frame coordinates
- Performance difference negligible for clip lengths
- Can optimize to pure FFmpeg later if needed

### Why No Job Queue Initially?
- Total processing time for typical session: ~1 hour
- Single user for MVP
- FastAPI BackgroundTasks sufficient for background processing
- Polling pattern works well with Cloudflare
- Can upgrade to Celery/Redis when concurrent users needed

### Why Polling Instead of WebSockets?
- Simpler infrastructure (no WebSocket support needed)
- More reliable with Cloudflare proxying
- Works behind firewalls/restrictive networks
- Sufficient for update frequency (2-3 second polls)

### Why 720p/1080p Previews?
- Faster encoding (~4-10x faster than 4K)
- Still validates tracking accuracy visually
- Reduces storage during preview phase
- Better browser playback performance
- Users only need to verify "is this the right player?"

### Why Web-Only (No CLI)?
- Interactive workflow requires visual feedback
- Clicking bounding boxes is natural in web UI
- CLI interaction with images is awkward
- Can add CLI later if demand exists

## Simplifications for MVP

These features are explicitly deferred to keep initial implementation manageable:

1. **No concurrent user support** - Single session at a time
2. **No advanced failure handling** - Basic retry only
3. **No confidence scores** - Show/hide based on simple success/fail
4. **No partial re-tracking** - If tracking fails, redo entire clip
5. **No transition effects** - Clips concatenate with hard cuts
6. **No multiple player tracking** - One player per clip (future feature)
7. **No GPU acceleration** - CPU-only for MVP
8. **No job queue** - Background tasks only
9. **No streaming playback** - Direct file downloads only
10. **No circle below feet** - Dot above head only

## Future Enhancements (Post-MVP)

### Phase 3: Advanced Tracking
- Multiple players per clip
- Confidence scores and manual correction
- Partial re-tracking (fix middle section without redoing entire clip)
- Better occlusion handling

### Phase 4: Performance
- GPU acceleration
- Concurrent user support with job queue
- Batch processing (multiple games at once)
- Distributed processing

### Phase 5: UX Improvements
- Streaming preview playback
- Real-time progress updates (WebSockets)
- Scrub timeline to review tracking frame-by-frame
- Visual editor for manual tracking corrections

### Phase 6: Visual Options
- Multiple indicator styles (dot, circle, glow, trail)
- Player name labels
- Team color customization
- Movement trails/heatmaps

## Questions Answered During Discussion

### Q: Should we use a separate branch for CV development?
**A**: No, build incrementally on `main`. Phase 2 is completely separate from Phase 1, no conflicts.

### Q: How do we handle occlusions?
**A**: BoT-SORT for MVP (better than ByteTrack), plan upgrade path to advanced re-ID later.

### Q: What indicator design?
**A**: Start with simple dot above head. Experiment later. Recruiters prefer understated.

### Q: FFmpeg or OpenCV for rendering?
**A**: OpenCV for flexibility during experimentation. Can optimize later if needed.

### Q: What quality for previews?
**A**: 720p or 1080p @ 30fps. Fast encode, validates tracking accuracy. Target ~1-2 min per 15-sec clip.

### Q: How to handle failures?
**A**: Defer for now. Basic retry in MVP. Advanced handling (confidence scores, partial fixes) later.

### Q: Multiple concurrent users?
**A**: Not for MVP. Document single-user limitation. Add queue when needed.

### Q: Cloudflare issues?
**A**: Use polling pattern (no long HTTP connections). Direct file downloads (no streaming).

### Q: CLI or web-only?
**A**: Web-only for MVP. Interactive bbox selection is awkward in CLI.

### Q: CPU or GPU?
**A**: CPU for MVP. GPU passthrough on Hyper-V is complex, defer until performance validated.

## Open Questions for Prototype

1. **Detection accuracy**: Does YOLO11 accurately detect players in real sports footage?
2. **Tracking quality**: Does BoT-SORT maintain correct player through typical occlusions?
3. **Performance**: Can we achieve 1-2 min encoding for 15-sec preview on CPU?
4. **Visual quality**: Is dot indicator clear and unobtrusive?

These will be answered by the prototype validation.

## Next Steps

1. **Create prototype** (spike/cv_prototype.py)
2. **Test with real footage** (30-second clip)
3. **Validate assumptions** (detection, tracking, performance)
4. **Decision point**: If successful → Web integration, if issues → adjust approach
5. **Implement Milestones 1-6** (web routes, UI, batch encoding, concatenation)

## References

- YOLO11 documentation: https://docs.ultralytics.com/
- BoT-SORT paper: https://arxiv.org/abs/2206.14651
- FastAPI background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
