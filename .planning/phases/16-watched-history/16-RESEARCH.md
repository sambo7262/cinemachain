# Phase 16: Watched History — Research

**Researched:** 2026-04-01
**Domain:** Full-stack feature addition + Phase 14 code removal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area A: Card Content & Visual Design**
- Two layouts, user-switchable: List layout (same as SearchPage rows) and Tile layout (3-wide poster grid, poster-dominant)
- Data fields: poster, title, year, runtime, genres, MPAA + all ratings badges (RT, IMDB, TMDB) via existing RatingsBadge + watched_at + personal rating badge (1–10)
- WatchEvent.rating (Integer, nullable) already in DB from migration 0014
- Splash dialog: poster + overview + full ratings + watched date + personal rating input (editable here only) + star/save action
- Splash is read-only except for personal rating and save/star toggle

**Area B: Sort, Filter & Pagination**
- Default sort: Alphabetical (A→Z) by title
- Sort options: Title, Year, Runtime, TMDB rating, RT score, Watched date (most recent first), Personal rating (highest first)
- Filter: title search only — no source filter, no genre filter
- Pagination (not infinite scroll); page size TBD by planner (suggest 24–36)

**Area C: Navigation**
- Label: Watch History, text label (no icon)
- Route: /watched
- Position: between Search and Settings in nav bar
- Updated order: `Game Mode | Search | Watch History | settings-icon`
- Active state: `location.pathname === "/watched"`

**Area D: MDBList Cleanup Scope**

Backend to remove:
- `_push_watch_to_mdblist` helper in mdblist.py
- All imports and call sites of `_push_watch_to_mdblist` in game.py and movies.py
- `/watched-sync/start` and `/watched-sync/status` endpoints in mdblist.py
- `_SyncState` dataclass and `_run_watched_sync` background task
- `mdblist_list_id` field from SettingsResponse and SettingsUpdateRequest
- `mdblist_list_id` read/write from settings.py router
- `mdblist_synced_at` column — drop via new Alembic migration (next after 0015)

Frontend to remove:
- Watch Sync card in Settings.tsx (list ID input, confirm dialog, polling progress bar, completion message)
- `startWatchedSync` and `getWatchedSyncStatus` functions in api.ts
- `WatchedSyncStatusDTO` type in api.ts
- `mdblist_list_id` field from SettingsDTO in api.ts

Tests to remove:
- Phase 14 tests in test_mdblist.py: MDBSYNC-02 `_run_watched_sync` test and MDBSYNC-01 `mdblist_synced_at` test
- Phase 14 tests in test_settings.py covering `mdblist_list_id`

What to KEEP:
- MDBList API key in Settings
- Nightly backfill UI (trigger button, progress bar, quota counter)
- All RT/IMDB/ratings fetch infrastructure
- WatchEvent.rating column — needed for Phase 16 personal rating feature

DB migration strategy:
- Write a new Alembic migration to DROP COLUMN mdblist_synced_at from watch_events
- Do NOT reverse migration 0013 — write a forward-only cleanup migration instead
- rating column (migration 0014) stays

### Claude's Discretion

No items designated Claude's discretion in CONTEXT.md — all areas have locked decisions.

### Deferred Ideas (OUT OF SCOPE)

No deferred ideas section present in CONTEXT.md.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WATCHED-01 | Watch History nav item appears alongside Game Mode and Search | NavBar.tsx extension pattern documented; route addition in App.tsx documented |
| WATCHED-02 | Shows all watched movies in tile or grid layout (user-toggleable), searchable by title | Backend GET /movies/watched extension + WatchedMovieDTO + frontend WatchHistoryPage component pattern documented |
| WATCHED-03 | All Phase 14 MDBList watched-sync code removed | Exhaustive line-level removal inventory below |
</phase_requirements>

---

## Summary

Phase 16 has two parallel concerns: building the Watch History page as a new first-party feature, and surgically removing Phase 14 MDBList watch-sync code. Both are well-understood with clear patterns available in the existing codebase.

The backend work centers on extending the existing `GET /movies/watched` endpoint (currently 18 lines returning 4 fields with no params) into a full paginated, sorted, searchable endpoint that joins `WatchEvent` fields alongside `Movie` fields. This mirrors the pattern already established by `GET /sessions/{id}/eligible-movies` in game.py. A new `WatchedMovieDTO` is needed because it carries `watched_at` and `personal_rating` — fields that do not exist on `EligibleMovieDTO`. A new `PATCH /movies/{tmdb_id}/rating` endpoint is also needed; no such endpoint currently exists.

