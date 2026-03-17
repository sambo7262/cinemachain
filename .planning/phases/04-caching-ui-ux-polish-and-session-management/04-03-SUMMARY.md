---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "03"
subsystem: api

tags: [fastapi, sqlalchemy, session-management, delete, postgresql]

requires:
  - phase: 04-01
    provides: Wave 0 foundation — GameSession model, game.py router with selectinload pattern

provides:
  - DELETE /game/sessions/{session_id}/steps/last — undo last move and revert session to prior movie
  - DELETE /game/sessions/{session_id} — permanently remove an archived session and all its steps
  - Integration tests for SESSION-01 and SESSION-02 in test_session_mgmt.py

affects:
  - frontend sessions management UI (any undo or delete session feature)
  - 04-04 and later plans that modify game.py

tech-stack:
  added: []
  patterns:
    - "Parameterized DELETE routes appended after all static sub-paths to respect FastAPI 422 rule"
    - "Step revert: sort steps by step_order, delete last, restore prev_step.movie_tmdb_id to session"
    - "Re-fetch with selectinload after commit for response building (same pattern as other routes)"
    - "Status guard (403) before destructive delete — only archived sessions deletable"

key-files:
  created:
    - backend/tests/test_session_mgmt.py  # stubs replaced with real integration tests
  modified:
    - backend/app/routers/game.py  # two new @router.delete endpoints appended at EOF

key-decisions:
  - "delete_last_step uses _resolve_current_movie_title helper (not inline title search) for consistency with other endpoints"
  - "delete_archived_session explicitly deletes steps before session (FK safety, no cascade assumed)"
  - "awaiting_continue status reverted to active on step delete — allows user to continue playing after undo"
  - "current_movie_watched set to False on step delete — forces home page CTA to reappear after undo"

patterns-established:
  - "Session undo pattern: sort steps by step_order, delete last, revert current_movie_tmdb_id to steps[-2].movie_tmdb_id"

requirements-completed: [SESSION-01, SESSION-02]

duration: 2min
completed: 2026-03-17
---

# Phase 04 Plan 03: Session Management DELETE Endpoints Summary

**Two DELETE endpoints for session undo (SESSION-01) and archived session cleanup (SESSION-02) added to game.py with integration test stubs promoted to real tests.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-17T23:45:20Z
- **Completed:** 2026-03-17T23:47:07Z
- **Tasks:** 2 (Task 1: delete_last_step; Task 2: delete_archived_session + tests)
- **Files modified:** 2

## Accomplishments

- SESSION-01: DELETE `/game/sessions/{id}/steps/last` removes highest-order step, reverts `current_movie_tmdb_id` to prior step's movie, sets `current_movie_watched=False`, and reverts `awaiting_continue` status back to `active`
- SESSION-02: DELETE `/game/sessions/{id}` permanently removes an archived session + all steps (explicit step deletion before session for FK safety); protected by 403 guard when status is not `archived`
- Four integration tests written in `test_session_mgmt.py` replacing `pytest.skip` stubs — all skip correctly in local dev (no DB), matching existing `test_game.py` behavior

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — Integration tests (failing stubs replaced)** - `09ae8d0` (test)
2. **Task 1+2 GREEN — Both DELETE endpoints implemented** - `a15eea1` (feat)

_Note: TDD RED committed first, GREEN committed after both endpoints implemented together (they share the same file and are tightly coupled)_

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/routers/game.py` — two new `@router.delete` endpoints appended at EOF (lines 1507–1577)
- `backend/tests/test_session_mgmt.py` — four `pytest.skip` stubs replaced with real integration tests

## Decisions Made

- `delete_last_step` calls `_resolve_current_movie_title(refreshed)` instead of inline title lookup — consistent with existing GET /sessions/{id} response building pattern
- Explicit step loop deletion (`for step in session.steps: await db.delete(step)`) before deleting the session — FK safety regardless of cascade setting in models
- `awaiting_continue` reverted to `active` on undo — plan specifies this, ensures session is playable after undoing the last pick
- Route ordering: both DELETE routes appended after line 1500 (request-movie), well after all static sub-paths — satisfies 03.1-08 ordering rule

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- SESSION-01 and SESSION-02 backend complete; frontend can now add Undo Last Step and Delete Session buttons
- No DB migration needed — no new tables or columns
- game.py route ordering preserved; no 422 risk from new parameterized DELETE routes

---
*Phase: 04-caching-ui-ux-polish-and-session-management*
*Completed: 2026-03-17*
