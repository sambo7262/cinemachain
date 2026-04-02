# ROADMAP — CinemaChain

---

## Completed Milestones

- **v1.0** (2026-03-14 → 2026-03-22) — Full Movie Game delivered: actor-chain session loop, multi-session support, TMDB cache, MDBList RT scores, Settings page, production deployment hardened for public use. 13 phases, 122 plans, 457 commits. [Full details →](.planning/milestones/v1.0-ROADMAP.md)

---

## Current Milestone: v2.0

**Goal:** Expand CinemaChain beyond the game loop — fix all known friction points, add Query Mode for direct movie discovery, richer session tools (save/compare), and deeper MDBList data integration.

---

## Phases

- [x] **Phase 8: Bug Fixes** — Mobile UI, MPAA/overview data gaps, pagination, sort stability, RT blanks, two session-specific bugs (completed 2026-03-31)
- [x] **Phase 9: Navigation Redesign** — Top nav restructure: Game Mode | Search | Settings permanently visible (completed 2026-03-30)
- [x] **Phase 10: Query Mode** — Movie and actor search, genre browse, sort/filter, Radarr requests from results (completed 2026-03-31)
- [x] **Phase 11: Session Enhancements** — Save/tag movies within a session, filter to saved, shortlist comparison (Game Mode only) (completed 2026-03-31)
- [x] **Phase 12: Mobile Movie List Redesign** — Condensed eligible-movies layout for mobile: no horizontal scroll, tighter data density, revised sort controls (completed 2026-04-01)
- [x] **Phase 13: MDBList Expansion** — Research + implement IMDB ratings, additional high-value MDBList data (completed 2026-04-01)

---

## Phase Details

### Phase 8: Bug Fixes
**Goal:** Resolve all known UX friction and data gaps before adding new features — mobile layout, missing metadata, pagination, sort stability, RT display, and two session-specific bugs.
**Depends on:** v1.0 (current state)
**Requirements:** BUG-01, BUG-02, BUG-03, BUG-04, BUG-05, BUG-06, BUG-07, BUG-08
**Success Criteria** (what must be TRUE):
  1. All game views render correctly on 320px–768px mobile viewports
  2. MPAA ratings appear for all movies where TMDB has the data
  3. Movie overview text appears in the splash dialog for all movies
  4. Chain history and movie search results paginate without missing or duplicating entries
  5. Eligible movies sort order remains stable when additional movies are loaded dynamically
  6. No movie with a valid TMDB entry shows a blank RT score — shows score or explicit N/A
  7. The Trainspotting-chain session shows eligible movies correctly for all actors
  8. CSV export succeeds for the affected session

### Phase 9: Navigation Redesign
**Goal:** Restructure the top navigation so Game Mode and Query Mode are first-class destinations, with Settings always globally accessible — laying the routing foundation for Query Mode.
**Depends on:** Phase 8
**Requirements:** NAV-01, NAV-02, NAV-03
**Plans:** 4 plans
**Success Criteria** (what must be TRUE):
  1. Top nav always shows: Game Mode, Query Mode, Settings — on every page
  2. Clicking Game Mode lands on the session grid (existing lobby, no behaviour change)
  3. Clicking Settings navigates to /settings from any page
  4. Query Mode nav item routes to a placeholder or live Query Mode page

Plans:
- [ ] 09-01-PLAN.md — NavBar redesign: Game Mode / Search / Settings with correct active-state logic
- [ ] 09-02-PLAN.md — Route restructure: /game + /search routes, remove /archived, fix catch-all
- [ ] 09-03-PLAN.md — Merge Archived into GameLobby as Active/Archived tabs
- [ ] 09-04-PLAN.md — Fix GameSession navigate("/") → navigate("/game") (2 call sites)

