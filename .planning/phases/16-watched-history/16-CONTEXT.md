# Phase 16 Context — Watched History

## Phase Goal
Add a Watch History page as a first-party replacement for MDBList watched-list sync. Shows all watched movies across sessions in a searchable, paginated view with list and tile layouts. Remove all Phase 14 MDBList watched-sync code cleanly.

---

## Area A: Card Content & Visual Design

### Layout toggle
Two layouts, user-switchable:
- **List layout** — same as SearchPage movie search rows (data-dense, full width)
- **Tile layout** — 3-wide poster grid, smaller scale cards (poster-dominant)

### Data shown on each card/tile
Same data fields used across the app (poster, title, year, runtime, genres, MPAA) plus:
- All ratings badges (RT, IMDB, TMDB) via existing `RatingsBadge` component
- **Watched date** (`watched_at` from `WatchEvent`)
- **Personal rating badge** (1–10, from `WatchEvent.rating`) — bring this back into the system

### Personal rating system
`WatchEvent.rating` (Integer, nullable) is already in the DB from migration 0014. Phase 16 brings back the rating input/display. Shown as an additional badge alongside RT/IMDB/TMDB badges.

### Movie splash dialog
Clicking any movie opens a splash dialog containing:
- Poster + overview
- Full ratings (RT, IMDB, TMDB, personal rating)
- Watched date
- Personal rating input — editable here only (not inline on card)
- "Star/save" action (bookmarks the movie, same save mechanism as GameSession)

**The splash is read-only for all fields except personal rating and the save/star toggle.**

---

## Area B: Sort, Filter & Pagination

### Default sort
Alphabetical (A→Z) by title.

### Sort options
All standard sorts plus two new ones specific to this page:
- Title (A→Z) — default
- Year
- Runtime
- TMDB rating
- RT score
- **Watched date** (most recent first when selected)
- **Personal rating** (highest first when selected)

### Filters
Title search only. No source filter (Plex vs manual), no genre filter.

### Pagination
Use pagination (not infinite scroll). Current library is ~150 titles and growing to 200+. Page size TBD by planner (suggest 24–36 per page to suit both layouts).

---

## Area C: Navigation

### Nav item
- **Label:** Watch History
- **Style:** Text label (no icon) — same treatment as Game Mode and Search
- **Route:** `/watched`
- **Position:** Between Search and Settings in the nav bar

### Updated nav order
`Game Mode | Search | Watch History | ⚙`

### Active state
Use same active-state logic as other nav items (`location.pathname === "/watched"`).

---

## Area D: MDBList Cleanup Scope

### What to REMOVE (Phase 14 code)

**Backend:**
- `_push_watch_to_mdblist` fire-and-forget helper in `mdblist.py`
- All imports and call sites of `_push_watch_to_mdblist` in `game.py` and `movies.py`
- `/watched-sync/start` and `/watched-sync/status` endpoints in `mdblist.py`
- `_SyncState` dataclass and `_run_watched_sync` background task
- `mdblist_list_id` field from `SettingsResponse` and `SettingsUpdateRequest`
- `mdblist_list_id` read/write from `settings.py` router
- `mdblist_synced_at` column — drop via new Alembic migration (next after 0015)

**Frontend:**
- Watch Sync card in `Settings.tsx` (list ID input, confirm dialog, polling progress bar, completion message)
- `startWatchedSync` and `getWatchedSyncStatus` functions in `api.ts`
- `WatchedSyncStatusDTO` type in `api.ts`
- `mdblist_list_id` field from `SettingsDTO` in `api.ts`

**Tests:**
- Delete Phase 14 tests in `test_mdblist.py`: `MDBSYNC-02 _run_watched_sync` test and `MDBSYNC-01 mdblist_synced_at` test
- Delete Phase 14 tests in `test_settings.py` covering `mdblist_list_id`

### What to KEEP (Phase 13 code)
- MDBList API key in Settings
- Nightly backfill UI (trigger button, progress bar, quota counter)
- All RT/IMDB/ratings fetch infrastructure
- `WatchEvent.rating` column — needed for Phase 16 personal rating feature

### DB migration strategy
- Write a new Alembic migration (0016) to `DROP COLUMN mdblist_synced_at` from `watch_events` (batch mode required for SQLite)
- Do NOT reverse migration 0013 — write a forward-only cleanup migration instead
- `rating` column (migration 0014) stays — it's used in Phase 16
- Orphaned `mdblist_list_id` row in `app_settings` DB table: leave it, no cleanup needed

### Global saves table (new scope addition)
The save/star action in the Watch History splash requires a session-independent bookmark. Decision: add a new `global_saves` table (or equivalent) with at minimum `(tmdb_id, saved_at)`. Saves from Watch History must surface as "saved" state when the same movie appears in a game session's eligible movies list. The planner must design:
- New migration for the global saves table
- Backend endpoints: POST/DELETE /movies/{tmdb_id}/save
- Frontend: save state query + mutation in Watch History splash
- GameSession: merge global saves into the saved-movies display (read global_saves alongside session_saves)

---

## Code Context

### Existing assets to reuse
- `RatingsBadge` component (`frontend/src/components/RatingsBadge.tsx`) — handles RT/IMDB/TMDB/Letterboxd badges with variants
- `/movies/watched` endpoint (`backend/app/routers/movies.py:54`) — already exists, returns basic movie data; extend with `watched_at`, `rating`, sort/search/pagination params
- `MovieFilterSidebar` pattern from SearchPage for sort controls
- `EligibleMovieDTO` shape — watched history response DTO should mirror this + add `watched_at: string` and `personal_rating: int | null`
- Card layout pattern from Phase 12 eligible-movies list for tile view

### Phase 14 entry points to remove
- `movies.py:16` — `from app.routers.mdblist import _push_watch_to_mdblist`
- `game.py` — `_push_watch_to_mdblist` call in `mark_current_watched`
- `movies.py` — `_push_watch_to_mdblist` call in `mark_movie_watched`
- `mdblist.py` — `_SyncState`, `_run_watched_sync`, `/watched-sync/start`, `/watched-sync/status`
- `settings.py` — `mdblist_list_id` read/write
