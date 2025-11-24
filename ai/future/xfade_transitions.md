# xfade Transition Support

## Overview

Add support for smooth video transitions between clips using FFmpeg's `xfade` filter. This would allow crossfades and other transition effects instead of hard cuts when concatenating player highlight clips.

## User Requirements

- Specify transition type (default: `fade`)
- Specify transition duration (default: `1.0` seconds)
- Optional feature - can do first pass without fades, then re-process with transitions

## Recommended Implementation: FFmpeg xfade Filter

### How It Works

- Use FFmpeg's built-in `xfade` filter instead of concat demuxer
- Build a complex filter graph that chains clips with transitions
- Requires **re-encoding** the video (cannot use `-c copy`)
- Slower processing but professional-looking results

### Example FFmpeg Command

```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 \
  -filter_complex "\
    [0:v][1:v]xfade=transition=fade:duration=1:offset=5[v01];\
    [v01][2:v]xfade=transition=fade:duration=1:offset=10[vout]" \
  -map "[vout]" -map 0:a output.mp4
```

### Available Transition Types

FFmpeg xfade supports 40+ transitions including:
- `fade` - Simple crossfade (recommended default)
- `wipeleft`, `wiperight`, `wipeup`, `wipedown`
- `slideleft`, `slideright`, `slideup`, `slidedown`
- `dissolve`, `pixelize`, `circleopen`, `circleclose`
- `distance`, `fadeblack`, `fadewhite`
- `radial`, `smoothleft`, `smoothright`
- And many more creative options

See [FFmpeg xfade documentation](https://ffmpeg.org/ffmpeg-filters.html#xfade) for complete list.

## Implementation Plan

### 1. New CLI Options

Add to `cli.py`:
```python
@click.option(
    "--transition-type",
    default="fade",
    help="Type of transition between clips (fade, wipeleft, dissolve, etc.)"
)
@click.option(
    "--transition-duration",
    default=1.0,
    type=float,
    help="Duration of transitions in seconds (default: 1.0)"
)
@click.option(
    "--no-transitions",
    is_flag=True,
    help="Disable transitions and use fast concatenation (default behavior)"
)
```

### 2. New Function in `ffmpeg.py`

Create `concat_clips_with_xfade()`:
```python
def concat_clips_with_xfade(
    clip_paths: List[str],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = 1.0
) -> None:
    """
    Concatenates clips with smooth transitions using xfade filter.
    
    Args:
        clip_paths: List of paths to clip files
        output_path: Path to save the final video
        transition_type: Type of xfade transition
        transition_duration: Duration of each transition in seconds
    """
    # Get duration of each clip using ffprobe
    # Build filter graph with xfade filters
    # Calculate offset times (sum of previous durations - overlaps)
    # Execute ffmpeg command
```

### 3. Logic Changes in `cli.py`

Modify the concatenation section:
```python
if no_transitions:
    concat_clips(temp_clips, output_file_path)
else:
    concat_clips_with_xfade(
        temp_clips,
        output_file_path,
        transition_type=transition_type,
        transition_duration=transition_duration
    )
```

### 4. Helper Function for Duration Detection

Add to `ffmpeg.py`:
```python
def get_video_duration(video_path: str) -> float:
    """Get duration of video file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
```

## Technical Considerations

### Pros
- Native FFmpeg support (no external dependencies)
- High quality, professional transitions
- Many transition types available
- All processing in single FFmpeg command

### Cons
- **Slower**: Requires re-encoding entire output video
- **Higher CPU usage**: Cannot use stream copy
- **More complex**: Filter graph syntax can be tricky
- **Audio handling**: Need to decide on audio crossfade strategy

### Audio Handling Options

1. **Simple**: Concatenate audio without crossfade (hard audio cuts)
2. **Advanced**: Use `acrossfade` filter for smooth audio transitions
3. **Hybrid**: Take audio from first clip during transition

Start with option 1, can enhance later.

## Testing Strategy

### Automated Tests
- Unit tests for command generation (don't run FFmpeg)
- Verify filter graph syntax is correct
- Test offset calculations with various clip counts
- Integration tests that run FFmpeg and verify:
  - Exit code is 0
  - Output file exists
  - Output duration is correct (sum of clips minus overlaps)
  - `ffprobe` shows expected streams

### Manual Testing (Visual QA Required)
- Test with 2 clips first
- Verify transition looks smooth
- Check timing is correct
- Test with multiple clips (5+)
- Try different transition types
- Verify audio sync

### Test Case Example
```bash
# Create test video with 2 clips
highlight-cuts --input-video test.mp4 --csv-file test.csv --game Test \
  --transition-type fade --transition-duration 1.0

# Verify output
ffprobe output.mp4  # Check duration and streams
# Visual inspection in video player
```

## Complexity Assessment

### Implementation Complexity: 6/10 (Medium)

**Straightforward parts:**
- FFmpeg has built-in support
- Command structure is well-documented
- CLI option additions are simple
- Offset calculation is deterministic

**Challenging parts:**
- Filter graph syntax with many clips
- Audio handling edge cases
- Cannot visually verify output (requires human QA)
- Performance optimization

### Development Time Estimate
- Core functionality: 2-3 hours
- Testing & refinement: 1-2 hours
- Audio crossfade (optional): +1-2 hours
- **Total**: 4-7 hours

## Alternative Approaches Considered

### Option 2: Hybrid Approach
Extract clips with overlap, use xfade only at transition points.
- **Complexity**: High
- **Benefit**: Faster than full re-encode
- **Decision**: Not worth the added complexity

### Option 3: Pre-render Transition Clips
Generate fade frames separately and insert between clips.
- **Complexity**: Medium-Low
- **Benefit**: Can still use concat demuxer
- **Decision**: Less professional looking (fades through black)

## Future Enhancements

1. **Custom transition per clip**: Different transitions between different clips
2. **Audio crossfade**: Smooth audio transitions with `acrossfade` filter
3. **Transition presets**: Named presets like "professional", "creative", "fast"
4. **Preview mode**: Generate low-res preview with transitions for quick review
5. **GPU acceleration**: Use hardware encoding for faster processing

## References

- [FFmpeg xfade filter documentation](https://ffmpeg.org/ffmpeg-filters.html#xfade)
- [FFmpeg acrossfade filter](https://ffmpeg.org/ffmpeg-filters.html#acrossfade)
- [FFmpeg complex filtergraphs](https://trac.ffmpeg.org/wiki/FilteringGuide)

## Decision

**Status**: Future enhancement - not implementing yet

**Rationale**: User prefers to do initial clip generation without transitions (fast), then optionally re-process with transitions once clips look good. This is a good workflow that allows iteration without waiting for slow re-encoding.

**Next Steps**: Implement when user is ready for this enhancement. The existing fast concatenation workflow should remain the default behavior.
