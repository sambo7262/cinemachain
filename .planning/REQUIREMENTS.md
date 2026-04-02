# Requirements: CinemaChain v2.0

**Defined:** 2026-03-30
**Core Value:** Expand CinemaChain beyond the game loop — add direct movie discovery via Query Mode, richer session tools (save/compare), deeper MDBList data integration, and fix all known UX friction points.

---

## v2 Requirements

### Bug Fixes (BUG)

- [x] **BUG-01**: Mobile UI renders correctly at 320–768px across all game views
- [x] **BUG-02**: MPAA rating displays for all movies with available TMDB data
- [x] **BUG-03**: Movie overview populates in splash dialog for all movies
- [x] **BUG-04**: Chain history and movie search results paginate correctly
- [x] **BUG-05**: Eligible movies sort order is stable when new movies are dynamically loaded
- [x] **BUG-06**: Movies with valid TMDB entries show RT score or explicit N/A — never blank
- [x] **BUG-07**: Session-specific: eligible movies display correctly for all actors in affected session (Trainspotting chain)
- [x] **BUG-08**: Session-specific: CSV export succeeds for affected session

### Navigation (NAV)

- [x] **NAV-01**: Top nav has three permanent items: Game Mode, Query Mode, Settings
- [x] **NAV-02**: Game Mode routes to session grid (existing lobby behaviour preserved)
- [x] **NAV-03**: Settings accessible globally from top nav at all times

### Query Mode (QMODE)

- [x] **QMODE-01**: User can search movies by title and see results with poster, year, rating, genre, RT score
- [x] **QMODE-02**: User can search by actor name and browse their filmography
- [x] **QMODE-03**: User can browse movies by genre
- [x] **QMODE-04**: User can sort results by rating, year, runtime, RT score
- [x] **QMODE-05**: User can toggle all movies / unwatched-only in results
- [x] **QMODE-06**: User can request a movie from query results via Radarr

### Session Enhancements (SESS)

- [x] **SESS-01**: User can tag/save any movie in the eligible movies list during an active session
- [x] **SESS-02**: Saved movies persist for the duration of the session
- [x] **SESS-03**: Eligible movies list can be filtered to show only saved movies
- [x] **SESS-04**: User can shortlist 2-6 eligible movies; list filters to shortlisted items for comparison

### MDBList Expansion (MDBLIST)

- [x] **MDBLIST-01**: Research what MDBList basic tier (10k/day) provides beyond RT scores
- [x] **MDBLIST-02**: IMDB ratings displayed alongside RT scores in eligible movies table, splash, and Now Playing tile
- [x] **MDBLIST-03**: Additional high-value MDBList data surfaced where contextually appropriate (determined in research phase)

### MDBList Watched List Sync (MDBSYNC)

- [x] **MDBSYNC-01**: ~~Every movie marked as watched (game session or Query Mode) is synced to the user's MDBList watched list in real time~~ — **Superseded:** Phase 14 MDBList watched-sync was intentionally removed in Phase 16 (Watched History). First-party Watch History replaces MDBList sync.
- [x] **MDBSYNC-02**: ~~Bulk sync on demand from Settings — push full existing watch history to MDBList; MDBList list ID configurable in Settings~~ — **Superseded:** See MDBSYNC-01.

### TMDB Suggested Movies (SUGGEST)

- [x] **SUGGEST-01**: A Suggested filter toggle appears in the eligible movies panel when TMDB recommendations intersect with eligible actors at the current step
- [x] **SUGGEST-02**: Suggested movies support the same actions as regular eligible movies (request, save, shortlist)
- [x] **SUGGEST-03**: Filter toggle is hidden when no intersecting suggestions exist — no empty state shown

### Watched History (WATCHED)

- [x] **WATCHED-01**: A Watched History nav item appears alongside Game Mode and Query Mode
- [x] **WATCHED-02**: Watched History shows all movies marked watched across all sessions in a tile or grid layout (user-toggleable)
- [x] **WATCHED-03**: Watched History is searchable by title; all Phase 14 MDBList watched-sync code is removed

### IMDB Actor Links (IMDB)

