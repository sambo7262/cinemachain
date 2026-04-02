---
plan: 17-02
status: complete
completed_at: 2026-04-02T06:01:34Z
phase: 17-backend-scheduler-settings-audit
subsystem: backend
tags: [scheduler, cache, mdblist, apscheduler, backfill]
requirements: [SCHED-01]
key-decisions:
  - mdblist_nightly_job shares quota state with manual backfill via _state and _increment_quota
  - Both CronTriggers use America/Los_Angeles timezone
  - _backfill_mpaa_pass now fetches TMDB release_dates inline (not via _fetch_mpaa_rating) to support 429 backoff handling
  - _backfill_overview_pass removed from nightly_cache_job call chain (stub pass covers it)
key-files:
  created:
    - backend/app/routers/cache.py
  modified:
    - backend/app/services/cache.py
    - backend/app/routers/mdblist.py
    - backend/app/main.py
---

# Phase 17 Plan 02: Scheduler Redesign + Cache Router Summary

Hardened TMDB nightly job with 25k limits, priority ordering, and 429 exponential backoff; added MDBList nightly scheduled job with 90-day re-fetch threshold and quota management; created POST /cache/run-now + GET /cache/status endpoints.

## What was built

**cache.py hardening:**
- Added `_CacheState` dataclass (`running`, `last_run_at`, `last_run_duration_s`) and `_cache_state` singleton
- `nightly_cache_job` wrapped with timing tracking: sets `_cache_state.running = True` at start, records `start = datetime.utcnow()`, clears state in `try/finally`
- Stub backfill limit raised from 2,000 to 25,000 with `ORDER BY vote_count DESC NULLS LAST`
- `_backfill_mpaa_pass` default limit raised from 2,000 to 25,000 with priority ordering
- 429 exponential backoff added to `_backfill_mpaa_pass` inner loop (start 5s, cap 60s, skip after 3 retries)
- 429 exponential backoff added to TMDB discover loop in `nightly_cache_job`
- `_backfill_overview_pass` call removed from `nightly_cache_job` (function kept; stub pass covers it)

**routers/cache.py (new):**
- `POST /cache/run-now`: concurrency guard via `_cache_state.running`, triggers `nightly_cache_job` as background task with `tmdb` from `request.app.state`, `top_n`/`top_actors` from `app.state` with fallback to `app_settings`
- `GET /cache/status`: returns `{running, last_run_at, last_run_duration_s}`

**mdblist.py additions:**
- Added `timedelta` import and `desc` from sqlalchemy
- New `mdblist_nightly_job()` async function: reads quota from DB, returns early if exhausted, reads `mdblist_refetch_days` setting (default "90"), queries movies with `mdblist_fetched_at IS NULL OR mdblist_fetched_at < cutoff` ordered by `nulls_first(asc(mdblist_fetched_at)), desc(vote_count).nulls_last()`, processes each movie at 1 req/s using shared `_state`/`_increment_quota`

**main.py wiring:**
- Added imports for `cache_router` and `mdblist_nightly_job`
- TMDB CronTrigger timezone changed from `"UTC"` to `"America/Los_Angeles"`
- MDBList schedule time read from DB (`mdblist_schedule_time`, default `"04:00"`)
- Second APScheduler job `nightly_mdblist` registered with LA timezone
- `app.state.tmdb_cache_top_n` and `app.state.tmdb_cache_top_actors` stored after TMDBClient init
- `cache_router.router` registered via `app.include_router`

## Key Decisions

1. **_backfill_mpaa_pass refactored to inline fetch:** The plan specified adding 429 backoff before `r.raise_for_status()`. The original implementation delegated to `_fetch_mpaa_rating` which swallows all exceptions internally. Refactored to fetch `release_dates` inline with 429 retry logic and parse the MPAA cert directly — avoids double-fetching and allows proper 429 handling.

2. **mdblist_nightly_job shares quota state:** Rather than creating a separate state object, `mdblist_nightly_job` reads/writes to the existing `_state` (shared with manual backfill) via `_increment_quota`. Quota exhaustion from a manual run correctly blocks the scheduled run and vice versa.

3. **Both CronTriggers use America/Los_Angeles:** Per Decision 4 in 17-CONTEXT.md. TMDB at 03:00 LA, MDBList at 04:00 LA (configurable via DB setting).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _backfill_mpaa_pass refactored to avoid swallowed 429 errors**
- **Found during:** Task 1
- **Issue:** The original `_backfill_mpaa_pass` delegated to `_fetch_mpaa_rating` which uses a broad `except Exception` block that would silently swallow 429 responses, making backoff logic unreachable
- **Fix:** Fetched `release_dates` endpoint inline with 429 backoff before parsing cert and writing to DB. `_fetch_mpaa_rating` is no longer called from this pass (still available for game.py on-demand use)
- **Files modified:** `backend/app/services/cache.py`
- **Commit:** 19fc469

## Tests

- Pre-existing test failures (4): `test_cache.py` tests fail on Python 3.9 (local dev uses 3.9; app runs on 3.10+ in Docker) — unrelated to this plan. `test_mdblist.py::test_parse_all_rating_sources` has a pre-existing IMDB rating parsing bug (93.0 vs 9.3).
- All 29 passing tests continue to pass after this plan's changes.
- No new test failures introduced.

## Self-Check: PASSED

- `backend/app/services/cache.py`: exists with `_CacheState`, `_cache_state`, 25000 limits, 429 backoff, timing tracking, no `_backfill_overview_pass` call
- `backend/app/routers/cache.py`: exists with `POST /run-now` and `GET /status`
- `backend/app/routers/mdblist.py`: exists with `mdblist_nightly_job`, `mdblist_refetch_days` read
- `backend/app/main.py`: 2x `America/Los_Angeles`, `nightly_mdblist` job registered, `cache_router` included
- Commit 19fc469: confirmed
