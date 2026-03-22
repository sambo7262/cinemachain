# CinemaChain

## What This Is

A Dockerized home media companion app running on Synology NAS, integrated with Radarr. Given a movie as the starting point, it surfaces filmography data to guide the user's next media selection through a structured actor-chain discovery game. Selections are queued automatically via Radarr.

## Core Value

The Movie Game — a chain-based discovery engine that navigates cinema through shared actors, making "what to watch next" effortless and exploratory without ever repeating an actor.

## Current State — v1.0 Shipped (2026-03-22)

**v1.0 is live on Synology NAS and publicly deployable via Docker Hub.**

### What's Working
- **Movie Game** — full actor-chain loop: start movie → pick actor → pick next movie → repeat; Radarr queuing on each pick
- **Multi-session support** — concurrent named sessions, archive/delete, session grid on home page
- **CSV import/export** — import a pre-existing chain with fuzzy actor resolution and disambiguation UI
- **Eligible Movies** — sortable (rating/runtime/year/MPAA), filterable (genre/MPAA/rating/vote-floor), searchable by title
- **RT scores** — MDBList Tomatometer displayed in eligible movies table, Now Playing tile, and movie splash
- **Settings page** — configure Radarr URL/key, TMDB key, MDBList key with encrypted DB storage and onboarding gate
- **Nightly TMDB cache** — pre-warms top 5,000 movies + 1,500 actors; zero on-demand calls during gameplay
- **Local poster caching** — nightly download of poster images; CDN fallback
- **Chain history** — searchable table of all picks with actor/movie thumbnails and TMDB external links
- **Public deployment** — generic `compose.yaml`, placeholder `.env.example`, 148-line README

### Known Tech Debt
- `backend/app/routers/debug.py` exists as dead code (unreachable — not registered in main.py)
- `backend/.env.example` has orphaned Plex/Sonarr/Tailscale placeholder fields
- `postgres` service in compose.yaml lacks explicit `networks:` declaration (implicit, works correctly)

## Next Milestone: v2.0

**Not yet planned.** Seed requirements from v1 scope exceptions:

| Requirement | Description |
|-------------|-------------|
| QUERY-01 | Search by actor name → full filmography |
| QUERY-02 | Search by movie/TV title → that specific item |
| QUERY-03 | Browse by genre/keyword |
| QUERY-04 | Sort results by genre, rating, year |
| QUERY-05 | Toggle show/hide watched items |
| QUERY-06 | Movie request via Radarr |
| QUERY-07 | TV show request via Sonarr |
| DATA-05 | Optional Plex webhook re-integration |

Run `/gsd:new-milestone` to begin requirements gathering for v2.

## Stack

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic
- **Frontend:** React + TypeScript + Vite + Tailwind v3 + shadcn/ui
- **Infrastructure:** Docker Compose + Nginx proxy + APScheduler
- **External APIs:** TMDB, Radarr, MDBList

## Context

- **Infrastructure:** Synology NAS running Docker; app on Tailscale LAN
- **Integrations:** Radarr API (movie requests), TMDB API (filmography + metadata), MDBList API (RT scores)
- **Primary use case:** On-the-couch media selection — UI designed for tablet/TV

---
*Updated: 2026-03-22 — v1.0 archived*
