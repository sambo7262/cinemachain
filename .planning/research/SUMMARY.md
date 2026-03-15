# Project Research Summary

**Project:** CinemaChain
**Domain:** Home media companion app — Plex/arr-stack integration with game mechanics
**Researched:** 2026-03-14
**Confidence:** HIGH (core patterns), MEDIUM (version pinning for less-active libs)

---

## Executive Summary

CinemaChain sits in a well-documented ecosystem (FastAPI + Plex + TMDB + arr-stack), but the Movie Game mechanic is genuinely novel — no existing tool surfaces "actors from your watch history with unwatched requestable filmography." The technical path is clear and well-understood; the risk is integration fragility, not architecture complexity.

The recommended stack is Python 3.12 + FastAPI + PostgreSQL + a React/Vue frontend, all in Docker Compose with a Tailscale sidecar for remote access. The key integration challenges are: (1) Plex webhooks require multipart parsing — not JSON — which trips up nearly everyone; (2) game session state must be persisted to PostgreSQL from day one, not in-memory, because NAS containers restart frequently; and (3) TMDB cache must be built before the game is usable.

The biggest strategic insight from research: **webhooks are a v1.x feature, not v1**. The game works perfectly well with a manual "I just finished watching" trigger. Plex webhooks require Plex Pass and an always-on endpoint, and have confirmed reliability bugs. Build the core game loop first, wire up auto-advance later.

---

## Key Findings

### Recommended Stack

Python 3.12 + FastAPI is the dominant 2025 choice for this domain (38% Python dev adoption, async-native, handles multipart POSTs natively). **One notable discrepancy:** the Stack research recommends SQLite for simplicity, while the Architecture research used PostgreSQL for its richer query support on game session joins. For CinemaChain's complex session-state queries (eligibility filtering, actor exclusion joins), **PostgreSQL is the right call** — the added complexity is justified by the schema.

**Core technologies:**
- **Python 3.12 + FastAPI 0.115.x**: Runtime + HTTP server — async-native, handles multipart webhooks
- **PostgreSQL 16-alpine**: Persistence — game sessions, filmography cache, watch history
- **PlexAPI 4.18.0** (`pip install plexapi[alert]`): Plex watch history + webhook support
- **tmdbv3api 1.9.0**: TMDB filmography data (actors, credits, movie metadata)
- **pyarr 5.2.0** or direct httpx: Radarr/Sonarr API integration
- **requests-cache 1.3.0**: TMDB HTTP-level caching (SQLite backend, drop-in for requests.Session)
- **Tailscale sidecar** (`TS_USERSPACE=true`): Remote access — **mandatory flag** on Synology DSM

> **Critical:** `TS_USERSPACE=true` is required on Synology — the kernel TUN device is unavailable in DSM containers. Without it, the Tailscale tunnel is never created.

### Expected Features

**Must have (table stakes):**
- Plex watch history read — the entire game depends on this
- TMDB cast/filmography fetch — core data for both modes
- Radarr request submission — the payoff action; without it, app is read-only
- Session actor tracking (no repeats) — core game rule, must be in v1
- Filter: unwatched only toggle — CinemaChain's primary value proposition
- Sort by genre and rating — required for navigating 50+ movies in a panel

**Should have (differentiators — v1.x):**
- Plex webhook receiver (auto-advance game on completion) — v1.x, not v1; manual trigger first
- Query Mode (actor/movie/genre search) — second mode; add after game loop is proven
- Sonarr integration for TV shows — add once movie game is working
- "Already in Radarr queue" status indicator
- Poster grid / list view toggle

**Defer (v2+):**
- Sort filmography by "most connectable actors" (graph traversal)
- Cross-session chain history / saved chains
- Genre-constrained game mode
- Discord webhook on download complete

**Anti-features to avoid:**
- Recommendation algorithm — the game IS the recommendation engine; ML recs erode trust
- Multi-user auth — single user, Overseerr already handles multi-user
- Push notifications — Radarr/Sonarr already do this; adds mobile infrastructure complexity

### Architecture Approach

Three-tier Dockerized architecture: FastAPI backend (service layer per external API), PostgreSQL for all state, and a React/Vue frontend. The key pattern is **cache-first TMDB access** — all filmography queries check PostgreSQL before hitting TMDB, with TTLs of 3–14 days depending on data volatility. Game session state is fully persisted in four tables: `game_sessions`, `session_used_actors`, `session_movie_chain`, and the filmography cache tables.

