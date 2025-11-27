# Documentation Instructions

This document defines the standards and workflow for all documentation in the `highlight-cuts` project. Following these guidelines ensures consistency, AI-readability, and maintainability.

## Quick Reference

- **End-user docs**: `docs/user/` - Simple, deployment-focused
- **Developer docs**: `docs/dev/` - Technical, contribution-focused
- **AI context**: `ai/` - Session summaries, future plans, notes
- **Session summaries**: Always create when starting a new chat tab/discussion
- **Tone**: Casual and friendly
- **Diagrams**: Mermaid preferred over ASCII art

---

## Session Summaries

### When to Create

**Always create a session summary** when you start a new tab or discussion in the AI chat. This includes:

- Code changes (features, bug fixes, refactoring)
- Documentation updates
- Configuration changes
- Planning sessions
- Research/exploration sessions

Even if you don't commit the summary, creating it helps track work and provides context for future sessions.

### Naming Convention

```
ai/session_summaries/YYYY-MM-DD_session_N.md
```

**Examples**:
- `2025-11-26_session_1.md` - First session of the day
- `2025-11-26_session_2.md` - Second session of the day

If you're unsure what session number to use, check existing files for the current date and increment.

### Structure

Every session summary should include:

```markdown
# AI Session Summary - Session N

**Date**: YYYY-MM-DD
**Project**: Highlight Cuts

## Overview
Brief 1-2 sentence summary of what was accomplished.

## Requirements & Context
What was requested? What was the starting point?

## Actions Taken
Detailed list of changes made, organized by category:
- Code changes
- Documentation updates
- Tests added/modified
- Configuration changes

## Key Decisions
Important choices made during the session and rationale.

## Outcome
Final state, test results, coverage metrics, etc.
```

### Best Practices

- **Be specific**: Include file paths, function names, line numbers
- **Explain why**: Document rationale for decisions, not just what changed
- **Include metrics**: Test coverage, performance improvements, file counts
- **Link to docs**: Reference updated documentation files
- **AI-friendly**: Use clear headings and structured lists for easy parsing

---

## Documentation Structure

### Two-Tier System

The project uses a **two-tier documentation structure** to serve different audiences:

#### 1. End-User Documentation (`docs/user/`)

**Audience**: Users who want to **deploy and use** the tool (coaches, parents, players).

**Focus**:
- Quick start guides
- Docker deployment
- Web interface usage
- Troubleshooting common issues
- FAQ for end users

**Characteristics**:
- Simple, clear instructions
- Minimal technical jargon
- Step-by-step tutorials
- Screenshots/videos where helpful
- "Just works" mentality

**Examples**:
- `docs/user/quickstart.md` - Get started in 5 minutes
- `docs/user/docker.md` - Running with Docker
- `docs/user/web_interface.md` - Using the web UI
- `docs/user/faq.md` - Common questions

#### 2. Developer Documentation (`docs/dev/`)

**Audience**: Developers and contributors who want to **understand, modify, or extend** the code.

**Focus**:
- Architecture and design
- Code structure and patterns
- Testing strategy
- Contributing guidelines
- Technical deep-dives

**Characteristics**:
- Technical depth
- Code examples
- Design decisions and trade-offs
- API references
- Development workflows

**Examples**:
- `docs/dev/architecture.md` - System design
- `docs/dev/contributing.md` - How to contribute
- `docs/dev/testing.md` - Testing infrastructure
- `docs/dev/tech_stack.md` - Technology choices

### Root-Level Documentation

Some docs live at the root or in `docs/` for maximum visibility:

- `README.md` - Project landing page (high-level, links to user/dev docs)
- `docs/CHANGELOG.md` - Version history (for all users)
- `CONTRIBUTING.md` - Quick contributor onboarding (links to `docs/dev/`)
- `SECURITY.md` - Security policy

---

## AI-Optimized Documentation

A **critical audience** for our documentation is AI assistants (like Claude Code) that read docs to:
- Answer user questions
- Understand code structure
- Suggest implementations
- Debug issues

### Guidelines for AI-Friendly Docs

#### 1. Use Clear, Hierarchical Headings

```markdown
# Main Topic

## Subtopic

### Specific Detail

#### Implementation Note
```

AI can easily parse and navigate hierarchical structures.

#### 2. Front-Load Key Information

