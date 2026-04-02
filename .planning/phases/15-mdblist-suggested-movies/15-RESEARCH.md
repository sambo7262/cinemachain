# Phase 15: TMDB Suggested Movies — Research

**Researched:** 2026-04-01
**Domain:** TMDB recommendations API, FastAPI BackgroundTasks, SQLAlchemy JSON column, React filter state
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Recommendations engine:** TMDB `/movie/{id}/recommendations` — already authenticated via stored TMDB API key. Returns ~20 suggested movies per seed.

**Seed pool:** Last N watched movies from `watch_events` ordered by watched time descending. N is user-configurable in Settings (default: 5). Sliding window — oldest drops off when newest enters.

**Ranking:** Frequency across seeds — a movie recommended by 3 of 5 seeds ranks above one by 1. Ties left in stable order.

**Per-movie cache:** New `tmdb_recommendations` JSON column on `Movie` row (list of TMDB IDs). If already populated, no API call is made. First session: up to N calls to warm cache; each movie thereafter: 1 call.

**Fetch trigger:** Fire-and-forget `BackgroundTask` on `mark_current_watched` — same pattern as Phase 14 `_push_watch_to_mdblist`. Does not block the response.

**UI placement:** Filter toggle alongside Saved (★) and Shortlist (✓) in eligible movies panel. NOT a new tab.

**Intersection:** Cross-reference TMDB suggestion IDs against existing `get_eligible_movies` pool. Chain-history enforced automatically by the existing eligibility query. No separate intersection query needed.

**Hidden when empty:** If no TMDB suggestions intersect the eligible pool, the Suggested toggle is not rendered.

**New settings field:** `tmdb_suggestions_seed_count` (int, default 5) stored in `app_settings`.

### Claude's Discretion

- Whether suggestions endpoint is a dedicated `GET /sessions/{id}/suggestions` or a flag on the existing eligible movies endpoint.

### Deferred Ideas (OUT OF SCOPE)

- Phase 14 MDBList sync removal (deferred to Phase 16 Watched History).
- Watched History view (Phase 16).
- Actor-scoped suggestions (which actor makes each suggestion reachable).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUGGEST-01 | A Suggested filter toggle appears in the eligible movies panel when TMDB recommendations intersect with eligible actors at the current step | Backend: `_update_session_suggestions` BG task + new `GET /sessions/{id}/suggestions` endpoint; Frontend: conditional toggle render |
| SUGGEST-02 | Suggested movies support the same actions as regular eligible movies (request, save, shortlist) | No new DTO changes needed — `EligibleMovieDTO` is reused; suggestions filter is client-side like Saved/Shortlist |
| SUGGEST-03 | Filter toggle is hidden when no intersecting suggestions exist — no empty state shown | Frontend: `suggestions.length === 0` conditional; BG task must complete before eligible movies panel opens |
</phase_requirements>

---

## Summary

Phase 15 adds a Suggested filter to the eligible movies panel by calling TMDB's `/movie/{id}/recommendations` endpoint for recently watched movies, aggregating by frequency, and surfacing the intersection with the current eligible pool.

The implementation has four discrete concerns: (1) a new `tmdb_recommendations` JSON column on `Movie` with an Alembic migration, (2) a new service function in `tmdb.py` that fetches and caches recommendations, (3) a background task wired into `mark_current_watched` using the existing `_bg_session_factory` pattern, and (4) a new backend endpoint `GET /sessions/{id}/suggestions` returning a flat list of TMDB IDs plus a new `getSessionSuggestions` call in `api.ts` with client-side filter state in `GameSession.tsx`.

The TMDB recommendations endpoint is straightforward: `api_key` via query param (already how the existing `TMDBClient` works), returns `results[]` with `id` and basic movie metadata. Rate limit is ~40 req/s with no daily quota — the per-movie cache means at most 1 TMDB call per `mark_current_watched` event in steady state, well within limits.

