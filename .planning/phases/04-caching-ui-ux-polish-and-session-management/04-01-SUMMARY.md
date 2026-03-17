---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "01"
subsystem: infra
tags: [apscheduler, radix-ui, vitest, testing, shadcn, react-dialog, react-dropdown-menu]

# Dependency graph
requires:
  - phase: 03.2-game-ux-enhancements
    provides: completed game loop, frontend component pattern (tabs.tsx manual-write shadcn)
provides:
  - APScheduler in requirements.txt for nightly cache job (Plans 04-02+)
  - dialog.tsx shadcn primitive for confirmation dialogs (Plans 04-04, 04-05, 04-06)
  - dropdown-menu.tsx shadcn primitive for session actions menu (Plans 04-05, 04-06)
  - test_cache.py stubs for CACHE-01 and CACHE-02 (RED state)
  - test_session_mgmt.py stubs for SESSION-01 and SESSION-02 (RED state)
  - RadarrBanner.test.tsx stub for UX-06 (RED state)
  - vitest + @testing-library/react frontend test infrastructure
affects:
  - 04-02-nightly-cache-job
  - 04-03-ui-polish
  - 04-04-radarr-notification-banner
  - 04-05-delete-last-step
  - 04-06-delete-archived-session

# Tech tracking
tech-stack:
  added:
    - apscheduler>=3.10.4,<4.0 (backend scheduler)
    - "@radix-ui/react-dialog ^1.1.15"
    - "@radix-ui/react-dropdown-menu ^2.1.16"
    - vitest ^4.1.0 (frontend test runner)
    - "@testing-library/react ^16.3.2"
    - "@testing-library/jest-dom ^6.9.1"
    - jsdom ^29.0.0
  patterns:
    - shadcn manual-write pattern: import * as XxxPrimitive from "@radix-ui/react-xxx", re-export roots directly, wrap compound pieces with cn() for className merging, export named components only
    - pytest skip stubs: @pytest.mark.asyncio + pytest.skip("not implemented — description")
    - vitest environment jsdom configured in vite.config.ts test block

key-files:
  created:
    - backend/tests/test_cache.py
    - backend/tests/test_session_mgmt.py
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/dropdown-menu.tsx
    - frontend/src/__tests__/RadarrBanner.test.tsx
  modified:
    - backend/requirements.txt (apscheduler added)
    - frontend/package.json (radix packages, vitest, test script)
    - frontend/vite.config.ts (vitest test block with jsdom)

key-decisions:
  - "Use client fixture (not async_client) in backend test stubs — aligns with existing conftest.py fixture definition"
  - "vitest installed in Task 4 as Rule 3 auto-fix — test script and jsdom environment absent; needed for RadarrBanner.test.tsx to be discoverable"
  - "VALIDATION.md nyquist_compliant and wave_0_complete already set to true in frontmatter — no update needed"

patterns-established:
  - "shadcn manual-write: import Primitive, re-export Root directly, forwardRef wrapper with cn() for styled sub-components, displayName assignment"
  - "pytest RED stubs: @pytest.mark.asyncio + client fixture + pytest.skip() with implementation hint"
  - "vitest RED stubs: @ts-expect-error on missing import, two test cases matching exact UX requirement behaviors"

requirements-completed: [CACHE-01, CACHE-02, SESSION-01, SESSION-02, UX-06]

# Metrics
duration: 12min
completed: 2026-03-17
---

# Phase 4 Plan 01: Foundation Dependencies Summary

**APScheduler, Radix dialog/dropdown-menu, vitest, and 7 RED test stubs establishing the full Phase 4 feedback loop**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-17T16:28:00Z
- **Completed:** 2026-03-17T16:40:00Z
- **Tasks:** 4
- **Files modified:** 8

