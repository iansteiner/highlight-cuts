# Interactive Clip Editing Feature Options

**Date:** 2025-11-26
**Status:** Future Enhancement - Not Currently Planned

## Context

Currently, the application generates highlight clips based on a Google Sheet where clips can be marked as disabled using an `include` column. Disabled clips are displayed in the UI (greyed out with red background and 50% opacity) but are excluded from the generated video.

The user has considered adding interactive features to allow:
1. Clicking on clips to enable/disable them dynamically in the UI
2. Editing timestamps directly in the UI

## Current Architecture

The current system is **stateless and document-driven**:
- Google Sheet CSV is the single source of truth
- Each request re-reads the CSV (no server-side session state)
- No client-side clip data manipulation
- Simple, elegant, reliable architecture

**Key Files:**
- `src/highlight_cuts/web.py:515-571` - `/get-clips` endpoint that generates the clips table
- `src/highlight_cuts/web.py:303-386` - `/process` endpoint that processes videos
- `src/highlight_cuts/core.py:101-212` - `process_csv()` function that loads and filters clips
- `src/highlight_cuts/templates/index.html` - Frontend with HTMX integration

## Option 1: Client-Side State Only (Recommended)

### How It Works
- Load clips from CSV as currently done
- Store clips in JavaScript state array
- Add click handlers to toggle individual clips on/off
- Add inline editing for timestamps
- When user clicks "Generate Highlights", send the **modified clip list** to the backend
- Backend processes the clips as received (ignoring CSV for this request)

### Pros
- Minimal backend changes
- Fast UI interactions
- Non-destructive (doesn't modify the Google Sheet)
- Users can experiment freely
- Easy upgrade path to add persistence later

### Cons
- Changes are lost on page refresh (unless localStorage is added)
- Doesn't update the source spreadsheet
- Two sources of truth (CSV + UI state)

### Complexity
**Low-Medium** (4-6 hours of work)

### Implementation Summary

**Frontend Changes (~150 lines):**
1. Add checkbox column to clips table for toggling `included` status
2. Make timestamp fields editable (input fields or contenteditable)
3. Add JavaScript state management:
   ```javascript
   let currentClips = []; // Store active clip list
   ```
4. Add event handlers for:
   - Checkbox changes (toggle included state)
   - Timestamp edits (with validation)
   - Form submission (include clip data as JSON)
5. Update row styling dynamically when clips are toggled

**Backend Changes (~80 lines):**
1. Modify `/process` endpoint to accept optional `clip_overrides` parameter:
   ```python
   clip_overrides: Optional[str] = Form(None)
   ```
2. If `clip_overrides` provided, parse JSON and use instead of calling `process_csv()`
3. Add validation for timestamp formats and clip data structure

**What Stays Simple:**
- CSV parsing logic (unchanged)
- Video processing logic (unchanged)
- File management (unchanged)
- Background task processing (unchanged)

**What Gets More Complex:**
- Frontend state management (new JavaScript state)
- Form submission (now includes JSON data)
- Backend endpoint (conditional logic for overrides)
- Validation (timestamp format checking in JS and Python)

### Estimated Code Changes
- ~100 lines of JavaScript for state management
- ~50 lines of HTML changes for editable table
- ~30 lines of Python for override handling
- ~50 lines for validation logic
- **Total: ~230 lines of code** (mostly additive)

---

## Option 2: Sync Back to Google Sheet

### How It Works
- Same as Option 1, but also write changes back to Google Sheets
- Use Google Sheets API to update the `include` column and timestamps
- Requires OAuth authentication or service account credentials

### Pros
- Single source of truth maintained
- Changes persist across sessions and devices
- Other users see the updates
- Professional multi-user workflow

### Cons
- Significantly more complex
- Requires Google Sheets API setup
- Authentication complexity (OAuth flow or service account)
- Race conditions possible with concurrent edits
- Permission management challenges
- API rate limits and error handling
- Harder to rollback mistakes

### Complexity
**High** (15-20 hours of work)

### Additional Requirements
- Google Sheets API integration (google-api-python-client)
- Authentication system (OAuth2 or service account JSON)
- Conflict resolution logic for concurrent edits
- Comprehensive error handling for API failures
- User permission verification
- Rate limiting and retry logic

---

## Option 3: Hybrid - Local Overrides with Persistence

### How It Works
- Load clips from CSV (base state)
- Allow UI edits stored in localStorage as "overrides"
- On processing, merge: CSV data + localStorage overrides
- Provide "Reset to Sheet" button to clear overrides
- Show visual indicator when overrides are active

### Pros
- Changes persist in browser across sessions
- No backend changes required for editing
- Non-destructive to source
- Good middle ground between Options 1 and 2
- Users can experiment with local changes before committing to sheet

### Cons
- Per-browser state (doesn't sync across devices)
- Slightly more complex UI logic
- Need to handle CSV updates gracefully (merge or override?)
- Can become confusing if sheet and overrides diverge significantly

### Complexity
**Medium** (8-12 hours of work)

### Additional Considerations
- localStorage key management (per game/player combination)
- UI to show which clips have local overrides
- Conflict resolution when CSV changes
- Export/import of overrides for sharing
- Storage size limits in localStorage

---

## Recommendation

**Start with Option 1 (Client-Side State Only)** if this feature is pursued in the future.

### Rationale

1. **Minimal disruption:** Current architecture stays mostly intact
2. **Fast iteration:** Can quickly test if this feature provides value
3. **Non-destructive:** Users can experiment without fear of breaking the sheet
4. **Low risk:** Easy to revert if it doesn't work out
5. **Upgrade path:** Can add localStorage (Option 3) or API sync (Option 2) later if needed

### Suggested Incremental Implementation

If implementing Option 1, build incrementally:

1. **Phase 1:** Add toggle checkboxes for enable/disable only
   - Simplest possible version
   - Test core concept and user reception

2. **Phase 2:** Add timestamp editing
   - Inline editable fields
   - Validation and error feedback

3. **Phase 3:** Add visual feedback and polish
   - Real-time row styling updates
   - Undo/redo functionality
   - "Reset to Sheet" button

4. **Phase 4 (Optional):** Add localStorage persistence
   - Upgrade to Option 3
   - Only if users request it

### Why Not the Other Options?

- **Option 2:** Too much complexity for uncertain value. Google Sheets API adds significant maintenance burden and security considerations. Only pursue if multi-user editing becomes a clear requirement.

- **Option 3:** Better as an upgrade from Option 1 rather than starting point. Build the core functionality first, then add persistence only if users need it.

---

## Decision

**Status: Not pursuing at this time**

The current document-driven architecture is clean, reliable, and sufficient for current needs. Users can edit the Google Sheet directly if they need to change clip selections or timestamps. The interactive editing feature would add complexity without a clear immediate benefit.

This document will be preserved for future reference if requirements change.