The frontend work reuses existing primitives almost entirely: the `Dialog` + `RatingsBadge` components, the SearchPage table layout for list mode, and the `MovieCard` component for tile mode. The WatchHistoryPage is a new page component with its own sort/search/pagination state — it does not extend or share state with SearchPage.

The Phase 14 removal is entirely mechanical: every call site, import, DTO field, and UI block has been identified at exact line numbers.

**Primary recommendation:** Implement in three plans — (1) backend endpoint extension + personal rating PATCH + Alembic migration 0016; (2) Phase 14 removal (backend + frontend + tests); (3) frontend WatchHistoryPage component.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | project-pinned | Backend route definition | Already in use; Query() for typed params |
| SQLAlchemy async | project-pinned | ORM query with join | Already in use; see eligible-movies join pattern |
| Alembic | project-pinned | DB migration for DROP COLUMN | Already in use; batch mode required for SQLite |
| React + TanStack Query | project-pinned | Frontend page + data fetching | Already in use throughout app |
| shadcn/ui Dialog, Button, Badge, Input | project-pinned | UI primitives | Already in use in SearchPage splash |
| lucide-react | project-pinned | Icons if needed | Already in use in NavBar |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-router-dom | project-pinned | `/watched` route + active state | NavBar and App.tsx extension |
| Pydantic BaseModel | project-pinned | WatchedMovieDTO response schema | Typed FastAPI response model |

---

## Architecture Patterns

### Recommended Project Structure

New files:
```
frontend/src/pages/WatchHistoryPage.tsx       # new page component
backend/alembic/versions/20260401_0016_drop_mdblist_synced_at.py  # new migration
```

Modified files:
```
backend/app/routers/movies.py      # extend GET /movies/watched, add PATCH /{tmdb_id}/rating
backend/app/routers/mdblist.py     # remove _SyncState, _run_watched_sync, /watched-sync/* endpoints
backend/app/routers/game.py        # remove _push_watch_to_mdblist import and call site
backend/app/routers/settings.py    # remove mdblist_list_id from both models
backend/app/models/__init__.py     # remove mdblist_synced_at mapped_column from WatchEvent
frontend/src/lib/api.ts            # add getWatchedHistory(), addRating(); remove sync functions/DTO
frontend/src/components/NavBar.tsx # add Watch History nav link
frontend/src/App.tsx               # add /watched route
frontend/src/pages/Settings.tsx    # remove Watch Sync card + associated state
backend/tests/test_mdblist.py      # delete Phase 14 tests
backend/tests/test_settings.py     # delete mdblist_list_id test
```

### Pattern 1: Extended GET /movies/watched with join + sort + search + pagination

The current endpoint (movies.py:54–71) does a simple `select(Movie).join(WatchEvent)`. The extension must also select `WatchEvent.watched_at` and `WatchEvent.rating` fields. The pattern mirrors `get_eligible_movies` in game.py, which uses Python-side sort (null-stable two-pass) and sliced pagination.

The key difference from eligible-movies: the watched endpoint must JOIN both tables and return columns from both. The cleanest approach is selecting both models explicitly.

**Query pattern:**
```python
# Source: existing game.py eligible-movies pattern
result = await db.execute(
    select(Movie, WatchEvent)
    .join(WatchEvent, WatchEvent.tmdb_id == Movie.tmdb_id)
    .where(Movie.title.ilike(f"%{search}%") if search else sa.true())
)
rows = result.all()
# Build dicts from (movie, watch_event) pairs, then sort + paginate in Python
```

**WatchedMovieDTO shape:**
```python
class WatchedMovieDTO(BaseModel):
    tmdb_id: int
    title: str
    year: int | None
    poster_path: str | None
    vote_average: float | None
    genres: str | None          # JSON string, same as EligibleMovieDTO
    runtime: int | None
    mpaa_rating: str | None
    overview: str | None
    rt_score: int | None
    rt_audience_score: int | None
    imdb_id: str | None
    imdb_rating: float | None
    metacritic_score: int | None
    letterboxd_score: float | None
    mdb_avg_score: float | None
    watched_at: str             # ISO 8601 datetime string
    personal_rating: int | None  # WatchEvent.rating
```

**Why not reuse EligibleMovieDTO:** EligibleMovieDTO carries `watched: bool`, `selectable: bool`, `via_actor_name`, `saved: bool`, `shortlisted: bool` — none of these are relevant to watch history. WatchedMovieDTO adds `watched_at` and `personal_rating`. Keeping them separate avoids misleading fields in both directions.

**Sort keys for the endpoint:**
- `title` (default) — alphabetical, Python `str.lower()`
- `year` — null-stable two-pass
- `runtime` — null-stable two-pass
- `rating` — TMDB vote_average, null-stable two-pass (matches existing eligible-movies convention)
- `rt` — rt_score, null-stable two-pass
- `watched_at` — from WatchEvent; default desc (most recent first); null-stable
- `personal_rating` — from WatchEvent.rating; default desc (highest first); null-stable

