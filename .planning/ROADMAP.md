# ROADMAP — CinemaChain v1.0

**Milestone:** v1.0 CinemaChain
**Created:** 2026-03-14
**Granularity:** Standard
**Coverage:** 25/25 requirements mapped

---

## Phases

- [ ] **Phase 1: Infrastructure** — Docker Compose stack with PostgreSQL, backend skeleton, and Tailscale sidecar running on Synology NAS
- [ ] **Phase 2: Data Foundation** — TMDB filmography cache, Plex watch history sync, and manual watch marking operational
- [ ] **Phase 3: Movie Game** — Complete actor-chain game loop with session state, eligibility panels, and Radarr request submission
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
**Plans:** 5 plans

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
**Plans:** TBD

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
| 2. Data Foundation | 1/5 | In Progress | — |
| 3. Movie Game | 0/? | Not started | — |
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
| QUERY-01 | Phase 4 |
| QUERY-02 | Phase 4 |
| QUERY-03 | Phase 4 |
| QUERY-04 | Phase 4 |
| QUERY-05 | Phase 4 |
| QUERY-06 | Phase 4 |
| QUERY-07 | Phase 4 |

**Total mapped:** 25/25

---

## Key Decisions Captured

| Decision | Rationale |
|----------|-----------|
| Phase 4 depends on Phase 2, not Phase 3 | Query mode shares the data layer but is independent of game session state; can be planned in parallel after Phase 2 |
| Plex webhook (DATA-05) in Phase 2, not deferred | It is a v1 requirement; manual mark (DATA-06) is the fallback if webhook proves unreliable during development |
| No separate frontend phase | Backend and UI for each mode are delivered together; splitting them leaves nothing verifiable at phase boundaries |
| No polish phase | v1 has no explicit polish requirements; hardening tasks belong in individual phase plans as acceptance conditions |

---
*Roadmap created: 2026-03-14*
*Last updated: 2026-03-15 — Phase 2 plan 02-01 complete (Wave 0 test stubs)*
