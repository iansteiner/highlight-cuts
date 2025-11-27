# Server-Side Google Sheets Tracking Feature

**Date:** 2025-11-26
**Status:** Future Enhancement - Not Currently Planned

## Context

Multiple users share Google Sheets files for highlight clip generation. Users currently paste the Google Sheets URL each time they use the application. The URL is only stored in browser `localStorage` (client-side), which means:
- URLs are not shared between users
- URLs are not shared between browsers/devices
- No easy way to switch between multiple frequently-used sheets

**User Request:** Add server-side tracking of Google Sheets files by name (not URL) so users can:
- Save sheets with friendly names (e.g., "Spring Tournament 2025")
- Select from a dropdown of saved sheets
- Share sheet collections with other users

## Current Architecture

The application is **completely stateless**:
- No database or persistent storage
- No user authentication or identification
- Google Sheets URLs stored only in browser `localStorage`
- Each request downloads fresh data from Google Sheets
- Simple, clean architecture focused on video processing

**Key Files:**
- `src/highlight_cuts/core.py:46-70` - `normalize_sheets_url()` converts any Google Sheets URL to CSV export format
- `src/highlight_cuts/web.py` - FastAPI application (415 lines)
- `src/highlight_cuts/templates/index.html` - Web UI with HTMX (412 lines)

## Exploration Summary

This feature would require introducing:
1. **Database layer** (currently none exists)
2. **Persistent storage** for sheet metadata
3. **API endpoints** for CRUD operations on saved sheets
4. **UI changes** for sheet selection and management
5. **Potentially authentication** for multi-user scenarios

This represents a significant architectural shift from stateless to stateful.

---

## Option 1: Simple Shared Registry (No User Auth)

### How It Works
- Add SQLite database to store sheet metadata
- Anyone can save a sheet with a friendly name
- Anyone can select from saved sheets via dropdown
- No user accounts - just a shared pool
- Track: `name`, `url`, `created_at`, `last_used_at`, `use_count`

### Pros
- ✅ Minimal complexity - no authentication needed
- ✅ Fast to implement (~4-6 hours)
- ✅ Easy sharing - users just select from dropdown
- ✅ Non-breaking - current workflow still works (paste URL)
- ✅ Simple deployment - SQLite embedded, no additional services