**Paginated response envelope:**
```python
class WatchedMoviesResponse(BaseModel):
    items: list[WatchedMovieDTO]
    total: int
    page: int
    page_size: int
    has_more: bool
```

This matches `PaginatedMoviesDTO` already in api.ts; the frontend type can be `PaginatedWatchedMoviesDTO` extending the same shape but with `WatchedMovieDTO` items.

### Pattern 2: PATCH /movies/{tmdb_id}/rating

No such endpoint currently exists. Simplest implementation:

```python
class RatingUpdate(BaseModel):
    rating: int | None  # None clears the rating

@router.patch("/{tmdb_id}/rating")
async def set_movie_rating(
    tmdb_id: int,
    body: RatingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Set or clear the personal rating on a WatchEvent."""
    result = await db.execute(
        select(WatchEvent).where(WatchEvent.tmdb_id == tmdb_id)
    )
    we = result.scalar_one_or_none()
    if we is None:
        raise HTTPException(status_code=404, detail="No watch event found for this movie")
    if body.rating is not None and not (1 <= body.rating <= 10):
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 10")
    we.rating = body.rating
    await db.commit()
    return {"tmdb_id": tmdb_id, "rating": we.rating}
```

**Route ordering risk:** `/{tmdb_id}/rating` must be declared BEFORE `/{tmdb_id}` in movies.py to prevent FastAPI from routing "rating" as a tmdb_id integer. Currently `/{tmdb_id}` is at line 230. New PATCH endpoint must appear earlier in the file (or FastAPI path-parameter routing will attempt to cast "rating" as int and fail with a 422, not a 404). Actually FastAPI will only route GET /{tmdb_id} for GET requests and PATCH /{tmdb_id}/rating for PATCH requests — different HTTP methods, so ordering is safe. But defensive placement before the catch-all GET is still recommended.

### Pattern 3: Alembic migration 0016 — DROP COLUMN mdblist_synced_at (SQLite batch mode)

**Critical SQLite constraint:** SQLite does not support `ALTER TABLE DROP COLUMN` natively prior to version 3.35.0. Even on newer versions, SQLAlchemy's Alembic generates `batch_alter_table` context for SQLite. The project uses SQLite in development (confirmed by existing migrations using `op.add_column` without batch mode for ADD, but DROP requires batch mode).

**Confirmed pattern from Alembic docs:** For SQLite DROP COLUMN, always use batch mode:

```python
# Source: Alembic documentation — SQLite ALTER TABLE batch operations
def upgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.drop_column("mdblist_synced_at")

def downgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.add_column(sa.Column("mdblist_synced_at", sa.DateTime(), nullable=True))
```

**Migration file naming:** Follow existing convention: `20260401_0016_drop_mdblist_synced_at.py`
- `revision = "0016"`
- `down_revision = "0015"`

**Model update:** Remove `mdblist_synced_at` mapped_column from `WatchEvent` in models/__init__.py (line 81) alongside the migration. SQLAlchemy model must stay in sync with the schema.

### Pattern 4: Phase 14 Removal — Exhaustive Inventory

**backend/app/routers/mdblist.py**
- Lines 22–64: `_push_watch_to_mdblist` async function — delete entirely
- Lines 79–88: `_SyncState` dataclass + `_sync_state` instance — delete entirely
- Lines 91–158: `_run_watched_sync` async function — delete entirely
- Lines 327–350: `start_watched_sync` endpoint — delete entirely
- Lines 354–375: `watched_sync_status` endpoint — delete entirely
- Line 7: `from dataclasses import dataclass` import — keep (still used by `_BackfillState`)
- Line 11: `from sqlalchemy import select, or_, func, asc, nulls_first` — keep (used by backfill)
- Line 14: `from app.models import Movie, WatchEvent` — keep `Movie`; after removal, `WatchEvent` is only needed by the removed sync functions. Verify whether `WatchEvent` is still referenced in remaining backfill code. After checking: `WatchEvent` appears only in `_push_watch_to_mdblist` and `start_watched_sync`/`watched_sync_status`. Remove `WatchEvent` from the import after deletion.

**backend/app/routers/movies.py**
- Line 16: `from app.routers.mdblist import _push_watch_to_mdblist` — delete this entire line
- Lines 320–330: `BackgroundTasks` usage block inside `mark_movie_watched` that calls `_push_watch_to_mdblist` — delete lines 321–330 (the imdb_id resolve query and the `background_tasks.add_task(...)` block). Also remove `BackgroundTasks` from the function signature at line 304 if it is no longer needed. Check: `mark_movie_watched` currently uses `BackgroundTasks` only for this call. After removal, `BackgroundTasks` is unused in that endpoint — remove it from the import and function signature.
- Line 7: `from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request` — remove `BackgroundTasks` from this import after removal above.

