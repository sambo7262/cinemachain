# Phase 17: Backend Scheduler, Settings Audit & IMDB Movie Links — Research

**Researched:** 2026-04-01
**Domain:** APScheduler (asyncio), SQLAlchemy async engine, FastAPI lifespan, React/TypeScript settings UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Decision 1: IMDB Movie Links (IMDB-01)**
- Scope is movies only — actor IMDB links are dropped entirely
- `ChainHistory.tsx` already has IMDB-first link logic; the gap is `StepResponse` not including `movie_imdb_id`
- Fix: add `movie_imdb_id: str | None = None` to `StepResponse` in `game.py`; populate from `Movie.imdb_id` in `_build_session_response` via an `imdb_map` parallel to `poster_map`
- No migration needed — `Movie.imdb_id` column already exists
- TMDB fallback is intentional and permanent for movies MDBList cannot find

**Decision 2: Nightly Scheduler Redesign (SCHED-01)**
- Two separate APScheduler jobs — not one monolithic job
- Both jobs use `timezone="America/Los_Angeles"`
- Job A (TMDB): raise all backfill limits from 2,000 → 25,000; add 429 exponential backoff (start 5s, cap 60s); priority ordering `ORDER BY <missing_field> NULLS FIRST, vote_count DESC NULLS LAST`; on-demand trigger `POST /cache/run-now` + `GET /cache/status`; remove standalone overview pass (covered by stub pass)
- Job B (MDBList): new scheduled job; 1 req/s; 25,000 calls/day limit; priority ordering (never fetched first, then stale > 90 days, by vote_count DESC); 90-day re-fetch threshold; respects existing `mdblist_calls_today` quota; time configurable via `mdblist_schedule_time` setting; default `04:00` LA time