### Cons
- ❌ No ownership tracking (can't tell who added what)
- ❌ No access control (anyone can see/use any sheet)
- ❌ Potential naming conflicts (two users want same name)
- ❌ No way to delete/edit if someone makes a mistake
- ❌ Trust-based system (suitable only for small teams)

### Implementation Complexity: **Low (4-6 hours, ~235 lines of code)**

#### Database Schema
```sql
CREATE TABLE sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,  -- e.g., "Spring Tournament 2025"
    url TEXT NOT NULL,           -- Full Google Sheets URL
    sheet_id TEXT,               -- Extracted sheet ID (for deduplication)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    notes TEXT                   -- Optional description
);
```

#### Code Changes Required
- **New:** `src/highlight_cuts/db.py` (~100 lines)
  - SQLite setup and CRUD operations
- **Modified:** `src/highlight_cuts/web.py` (~50 lines added)
  - `POST /sheets/save` - Save sheet with name
  - `GET /sheets/list` - Get all sheets as JSON
  - `DELETE /sheets/{id}` - Remove sheet
- **Modified:** `src/highlight_cuts/templates/index.html` (~80 lines)
  - Dropdown for saved sheets
  - "Save this sheet" button with name input
  - Auto-populate URL when sheet selected

#### Dependencies
- Built-in `sqlite3` module (or `sqlalchemy` for ORM)

---

## Option 2: User-Scoped Collections (Simple Auth)

### How It Works
- Add user identification (username/password or JWT tokens)
- Each user has their own collection of saved sheets
- Users can mark sheets as "shared" (visible to all) or "private"
- Track ownership: who added which sheet
- Allow users to delete only their own sheets

### Pros
- ✅ Personal collections - each user manages their own
- ✅ Sharing control - opt-in to share with others
- ✅ Ownership tracking - know who added what
- ✅ Deletion capability - users can clean up their own lists
- ✅ Scalable - works for larger teams

### Cons
- ❌ Moderate complexity - authentication system required
- ❌ User management overhead - account creation, password resets
- ❌ Longer implementation (~15-20 hours)
- ❌ Additional dependencies - JWT, password hashing

### Implementation Complexity: **Medium (15-20 hours, ~620 lines of code)**

#### Database Schema
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 0
);
```

#### Code Changes Required
- **New:** `src/highlight_cuts/db.py` (~200 lines)
  - User and sheet CRUD with ownership filtering
- **New:** `src/highlight_cuts/auth.py` (~150 lines)
  - JWT token generation/validation
  - Password hashing (bcrypt)
  - Login/logout endpoints
  - Authentication middleware
- **Modified:** `src/highlight_cuts/web.py` (~120 lines added)
  - Auth endpoints (register, login)
  - Sheet endpoints with ownership checks
  - Protected routes with auth middleware
- **Modified:** `src/highlight_cuts/templates/index.html` (~150 lines)
  - Login/register forms
  - User account section
  - "My Sheets" vs "Shared Sheets" tabs

#### Dependencies
- `PyJWT` - JWT tokens
- `passlib[bcrypt]` - Password hashing
- `sqlalchemy` - ORM

---

## Option 3: Team-Based Collections (Mid-Complexity Auth)

### How It Works
- Hybrid of Options 1 and 2
- Simple "team code" system (like a shared password)
- Each team has their own shared pool of sheets
- No individual user accounts - just team membership
- Users enter team code on first visit, stored in browser

### Pros
- ✅ Multi-team support - different groups don't clash
- ✅ Simple auth model - just a team code
- ✅ Shared ownership - anyone in team can manage sheets
- ✅ Privacy between teams - teams don't see each other's sheets
- ✅ Moderate complexity - simpler than full user auth

### Cons
- ❌ No individual ownership tracking
- ❌ Team code sharing required (security consideration)
- ❌ No audit trail (can't tell who did what within team)
- ❌ If team code leaks, whole team is exposed

### Implementation Complexity: **Medium-Low (8-12 hours, ~300 lines of code)**

#### Database Schema
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(id),
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 0
);
```

#### Code Changes Required
- **New:** `src/highlight_cuts/db.py` (~120 lines)
- **Modified:** `src/highlight_cuts/web.py` (~80 lines added)
  - Team join/create endpoints
  - Team-scoped sheet operations
- **Modified:** `src/highlight_cuts/templates/index.html` (~100 lines)
  - Team code entry modal
  - Team name display

---

## Database Technology Options

### SQLite (Recommended for Start)
- ✅ Zero configuration, embedded
- ✅ No additional Docker containers
- ✅ Perfect for small-medium teams
- ✅ File-based, easy backups
- ❌ Single-writer limitation (low concurrency)
- ❌ Not suitable for >100 concurrent users

### PostgreSQL (For Production Scale)
- ✅ Production-grade, high concurrency
- ✅ Better for multi-user scenarios
- ✅ Advanced features (JSON columns, full-text search)
- ❌ Requires separate container in docker-compose
- ❌ More operational complexity

---

## Comparison Matrix

| Option | Time | Code | Auth | Best For |
|--------|------|------|------|----------|
| **Option 1: Shared Registry** | 4-6h | ~235 LOC | None | Small trusted teams |
| **Option 3: Team Codes** | 8-12h | ~300 LOC | Team-based | Multiple independent groups |
| **Option 2: User Auth** | 15-20h | ~620 LOC | Full user accounts | Large orgs, audit needs |

---

## Security Considerations

Even for simple implementations, consider:

1. **Input Validation:**
   - Sanitize sheet names (prevent SQL injection, XSS)
   - Validate URLs are actually Google Sheets
   - Limit name length (e.g., 100 chars)

