# CinemaChain

## What This Is

A Dockerized home media companion app running on Synology NAS, integrated with Plex, Radarr, and Sonarr. Given a movie or actor as input, it surfaces filmography data to guide the user's next media selection — through a structured actor-chain discovery game or direct search. Selections are queued automatically via Radarr/Sonarr.

## Core Value

The Movie Game — a chain-based discovery engine that navigates cinema through shared actors, making "what to watch next" effortless and exploratory without ever repeating an actor.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Data Layer**
- [ ] TMDB API as primary filmography source (actors, movies, TV shows, ratings, roles)
- [ ] IMDB as fallback data source for coverage gaps
- [ ] PostgreSQL storing filmography data, watch history, and game session state
- [ ] Plex API integration to sync watch history
- [ ] Plex webhook listener for playback completion events (manual "mark watched" as fallback)

**Movie Game Mode**
- [ ] Session state: tracks which actors have been picked (no repeats per session)
- [ ] Eligible Actors panel: cast of last-watched movie, excluding previously picked actors
- [ ] Eligible Movies panel: unwatched filmography of the selected actor
- [ ] Sort by genre, IMDB rating, and aggregated rating
- [ ] Toggle: show all movies with watched badges vs hide already-watched
- [ ] Only unwatched movies are selectable/requestable
- [ ] Selection triggers Radarr (movies) or Sonarr (TV) request

**Query Mode**
- [ ] Search by actor name → full filmography
- [ ] Search by movie/show title → that specific item
- [ ] Search by genre/keyword → browse results
- [ ] Sort by genre, rating, year
- [ ] Toggle: show/hide watched
- [ ] Selection triggers Radarr/Sonarr request

**Infrastructure**
- [ ] Docker Compose: separate containers for backend, PostgreSQL, and frontend
- [ ] .env support for all API keys and config (TMDB, Plex, Radarr, Sonarr)
- [ ] Volumes for DB persistence
- [ ] Accessible via Tailscale on home network

### Out of Scope

- Plex library status in results — adds complexity without clear value for this use case
- Multi-user / authentication — single-user household, not needed
- Movie Game for TV shows — Movie Game is movies-only; TV shows available in Query mode only
- Rotten Tomatoes official API — no public API exists; RT scores deferred to planning phase

## Context

- **Infrastructure:** Synology NAS running Docker; existing stack: Plex, Radarr, Sonarr, SabNZBD
- **Network:** Ubiquiti LAN with Tailscale for remote access; app must be reachable via Tailscale IP
- **Integration targets:** Plex API (watch history + webhooks), Radarr API (movie requests), Sonarr API (TV requests), TMDB API (filmography)
- **Primary use case:** On-the-couch media selection — UI should be responsive and easy to navigate from a TV/tablet
- **Rotten Tomatoes:** No public API; displaying RT scores requires scraping or a third-party aggregator — to be resolved during planning

## Constraints

- **Deployment:** Docker on Synology NAS — resource-constrained; avoid bloated runtimes
- **Network:** Must be accessible via Tailscale hostname/IP; no public exposure required
- **API limits:** TMDB free tier has rate limits — cache fetched data aggressively
- **Stack compatibility:** Must integrate with existing Radarr/Sonarr/Plex without modifying them

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| TMDB primary + IMDB fallback | TMDB has reliable free API; IMDB scraping fragile but fills gaps | — Pending |
| PostgreSQL over SQLite | Synology has headroom; Postgres handles filtering/sorting better at scale | — Pending |
| Plex webhook + manual fallback | Webhook automates game loop; manual mark covers edge cases | — Pending |
| Radarr for movies, Sonarr for TV | Standard arr-stack split; already running both | — Pending |
| RT ratings source | No public API — scraping vs third-party aggregator TBD | — Pending |

## Current Milestone: v1.0 CinemaChain

**Goal:** Build the full initial app — data layer, Movie Game mode, Query mode, and Docker infrastructure.

**Target features:**
- TMDB + PostgreSQL + Plex data layer with watch sync
- Movie Game mode with actor-chain session state
- Query mode with actor/title/genre search
- Docker Compose deployment for Synology NAS

---
*Last updated: 2026-03-22 after Phase 06 complete — Settings/Onboarding, movie splash dialog, session management dropdown, chain history search, TMDB links, info density improvements*
