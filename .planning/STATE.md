---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Dead state in session home eliminated — active+isWatched now shows Continue the chain button; navigates to actor selection tab without a backend call; no Docker rebuild required (frontend-only)
stopped_at: Completed 03.2-25-PLAN.md
last_updated: "2026-03-17T19:06:17.793Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 74
  completed_plans: 71
---

# STATE.md — CinemaChain

## Project Reference

**What:** A Dockerized home media companion app on Synology NAS integrated with Plex, Radarr, and Sonarr. Surfaces filmography data via a chain-based actor discovery game and direct search. Selections are queued via Radarr/Sonarr.

**Core Value:** The Movie Game — navigate cinema through shared actors, making "what to watch next" effortless without ever repeating an actor.

**Current Milestone:** v1.0 CinemaChain

## Current Position

- **Phase:** Phase 03.2 — Game UX Enhancements (follow-up plans executing; all open issues addressed)
- **Plan:** Completed 03.2-25 (CSV import actor eligibility fix — Movie stub upsert + BackgroundTasks pre-fetch)
- **Status:** CSV import actor eligibility fixed — _ensure_movie_cast_in_db upserts Movie stub before cast loop; import_csv_session fires _prefetch_credits_background; Docker rebuild + NAS deploy required to activate

## Progress

`[██████████] 96%` — 71 of 74 plans complete

| Phase | Status |
|-------|--------|
| 1. Infrastructure | Complete |
| 2. Data Foundation | Complete (02-01 through 02-05 done) |
| 3. Movie Game | Complete — all 29 plans done; full 6-step game loop PASS on live NAS; GAME-04 confirmed resolved (2026-03-15) |
| 3.1. UI Improvements and Multi-Session Support | Complete — all 9 plans done (03.1-09: frontend gap closure — getSession(id), movie badge, Import Chain card, Pause/Resume/End removed) |
| 3.2. Game UX Enhancements | Follow-up plans executing — 03.2-13 stale cache fix done (Mark as Watched button regression closed); Gap 3 (eligible movies without actor) and Regression 2 (stale movie list on actor change) still open |
| 4. Query Mode | Not started — waiting on Phase 03.2 completion |

## Recent Decisions