**Decision 3: DB Connection Pool (SCHED-02)**
Exact engine config to use:
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=60,
    connect_args={"command_timeout": 60},
    echo=False,
)
```

**Decision 4: Settings Audit & Settings Page Overhaul (SCHED-03)**
- Add `TZ=America/Los_Angeles` to `backend` service environment in `compose.yaml`
- Change both CronTrigger instances to `timezone="America/Los_Angeles"`
- Remove `tmdb_base_url` from `SettingsResponse`, `SettingsUpdateRequest`, `_ENV_KEYS_TO_MIGRATE`, and migration default
- Add new settings keys: `mdblist_schedule_time` (str HH:MM, default `04:00`) and `mdblist_refetch_days` (int, default `90`)
- API key fields (tmdb, radarr, mdblist) become password-style inputs
- New Settings page sections: TMDB, MDBList, Radarr, DB Health
- New endpoint `GET /settings/db-health` — live query, not cached
- `mdblist_calls_today` / `mdblist_calls_reset_date` stay internal (not in SettingsResponse)
- `tmdb_cache_run_on_startup` stays `.env`-only

### Claude's Discretion

None specified — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- User timezone configurability — `TZ=America/Los_Angeles` is hardcoded, no UI picker
- IMDB actor links — `imdb_person_id` backfill dropped entirely
- RT score backfill removal from TMDB job — leaving the `backfill_rt_scores` call in `nightly_cache_job` for now; planner should flag if double-counting is a concern
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHED-01 | Nightly backfill redesigned as two separate APScheduler jobs (TMDB + MDBList) with raised limits, 429 backoff, priority ordering, and on-demand triggers | APScheduler `AsyncIOScheduler` + `CronTrigger` patterns documented below; on-demand trigger pattern mirrors existing MDBList backfill; in-memory `_CacheState` dataclass for status tracking |
| SCHED-02 | DB connection pool hardened with pool_size=10, max_overflow=5, pool_pre_ping, pool_recycle, pool_timeout, and asyncpg command_timeout | Exact config specified by user; SQLAlchemy asyncpg `connect_args` documented; `_bg_session_factory` uses the same engine |
| SCHED-03 | Settings page restructured with TMDB/MDBList/Radarr/DB Health sections; new settings keys; API keys masked; tmdb_base_url removed; timezone fixed | Full Settings.tsx rewrite; new `GET /settings/db-health` endpoint; Postgres table-size query pattern documented |
| IMDB-01 | `movie_imdb_id` surfaced in ChainHistory via `StepResponse` populated from `Movie.imdb_id` | ChainHistory.tsx already has IMDB-first link logic; `_build_session_response` needs `imdb_map` parameter; all 9 call-sites need updating |
</phase_requirements>

---

## Summary

Phase 17 is a backend hardening and settings overhaul phase. The codebase is well-understood — all four requirements map directly to existing code files with no ambiguous architecture choices. The research below confirms exact code paths, identifies all change-sites, and documents gotchas found during code review.

The IMDB link fix (IMDB-01) is the smallest change: one new field in `StepResponse`, one DB query extension in `_enrich_steps_thumbnails` (or a new `_enrich_steps_imdb_ids` helper), and one `imdb_map` parameter threaded through `_build_session_response`. The challenge is that `_build_session_response` is called from 9 distinct call-sites in `game.py` — all need the `imdb_map` wiring but most don't call `_enrich_steps_thumbnails`, so the imdb_map must be populated separately or the thumbnail enrichment extended to also return imdb data.

The scheduler redesign (SCHED-01) is the largest change: a new `_run_mdblist_nightly` function in `mdblist.py` (or a separate scheduler module), wiring it into `main.py` alongside the existing TMDB job, and adding `POST /cache/run-now` + `GET /cache/status` endpoints. The MDBList scheduled job is a variant of the existing `_run_backfill` with priority ordering and a 90-day re-fetch filter added.

The connection pool (SCHED-02) is a one-line change in `db.py`. The settings overhaul (SCHED-03) is the most UI-intensive: a full `Settings.tsx` rewrite and two new backend endpoints.

**Primary recommendation:** Implement in four discrete plans: IMDB-01 → SCHED-02 → SCHED-01 → SCHED-03 (UI last, since it builds on the new endpoints from SCHED-01).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.x (AsyncIOScheduler) | Cron job scheduling in asyncio context | Already in use — nightly TMDB cache job running |
| SQLAlchemy async | 2.x | Async DB engine + connection pool | Already in use — entire backend uses it |
| asyncpg | current | Async PostgreSQL driver | Already in use via `postgresql+asyncpg://` URL |
| FastAPI | current | API endpoints | Already in use throughout |
| React Query | v5 | Frontend data fetching + polling | Already in use — MDBList backfill UI uses 2s polling pattern |

### No New Libraries
Phase 17 introduces no new dependencies. All work uses existing stack.

---

## Architecture Patterns

### Pattern 1: APScheduler Two-Job Registration

Current `main.py` registers one job. The MDBList job is added as a second `scheduler.add_job` call in the same `lifespan` function.

```python
# Source: main.py lifespan — existing TMDB job (to be updated)
scheduler.add_job(
    nightly_cache_job,
    trigger=CronTrigger(hour=cache_hour, minute=cache_minute, timezone="America/Los_Angeles"),
    kwargs={"tmdb": tmdb_client, "top_n": settings.tmdb_cache_top_n, "top_actors": settings.tmdb_cache_top_actors},
    id="nightly_tmdb_cache",
    replace_existing=True,
    misfire_grace_time=3600,
)

# NEW: MDBList job — read schedule time from app_settings at startup
mdb_time = "04:00"  # default — overridden by DB setting if present
scheduler.add_job(
    mdblist_nightly_job,
    trigger=CronTrigger(hour=mdb_hour, minute=mdb_minute, timezone="America/Los_Angeles"),
    id="nightly_mdblist",
    replace_existing=True,
    misfire_grace_time=3600,
)
```

**Key point:** The MDBList schedule time (`mdblist_schedule_time`) is stored in `app_settings` DB, not `.env`. The lifespan needs to read it at startup via `settings_service.get_setting`. This requires an async DB read inside the lifespan before the scheduler starts — the existing lifespan already does this for `.env` migration, so the pattern is established.

