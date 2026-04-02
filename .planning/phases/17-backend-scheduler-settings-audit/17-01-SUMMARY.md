---
plan: 17-01
status: complete
completed_at: 2026-04-01T00:00:00Z
---
# 17-01 Summary — DB Pool + IMDB Links

## What was built
- DB engine pool_size=10, max_overflow=5, pool_pre_ping=True, pool_recycle=1800, pool_timeout=60, command_timeout=60
- StepResponse.movie_imdb_id field added (populated via _enrich_steps_thumbnails on full-enrich paths)
- _enrich_steps_thumbnails returns 3-tuple (poster_map, profile_map, imdb_map)
- _build_session_response wired with imdb_map parameter
- All 5 call-sites of _enrich_steps_thumbnails updated to unpack and pass imdb_map (plan identified 4; one additional call-site at line ~2231 was also updated)

## Key decisions
- imdb_map=None on lightweight list endpoints (correct — TMDB fallback in ChainHistory.tsx)
- 5th call-site (CSV export / session reload path) updated as deviation Rule 2 — correctness requires all full-enrich paths return imdb_map

## Tests
- All pytest tests pass (26 passed, 84 skipped)
- 2 pre-existing failures in test_cache.py and test_mdblist.py confirmed unrelated to this plan's changes

## Deviations from Plan
### Auto-fixed Issues

**1. [Rule 2 - Missing Coverage] 5th _enrich_steps_thumbnails call-site**
- **Found during:** Task 2
- **Issue:** Plan identified 4 call-sites needing update; grep revealed a 5th at line ~2231 (session reload in archive/CSV area)
- **Fix:** Updated the 5th call-site to unpack 3-tuple and pass imdb_map=imdb_map to _build_session_response
- **Files modified:** backend/app/routers/game.py

## Self-Check: PASSED