- **2026-03-17:** 03.2-25: _ensure_movie_cast_in_db upserts Movie stub with title='' before cast loop — CSV sessions never insert into movies table so Credit FK target was missing; empty title filled by _ensure_movie_details_in_db later
- **2026-03-17:** 03.2-25: Movie PK resolved once outside cast loop (was per-iteration SELECT) — same movie_tmdb_id for all cast members; eliminates N redundant DB round-trips per call
- **2026-03-17:** 03.2-25: background_tasks.add_task placed unconditionally after if prior_movie_ids: block in import_csv_session — mirrors create_session; even single-movie CSV imports get the cast pre-fetch
- **2026-03-17:** 03.2-26: active+isWatched branch in Continue the chain handler skips continueChain backend call — transition already occurred; setView("tabs") + setActiveTab("actors") navigate directly; eliminates only known stuck state on session home page
- **2026-03-17:** 03.2-23: prior_movie_ids set comprehension over steps_data (actor_tmdb_id is None and movie != last_movie_id) batch-inserts WatchEvent rows with source="csv_import" after db.commit()/db.refresh(); second db.commit() ensures WatchEvents exist before _build_session_response derives watched_count from them
- **2026-03-17:** 03.2-22: staleTime: 0 added to session query in GameSession.tsx — cached current_movie_watched: true was hiding Mark as Watched button after navigate-away and return; zero staleTime forces immediate refetch before render-critical button condition evaluates
- **2026-03-17:** 03.2-22: ChainHistory already correctly guarded by session.steps.length > 0 — no separate Watch History TabsTrigger exists; no change needed for Fix 3
- **2026-03-17:** 03.2-21: Both TMDB enrichment blocks merged under single `if actor_id is not None and hasattr(...)` guard — eliminates duplicate hasattr checks and makes combined-view vs actor-scoped branching explicit; combined-view returns immediately from DB cache avoiding NAS 504 timeouts
- **2026-03-16:** 03.2-18: useLoadingMessages returns string|null (not empty string); GameSession actors+movies and GameLobby CSV import use it; showMoviesSpinner state+useEffect removed entirely
- **2026-03-16:** 03.2-18: Direct TMDB ID input in CSV validation report placed outside u.suggestions conditional so it appears for both suggestion and no-result rows; calls handleOverridePick same as suggestion buttons
- **2026-03-16:** 03.2-18: import_csv_session sets current_movie_watched=False explicitly to document intent that last CSV row is in-progress (not yet watched)
- **2026-03-17:** 03.2-15: WatchEvent session-scoping via session.steps tmdb_id intersection instead of WatchEvent.session_id FK column — plan incorrectly assumed column existed; steps intersection avoids migration and delivers identical cross-session eligibility semantics (movie watched in Session A remains eligible in Session B)
- **2026-03-16:** 03.2-14: httpx.Timeout(connect=60s, read=90s) raised in TMDBClient to prevent ConnectTimeout on NAS for 136-row CSV imports
- **2026-03-16:** 03.2-14: import_csv_session two-pass validate-first: high/medium confidence rows auto-resolve; low/none rows return 200+validation_required without creating session; overrides re-submission skips TMDB lookup
- **2026-03-16:** 03.2-14: medium confidence (contains-match) auto-accepts to avoid excessive false-positive pickers; only low and none trigger suggestion picker
- **2026-03-16:** 03.2-14: CsvValidationResponse returns HTTP 200 (not 201) so frontend mutation onSuccess receives it instead of onError
- **2026-03-16:** 03.2-11: selectedActor?.tmdb_id ?? null in eligibleMovies queryKey — null (not undefined) creates distinct React Query cache entry for no-actor state; fixes Regression 2 stale movie list on actor change
- **2026-03-16:** 03.2-11: enabled condition for eligibleMovies is !!sid && !!session && isWatched with no selectedActor requirement — combined-view fires on tab open without actor selected; closes Gap 3 (UX-03)
- **2026-03-16:** 03.2-13: setQueryData(["session", sid], requestResult.session) inserted in handleMovieConfirm immediately after setView("home") — ensures current_movie_watched: false is in cache before user navigates away; invalidateQueries still runs for background refresh
- **2026-03-17:** 03.2-10: Regression 1 closed — fresh_stmt rebuilt after all _ensure_actor_credits_in_db inserts committed; reusing pre-built stmt missed new Credit rows due to SQLAlchemy async session transaction boundary semantics; fix is surgical (if not actors: block only)
- **2026-03-17:** 03.2-09: Gap 3 redefined — Eligible Movies tab must load ALL eligible movies immediately when opened without an actor selected (no-actor = show-all); loading spinner acceptable if fetch >1s; plan 08 empty-state text change does not satisfy this intent; new plan required
- **2026-03-17:** 03.2-09: Regression found — South Park chain (The Martian → Matt Damon → Good Will Hunting → Minnie Driver → South Park: Bigger Longer Uncut) returns zero eligible actors; likely _ensure_movie_details_in_db corrupting credits data during detail fetch
- **2026-03-17:** 03.2-09: Regression found — stale movie list on actor change; React Query queryKey for eligible-movies does not include selected actor ID, so cache is not invalidated when actor changes
- **2026-03-17:** 03.2-08: showIneligible toggle removed entirely; always call getEligibleActors(sid, true); queryKey drops showIneligible entry; ChainHistory moved to bottom of GameSession page after Tabs; movies empty state updated to "Pick an actor from the Eligible Actors tab to see movies."
- **2026-03-16:** 03.2-07: _ensure_movie_details_in_db fetches per-movie inside try/except; refresh query re-reads genre+runtime for all movies_map keys after fetch; helper placed between _ensure_actor_credits_in_db and _prefetch_credits_background
- **2026-03-16:** 03.2-05: eligibleActorsData holds full API result (eligible+ineligible); eligibleActors filtered client-side to is_eligible !== false; ineligible section reads eligibleActorsData directly — avoids double-fetch
- **2026-03-16:** 03.2-05: filteredMovies computed from allEligibleMovies (current paginated page); Load More pagination unchanged; filters apply within each loaded page
- **2026-03-16:** 03.2-05: parseGenres utility placed as module-level const in GameSession.tsx (not exported) — avoids coupling without adding a shared utility file
- **2026-03-16:** 03.2-05: SessionCounters rendered inside header flex-col alongside session name and Now Playing line — matches UI-SPEC.md placement between name and tab panel
- **2026-03-16:** 03.2-02: vote_count and mpaa_rating columns nullable — no backfill needed; migration 0005 chains from 0004; mpaa_rating VARCHAR(10) covers NC-17; no index needed (display/filter only)
- **2026-03-17:** 03.2-04: Slider thumb rendering uses both defaultValue and value arrays to support controlled and uncontrolled modes; callers always use controlled value in practice
- **2026-03-17:** 03.2-04: Collapsible is a thin Radix re-export with no forwardRef wrapper — matches canonical shadcn pattern for this primitive
- **2026-03-17:** 03.2-04: Installed @radix-ui/react-slider, react-checkbox, react-collapsible via npm — packages assumed bundled but were absent from package.json
- **2026-03-15:** 03.1-09: getSession(id) added alongside getActiveSession — both kept; getActiveSession still used in NavBar and other contexts
- **2026-03-15:** 03.1-09: key={defaultTab} on Tabs remounts component to reset active tab — simpler than controlled tab state for Import Chain card pre-selection
- **2026-03-15:** 03.1-09: pauseMutation/resumeMutation/endMutation removed entirely from GameSession.tsx — dead code elimination after Pause/Resume/End buttons removed
- **2026-03-16:** 03.1-08: current_movie_title derived from session.steps — no extra DB query; step.movie_title already stored at session creation
- **2026-03-16:** 03.1-08: GET /sessions/{session_id} placed after static /sessions/active to prevent FastAPI casting string 'active' as integer (422 error)
- **2026-03-16:** 03.1-08: _enrich_steps_watched_at uses MAX(watched_at) GROUP BY tmdb_id — defensive dedup even though UniqueConstraint currently guarantees one row per tmdb_id
- **2026-03-16:** 03.1-06: NavBar Sessions link routes to "/" always — multi-session world has no single active session; isSessionsActive covers "/" and "/game/*" via useLocation
- **2026-03-16:** 03.1-06: getActiveSession poll removed from NavBar — eliminates single-session assumption; useQuery/api imports removed entirely
- **2026-03-16:** 03.1-06: ArchivedSessions staleTime 30000 — archived data immutable; View button navigates to /game/:id for read-only viewing via GameSession
- **2026-03-15:** 03.1-05: currentMovieTitle fallback chain: find by movie_tmdb_id -> last step title -> (untitled); avoids TMDB ID leaking into UI
- **2026-03-15:** 03.1-05: ChainHistory actor thumbnail uses initials placeholder — step DTO does not carry profile_path; bg-muted circle with initials matches existing eligible actors table pattern
- **2026-03-15:** 03.1-05: Export CSV button placed before Pause/Resume in GameSession header actions — consistent left-to-right: export, pause, end
- **2026-03-16:** 03.1-04: view: 'grid' | 'form' enum state drives GameLobby home page — grid is default; form expands inline on '+ Start a new session' click; no modal needed
- **2026-03-16:** 03.1-04: activeSessions (plural) queryKey used for session list in GameLobby — avoids cache collision with per-session 'session' key in GameSession.tsx
- **2026-03-16:** 03.1-04: isNameValid gates movie-selection tabs via opacity-50 + pointer-events-none CSS; ParsedRow.isValid flag carries per-row sequence validity; currentMovieForSession helper resolves title from steps with fallback
- **2026-03-16:** 03.1-03: exportCsv is void fire-and-forget using fetch+blob — cannot use apiFetch JSON wrapper for CSV blob download; getActiveSession kept intact for GameSession.tsx polling
- **2026-03-16:** 03.1-02: name required on CreateSessionRequest; partial unique index uq_game_sessions_name_active allows name reuse after archive/end; _build_session_response centralizes response construction with watched_at enrichment
- **2026-03-16:** 03.1-02: radarr_quality_profile setting (default "HD+") selects quality profile by name with fallback to first profile + warning if named profile not found
- **2026-03-16:** 03.1-01: Wave 0 test stubs for UI-01 through UI-08 appended to test_game.py — test_create_session_conflict preserved for 03.1-02 to update when multi-session gate is removed
- **2026-03-15:** 03-29: Full 6-step game loop PASS on live NAS — Phase 3 declared complete; all GAME-01 through GAME-08 requirements satisfied in production; Phase 4 (Query Mode) ready to start
- **2026-03-16:** 03-28: GAME-04 fix applied — request_movie fires BackgroundTasks pre-fetch for new movie cast; get_eligible_actors has on-demand TMDB fallback (top 20 cast) when DB returns empty; both changes in game.py only; Docker rebuild + NAS deploy + Step 6 re-verify required via 03-29
- **2026-03-16:** 03-28: on-demand fallback re-runs original SQL stmt (same current_movie_tmdb_id filter + picked_ids exclusion) after populating credits — avoids code duplication; degrades gracefully if TMDB unavailable
- **2026-03-15:** 03-27: PARTIAL PASS — Steps 1-5 verified on live NAS (deploy, fresh session, first movie flow, 2nd movie Mark as Watched button confirmed); Step 6 blocked by GAME-04 eligible-actors intersection bug; 03-28 required to close Phase 3
- **2026-03-15:** 03-27: GAME-04 root cause — get_eligible_actors intersects cast across all chain movies rather than (cast of current_movie_tmdb_id) MINUS (actor_tmdb_id values already in session.steps); fix: query credits for current movie only, exclude picked actor ids; no architectural change needed
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