### Phase 10: Query Mode
**Goal:** Users can discover movies directly without starting a game — search by title or actor, browse by genre, sort and filter results, and request via Radarr.
**Depends on:** Phase 9
**Requirements:** QMODE-01, QMODE-02, QMODE-03, QMODE-04, QMODE-05, QMODE-06
**Plans:** 4 plans
**Success Criteria** (what must be TRUE):
  1. Searching a movie title returns results with poster, year, TMDB rating, genre, RT score
  2. Searching an actor name returns their filmography with the same data
  3. Browsing by genre returns a filtered movie list
  4. Results can be sorted by rating, year, runtime, and RT score
  5. User can toggle between all movies and unwatched-only
  6. Requesting a movie from results triggers a Radarr queue request and shows confirmation

Plans:
- [x] 10-01-PLAN.md — Wave 0: backend + frontend test stubs (asyncpg-skip pattern)
- [x] 10-02-PLAN.md — Wave 1: backend endpoints (search router, popular genre, Radarr request, radarr_helper)
- [x] 10-03-PLAN.md — Wave 2: frontend SearchPage (genre chips, search, results table, splash dialog)
- [x] 10-04-PLAN.md — Wave 3: action button state machine audit + human checkpoint

### Phase 11: Session Enhancements
**Goal:** Give users tools to manage decision-making during gameplay — save movies for later in a session and shortlist candidates for comparison.
**Depends on:** Phase 8
**Requirements:** SESS-01, SESS-02, SESS-03, SESS-04
**Plans:** 3 plans
**Success Criteria** (what must be TRUE):
  1. A save/bookmark action is available on each movie in the eligible movies list
  2. Saved movies are retained for the life of the session (survive tab changes, page refreshes)
  3. A "Saved" filter option in eligible movies shows only tagged movies
  4. User can select 2–6 movies to shortlist; a comparison filter reduces the list to those items only

Plans:
- [x] 11-01-PLAN.md — Backend: DB models, migration, 7 API endpoints, EligibleMovieResponse extension, request_movie side-effects
- [x] 11-02-PLAN.md — Frontend: api.ts functions, GameSession save/shortlist mutations, icons, filters, row treatments
- [x] 11-03-PLAN.md — Human verification: full save/shortlist feature testing

### Phase 12: Mobile Movie List Redesign
**Goal:** Rebuild the eligible-movies table so it works well on mobile without horizontal scrolling — condensed row layout, data density improvements, and revised sort controls that don't depend on column headers.
**Depends on:** Phase 11
**Requirements:** MOB-01, MOB-02, MOB-03
**Plans:** 1 plan
**Success Criteria** (what must be TRUE):
  1. Eligible movies list renders correctly on 320px–768px mobile viewports with no horizontal scrolling
  2. All key data fields (title, year, runtime, rating, RT, MPAA) visible without scrolling on mobile
  3. Sort controls work on mobile without requiring column header clicks

Plans:
- [x] 12-01-PLAN.md — Replace eligible-movies table with card list; add sort dropdown; move icons to poster overlays

### Phase 13: MDBList Expansion
**Goal:** Research the full MDBList basic tier API surface and implement IMDB ratings + any other high-value data throughout the app.
**Depends on:** Phase 8
**Requirements:** MDBLIST-01, MDBLIST-02, MDBLIST-03
**Success Criteria** (what must be TRUE):
  1. MDBList API capabilities documented (what data is available, request cost, caching strategy)
  2. IMDB ratings displayed in eligible movies table, movie splash, and Now Playing tile alongside RT scores
  3. At least one additional MDBList data point integrated where it adds clear value
**Plans:** 4/4 complete

Plans:
- [x] 13-01-PLAN.md — Backend data layer: migration, model columns, mdblist parser expansion, DTO extension
- [x] 13-02-PLAN.md — Backfill infrastructure: mdblist router, quota tracking, start/status endpoints
- [x] 13-03-PLAN.md — Frontend ratings: RatingsBadge component, replace RT displays, IMDB link swap
- [x] 13-04-PLAN.md — Settings backfill UI + human verification checkpoint

