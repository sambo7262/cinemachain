# Phase 14: MDBList Watched List Sync - Research

**Researched:** 2026-04-01
**Domain:** MDBList list write API, FastAPI background tasks, SQLAlchemy async migrations
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Decision 1: Real-Time Sync Coupling (MDBSYNC-01)**
- Trigger: fire-and-forget BackgroundTask alongside WatchEvent write; response not blocked
- Failure handling: all failures silently logged; `mdblist_synced_at` stays NULL on failure
- Guard: check both `mdblist_api_key` AND `mdblist_list_id` before attempting push; skip silently if either missing
- Quota: every successful real-time push increments `mdblist_calls_today` via `_increment_quota`

**Decision 2: Sync State Tracking**
- New column: `mdblist_synced_at: datetime | None` (nullable) on `WatchEvent`; added via new Alembic migration
- NULL = not yet synced; timestamp = successfully pushed at that time
- Written ONLY on confirmed 2xx API success
- Bulk sync query: `SELECT * FROM watch_events WHERE mdblist_synced_at IS NULL`

**Decision 3: Movie Identifier Strategy**
- Preferred: `imdb_id` (tt-format) from Movie row (populated by Phase 13)
- Fallback: `tmdb_id` if `imdb_id` is NULL
- If a movie has no usable identifier: skip silently, leave `mdblist_synced_at = NULL`

**Decision 4: Bulk Sync UI + Settings (MDBSYNC-02)**
- New settings field: `mdblist_list_id` added to `SettingsResponse` and `SettingsUpdateRequest`
- Separate "MDBList Watch Sync" Card section below existing MDBList ratings section
- Bulk sync has its own `_SyncState` dataclass (separate from `_BackfillState`)
- Bulk sync increments the same `mdblist_calls_today` / `mdblist_calls_reset_date` keys
- Endpoints: `POST /mdblist/watched-sync/start`, `GET /mdblist/watched-sync/status`
- Status response: `{ running: bool, synced: int, total: int, calls_used_today: int, daily_limit: int }`
- Frontend polls every 2s while running

### Claude's Discretion

None specified beyond Researcher's investigation of MDBList list write API specifics.

### Deferred Ideas (OUT OF SCOPE)

- MDBList recommendations → Suggested tab (Phase 15)
- Automatic nightly sync
- Remove from MDBList list on unwatch
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MDBSYNC-01 | Every movie marked as watched (game session or Query Mode) is synced to the user's MDBList watched list in real time | MDBList list items add API confirmed; BackgroundTasks pattern from Phase 13 applies directly; both watch paths identified in game.py and movies.py |
| MDBSYNC-02 | Bulk sync on demand from Settings — push full existing watch history to MDBList; MDBList list ID configurable in Settings | `_SyncState` + `/watched-sync/start` + `/watched-sync/status` mirrors `_BackfillState` pattern; Settings DTO extension documented; frontend polling pattern confirmed from Phase 13 |
</phase_requirements>

---

## Summary

Phase 14 adds MDBList list sync to the two watch paths in the app. The MDBList list write API is well-documented and straightforward: `POST /lists/{listid}/items/add?apikey=KEY` with a JSON body containing arrays of movie objects. Each movie object accepts both `imdb` and `tmdb` as identifier fields — either alone is sufficient. Duplicate adds are handled gracefully (returned in an `existing` counter, no error raised). Batch adds are supported in a single request.

The codebase from Phase 13 provides all the scaffolding this phase needs: `_BackfillState`, `_increment_quota`, `_bg_session_factory`, settings_service CRUD, and the Phase 13 backfill UI pattern in Settings.tsx. The implementation is a structural mirror of Phase 13's backfill.

Two watch event creation paths need to be hooked: `mark_current_watched()` in `game.py` (game mode) and `mark_movie_watched()` in `movies.py` (Query Mode). Both currently upsert a `WatchEvent` with `on_conflict_do_nothing` — the fire-and-forget push should be enqueued after the upsert, before or after `db.commit()`. The `WatchEvent` model needs one new nullable column `mdblist_synced_at`.

**Primary recommendation:** Use `POST /lists/{listid}/items/add` (not the `/sync/watched` endpoint) — the list items API is simpler, requires only one identifier field, and matches the user's intent of maintaining a specific named MDBList list. Send `imdb` when available, fall back to `tmdb`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | already in requirements | HTTP client for MDBList API calls | Already used for Phase 13 backfill |
| FastAPI BackgroundTasks | already in use | Fire-and-forget real-time push | Identical pattern to how Phase 13 was NOT done — but CONTEXT specifies this approach |
| SQLAlchemy async | already in use | WatchEvent query + mdblist_synced_at update | Existing ORM pattern |
| Alembic | already in use | Migration for `mdblist_synced_at` column | Existing migration chain |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.sleep | stdlib | Rate-limit pacing in bulk sync loop | ~1 req/s as per Phase 13 pattern |