**backend/app/routers/game.py**
- Line 21: `from app.routers.mdblist import _push_watch_to_mdblist` — delete this line
- Lines 1267–1276: The comment "# Resolve imdb_id for MDBList push" + the imdb_id query + `background_tasks.add_task(_push_watch_to_mdblist, ...)` block (4 lines) — delete these lines. The `background_tasks.add_task(_update_session_suggestions, session_id)` call on line 1277 must REMAIN. The `_imdb_result` variable and `_imdb_id` variable at lines 1268–1271 are only used to feed `_push_watch_to_mdblist` — delete them too.
- **IMPORTANT:** `BackgroundTasks` in game.py's `mark_current_watched` is still needed for `_update_session_suggestions` (line 1277). Do NOT remove it from the game.py function signature.

**backend/app/routers/settings.py**
- Line 23: `mdblist_list_id: str | None = None` in `SettingsResponse` — delete
- Line 37: `mdblist_list_id: str | None = None` in `SettingsUpdateRequest` — delete

**backend/app/models/__init__.py**
- Line 81: `mdblist_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)` — delete (schema removed by migration 0016)

**backend/tests/test_mdblist.py**
Delete the following test functions (all are already `pytest.skip` stubs, but they reference removed symbols):
- Lines 213–215: `test_bulk_sync_queries_unsynced`
- Lines 218–221: `test_watched_sync_status_endpoint`
- Lines 229–237: `test_realtime_push_enqueued_on_mark_watched`
- Lines 234–237: `test_realtime_push_enqueued_on_query_mode_watched`
- Lines 240–243: `test_realtime_push_skipped_when_unconfigured`
- Lines 247–249: `test_synced_at_written_on_success_only`
The first three test functions (test_parse_all_rating_sources, test_score_average_stored, test_imdbid_stored, test_backfill_status_schema) MUST be kept — they test Phase 13 backfill code that is staying.

**backend/tests/test_settings.py**
- Lines 76–79: `test_settings_accepts_mdblist_list_id` function — delete

**frontend/src/lib/api.ts**
- Lines 152: `mdblist_list_id: string | null` in `SettingsDTO` — delete
- Lines 161–167: `WatchedSyncStatusDTO` interface — delete
- Lines 340–344: `startWatchedSync` and `getWatchedSyncStatus` in the `mdblist` namespace — delete both functions (keep `startBackfill` and `getBackfillStatus`)

**frontend/src/pages/Settings.tsx**
- Lines 21: `mdblist_list_id: "",` in `emptyForm` — delete
- Lines 54–59: `syncRunning`, `syncStatus`, `syncDone`, `showSyncConfirm` state declarations — delete all four
- Lines 87–92: `api.mdblist.getWatchedSyncStatus()` call in the mount effect — delete these lines (keep the backfill status check above)
- Lines 110–123: The entire `syncRunning` polling `useEffect` — delete
- Lines 176–192: `handleSyncClick` and `handleSyncConfirm` handler functions — delete both
- Lines 387–469: The entire "MDBList Watch Sync" `<Card>` block (from `{/* MDBList Watch Sync */}` to closing `</Card>`) — delete
- **Note on `emptyForm` type:** After removing `mdblist_list_id`, the `FieldErrors` type uses `keyof SettingsDTO` which will no longer include that key — this is a safe change with no cascading effect.

### Pattern 5: WatchHistoryPage component structure

The page has two modes (list view / tile view) with shared sort+search+pagination state. This is similar to SearchPage but simpler: no genre chips, no sidebar filters, no "person search" mode.

**State:**
```typescript
const [view, setView] = useState<"list" | "tile">("list")
const [searchInput, setSearchInput] = useState("")
const [debouncedSearch, setDebouncedSearch] = useState("")
const [sortCol, setSortCol] = useState<WatchedSortCol>("title")
const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")  // title sorts asc by default
const [page, setPage] = useState(1)
const [splashMovie, setSplashMovie] = useState<WatchedMovieDTO | null>(null)
const [splashOpen, setSplashOpen] = useState(false)
const [pendingRating, setPendingRating] = useState<number | null>(null)
```

**Data fetching:** Single `useQuery` hitting `api.getWatchedHistory(params)`. Because sort and pagination are handled server-side (backend), the queryKey includes all params:
```typescript
queryKey: ["watchedHistory", { sort: sortCol, sort_dir: sortDir, search: debouncedSearch, page }]
```