### Phase 14: MDBList Watched List Sync
**Goal:** Sync all watched movies (from game sessions and Query Mode mark-as-watched) to a MDBList list — seeding watch history so MDBList can generate personalised recommendations.
**Depends on:** Phase 13
**Requirements:** MDBSYNC-01, MDBSYNC-02
**Plans:** 3 plans
**Success Criteria** (what must be TRUE):
  1. Every movie marked as watched (game session or Query Mode) is posted to the user's MDBList watched list
  2. Bulk sync on demand: existing watch history can be pushed to MDBList from Settings
  3. MDBList list ID is configurable in Settings alongside the API key

Plans:
- [ ] 14-01-PLAN.md — Backend data layer: migration, model, push helper, real-time hooks in game.py + movies.py
- [ ] 14-02-PLAN.md — Bulk sync infrastructure: _SyncState, watched-sync endpoints, settings mdblist_list_id
- [ ] 14-03-PLAN.md — Frontend Settings Watch Sync UI + human verification checkpoint

### Phase 15: TMDB Suggested Movies
**Goal:** Surface TMDB-recommended movies as a Suggested filter in the eligible movies panel — cross-referenced against eligible actors so every suggestion is playable at the current game step.
**Depends on:** Phase 14
**Requirements:** SUGGEST-01, SUGGEST-02, SUGGEST-03
**Plans:** 4 plans
**Success Criteria** (what must be TRUE):
  1. A Suggested filter toggle appears in the eligible movies panel when TMDB recommendations intersect with eligible actors at the current step
  2. Suggested movies show the same data and actions (request, save, shortlist) as regular eligible movies
  3. Filter toggle is hidden when there are no intersecting suggestions — no empty state clutter

Plans:
- [x] 15-01-PLAN.md — Backend data layer: Alembic migration 0015 (tmdb_recommendations JSON column), settings DTO update
- [x] 15-02-PLAN.md — TMDB service + suggestions engine: TMDBClient.fetch_recommendations, suggestions.py service, BG task wired into mark_current_watched
- [x] 15-03-PLAN.md — Suggestions API endpoint: GET /sessions/{id}/suggestions with eligible pool intersection
- [x] 15-04-PLAN.md — Frontend: api.ts, GameSession filter toggle, Settings seed count input, human verification

### Phase 16: Watched History
**Goal:** Add a Watched History section as a first-party replacement for MDBList watched list sync — showing all watched movies across sessions in a searchable tile/grid view. Includes removal of all Phase 14 MDBList watched-sync code.
**Depends on:** Phase 15
**Requirements:** WATCHED-01, WATCHED-02, WATCHED-03
**Success Criteria** (what must be TRUE):
  1. A Watched History nav item appears alongside Game Mode and Query Mode
  2. Watched History shows all movies marked watched across all sessions, in a tile or grid layout (user-toggleable)
  3. Watched History is searchable by title
  4. All Phase 14 MDBList watched-sync code is removed (fire-and-forget push, /watched-sync endpoints, Settings UI, mdblist_synced_at column)
**Plans:** 4 plans
Plans:
- [ ] 16-01-PLAN.md — Phase 14 cleanup: remove all MDBList watched-sync code (backend + frontend + tests), Alembic migration 0016 to drop mdblist_synced_at
- [ ] 16-02-PLAN.md — Backend data layer: migration 0017 (global_saves table), extend GET /movies/watched with sort/search/pagination, PATCH /movies/{id}/rating, POST/DELETE /movies/{id}/save
- [ ] 16-03-PLAN.md — Frontend WatchHistoryPage: list/tile toggle, search, sort, pagination, splash dialog with personal rating + save/star; wire NavBar + App.tsx route
- [ ] 16-04-PLAN.md — GameSession integration: merge global_saves into eligible-movies saved_set; end-to-end human verification