**Primary recommendation:** Implement as a dedicated `GET /sessions/{id}/suggestions` endpoint that returns `{ suggestion_tmdb_ids: list[int] }`. The frontend calls it immediately when the eligible movies panel is shown, cross-references against `filteredMovies`, and toggles the button visible/hidden. This keeps the eligible movies endpoint unchanged and avoids over-fetching suggestions on every sort/filter/page change.

---

## Standard Stack

### Core (no new libraries required)

| Component | Existing | Purpose in Phase 15 |
|-----------|----------|---------------------|
| `httpx.AsyncClient` | `tmdb.py` TMDBClient | New `fetch_recommendations(tmdb_id)` method — same HTTP pattern |
| `sqlalchemy.ext.asyncio.AsyncSession` | throughout | DB reads/writes in BG task |
| `_bg_session_factory` | `app/db.py` | Creates DB session inside background task (no request context) |
| `fastapi.BackgroundTasks` | `game.py` | Registers `_update_session_suggestions` task |
| `app.services.settings_service.get_setting` | `mdblist.py` | Reads `tmdb_suggestions_seed_count` and `tmdb_api_key` from `app_settings` |
| `sa.JSON` (SQLAlchemy) | new | Column type for `Movie.tmdb_recommendations` |

### Supporting

| Component | Where | When to Use |
|-----------|-------|-------------|
| `React.useState` / `useQuery` | `GameSession.tsx` | `showSuggestedOnly` state + `getSessionSuggestions` query |
| `Counter` / `collections` pattern | `suggestions.py` | Frequency count across seeds — use `dict.get(id, 0) + 1` or `Counter` |

**Installation:** No new packages required.

---

## Architecture Patterns

### New Service: `backend/app/services/suggestions.py`

Keep TMDB recommendations logic out of `game.py` (already large at 2000+ lines). Place in a standalone service module, analogous to `mdblist.py` service.

```
backend/app/services/
├── tmdb.py              # Add fetch_recommendations() method to TMDBClient
├── mdblist.py           # Existing
└── suggestions.py       # NEW: fetch_and_cache, get_session_suggestions
```

### Pattern 1: Adding a Method to TMDBClient

The existing `TMDBClient` in `tmdb.py` owns all TMDB HTTP calls. Add `fetch_recommendations` as a new method with the same semaphore + `raise_for_status` pattern.

```python
# Source: tmdb.py existing pattern
async def fetch_recommendations(self, tmdb_id: int, page: int = 1) -> dict:
    """Fetch TMDB recommendations for a movie. Returns raw response with results[]."""
    async with self._sem:
        r = await self._client.get(f"/movie/{tmdb_id}/recommendations", params={"page": page})
        r.raise_for_status()
        return r.json()
```

The `api_key` is already injected as a default param in `self._client` constructor — no auth changes needed.

### Pattern 2: Background Task with `_bg_session_factory`

This is the **exact established pattern** from `_push_watch_to_mdblist` in `mdblist.py` and `_prefetch_credits_background` in `game.py`.

```python
# Source: backend/app/routers/mdblist.py _push_watch_to_mdblist
async def _update_session_suggestions(session_id: int) -> None:
    try:
        async with _bg_session_factory() as db:
            # all DB access here — no request context available
            ...
    except Exception:
        logger.exception("_update_session_suggestions: unexpected error session_id=%d", session_id)
```

**Critical:** The `TMDBClient` instance lives on `request.app.state.tmdb_client` — not accessible in a background task. The background task must instantiate its own `TMDBClient` using the API key read from `app_settings` via `settings_service.get_setting(db, "tmdb_api_key")`. See how `_run_backfill` in `mdblist.py` reads API key from DB rather than relying on request state.

### Pattern 3: Wiring into `mark_current_watched`

```python
# Source: backend/app/routers/game.py lines 1225–1288
@router.post("/sessions/{session_id}/mark-current-watched", ...)
async def mark_current_watched(session_id: int, background_tasks: BackgroundTasks, db: ...):
    ...
    background_tasks.add_task(_push_watch_to_mdblist, ...)   # existing Phase 14 task
    background_tasks.add_task(_update_session_suggestions, session_id)  # NEW Phase 15 task
    ...
```

No additional parameters needed beyond `session_id` — the BG task reads seed count from `app_settings` internally.