**List view:** Reuse the `<table>` pattern from SearchPage verbatim, with additional columns for Watched Date and Personal Rating. The `RatingsBadge` component is used in the Ratings column.

**Tile view:** A CSS grid of 3 columns (`grid grid-cols-3 gap-3`). Each tile uses the existing `MovieCard` component, which already displays poster, title, year, runtime, genres, MPAA, and vote_average. For watch history tiles, `MovieCard` needs `watched_at` and `personal_rating` displayed — these are not in MovieCard's current props. **Options:**
  1. Add optional `watched_at?: string` and `personal_rating?: number | null` props to `MovieCard` (displayed if present)
  2. Build a `WatchedTile` inline variant without changing MovieCard

**Recommendation:** Option 1 — add the two optional props to MovieCard. This is a backward-compatible additive change (MovieCard renders them only when truthy). It avoids code duplication of the entire card structure.

### Pattern 6: Splash dialog for Watch History

The existing SearchPage `Dialog` uses `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` from `@/components/ui/dialog`. The same imports work directly in WatchHistoryPage. There is no shared extracted dialog component — each page inlines its own Dialog JSX.

**WatchHistory splash additions vs SearchPage splash:**
- Add watched_at display (formatted date string)
- Add personal rating display badge
- Add personal rating input (1–10 number input, or 10-button star-picker)
- Replace "Download via Radarr" / "Watch Online" action buttons with a single "Save" (star/bookmark) button

**Personal rating input pattern:** A simple `<Input type="number" min={1} max={10}>` in the splash footer. On change, call `api.setMovieRating(tmdb_id, rating)` with a PATCH. Optimistic update: update `pendingRating` state locally, invalidate `watchedHistory` query on success. Show "Saved" confirmation briefly.

### Pattern 7: Save/star action from Watch History splash

**The question:** The existing `SessionSave` model is scoped to a `(session_id, tmdb_id)` pair. Watch History has no session context.

**Research finding:** Looking at the `SessionSave` model (models/__init__.py lines 139–145), saves are strictly session-scoped. There is no global save table. The `saveMovie` / `unsaveMovie` API calls both require `sessionId`.

**The user's CONTEXT.md says:** "Star/save action (bookmarks the movie, same save mechanism as GameSession)" — this implies the same `SessionSave` mechanism.

**Implementation risk:** A watched movie may have been watched in any session or even outside a session (e.g., source="online" from SearchPage). Without a session_id, the save API cannot be called.

**Recommended resolution for planner to decide:** Two viable approaches:
1. **Omit save/star from Watch History splash for now.** The feature requires a session-scoped save. Users can save from within GameSession where context exists. The splash still shows all data. Note this as a known gap.
2. **Add a global `saved_movies` table** (not session-scoped) and a new endpoint. This is a larger scope addition.

The CONTEXT.md says "same save mechanism as GameSession" — this could mean the planner should implement a global save table as a prerequisite, or it could mean the intent was just visual consistency (same star icon). This is the key open question the planner must resolve.

**For research purposes:** The save feature requires either a new global save table (new migration, new endpoints, new frontend state) or descoping from Phase 16. The planner should flag this as a gate decision before designing the splash dialog.

### Anti-Patterns to Avoid

- **Querying WatchEvent.mdblist_synced_at after migration 0016:** Once the migration runs, the column is gone. Any code referencing it after 0016 will cause a runtime error. The model update and migration must ship together.
- **Sorting on watched_at or personal_rating in Python after fetching entire table:** With 150+ records this is fine, but the pattern should still use null-stable two-pass (same as eligible-movies) so it does not break when a WatchEvent has no rating set.
- **Reusing EligibleMovieDTO for watch history items:** These types carry different fields. Using EligibleMovieDTO would require filling `watched: bool`, `selectable: bool`, `saved: bool`, etc. with dummy values — misleading and fragile.
- **Treating search as a server-side filter that bypasses pagination when active:** The eligible-movies endpoint does this (bypasses pagination on search). For watch history, keep pagination active even during search — the dataset is small and paginated UX is consistent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQLite DROP COLUMN | Custom migration without batch_alter_table | Alembic batch mode | SQLite does not support raw DROP COLUMN in older versions; Alembic batch recreates the table safely |
| Null-stable sort | Custom sort with None comparisons | Two-pass pattern from game.py | Already battle-tested in the codebase; avoids Python TypeError on None < int |
| Debounced search input | setTimeout in effect manually | Existing pattern from SearchPage (copied verbatim) | Already implemented correctly with cleanup |
| Personal rating display | Custom badge component | Extend RatingsBadge with a new `personal_rating` key entry or render alongside | RatingsBadge already handles icon+value rendering pattern |
| Pagination UI | Custom prev/next buttons | SearchPage pagination block (copied verbatim) | Already implemented with correct disabled states |

