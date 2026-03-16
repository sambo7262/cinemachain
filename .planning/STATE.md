---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: "Completed 03-movie-game-03-26-PLAN.md — request_movie resets current_movie_watched=False, game loop state machine closed"
last_updated: "2026-03-15T00:10:00Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 36
  completed_plans: 36
---

# STATE.md — CinemaChain

## Project Reference

**What:** A Dockerized home media companion app on Synology NAS integrated with Plex, Radarr, and Sonarr. Surfaces filmography data via a chain-based actor discovery game and direct search. Selections are queued via Radarr/Sonarr.

**Core Value:** The Movie Game — navigate cinema through shared actors, making "what to watch next" effortless without ever repeating an actor.

**Current Milestone:** v1.0 CinemaChain

## Current Position

- **Phase:** Phase 3 — Movie Game (03-26 complete — game loop state machine closed; deploy + full verification required)
- **Plan:** Completed 03-26
- **Status:** Fix applied — request_movie now resets current_movie_watched=False; Docker rebuild and NAS deploy required to activate; full game loop end-to-end verification pending

## Progress

`[██████████] 100%` — 36 of 36 plans complete (03-26 fix applied; deploy + verify remaining)

| Phase | Status |
|-------|--------|
| 1. Infrastructure | Complete |
| 2. Data Foundation | Complete (02-01 through 02-05 done) |
| 3. Movie Game | In progress — 03-25 partial pass (Steps 2-5 verified; Step 6 fails); 03-26 fix + verify required before Phase 3 closes |
| 4. Query Mode | Not started |

## Recent Decisions

