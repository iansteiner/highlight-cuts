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

## Limitations & Considerations

### Keyframe Snapping

**What it is**: When using stream copy mode, clips can only start and end at "keyframes" (I-frames) in the video.

**Impact**: 
- Clips may start up to 1-2 seconds earlier than requested
- Clips may end slightly later than requested
- Exact frame-perfect cuts are not possible

**Why this happens**: Keyframes are reference frames in video compression. To avoid re-encoding, we can only cut at these points.

**Mitigation**:
- Use `--padding` to add buffer time around clips
- Accept the minor timing variance (usually imperceptible)
- Future: Re-encoding mode for frame-accurate cuts (much slower)

### Codec Compatibility

**Supported formats**:
- ✅ MP4 with H.264 video and AAC audio (recommended)
- ✅ MOV with H.264 video and AAC audio
- ✅ Most modern video formats

**Unsupported/problematic formats**:
- ⚠️ Old codecs (MPEG-2, DivX, XviD)
- ⚠️ Uncommon containers (FLV, WMV)
- ⚠️ Variable frame rate videos (may cause sync issues)

**Solution**: Convert to MP4 with H.264:
```bash
ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4
```

### Interval Merging Behavior

**What it does**: Automatically merges overlapping or adjacent clips.

**Example**:
- Clip 1: `00:01:00` to `00:01:10`
- Clip 2: `00:01:08` to `00:01:20`
- Result: One merged clip `00:01:00` to `00:01:20`

**Why**: Avoids duplicate content and creates smoother highlights.

**Consideration**: If you want separate clips, ensure they don't overlap (even after padding).

### Performance Factors

**Fast scenarios**:
- SSD storage
- H.264 video codec
- Moderate number of clips (<50 per player)

**Slow scenarios**:
- HDD or network storage
- Uncommon codecs requiring re-encoding
- Very large number of clips (>100 per player)
- Very large source files (>10GB)

### Google Sheets Limitations

**Rate limiting**: Google may throttle excessive requests. If processing many games rapidly, consider downloading the CSV locally.

**Privacy**: Shared sheets are publicly accessible. Don't include sensitive information.

**Reliability**: Requires internet connection. For offline processing, use local CSV files.

### Current Feature Limitations

**Not yet supported** (but planned for future versions):
- ❌ Transitions between clips (crossfades, wipes)
- ❌ Re-encoding mode for frame-accurate cuts
- ❌ Batch processing multiple games in one command
- ❌ Custom output filename templates
- ❌ Slow-motion effects
- ❌ Adding music or commentary
- ❌ Watermarking

See `ai/future/` directory for detailed plans on upcoming features.

## When to Use This Tool

### ✅ Good Use Cases

- Creating highlight reels for 5-20 players from a single game
- Processing multiple games throughout a season
- Collaborative timestamp logging with Google Sheets
- Quick turnaround needed (highlights same day as game)
- Maintaining original video quality is important

### ⚠️ Consider Alternatives

- **Professional editing needed**: Use DaVinci Resolve, Premiere Pro, or Final Cut Pro
- **Advanced effects required**: Slow-motion, color grading, graphics, music
- **Frame-perfect accuracy critical**: Use a professional editor with re-encoding
- **Single player, manual selection**: Might be faster to edit manually

## Comparison with Manual Editing

| Aspect | Manual Editing | Highlight Cuts |
|--------|----------------|----------------|
| **Time** | 30-60 min per player | Seconds for all players |
| **Skill Required** | Video editing knowledge | Basic command-line usage |
| **Quality** | Depends on export settings | 100% original quality |
| **Flexibility** | Full creative control | Automated, consistent |
| **Cost** | Software license ($20-50/mo) | Free and open-source |
| **Accuracy** | Frame-perfect | Keyframe-snapped (±1-2s) |

## Technical Background

### Why FFmpeg?

FFmpeg is the industry-standard video processing tool:
- Powers YouTube, Netflix, and most video platforms
- Extremely fast and efficient
- Supports virtually all video formats
- Free and open-source
- Cross-platform (Windows, Mac, Linux)

### Why Python?

Python provides:
- Excellent data processing libraries (pandas)
- Easy subprocess management for FFmpeg
- Cross-platform compatibility
- Large ecosystem for future enhancements
- Readable, maintainable code

### Why Stream Copy?

Stream copying is **100x faster** than re-encoding:

**Re-encoding workflow**:
1. Decode compressed video → raw frames
2. Edit raw frames
3. Re-encode frames → compressed video
4. Time: ~1x real-time (1 hour video = 1 hour processing)
5. Quality: Generation loss from re-compression

**Stream copy workflow**:
1. Copy compressed video streams directly
2. No decoding/encoding
3. Time: ~100x real-time (1 hour video = 36 seconds)
4. Quality: Zero generation loss

**Trade-off**: Stream copy requires cutting at keyframes, sacrificing frame-perfect accuracy for massive speed gains.

---

For more technical details, see [Architecture & Design](architecture.md).