**Installation:** No new dependencies required.

---

## MDBList List Write API (Verified)

**Source:** https://raw.githubusercontent.com/linaspurinis/api.mdblist.com/master/apiary.apib (official API Blueprint spec)

### Endpoint: Add items to a list

```
POST /lists/{listid}/items/add?apikey={YOUR_API_KEY}
```

**Request body:**
```json
{
  "movies": [
    {"imdb": "tt0111161"},
    {"tmdb": 238},
    {"tmdb": 630, "imdb": "tt0032138"}
  ]
}
```

**Key facts (HIGH confidence — verified from official spec):**

- `listid` = the numeric or slug ID of the user's MDBList list (stored as `mdblist_list_id` setting)
- Auth: `?apikey=KEY` query parameter (same pattern as existing ratings calls)
- Identifier fields: `imdb` (tt-format string) and/or `tmdb` (integer) — either alone is sufficient
- Batch: YES — multiple movies per request in the `movies` array
- Duplicate handling: SILENT — duplicates appear in `existing` counter, no error raised; 2xx always returned when request is valid
- Response:
  ```json
  {
    "added": {"movies": 1, "shows": 0},
    "existing": {"movies": 0, "shows": 0},
    "not_found": {"movies": 0, "shows": 0}
  }
  ```

### Identifier strategy (confirmed)

- `imdb` field: accepts tt-format string — directly matches `Movie.imdb_id` column (populated by Phase 13)
- `tmdb` field: accepts integer — matches `WatchEvent.tmdb_id` and `Movie.tmdb_id`
- Both can coexist in one payload object for disambiguation, but either alone is sufficient

### Real-time push payload (single movie)

```python
# With imdb_id available (preferred)
payload = {"movies": [{"imdb": movie.imdb_id}]}

# Fallback to tmdb_id
payload = {"movies": [{"tmdb": watch_event.tmdb_id}]}
```

### Alternative: `/sync/watched` endpoint

The API also has `POST /sync/watched` which accepts a `watched_at` timestamp. This endpoint syncs to MDBList's internal watch history (Trakt-compatible). The `/lists/{id}/items/add` endpoint was chosen per the user's intent (seeding a specific named list for recommendations). The sync/watched endpoint would also work if the user's list is auto-populated from watch history, but that is outside scope.

---

## Architecture Patterns

### Recommended Project Structure Impact

```
backend/app/
├── routers/
│   └── mdblist.py       # Add _SyncState, _run_watched_sync(), /watched-sync/start, /watched-sync/status
├── services/
│   └── mdblist_sync.py  # OR inline in mdblist.py — push_to_mdblist_list() helper
├── models/
│   └── __init__.py      # Add mdblist_synced_at to WatchEvent
└── alembic/versions/
    └── 0013_...py        # New migration: mdblist_synced_at on watch_events

frontend/src/
├── pages/
│   └── Settings.tsx     # Add MDBList Watch Sync section (new Card)
└── lib/
    └── api.ts           # Add startWatchedSync(), getWatchedSyncStatus()
```

### Pattern 1: Fire-and-Forget Real-Time Push (BackgroundTasks)

FastAPI `BackgroundTasks` is injected into the endpoint function and `.add_task()` is called after the DB write. The response is returned immediately. The background function opens its own DB session using `_bg_session_factory`.

```python
# Source: Phase 13 pattern in mdblist.py + FastAPI docs
@router.post("/sessions/{session_id}/mark-current-watched")
async def mark_current_watched(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # ... existing WatchEvent upsert ...
    await db.commit()
    # Enqueue fire-and-forget push AFTER commit so WatchEvent row exists
    background_tasks.add_task(_push_watch_event_to_mdblist, tmdb_id, imdb_id)
    return _build_session_response(...)
```

**IMPORTANT:** The background task runs in the same event loop. Use `_bg_session_factory` for its own DB session — do not reuse the request's `db` session after the response is returned.

### Pattern 2: _SyncState Dataclass (mirrors _BackfillState)

```python
# Source: Phase 13 _BackfillState pattern in mdblist.py
@dataclass
class _SyncState:
    running: bool = False
    synced: int = 0
    total: int = 0
    calls_used_today: int = 0
    daily_limit: int = 10_000

_sync_state = _SyncState()
```