- **2026-03-15:** 03-26: request_movie resets current_movie_watched=False after updating current_movie_tmdb_id and before db.commit() — closes game loop state machine so Session Home Page condition (active + !current_movie_watched) is met for 2nd movie
- **2026-03-15:** 03-25: PARTIAL PASS — Steps 2-5 verified on live NAS; Step 6 (2nd movie) blocked by request_movie not resetting current_movie_watched=False; 03-26 required to close game loop
- **2026-03-15:** 03-25: request_movie root cause — endpoint advances current_movie_tmdb_id but leaves current_movie_watched=True (from first movie Mark as Watched); home page condition (active + !current_movie_watched) never met for 2nd movie; fix: add session.current_movie_watched = False in game.py request_movie after creating new step
- **2026-03-15:** 03-25: UI refinements deferred to a later iteration after core user journey is solidified — captured in deferred-items.md
- **2026-03-16:** 03-24: view: 'home' | 'tabs' enum state replaces showSessionHome boolean — Session Home Page is permanent default hub; Continue the chain button on home hub; Back button from Tab View; Tabs only render when view === 'tabs'
- **2026-03-16:** 03-24: NavBar queries getActiveSession independently with queryKey ['activeSession'] and polls every 10s — routes Sessions link to /game/{id} when session is active, '/' otherwise
- **2026-03-15:** 03-23: PARTIAL PASS — root state machine cycling defect confirmed fixed (continue-chain no longer reverts UI); UX gap remaining: session home page lacks Mark as Watched button, no Back button from tab view to home page, NavBar does not consistently land on session home page hub
- **2026-03-15:** 03-23: Two-view session UX architecture confirmed — Session Home Page (permanent hub: current+previous movie, Mark as Watched, Continue the chain) is architecturally distinct from Tab View (Eligible Actors/Movies with Back button); NavBar Sessions always routes to home page
- **2026-03-15:** 03-22: continueChain must be called instead of resumeSession in handleContinue — resumeSession resets current_movie_watched=False causing state machine cycling defect (users reverted to Mark as Watched state)
- **2026-03-15:** 03-22: Radarr status fallback reads session.radarr_status from first poll response via useEffect with useRef guard — resolves confirmed NAS location.state delivery failure
- **2026-03-15:** 03-22: queryClient.setQueryData used in handleContinue to synchronously inject continueChain response — avoids stale poll cycle before next 5s refetch
- **2026-03-15:** 03-21: continue-chain endpoint is distinct from resume_session — each state machine edge has its own endpoint with correct side-effect semantics (awaiting_continue->active preserves current_movie_watched=True, paused->active resets it)
- **2026-03-15:** 03-21: Plex webhook removed entirely — all watched events now manual via Mark as Watched; sync_on_startup also removed to eliminate Plex startup dependency
- **2026-03-15:** 03-20 partial pass: Radarr notification not surfacing from location.state; Eligible Actors tab completely empty (root cause unknown); state machine cycles back to Mark as Watched after Continue the chain; sorting ineffective; thumbnails too small
- **2026-03-15:** 03-20 new requirements: remove Plex webhook entirely (all watched events manual via Mark as Watched button); add session home page after movie confirmation showing current + previous movie in chain
- **2026-03-15:** 03-19: HTTP 423 Locked used as watched gate on eligible endpoints; background pre-fetch uses _bg_session_factory (async_sessionmaker(engine)) with errors swallowed; Radarr check fires synchronously at create_session; current_movie_watched reset to False in resume_session; mark_current_watched duplicates _maybe_advance_session logic inline to avoid circular import
- **2026-03-15:** 03-19: eligible-movies returns paginated envelope {items, total, page, page_size, has_more}; default page_size=20; plex.py _maybe_advance_session now also sets current_movie_watched=True
- **2026-03-15:** 03-18: GAME-01 session start guidance confirmed PASS in live NAS; GAME-03 combined-view times out — synchronous TMDB credits fetch for all cast members before returning results reliably exceeds NAS request timeout for large casts
- **2026-03-15:** 03-18: Flow redesign: eligible actors/movies must be gated behind watched state; Radarr check fires at session start for starting movie; manual Mark as Watched button needed in GameSession UI; async background credits pre-fetch on session creation; eligible movies pagination (first N actors immediately, more on demand)
- **2026-03-15:** 03-17: Combined-view branch now mirrors actor-scoped branch — added tmdb declaration and _ensure_actor_credits_in_db loop before filmography query in else branch; isStartingMovie derived from steps.length===1 && lastStep.actor_tmdb_id===null; radarrStatus captures requestResult.status for conditional user feedback; confirm dialog changed to neutral wording
- **2026-03-15:** 03-16: Phase 3 not closed — session state machine flow defect found in live testing; correct flow is: movie search → select movie (session created, movie_selected_unwatched, NO actor prompt) → user watches → user picks actor → user picks next movie → Radarr queried only if movie not already in Radarr; 03-17 required
- **2026-03-15:** 03-16: setQueryData end-session fix (03-14) confirmed working in live NAS — GAME-01 end-session sub-requirement passes; NavBar (03-15) confirmed on all pages
- **2026-03-15:** 03-15: isMovieSelected derived client-side from lastStep.actor_tmdb_id === null && steps.length > 1 — avoids new backend field for movie_selected_unwatched sub-state; NavBar added as sticky layout element above Routes in App.tsx
- **2026-03-15:** 03-14: setQueryData(['activeSession'], null) in endMutation.onSuccess guarantees synchronous banner clear — eliminates async refetchQueries timing race on NAS hardware; staleTime reduced to 0; eligibleMovies enabled on !!session (not activeTab) so combined view loads on mount
- **2026-03-15:** 03-13 checkpoint PARTIAL PASS — GAME-01 session lifecycle (end-session + start-new-session from lobby) still broken after 03-12 refetchQueries fix; root cause unknown; 03-14 must diagnose and fix before Phase 3 can close
- **2026-03-15:** GAME-03 confirmed FIXED: eligible-movies populates full TMDB filmography after actor selection; user confirmed 5+ movies appear
- **2026-03-15:** GAME-08 confirmed FIXED: Radarr request triggered and session advances on movie selection; Pause/resume toggle (03-12) confirmed working
- **2026-03-15:** 03-11: _ensure_actor_credits_in_db uses pg_insert on_conflict_do_nothing — idempotent upsert; TMDB errors swallowed so eligible-movies endpoint degrades gracefully to cached data
- **2026-03-15:** 03-11: Makefile rebuild target tags images as sambo7262/cinemachain-*:latest matching compose.yaml — Docker Compose picks up locally built images instead of Hub versions
- **2026-03-15:** resumeMutation added to GameSession header as sibling of pauseMutation — distinct from handleContinue which handles awaiting_continue UX path
- **2026-03-15:** refetchQueries used over invalidateQueries in GameLobby endMutation.onSuccess — forces immediate synchronous banner clear rather than lazy re-render on next query cycle
- **2026-03-15:** 03-10 checkpoint FAILED — eligible-movies endpoint must call TMDBClient.fetch_actor_credits on demand when credits are missing from DB; no on-demand fetch was implemented in 03-06
- **2026-03-15:** 03-10 checkpoint FAILED — Docker build cache likely serving Phase 1 placeholder frontend; force `--no-cache` rebuild required as part of remediation
- **2026-03-15:** 03-10 checkpoint FAILED — session query cache not invalidated after pause/resume mutations in GameSession; `onSuccess` must invalidate `["session", sid]` key
- **2026-03-15:** 03-10 checkpoint FAILED — session lifecycle in lobby broken; existing active session blocks new session start and end button is ineffective
- **2026-03-15:** Python-side sort on eligible-movies result list — DB sort would require complex joins; filmography result sizes bounded (<200 movies)
- **2026-03-15:** WatchEvent tmdb_id set fetched once per eligible-movies request — single SELECT, Python set for O(1) lookup; avoids N+1 EXISTS queries per movie
- **2026-03-15:** request-movie records GameSessionStep before Radarr call — ensures DB consistency even if Radarr is slow or fails
- **2026-03-15:** radarr_client accessed via request.app.state.radarr_client — matches tmdb_client pattern; wired in lifespan (plan 03-09)
- **2026-03-15:** window.confirm used for movie selection confirmation in GameSession — no modal component available; plan permits this pattern as acceptable approach
- **2026-03-15:** ChainHistory imports GameSessionStepDTO from api.ts (already exported) rather than redefining — avoids type duplication across components
- **2026-03-15:** Watched movies wrapped in opacity-50 div rather than adding prop to MovieCard — keeps MovieCard selectable logic unchanged; two-layer approach is clean
- **2026-03-15:** import-csv route registered before /{session_id} to prevent FastAPI matching "import-csv" string as integer path param (would return 422)
- **2026-03-15:** GameSession selectinload re-fetched after db.commit() — db.refresh() does not reload lazy="raise" relationships; separate select with options(selectinload) required
- **2026-03-15:** Client-side CSV parsing uses FileReader + basic string split — PapaParse not needed for simple three-column Movie Name/Actor Name/Order format
- **2026-03-15:** toast() in GameLobby implemented as alert() wrapper — sonner not installed; plan permitted this as acceptable fallback for lobby error cases
- **2026-03-15:** MovieCard is the shared display primitive for lobby search, watched history, and game eligible-movies — single component handles all movie display contexts
- **2026-03-15:** Vite scaffold created manually (not via npm create vite) — interactive CLI cancelled on non-empty directory; all config files written directly
- **2026-03-15:** shadcn/ui components written manually rather than via npx shadcn init — avoids interactive CLI in automated context; produces identical output
- **2026-03-15:** api.ts uses relative /api base URL — nginx proxies to backend:8000 at runtime; frontend never calls backend directly
- **2026-03-15:** SessionStatus stored as String(20) not PostgreSQL ENUM — avoids Alembic complexity with enum type migrations; Python enum used for application-level type safety only
- **2026-03-15:** GameSessionStep.actor_tmdb_id/actor_name nullable — first step (starting movie) has no actor transition; nullable fields support this without a special case row
- **2026-03-15:** RadarrClient uses X-Api-Key header auth and Python-side tmdbId filtering to handle Radarr bug #6086; HTTP 400 from add_movie treated as success sentinel
- **2026-03-15:** from __future__ import annotations required in radarr.py for Python 3.9 union type hint (dict | None) compatibility
- **2026-03-15:** httpx.Response in unit tests requires explicit request= and content= to support raise_for_status() without RuntimeError
- **2026-03-15:** pyarr not used — direct async httpx RadarrClient implemented matching TMDBClient pattern (pyarr is synchronous)
- **2026-03-15:** POST /webhooks/plex uses Form(...) not Body(...) — Plex sends multipart/form-data; JSON body parameter would be rejected by FastAPI
- **2026-03-15:** TMDBClient stored as app.state.tmdb_client in lifespan — single shared async instance with close() on shutdown to flush httpx connection pool
- **2026-03-15:** Plex startup sync wrapped in try/except in lifespan — Plex unreachable is non-fatal; app starts regardless (per CONTEXT.md decisions)
- **2026-03-15:** _extract_tmdb_id handles both new Guid list (tmdb://550) and legacy guid string (com.plexapp.agents.themoviedb://550?lang=en) GUID formats
- **2026-03-15:** fetch_person added to TMDBClient — /person/id/movie_credits doesn't return actor metadata; separate /person/id call required for actor name and profile_path; method added for testability over accessing _client directly
- **2026-03-15:** Movie stubs from actor filmography have genres=NULL — genre_ids integers from movie_credits endpoint resolved on-demand via GET /movies/{id}
- **2026-03-15:** lazy="raise" on all ORM relationships — async SQLAlchemy cannot lazy-load; callers must use explicit selectinload/joinedload
- **2026-03-15:** WatchEvent.movie_id nullable FK — Plex scrobble arrives before TMDB fetch; event stored immediately and linked to Movie later
- **2026-03-15:** Alembic migration hand-authored (not autogenerated) — no live DB at plan execution time; matches ORM schema exactly
- **2026-03-15:** DATA-05 webhook tests use multipart/form-data (`data=` param) not JSON — matches actual Plex payload format and FastAPI Form(...) requirement
- **2026-03-15:** DATA-03 cache verification uses fetched_at timestamp stability (black-box) not mock call counting — keeps tests decoupled from implementation
- **2026-03-15:** Idempotency tests for DATA-05 and DATA-06 explicitly exercise ON CONFLICT DO NOTHING semantics that Wave 2 must implement
- **2026-03-14:** PostgreSQL chosen over SQLite — game session join queries (eligibility filtering, actor exclusion) require the richer query support; SQLite recommendation from Stack research overridden
- **2026-03-14:** Plex webhook (DATA-05) included in Phase 2 as a v1 requirement; DATA-06 (manual mark) is the fallback if webhook proves unreliable
- **2026-03-14:** Phase 4 (Query Mode) depends only on Phase 2 (data layer), not Phase 3 (game); shared services, no session state dependency
- **2026-03-14:** No separate frontend phase — backend and UI for each mode delivered together so each phase boundary produces something verifiable

## Pending Todos

- Resolve RT ratings source before Phase 3 planning (options: TMDB vote_average as proxy, OMDb `tomatoes=true`, or scraping — OMDb is cleanest path)
- Verify pyarr v5.2.0 compatibility with installed Radarr/Sonarr versions before Phase 3 planning; fall back to direct httpx if needed
- Confirm Plex Pass availability before Phase 2 — DATA-05 (webhook) requires Plex Pass; DATA-06 (manual mark) covers non-Plex-Pass setups

## Blockers / Concerns

- **[RESOLVED — 03-26] request_movie does not reset current_movie_watched=False:**
  - Fix applied in d6003d9 — session.current_movie_watched = False added at line 798 in request_movie endpoint
  - Docker rebuild and NAS deploy required to activate fix; full game loop end-to-end verification pending
- **[RESOLVED — 03-25] 03-24 frontend changes not yet deployed to NAS:**
  - Docker rebuild completed; NAS updated; Steps 2-5 verified passing
- **[RESOLVED — 03-23] Root state machine cycling defect:** continue-chain endpoint confirmed working; Eligible Actors populates after Continue the chain; no reversion to Mark as Watched
- **[RESOLVED — 03-23] Plex webhook:** returns 404 as expected
- **[RESOLVED — 03-23] Thumbnail size:** visibly larger in Eligible Movies tab
- **[RESOLVED] 03-10 defects 1, 3, 4 fixed by 03-11/03-12:**
  1. Routing: FIXED — Docker `--no-cache` rebuild resolved Phase 1 placeholder at `/`
  3. Eligible movies: FIXED — `_ensure_actor_credits_in_db` fetches filmography on demand; user confirmed 5+ movies populate
  4. Pause button: FIXED — pause/resume toggle working correctly in live app
- **[CONFIRMED IN 03-16] GAME-01 end-session:** setQueryData(null) fix confirmed working — banner clears immediately in live NAS test
- **[BACKEND DONE — FRONTEND + DEPLOY REQUIRED] GAME-03 combined-view timeout + flow redesign:** Backend complete: watched gate (HTTP 423), mark-current-watched, Radarr-on-start, background pre-fetch, pagination. Frontend needs: Mark as Watched button, gate locked state UI. Docker rebuild + migration 0003 deploy required before NAS verification.
- RT ratings source unresolved (no public API — TMDB proxy vs OMDb vs scraping TBD before Phase 3 UI)
- pyarr currency risk: last release July 2023; verify against installed Radarr/Sonarr API version before writing integration code
- Plex webhook reliability: `media.scrobble` has confirmed delivery bugs; polling fallback must be implemented alongside webhook in Phase 2
- Synology PUID/PGID: must match a NAS user; PostgreSQL must not bind to port 5432 (reserved on Synology — use 5433)

## Accumulated Context

### Critical Pitfalls (from research)

1. Plex webhooks are `multipart/form-data`, not JSON — install `python-multipart`; use `Form(...)` in FastAPI
2. TMDB rate limiting on cold cache — use `asyncio.Semaphore`; eager pre-cache when movies are added
3. `media.scrobble` fires at 90% and has reliability bugs — must implement polling fallback
4. Game session state must be persisted to PostgreSQL from day one — NAS containers restart frequently
5. Radarr/Sonarr return 400 on duplicate — treat as success, not error
6. Synology PUID/PGID permission failures — explicit PUID/PGID required; PostgreSQL port 5433 not 5432
7. No memory limits causes OOM kills — set `mem_limit` on every container; use `restart: unless-stopped`
8. Sonarr season numbering (TVDB vs Scene) — always use Sonarr-internal series/season IDs

### Stack Decisions

- Python 3.12 + FastAPI 0.115.x + Uvicorn
- PostgreSQL 16-alpine (not SQLite)
- PlexAPI 4.18.0, tmdbv3api 1.9.0, pyarr 5.2.0 (or httpx fallback)
- Tailscale sidecar with `TS_USERSPACE=true` (mandatory on Synology DSM)

## Session Continuity

Last session: 2026-03-15T00:10:00Z
Stopped at: Completed 03-26-PLAN.md — request_movie resets current_movie_watched=False, game loop state machine closed
Resume with: Rebuild Docker images (make rebuild), push to registry, deploy to NAS, verify full game loop end-to-end (GAME-04 actor dedup, GAME-05 session continuation).
