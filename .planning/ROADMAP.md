# ROADMAP — CinemaChain

---

## Completed Milestones

- **v1.0** (2026-03-14 → 2026-03-22) — Full Movie Game delivered: actor-chain session loop, multi-session support, TMDB cache, MDBList RT scores, Settings page, production deployment hardened for public use. 13 phases, 122 plans, 457 commits. [Full details →](milestones/v1.0-ROADMAP.md)
- **v2.0** (2026-03-22 → 2026-05-29) — Beyond the game loop: Query Mode for direct discovery, Save + Shortlist, Watched History, multi-source ratings (IMDB/RT/Metacritic/Letterboxd/MDB Avg), TMDB suggested-movies, mobile redesign, log/key security hardening, filmography freshness gap closed (Meryl/DWP2). 14 active phases, 50 plans. [Full details →](milestones/v2.0-ROADMAP.md)

---

## v2.0 Post-Release Patches

Bug-fix and data-quality patches shipping under the v2.0 lineage. Each patch tags a new semver point release. Substantive new features wait for v2.1.

| Patch | Phase | Description | Status |
|-------|-------|-------------|--------|
| v2.0.1 | Phase 22 | Filmography Refresh Gap — newly-released movies surface for cached actors | Shipped 2026-05-29 |
| v2.0.2 | Phase 23 | Smart Metadata Backfill — stop wasteful nightly re-tries on confirmed-empty fields; align DB Health audit semantics with sentinel pattern | Shipped 2026-05-29 |

### Phase 23: Smart Metadata Backfill
**Goal:** Stop the nightly cache job from wastefully re-querying TMDB/MDBList for movies where the data ceiling has already been reached, AND fix the DB Health audit so it shows the actually-addressable gap (not the sentinel-zero false positives). Net effect: `Missing MPAA` and `Missing RT score` stats drop from ~30k each to a few hundred genuinely addressable rows that close within 1-2 nightly cycles.
**Depends on:** Phase 22
**Requirements:** HEALTH-01, HEALTH-02, HEALTH-03
**Plans:** TBD (set during /gsd:plan-phase)
**Success Criteria** (what must be TRUE):
  1. `_backfill_mpaa_pass` no longer re-queries TMDB for movies where a prior attempt returned no US certification (positive sentinel pattern: write `"NR"`, then `WHERE mpaa_rating IS NULL` query)
  2. Migration 0020 promotes existing `mpaa_rating = ''` rows to `mpaa_rating = 'NR'` so the new query semantics take immediate effect
  3. DB Health audit endpoint reports accurate "addressable gap" counts — sentinel-zero rows (RT `0`, IMDB rating `0.0`, IMDB ID `""`, MPAA `"NR"`) excluded from `missing X` stats; optionally surfaced as a separate `confirmed N/A` column
  4. Nightly MDBList pass clears the 1,459 never-fetched movies within 1-2 nights at paid-tier rate
  5. No regression in user-facing rendering — frontend handles `"NR"` MPAA exactly as it currently handles `""` (per Phase 8 "explicit N/A")

---

## v2.1 Backlog Candidates

Surfaced during v2.0 close-out — to be triaged when v2.1 requirements are gathered:

- **Plex polling sync** — re-add automatic watched-detection via polling (Plex webhook was removed in v1)
- **Stats dashboard** — longest chain, most-picked actors, total runtime, chains over time
- **Alternative chain types** — director / writer / composer chains (TMDB data already available)
- **Genre-constrained game mode** — lock a session to one genre (e.g., horror-only)
- **Retroactive phase assignment** — formalize the two post-Phase-21 ad-hoc commits (e2a8695, e5d54c7)
- **Actor IMDB links** — IMDB-01 partial in v2.0; backfill `imdb_person_id` if value clarifies
- **Discord download notifications** — NOTIF-01 from v1 backlog
- **Dead-end recovery suggestions** — instead of "you're stuck", surface nearby actors

---

## Backlog (999.x — parked items not yet promoted)

- **999.1: Backend Logging Hardening** — original Phase 18 numbering preserved; work delivered as part of v2.0 Phase 18. Directory retained for the few unstamped logging touchups that may surface.

---

*ROADMAP collapsed to milestone summaries on 2026-05-29 after v2.0 close-out. Full v1.0 and v2.0 phase details live in `.planning/milestones/`.*