2. **Rate Limiting:**
   - Prevent spam creation of sheets
   - Limit saves per IP per hour

3. **Data Privacy:**
   - Google Sheets URLs contain sheet IDs (act like passwords)
   - Anyone with URL can access sheet data
   - Consider visibility when displaying saved sheets

4. **Deletion Policy:**
   - Who can delete sheets?
   - Soft delete vs hard delete?
   - Audit log for deletions?

---

## Key Decision Points

Before implementing, clarify:

1. **User Model:** Single trusted team or multiple independent groups?
2. **Scale:** How many people will use this? (affects DB choice)
3. **Privacy:** All sheets visible to everyone, or access control needed?
4. **Naming Conflicts:** What if two people save a sheet with the same name?
5. **Sheet Lifecycle:** Should old/unused sheets be automatically removed?

---

## Recommended Approach

**Start with Option 1 (Simple Shared Registry)** if this feature is pursued:

### Rationale
1. **Aligns with current trust model** - shared access to videos already exists
2. **Minimal disruption** - keeps stateless architecture mostly intact
3. **Fast validation** - test feature value before larger investment
4. **Easy upgrade path** - can add auth later if needed
5. **Low risk** - small code footprint, easy to revert

### Evolution Path
- **If naming conflicts arise** → upgrade to Option 3 (team codes)
- **If ownership tracking needed** → upgrade to Option 2 (user auth)
- **If it works well as-is** → keep it simple

### Implementation Roadmap (Option 1)

**Phase 1: Backend Storage (2-3 hours)**
1. Add SQLite database with simple schema
2. Create `db.py` with CRUD operations
3. Initialize database on app startup
4. Write tests for database operations

**Phase 2: API Endpoints (1-2 hours)**
1. `POST /sheets/save` - Save sheet URL with name
2. `GET /sheets/list` - Get all saved sheets
3. `PUT /sheets/{id}` - Update sheet name/URL
4. `DELETE /sheets/{id}` - Remove sheet

**Phase 3: UI Integration (2-3 hours)**
1. Dropdown to select from saved sheets
2. "Save this sheet" button with name input
3. Auto-populate URL when sheet selected
4. Show usage count or last used date

**Phase 4: Polish (1 hour)**
1. Validation (unique names, valid URLs)
2. Error handling and user feedback
3. Sort by most recently used
4. Optional: Search/filter saved sheets

---

## Why Not Pursuing Now

**Decision: Avoiding this complexity for now**

The current architecture is intentionally stateless and simple:
- Users can bookmark Google Sheets URLs in their browser
- Users can share Google Sheets URLs via Slack/email/docs
- The application focuses on video processing, not data management
- Adding persistence introduces maintenance burden and deployment complexity

This feature would represent a significant architectural shift that requires:
- Database management and backups
- Schema migrations
- Potentially authentication system
- More complex deployment (database container/service)
- Ongoing maintenance of data layer

**Current workflow is sufficient:**
- Users can share Google Sheets URLs directly
- Browser `localStorage` provides basic persistence per device
- Team can maintain a shared document with commonly-used sheet URLs

---

## Future Reconsideration Triggers

Consider implementing if:
- Team grows beyond ~10 people (naming/sharing becomes painful)
- Users request this feature multiple times
- Need to track which sheets are actively used (analytics)
- Want to enforce sheet naming conventions
- Need audit trail of who uses which sheets

---

## Related Documents

- [Interactive Clip Editing](./interactive_clip_editing.md) - Another future feature that would add state management
- [Architecture Documentation](../docs/architecture.md) - Current stateless design
- [Google Sheets Integration](../docs/google_sheets.md) - How sheets currently work

---

## Session Notes

**Date Explored:** 2025-11-26
**Explored With:** Claude Code exploration agent
**Outcome:** Documented for future reference, not implementing now
**Key Insight:** Adding database persistence is a major architectural change; current simple approach is working well for the use case