### Pattern 4: `fetch_and_cache_recommendations` Logic

```python
# Source: CONTEXT.md design + tmdb.py patterns
async def fetch_and_cache_recommendations(
    tmdb_id: int, db: AsyncSession, tmdb: TMDBClient
) -> list[int]:
    # 1. Load Movie row — check if tmdb_recommendations is already populated
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        return []
    if movie.tmdb_recommendations is not None:  # cache hit
        return movie.tmdb_recommendations

    # 2. Fetch from TMDB (page 1 only — ~20 results, sufficient)
    data = await tmdb.fetch_recommendations(tmdb_id)
    rec_ids = [r["id"] for r in data.get("results", [])]

    # 3. Cache on Movie row
    movie.tmdb_recommendations = rec_ids
    await db.commit()
    return rec_ids
```

### Pattern 5: `get_session_suggestions` Aggregation

```python
async def get_session_suggestions(
    session_id: int, db: AsyncSession, tmdb: TMDBClient, n: int = 5
) -> list[int]:
    # 1. Global sliding window: last N watch_events by watched_at desc
    result = await db.execute(
        select(WatchEvent.tmdb_id)
        .order_by(WatchEvent.watched_at.desc())
        .limit(n)
    )
    seed_tmdb_ids = [row[0] for row in result.all()]

    # 2. Accumulate frequency counts
    freq: dict[int, int] = {}
    for seed_id in seed_tmdb_ids:
        recs = await fetch_and_cache_recommendations(seed_id, db, tmdb)
        for rec_id in recs:
            freq[rec_id] = freq.get(rec_id, 0) + 1

    # 3. Sort by frequency desc, return tmdb_id list
    return sorted(freq.keys(), key=lambda k: freq[k], reverse=True)
```

Note: `WatchEvent` uses a global sliding window (not scoped to `session_id`) — this matches the CONTEXT.md intent that the recommendation pool reflects the user's global watch history.

### Pattern 6: Dedicated `GET /sessions/{id}/suggestions` Endpoint

Recommendation: new dedicated endpoint rather than a flag on the eligible movies endpoint. Rationale:
- Eligible movies endpoint is called on every sort/filter/page change — appending suggestions computation to it would re-run it on every interaction
- Suggestions are session-level, not page-level — they don't change as the user scrolls
- The frontend needs to know suggestions once per actor step, then filters locally

```python
@router.get("/sessions/{session_id}/suggestions")
async def get_session_suggestions_endpoint(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return TMDB-recommended movie IDs cross-referenced against the eligible pool."""
    # 1. Validate session exists and current_movie_watched=True
    # 2. Build eligible pool (tmdb_ids only) via existing eligibility query
    # 3. Call get_session_suggestions() from suggestions.py
    # 4. Intersect: return only suggestion_ids that appear in eligible pool
    return {"suggestion_tmdb_ids": intersected_ids}
```

Response DTO: `{ suggestion_tmdb_ids: number[] }` — minimal, just IDs. The full `EligibleMovieDTO` data is already loaded by the eligible movies query; the frontend just needs to know which IDs to flag.

### Pattern 7: Frontend Filter Toggle

The existing `showSavedOnly` / `showShortlistOnly` boolean state in `GameSession.tsx` is the exact model to follow.

```typescript
// Source: frontend/src/pages/GameSession.tsx lines 49-50, 182-183, 916-931
const [showSuggestedOnly, setShowSuggestedOnly] = useState(false)

// Client-side filter (same location as saved/shortlist filters, lines 182-183):
.filter((m) => !showSuggestedOnly || suggestionIds.has(m.tmdb_id))

// Toggle button (same location as lines 916-931, hidden when suggestionIds.size === 0):
{suggestionIds.size > 0 && (
  <Button
    variant={showSuggestedOnly ? "default" : "outline"}
    size="sm"
    onClick={() => setShowSuggestedOnly((v) => !v)}
  >
    Suggested
  </Button>
)}
```