### Pattern 2: On-Demand TMDB Job Trigger

The existing MDBList backfill uses `BackgroundTasks.add_task` for on-demand triggering. The TMDB on-demand endpoint mirrors this pattern but must also guard against concurrent runs.

```python
# In-memory state tracking (same pattern as _BackfillState in mdblist.py)
@dataclass
class _CacheState:
    running: bool = False
    last_run_at: datetime | None = None
    last_run_duration_s: float | None = None

_cache_state = _CacheState()

@router.post("/cache/run-now")
async def run_cache_now(background_tasks: BackgroundTasks, request: Request):
    if _cache_state.running:
        return {"running": True}
    tmdb = request.app.state.tmdb_client
    background_tasks.add_task(_run_cache_with_tracking, tmdb)
    return {"started": True}
```

**Note:** `POST /cache/run-now` needs `request: Request` to access `app.state.tmdb_client`, since the TMDB client is stored on app state at startup.

The `/cache/` router prefix must be added to `main.py` via `app.include_router(cache_router)`. Currently `cache.py` is a service (no router). Decision: add a minimal router to `cache.py` or create a new `routers/cache.py`. The latter is cleaner — mirrors the existing `mdblist.py` router pattern.

### Pattern 3: IMDB ID Map in _build_session_response

The existing `_enrich_steps_thumbnails` queries `Movie.tmdb_id, Movie.poster_path`. The cleanest approach is extending the same query to also fetch `Movie.imdb_id`, returning a third map:

```python
async def _enrich_steps_thumbnails(
    steps: list[GameSessionStep], db: AsyncSession
) -> tuple[dict[int, str | None], dict[int, str | None], dict[int, str | None]]:
    """Return (poster_map, profile_map, imdb_map)."""
    ...
    if movie_tmdb_ids:
        m_rows = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path, Movie.imdb_id)
            .where(Movie.tmdb_id.in_(movie_tmdb_ids))
        )
        rows = m_rows.all()
        poster_map = {row.tmdb_id: row.poster_path for row in rows}
        imdb_map = {row.tmdb_id: row.imdb_id for row in rows}
```

**Alternative:** A standalone `_enrich_steps_imdb_ids(steps, db) -> dict` helper. This avoids changing the return signature of `_enrich_steps_thumbnails` but requires a second DB round-trip. Extending the existing function is preferred — one query.

**Call-site audit:** `_enrich_steps_thumbnails` is called at 6 call-sites in `game.py`. The other 9 calls to `_build_session_response` that do NOT call `_enrich_steps_thumbnails` will need `imdb_map=None` (which will populate imdb_id as None for all steps — TMDB fallback takes over in the frontend). The full-enrich call-sites (active session, get_session_by_id, mark_current_watched, delete_last_step, pick_actor, archive_session) should also call the extended thumbnail function to populate imdb_map.

```python
# StepResponse addition (game.py)
class StepResponse(BaseModel):
    step_order: int
    movie_tmdb_id: int
    movie_title: str | None
    movie_imdb_id: str | None = None   # NEW — populated where imdb_map is available
    actor_tmdb_id: int | None
    actor_name: str | None
    watched_at: _datetime | None = None
    poster_path: str | None = None
    profile_path: str | None = None
```

### Pattern 4: Priority-Ordered Backfill Query (SQLAlchemy)

Priority ordering for all backfill passes uses `nulls_first(asc(...))` combined with `vote_count DESC NULLS LAST`. The existing `mdblist.py` already imports and uses `nulls_first` and `asc`:

```python
# Source: mdblist.py — existing pattern
from sqlalchemy import select, or_, func, asc, nulls_first
...
result = await db.execute(
    select(Movie).order_by(nulls_first(asc(Movie.mdblist_fetched_at)))
)
```

For the stub backfill pass in `cache.py`, the query becomes:
```python
select(Movie.tmdb_id).where(
    (Movie.title == "") | Movie.genres.is_(None)
).order_by(
    Movie.genres.is_(None).desc(),  # NULL genres first
    Movie.vote_count.desc().nulls_last()
).limit(25000)
```

