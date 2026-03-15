---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Plan 01-04 Task 1 complete — ts-serve.json, volume placeholders, compose.yaml mount; awaiting NAS cold-boot (human-action gate)
last_updated: "2026-03-15T05:47:08.755Z"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
---

# STATE.md — CinemaChain

## Project Reference

**What:** A Dockerized home media companion app on Synology NAS integrated with Plex, Radarr, and Sonarr. Surfaces filmography data via a chain-based actor discovery game and direct search. Selections are queued via Radarr/Sonarr.

**Core Value:** The Movie Game — navigate cinema through shared actors, making "what to watch next" effortless without ever repeating an actor.

**Current Milestone:** v1.0 CinemaChain

## Current Position

- **Phase:** Phase 1 — Infrastructure (not started)
- **Plan:** —
- **Status:** Roadmap complete; ready to plan Phase 1

## Progress

`[░░░░░░░░░░] 0%` — Phase 1 of 4 not started

| Phase | Status |
|-------|--------|
| 1. Infrastructure | Not started |
| 2. Data Foundation | Not started |
| 3. Movie Game | Not started |
| 4. Query Mode | Not started |

## Recent Decisions

- **2026-03-14:** PostgreSQL chosen over SQLite — game session join queries (eligibility filtering, actor exclusion) require the richer query support; SQLite recommendation from Stack research overridden
- **2026-03-14:** Plex webhook (DATA-05) included in Phase 2 as a v1 requirement; DATA-06 (manual mark) is the fallback if webhook proves unreliable
- **2026-03-14:** Phase 4 (Query Mode) depends only on Phase 2 (data layer), not Phase 3 (game); shared services, no session state dependency
- **2026-03-14:** No separate frontend phase — backend and UI for each mode delivered together so each phase boundary produces something verifiable

## Pending Todos

- Resolve RT ratings source before Phase 3 planning (options: TMDB vote_average as proxy, OMDb `tomatoes=true`, or scraping — OMDb is cleanest path)
- Verify pyarr v5.2.0 compatibility with installed Radarr/Sonarr versions before Phase 3 planning; fall back to direct httpx if needed
- Confirm Plex Pass availability before Phase 2 — DATA-05 (webhook) requires Plex Pass; DATA-06 (manual mark) covers non-Plex-Pass setups

## Blockers / Concerns

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

Last session: 2026-03-15T05:46:55.019Z
Stopped at: Plan 01-04 Task 1 complete — ts-serve.json, volume placeholders, compose.yaml mount; awaiting NAS cold-boot (human-action gate)
Resume with: `/gsd:plan-phase 1`
