# ROADMAP — CinemaChain

---

## Completed Milestones

- **v1.0** (2026-03-14 → 2026-03-22) — Full Movie Game delivered: actor-chain session loop, multi-session support, TMDB cache, MDBList RT scores, Settings page, production deployment hardened for public use. 13 phases, 122 plans, 457 commits. [Full details →](milestones/v1.0-ROADMAP.md)
- **v2.0** (2026-03-22 → 2026-05-29) — Beyond the game loop: Query Mode for direct discovery, Save + Shortlist, Watched History, multi-source ratings (IMDB/RT/Metacritic/Letterboxd/MDB Avg), TMDB suggested-movies, mobile redesign, log/key security hardening, filmography freshness gap closed (Meryl/DWP2). 14 active phases, 50 plans. [Full details →](milestones/v2.0-ROADMAP.md)

---

## Current Milestone

*(none — v2.0 just shipped. Run `/gsd:new-milestone` to begin v2.1 planning.)*

---

## v2.1 Backlog Candidates

Surfaced during v2.0 close-out — to be triaged when v2.1 requirements are gathered:

- **Plex polling sync** — re-add automatic watched-detection via polling (Plex webhook was removed in v1)
- **Stats dashboard** — longest chain, most-picked actors, total runtime, chains over time
- **Alternative chain types** — director / writer / composer chains (TMDB data already available)
- **Genre-constrained game mode** — lock a session to one genre (e.g., horror-only)
- **DB metadata scrub audit** — surface movies missing rating/overview; provide a re-enrichment mechanism
- **Retroactive phase assignment** — formalize the two post-Phase-21 ad-hoc commits (e2a8695, e5d54c7)
- **Actor IMDB links** — IMDB-01 partial in v2.0; backfill `imdb_person_id` if value clarifies
- **Discord download notifications** — NOTIF-01 from v1 backlog
- **Dead-end recovery suggestions** — instead of "you're stuck", surface nearby actors

---

## Backlog (999.x — parked items not yet promoted)

- **999.1: Backend Logging Hardening** — original Phase 18 numbering preserved; work delivered as part of v2.0 Phase 18. Directory retained for the few unstamped logging touchups that may surface.

---

*ROADMAP collapsed to milestone summaries on 2026-05-29 after v2.0 close-out. Full v1.0 and v2.0 phase details live in `.planning/milestones/`.*