- [~] **IMDB-01**: Actor rows have `imdb_person_id` stored; ChainHistory actor links point to `imdb.com/name/{id}` instead of TMDB — **Partial:** Movie links point to IMDB (with TMDB fallback) per Phase 17. Actor IMDB links (`imdb_person_id`) explicitly deferred — backfill cost not justified.

### Backend Logging & Key Security Hardening (LOG / SEC)

- [x] **LOG-01**: No API key or credential value appears in plaintext in any backend log line or exception traceback
- [x] **LOG-02**: Masked format `***abc` (last 3 chars of actual key) used consistently across logs, API responses, and Settings display
- [x] **SEC-01**: GET /settings never returns full API key values — returns masked values so keys cannot be extracted via network tab or API call after initial save
- [x] **SEC-02**: Settings encryption key auto-generated and persisted on first run if not configured — DB storage is always encrypted, no plaintext fallback
- [x] **SEC-03**: External API keys transmitted via HTTP headers (not URL query params) where the API supports it — TMDB upgraded to Bearer token; MDBList best-effort

### v2 Bug Fixes (v2BUG)

- [x] **v2BUG-01**: Bugs logged during v2 development (Phases 13-18) resolved: rating dialog on mark-as-watched, mobile UI fixes, filter/search bugs, NR filter, session menu reorder, atomic delete-last-step, badge tooltips, sort defaults, UI polish


### Now Playing Polish (POLISH)

- [x] **POLISH-01**: Now Playing hub shows full movie metadata (ratings, runtime, year, MPAA, overview) in both pre-watch and post-watch states, sourced from backend session response
- [x] **POLISH-02**: Content padding on all pages aligns exactly with NavBar edges on all viewport sizes — no double-padding
---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Plex integration | Shelved — manual Mark as Watched is the supported path |
| Sonarr / TV show requests | Movies only for Query Mode in v2 |
| Mark as Watched improvements | Too complex (multi-session, re-watch scenarios) |
| Genre-constrained game mode | Deferred to v2.1+ |
| Director/writer chain types | Deferred to v2.1+ |
| Stats dashboard | Deferred to v2.1+ |
| Discord download notifications | Deferred to v2.1+ |

---

## Traceability

| Requirement | Phase |
|-------------|-------|
| BUG-01 | Phase 8 |
| BUG-02 | Phase 8 |
| BUG-03 | Phase 8 |
| BUG-04 | Phase 8 |
| BUG-05 | Phase 8 |
| BUG-06 | Phase 8 |
| BUG-07 | Phase 8 |
| BUG-08 | Phase 8 |
| NAV-01 | Phase 9 |
| NAV-02 | Phase 9 |
| NAV-03 | Phase 9 |
| QMODE-01 | Phase 10 |
| QMODE-02 | Phase 10 |
| QMODE-03 | Phase 10 |
| QMODE-04 | Phase 10 |
| QMODE-05 | Phase 10 |
| QMODE-06 | Phase 10 |
| SESS-01 | Phase 11 |
| SESS-02 | Phase 11 |
| SESS-03 | Phase 11 |
| SESS-04 | Phase 11 |
| MDBLIST-01 | Phase 13 |
| MDBLIST-02 | Phase 13 |
| MDBLIST-03 | Phase 13 |
| MDBSYNC-01 | Phase 14 |
| MDBSYNC-02 | Phase 14 |
| SUGGEST-01 | Phase 15 |
| SUGGEST-02 | Phase 15 |
| SUGGEST-03 | Phase 15 |
| WATCHED-01 | Phase 16 |
| WATCHED-02 | Phase 16 |
| WATCHED-03 | Phase 16 |
| IMDB-01 | Phase 17 |
| SCHED-01 | Phase 17 |
| SCHED-02 | Phase 17 |
| SCHED-03 | Phase 17 |
| LOG-01 | Phase 18 |
| LOG-02 | Phase 18 |
| SEC-01 | Phase 18 |
| SEC-02 | Phase 18 |
| SEC-03 | Phase 18 |
| POLISH-01 | Phase 20 |
| POLISH-02 | Phase 20 |

**Coverage:** 44 requirements · 13 phases · 0 unmapped

---

*Requirements defined: 2026-03-30*