SQLAlchemy 2.x supports `.nulls_last()` as a method on column expressions directly. Alternatively, import `nullslast` from `sqlalchemy`:
```python
from sqlalchemy import nullslast, desc
.order_by(nullslast(desc(Movie.vote_count)))
```

### Pattern 5: asyncpg connect_args

The `connect_args` parameter for asyncpg `command_timeout` is passed as:
```python
engine = create_async_engine(
    settings.database_url,
    ...
    connect_args={"command_timeout": 60},  # asyncpg-specific
)
```

This is asyncpg-specific syntax. The timeout is in seconds. `pool_pre_ping=True` sends a lightweight `SELECT 1` before each connection is handed to a requester — important for NAS idle wakeup scenarios.

### Pattern 6: DB Health Query

PostgreSQL table sizes use `pg_total_relation_size`:

```sql
SELECT
  pg_size_pretty(pg_total_relation_size('movies')) AS movies,
  pg_size_pretty(pg_total_relation_size('credits')) AS credits,
  pg_size_pretty(pg_total_relation_size('actors')) AS actors,
  pg_size_pretty(pg_total_relation_size('watch_events')) AS watch_events,
  pg_size_pretty(pg_database_size('cinemachain')) AS total_db
```

The row-level health stats use `COUNT(*) FILTER (WHERE ...)` in a single query:
```sql
SELECT
  COUNT(*) AS total_movies,
  COUNT(*) FILTER (WHERE overview IS NULL OR overview = '') AS missing_overview,
  COUNT(*) FILTER (WHERE mpaa_rating IS NULL OR mpaa_rating = '') AS missing_mpaa,
  COUNT(*) FILTER (WHERE imdb_id IS NULL OR imdb_id = '') AS missing_imdb_id,
  COUNT(*) FILTER (WHERE imdb_rating IS NULL OR imdb_rating = 0) AS missing_imdb_rating,
  COUNT(*) FILTER (WHERE rt_score IS NULL OR rt_score = 0) AS missing_rt_score,
  COUNT(*) FILTER (WHERE mdblist_fetched_at IS NULL) AS never_mdblist_fetched
FROM movies
```

In SQLAlchemy async, this is run with `await db.execute(text("..."))`.

### Pattern 7: MDBList Nightly Job (Scheduled Variant)

The scheduled MDBList job is a variant of `_run_backfill` with two changes:
1. **Priority ordering with re-fetch threshold filter:** `WHERE mdblist_fetched_at IS NULL OR mdblist_fetched_at < NOW() - INTERVAL '90 days'`, ordered by `nulls_first(asc(mdblist_fetched_at))`, then `vote_count DESC NULLS LAST`.
2. **Uses stored `mdblist_refetch_days` setting** from `app_settings` (default 90) to compute the interval dynamically.

The scheduled job shares `_increment_quota` and respects `_state.calls_used_today` — same in-memory state tracker. If quota is already exhausted when the scheduled job fires, it logs a no-op and returns.

### Pattern 8: Settings Page — Per-Field Password Masking

The current Settings.tsx has `type="password"` only on `mdblist-api-key`. The redesign applies `type="password"` to all three API key fields:
- `tmdb_api_key`
- `radarr_api_key`
- `mdblist_api_key`

The `tmdb_base_url` field is removed entirely from the form and validation (`handleSave` currently validates `tmdb_base_url` as required URL — this validation must be removed).

### Anti-Patterns to Avoid