## Accomplishments
- Installed all Wave 0 dependencies: APScheduler (backend) and two Radix UI primitives (frontend)
- Wrote dialog.tsx and dropdown-menu.tsx following the established shadcn manual-write pattern from tabs.tsx
- Created 7 pytest skip stubs (3 cache, 4 session management) that collect and skip cleanly
- Created RadarrBanner.test.tsx with 2 UX-06 stubs; vitest discovers and errors in RED state
- Bootstrapped frontend test infrastructure (vitest, @testing-library/react, jsdom)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install APScheduler and Radix packages** - `a869a7a` (chore)
2. **Task 2: Write shadcn Dialog and DropdownMenu primitives** - `73dbd37` (feat)
3. **Task 3: Write failing test stubs for CACHE-01, CACHE-02, SESSION-01, SESSION-02** - `bfb3fdc` (test)
4. **Task 4: Write failing RadarrBanner test stub for UX-06** - `ec3e6b0` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `backend/requirements.txt` - Added apscheduler>=3.10.4,<4.0
- `frontend/package.json` - Added @radix-ui/react-dialog, @radix-ui/react-dropdown-menu, vitest, @testing-library/react, jsdom; added test script
- `frontend/vite.config.ts` - Added test block (globals: true, environment: jsdom)
- `frontend/src/components/ui/dialog.tsx` - shadcn Dialog primitive (9 named exports)
- `frontend/src/components/ui/dropdown-menu.tsx` - shadcn DropdownMenu primitive (10 named exports)
- `backend/tests/test_cache.py` - 3 skip stubs for CACHE-01/CACHE-02
- `backend/tests/test_session_mgmt.py` - 4 skip stubs for SESSION-01/SESSION-02
- `frontend/src/__tests__/RadarrBanner.test.tsx` - 2 UX-06 stubs (RED state)

## Decisions Made
- Used `client` fixture (not `async_client`) in backend test stubs — aligns with existing conftest.py fixture; the plan specified `async_client` but that fixture does not exist
- Installed vitest as Rule 3 auto-fix — frontend had no test infrastructure (no `test` script, no vitest config); required for RadarrBanner.test.tsx to run at all

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing vitest frontend test infrastructure**
- **Found during:** Task 4 (RadarrBanner test stub)
- **Issue:** vitest not installed; no `test` script in package.json; no vitest config in vite.config.ts — `npm run test` would fail with "missing script"
- **Fix:** Installed vitest, @testing-library/react, @testing-library/jest-dom, jsdom; added `test: vitest run` script; added test block to vite.config.ts with jsdom environment
- **Files modified:** frontend/package.json, frontend/vite.config.ts, frontend/package-lock.json
- **Verification:** `npm run test -- RadarrBanner` runs vitest, discovers file, errors on missing component (expected RED state)
- **Committed in:** ec3e6b0 (Task 4 commit)

**2. [Rule 1 - Bug] Used `client` fixture instead of `async_client` in backend test stubs**
- **Found during:** Task 3 (backend test stubs)
- **Issue:** Plan specified `async_client: AsyncClient` fixture but conftest.py only defines `client`; using `async_client` would cause a fixture-not-found error
- **Fix:** Used `client: AsyncClient` to match existing conftest.py fixture name
- **Files modified:** backend/tests/test_cache.py, backend/tests/test_session_mgmt.py
- **Verification:** `python3 -m pytest tests/test_cache.py tests/test_session_mgmt.py -v` — 7 skipped, 0 errors
- **Committed in:** bfb3fdc (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## Next Phase Readiness
- All Phase 4 foundation dependencies in place; Wave 1 plans (04-02 through 04-07) can execute
- dialog.tsx and dropdown-menu.tsx ready for import by session management and UI polish plans
- 7 RED test stubs provide the Nyquist feedback loop hooks for cache and session management plans
- RadarrBanner.test.tsx RED state will flip GREEN when Plan 04 creates RadarrNotificationBanner

---
*Phase: 04-caching-ui-ux-polish-and-session-management*
*Completed: 2026-03-17*