The bulk sync loop mirrors `_run_backfill()`: open `_bg_session_factory`, query `WatchEvent WHERE mdblist_synced_at IS NULL`, iterate with `asyncio.sleep(1.0)` pacing, update `mdblist_synced_at` on success, call `_increment_quota`, commit per item or per batch.

### Pattern 3: Batch vs. Per-Item for Bulk Sync

The MDBList list items API supports batch adds. However, the bulk sync loop should write `mdblist_synced_at` per item (or small batches) to ensure partial progress is preserved if the server restarts mid-sync. Recommended: process one item at a time in the loop (matches Phase 13 backfill pattern), commit after each success.

### Pattern 4: Settings Extension

`mdblist_list_id` is a non-secret setting (does not contain "key", "token", or "password"). It will NOT be encrypted at rest by `settings_service._is_secret_key()`. This is correct — list IDs are not sensitive.

```python
# settings.py additions
class SettingsResponse(BaseModel):
    # ... existing fields ...
    mdblist_list_id: str | None = None

class SettingsUpdateRequest(BaseModel):
    # ... existing fields ...
    mdblist_list_id: str | None = None
```

### Anti-Patterns to Avoid

- **Reusing the request's `db` session in a background task:** After the response is returned, the request's `db` session is closed. Always open a new session with `_bg_session_factory` in background tasks.
- **Marking `mdblist_synced_at` before API call:** Only write the timestamp on confirmed 2xx response. Write-before-call means failures are silently lost and never retried by bulk sync.
- **Blocking the watched endpoint on MDBList API:** The user decision is fire-and-forget. Never `await` the MDBList HTTP call inside the request handler.
- **Using `/sync/watched` instead of `/lists/{id}/items/add`:** The sync/watched endpoint updates MDBList's internal history tracker — not a named list. The decisions specify a configurable list ID.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quota counting | Custom counter logic | `_increment_quota()` in mdblist.py | Already handles reset-date logic, persist to settings |
| HTTP client | requests/urllib | httpx.AsyncClient | Already used; async-compatible |
| DB session in background | threading.local | `_bg_session_factory()` as async context manager | Already the project pattern; closes cleanly |
| Settings storage | New DB table | `settings_service.save_settings()` / `get_setting()` | Existing key-value store handles encryption, upsert |
| Progress polling | WebSocket | Simple GET status endpoint + 2s interval | Phase 13 proven this pattern; no added complexity needed |

---

## Common Pitfalls

### Pitfall 1: WatchEvent upsert uses on_conflict_do_nothing — background task timing

**What goes wrong:** Both `mark_current_watched` and `mark_movie_watched` use `pg_insert(...).on_conflict_do_nothing()`. If the conflict fires (movie already watched), the result returns 0 rows inserted. The background task is still enqueued and will attempt to push — which is fine (idempotent on MDBList side due to `existing` response), but the `WatchEvent` row may not have been updated, so querying it right after may return the old row (without a fresh `tmdb_id` if it was a conflict).

**How to avoid:** Pass `tmdb_id` (and `imdb_id` if available, resolved before the upsert) directly to the background task function as parameters. Do not re-query `WatchEvent` inside the background task to find the tmdb_id — pass it as an argument.

### Pitfall 2: imdb_id is empty string sentinel, not NULL

**What goes wrong:** Phase 13 sets `movie.imdb_id = ""` (empty string) when MDBList returns 404 for a movie. The identifier strategy says "fall back to tmdb_id if imdb_id is NULL" — but empty string is falsy in Python, so the check `if movie.imdb_id` correctly catches both `None` and `""`.

**How to avoid:** Use `if movie.imdb_id` (truthy check), not `if movie.imdb_id is not None`. This correctly handles the empty-string sentinel.

### Pitfall 3: mdblist_list_id not validated — silent wrong-list writes

**What goes wrong:** The user enters a bad list ID. The MDBList API returns a non-2xx (likely 404 or 401). This silently logs and leaves `mdblist_synced_at = NULL` — but the user doesn't know why sync isn't working.

**How to avoid:** Log the HTTP status code and response body on non-2xx in the bulk sync loop (not just "error"). This gives the user enough information in container logs to diagnose misconfiguration. UI shows "Done — 0 movies synced" which signals the problem.

### Pitfall 4: BackgroundTasks vs asyncio.create_task

**What goes wrong:** Using `asyncio.create_task()` instead of `background_tasks.add_task()` for the real-time push. `create_task` is lower-level; FastAPI's BackgroundTasks are run after the response is sent and are properly lifecycle-managed.