- **Calling `_enrich_steps_thumbnails` in ALL `_build_session_response` call-sites:** The existing code only calls it for fully-enriched session views. The cheaper session endpoints (list, archive, create) skip it intentionally for performance. The `imdb_map` should follow the same selective-enrichment pattern — only pass it where thumbnails are already being fetched.
- **Reading `mdblist_schedule_time` from `.env` at startup:** The value is in `app_settings` DB. At startup the lifespan must read it from DB with a fallback of `"04:00"` if not yet set.
- **Modifying `_bg_session_factory`:** The decision says pool_size changes apply to `engine`. Both `AsyncSessionLocal` and `_bg_session_factory` use the same `engine` instance, so they automatically inherit the new pool settings.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 429 exponential backoff | Custom retry loop | `asyncio.sleep` with doubling delay (start 5s, cap 60s) inside existing for-loops | Simple enough in-line; no library needed given single caller |
| DB table sizes | Manual byte counting | `pg_total_relation_size` + `pg_size_pretty` PostgreSQL built-ins | Accurate, zero code |
| Scheduler job run tracking | Event listeners | In-memory `_CacheState` dataclass (same pattern as `_BackfillState`) | App is single-process; state survives restarts via DB |
| Priority NULL ordering | Python sort post-query | SQLAlchemy `nulls_first()` / `nullslast()` | DB-side ordering is correct and efficient |

---

## Common Pitfalls

### Pitfall 1: MDBList Schedule Time Read at Startup
**What goes wrong:** `mdblist_schedule_time` is stored in `app_settings` DB, not in `.env`. If `settings_service.get_setting` returns `None` (first deploy, DB empty), the scheduler fails to start or uses wrong time.
**Why it happens:** DB settings are migrated in lifespan step 1b but may not include `mdblist_schedule_time` since it's a new key.
**How to avoid:** Default to `"04:00"` when the DB returns None. Use `(await settings_service.get_setting(db, "mdblist_schedule_time")) or "04:00"` and handle the async read using the existing DB session opened in the lifespan.
**Warning signs:** Scheduler startup log shows wrong time or crashes with `AttributeError` on None.split().

### Pitfall 2: _build_session_response Call-Site Audit
**What goes wrong:** `movie_imdb_id` is `None` for ALL steps on endpoints that don't call `_enrich_steps_thumbnails`, since the imdb_map is not populated.
**Why it happens:** `_build_session_response` is called from 9 places; only 6 of them call `_enrich_steps_thumbnails`. The other 3 (session list, archived list, various lightweight endpoints) skip thumbnail enrichment.
**How to avoid:** This is intentional and correct — TMDB fallback in `ChainHistory.tsx` handles `None`. Document that imdb_map is only populated on full-enrich paths.
**Warning signs:** Would only matter if ChainHistory broke on missing imdb_id — it already handles this with the ternary operator.

### Pitfall 3: tmdb_base_url Validation in handleSave
**What goes wrong:** After removing `tmdb_base_url` from the Settings form, the `handleSave` function in `Settings.tsx` still validates `formData.tmdb_base_url` as required. This will always error since the field is no longer in the form.
**Why it happens:** The validation block must be explicitly updated when removing the field.
**How to avoid:** Remove the `tmdb_base_url` validation check from `handleSave`; also remove it from `emptyForm`, `SettingsDTO` (api.ts), and `nullToEmpty`.
**Warning signs:** Save button always shows field error even with no `tmdb_base_url` input visible.

### Pitfall 4: CronTrigger Timezone vs TZ Environment Variable
**What goes wrong:** Setting `TZ=America/Los_Angeles` in `compose.yaml` changes the container's system clock interpretation. If CronTrigger still uses `timezone="UTC"`, the job still fires at UTC time — but `datetime.utcnow()` calls in logging may appear shifted.
**Why it happens:** APScheduler's timezone parameter is independent of the OS TZ env var.
**How to avoid:** Both changes are needed together: `TZ=America/Los_Angeles` in compose + `timezone="America/Los_Angeles"` in both CronTrigger instances. Verify the scheduler startup log shows the correct next fire time.
**Warning signs:** After deploy, scheduler logs show next run at unexpected wall-clock time.