---

## Runtime State Inventory

> This phase includes a DROP COLUMN migration and code removal. Runtime state check required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `watch_events.mdblist_synced_at` column — data in production NAS SQLite | DROP COLUMN via migration 0016; data is deleted, no migration of values needed (column has no business value after Phase 14 removal) |
| Stored data | `app_settings` row with key `mdblist_list_id` — persisted in DB by Settings UI | No migration needed; the key will remain as an orphaned row in app_settings but will not be readable via API after settings.py is updated. Safe to leave (ignored by all code) or clean up with a one-time SQL DELETE |
| Live service config | None — the only external service configured by the removed code (MDBList list sync) is opt-in and no longer called | None |
| OS-registered state | None | None — verified by code review |
| Secrets/env vars | `mdblist_list_id` stored as app_settings DB row — no env var, no .env file | Code removal only; DB row is orphaned but harmless |
| Build artifacts | None | None — verified by code review |

---

## Common Pitfalls

### Pitfall 1: BackgroundTasks still needed in game.py after mdblist removal
**What goes wrong:** Developer removes `_push_watch_to_mdblist` from game.py imports and accidentally also removes `BackgroundTasks` from the `mark_current_watched` function signature, breaking the `_update_session_suggestions` background task (Phase 15 feature).
**Why it happens:** Both background tasks are added in the same code block (lines 1272–1277); they look visually similar.
**How to avoid:** When deleting the mdblist block (lines 1267–1276), explicitly preserve line 1277: `background_tasks.add_task(_update_session_suggestions, session_id)`.
**Warning signs:** `_update_session_suggestions` never fires after suggestions were working in Phase 15.

### Pitfall 2: movies.py still imports BackgroundTasks after mdblist push removal
**What goes wrong:** `BackgroundTasks` stays in the import line but is unused, causing a linting warning. More critically, the `background_tasks: BackgroundTasks` param stays in `mark_movie_watched`'s signature — FastAPI will inject a BackgroundTasks instance for every request even though nothing uses it.
**Why it happens:** Partial cleanup — import is removed but function signature is not, or vice versa.
**How to avoid:** After removing the push block from `mark_movie_watched` (lines 320–330), also remove `background_tasks: BackgroundTasks` from the function parameter list and remove `BackgroundTasks` from the fastapi import line.

### Pitfall 3: WatchEvent model still has mdblist_synced_at after migration 0016
**What goes wrong:** If migration runs but the SQLAlchemy model is not updated, SQLAlchemy will attempt to access a column that no longer exists, causing AttributeError or mapping errors at startup.
**Why it happens:** Migration and model update are different files — easy to do one but forget the other.
**How to avoid:** Treat migration 0016 and model update as a single atomic task.

### Pitfall 4: /movies/watched route collision with /movies/{tmdb_id}
**What goes wrong:** FastAPI path parameters match any string segment. `GET /movies/watched` would match `/{tmdb_id}` and try to cast "watched" as an integer, returning a 422.
**Why it happens:** `GET /movies/{tmdb_id}` at line 230 is a catch-all for integer paths; but FastAPI resolves routes in declaration order and "watched" is not an integer so it will try to match the integer path param and fail.
**Current status:** This is already safe — `GET /movies/watched` at line 54 is declared BEFORE `GET /movies/{tmdb_id}` at line 230. The ordering must be preserved after the endpoint is extended.
**Warning signs:** `GET /movies/watched?sort=title` returns 422 "value is not a valid integer".

### Pitfall 5: Settings.tsx sync state variables used in Watch Sync card still in scope after card removal
**What goes wrong:** If only the JSX card block is removed but the state variables (`syncRunning`, `syncStatus`, `syncDone`, `showSyncConfirm`) and their useEffects/handlers are left behind, TypeScript will emit "declared but never used" errors and the api.mdblist calls will still fire on mount.
**Why it happens:** The sync state is spread across the top of the component (state declarations), a mount effect, a polling effect, and two handlers. Each must be removed.
**How to avoid:** Remove all four state declarations, the polling useEffect, the two handlers, AND the mount effect check for sync status — not just the JSX card.

### Pitfall 6: Page size decision — list vs tile layout alignment
**What goes wrong:** A page size of 20 (SearchPage default) leaves the tile view with an incomplete last row (20 / 3 = 6 rows + 2 tiles), which looks odd. A page size of 24 divides evenly into 3-column rows and 4-column rows (if the layout ever changes to 4).
**Why it happens:** Page size is optimized for table view (any number works) but tile view benefits from multiples of the column count.
**How to avoid:** Use page_size=24 as the default. This gives 8 complete rows in tile mode and a reasonable table page.