### Phase 17: Backend Scheduler, Settings Audit & IMDB Actor Links
**Goal:** Review and harden backend scheduled jobs, database connection settings, and app configuration; plus swap actor external links in ChainHistory from TMDB to IMDB.
**Depends on:** Phase 13
**Requirements:** SCHED-01, SCHED-02, SCHED-03, IMDB-01
**Success Criteria** (what must be TRUE):
  1. All scheduled jobs (nightly MDBList backfill, any TMDB enrichment tasks) are correctly configured, fire on expected intervals, and log outcomes clearly
  2. Database connection pool settings are appropriate for a NAS SQLite/Postgres workload (pool size, timeout, overflow)
  3. App settings schema is audited — all keys documented, defaults verified, no orphaned or conflicting keys
  4. No redundant or overlapping background tasks that could double-fetch or exceed rate limits
  5. ChainHistory movie links point to `imdb.com/title/{id}` with TMDB fallback (actor IMDB links deferred)
**Plans:** 3 plans

Plans:
- [ ] 17-01-PLAN.md — IMDB movie links in StepResponse + DB connection pool hardening
- [ ] 17-02-PLAN.md — Scheduler redesign: TMDB job hardening + MDBList nightly job + cache router
- [ ] 17-03-PLAN.md — Settings audit, UI restructure, DB health endpoint, compose TZ fix

### Phase 18: Backend Logging & Key Security Hardening
**Goal:** Scrub API keys from all backend logs and exception tracebacks; harden key storage, transmission, and API response exposure so keys cannot be extracted once saved.
**Depends on:** Phase 8
**Requirements:** LOG-01, LOG-02, SEC-01, SEC-02, SEC-03
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. No API key or credential value appears in plaintext in any log line or exception traceback
  2. Masked format `***abc` (last 3 chars) used consistently across logs, API responses, and Settings display
  3. GET /settings returns masked key values — full keys are never returned to the client after initial save
  4. Settings encryption key auto-generated and persisted on first run — DB storage is always encrypted
  5. TMDB API calls use Bearer token header (not URL query param); MDBList best-effort

Plans:
- [x] 18-01-PLAN.md — Key security hardening: masking utils, encryption bootstrap, re-encrypt pass, GET/PUT masking, TMDB Bearer upgrade, test fix
- [x] 18-02-PLAN.md — Log scrubbing: ScrubSecretsFilter on root logger, httpx event hooks on all clients, scrub_traceback() at exception call sites

### Phase 19: v2 Bug Fixes & Polish
**Goal:** Resolve bugs logged during v2 development (Phases 13-18) and deliver small polish items — blocking issues fixed immediately, non-blocking issues batched here.
**Depends on:** Phase 13
**Requirements:** v2BUG-01 (and additional entries logged during development)
**Plans:** 9 plans (6 core + 3 gap closure)
**Success Criteria** (what must be TRUE):
  1. All bugs logged to this phase are resolved or explicitly deferred with rationale
  2. No regressions introduced in existing v2 features
  3. Rating prompt on mark-as-watched: a 1-10 dialog (skippable) appears when marking a movie watched from GameSession or Query Mode; rating written to `WatchEvent.rating`

Plans:
- [x] 19-01-PLAN.md — Rating dialog: RatingSlider component + integration into GameSession, SearchPage, WatchHistoryPage
- [x] 19-02-PLAN.md — Mobile UI fixes: nav overflow, badge overflow, global padding, session tile padding, Watch History portrait
- [x] 19-03-PLAN.md — GameSession bugs: filter/search reset on step advance, cross-page search, NR filter toggle, sort defaults DESC
- [x] 19-04-PLAN.md — Session menu reorder + atomic two-step delete-last-step
- [x] 19-05-PLAN.md — UI polish: save/shortlist button repositioning, badge tooltips, session tile changes
- [x] 19-06-PLAN.md — Requirements housekeeping + human verification checkpoint
- [x] 19-07-PLAN.md — Gap closure: mark-as-watched dialog layout rework + Now Playing post-watched badges
- [x] 19-08-PLAN.md — Gap closure: play space padding reduction + movie tile sizing on wider screens
- [x] 19-09-PLAN.md — Gap closure: home page session tile poster-first redesign with overlay Continue

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Bug Fixes | 4/4 | Complete   | 2026-03-31 |
| 9. Navigation Redesign | 4/4 | Complete | 2026-03-30 |
| 10. Query Mode | 4/4 | Complete | 2026-03-31 |
| 11. Session Enhancements | 3/3 | Complete | 2026-03-31 |
| 12. Mobile Movie List Redesign | 1/1 | Complete | 2026-04-01 |
| 13. MDBList Expansion | 4/4 | Complete | 2026-04-01 |
| 14. MDBList Watched List Sync | 0/3 | Superseded by Phase 16 | |
| 15. TMDB Suggested Movies | 4/4 | Complete | 2026-04-01 |
| 16. Watched History | 4/4 | Complete | 2026-04-01 |
| 17. Backend Scheduler, Settings Audit & IMDB Actor Links | 0/3 | Planned | |
| 18. Backend Logging & Key Security Hardening | 2/2 | Complete | 2026-04-02 |
| 19. v2 Bug Fixes & Polish | 9/9 | Complete | 2026-04-02 |
| 20. Now Playing Polish & Layout Alignment | 0/2 | Complete    | 2026-04-02 |
| 21. Pre-Deploy Hardening | 0/2 | Planned | |

