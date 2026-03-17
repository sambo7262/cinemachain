# ROADMAP — CinemaChain v1.0

**Milestone:** v1.0 CinemaChain
**Created:** 2026-03-14
**Granularity:** Standard
**Coverage:** 25/25 requirements mapped

---

## Phases

- [ ] **Phase 1: Infrastructure** — Docker Compose stack with PostgreSQL, backend skeleton, and Tailscale sidecar running on Synology NAS
- [x] **Phase 2: Data Foundation** — TMDB filmography cache, Plex watch history sync, and manual watch marking operational (completed 2026-03-15)
- [x] **Phase 3: Movie Game** — Complete actor-chain game loop with session state, eligibility panels, and Radarr request submission (completed 2026-03-15 — full 6-step game loop PASS on live NAS; GAME-04 resolved)
- [ ] **Phase 03.1: UI Improvements and Multi-Session Support** — Multi-session support, session naming, archive/unarchive, home page session grid, chain history table, TMDB ID fix, CSV export/import validation
- [~] **Phase 03.2: Game UX Enhancements** — Movie filters (genre, runtime, MPAA rating, TMDB rating with vote floor), movie name search within eligible movies, ineligible actor toggle, chain history moved to bottom, actor/movie thumbnails in chain, session watched-count and runtime counter (gaps 1,2,4,5 closed; gap 3 redefined — all eligible movies on tab open without actor; 2 regressions open; plans 10-12 created)
- [ ] **Phase 4: Query Mode** — Actor, title, and genre search with Radarr and Sonarr request submission from search results

---

## Phase Details

