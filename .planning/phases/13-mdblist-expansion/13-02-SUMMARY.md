---
phase: 13-mdblist-expansion
plan: "02"
subsystem: backend
tags: [mdblist, backfill, quota, ratings, background-tasks]
dependency_graph:
  requires:
    - backend/app/services/mdblist.py (MDBLIST_API_URL constant)
    - backend/app/services/settings_service.py (get_setting, save_settings)
    - backend/app/db.py (_bg_session_factory)
    - backend/app/models (Movie model with new rating fields — provided by Plan 01)
  provides:
    - POST /mdblist/backfill/start — triggers background rating backfill
    - GET /mdblist/backfill/status — returns live job state + quota
  affects:
    - backend/app/main.py (router registration)
tech_stack:
  added: []
  patterns:
    - FastAPI BackgroundTasks for non-blocking backfill execution
    - _bg_session_factory (not request-scoped session) for background DB access
    - In-memory dataclass for job state tracking
    - app_settings table for persistent daily quota counter
key_files:
  created:
    - backend/app/routers/mdblist.py
  modified:
    - backend/app/main.py
decisions:
  - Used in-memory _BackfillState dataclass (not DB-persisted) for running/fetched/total — single-user NAS, no restart concern during backfill
  - Quota counter stored in app_settings (not in-memory) so it persists across server restarts
  - Router references new Movie fields (imdb_rating, metacritic_score, letterboxd_score, mdb_avg_score, imdb_id) that Plan 01 adds via migration — router created as-spec'd per plan instructions
metrics:
  duration: "~8 minutes"
  completed: "2026-04-01T04:26:25Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 1
---

# Phase 13 Plan 02: MDBList Backfill Router Summary

MDBList backfill router with in-memory job state, per-movie HTTP calls to MDBList API, and daily quota counter persisted in app_settings.

## What Was Built

**`backend/app/routers/mdblist.py`** — New FastAPI router with:

- `_BackfillState` dataclass: `running`, `fetched`, `total`, `calls_used_today`, `daily_limit` (10,000)
- `_increment_quota(db)`: reads/writes `mdblist_calls_today` and `mdblist_calls_reset_date` from app_settings; resets counter when date changes
- `_run_backfill()`: background task that selects all movies with any NULL rating field, iterates with 0.1s sleep (~10 req/s), parses tomatometer/audience/metacritic/letterboxd/imdb/score_average from MDBList response, writes all six fields + imdb_id per movie, commits per movie, stops on 429 or quota exhaustion
- `POST /mdblist/backfill/start`: returns 409 if already running; loads current quota from DB; counts pending movies; starts background task
- `GET /mdblist/backfill/status`: returns all five state fields

**`backend/app/main.py`** — Added `from app.routers import mdblist as mdblist_router` import and `app.include_router(mdblist_router.router)` registration.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

The router references `Movie.imdb_rating`, `Movie.metacritic_score`, `Movie.letterboxd_score`, `Movie.mdb_avg_score`, and `Movie.imdb_id` — columns that Plan 01 adds via DB migration. The router is intentionally created ahead of Plan 01 completing (waves run in parallel). The `start_backfill` endpoint's count query and `_run_backfill`'s filter will raise `AttributeError` at runtime until Plan 01 migration is applied. This is expected and documented.

## Self-Check: PASSED

- backend/app/routers/mdblist.py: FOUND
- backend/app/main.py: FOUND
- Commit d884409: FOUND