The `suggestionIds` Set comes from a `useQuery` call to `GET /sessions/{id}/suggestions`. It should be fetched once when `isWatched` becomes true (same condition that enables the eligible movies query).

### Anti-Patterns to Avoid

- **Don't instantiate `TMDBClient` using `request.app.state`** inside the BG task — it doesn't exist. Read `tmdb_api_key` from DB via `settings_service` and construct a fresh client.
- **Don't run frequency aggregation inside the eligible movies endpoint** — it runs on every page/sort change and would cause N TMDB calls per interaction.
- **Don't add `tmdb_recommendations` to the main `Movie` ORM relationship loads** without `lazy="raise"` consideration — the column is JSON and gets loaded only when explicitly queried.
- **Don't paginate the TMDB recommendations fetch** — page 1 returns ~20 results, which is sufficient for suggestion ranking. Fetching page 2+ adds complexity with marginal value.
- **Don't reset `showSuggestedOnly` to `false` on actor step change** without also clearing `suggestionIds` — stale suggestions from the previous step would filter the new step's eligible movies.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frequency counter | Custom sort algorithm | `dict.get(k, 0) + 1` pattern or `collections.Counter` | One line; Counter handles all edge cases |
| Background DB session | Manual `AsyncSession` setup | `async with _bg_session_factory() as db:` | Already the project pattern; handles commit/rollback/close |
| TMDBClient HTTP auth | Custom header injection | Existing `TMDBClient` — `api_key` is baked into `self._client.params` | Already set up in constructor |
| JSON column encoding | `json.dumps` + Text column | `sa.JSON` column type | SQLAlchemy handles serialization; works with both SQLite (TEXT stored) and Postgres (JSONB) |

---

## Common Pitfalls

### Pitfall 1: TMDBClient Not Available in Background Task

**What goes wrong:** `request.app.state.tmdb_client` is a request-scoped object — it doesn't exist in a background task (no `request` object). The background task will fail with `AttributeError`.

**Why it happens:** FastAPI's `request.app.state` is only accessible within request handlers, not bare coroutines scheduled via `BackgroundTasks`.

**How to avoid:** In the background task, read `tmdb_api_key` from `app_settings` via `settings_service.get_setting(db, "tmdb_api_key")` and instantiate a fresh `TMDBClient`. Close it after use with `await tmdb.close()`.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'tmdb_client'` in background task logs.

### Pitfall 2: WatchEvent Unique Constraint Means At Most One Entry Per Movie

**What goes wrong:** `WatchEvent` has `UniqueConstraint("tmdb_id")` — there can only be one watch event per movie globally. The "last N watched" query `ORDER BY watched_at DESC LIMIT N` thus returns at most N distinct movies — and if the user has watched fewer than N movies, the window is smaller.

**Why it happens:** The `WatchEvent` model was designed for a single-watch-per-movie history. Re-watches do not add new rows.

**How to avoid:** The seed query should just be `SELECT tmdb_id FROM watch_events ORDER BY watched_at DESC LIMIT N` — this is correct. No join needed. Document that N seeds = N distinct movies maximum.

**Warning signs:** If testing with a fresh DB that has fewer than N watch events, `seed_tmdb_ids` will be shorter than `n` — this is expected behaviour, not a bug.

### Pitfall 3: `tmdb_recommendations` NULL vs Empty List

**What goes wrong:** `NULL` in the DB means "never fetched." An empty list `[]` should mean "fetched, but TMDB returned no recommendations." If both map to `None` in Python (because SQLAlchemy returns `None` for both `NULL` and missing data), the cache check `if movie.tmdb_recommendations is not None` will re-fetch empty results every time.

**Why it happens:** JSON column with a Python default of `None`. An empty list serialises to `[]` in JSON, which is not `NULL` in Postgres/SQLite — but careless upsert code could write `None` for an empty list.

**How to avoid:** After fetching, always write the list even if empty: `movie.tmdb_recommendations = rec_ids` where `rec_ids` is `[]` for no results. The cache check `if movie.tmdb_recommendations is not None` then correctly short-circuits.

### Pitfall 4: Stale Suggestion IDs After Actor Step Advance

**What goes wrong:** When the user picks an actor and moves to the next movie step, the suggestions query (keyed on `session_id`) returns the same cached data from the previous step if the query key hasn't changed.

**Why it happens:** React Query caches by `queryKey`. If the query key is just `["suggestions", sid]`, it won't refetch after the actor pick.

**How to avoid:** Include the current movie's `tmdb_id` (or `step_order`) in the query key: `["suggestions", sid, session?.current_movie_tmdb_id]`. This forces a refetch when the active movie changes.

### Pitfall 5: Settings Stored as Strings — Integer Conversion Required

**What goes wrong:** `AppSettings.value` is a `Text` column — all settings are stored as strings. Reading `tmdb_suggestions_seed_count` from the DB returns `"5"` not `5`. Passing a string as `LIMIT` to SQLAlchemy or as a range argument will raise a `TypeError`.

**Why it happens:** The `app_settings` key-value store is schemaless by design — all values are text.

**How to avoid:** Always cast: `n = int(await settings_service.get_setting(db, "tmdb_suggestions_seed_count") or "5")`.

---

## TMDB Recommendations Endpoint — Verified Details

**Endpoint:** `GET https://api.themoviedb.org/3/movie/{movie_id}/recommendations`

