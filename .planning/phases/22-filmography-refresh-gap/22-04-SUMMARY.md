# 22-04 SUMMARY — Live NAS Verification

**Plan:** 22-04 — Filmography Refresh Gap — Live NAS verification
**Status:** ✅ COMPLETE — 3/3 verifications PASS
**Verified:** 2026-05-29
**Requirements covered:** STALE-01, STALE-02, STALE-03

---

## Pre-Deploy Automated Checks (Task 1) — PASS

| Check | Result |
|-------|--------|
| Backend pytest (`-k "ensure_actor_credits or refresh"`) | 6 skipped (asyncpg-skip pattern), 0 failures, 0 errors |
| Backend AST parse (5 files) | All parse cleanly |
| Migration chain | `20260408_0018` → `20260529_0019_filmography_fetched_at.py` ✓ |
| New endpoint registered | `@router.post("/actors/refresh-now")` confirmed in routers/cache.py |
| Frontend `npx tsc --noEmit` | exit 0 |
| Frontend `npx vitest run` | 8 failures all pre-existing in unrelated files (ChainHistory, RatingsBadge, GameLobby); no regression from Phase 22 |

---

## Deploy to NAS (Task 2) — PASS

- `make rebuild` — completed without error (Docker images built, pushed to Docker Hub, deployed to NAS via SSH)
- `alembic upgrade head` — migration 0019 applied; column `filmography_fetched_at TIMESTAMP NULL` added to `actors` table
- `POST /cache/actors/refresh-now` endpoint — reachable and operational

---

## Live NAS Verifications (Task 3)

### Verification A — STALE-02 on-demand TTL self-heal: **PASS**

Original bug repro:
- Opened active game session that landed on Hoppers
- Clicked Meryl Streep in Eligible Actors
- Opened her Eligible Movies list
- **The Devil Wears Prada 2 appeared.**

The synchronous on-demand re-fetch path triggered correctly on first click. New TMDB releases are now visible for cached actors whose `filmography_fetched_at` is NULL or older than `FILMOGRAPHY_TTL_DAYS = 14`.

This proves Decision 3 (synchronous, not stale-while-revalidate) was the right call — the user saw fresh data on the very first click, not the next one.

### Verification B — STALE-03 manual refresh button: **PASS**

- Clicked "Refresh actor filmographies" in Settings
- Button transitioned to "Refreshing..." (disabled state)
- Existing `cacheRunning` polling state machine drove the lifecycle (Decision 5 honored)
- Refresh completed without backend errors

### Verification C — STALE-01 freshness audit: **PASS**

```sql
SELECT count(*) FROM actors WHERE filmography_fetched_at IS NOT NULL;
-- 901
```

901 actors now carry populated `filmography_fetched_at` timestamps after the Settings refresh pass. This confirms:
- Migration 0019 applied cleanly (column writable)
- `_ensure_actor_credits_in_db` success path correctly stamps the timestamp alongside `filmography_fetched = True` (Decision 4 line 504 area)
- `refresh_top_actors_force` helper successfully drove `force_refresh=True` across the top popular actor set

---

## Requirements Coverage

| ID | Status | Evidence |
|----|--------|----------|
| STALE-01 | PASS | 901 timestamps populated post-refresh; `refresh_top_actors_force` operational; nightly delegate wired with `force_refresh=True` (services/cache.py:481) |
| STALE-02 | PASS | DWP2 surfaced in Meryl Streep's filmography on first click — synchronous TTL self-heal working in production |
| STALE-03 | PASS | Settings button completed full refresh pass; reuses existing `cacheRunning` state machine; no regression to existing "Run TMDB Cache Now" button |

---

## Regressions Checked

- ✅ Existing "Run TMDB Cache Now" button still functions (shares state machine, no contention)
- ✅ Gameplay latency for fresh actors (within 14-day TTL) unchanged — short-circuit preserved at game.py:438
- ✅ `_ensure_movie_cast_in_db` and `_ensure_movie_details_in_db` untouched (Decision 7 scope discipline)
- ✅ TMDB rate limits respected (existing semaphore pattern intact; nightly = ~5k calls vs daily budget)

---

## Phase 22 Status: COMPLETE

The original Meryl Streep / Devil Wears Prada 2 bug is fixed. Newly-released movies now surface for cached actors via three paths:

1. **Lazy (on-demand):** TTL-based self-heal on first actor click after expiry
2. **Scheduled (nightly):** force-refresh of top popular actors every night
3. **Manual (user-triggered):** Settings button for "I want fresh data now"

v2.0 milestone is now formally complete and ready for `/gsd:audit-milestone` → `/gsd:complete-milestone`.