---

## Code Examples

Verified patterns from existing codebase:

### Null-stable two-pass sort (from game.py lines 1799–1803)
```python
# Sort by runtime, nulls last, secondary key tmdb_id for determinism
with_runtime = [m for m in movies if m.get("runtime") is not None]
without_runtime = [m for m in movies if m.get("runtime") is None]
with_runtime.sort(key=lambda m: (m["runtime"], m["tmdb_id"]), reverse=_desc)
without_runtime.sort(key=lambda m: m["tmdb_id"])
movies = with_runtime + without_runtime
```

### Alphabetical title sort (new for watched history)
```python
# Title sort — always case-insensitive, secondary key tmdb_id
_desc = sort_dir == "desc"
movies.sort(key=lambda m: (m["title"].lower(), m["tmdb_id"]), reverse=_desc)
```

### Alembic batch DROP COLUMN for SQLite
```python
# Source: Alembic documentation
def upgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.drop_column("mdblist_synced_at")

def downgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.add_column(sa.Column("mdblist_synced_at", sa.DateTime(), nullable=True))
```

### NavBar extension (from NavBar.tsx lines 36–46 — add Watch History between Search and Settings)
```tsx
// Add between Search Link and Settings Link
<Link
  to="/watched"
  className={cn(
    "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
    location.pathname === "/watched"
      ? "bg-accent text-accent-foreground"
      : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
  )}
>
  Watch History
</Link>
```

### App.tsx route addition (after SearchPage route, before Settings route)
```tsx
<Route path="/watched" element={<WatchHistoryPage />} />
```

### Personal rating badge rendering (new entry in RatingsBadge or inline)
```tsx
// Alongside RatingsBadge in splash dialog
{movie.personal_rating != null && (
  <span className="inline-flex items-center gap-0.5 text-xs" aria-label={`Personal rating: ${movie.personal_rating}/10`}>
    <Star className="w-3 h-3 fill-current text-amber-400" />
    <span>{movie.personal_rating}/10</span>
  </span>
)}
```

### Tile grid layout
```tsx
<div className="grid grid-cols-3 gap-3">
  {paginated.map((movie) => (
    <MovieCard
      key={movie.tmdb_id}
      {...movie}
      watched_at={movie.watched_at}
      personal_rating={movie.personal_rating}
      onClick={() => { setSplashMovie(movie); setSplashOpen(true) }}
    />
  ))}
</div>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `GET /movies/watched` returning 4 fields, no params | Extended endpoint with sort/search/pagination + WatchedMovieDTO | Phase 16 | Frontend can render full watch history page |
| `WatchEvent.mdblist_synced_at` column tracking MDBList push state | Column dropped via migration 0016 | Phase 16 | Schema simplified; all Phase 14 sync infrastructure removed |
| Fire-and-forget push to MDBList on every mark-watched | Removed; watch history is now first-party | Phase 16 | Simpler mark-watched flow; no external dependency |

**Deprecated/outdated after Phase 16:**
- `_push_watch_to_mdblist`: removed
- `_SyncState` / `_run_watched_sync`: removed
- `mdblist_list_id` setting key: orphaned in DB (harmless), no longer exposed via API
- `getWatchedMovies` in api.ts: replaced by `getWatchedHistory` with full params

---

## Open Questions

1. **Save/star from Watch History splash — session scope conflict**
   - What we know: `SessionSave` requires `(session_id, tmdb_id)`. Watch History has no session context. CONTEXT.md says "same save mechanism as GameSession."
   - What's unclear: Does "same save mechanism" mean the planner should introduce a global saves table, or is this a mistake in the CONTEXT.md that intended to scope saves to sessions only?
   - Recommendation: Planner should decide before designing the splash. If global save is too large for Phase 16, scope it to "personal rating only" in the splash and note save as a Phase 17+ item. If the save feature is required, it needs a migration (new `global_saves` table), a new endpoint (`POST /movies/{tmdb_id}/save`, no session_id), and frontend state.

2. **WatchEvent uniqueness constraint — one watch event per movie**
   - What we know: `WatchEvent` has `UniqueConstraint("tmdb_id")` (models/__init__.py line 74). This means a movie can only appear once in watch history regardless of how many sessions it appeared in.
   - What's unclear: This was by design (Phase 14), but it means "watched date" reflects the first time a movie was marked watched, not a cumulative list of viewings.
   - Recommendation: No action needed for Phase 16 — the constraint is documented and working. Planner should note in the PLAN that the history page shows one entry per movie, not one per viewing.

3. **`mdblist_list_id` orphaned row in app_settings**
   - What we know: The DB row persists after the settings.py model is updated; it has no business effect.
   - What's unclear: Whether to add a data-cleanup SQL to migration 0016 to remove the row.
   - Recommendation: Include a `DELETE FROM app_settings WHERE key = 'mdblist_list_id'` in migration 0016's upgrade() for cleanliness. This is a data migration, not a schema migration, but it belongs with the cleanup.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | backend/pytest.ini or inferred from pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/test_movies.py -x -q` |