**Authentication:** `api_key` query parameter (already the pattern in `TMDBClient` — injected as a default param in `httpx.AsyncClient` constructor).

**Query parameters:**
- `page` (int, default 1) — pagination

**Response structure:**
```json
{
  "page": 1,
  "results": [
    {
      "id": 12345,
      "title": "...",
      "poster_path": "...",
      "vote_average": 7.2,
      "vote_count": 1500,
      "genre_ids": [28, 12],
      "release_date": "2023-01-15",
      "overview": "..."
    }
  ],
  "total_pages": 2,
  "total_results": 40
}
```

**Key field:** `results[].id` is the TMDB movie ID. This is what gets stored in `Movie.tmdb_recommendations`.

**Page 1 typical count:** ~20 results per page. `total_results` is typically 20–40. For Phase 15, page 1 only is sufficient — no need to paginate.

**Rate limits:** ~40 req/s soft limit, no daily quota. HTTP 429 means back off. With per-movie caching (1 call per newly watched movie), Phase 15 will produce at most 1 TMDB call per `mark_current_watched` event in steady state. Confidence: HIGH (verified via official TMDB docs).

---

## Alembic Migration Pattern

**Next revision ID:** `0015` (follows `0014` which added `watch_events.rating`).

**Pattern** (from `20260401_0011_mdblist_expansion.py` and `20260401_0014_watch_event_rating.py`):
```python
# File: backend/alembic/versions/20260401_0015_tmdb_recommendations.py
"""Add tmdb_recommendations JSON column to movies

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-01
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("tmdb_recommendations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "tmdb_recommendations")
```

**Note on `sa.JSON` with SQLite:** SQLAlchemy's `sa.JSON` type works with SQLite (stored as TEXT, serialised/deserialised transparently). No special configuration needed for this project.

---

## Settings Integration — Full Pattern

**Backend `settings.py`:**
- Add `tmdb_suggestions_seed_count: str | None = None` to both `SettingsResponse` and `SettingsUpdateRequest` (string, consistent with all other numeric settings which are stored as Text)

**`app_settings` DB row:** key `"tmdb_suggestions_seed_count"`, default value `"5"` if not set.

**Frontend `api.ts` `SettingsDTO`:** Add `tmdb_suggestions_seed_count: string | null`.

**Frontend `Settings.tsx`:** Add a number input in a "Suggested Movies" section or alongside TMDB settings. Label: "Recommendation seed depth (last N watched movies)".

---

## Frontend Integration — Exact Touch Points

### `GameSession.tsx` state additions
```typescript
const [showSuggestedOnly, setShowSuggestedOnly] = useState(false)
```

### Suggestions query
```typescript
const { data: suggestionsData } = useQuery({
  queryKey: ["suggestions", sid, session?.current_movie_tmdb_id],
  queryFn: () => api.getSessionSuggestions(sid),
  enabled: isWatched,  // same condition as eligible movies
})
const suggestionIds = new Set(suggestionsData?.suggestion_tmdb_ids ?? [])
```