### Pitfall 5: RT Score Double-Counting
**What goes wrong:** The existing `nightly_cache_job` calls `_backfill_rt_scores_pass` which internally calls `backfill_rt_scores` from `mdblist.py`. Once the new MDBList scheduled job also runs nightly, both jobs touch RT score fields via MDBList API — consuming quota twice.
**Why it happens:** The CONTEXT.md defers removing `_backfill_rt_scores_pass` from the TMDB job. The two jobs share the same quota counter (`mdblist_calls_today`), so double-counting shows up as faster quota exhaustion.
**How to avoid:** The shared quota counter in `_increment_quota` will self-limit. Document this in code comments. Flag to user: once the MDBList job runs consistently, remove `_backfill_rt_scores_pass` from the TMDB job in a future pass.
**Warning signs:** `mdblist_calls_today` reaches 25,000 sooner than expected.

### Pitfall 6: 429 Backoff Resets to Beginning of Movie List
**What goes wrong:** On 429, the existing `_run_backfill` uses `continue` to retry the same movie. The TMDB backfill loop doesn't have 429 handling at all — `r.raise_for_status()` will throw an exception and the movie is skipped.
**Why it happens:** TMDB 429 is a transient rate limit; skipping the movie permanently is wrong.
**How to avoid:** Add explicit 429 check before `raise_for_status()`. On 429: sleep with exponential backoff (start 5s, cap 60s, no skip), then retry. Use a retry counter per-movie (max 3 retries) to avoid infinite loops on persistent 429.
**Warning signs:** TMDB backfill logs show a cascade of "failed for tmdb_id=X" during heavy runs.

---

## Code Examples

### Extending _enrich_steps_thumbnails to return imdb_map
```python
# Source: game.py — extend existing function
async def _enrich_steps_thumbnails(
    steps: list[GameSessionStep], db: AsyncSession
) -> tuple[dict[int, str | None], dict[int, str | None], dict[int, str | None]]:
    """Return (poster_map, profile_map, imdb_map)."""
    movie_tmdb_ids = [s.movie_tmdb_id for s in steps]
    actor_tmdb_ids = [s.actor_tmdb_id for s in steps if s.actor_tmdb_id is not None]

    poster_map: dict[int, str | None] = {}
    profile_map: dict[int, str | None] = {}
    imdb_map: dict[int, str | None] = {}

    if movie_tmdb_ids:
        m_rows = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path, Movie.imdb_id)
            .where(Movie.tmdb_id.in_(movie_tmdb_ids))
        )
        rows = m_rows.all()
        poster_map = {row.tmdb_id: row.poster_path for row in rows}
        imdb_map = {row.tmdb_id: row.imdb_id for row in rows}

    if actor_tmdb_ids:
        a_rows = await db.execute(
            select(Actor.tmdb_id, Actor.profile_path).where(Actor.tmdb_id.in_(actor_tmdb_ids))
        )
        profile_map = {row.tmdb_id: row.profile_path for row in a_rows.all()}

    return poster_map, profile_map, imdb_map
```

### _build_session_response with imdb_map
```python
# Source: game.py — add imdb_map parameter
def _build_session_response(
    session: GameSession,
    watched_at_map: dict[int, _datetime] | None = None,
    radarr_status: str | None = None,
    current_movie_title: str | None = None,
    poster_map: dict[int, str | None] | None = None,
    profile_map: dict[int, str | None] | None = None,
    runtime_map: dict[int, int | None] | None = None,
    imdb_map: dict[int, str | None] | None = None,   # NEW
) -> GameSessionResponse:
    ...
    steps.append(StepResponse(
        ...
        poster_path=(poster_map or {}).get(s.movie_tmdb_id),
        profile_path=(profile_map or {}).get(s.actor_tmdb_id) if s.actor_tmdb_id else None,
        movie_imdb_id=(imdb_map or {}).get(s.movie_tmdb_id),   # NEW
    ))
```

### 429 Exponential Backoff for TMDB Cache
```python
# In _backfill_mpaa_pass and stub backfill loops:
MAX_RETRIES = 3
retry_delay = 5.0
for attempt in range(MAX_RETRIES):
    r = await tmdb._client.get(...)
    if r.status_code == 429:
        logger.warning("TMDB 429 on tmdb_id=%d, backing off %.0fs", tmdb_id, retry_delay)
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60.0)
        continue
    r.raise_for_status()
    # ... process response
    break
```