---

### Phase 21: Pre-Deploy Hardening — API Key Validation & Git Cleanup
**Goal:** Add test-connection buttons for all three API keys in Settings so users get immediate feedback; clean up git history to v1.0 + v2.0 only; tidy orphaned fields from .env.example files before tagging and publishing v2.0.
**Depends on:** Phase 20
**Requirements:** PREDEPLOY-01, PREDEPLOY-02
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. Each Settings card (TMDB, MDBList, Radarr) has a test button that shows green/red/yellow feedback with verbose error messages; masked keys test the stored DB value
  2. Auto-validate all configured services on save
  3. Git history is squashed to two commits: v1.0 + v2.0 (force-pushed to GitHub, tagged v2.0 + latest)
  4. backend/.env.example has no orphaned Plex/Sonarr/Tailscale fields; root .env.example SETTINGS_ENCRYPTION_KEY comment reflects auto-generation

Plans:
- [x] 21-01-PLAN.md — API key validation: backend /settings/validate endpoint + frontend test buttons per card
- [x] 21-02-PLAN.md — Git cleanup: squash v2 history, force-push, tag v2.0 + latest, .env.example tidy

---

### Phase 20: Now Playing Polish & Layout Alignment
**Goal:** Enrich the Now Playing screen with full movie metadata and ratings so blank space is used effectively; align content padding to nav header width on all viewports.
**Depends on:** Phase 19
**Requirements:** POLISH-01, POLISH-02
**Plans:** 2/2 plans complete
**Success Criteria** (what must be TRUE):
  1. Now Playing shows movie ratings (IMDB, RT, Metacritic where available), runtime, year, MPAA, and overview in the space below the poster/title
  2. Content padding on actor/movie selection screens aligns exactly with the CinemaChain logo left-edge and settings icon right-edge on all viewport sizes

Plans:
- [ ] 20-01-PLAN.md — Now Playing metadata: ratings, runtime, year, MPAA, overview in home hub
- [ ] 20-02-PLAN.md — Content padding alignment: match nav header px exactly across all breakpoints

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| BUG-01 through BUG-08 | Phase 8 |
| NAV-01 through NAV-03 | Phase 9 |
| QMODE-01 through QMODE-06 | Phase 10 |
| SESS-01 through SESS-04 | Phase 11 |
| MOB-01 through MOB-03 | Phase 12 |
| MDBLIST-01 through MDBLIST-03 | Phase 13 |
| MDBSYNC-01 through MDBSYNC-02 | Phase 14 |
| SUGGEST-01 through SUGGEST-03 | Phase 15 |
| WATCHED-01 through WATCHED-03 | Phase 16 |
| SCHED-01 through SCHED-03 | Phase 17 |
| LOG-01 through LOG-02 | Phase 18 |
| v2BUG-01+ | Phase 19 |
| POLISH-01 through POLISH-02 | Phase 20 |
| PREDEPLOY-01 through PREDEPLOY-02 | Phase 21 |

---

