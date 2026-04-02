---
phase: 10
slug: query-mode
status: approved
tested_at: 2026-03-31
tested_by: user (browser + NAS dev environment)
---

# Phase 10 — UAT Results

## Summary

**Verdict: APPROVED** — All 8 scenarios pass. One known issue (MPAA blank vs NULL in DB) deferred to a future metadata quality phase.

---

## Test Results

| # | Scenario | Requirement | Result | Notes |
|---|----------|-------------|--------|-------|
| 1 | Landing state — genre chips grid appears at /search | QMODE-03 | ✅ PASS | |
| 2 | Genre browse — Sci-Fi chip loads ~100 movies | QMODE-03 | ✅ PASS | Confirmed TMDB Discover live call; bumped to 5 pages (~100) |
| 3 | Title search — "inception" returns enriched results | QMODE-01 | ✅ PASS | MPAA null — deferred (DB blank vs NULL issue, not code bug) |
| 4 | Actor search — "a: christopher nolan" returns filmography | QMODE-02 | ✅ PASS | Hint text updated to say "actor"; backend unchanged (cast+crew) |
| 5 | Sort by year + Unwatched Only toggle | QMODE-04, QMODE-05 | ✅ PASS | |
| 6 | Radarr request from splash — queued / already_in_radarr states | QMODE-06 | ✅ PASS | |
| 7 | Watch Online — "Marked as Watched" stays until dialog close | QMODE-06 | ✅ PASS | Behavior updated: no 2s auto-reset; clears on dialog close |
| 8 | Dialog close resets button state | QMODE-06 | ✅ PASS | |

---

## Issues Found + Resolutions

### Issue A — MPAA not appearing in title search results
- **Root cause:** `mpaa_rating` stored as `""` (empty string) in DB for many movies, not `NULL` — enrichment guard `WHERE mpaa_rating IS NULL` skips them
- **Resolution:** Deferred to future metadata quality phase (DB scrub + re-enrichment pass). Same root cause as tracked DB missing ratings/overviews issue.
- **Impact:** Low — MPAA visible for newly-fetched movies; blank for existing DB entries

### Issue B — `a:` prefix hint implied actor + director
- **Root cause:** Placeholder text said "actor or director"
- **Resolution:** Updated hint to "actor" for `a:` and "director" for `d:`. Backend behavior unchanged.

### Issue C — "Marked as Watched" auto-reset after 2s
- **Root cause:** Plan 10-04 specified 2s timeout matching Radarr behavior
- **Resolution:** Watch Online success state now persists until dialog close (no auto-reset). Radarr "Added" state keeps 2s reset.

### Issue D — Genre browse capped at ~60 movies
- **Root cause:** Initial plan specified 3 pages × 20
- **Resolution:** Bumped to 5 pages × 20 = ~100 movies

---

## Deferred Items

| Item | Reason | Phase |
|------|--------|-------|
| MPAA blank vs NULL enrichment | DB data quality issue — needs scrub + re-enrichment pass | Future metadata quality phase |

---

## Phase Sign-Off

All QMODE requirements verified:

- ✅ QMODE-01: Title search returns enriched movie list
- ✅ QMODE-02: Actor name search returns filmography
- ✅ QMODE-03: Genre browse returns top popular movies
- ✅ QMODE-04: Sort by rating/year/RT/runtime with null stability
- ✅ QMODE-05: Unwatched Only toggle works
- ✅ QMODE-06: Radarr request + Watch Online with correct confirmation states

**Phase 10: COMPLETE**