### `filteringByMark` update (line 147)
```typescript
// Before:
const filteringByMark = showSavedOnly || showShortlistOnly
// After:
const filteringByMark = showSavedOnly || showShortlistOnly || showSuggestedOnly
```

### Filter chain (lines 182-183)
```typescript
.filter((m) => !showSuggestedOnly || suggestionIds.has(m.tmdb_id))
```

### Reset on actor/movie step change
```typescript
useEffect(() => {
  setShowSuggestedOnly(false)
}, [session?.current_movie_tmdb_id])
```

### `api.ts` new function
```typescript
getSessionSuggestions: (sessionId: number) =>
  apiFetch<{ suggestion_tmdb_ids: number[] }>(`/game/sessions/${sessionId}/suggestions`),
```

---

## Code Examples

### TMDBClient.fetch_recommendations (verified pattern)
```python
# Source: tmdb.py existing method structure
async def fetch_recommendations(self, tmdb_id: int) -> dict:
    """Fetch TMDB movie recommendations. Returns raw response with results[].

    Each result has 'id' (TMDB movie ID), 'title', 'vote_average', etc.
    Page 1 returns ~20 results — pagination not required for suggestion ranking.
    """
    async with self._sem:
        r = await self._client.get(f"/movie/{tmdb_id}/recommendations")
        r.raise_for_status()
        return r.json()
```

### Background task invocation pattern
```python
# Source: game.py line 1266-1270 (_push_watch_to_mdblist wiring)
background_tasks.add_task(
    _update_session_suggestions,
    session_id,
)
```

### `_bg_session_factory` usage
```python
# Source: mdblist.py _push_watch_to_mdblist lines 30-64
async def _update_session_suggestions(session_id: int) -> None:
    try:
        async with _bg_session_factory() as db:
            api_key = await settings_service.get_setting(db, "tmdb_api_key")
            if not api_key:
                return
            n_str = await settings_service.get_setting(db, "tmdb_suggestions_seed_count")
            n = int(n_str or "5")
            tmdb = TMDBClient(api_key)
            try:
                await _do_update(session_id, db, tmdb, n)
            finally:
                await tmdb.close()
    except Exception:
        logger.exception("_update_session_suggestions error session_id=%d", session_id)
```

---

## Session Suggestions Endpoint — Design Decision

**Recommendation: dedicated `GET /sessions/{id}/suggestions` endpoint** (not a flag on eligible movies).

| Factor | Dedicated endpoint | Flag on eligible movies |
|--------|--------------------|------------------------|
| Call frequency | Once per actor step | Every sort/filter/page change |
| Suggestions stability | Stable per step | Recomputed unnecessarily |
| Eligible movies endpoint impact | None | Adds latency + complexity to an already complex endpoint |
| Frontend implementation | One extra `useQuery` | Bloats existing query |
| Data returned | `{ suggestion_tmdb_ids: [int] }` (tiny) | Full movie list + suggestion flag |

**Verdict:** Dedicated endpoint. It is simpler, cheaper to call, and keeps the eligible movies endpoint unchanged.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/` (pytest config in pyproject.toml or pytest.ini — not verified) |
| Quick run command | `cd backend && pytest tests/test_game.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUGGEST-01 | `GET /sessions/{id}/suggestions` returns intersection of TMDB recs and eligible pool | unit | `pytest tests/test_suggestions.py -x` | No — Wave 0 gap |
| SUGGEST-01 | BG task wired into `mark_current_watched` | unit (mock) | `pytest tests/test_game.py::test_mark_current_watched_fires_suggestions_task -x` | No — Wave 0 gap |
| SUGGEST-02 | Suggested movies render with same actions as regular eligible movies | manual | N/A — browser verification | N/A |
| SUGGEST-03 | Toggle hidden when no suggestions intersect | unit | `pytest tests/test_suggestions.py::test_empty_suggestions_returns_empty -x` | No — Wave 0 gap |

