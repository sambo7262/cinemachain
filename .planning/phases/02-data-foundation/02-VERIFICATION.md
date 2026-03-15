---
phase: 02-data-foundation
verified: 2026-03-15T00:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 2: Data Foundation Verification Report

**Phase Goal:** The application can fetch filmography data from TMDB, cache it in PostgreSQL, and know which movies the user has watched — either via Plex sync or manual marking.
**Verified:** 2026-03-15
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GET /movies/{tmdb_id} fetches from TMDB on first call and returns title, poster_path, vote_average, year, genres, watched, fetched_at | VERIFIED | `movies.py` lines 15-84: cache miss triggers `tmdb_client.fetch_movie()`, full response dict returned |
| 2  | GET /movies/{tmdb_id} returns same fetched_at on repeat calls (cache hit) | VERIFIED | `movies.py` lines 19-22: DB select checked first; on hit, TMDB is never called; `fetched_at` not updated |
| 3  | GET /actors/{tmdb_id}/filmography returns actor name, profile_path, and list of movie credits with watched state | VERIFIED | `actors.py` lines 15-115: fetches via `fetch_actor_credits` + `fetch_person`, builds credits list with per-movie watched bool |
| 4  | POST /webhooks/plex with media.scrobble multipart payload creates a watch_events row with source='plex_webhook' | VERIFIED | `plex.py` lines 44-82: `Form(...)` used, scrobble check, `pg_insert(WatchEvent).on_conflict_do_nothing()` with `source="plex_webhook"` |
| 5  | On startup, Plex library is synced and watch_events rows written for watched movies | VERIFIED | `services/plex.py` lines 66-81: `sync_on_startup` calls `run_in_executor` wrapping sync `_sync_plex_watched`, upserts with `source="plex_sync"` |
| 6  | PATCH /movies/{tmdb_id}/watched creates a watch_events row with source='manual' and returns watched=true | VERIFIED | `movies.py` lines 87-98: `pg_insert(WatchEvent)` with `source="manual"`, returns `{"watched": True, "source": "manual"}` |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_tmdb.py` | DATA-01, DATA-02, DATA-03 stub tests | VERIFIED | 51 lines; 3 named test functions; imports only pytest; no skip guards needed (tests delegate to `client` fixture) |
| `backend/tests/test_plex_sync.py` | DATA-04 stub test | VERIFIED | 23 lines; `test_startup_sync_marks_watched` present |
| `backend/tests/test_plex_webhook.py` | DATA-05 stub tests | VERIFIED | 77 lines; 3 test functions covering scrobble, idempotency, ignored events |
| `backend/tests/test_movies.py` | DATA-06 stub tests | VERIFIED | 32 lines; `test_manual_mark_watched` + `test_manual_mark_watched_is_idempotent` |
| `backend/app/models/__init__.py` | Movie, Actor, Credit, WatchEvent ORM models | VERIFIED | All 4 models present; `lazy="raise"` on all 6 relationships; `UniqueConstraint("tmdb_id")` on WatchEvent; `UniqueConstraint("movie_id", "actor_id")` on Credit |
| `backend/alembic/versions/20260315_0001_initial_data_schema.py` | Initial migration creating all 4 tables | VERIFIED | `down_revision=None`; `op.create_table` for movies, actors, credits, watch_events; full downgrade; FK deps in correct order |
| `backend/requirements.txt` | plexapi dependency added | VERIFIED | Line 12: `plexapi==4.18.0` present |
| `backend/app/services/tmdb.py` | TMDBClient with fetch_movie, fetch_actor_credits, fetch_person, close | VERIFIED | All 4 methods present; `asyncio.Semaphore(10)` on `self._sem`; semaphore guards all HTTP calls |
| `backend/app/services/plex.py` | PlexSyncService with correct sync/async split | VERIFIED | `_sync_plex_watched` is synchronous; `sync_on_startup` and `_upsert_watch_events` are coroutines; `run_in_executor` used; non-fatal error handling |
| `backend/app/routers/movies.py` | GET /movies/{tmdb_id} + PATCH /movies/{tmdb_id}/watched | VERIFIED | Both endpoints present; cache check before TMDB call; `selectinload` not needed here (no relationship traversal in GET); PATCH uses `on_conflict_do_nothing` |
| `backend/app/routers/actors.py` | GET /actors/{tmdb_id}/filmography | VERIFIED | Endpoint present; `selectinload(Actor.credits).selectinload(Credit.movie)` on final query |
| `backend/app/routers/plex.py` | POST /webhooks/plex | VERIFIED | `Form(...)` used (not Body); both new and legacy GUID formats handled; non-movie types silently ignored |
| `backend/app/main.py` | Updated lifespan + all routers registered | VERIFIED | TMDBClient instantiated and stored as `app.state.tmdb_client`; `sync_on_startup` called; 4 routers registered via `include_router` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/alembic/env.py` | `backend/app/models/__init__.py` | `from app.models import Base` | VERIFIED | Line 7 of env.py imports Base; `target_metadata = Base.metadata` on line 14 |
| `backend/app/routers/movies.py` | `backend/app/services/tmdb.py` | `request.app.state.tmdb_client` | VERIFIED | Line 26 in movies.py; same pattern in actors.py line 24 |
| `backend/app/services/tmdb.py` | `https://api.themoviedb.org/3` | `httpx.AsyncClient` with base_url | VERIFIED | `httpx.AsyncClient(base_url=self.BASE_URL, ...)` in `__init__` |
| `backend/app/routers/movies.py` | `backend/app/models/__init__.py` | `select(Movie).where(Movie.tmdb_id` | VERIFIED | Line 20 of movies.py |
| `backend/app/routers/plex.py` | `backend/app/models/__init__.py` | `pg_insert(WatchEvent).on_conflict_do_nothing()` | VERIFIED | Lines 72-78 of plex.py |
| `backend/app/main.py` | `backend/app/services/tmdb.py` | `TMDBClient` instantiated in lifespan | VERIFIED | Lines 12, 27-28 of main.py |
| `backend/app/main.py` | `backend/app/services/plex.py` | `sync_on_startup` called in lifespan | VERIFIED | Lines 13, 32 of main.py |
| `backend/app/services/plex.py` | `plexapi.server.PlexServer` | `run_in_executor` wrapping sync call | VERIFIED | Line 75 of services/plex.py: `loop.run_in_executor(None, _sync_plex_watched, ...)` |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| DATA-01 | 02-01, 02-02, 02-03 | System fetches movie metadata from TMDB API | SATISFIED | `GET /movies/{id}` hits TMDB on cache miss; returns title, poster_path, vote_average, year, genres |
| DATA-02 | 02-01, 02-02, 02-03 | System fetches actor metadata and filmography credits from TMDB | SATISFIED | `GET /actors/{id}/filmography` hits TMDB for credits + person metadata on cache miss |
| DATA-03 | 02-01, 02-02, 02-03 | System caches TMDB data in PostgreSQL | SATISFIED | DB select before TMDB call; `fetched_at` not updated on cache hit; `test_movie_cached_on_repeat_request` verifies stable `fetched_at` |
| DATA-04 | 02-01, 02-04 | System cross-references Plex library for watched state | SATISFIED | `sync_on_startup` → `run_in_executor(_sync_plex_watched)` → `_upsert_watch_events(source="plex_sync")` |
| DATA-05 | 02-01, 02-05 | System receives Plex webhook events to update watch state | SATISFIED | `POST /webhooks/plex` with `Form(...)`, scrobble handling, `source="plex_webhook"`, idempotent upsert |
| DATA-06 | 02-01, 02-05 | User can manually mark a movie as watched | SATISFIED | `PATCH /movies/{id}/watched` with `source="manual"`, idempotent upsert, returns `watched=true` |