### MDBList Nightly Job with Re-Fetch Filter
```python
# In mdblist.py — new scheduled variant
from datetime import timedelta
from sqlalchemy import or_, and_

async def _run_mdblist_nightly():
    async with _bg_session_factory() as db:
        refetch_days_str = await settings_service.get_setting(db, "mdblist_refetch_days") or "90"
        refetch_days = int(refetch_days_str)
        cutoff = datetime.utcnow() - timedelta(days=refetch_days)

        result = await db.execute(
            select(Movie).where(
                or_(
                    Movie.mdblist_fetched_at.is_(None),
                    Movie.mdblist_fetched_at < cutoff,
                )
            ).order_by(
                nulls_first(asc(Movie.mdblist_fetched_at)),
                nullslast(desc(Movie.vote_count)),
            )
        )
        movies = result.scalars().all()
    # ... same loop as _run_backfill with quota guard at top
```

### GET /settings/db-health Endpoint
```python
# In routers/settings.py
from sqlalchemy import text

@router.get("/db-health")
async def get_db_health(db: AsyncSession = Depends(get_db)):
    row_stats = await db.execute(text("""
        SELECT
          COUNT(*) AS total_movies,
          COUNT(*) FILTER (WHERE overview IS NULL OR overview = '') AS missing_overview,
          COUNT(*) FILTER (WHERE mpaa_rating IS NULL OR mpaa_rating = '') AS missing_mpaa,
          COUNT(*) FILTER (WHERE imdb_id IS NULL OR imdb_id = '') AS missing_imdb_id,
          COUNT(*) FILTER (WHERE imdb_rating IS NULL OR imdb_rating = 0) AS missing_imdb_rating,
          COUNT(*) FILTER (WHERE rt_score IS NULL OR rt_score = 0) AS missing_rt_score,
          COUNT(*) FILTER (WHERE mdblist_fetched_at IS NULL) AS never_mdblist_fetched
        FROM movies
    """))
    r = row_stats.mappings().one()

    total_actors = await db.execute(text("SELECT COUNT(*) FROM actors"))

    size_stats = await db.execute(text("""
        SELECT
          pg_size_pretty(pg_database_size(current_database())) AS total_db,
          pg_size_pretty(pg_total_relation_size('movies')) AS movies,
          pg_size_pretty(pg_total_relation_size('credits')) AS credits,
          pg_size_pretty(pg_total_relation_size('actors')) AS actors,
          pg_size_pretty(pg_total_relation_size('watch_events')) AS watch_events
    """))
    s = size_stats.mappings().one()

    return {
        "row_health": dict(r) | {"total_actors": total_actors.scalar()},
        "table_sizes": dict(s),
    }
```

### Settings.tsx — tmdb_cache_top_actors field (missing from current form)
Current `Settings.tsx` is missing `tmdb_cache_top_actors` from the Sync Schedule card even though it exists in `SettingsDTO`. The redesign adds it alongside `tmdb_cache_top_n`. Verify during implementation.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `timezone="UTC"` in CronTrigger | `timezone="America/Los_Angeles"` + `TZ=` env | Phase 17 | Jobs fire at correct local time |
| `pool_size=5, max_overflow=2` | `pool_size=10, max_overflow=5, pre_ping, recycle` | Phase 17 | Handles concurrent backfill + web requests |
| 2,000-item backfill limits | 25,000-item limits | Phase 17 | Clears 57k movie backlog in 2–3 nights |
| Manual MDBList backfill only | Scheduled nightly at 04:00 + manual | Phase 17 | Automated ratings currency |

**Deprecated in this phase:**
- `tmdb_base_url` in settings: Hardcoded in `TMDBClient.BASE_URL` already; removing from UI reduces confusion
- Standalone `_backfill_overview_pass`: Covered by `_ensure_movie_details_in_db` in stub pass; remove to reduce duplicate API calls

---

## Open Questions

