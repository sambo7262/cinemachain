---
phase: 13-mdblist-expansion
plan: "01"
subsystem: backend
tags: [mdblist, ratings, migration, parser, dto]
dependency_graph:
  requires: []
  provides: [mdblist-expanded-parser, movie-model-rating-columns, dto-rating-fields]
  affects: [game-eligible-movies, search-movies, mdblist-backfill]
tech_stack:
  added: []
  patterns: [sentinel-0-for-fetched-no-data, backward-compat-alias]
key_files:
  created:
    - backend/alembic/versions/20260401_0011_mdblist_expansion.py
    - backend/tests/test_mdblist.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/services/mdblist.py
    - backend/app/routers/game.py
    - backend/app/routers/search.py
decisions:
  - "sentinel-0 pattern extended to all new float/int rating fields; empty string used as imdb_id sentinel for 404s"
  - "backfill_rt_scores kept as module-level alias pointing to renamed backfill_mdblist_scores for backward compatibility"
  - "backfill trigger condition changed from rt_score IS NULL to (rt_score IS NULL OR imdb_rating IS NULL) to catch any missing field"
  - "rt_score refresh block in game.py extended to SELECT all 7 fields so a single DB round-trip refreshes everything post-MDBList fetch"
  - "rt_audience_score bug fixed in search.py: was returning raw value including 0-sentinel; now applies same sentinel-filter as game.py"
metrics:
  duration_minutes: 25
  tasks_completed: 2
  files_created: 2
  files_modified: 4
  completed_date: "2026-04-01"
---

# Phase 13 Plan 01: MDBList Expansion — Backend Data Layer Summary

Extended the MDBList parser to capture all rating sources from the existing API call and wired 5 new DB columns through both game.py and search.py DTOs, including a fix for the rt_audience_score field that existed in the DB but was never serialized.

## What Was Built

### Task 1: Wave 0 test stubs + DB migration + Movie model columns

**Migration 0011** (`backend/alembic/versions/20260401_0011_mdblist_expansion.py`):
- Adds 5 nullable columns to the `movies` table: `imdb_id` (String 20), `imdb_rating` (Float), `metacritic_score` (Integer), `letterboxd_score` (Float), `mdb_avg_score` (Float)
- Issues `UPDATE movies SET rt_score = NULL` to force full re-fetch so all new fields get populated in one backfill pass
- `down_revision = "0010"` (session_saves/shortlist migration)

**Movie model** (`backend/app/models/__init__.py`):
- 5 new `Mapped[Optional[...]]` columns added after `rt_audience_score`

**Test stubs** (`backend/tests/test_mdblist.py`):
- 4 tests with asyncpg-skip pattern, all currently skipped locally (run in Docker)
- `test_parse_all_rating_sources` — verifies all 6 score fields assigned from mock MDBList response
- `test_score_average_stored` — verifies `score_average` top-level field → `mdb_avg_score`
- `test_imdbid_stored` — verifies `imdbid` top-level field → `imdb_id`
- `test_backfill_status_schema` — verifies backfill status response shape (keys + types)

### Task 2: Extended parser + DTO wiring

**mdblist.py** (`backend/app/services/mdblist.py`):
- Module docstring updated from "Rotten Tomatoes scores" to "MDBList API client for fetching movie ratings"
- Both `fetch_rt_scores()` and `_fetch_and_store_rt()` now extract `metacritic`, `letterboxd`, `imdb` sources from the `ratings` array loop
- Both functions extract top-level `imdbid` and `score_average` fields
- All 7 fields stored with sentinel-0 pattern; 404 response sets `imdb_id = ""`
- Backfill query trigger changed from `rt_score IS NULL` to `(rt_score IS NULL OR imdb_rating IS NULL)`
- `backfill_rt_scores` renamed to `backfill_mdblist_scores`; old name kept as module-level alias for backward compat

**game.py** (`backend/app/routers/game.py`):
- Both `movies_map` construction blocks (actor-specific path ~1490 and combined path ~1569) extended with 6 new keys: `rt_audience_score`, `imdb_id`, `imdb_rating`, `metacritic_score`, `letterboxd_score`, `mdb_avg_score`
- RT score refresh block SELECT extended from `(tmdb_id, rt_score)` to all 8 columns; loop now updates all 7 rating fields in `movies_map`

**search.py** (`backend/app/routers/search.py`):
- `_movie_to_dto()` extended with `rt_audience_score` (bug fix — was missing) and all 5 new rating fields
- `rt_score` line corrected to apply the sentinel filter (was returning raw DB value including 0-sentinel)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed rt_score sentinel leak in search.py**
- **Found during:** Task 2
- **Issue:** The original `_movie_to_dto()` returned `"rt_score": movie.rt_score` — the raw value, meaning a 0-sentinel would be sent to the frontend as a score instead of null. game.py already had the `> 0` filter; search.py did not.
- **Fix:** Applied the same `movie.rt_score if movie.rt_score and movie.rt_score > 0 else None` pattern when adding the rt_score line during DTO extension.
- **Files modified:** `backend/app/routers/search.py`
- **Commit:** 5f7d8ed

## Known Stubs

None — all new fields are wired from DB to DTO. The test stubs in `test_mdblist.py` are intentional Wave 0 stubs (RED phase) that will be implemented in a future plan once the Docker test environment can run them.

## Self-Check: PASSED

Files created:
- /Users/Oreo/Projects/CinemaChain/backend/alembic/versions/20260401_0011_mdblist_expansion.py — FOUND
- /Users/Oreo/Projects/CinemaChain/backend/tests/test_mdblist.py — FOUND

Commits:
- 732e68d — Task 1: Wave 0 test stubs + DB migration + Movie model columns — FOUND
- 5f7d8ed — Task 2: Extend mdblist.py parser + wire new fields into DTOs — FOUND