**Major components:**
1. **FastAPI Backend** — REST API, Plex webhook receiver (`/webhook/plex`), service orchestration
2. **TMDBService** — Cache-first filmography fetcher; `append_to_response=credits` reduces calls
3. **GameService** — Session state machine; actor eligibility queries; `SELECT ... FOR UPDATE` locking
4. **RadarrService / SonarrService** — httpx clients; treat 400 "already exists" as success
5. **PlexService** — Multipart webhook parser; history sync/polling fallback
6. **PostgreSQL** — Game sessions, used actors, movie chain, filmography cache, watch history

### Critical Pitfalls

1. **Plex webhooks are `multipart/form-data`, not JSON** — Standard JSON parsers fail silently. JSON payload is buried in a `payload` field inside the multipart body. Install `python-multipart`; use `Form(...)` in FastAPI. A dedicated proxy project exists solely because this trips up everyone.

2. **TMDB rate limiting breaks game traversal** — 50 req/sec per IP. A cold-cache 5-step chain fans out across cast members and exhausts the limit instantly. Solution: eager pre-caching when movies are added; `asyncio.Semaphore` around concurrent TMDB calls; exponential backoff on 429.

3. **`media.scrobble` is unreliable and misses manual "mark watched"** — Fires at 90% playback only, not on manual Plex UI actions. Has confirmed delivery bugs requiring Plex server restarts. Must implement polling fallback against Plex library API to reconcile watch state.

4. **Game session state wiped on NAS restart** — NAS containers restart far more frequently than cloud VMs (OOM kills, DSM updates, power events). Must persist all session state to PostgreSQL from day one. Use `SELECT ... FOR UPDATE` to prevent race conditions on actor selection.

5. **Radarr/Sonarr return 400/422 on duplicate — treat as success** — "Already added" is not an error from the user's perspective. Check existence with `GET /api/v3/movie?tmdbId=` before adding; treat 400 with "already added" body as success.

6. **Synology PUID/PGID permission failures** — DSM uses POSIX ACLs that Docker ignores. Every container needs explicit PUID/PGID matching a NAS user. PostgreSQL host port must not be 5432 (reserved on Synology — use 5433).

7. **No memory limits → OOM kills the NAS stack** — Set `mem_limit` on every container. Recommended: 512m for backend, 256m for PostgreSQL on a typical NAS. Use `restart: unless-stopped` not `always`.

8. **Sonarr season numbering (TVDB vs. Scene)** — Never assume TMDB season numbers == Sonarr season numbers. Always use Sonarr-internal series/season IDs from `GET /api/v3/series`.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Infrastructure Foundation
**Rationale:** Synology Docker permissions, memory limits, and networking must be solved before any code runs. Get this wrong and every phase is blocked.
**Delivers:** Working Docker Compose on Synology — PostgreSQL, backend skeleton, Tailscale sidecar
**Avoids:** PUID/PGID permission failures (Pitfall 5), OOM crashes (Pitfall 7), Tailscale config failure
**Research flag:** Standard patterns — no phase-level research needed

### Phase 2: Data Foundation (TMDB + Plex History)
**Rationale:** Both game modes depend on filmography data and watch history. The cache layer must exist before the game can be built. Pre-warming the cache at this phase prevents TMDB rate limiting during gameplay.
**Delivers:** TMDB filmography fetch + PostgreSQL cache; Plex watch history sync (polling, not webhooks)
**Uses:** tmdbv3api, requests-cache, PlexAPI, `append_to_response=credits` pattern
**Implements:** Filmography cache tables, watch_history table
**Avoids:** TMDB rate limiting on game traversal (Pitfall 2)

### Phase 3: Movie Game Core
**Rationale:** The core value proposition. Game session state must be DB-backed from day one (not in-memory). Build the full actor-chain loop before adding any bells and whistles.
**Delivers:** Session creation, eligible-actors panel, eligible-movies panel, actor selection with no-repeat enforcement, movie selection → Radarr request
**Implements:** `game_sessions`, `session_used_actors`, `session_movie_chain` tables; GameService; `SELECT ... FOR UPDATE` locking
**Avoids:** Session state corruption (Pitfall 7), Radarr duplicate errors (Pitfall 4)

### Phase 4: Frontend — Game Mode UI
**Rationale:** The side-by-side actor + movie panels with sort/filter controls are the defining UX. Implement against the working backend from Phase 3.
**Delivers:** Side-by-side panels, sort by genre/rating, watched toggle, poster/card display
**Research flag:** Standard React/Vue patterns — no phase-level research needed

### Phase 5: Plex Webhook Integration
**Rationale:** Auto-advance game on movie completion. Deferred from v1 because (a) manual trigger works fine and (b) webhook reliability requires careful handling. Do this after the manual flow is proven.
**Delivers:** `POST /webhook/plex` endpoint; `media.scrobble` parsing; auto-creation of game session; account-ID filtering to prevent multi-user contamination; polling fallback
**Avoids:** Multipart parsing failure (Pitfall 1), scrobble unreliability (Pitfall 3)
**Research flag:** Needs careful testing with a real Plex server — mock POST testing will not catch the multipart format issue

