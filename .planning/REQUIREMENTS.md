# Requirements: CinemaChain

**Defined:** 2026-03-14
**Core Value:** The Movie Game — chain-based discovery engine navigating cinema through shared actors, making "what to watch next" effortless without ever repeating an actor.

## v1 Requirements

### Data Layer (DATA)

- [ ] **DATA-01**: System fetches movie metadata (poster, rating, year, genres) from TMDB API
- [ ] **DATA-02**: System fetches actor metadata and filmography credits from TMDB API
- [ ] **DATA-03**: System caches TMDB data in PostgreSQL to respect rate limits
- [x] **DATA-04**: System cross-references Plex library to determine watched/unwatched state per movie
- [x] **DATA-05**: System receives Plex webhook events to update watch state on playback completion
- [x] **DATA-06**: User can manually mark a movie as watched (fallback without Plex Pass)

### Movie Game (GAME)

- [ ] **GAME-01**: User can start a Movie Game session by manually selecting any movie as the starting point
- [x] **GAME-02**: User sees an Eligible Actors panel: cast of current movie, excluding already-picked actors
- [ ] **GAME-03**: User selects an actor to view their Eligible Movies panel (unwatched filmography)
- [ ] **GAME-04**: Session tracks picked actors so no actor can repeat within a session
- [ ] **GAME-05**: User can sort Eligible Movies by genre, TMDB rating, or aggregated rating
- [ ] **GAME-06**: User can toggle between unwatched-only or all movies with watched badges
- [ ] **GAME-07**: Only unwatched movies are selectable in Game mode
- [ ] **GAME-08**: User requests a movie, triggering an automatic Radarr queue request

### Query Mode (QUERY)

- [ ] **QUERY-01**: User can search by actor name to browse their full filmography
- [ ] **QUERY-02**: User can search by movie or TV show title to find a specific item
- [ ] **QUERY-03**: User can browse by genre or keyword
- [ ] **QUERY-04**: User can sort results by genre, rating, or year
- [ ] **QUERY-05**: User can toggle show/hide watched items
- [ ] **QUERY-06**: User can request a movie, triggering a Radarr request
- [ ] **QUERY-07**: User can request a TV show, triggering a Sonarr request

### Infrastructure (INFRA)

- [x] **INFRA-01**: App runs as Docker Compose stack (backend + PostgreSQL + frontend containers)
- [x] **INFRA-02**: All API keys and config managed via .env (TMDB, Plex, Radarr, Sonarr)
- [x] **INFRA-03**: PostgreSQL data persists via Docker volumes across restarts
- [x] **INFRA-04**: App is accessible via Tailscale IP/hostname on the home network

## v2 Requirements

### Enhancements

- **GAME-EX-01**: Sort filmography by "most connectable" (actor appears in most unwatched movies) — gamification depth requiring graph traversal
- **GAME-EX-02**: Cross-session chain history / saved chains — lets user replay or continue past sessions
- **GAME-EX-03**: Genre-constrained game mode (e.g., horror-only chain)
- **NOTIF-01**: Discord/webhook notification when download completes
- **SOCIAL-01**: Letterboxd export of watch log

## Out of Scope

| Feature | Reason |
|---------|--------|
| Plex watch history auto-start | Replaced by manual movie selection (GAME-01) |
| Multi-user / authentication | Single-user household; Overseerr handles multi-user use cases |
| Movie Game for TV shows | Game mode is movies-only; TV available in Query mode only |
| Rotten Tomatoes integration | No public API; scraping fragile; deferred indefinitely |
| Plex library status in results | Adds complexity without clear value for this use case |
| Push/mobile notifications | Infrastructure overhead; Discord webhook sufficient |
| Recommendation algorithm | Actor-chain mechanic IS the recommendation engine |
| Full Plex player embed | Plex already does this; out of scope for companion app |
| Social features (reviews, follows) | Single-user app; Letterboxd already exists |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Complete |
| DATA-05 | Phase 2 | Complete |
| DATA-06 | Phase 2 | Complete |
| GAME-01 | Phase 3 | Incomplete — session start state machine flow defect (03-17) |
| GAME-02 | Phase 3 | Complete |
| GAME-03 | Phase 3 | Incomplete — combined-view credits not populated on mount (03-17) |
| GAME-04 | Phase 3 | Incomplete — blocked pending GAME-01 live verification |
| GAME-05 | Phase 3 | Incomplete — blocked pending GAME-01 live verification |
| GAME-06 | Phase 3 | Incomplete — blocked pending GAME-01 live verification |
| GAME-07 | Phase 3 | Incomplete — blocked pending GAME-01 live verification |
| GAME-08 | Phase 3 | Incomplete — Radarr result not surfaced to user (03-17) |
| QUERY-01 | Phase 4 | Pending |
| QUERY-02 | Phase 4 | Pending |
| QUERY-03 | Phase 4 | Pending |
| QUERY-04 | Phase 4 | Pending |
| QUERY-05 | Phase 4 | Pending |
| QUERY-06 | Phase 4 | Pending |
| QUERY-07 | Phase 4 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-15 after 03-16 partial pass — GAME-01, GAME-03, GAME-08 incomplete; GAME-04 through GAME-07 blocked pending GAME-01 live verification*
