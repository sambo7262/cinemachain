# Phase 14 Context — MDBList Watched List Sync

**Phase goal:** Sync all watched movies (game session + Query Mode) to a MDBList list — seeding watch history so MDBList can generate personalised recommendations.
**Requirements:** MDBSYNC-01, MDBSYNC-02

---

## Decision 1: Real-Time Sync Coupling (MDBSYNC-01)

### Trigger strategy
When a movie is marked watched — via either `POST /sessions/{id}/mark-current-watched` (game mode) or `PATCH /movies/{tmdb_id}/watched` (Query Mode) — enqueue a **fire-and-forget background task** that pushes to MDBList alongside writing the `WatchEvent` row. The response to the frontend is not blocked.

### Failure handling
All failures (network error, 429, missing config, API error) are **silently logged**. Nothing is surfaced to the UI. The `mdblist_synced_at` column on `WatchEvent` remains `NULL` on failure, so bulk sync from Settings is the natural recovery path.

### Guard: unconfigured
Before attempting the real-time push, check that **both** `mdblist_api_key` and `mdblist_list_id` are configured. If either is missing, skip silently — MDBList sync is opt-in.

### Quota counting
Every successful real-time push call increments `mdblist_calls_today`, using the same `_increment_quota` helper as the ratings backfill.

---

## Decision 2: Sync State Tracking

### New column: mdblist_synced_at on WatchEvent
Add `mdblist_synced_at: datetime | None` (nullable) to the `WatchEvent` model via a new Alembic migration.

- **NULL** = not yet synced to MDBList
- **Timestamp** = successfully pushed to MDBList at this time

### Write rules
- `mdblist_synced_at` is written **only on confirmed API success** (2xx response from MDBList).
- On any failure, it stays `NULL` so the next bulk sync retries.

### Existing WatchEvent rows
Rows created before Phase 14 is deployed have `mdblist_synced_at = NULL`. The first bulk sync from Settings will pick them all up — this is the intended catch-up mechanism.

### Bulk sync query
```sql
SELECT * FROM watch_events WHERE mdblist_synced_at IS NULL
```

---

## Decision 3: Movie Identifier Strategy

### Preferred identifier: imdb_id
- Use `imdb_id` (tt-format, e.g. `tt0111161`) when available on the `Movie` row — populated by Phase 13.
- Fall back to `tmdb_id` if `imdb_id` is `NULL`.
- Researcher must confirm which parameter name(s) MDBList list API accepts for each format.

### Missing identifier handling
If a movie cannot be identified (e.g. `imdb_id` is NULL and researcher confirms `tmdb_id` isn't accepted), **skip** the movie and **leave `mdblist_synced_at = NULL`**. Do not mark as synced. On the next bulk sync (after ratings backfill has populated `imdb_id`), it will be retried automatically.

### Researcher task
Researcher must document the exact MDBList list write endpoint:
- URL, method, auth header/param
- Accepted identifier fields (imdb_id? tmdb_id? both?)
- Payload format for adding a single item
- What the API returns on duplicate add (error or silent ignore?)
- Whether batch/multi-item add is supported

---

## Decision 4: Bulk Sync UI + Settings (MDBSYNC-02)

### New settings field: mdblist_list_id
Add `mdblist_list_id` to `SettingsResponse` and `SettingsUpdateRequest` in `settings.py`. Stored as a plain string in `app_settings`. No live validation — errors surface on first sync attempt.

### Settings page layout
Separate **"MDBList Watch Sync"** section below the existing MDBList ratings section:

```
├─ MDBList
│   API Key: [***]
│   [Refresh Ratings Data]   ← Phase 13, unchanged
│
├─ MDBList Watch Sync
│   List ID: [          ]
│   [Sync Watched History]
│
│   Confirm dialog:
│   'X movies not yet synced to MDBList'
│   Optional quota warning if X > remaining daily limit
│   [Cancel] [Sync Now]
│
└─ Progress: [=====>    ] 23/47
```

### Bulk sync UX (mirrors Phase 13 backfill pattern)
1. Button: "Sync Watched History"
2. On click: confirm dialog showing:
   - Count of WatchEvents where `mdblist_synced_at IS NULL`
   - Current quota: `X of 10,000 calls used today`
   - Warning if unsynced count > remaining quota
3. User confirms → `POST /mdblist/watched-sync/start`
4. Button disables, progress bar appears
5. Frontend polls `GET /mdblist/watched-sync/status` every 2s
6. Status response: `{ running: bool, synced: int, total: int, calls_used_today: int, daily_limit: int }`
7. On complete: "Done — X movies synced"

### Concurrency
Bulk sync has its **own `_SyncState` dataclass** in `mdblist.py` router (separate from `_BackfillState`). Both operations can run simultaneously — they don't share DB rows.

### Shared quota counter
Bulk sync calls increment the same `mdblist_calls_today` / `mdblist_calls_reset_date` settings keys used by the ratings backfill. Single quota view in the UI.

---

## Deferred Ideas (captured, not in scope for Phase 14)

- **MDBList recommendations → Suggested tab** — already captured in Phase 13 deferred; Phase 15 in roadmap.
- **Automatic nightly sync** — schedule a nightly task to sync any unsynced WatchEvents. Deferred; manual bulk sync is sufficient for single-user NAS.
- **Remove from MDBList list on unwatch** — no unwatch feature exists; deferred.

---

## Code Context

### Watch event creation — two paths
1. **Game mode:** `backend/app/routers/game.py` — `mark_current_watched()` at `@router.post("/sessions/{session_id}/mark-current-watched")`; creates a `WatchEvent` and sets `session.current_movie_watched = True`
2. **Query Mode:** `backend/app/routers/movies.py` — `mark_movie_watched()` at `@router.patch("/{tmdb_id}/watched")`; upserts via `pg_insert(WatchEvent)...on_conflict_do_nothing`

### Existing MDBList infrastructure (Phase 13)
- `backend/app/services/mdblist.py` — `MDBLIST_API_URL`, `fetch_rt_scores()`, `backfill_mdblist_scores()`; quota via `settings_service`
- `backend/app/routers/mdblist.py` — `_BackfillState`, `_increment_quota()`, `_run_backfill()`, `/backfill/start`, `/backfill/status`
- `backend/app/routers/settings.py` — `SettingsResponse` + `SettingsUpdateRequest`; add `mdblist_list_id` here
- `backend/app/services/settings_service.py` — `get_setting()`, `save_settings()`, `get_all_settings()`

### Models to update
- `WatchEvent` in `backend/app/models/__init__.py` — add `mdblist_synced_at: Mapped[datetime | None]`
- New Alembic migration for this column

### Frontend
- `frontend/src/pages/Settings.tsx` — add MDBList Watch Sync section mirroring the Phase 13 backfill UI
- `frontend/src/lib/api.ts` — add `startWatchedSync()` and `getWatchedSyncStatus()` functions