**How to avoid:** Always use `BackgroundTasks` for fire-and-forget in FastAPI endpoints. The endpoint signature must include `background_tasks: BackgroundTasks` as a parameter.

### Pitfall 5: Bulk sync and real-time push writing mdblist_synced_at concurrently

**What goes wrong:** A bulk sync is running while the user watches a movie (real-time push). Both try to update `mdblist_synced_at` on the same `WatchEvent` row.

**How to avoid:** The decisions say both operations can run simultaneously. Real-time push updates a single row immediately. Bulk sync's query is `WHERE mdblist_synced_at IS NULL` — if real-time push already wrote the timestamp, bulk sync skips that row (correct). If bulk sync processes the row first, real-time push still attempts the add (MDBList returns `existing: 1`, still 2xx) and writes timestamp again (idempotent). No lock needed.

---

## Code Examples

### Real-time push helper function

```python
# Source: pattern derived from _run_backfill() in mdblist.py and official MDBList API spec
async def _push_watch_to_mdblist(tmdb_id: int, imdb_id: str | None) -> None:
    """Fire-and-forget: push a single watched movie to the user's MDBList list."""
    try:
        async with _bg_session_factory() as db:
            api_key = await settings_service.get_setting(db, "mdblist_api_key")
            list_id = await settings_service.get_setting(db, "mdblist_list_id")
            if not api_key or not list_id:
                return  # opt-in feature — silently skip if not configured

            # Build identifier payload
            movie_item: dict = {}
            if imdb_id:  # truthy — handles None and "" sentinel
                movie_item["imdb"] = imdb_id
            else:
                movie_item["tmdb"] = tmdb_id

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://mdblist.com/api/lists/{list_id}/items/add",
                    params={"apikey": api_key},
                    json={"movies": [movie_item]},
                )
                if resp.status_code == 200:
                    # Update mdblist_synced_at on WatchEvent
                    result = await db.execute(
                        select(WatchEvent).where(WatchEvent.tmdb_id == tmdb_id)
                    )
                    we = result.scalar_one_or_none()
                    if we:
                        we.mdblist_synced_at = datetime.utcnow()
                        count = await _increment_quota(db)
                        await db.commit()
                else:
                    logger.warning(
                        "MDBList watched push failed: status=%d tmdb_id=%d",
                        resp.status_code, tmdb_id,
                    )
    except Exception:
        logger.exception("MDBList watched push error for tmdb_id=%d", tmdb_id)
```

### Alembic migration for mdblist_synced_at

```python
# Source: pattern from 20260401_0012_mdblist_fetched_at.py
revision = "0013"
down_revision = "0012"

def upgrade():
    op.add_column(
        "watch_events",
        sa.Column("mdblist_synced_at", sa.DateTime(), nullable=True)
    )

def downgrade():
    op.drop_column("watch_events", "mdblist_synced_at")
```

### WatchEvent model addition

```python
# Source: models/__init__.py existing pattern
class WatchEvent(Base):
    # ... existing columns ...
    mdblist_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

### Enqueue in mark_current_watched (game.py)

```python
# Source: FastAPI BackgroundTasks docs + existing game.py pattern
@router.post("/sessions/{session_id}/mark-current-watched", response_model=GameSessionResponse)
async def mark_current_watched(
    session_id: int,
    background_tasks: BackgroundTasks,   # ADD THIS
    db: AsyncSession = Depends(get_db),
):
    # ... existing logic ...
    await db.commit()
    # Resolve imdb_id for the current movie before enqueuing
    movie_result = await db.execute(
        select(Movie.imdb_id).where(Movie.tmdb_id == session.current_movie_tmdb_id)
    )
    imdb_id = movie_result.scalar_one_or_none()
    background_tasks.add_task(
        _push_watch_to_mdblist,
        session.current_movie_tmdb_id,
        imdb_id,
    )
    # ... rest of existing logic ...
```

### Frontend api.ts additions

```typescript
// Source: existing api.mdblist pattern in api.ts
export interface WatchedSyncStatusDTO {
  running: boolean
  synced: number
  total: number
  calls_used_today: number
  daily_limit: number
}

// Inside api.mdblist namespace:
startWatchedSync: () =>
  apiFetch<{ started: boolean; total: number }>("/mdblist/watched-sync/start", { method: "POST" }),
getWatchedSyncStatus: () =>
  apiFetch<WatchedSyncStatusDTO>("/mdblist/watched-sync/status"),