1. **scheduler.reschedule_job when mdblist_schedule_time is changed via Settings UI**
   - What we know: APScheduler supports `scheduler.reschedule_job(job_id, trigger=new_trigger)` at runtime
   - What's unclear: The CONTEXT.md does not mention live reschedule — it only says the time is configurable. The current TMDB schedule time is also configurable but changes only take effect on restart.
   - Recommendation: Match the TMDB job behavior — setting change takes effect on next container restart. No live reschedule needed. Document in Settings UI label.

2. **_bg_session_factory vs AsyncSessionLocal for the new cache router**
   - What we know: Both use the same `engine`; `_bg_session_factory` is used by background jobs, `get_db` (via `AsyncSessionLocal`) is used by request handlers
   - What's unclear: The new `GET /cache/status` and `POST /cache/run-now` are request handlers but the background task uses `_bg_session_factory`
   - Recommendation: Status endpoint reads in-memory `_CacheState` (no DB needed). Run-now endpoint uses `BackgroundTasks` to launch the job (same as MDBList backfill pattern) — no direct DB access in the handler itself.

---

## Validation Architecture

Framework is pytest with `asyncio_mode = auto`. Tests live in `backend/tests/`. Quick run: `pytest tests/test_cache.py tests/test_settings.py -x`. Full suite: `pytest`.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMDB-01 | `StepResponse` includes `movie_imdb_id` populated from Movie.imdb_id | unit | `pytest tests/test_game.py -k imdb -x` | ✅ (test_game.py exists; new test needed) |
| SCHED-01 | nightly_cache_job raises limits to 25k; MDBList nightly job respects quota + re-fetch threshold | unit | `pytest tests/test_cache.py tests/test_mdblist.py -x` | ✅ |
| SCHED-02 | Engine pool settings applied (pool_size=10, pre_ping, recycle) | unit | `pytest tests/test_models.py -x` | ✅ (structural — verify in code review) |
| SCHED-03 | GET /settings/db-health returns expected JSON shape; new settings keys round-trip via PUT /settings | unit | `pytest tests/test_settings.py -x` | ✅ |

### Sampling Rate
- Per task commit: `pytest tests/test_cache.py tests/test_game.py tests/test_settings.py tests/test_mdblist.py -x`
- Per wave merge: `pytest`
- Phase gate: Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cache.py` — needs new test: `test_nightly_cache_job_priority_ordering` and `test_tmdb_429_backoff`
- [ ] `tests/test_mdblist.py` — needs new test: `test_mdblist_nightly_job_respects_refetch_threshold`
- [ ] `tests/test_game.py` — needs new test: `test_step_response_includes_movie_imdb_id`
- [ ] `tests/test_settings.py` — needs new test: `test_db_health_endpoint_returns_expected_keys`

---

## Sources

### Primary (HIGH confidence)
- Codebase direct read — `backend/app/main.py`, `db.py`, `routers/game.py`, `routers/settings.py`, `routers/mdblist.py`, `services/cache.py`, `services/settings_service.py`, `models/__init__.py`
- Codebase direct read — `frontend/src/components/ChainHistory.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/lib/api.ts`
- Codebase direct read — `compose.yaml`, `backend/.env.example`, `backend/app/settings.py`
- `.planning/phases/17-backend-scheduler-settings-audit/17-CONTEXT.md` — all decisions

### Secondary (MEDIUM confidence)
- APScheduler AsyncIOScheduler / CronTrigger pattern: verified against existing working implementation in codebase
- SQLAlchemy asyncpg `connect_args={"command_timeout": 60}`: standard asyncpg-specific parameter
- PostgreSQL `pg_total_relation_size` / `pg_size_pretty`: standard Postgres catalog functions

---

## Metadata

**Confidence breakdown:**
- IMDB-01: HIGH — exact code paths confirmed, ChainHistory already wired, only backend field missing
- SCHED-01: HIGH — APScheduler already running, patterns established, all constraints from CONTEXT.md
- SCHED-02: HIGH — one-line change, exact config specified by user
- SCHED-03: HIGH — full Settings.tsx audit completed, all removal targets and new fields identified

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack, no fast-moving dependencies)