### Phase 1: Infrastructure
**Goal:** The application stack runs on the Synology NAS with all containers healthy, data persisted across restarts, and the UI reachable over Tailscale.
**Depends on:** Nothing
**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up -d` starts backend, PostgreSQL, and frontend containers with no errors
  2. PostgreSQL data survives a container restart (volumes correctly bind-mounted)
  3. All API keys and service URLs are loaded from .env with no credentials baked into images
  4. The application UI is reachable at the Tailscale IP or hostname from another device on the network
**Plans:** 1/4 plans executed

Plans:
- [ ] 01-01-PLAN.md — Wave 0: pytest config and test stubs for INFRA-01, INFRA-02, INFRA-03
- [ ] 01-02-PLAN.md — Wave 1: Docker Compose stack config, .env.example, .gitignore, frontend placeholder
- [ ] 01-03-PLAN.md — Wave 1: FastAPI backend skeleton, settings, DB, health endpoint, Alembic
- [ ] 01-04-PLAN.md — Wave 2: Tailscale Serve config, cold-boot verification, Tailscale checkpoint

### Phase 2: Data Foundation
**Goal:** The application can fetch filmography data from TMDB, cache it in PostgreSQL, and know which movies the user has watched — either via Plex sync or manual marking.
**Depends on:** Phase 1
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. Fetching a movie returns poster, rating, year, and genre data sourced from TMDB
  2. A second request for the same movie or actor is served from the PostgreSQL cache without hitting the TMDB API
  3. Movies the user has watched in Plex are reflected as watched in the app after a Plex library sync
  4. A Plex playback completion event (webhook) automatically marks the corresponding movie as watched
  5. User can manually mark a movie as watched through the UI (fallback for non-Plex-Pass setups)
**Plans:** 5/5 plans complete

Plans:
- [x] 02-01-PLAN.md — Wave 0: test stubs for DATA-01 through DATA-06
- [ ] 02-02-PLAN.md — Wave 1: ORM models (Movie, Actor, Credit, WatchEvent) + Alembic migration
- [ ] 02-03-PLAN.md — Wave 2: TMDBClient service + GET /movies/{id} + GET /actors/{id}/filmography
- [ ] 02-04-PLAN.md — Wave 2: PlexSyncService + startup library sync
- [ ] 02-05-PLAN.md — Wave 3: POST /webhooks/plex + PATCH /movies/{id}/watched + main.py wiring

### Phase 3: Movie Game
**Goal:** A user can start a Movie Game session, navigate an actor-chain across movies without repeating actors, and queue a chosen movie via Radarr — with session state fully persisted to the database.
**Depends on:** Phase 2
**Requirements:** GAME-01, GAME-02, GAME-03, GAME-04, GAME-05, GAME-06, GAME-07, GAME-08
**Success Criteria** (what must be TRUE):
  1. User can start a game session by selecting any movie as the starting point
  2. The Eligible Actors panel shows only cast members of the current movie who have not been picked in this session
  3. Selecting an actor reveals an Eligible Movies panel showing only that actor's unwatched filmography
  4. An actor selected in this session cannot appear again in the Eligible Actors panel for the remainder of that session
  5. User can sort Eligible Movies by genre, TMDB rating, or aggregated rating; toggle between unwatched-only and all movies (with watched badges); only unwatched movies are selectable
  6. Selecting an unwatched movie triggers a Radarr download request and advances the session to that movie
**Plans:** 29/29 plans complete

Plans:
- [ ] 03-01-PLAN.md — Wave 0: test stubs for GAME-01 through GAME-08 (test_game.py + test_radarr.py)
- [ ] 03-02-PLAN.md — Wave 1: ORM models (GameSession, GameSessionStep, runtime on Movie) + Alembic migration 0002
- [ ] 03-03-PLAN.md — Wave 1: RadarrClient service (mirrors TMDBClient pattern)
- [ ] 03-04-PLAN.md — Wave 1: Frontend scaffold (Vite + React + Tailwind v3 + shadcn/ui)
- [ ] 03-05-PLAN.md — Wave 2: Game session lifecycle API (create, active, pause/resume/end, import-csv) + movies search/watched endpoints
- [ ] 03-06-PLAN.md — Wave 2: Game interaction API (eligible-actors, eligible-movies, pick-actor, request-movie)
- [x] 03-07-PLAN.md — Wave 2: GameLobby page (three start modes: watched history, title search, CSV import)
- [ ] 03-08-PLAN.md — Wave 3: GameSession page (two-tab UI, sort/filter, ChainHistory, session advance)
- [ ] 03-09-PLAN.md — Wave 4: Backend wiring (RadarrClient lifespan, game router mount, Plex advancement hook) + Frontend Docker
- [~] 03-10-PLAN.md — Wave 5: Human verify checkpoint FAILED (4 defects; see 03-10-SUMMARY.md)
- [x] 03-11-PLAN.md — Wave 6 (gap-closure): eligible-movies on-demand TMDB fetch + Makefile rebuild target
- [x] 03-12-PLAN.md — Wave 6 (gap-closure): GameSession pause/resume toggle + GameLobby end-session refetch
- [~] 03-13-PLAN.md — Wave 7 (gap-closure): Re-verification PARTIAL PASS — GAME-03/08/pause FIXED; GAME-01 session lifecycle still broken
- [ ] 03-14-PLAN.md — Wave 8 (gap-closure): Fix end-session synchronous cache clear + Eligible Movies combined view on mount
- [ ] 03-15-PLAN.md — Wave 8 (gap-closure): Global NavBar + session state machine UI (7 states) + compact table layout
- [~] 03-16-PLAN.md — Wave 9 (gap-closure): Final re-verification PARTIAL PASS — End Session + NavBar confirmed; session state machine flow defect found; 03-17 required
- [ ] 03-17-PLAN.md — Wave 10 (gap-closure): Fix isStartingMovie state machine + combined-view _ensure_actor_credits_in_db + Radarr conditional notification
- [~] 03-18-PLAN.md — Wave 11 (gap-closure): Docker rebuild + human verify — PARTIAL PASS: Test 1 (GAME-01) pass; Test 2 (GAME-03) fail (combined-view timeout); Tests 3-5 blocked; 03-19 required
- [ ] 03-19-PLAN.md — Wave 12 (gap-closure): Backend — current_movie_watched column, watched gate on eligible endpoints, mark-current-watched endpoint, Radarr on session start, async credits pre-fetch, eligible movies pagination
- [~] 03-20-PLAN.md — Wave 13 (gap-closure): Frontend — watched gate UI, Mark as Watched button, Radarr start notification, pagination controls; Docker rebuild + final verify PARTIAL PASS: pagination + Mark as Watched pass; Radarr notification missing, Eligible Actors empty, state machine reversion, sorting broken — 03-21 required
- [ ] 03-21-PLAN.md — Wave 14 (gap-closure): Backend — continue-chain endpoint (awaiting_continue -> active without resetting current_movie_watched); Plex webhook removal (plex.py deleted, main.py updated)
- [ ] 03-22-PLAN.md — Wave 14 (gap-closure): Frontend — handleContinue fix (calls continueChain), Radarr polling fallback, session home page (NEW-02), thumbnail size fix
- [~] 03-23-PLAN.md — Wave 15 (gap-closure): Docker rebuild + NAS deploy + PARTIAL PASS — root state machine defect fixed; session home page UX gaps (Mark as Watched button, Back button, NavBar routing) require 03-24
- [ ] 03-24-PLAN.md — Wave 16 (gap-closure): Frontend — view state refactor (home|tabs), Session Home Page as default hub, Back button in Tab View, NavBar active session routing
- [~] 03-25-PLAN.md — Wave 17 (gap-closure): Docker rebuild + NAS deploy + PARTIAL PASS — Steps 2-5 verified (session home page, NavBar, Mark as Watched, Continue/Back); Step 6 fails (request_movie does not reset current_movie_watched=False); 03-26 required
- [ ] 03-26-PLAN.md — Wave 18 (gap-closure): Backend fix — set current_movie_watched=False in request_movie after advancing current_movie_tmdb_id
- [~] 03-27-PLAN.md — Wave 19 (gap-closure): Docker rebuild + NAS deploy + PARTIAL PASS — Steps 1-5 verified; Step 6 blocked by GAME-04 eligible-actors intersection bug; 03-28 required
- [ ] 03-28-PLAN.md — Wave 20 (gap-closure): Backend fix — BackgroundTasks pre-fetch in request_movie + on-demand fallback in get_eligible_actors
- [x] 03-29-PLAN.md — Wave 21 (gap-closure): Docker rebuild + NAS deploy + full game loop verification (Step 6 GAME-04 close-out)

### Phase 03.1: UI improvements and multi-session support (INSERTED)

**Goal:** Multiple game sessions can run concurrently, each identified by a unique name, with full session management (archive, browse archived), a readable chain history table, TMDB ID display bugs eliminated, and CSV export/import working reliably.
**Depends on:** Phase 3
**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08
**Plans:** 8/9 plans executed

Plans:
- [ ] 03.1-01-PLAN.md — Wave 1: Test stubs for UI-01 through UI-08 (test_game.py additions)
- [ ] 03.1-02-PLAN.md — Wave 2: Backend — Alembic migration 0004, ORM updates, multi-session gate removal, session naming, archive endpoint, list/archived endpoints, export-csv, watched_at enrichment
- [ ] 03.1-03-PLAN.md — Wave 3: Frontend data layer — api.ts DTO expansion, new API functions (listSessions, listArchivedSessions, archiveSession, exportCsv)
- [ ] 03.1-04-PLAN.md — Wave 4: GameLobby rewrite — session grid, name-required creation form, CSV import validation UI
- [ ] 03.1-05-PLAN.md — Wave 4: GameSession + ChainHistory — vertical chain table, TMDB ID fix, CSV export button
- [ ] 03.1-06-PLAN.md — Wave 5: ArchivedSessions page + NavBar update + App.tsx route
- [ ] 03.1-07-PLAN.md — Wave 6: Docker rebuild + NAS deploy + migration 0004 + human verify checkpoint
- [ ] 03.1-08-PLAN.md — Wave 5 (gap-closure): Backend — GET /sessions/{id} endpoint, current_movie_title in response, _enrich_steps_watched_at GROUP BY dedup
- [ ] 03.1-09-PLAN.md — Wave 6 (gap-closure): Frontend — GameSession fetch-by-ID, remove pause/resume/end buttons, movie badge on session cards, standalone Import Chain card

### Phase 03.2: Game UX Enhancements (INSERTED)
**Goal:** Make movie selection faster and more informed during active gameplay, and surface richer session context. Adds filters, search, and richer display to the game loop without changing game rules.
**Depends on:** Phase 03.1
**Requirements:** UX-01, UX-02, UX-03, UX-04, UX-05
**Success Criteria** (what must be TRUE):
  1. User can filter eligible movies by genre, runtime, MPAA rating, and TMDB rating (with vote-count floor)
  2. User can search eligible movies by title after picking an actor
  3. Ineligible actors are always visible below eligible actors (no toggle)
  4. Chain history is displayed at the bottom of the session page with actor and movie thumbnails
  5. Session page shows a counter for movies watched and total runtime of watched movies
**Plans:** 11/14 plans executed

Plans:
- [ ] 03.2-01-PLAN.md — Wave 0: Test stubs (RED phase) for 5 new backend behaviors
- [ ] 03.2-02-PLAN.md — Wave 1: Alembic migration 0005 + Movie ORM model (vote_count, mpaa_rating columns)
- [ ] 03.2-03-PLAN.md — Wave 2: Backend endpoint changes — eligible-actors include_ineligible, eligible-movies vote_count/mpaa + vote floor sort, session counters, step thumbnails
- [ ] 03.2-04-PLAN.md — Wave 1: Frontend shadcn UI primitives — Slider, Checkbox, Collapsible components
- [ ] 03.2-05-PLAN.md — Wave 3: Frontend feature work — api.ts DTOs, MovieFilterSidebar, SessionCounters, GameSession.tsx integration, ChainHistory.tsx thumbnails
- [~] 03.2-06-PLAN.md — Wave 4: Docker rebuild + NAS deploy + migration 0005 + human verify checkpoint (5 gaps identified)
- [ ] 03.2-07-PLAN.md — Wave 1 (gap-closure): Backend — _ensure_movie_details_in_db to fetch genres + runtime from TMDB for movie stubs
- [ ] 03.2-08-PLAN.md — Wave 1 (gap-closure): Frontend — ChainHistory to bottom, always-visible ineligible actors, movies tab empty state
- [~] 03.2-09-PLAN.md — Wave 2 (gap-closure): Docker rebuild + NAS deploy + verify; gaps 1,2,4,5 CLOSED; gap 3 redefined; 2 regressions found (actor eligibility after _ensure_movie_details_in_db; stale movie list on actor change)
- [ ] 03.2-10-PLAN.md — Wave 1 (gap-closure round 2): Backend — Regression 1 fix: fresh SELECT in get_eligible_actors on-demand fallback
- [ ] 03.2-11-PLAN.md — Wave 1 (gap-closure round 2): Gap 3 + Regression 2: frontend no-actor eligible movies fetch + queryKey null-stabilization + loading spinner
- [ ] 03.2-12-PLAN.md — Wave 2 (gap-closure round 2): Docker rebuild + NAS deploy + human verify all 3 issues

### Phase 4: Query Mode
**Goal:** A user can search for any actor, movie, or TV show by name or genre, browse results with sort and filter controls, and queue a selection via Radarr or Sonarr.
**Depends on:** Phase 2
**Requirements:** QUERY-01, QUERY-02, QUERY-03, QUERY-04, QUERY-05, QUERY-06, QUERY-07
**Success Criteria** (what must be TRUE):
  1. Searching by actor name returns that actor's full filmography from TMDB
  2. Searching by movie or TV show title returns a matching result the user can inspect and request
  3. Browsing by genre or keyword returns a list of relevant results
  4. Results can be sorted by genre, rating, or year; user can toggle to hide already-watched items
  5. Selecting a movie from search results triggers a Radarr request
  6. Selecting a TV show from search results triggers a Sonarr request
**Plans:** TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 1/4 | In Progress|  |
| 2. Data Foundation | 5/5 | Complete    | 2026-03-15 |
| 3. Movie Game | 29/29 | Complete   | 2026-03-16 |
| 03.1. UI + Multi-Session | 8/9 | In Progress|  |
| 03.2. Game UX Enhancements | 11/14 | In Progress|  |
| 4. Query Mode | 0/? | Not started | — |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| INFRA-01 | Phase 1 |
| INFRA-02 | Phase 1 |
| INFRA-03 | Phase 1 |
| INFRA-04 | Phase 1 |
| DATA-01 | Phase 2 |
| DATA-02 | Phase 2 |
| DATA-03 | Phase 2 |
| DATA-04 | Phase 2 |
| DATA-05 | Phase 2 |
| DATA-06 | Phase 2 |
| GAME-01 | Phase 3 |
| GAME-02 | Phase 3 |
| GAME-03 | Phase 3 |
| GAME-04 | Phase 3 |
| GAME-05 | Phase 3 |
| GAME-06 | Phase 3 |
| GAME-07 | Phase 3 |
| GAME-08 | Phase 3 |
| UI-01 | Phase 03.1 |
| UI-02 | Phase 03.1 |
| UI-03 | Phase 03.1 |
| UI-04 | Phase 03.1 |
| UI-05 | Phase 03.1 |
| UI-06 | Phase 03.1 |
| UI-07 | Phase 03.1 |
| UI-08 | Phase 03.1 |
| UX-01 | Phase 03.2 |
| UX-02 | Phase 03.2 |
| UX-03 | Phase 03.2 |
| UX-04 | Phase 03.2 |
| UX-05 | Phase 03.2 |
| QUERY-01 | Phase 4 |
| QUERY-02 | Phase 4 |
| QUERY-03 | Phase 4 |
| QUERY-04 | Phase 4 |
| QUERY-05 | Phase 4 |
| QUERY-06 | Phase 4 |
| QUERY-07 | Phase 4 |

**Total mapped:** 25/25 v1 + 8 Phase 03.1 UI requirements + 5 Phase 03.2 UX requirements

---

## Key Decisions Captured

| Decision | Rationale |
|----------|-----------|
| Phase 4 depends on Phase 2, not Phase 3 | Query mode shares the data layer but is independent of game session state; can be planned in parallel after Phase 2 |
| Plex webhook (DATA-05) in Phase 2, not deferred | It is a v1 requirement; manual mark (DATA-06) is the fallback if webhook proves unreliable during development |
| No separate frontend phase | Backend and UI for each mode are delivered together; splitting them leaves nothing verifiable at phase boundaries |
| No polish phase | v1 has no explicit polish requirements; hardening tasks belong in individual phase plans as acceptance conditions |
| RadarrClient uses httpx directly (not pyarr) | pyarr is synchronous (blocks event loop); last release July 2023; httpx matches existing TMDBClient pattern |
| Tailwind v3 pinned (not v4) | shadcn/ui components authored for Tailwind v3 config.js theming; v4 breaks CSS variable setup |
| React Router v6 SPA mode (not TanStack Router) | Two-screen app; TanStack Router type-safety overhead unjustified |
| Game state persisted to PostgreSQL immediately | NAS containers restart unexpectedly; no in-memory session state |
| 03-19/03-20 flow redesign | 03-18 live NAS verification: eligible endpoints gated behind current_movie_watched; Radarr fires at session start; manual Mark as Watched button; async background credits pre-fetch; eligible movies paginated |
| Plex webhook removed in 03-21 (new requirement) | 03-20 live NAS testing: Plex webhook unreliable; all watched events manual via Mark as Watched button; plex.py deleted, main.py updated |
| continue-chain endpoint separate from resume (03-21) | resume_session (paused->active) must reset current_movie_watched=False for new movie iteration; continue-chain (awaiting_continue->active) must preserve current_movie_watched=True so eligible tabs remain unlocked |
| Session Home Page as default hub, view state replacing showSessionHome (03-24) | 03-23 live test: showSessionHome defaulting to false causes Tab View to appear on every load; two-view model (home|tabs) with home as default is the correct architecture |
| request_movie must reset current_movie_watched=False (03-26) | 03-25 live test: after continue-chain preserves current_movie_watched=True, request_movie must reset it to False so Session Home Page condition (active + !current_movie_watched) is met for the 2nd movie |
| get_eligible_actors needs BackgroundTasks pre-fetch + on-demand fallback (03-28) | 03-27 live test: eligible-actors returns intersection of all chain movies' casts because request_movie never triggered a credit pre-fetch for the new movie; fix: (1) add background_tasks.add_task in request_movie, (2) add synchronous TMDB fallback in get_eligible_actors when DB returns empty |
| Multi-session gate removed in Phase 03.1 | Original single-session gate was for Plex webhook matching; Plex webhook was removed in 03-21; all interactions are now manual; no reason to restrict to one session |
| SessionStatus.archived as new enum value, not boolean column | status is String(20) not PostgreSQL ENUM; adding "archived" requires no schema change to the column; partial unique index on name enforces name uniqueness among active sessions only |
| NavBar Sessions link → "/" always in Phase 03.1 | Multi-session world has no single "the active session"; NavBar polls removed; home page shows all sessions |
| GameSession fetches by session ID not getActiveSession (03.1-09) | Live NAS testing: second session showed no buttons because getActiveSession always returned session 1; fix: use api.getSession(sid) with React Router :sessionId param |
| Pause/resume removed from UI entirely (03.1-09) | Live NAS testing confirmed R1: pause/resume adds complexity without user value; archive is the session lifecycle end-point; removal simplifies GameSession.tsx significantly |
| Phase 03.2 filters are client-side (no new API params per filter change) | CONTEXT.md locked decision: eligible-movies list loaded once per actor selection; all filter/search applied client-side to the fetched list |
| mpaa_rating="" sentinel for "checked, no US cert" (03.2-02) | None = never fetched; "" = fetched but no US certification found; prevents re-fetch on every eligible-movies request |
| vote_count uses on_conflict_do_update (03.2-03) | on_conflict_do_nothing would silently skip updating vote_count on existing Movie rows; must use on_conflict_do_update for vote_count and vote_average fields |
| Step thumbnails only in get_session_by_id and get_active_session (03.2-03) | _enrich_steps_thumbnails adds DB queries; only these two endpoints render ChainHistory; other endpoints (pause, resume, etc.) return poster_path=None by default |
| _ensure_movie_details_in_db called in eligible-movies (03.2-07) | Movie stubs from _ensure_actor_credits_in_db have genres=NULL and runtime=NULL; /person/{id}/movie_credits does not return genres or runtime; full TMDB movie detail fetch required during eligible-movies request for stubs with genres IS NULL |
| Ineligible actors always visible, no toggle (03.2-08) | 03.2-06 human verify: user prefers always-visible at top rather than toggle; removes showIneligible state, always fetches include_ineligible=true |
| Gap 3 redefined — Eligible Movies tab must show all eligible movies immediately without actor selection (03.2-09) | 03.2-09 human verify: empty state text change insufficient; user intent is no-actor = load all eligible movies for session with filters available; entirely new behavior not yet implemented |
| Regression 1 fix — rebuild SELECT after on-demand fallback inserts (03.2-10) | get_eligible_actors on-demand fallback reused pre-built `stmt` after multiple db.commit() calls; fresh SELECT guarantees visibility of newly inserted Credit rows |
| Gap 3 fix — eligible-movies query enabled without actor (03.2-11) | Backend combined-view already returns all eligible movies when actor_id=None; frontend fix: enable query unconditionally, queryKey uses null (not undefined) for no-actor state |
| Regression 2 fix — queryKey null-stabilization (03.2-11) | selectedActor?.tmdb_id ?? null ensures distinct React Query cache entries for no-actor vs actor-present states, preventing stale actor data flash |

---
*Roadmap created: 2026-03-14*
*Last updated: 2026-03-17 — Phase 03.2 gap closure round 2: plans 10 (Regression 1 backend fix), 11 (Gap 3 frontend + Regression 2 queryKey fix), 12 (Docker rebuild + verify) added*