```

---

## Validation Architecture

Config does not have `workflow.nyquist_validation = false` — section included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` or pyproject.toml |
| Quick run command | `pytest backend/tests/test_mdblist.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MDBSYNC-01 | Real-time push enqueued on mark_current_watched | unit | `pytest backend/tests/test_mdblist.py::test_realtime_push_enqueued_on_mark_watched -x` | ❌ Wave 0 |
| MDBSYNC-01 | Real-time push enqueued on mark_movie_watched | unit | `pytest backend/tests/test_mdblist.py::test_realtime_push_enqueued_on_query_mode_watched -x` | ❌ Wave 0 |
| MDBSYNC-01 | Push skipped silently when api_key or list_id missing | unit | `pytest backend/tests/test_mdblist.py::test_realtime_push_skipped_when_unconfigured -x` | ❌ Wave 0 |
| MDBSYNC-01 | mdblist_synced_at written only on 2xx | unit | `pytest backend/tests/test_mdblist.py::test_synced_at_written_on_success_only -x` | ❌ Wave 0 |
| MDBSYNC-02 | Bulk sync queries WHERE mdblist_synced_at IS NULL | unit | `pytest backend/tests/test_mdblist.py::test_bulk_sync_queries_unsynced -x` | ❌ Wave 0 |
| MDBSYNC-02 | Bulk sync status endpoint reflects running state | unit | `pytest backend/tests/test_mdblist.py::test_watched_sync_status_endpoint -x` | ❌ Wave 0 |
| MDBSYNC-02 | Settings accepts mdblist_list_id | unit | `pytest backend/tests/test_settings.py::test_settings_accepts_mdblist_list_id -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_mdblist.py -x`
- **Per wave merge:** `pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_mdblist.py` — append MDBSYNC-01 and MDBSYNC-02 test stubs (file exists, append required)
- [ ] `backend/tests/test_settings.py` — append `test_settings_accepts_mdblist_list_id` stub (file exists, append required)

*(No new test files required — existing test_mdblist.py and test_settings.py are extended)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 13 backfill: no list write | Phase 14: list items add endpoint | Phase 14 | New endpoint path, same auth pattern |
| WatchEvent: no sync tracking | WatchEvent: mdblist_synced_at | Phase 14 migration | Enables retry-on-failure via NULL |

**Deprecated/outdated:**

- N/A — this is new functionality built on existing Phase 13 patterns.

---

## Open Questions

1. **Does MDBList list items API require the list to be of type "static"?**
   - What we know: The API Blueprint describes `/lists/{listid}/items/{action}` for "static list item management"
   - What's unclear: Whether a user-created watched list or any list type works
   - Recommendation: Document in Settings UI that the list must be a "static list" on MDBList; user creates it manually at mdblist.com. Log a clear warning if 404/403 returned.

2. **What does MDBList return if the list_id is invalid?**
   - What we know: Standard REST APIs return 404 for unknown resource
   - What's unclear: Exact status code and body from MDBList
   - Recommendation: Treat any non-2xx as failure, log status + body. The `existing` response counter confirms duplicate handling.

3. **Rate limits on list items add endpoint**
   - What we know: MDBList free tier is 10,000 calls/day total; same quota counter governs all calls
   - What's unclear: Whether list write calls count against the same 10k/day quota as the ratings API
   - Recommendation: Assume yes (shared quota). The `_increment_quota` helper is called after each successful list write, consistent with ratings backfill.

---

## Sources

### Primary (HIGH confidence)
- `https://raw.githubusercontent.com/linaspurinis/api.mdblist.com/master/apiary.apib` — MDBList API Blueprint spec; list write endpoint, payload format, identifier fields, duplicate handling, batch support all verified
- Existing codebase: `backend/app/routers/mdblist.py`, `backend/app/services/mdblist.py`, `backend/app/models/__init__.py`, `backend/app/routers/settings.py`, `backend/app/services/settings_service.py` — all read directly

### Secondary (MEDIUM confidence)
- `https://github.com/linaspurinis/api.mdblist.com` — GitHub repo metadata confirming apiary.apib is the canonical spec

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- MDBList API endpoint: HIGH — verified from official API Blueprint spec (apiary.apib)
- Identifier fields (imdb/tmdb): HIGH — explicit in spec payload examples
- Duplicate handling (existing counter, no error): HIGH — spec response schema documents `existing` field
- Batch support: HIGH — spec shows arrays in payload
- Architecture patterns: HIGH — derived directly from Phase 13 code already in repo
- Standard stack: HIGH — no new dependencies; all existing

**Research date:** 2026-04-01
**Valid until:** 2026-07-01 (MDBList API is stable; free-tier quota may change)