**REQUIREMENTS.md status check:** DATA-01, DATA-02, DATA-03 are marked `[ ]` (pending) in REQUIREMENTS.md while DATA-04, DATA-05, DATA-06 are marked `[x]` (complete). This is an inconsistency between REQUIREMENTS.md tracking state and the actual implementation — all six are implemented. This is a documentation tracking issue, not a code gap.

---

### Anti-Patterns Found

No blockers or stubs found in implementation files. Scan results:

- No TODO/FIXME/PLACEHOLDER comments in any implementation file
- No empty return values (`return null`, `return {}`, `return []`) in any handler
- No console.log-only handlers
- No `return {"message": "Not implemented"}` placeholders

One minor note: `actors.py` imports `selectinload` from `sqlalchemy.orm` but does not use it in the movies router — this is correct because `movies.py` does not traverse relationships. The import is appropriate only in `actors.py`.

---

### Human Verification Required

The following behaviors cannot be verified by static analysis and require a live environment:

**1. TMDB Cache Hit Correctness**
- **Test:** Start the app with a real DATABASE_URL. Call `GET /movies/550` twice. Compare `fetched_at` values in both responses.
- **Expected:** `fetched_at` values are identical on both calls.
- **Why human:** Requires a live PostgreSQL instance and real TMDB credentials.