- **[RESOLVED — 03.2-11] Gap 3 — Eligible Movies tab without actor:**
  - Fix: removed selectedActor requirement from enabled condition; queryKey uses null-stable actor ID; combined-view backend branch already handles actor_id=None correctly.
  - Commit: 40e404e in `frontend/src/pages/GameSession.tsx`.

- **[RESOLVED — 03.2-10] Regression 1 — Actor eligibility broken for _ensure_movie_details_in_db movies:**
  - Root cause: `get_eligible_actors` on-demand fallback reused pre-built `stmt` after `db.commit()` calls inside `_ensure_actor_credits_in_db`; new Credit rows were invisible due to SQLAlchemy async session transaction boundary semantics.
  - Fix: rebuild `fresh_stmt` after all inserts complete; commit be332ca in `backend/app/routers/game.py`.

- **[RESOLVED — 03.2-11] Regression 2 — Stale movie list on actor change:**
  - Fix: `selectedActor?.tmdb_id ?? null` in queryKey creates distinct cache entries for no-actor vs actor-scoped queries; loading spinner added for slow combined-view fetches.
  - Commit: 40e404e in `frontend/src/pages/GameSession.tsx`.

- **[RESOLVED — 03-29] GAME-04 eligible-actors intersection bug:**
  - Fix confirmed PASS in live NAS Step 6 verification (2026-03-15)
  - Eligible Actors for Deadpool and Wolverine shows full cast minus Ryan Reynolds; Phase 3 complete
- **[RESOLVED — 03-27] 03-26 fix deployed and confirmed:**
  - request_movie current_movie_watched=False reset is live; 2nd movie Mark as Watched button confirmed working in production
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

### Roadmap Evolution

- Phase 03.1 inserted after Phase 03: UI improvements and multi-session support (INSERTED)

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

Last session: 2026-03-17T19:06:17.788Z
Stopped at: Completed 03.2-25-PLAN.md
Resume with: Phase 03.1 fully complete. Docker rebuild + NAS deploy required. Begin Phase 4 (Query Mode).