### Wave 0 Gaps
- [ ] `backend/tests/test_suggestions.py` — covers SUGGEST-01, SUGGEST-03
- [ ] `backend/tests/test_game.py` — add `test_mark_current_watched_fires_suggestions_task`

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| In-memory suggestion computation | Per-movie cached JSON column | Reduces TMDB calls to 1/watch in steady state |
| Separate suggestions tab | Filter toggle alongside Saved/Shortlist | Consistent with existing filter UX |
| Blocking TMDB call on eligible movies | Fire-and-forget BG task | Non-blocking; results available by the time user opens panel |

---

## Open Questions

1. **What if the TMDBClient instantiated in the BG task has no request-level semaphore sharing?**
   - What we know: Each `TMDBClient` instance has its own `asyncio.Semaphore(10)`. A fresh instance in the BG task has a separate semaphore from the one used by request handlers.
   - What's unclear: Whether simultaneous BG tasks + requests could briefly exceed the TMDB ~40 req/s soft limit.
   - Recommendation: Not a concern for Phase 15. BG task makes at most 1 TMDB call per `mark_current_watched` event. No concurrency issue in practice.

2. **Should `tmdb_recommendations` be included in `Movie` model relationship loads?**
   - What we know: The `Movie` model uses `lazy="raise"` for relationships. The `tmdb_recommendations` column is a plain column (not a relationship), so it loads with the model by default.
   - What's unclear: Whether loading this JSON column in every Movie fetch (e.g., in `get_eligible_movies` which loads many Movie rows) adds meaningful overhead.
   - Recommendation: Use `defer(Movie.tmdb_recommendations)` in queries that don't need it if profiling shows overhead. Not worth pre-optimising.

---

## Sources

### Primary (HIGH confidence)
- TMDB official API docs (`developer.themoviedb.org/reference/movie-recommendations`) — endpoint URL, response structure, auth method verified
- TMDB rate limiting docs (`developer.themoviedb.org/docs/rate-limiting`) — ~40 req/s soft cap, no daily quota confirmed
- `/Users/Oreo/Projects/CinemaChain/backend/app/services/tmdb.py` — exact HTTP client pattern, semaphore, base URL
- `/Users/Oreo/Projects/CinemaChain/backend/app/routers/game.py` — `mark_current_watched` (lines 1224–1288), `get_eligible_movies` (lines 1437–1759), BackgroundTasks wiring
- `/Users/Oreo/Projects/CinemaChain/backend/app/routers/mdblist.py` — `_push_watch_to_mdblist` and `_bg_session_factory` background task pattern
- `/Users/Oreo/Projects/CinemaChain/backend/app/db.py` — `_bg_session_factory` definition
- `/Users/Oreo/Projects/CinemaChain/backend/app/models/__init__.py` — `Movie`, `WatchEvent`, `AppSettings` models
- `/Users/Oreo/Projects/CinemaChain/backend/app/routers/settings.py` — `SettingsResponse`, `SettingsUpdateRequest`
- `/Users/Oreo/Projects/CinemaChain/backend/alembic/versions/20260401_0014_watch_event_rating.py` — latest migration pattern
- `/Users/Oreo/Projects/CinemaChain/frontend/src/pages/GameSession.tsx` — filter state (showSavedOnly/showShortlistOnly), filteringByMark, filter button location
- `/Users/Oreo/Projects/CinemaChain/frontend/src/lib/api.ts` — `EligibleMovieDTO`, `apiFetch` pattern, existing session API

### Secondary (MEDIUM confidence)
- WebSearch on TMDB rate limits (2025): confirms no daily quota, ~40 req/s soft cap — consistent with official docs

---

## Metadata

**Confidence breakdown:**
- TMDB endpoint details: HIGH — verified via official docs
- Background task pattern: HIGH — copied from existing codebase
- Migration pattern: HIGH — 14 prior migrations reviewed
- Frontend filter integration: HIGH — exact parallel with existing Saved/Shortlist
- Settings integration: HIGH — exact parallel with existing string-typed settings

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (TMDB API is stable; internal codebase is the primary reference)