### Phase 6: Query Mode
**Rationale:** Second stated mode. Add after the game mode is stable. Simpler than game mode — direct TMDB search → display → request flow.
**Delivers:** Search by actor/movie/genre, filmography results, Radarr + Sonarr request submission, TV show support
**Avoids:** Sonarr season numbering mismatch (Pitfall 8) — use Sonarr-internal IDs

### Phase 7: Polish + Hardening
**Rationale:** UX quality-of-life + production reliability. Add after all functional phases are complete.
**Delivers:** Poster grid / list toggle, Radarr queue status indicator, memory limit tuning, "looks done but isn't" checklist verification
**Research flag:** Run the "Looks Done But Isn't" checklist from PITFALLS.md as acceptance criteria

### Phase Ordering Rationale

- **Infrastructure first** — Synology permission issues are blockers that manifest in every subsequent phase if not solved upfront
- **Data before game** — Cold TMDB cache makes the game feel broken; pre-warm before building game UI
- **Game before webhook** — Manual trigger validates the full loop without webhook reliability uncertainty
- **Query after game** — It's simpler and shares all the same services; add once core is proven
- **Frontend and backend in tandem** — Phase 4 frontend follows Phase 3 backend directly; don't let the gap grow

### Research Flags

Phases needing deeper research during planning:
- **Phase 5 (Plex Webhooks):** Test with a real Plex server early — the multipart format issue is invisible in unit tests
- **Phase 6 (Sonarr TV):** Verify Sonarr API version compatibility with your installed version before writing integration code

Phases with standard patterns (skip `research-phase`):
- **Phase 1 (Infrastructure):** Synology Docker Compose is well-documented (TRaSH Guides)
- **Phase 2 (TMDB cache):** Cache-aside pattern is standard; TMDB endpoints are stable
- **Phase 4 (Frontend):** Standard React/Vue SPA patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core libs verified with official docs and PyPI; Tailscale sidecar confirmed with March 2026 source |
| Features | HIGH | Overseerr/Ombi/Petio analyzed; gap confirmed; TMDB field availability verified |
| Architecture | HIGH | Plex webhook payload structure confirmed with official docs + real-world scrobbler projects |
| Pitfalls | HIGH | Multipart pitfall has a dedicated proxy project as evidence; all major pitfalls confirmed with GitHub issues or official forum threads |

**Overall confidence:** HIGH

### Gaps to Address

- **SQLite vs PostgreSQL:** Stack agent recommends SQLite; Architecture agent used PostgreSQL. Decision: PostgreSQL wins for the complex game session join queries. Flag as resolved Key Decision.
- **Rotten Tomatoes ratings:** No public API. Options: (a) use TMDB vote_average + vote_count as proxy, (b) scrape RT (fragile), (c) integrate OMDb API (has RT scores via `tomatoes=true` param, free tier 1000 req/day). OMDb is the cleanest path — resolve during Phase 4 planning.
- **pyarr currency:** Last released July 2023. Verify against your installed Radarr/Sonarr version during Phase 3 planning; fall back to direct httpx if needed.
- **Plex Pass requirement for webhooks:** If you don't have Plex Pass, Phase 5 is manual-only. Manual trigger is fully functional — webhooks are enhancement, not dependency.

---

## Sources

### Primary (HIGH confidence)
- Plex Webhooks Official Documentation — multipart format, event types, Plex Pass requirement
- TMDB API Official Docs — rate limits, caching policy, endpoint reference
- Radarr OpenAPI Spec + Servarr Wiki — request flow, duplicate handling, quality profiles
- PlexAPI Official Docs (python-plexapi.readthedocs.io) — watch history methods, webhook alert listener
- TRaSH Guides: Synology Setup — PUID/PGID, volume paths, arr-stack file structure
- Tailscale Docker Docs + March 2026 Synology-specific guide — TS_USERSPACE requirement

### Secondary (MEDIUM confidence)
- Overseerr/Seerr GitHub — architecture reference for service patterns and Radarr integration flow
- FastAPI + Async SQLAlchemy setup guide — DB session factory, health check pattern
- Synology community forums (Marius Hosting, DrFrankenstein) — NAS-specific Docker permission guides
- plex-webhook-proxy GitHub — evidence that multipart parsing is a widespread known issue

### Tertiary (LOW confidence, needs validation)
- OMDb API for RT scores via `tomatoes=true` — noted in gaps, needs API key testing
- pyarr v5.2.0 against Radarr v6+ — library is stable but last release was July 2023

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