Put the most important info at the top:

```markdown
# Feature X

**Purpose**: One-sentence description
**Location**: `src/module/file.py:123`
**Dependencies**: pandas, requests

## Details
[More info here...]
```

#### 3. Use Structured Lists

Prefer structured lists over prose paragraphs for factual information:

**Good** (AI-friendly):
```markdown
## CSV Columns
- `videoName`: Game identifier (string)
- `startTime`: HH:MM:SS or MM:SS (string)
- `stopTime`: HH:MM:SS or MM:SS (string)
- `playerName`: Player identifier (string)
```

**Less Ideal**:
```markdown
The CSV should have a videoName column for the game, plus startTime
and stopTime in HH:MM:SS format, and a playerName field.
```

#### 4. Include Code Examples

Always show concrete examples:

```markdown
## Example

\`\`\`python
# Good: Shows actual usage
from highlight_cuts.core import merge_intervals

intervals = [(10, 20), (15, 25)]
merged = merge_intervals(intervals, padding=2.0)
# Result: [(8, 27)]
\`\`\`
```

#### 5. Link to Code Locations

Reference specific files and line numbers:

```markdown
Time parsing is handled in [utils.py:15-25](../src/highlight_cuts/utils.py#L15-L25).
```

#### 6. Document Decisions, Not Just Facts

AI benefits from understanding "why":

```markdown
## Why Stream Copy?

**Decision**: Use FFmpeg `-c copy` for all clips

**Rationale**:
- 100x faster than re-encoding
- Zero quality loss
- Minimal CPU usage

**Trade-off**:
- Clips snap to keyframes (±1-2 seconds)
- Mitigated by user-configurable padding
```

#### 7. Use Tables for Comparisons

```markdown
| Feature | Stream Copy | Re-encode |
|---------|-------------|-----------|
| Speed | 100x real-time | 1x real-time |
| Quality | Lossless | Depends on settings |
| Accuracy | ±1-2s (keyframes) | Frame-perfect |
```

---

## Documentation Update Workflow

### What to Update When

| Change Type | Documentation to Update |
|-------------|------------------------|
| New CLI flag | `docs/user/usage.md`, `README.md` (if major), `CHANGELOG.md` |
| New feature | User or dev docs (depending on audience), `CHANGELOG.md`, `README.md` (features list) |
| Bug fix | `CHANGELOG.md`, possibly `docs/user/troubleshooting.md` if common issue |
| New module/class | `docs/dev/architecture.md`, `docs/dev/tech_stack.md` |
| Breaking change | `CHANGELOG.md` (prominently), `README.md`, affected user/dev docs |
| Performance improvement | `CHANGELOG.md`, possibly `README.md` (performance section) |
| New dependency | `docs/dev/tech_stack.md`, `README.md` (requirements) |
| Docker changes | `docs/user/docker.md`, `README.md` (quick start) |
| Web UI changes | `docs/user/web_interface.md` |

### Update Checklist

When making **any change**, follow this checklist:

1. ✅ **Update relevant docs** (see table above)
2. ✅ **Add entry to `CHANGELOG.md`** (unless trivial)
3. ✅ **Update `README.md`** (if user-facing or major)
4. ✅ **Check cross-references** (are links still valid?)
5. ✅ **Create session summary** (always)

---

## Writing Best Practices

### Tone and Voice

- **Casual and friendly**: Write like you're explaining to a colleague
- **Direct and clear**: Avoid unnecessary jargon
- **Encouraging**: Assume users want to succeed
- **Honest about trade-offs**: Don't oversell or hide limitations

**Example**:
```markdown
❌ "The utilization of stream copy methodology facilitates expedited processing."
✅ "Stream copy makes processing fast - about 100x real-time."
```

### Code Examples

#### Inline Code

Use inline code for:
- File names: `utils.py`
- Function names: `merge_intervals()`
- CLI flags: `--padding`
- Variable names: `video_path`
- Short commands: `uv run pytest`

#### Code Blocks

Use fenced code blocks with syntax highlighting:

```markdown
\`\`\`bash
# Install dependencies
uv sync

# Run the tool
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1
\`\`\`
```

**Always specify the language** (`python`, `bash`, `csv`, `yaml`, etc.) for proper syntax highlighting.

#### Including Output

