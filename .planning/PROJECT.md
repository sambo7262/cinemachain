# CinemaChain

## What This Is

A Dockerized home media companion app running on Synology NAS, integrated with Radarr. Surfaces filmography data to guide media selection through a structured actor-chain discovery game, plus direct search (Query Mode), save/shortlist tools, a Watched History view, and multi-source ratings (IMDB / RT / Metacritic / Letterboxd / MDB Average). Selections are queued automatically via Radarr.

## Core Value

**The Movie Game inside a complete media companion.** Chain-based actor discovery is still the default mode, but users can now search directly, save/compare candidates, see what they've watched, and trust the ratings on every tile.

## Current State — v2.0 shipped (2026-05-29)

**v2.0 is live on Synology NAS, deployable via Docker Hub, and verified against the original Filmography Refresh Gap bug.**

### What v2.0 Added Over v1.0
- **Query Mode** — direct movie/actor/genre search with Radarr requests, no game needed
- **Save + Shortlist** — bookmark or compare 2–6 movies during a session
- **Watched History** — first-party `/watched` route with tile/grid + sort + search
- **Multi-source ratings** — IMDB + RT + Metacritic + Letterboxd + MDB Average via MDBList API
- **TMDB suggestions** — recommendations filter intersected with eligible actors
- **Mobile redesign** — card-based eligible movies, mobile nav overflow fixes
- **Settings hardening** — key masking (`***xyz`), log scrubbing, encrypted DB storage, per-card test-connection buttons
- **Filmography freshness** — 14-day TTL self-heal + nightly force-refresh + manual Settings button (closes the Meryl/DWP2 staleness gap)

### Known Tech Debt
- Two ad-hoc post-Phase-21 commits (`e2a8695`, `e5d54c7`) are on `main` but never assigned to a formal phase
- `backend/app/routers/debug.py` — dead code, not registered in main.py
- `postgres` service in `compose.yaml` lacks explicit `networks:` declaration (implicit, works)
- `filmography_fetched_at` only populated for actors interacted with post-v2.0 deploy; long-tail stays NULL until first encounter (by design — additive-only migration)
- `IMDB-01` partial: movie IMDB links delivered, actor IMDB backfill deferred

## Next Milestone — v2.1 (not yet planned)

Run `/gsd:new-milestone` to start requirements gathering. Candidate seeds surfaced from v2.0 close-out:

| Candidate | Description |
|-----------|-------------|
| Plex polling sync | Automatic watched-detection via polling (webhook was removed in v1) |
| Stats dashboard | Longest chain, most-picked actors, total runtime, chains over time |
| Alt chain types | Director / writer / composer chains — TMDB data already available |
| Genre-constrained game | Lock a session to a single genre (e.g., horror-only) |
| DB metadata scrub | Audit + re-enrich movies missing rating/overview |
| Retroactive phase | Formalize the two post-Phase-21 ad-hoc commits |
| Actor IMDB links | Backfill `imdb_person_id`, finish IMDB-01 |
| Discord notifications | NOTIF-01 from v1 backlog — Radarr download complete pings |
| Dead-end recovery | Surface nearby actors when chain is stuck |

## Stack

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic
- **Frontend:** React + TypeScript + Vite + Tailwind v3 + shadcn/ui
- **Infrastructure:** Docker Compose + Nginx proxy + APScheduler
- **External APIs:** TMDB (Bearer token auth), Radarr (X-Api-Key), MDBList

## Context

- **Infrastructure:** Synology NAS running Docker; app on Tailscale LAN
- **Integrations:** Radarr API (movie requests), TMDB API (filmography + metadata), MDBList API (ratings — RT, IMDB, Metacritic, Letterboxd, MDB Average)
- **Primary use case:** On-the-couch media selection — UI designed for tablet/TV

<details>
<summary>Previous milestone state — v1.0</summary>

> A Dockerized home media companion app running on Synology NAS, integrated with Radarr. Given a movie as the starting point, it surfaced filmography data to guide the user's next media selection through a structured actor-chain discovery game. Selections were queued automatically via Radarr.
>
> Core value (v1): The Movie Game — a chain-based discovery engine.
>
> v1 delivered the full initial app — TMDB data layer, Movie Game with actor-chain session state, multi-session support, UI/UX polish, RT ratings via MDBList, Docker deployment hardened for public use. 13 phases, 122 plans, 457 commits.

</details>

---
*Updated: 2026-05-29 — v2.0 milestone shipped and archived.*