**2. Plex Startup Sync End-to-End**
- **Test:** Start the app with valid `PLEX_URL` and `PLEX_TOKEN`. Check logs for "Plex startup sync complete: N watched movies synced". Call `GET /movies/{id}` for a movie known to be watched in Plex.
- **Expected:** `watched=true` in the response.
- **Why human:** Requires live Plex server and PostgreSQL.

**3. Plex Startup Non-Fatal Behavior**
- **Test:** Start the app with an invalid `PLEX_URL`. Verify the app starts successfully (does not crash) and logs a warning.
- **Expected:** App starts; logs contain "Plex startup sync failed (non-fatal)"; health endpoint responds 200.
- **Why human:** Requires app startup observation.

**4. Webhook Multipart Format**
- **Test:** POST to `/webhooks/plex` using actual `multipart/form-data` encoding (e.g. curl with `-F payload=...`).
- **Expected:** 200 response with `{"status": "ok"}`.
- **Why human:** `AsyncClient` in tests accepts `data={}` which httpx sends as form-encoded; real Plex uses multipart boundary — worth verifying with an actual Plex webhook replay.

**5. Test Suite Runs Green**
- **Test:** `cd backend && pytest tests/test_tmdb.py tests/test_plex_webhook.py tests/test_movies.py tests/test_plex_sync.py -x -q` against a live Docker compose stack.
- **Expected:** All tests pass, exit 0.
- **Why human:** Requires live database (tests use `client` fixture that triggers lifespan with real DB connection).

---

## Summary

All six DATA requirements are implemented with substantive, wired code — no stubs or placeholders. The implementation satisfies the phase goal:

- **TMDB pipeline:** `TMDBClient` fetches and caches movie/actor data; `GET /movies/{id}` and `GET /actors/{id}/filmography` implement the lazy-fetch-and-cache pattern correctly using `fetched_at` as the cache signal.
- **PostgreSQL schema:** Four ORM models registered with `lazy="raise"`, Alembic migration with all tables, FK constraints, and unique constraints matches the spec exactly.
- **Plex sync:** `sync_on_startup` correctly wraps the synchronous `PlexServer` call in `run_in_executor`; non-fatal on Plex unavailability; idempotent via `ON CONFLICT DO NOTHING`.
- **Plex webhook:** `POST /webhooks/plex` correctly uses `Form(...)`, handles both new and legacy GUID formats, ignores non-scrobble events.
- **Manual mark watched:** `PATCH /movies/{id}/watched` is idempotent and returns the expected shape.
- **Wiring:** `main.py` lifespan correctly initializes `TMDBClient` into `app.state`, calls Plex sync, and registers all four routers.

The only outstanding item is that REQUIREMENTS.md shows DATA-01/02/03 as `[ ]` pending — this is a tracking document inconsistency, not a code gap.

---

_Verified: 2026-03-15_
_Verifier: Claude (gsd-verifier)_