Show expected output when helpful:

```markdown
\`\`\`bash
$ uv run highlight-cuts --dry-run --input-video game.mp4 --csv-file clips.csv --game Game1

Processing game: Game1
Found 2 players:
  - Alice: 3 clips → 2 merged intervals (45.5 seconds)
  - Bob: 2 clips → 1 merged interval (20.0 seconds)

[DRY RUN] No files were created.
\`\`\`
```

### Diagrams

#### Prefer Mermaid

Use Mermaid for flow charts, sequence diagrams, and architecture diagrams:

```markdown
\`\`\`mermaid
graph LR
    A[User] --> B[CLI]
    B --> C[Core Logic]
    C --> D[FFmpeg]
    D --> E[Output Videos]
\`\`\`
```

**Why Mermaid?**
- Renders natively in GitHub, VS Code, and many viewers
- Text-based (version control friendly)
- AI can easily understand and suggest modifications
- Professional appearance

#### When to Use ASCII

Only use ASCII art for:
- Very simple diagrams (3-4 elements)
- Terminal-based UI mockups
- Situations where Mermaid is not supported

### Cross-Referencing

#### Internal Links

Link liberally to other docs:

```markdown
See the [Architecture Guide](../dev/architecture.md) for implementation details.

For Docker deployment, check the [Docker Setup Guide](docker.md).
```

**Best practices**:
- Use relative paths
- Include descriptive link text (not "click here")
- Link to specific sections when relevant: `[Merging Logic](architecture.md#interval-merging)`

#### External Links

Link to external resources when helpful:

```markdown
- FFmpeg Documentation: [https://ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html)
- Google Sheets API: [https://developers.google.com/sheets/api](https://developers.google.com/sheets/api)
```

**Best practices**:
- Prefer official documentation over blog posts
- Use permalink URLs when available
- Provide context for why the link is relevant

### Formatting Standards

#### Emphasis

- **Bold** for important terms on first mention: "The **padding** setting adds time before/after clips."
- *Italic* for emphasis: "Make sure you *actually* install FFmpeg first."
- `Code` for technical terms: "The `--dry-run` flag is useful for testing."

#### Lists

**Ordered lists** for sequential steps:
```markdown
1. Install FFmpeg
2. Clone the repository
3. Run `uv sync`
4. Execute the tool
```

**Unordered lists** for non-sequential items:
```markdown
- Supports MP4, AVI, MOV
- Works on macOS, Linux, Windows
- Requires Python 3.13+
```

#### Callouts

Use blockquotes for important notes:

```markdown
> **Note**: Stream copy mode snaps to keyframes. Add padding to ensure clips capture all action.

> **Warning**: The `--force` flag will overwrite existing files without prompting.

> **Tip**: Use `--dry-run` to preview clips before processing.
```

#### Tables

Use tables for structured comparisons or reference data:

```markdown
| Option | Default | Description |
|--------|---------|-------------|
| `--padding` | 0.0 | Seconds to add before/after clips |
| `--output-dir` | `.` | Output directory path |
| `--dry-run` | false | Preview mode (no file creation) |
```

**Formatting tips**:
- Align columns for readability in source
- Keep cell content concise
- Use `-` for left-align, `:-:` for center, `-:` for right-align

---

## Documentation Maintenance

### Regular Reviews

Documentation should be reviewed:
- **After major features**: Ensure all new functionality is documented
- **Before releases**: Verify accuracy and completeness
- **When users ask questions**: If a question is asked repeatedly, improve docs
- **Quarterly**: General cleanup and accuracy check

### Dealing with Outdated Docs

If you notice outdated documentation:

1. **Quick fix**: If you can fix it in < 5 minutes, do it immediately
2. **Create an issue**: For larger updates, create a GitHub issue with label `documentation`
3. **Update incrementally**: Don't let perfect be the enemy of good

### Version-Specific Docs

For this project, we maintain **single-version documentation** (latest only). Don't create version-specific docs unless:
- Breaking change requires distinct instructions
- Feature availability differs significantly between versions

In those cases, use callouts:

```markdown
> **Version Note**: The `--transition` flag was added in v2.0. If using v1.x, this option is not available.
```

---

## File Organization

### Current Structure