| Full suite command | `cd backend && python -m pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WATCHED-01 | GET /movies/watched returns paginated WatchedMovieDTO items with sort/search params | unit/integration | `cd backend && python -m pytest tests/test_movies.py -x -q` | ✅ (extend existing file) |
| WATCHED-01 | PATCH /movies/{tmdb_id}/rating sets WatchEvent.rating | unit/integration | `cd backend && python -m pytest tests/test_movies.py -x -q` | ✅ (extend existing file) |
| WATCHED-02 | Migration 0016 drops mdblist_synced_at from watch_events | integration | `cd backend && alembic upgrade head` | ❌ Wave 0 |
| WATCHED-03 | /mdblist/watched-sync/start returns 404 (endpoint removed) | integration | `cd backend && python -m pytest tests/test_mdblist.py -x -q` | ✅ (existing file, test the absence) |
| WATCHED-03 | GET /settings no longer returns mdblist_list_id field | integration | `cd backend && python -m pytest tests/test_settings.py -x -q` | ✅ (existing file) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_movies.py tests/test_mdblist.py tests/test_settings.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test functions in `tests/test_movies.py` covering:
  - `test_get_watched_history_with_sort_title` — GET /movies/watched?sort=title returns items sorted A→Z
  - `test_get_watched_history_with_pagination` — GET /movies/watched?page=1&page_size=2 returns correct envelope
  - `test_get_watched_history_with_search` — GET /movies/watched?search=godfather returns filtered results
  - `test_get_watched_history_sort_watched_at` — GET /movies/watched?sort=watched_at returns most recent first
  - `test_set_movie_rating_success` — PATCH /movies/{tmdb_id}/rating sets WatchEvent.rating
  - `test_set_movie_rating_clears_on_null` — PATCH /movies/{tmdb_id}/rating with null clears rating
  - `test_set_movie_rating_404_no_watch_event` — PATCH /movies/99999/rating returns 404
  - `test_set_movie_rating_invalid_range` — PATCH with rating=11 returns 422

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `backend/app/routers/movies.py` — current GET /movies/watched endpoint at lines 54–71; mark_movie_watched at lines 302–332
- Direct code inspection of `backend/app/routers/game.py` — eligible-movies sort/pagination pattern at lines 1786–1858; _push_watch_to_mdblist call site at lines 1267–1276
- Direct code inspection of `backend/app/routers/mdblist.py` — _push_watch_to_mdblist (lines 22–64), _SyncState (lines 79–88), _run_watched_sync (lines 91–158), /watched-sync endpoints (lines 327–375)
- Direct code inspection of `backend/app/models/__init__.py` — WatchEvent model at lines 72–84
- Direct code inspection of `backend/app/routers/settings.py` — mdblist_list_id at lines 23 and 37
- Direct code inspection of `frontend/src/lib/api.ts` — WatchedSyncStatusDTO (lines 161–167), mdblist namespace (lines 327–345), SettingsDTO (lines 143–154)
- Direct code inspection of `frontend/src/pages/Settings.tsx` — Watch Sync card (lines 387–469), sync state (lines 54–59)
- Direct code inspection of `frontend/src/components/NavBar.tsx` — current nav link pattern
- Direct code inspection of `frontend/src/App.tsx` — route registration pattern
- Direct code inspection of `frontend/src/pages/SearchPage.tsx` — list layout, splash dialog, pagination
- Direct code inspection of `backend/alembic/versions/` — migration numbering, 0015 is current head
- Direct code inspection of `backend/tests/test_mdblist.py` — Phase 14 tests at lines 213–249
- Direct code inspection of `backend/tests/test_settings.py` — mdblist_list_id test at lines 76–79

### Secondary (MEDIUM confidence)
- Alembic documentation pattern for SQLite batch ALTER TABLE (batch_alter_table context manager for DROP COLUMN) — standard Alembic SQLite guidance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use in the project
- Architecture: HIGH — all patterns verified against existing codebase code
- Pitfalls: HIGH — all identified from direct code inspection
- Phase 14 removal inventory: HIGH — all line numbers verified by reading actual files

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable codebase; no external dependencies being added)
