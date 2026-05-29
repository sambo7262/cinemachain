# Requirements: CinemaChain v2.0.x Patches

**Lineage:** v2.0 post-release patches (semver point releases, not a new milestone).
**v2.0.1 — Phase 22 STALE-01..03** — Filmography Refresh Gap (complete; archived to `milestones/v2.0-REQUIREMENTS.md`).
**v2.0.2 — Phase 23 HEALTH-01..03** — Smart Metadata Backfill (active).

---

## v2.0.2 — Phase 23: Smart Metadata Backfill (HEALTH)

- [ ] **HEALTH-01**: `_backfill_mpaa_pass` writes positive sentinel `"NR"` instead of empty string `""` when TMDB returns no US certification; backfill query targets `mpaa_rating IS NULL` only (no more retries on confirmed-no-data rows). Migration 0020 promotes existing `''` rows to `'NR'`. Nightly TMDB call count for MPAA backfill drops to the size of the truly-NULL set (expected: a few hundred max, not 33k).
- [ ] **HEALTH-02**: DB Health audit endpoint (Phase 17) reports "addressable gap" counts using sentinel-aware semantics — `Missing MPAA` excludes `'NR'`, `Missing RT score` excludes `0`, `Missing IMDB ID` excludes `""`, `Missing IMDB rating` excludes `0.0`. Either drop the sentinel-counting OR add a parallel "Confirmed N/A" column showing the breakdown. Dashboard reads honestly post-deploy.
- [ ] **HEALTH-03**: Live NAS verification — deploy via `make rebuild` + `alembic upgrade head`, observe within ≤2 nightly cycles that: (a) `_backfill_mpaa_pass` log entry shows ~few hundred rows processed (not 25k); (b) DB Health view shows realistic addressable gaps for MPAA + RT; (c) the 1,459 never-fetched MDBList movies are processed and gap closes; (d) no regression in frontend MPAA rendering — `"NR"` displays identically to current `""` handling.

---

*See `.planning/milestones/v2.0-REQUIREMENTS.md` for the full v2.0 requirement archive.*