```
docs/
├── user/                    # End-user documentation
│   ├── quickstart.md
│   ├── docker.md
│   ├── web_interface.md
│   ├── faq.md
│   └── troubleshooting.md
├── dev/                     # Developer documentation
│   ├── architecture.md
│   ├── contributing.md
│   ├── testing.md
│   └── tech_stack.md
├── examples/                # Example files (CSVs, configs)
│   └── README.md
└── CHANGELOG.md             # Version history

ai/
├── session_summaries/       # AI session logs
│   ├── 2025-11-26_session_1.md
│   └── ...
├── future/                  # Future feature plans
│   ├── gui_distribution_plan.md
│   └── ...
├── notes/                   # Development notes
└── doc_instructions.md      # This file

README.md                    # Project landing page
CONTRIBUTING.md              # Contributor quick-start
SECURITY.md                  # Security policy
```

### Naming Conventions

- Use lowercase with underscores: `web_interface.md`, not `WebInterface.md`
- Be descriptive: `google_sheets.md`, not `sheets.md`
- Avoid redundant prefixes: `architecture.md` (not `dev_architecture.md` when in `docs/dev/`)

---

## Examples of Great Documentation

### Example: User-Focused Doc

```markdown
# Quick Start Guide

Get `highlight-cuts` running in 5 minutes.

## Prerequisites

You'll need:
- Python 3.13+ ([download](https://python.org))
- FFmpeg ([install guide](https://ffmpeg.org))

## Installation

\`\`\`bash
git clone https://github.com/yourusername/highlight-cuts.git
cd highlight-cuts
uv sync
\`\`\`

## Your First Highlight Reel

1. Create a CSV file called `clips.csv`:

\`\`\`csv
videoName,startTime,stopTime,playerName
Game1,00:01:30,00:01:40,Alice
Game1,00:05:10,00:05:20,Alice
\`\`\`

2. Run the tool:

\`\`\`bash
uv run highlight-cuts --input-video game.mp4 --csv-file clips.csv --game Game1
\`\`\`

3. Find your video: `Game1_Alice.mp4`

That's it! 🎉

## Next Steps

- [Add more players](usage.md#csv-format)
- [Use Google Sheets](google_sheets.md)
- [Run with Docker](docker.md)
```

### Example: Developer-Focused Doc

```markdown
# Architecture Overview

This document explains the technical design of `highlight-cuts`.

## High-Level Design

\`\`\`mermaid
graph TD
    A[CLI Layer] --> B[Core Logic]
    B --> C[CSV Parser]
    B --> D[Interval Merger]
    B --> E[FFmpeg Wrapper]
    E --> F[Output Videos]
\`\`\`

## Module Breakdown

### `core.py` - Business Logic

**Location**: `src/highlight_cuts/core.py`

**Responsibility**: CSV processing, interval merging, clip planning.

**Key Functions**:

#### `process_csv(csv_path: str, game_name: str) -> pd.DataFrame`

Reads CSV (local or Google Sheets URL) and filters by game.

**Algorithm**:
1. Detect URL vs. file path
2. Download/read CSV
3. Filter by `videoName == game_name`
4. Return DataFrame

**Example**:
\`\`\`python
df = process_csv("clips.csv", "Game1")
# Returns: DataFrame with columns [startTime, stopTime, playerName]
\`\`\`

**Testing**: See `tests/test_core.py:45-67`

[... more details ...]
```

---

## Checklist for New Documentation

Use this checklist when creating a **new** documentation file:

- [ ] File is in correct directory (`docs/user/` or `docs/dev/`)
- [ ] File name follows naming convention (lowercase, underscores)
- [ ] Clear H1 title at the top
- [ ] Front-loaded key information
- [ ] Code examples include syntax highlighting
- [ ] Links use relative paths
- [ ] Cross-referenced from other relevant docs
- [ ] Added to `README.md` (if appropriate)
- [ ] Tone is casual and friendly
- [ ] AI-friendly structure (headings, lists, examples)
- [ ] Diagrams use Mermaid (not ASCII)
- [ ] Session summary created

---

## Questions?

If you're unsure about documentation:
1. Check existing docs for patterns
2. Follow the principle: **Write docs the way you'd want to read them**
3. Optimize for AI and human readers equally
4. When in doubt, err on the side of more detail

Remember: **Good documentation is code**. Treat it with the same care and attention you give to the codebase.
