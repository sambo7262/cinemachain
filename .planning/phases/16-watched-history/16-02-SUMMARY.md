---
phase: 16-watched-history
plan: 02
subsystem: backend
tags: [api, orm, migration, watch-history]
dependencies:
  requires: [16-01]
  provides: [GlobalSave model, migration-0017, GET /movies/watched paginated, PATCH /movies/{id}/rating, POST/DELETE /movies/{id}/save]
  affects: [backend/app/routers/movies.py, backend/app/models/__init__.py]
tech-stack:
  added: []
  patterns: [null-stable two-pass sort, pg_insert on_conflict_do_nothing, WatchedMoviesResponse pagination shape]
key-files:
  created:
    - backend/alembic/versions/20260401_0017_global_saves.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/movies.py
    - backend/tests/test_models.py
key-decisions:
  - GlobalSave has no ForeignKey to game_sessions by design (session-independent bookmark)
  - Null-stable two-pass sort applied for all 7 sort keys; unknown sort key falls back to title asc
  - PATCH /rating validates 1-10 range in Python (not DB constraint) to return 422 cleanly
  - Route ordering: /watched, /poster-wall, /popular all declared before /{tmdb_id} catch-all
metrics:
  duration: 7 minutes
  completed: 2026-04-02T04:13:22Z
  tasks_completed: 2
  files_modified: 4
---

# Phase 16 Plan 02: Watch History Backend Data Layer Summary

Paginated/sorted/searchable GET /movies/watched + PATCH rating + POST/DELETE global save, backed by new GlobalSave model and Alembic migration 0017.

## What Was Built

### Task 1: GlobalSave model + Alembic migration 0017

- Created `backend/alembic/versions/20260401_0017_global_saves.py` with `revision="0017"`, `down_revision="0016"`, creating `global_saves` table with `(id, tmdb_id UNIQUE, saved_at)` and `ix_global_saves_tmdb_id` index.
- Added `GlobalSave` SQLAlchemy model to `backend/app/models/__init__.py` after `SessionShortlist`, using the same `UniqueConstraint("tmdb_id")` pattern as other save tables. No ForeignKey to `game_sessions` — this is session-independent by design.

### Task 2: Extended movies.py endpoints

**GET /movies/watched** — replaced the simple 4-field list response with a full `WatchedMoviesResponse` (paginated):
- New Pydantic models: `WatchedMovieDTO` (18 fields including `watched_at` ISO string and `personal_rating`), `WatchedMoviesResponse` (items/total/page/page_size/has_more), `RatingUpdate`
- Query params: `sort` (default: title), `sort_dir` (default: asc), `search` (ilike filter), `page` (ge=1), `page_size` (1–100, default 24)
- Null-stable two-pass sort for all 7 keys: title, year, runtime, rating (TMDB vote_average), rt, watched_at, personal_rating
- Joins `Movie + WatchEvent` to get `watched_at` and `personal_rating` (WatchEvent.rating)

**PATCH /movies/{tmdb_id}/rating**:
- Looks up `WatchEvent` by `tmdb_id`, raises 404 if not found
- Validates `1 <= rating <= 10` in Python, raises 422 if out of range
- `rating=null` clears the rating

**POST /movies/{tmdb_id}/save**:
- `pg_insert(GlobalSave)` with `on_conflict_do_nothing(index_elements=["tmdb_id"])` — safe upsert
- Returns `{tmdb_id, saved: True}`

**DELETE /movies/{tmdb_id}/save**:
- `sa.delete(GlobalSave).where(...)` — no-op if not saved
- Returns `{tmdb_id, saved: False}`

Route ordering verified: `/movies/watched` (line 85) comes before `/movies/{tmdb_id}` catch-all (line 396).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_models.py stale table assertion**
- **Found during:** Task 2 verification
- **Issue:** `test_all_four_tables_registered` expected exactly 6 tables but codebase had grown to 10 tables across previous phases (session_saves, session_shortlist, app_settings added in phases 3.x–4; global_saves added in this plan). The test had drifted without being updated.
- **Fix:** Updated expected set to include all 10 current tables
- **Files modified:** `backend/tests/test_models.py`
- **Commit:** a037100

**2. [Rule 3 - Blocking] movies.py had stale BackgroundTasks + _push_watch_to_mdblist references**
- **Found during:** Task 2 (Step 1 import changes)
- **Issue:** Plan 16-01's movies.py cleanup had not been applied yet — `BackgroundTasks` was in the fastapi import and `_push_watch_to_mdblist` was referenced in `mark_movie_watched`. The linter automatically cleaned up the `BackgroundTasks` import when I added `Query`, but `_push_watch_to_mdblist` call remained in the function body. Fixed as part of completing the module before adding new endpoints.
- **Fix:** Cleaned `mark_movie_watched` to remove `BackgroundTasks` param and the entire MDBList push block (this is Plan 16-01's intended change)
- **Files modified:** `backend/app/routers/movies.py`
- **Note:** This fix was absorbed into Task 2 commit

## Pre-existing Test Failures (Out of Scope)

- `tests/test_cache.py` — fails due to Python 3.9 local environment not supporting `str | None` syntax in Pydantic models. Backend runs Python 3.12 in Docker. Pre-existing across all phases.
- `tests/test_mdblist.py::test_parse_all_rating_sources` — asserts `imdb_rating == 9.3` but gets `93.0`. Pre-existing bug unrelated to this plan.

## Known Stubs

None — all endpoints are fully implemented. Migration 0017 is not yet applied (requires running `alembic upgrade head` in the Docker container, which is a deployment step, not a code stub).

## Self-Check

- [x] Migration file exists: `backend/alembic/versions/20260401_0017_global_saves.py`
- [x] GlobalSave model importable: `from app.models import GlobalSave`
- [x] `get_watched_movies`, `set_movie_rating`, `save_movie`, `unsave_movie` functions present
- [x] `WatchedMoviesResponse`, `WatchedMovieDTO`, `RatingUpdate` classes present
- [x] Route ordering: /watched before /{tmdb_id}
- [x] Task 1 commit: a6da7b4
- [x] Task 2 commit: a037100

## Self-Check: PASSED
