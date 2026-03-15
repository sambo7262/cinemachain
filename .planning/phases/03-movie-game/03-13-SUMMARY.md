---
phase: 03-movie-game
plan: "13"
subsystem: verification
tags: [verification, game, session-lifecycle, docker, e2e, gap-closure]

# Dependency graph
requires:
  - phase: 03-11
    provides: eligible-movies on-demand TMDB fetch, Makefile rebuild target
  - phase: 03-12
    provides: pause/resume toggle, end-session refetch fix

provides:
  - Verification record: GAME-02, GAME-03, GAME-05, GAME-06, GAME-08 PASSED; GAME-01 session lifecycle FAILED (second round gap closure required); GAME-04, GAME-07 untested (blocked by session start)

affects:
  - 03-14 (must fix GAME-01 session lifecycle: end-session banner clear and new session start from lobby)

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "03-13 checkpoint PARTIAL PASS — GAME-01 session lifecycle still broken after 03-12 refetchQueries fix; a 03-14 gap-closure plan is required targeting end-session + create-session lobby flow"
  - "End-session banner clear is the primary remaining defect: endMutation.onSuccess calls refetchQueries but banner does not disappear; root cause is unclear — candidates include stale cache race with staleTime:10000, backend end endpoint rejecting the request, or nginx proxy not reaching the running container on the NAS"
  - "GAME-03 confirmed FIXED: eligible-movies now returns full actor filmography from TMDB after 03-11 on-demand fetch; user confirmed 5+ movies populate after actor selection"
  - "GAME-08 confirmed FIXED: Radarr request triggered and session advances on movie selection"
  - "Pause/resume toggle (03-12) confirmed FIXED: button correctly shows Pause when active and Resume when paused"
  - "Docker rebuild (03-11) confirmed FIXED: frontend image confirmed serving CinemaChain React app, not the Phase 1 placeholder"

patterns-established: []

requirements-completed: []

# Metrics
duration: ~83min
completed: 2026-03-15
---

# Phase 3 Plan 13: Gap Closure Re-Verification Summary

**Re-verification after 03-11/03-12 remediation: GAME-03 (eligible movies), GAME-08 (Radarr), and pause/resume UX confirmed fixed; GAME-01 session lifecycle (end-session + start-new-session from lobby) still broken — a second round of gap closure (03-14) is required.**

## Performance

- **Duration:** ~83 min (including Docker rebuild wait and user verification time)
- **Started:** 2026-03-15T18:32:31Z
- **Completed:** 2026-03-15T19:55:00Z (approx)
- **Tasks:** 1 of 2 auto (Task 1 complete); Task 2 checkpoint reached and human verified
- **Files modified:** 0 (verification-only plan)

## Accomplishments

- Both Docker images (`sambo7262/cinemachain-backend:latest`, `sambo7262/cinemachain-frontend:latest`) successfully rebuilt from source with `--no-cache`
- `_ensure_actor_credits_in_db` confirmed present in the built backend image — TMDB on-demand fetch fix (03-11) is live
- Frontend image confirmed serving "CinemaChain" + Vite React app — Phase 1 placeholder routing defect fully resolved
- 20 backend unit tests pass in the rebuilt container (9 DB-connection failures are expected without a live Postgres, same as before remediation)
- Human verification confirmed GAME-03, GAME-08, pause/resume UX, and routing all working in the live app
- Remaining defect (GAME-01 session lifecycle) scoped and documented for 03-14

## Task Commits

No code commits — this was a verification-only plan. The rebuilt Docker images are local artifacts (not git commits).

## Files Created/Modified

None — verification checkpoint only.

## Verification Result

**Status: PARTIAL PASS**

### Requirements Verified

| Requirement | Status | Notes |
|-------------|--------|-------|
| GAME-01 (routing) | PASSED | CinemaChain lobby loads at / — not the "coming soon" placeholder |
| GAME-01 (session lifecycle) | FAILED | End-session banner does not clear; cannot start new session from lobby |
| GAME-02 | PASSED | Eligible Actors panel renders correctly (carried from 03-10) |
| GAME-03 | PASSED | Eligible Movies tab now populates with full actor filmography after actor selection |
| GAME-04 | UNTESTED | Blocked — cannot complete a game move to reach the second-move actor panel (session start broken) |
| GAME-05 | PASSED | Sort controls (By Rating, By Runtime, By Genre) reorder the movie list |
| GAME-06 | PASSED | Unwatched/All toggle changes which movies appear with watched badges |
| GAME-07 | UNTESTED | Blocked — unable to reach the selector UI to confirm watched movies are non-clickable |
| GAME-08 | PASSED | Movie selection triggers Radarr request; session advances to new movie |
| Pause/Resume UX | PASSED | Button correctly toggles between "Pause" and "Resume" states |

