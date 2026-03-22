---
phase: 07-production-deployment
plan: 01
subsystem: infra
tags: [docker, compose, settings, pydantic, fastapi, postgres]

requires:
  - phase: 06.1-bug-fixes
    provides: working backend/frontend with MDBList RT scores, settings nav fixed

provides:
  - Clean settings.py with no required Plex/Sonarr env vars
  - Scrubbed .env.example with placeholder values and all tunable params documented
  - Generic compose.yaml deployable on any Docker host (DATA_DIR volumes, cinemachain-net)
  - TMDB_CACHE_TOP_ACTORS exposed as configurable setting (was hardcoded 1500 in cache.py)

affects:
  - 07-02-PLAN (next plan in production deployment phase)
  - anyone deploying CinemaChain from public repo

tech-stack:
  added: [math (stdlib, for ceil calculation in cache.py)]
  patterns:
    - "nightly_cache_job receives top_actors param from main.py settings, parallel to top_n pattern"
    - "compose.yaml uses ${VAR:-default} syntax for all optional env vars"
    - "DATA_DIR variable for all volume bind-mounts — single override point for NAS paths"

key-files:
  created: []
  modified:
    - backend/app/settings.py
    - backend/app/services/settings_service.py
    - backend/app/routers/settings.py
    - backend/app/services/cache.py
    - backend/app/main.py
    - compose.yaml
    - .env.example
    - .gitignore

key-decisions:
  - "Keep plex.py service file as dead code — not called from main.py, preserved for potential v2 Plex integration"
  - "Add tmdb_cache_top_actors to _ENV_KEYS_TO_MIGRATE so existing deployments can migrate from .env to DB settings"
  - "Use math.ceil(top_actors / 20) so actor page count is always sufficient regardless of non-round values"
  - "compose.yaml network cinemachain-net driver:bridge replaces external synobridge — works on all Docker hosts"

patterns-established:
  - "Function params pattern: nightly_cache_job(tmdb, top_n, top_actors) — settings wired in main.py, not imported in cache.py"
  - ".env.example uses placeholder strings like your_tmdb_api_key_here — not empty, not real"

requirements-completed: [PROD-01, PROD-03]

duration: 15min
completed: 2026-03-22
---

# Phase 07 Plan 01: Settings Cleanup and Deployment Genericization Summary

**Plex/Sonarr dead code removed from settings/router/migration; .env.example scrubbed of all real credentials; TMDB_CACHE_TOP_ACTORS promoted from hardcoded 1500 to configurable setting; compose.yaml genericized with DATA_DIR volumes and cinemachain-net bridge network**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-22T18:05:00Z
- **Completed:** 2026-03-22T18:20:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Removed plex_token, plex_url, sonarr_url, sonarr_api_key from Settings class, _ENV_KEYS_TO_MIGRATE tuple, SettingsResponse, and SettingsUpdateRequest — app no longer requires Plex/Sonarr env vars to start
- Scrubbed .env.example of all real credentials (TMDB API key, Plex token, LAN IPs, Radarr/Sonarr API keys) and replaced with placeholder values; added DATA_DIR, PUID/PGID, all cache parameters including the previously undocumented TMDB_CACHE_TOP_ACTORS
- Promoted TMDB_CACHE_TOP_ACTORS from hardcoded 1500 in cache.py to configurable setting wired through settings.py, main.py kwargs, and nightly_cache_job function signature
- compose.yaml now works on any Docker host: DATA_DIR variable for all volume paths (default ./data), compose-managed cinemachain-net bridge network replacing external synobridge, all dead Plex/Sonarr env vars removed, all tunable params added with defaults

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead Plex/Sonarr code, expose TMDB_CACHE_TOP_ACTORS, scrub secrets** - `7c4eb19` (feat)
2. **Task 2: Genericize compose.yaml for any Docker host** - `666db1b` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `backend/app/settings.py` - Removed plex_token, plex_url, sonarr_url, sonarr_api_key; added tmdb_cache_top_actors: int = 1500
- `backend/app/services/settings_service.py` - Removed 4 dead keys from _ENV_KEYS_TO_MIGRATE; added tmdb_cache_top_actors
- `backend/app/routers/settings.py` - Removed 4 dead fields from SettingsResponse and SettingsUpdateRequest; added tmdb_cache_top_actors to both
- `backend/app/services/cache.py` - Added math import; replaced hardcoded range(1, 76) with math.ceil(top_actors / 20); added top_actors param to nightly_cache_job
- `backend/app/main.py` - Pass top_actors=settings.tmdb_cache_top_actors in scheduler kwargs and startup task
- `compose.yaml` - Genericized volumes (DATA_DIR), network (cinemachain-net), removed dead vars, added all tunable params
- `.env.example` - Complete rewrite: scrubbed all real credentials, added DATA_DIR/PUID/PGID/TMDB_CACHE_TOP_ACTORS/SETTINGS_ENCRYPTION_KEY documentation
- `.gitignore` - Added .env.local and .env.*.local

## Decisions Made

- Kept plex.py service file as dead code — it is not called from main.py and has no runtime impact; preserving for potential v2 Plex reactivation
- Added tmdb_cache_top_actors to _ENV_KEYS_TO_MIGRATE so first-startup migration from .env to DB captures the new setting
- math.ceil used so actor page count is always sufficient for non-round top_actors values

## Deviations from Plan

**1. [Rule 2 - Missing Critical] Added top_actors param wiring in main.py**

- **Found during:** Task 1 (cache.py changes)
- **Issue:** Plan specified adding top_actors param to nightly_cache_job but did not explicitly mention updating main.py scheduler kwargs and startup task call
- **Fix:** Updated both scheduler `kwargs` dict and `asyncio.create_task()` call in main.py to pass `top_actors=settings.tmdb_cache_top_actors`
- **Files modified:** backend/app/main.py
- **Verification:** grep confirms both call sites pass top_actors
- **Committed in:** 7c4eb19 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical wiring)
**Impact on plan:** Essential for the setting to have any effect. No scope creep.

## Issues Encountered

None - all checks passed on first attempt.

## User Setup Required

None - this plan contains no external service configuration. Users who want to deploy will copy .env.example to .env and fill in values.

## Next Phase Readiness

- Settings are clean; app can start without Plex/Sonarr env vars
- compose.yaml works on any Docker host with ./data as default volume location
- .env.example is safe for public repo — no real credentials
- Ready for 07-02 (next plan in production deployment phase)

---
*Phase: 07-production-deployment*
*Completed: 2026-03-22*