### Verified Fixed (from 03-10 defect list)

**Defect 1 — Routing (FIXED):** Docker `--no-cache` rebuild resolved the stale Phase 1 placeholder at `/`. Frontend image confirmed serving the CinemaChain React SPA.

**Defect 3 — Eligible Movies (FIXED):** `_ensure_actor_credits_in_db` now fetches full TMDB filmography before the DB JOIN. User confirmed 5+ movies populate when selecting an actor. First-query TMDB fetch delay observed as expected.

**Defect 4 — Pause Toggle (FIXED):** `resumeMutation` added as sibling to `pauseMutation`; session query key invalidated on both. Button correctly shows "Resume" when paused and "Pause" when active.

### Remaining Defect

**Defect 2 — Session Lifecycle (STILL BROKEN):** The lobby's "End Session" button calls `api.endSession(sessionId)` via `endMutation`; `onSuccess` calls `await queryClient.refetchQueries({ queryKey: ["activeSession"] })`. Despite the 03-12 fix (refetchQueries over invalidateQueries), the banner does not disappear after clicking "End Session". Creating a new session also fails — either because the ended session is not cleared from the active query, or because the backend still returns 409 (active session exists) for the create call.

**Root cause candidates for 03-14 investigation:**

1. **`getActiveSession` returns stale data despite refetch:** `staleTime: 10_000` in the `useQuery` for `activeSession` may prevent the refetch from returning the updated (null) value. `refetchQueries` does bypass stale time, but the response handling in `apiFetch` may be returning a cached 200 body.

2. **Backend end endpoint silently failing:** `POST /game/sessions/{id}/end` sets `session.status = "ended"` — if the session is already in `"ended"` state (from a prior attempt), the handler still succeeds (no guard). But if the session was already ended, `GET /sessions/active` correctly returns null. This suggests the refetch may be succeeding but the React component is not re-rendering (stale `activeSession` reference).

3. **`refetchQueries` call not awaited correctly:** The `endMutation.onSuccess` is `async () => { await queryClient.refetchQueries(...) }` — TanStack Query mutation `onSuccess` handlers may not propagate the `async` context; the `await` may not actually block the state update.

4. **NAS-specific nginx proxy issue:** The `docker compose up` on the NAS requires the `synobridge` external network. If the containers started with stale networking after the rebuild, the nginx proxy to the backend may be using an old IP, causing `/api/game/sessions/{id}/end` to return a network error that the `onError` handler swallows silently.

## Decisions Made

- 03-13 checkpoint recorded as PARTIAL PASS. Phase 3 cannot close yet.
- A gap-closure plan 03-14 must be written to fix GAME-01 session lifecycle before Phase 3 can be marked complete.
- Requirements GAME-04 and GAME-07 remain untested pending session lifecycle fix; they will be re-verified in 03-14's checkpoint.
- No code changes were made during this plan — all findings are documented here for the 03-14 remediation plan.

## Deviations from Plan

**Docker `compose up` failed on dev machine** (not a defect): `make rebuild` built both images successfully but `docker compose up -d` failed with `network synobridge declared as external, but could not be found`. This is expected — `synobridge` is a Synology NAS-specific Docker network that does not exist on the dev machine. Images were verified directly via `docker run --rm` and by inspecting the image filesystem. The rebuilt images are ready for deployment to the NAS.

The plan's automated check was adapted: instead of `docker exec cinemachain-backend python -c "..."` (container not running on dev), used `docker run --rm ... python -c "..."` against the newly built image.

## Issues Encountered

GAME-01 session lifecycle defect persisted through the 03-12 fix. The `refetchQueries` approach was theoretically correct but did not resolve the problem in the live app. Root cause requires active debugging (network inspection, console logs, or backend log tailing) in the running NAS environment — outside the scope of a verification plan.

## User Setup Required

None — no new configuration required.

## Next Phase Readiness

Phase 3 is NOT ready to close. Required before Phase 3 completes:

1. **Write and execute 03-14:** Gap-closure plan targeting GAME-01 session lifecycle — investigate and fix end-session banner clear and new-session start from lobby
2. **Re-verify GAME-04 and GAME-07** in the 03-14 checkpoint (blocked by session lifecycle in this pass)
3. After GAME-01 fully verified: update ROADMAP.md Phase 3 status to "Complete", STATE.md to Phase 4

---
*Phase: 03-movie-game*
*Completed: 2026-03-15 (partial pass — session lifecycle defect remains; 03-14 required)*
