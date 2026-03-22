---
phase: 05-bug-fixes
plan: "07"
subsystem: backend
tags: [bug-fix, csv-import, actor-validation, gap-closure]
dependency_graph:
  requires: []
  provides: [structured-actor-errors-in-csv-import]
  affects: [backend/app/routers/game.py, backend/tests/test_game.py]
tech_stack:
  added: []
  patterns: [collect-then-report, early-return-guard]
key_files:
  created: []
  modified:
    - backend/app/routers/game.py
    - backend/tests/test_game.py
decisions:
  - "actor_errors collected in same guard as unresolved — both block session creation and are returned together in validation_required response"
  - "Movie-pick step still added when actor resolution fails — only actor step is skipped"
  - "actor_id is None check gates steps_data.append — no silent null actor_tmdb_id stored"
metrics:
  duration: "81 seconds"
  completed: "2026-03-22"
  tasks_completed: 1
  files_modified: 2
---

# Phase 5 Plan 07: CSV Actor Validation Gap Closure Summary

**One-liner:** Row-level actor validation in import_csv_session surfaces (None, None) TMDB failures as structured actor_errors instead of silently storing null actor_tmdb_id.

## What Was Built

BUG-4 gap closure: `import_csv_session` in `game.py` now collects actor name resolution failures into an `actor_errors` list. When `_resolve_actor_tmdb_id` returns `(None, None)`, the row is flagged with `row`, `csv_movie_title`, `csv_actor_name`, and `reason: "actor_not_found"` — and no actor step with a null `actor_tmdb_id` is stored.

The `validation_required` early-return guard now checks `if unresolved or actor_errors`, combining both failure types in a single 200 response. Session creation is blocked until the user fixes their CSV.

A test stub (`test_csv_actor_validation_errors`) was added following the asyncpg-skip pattern — skips locally, must PASS in Docker.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 (RED) | Add failing test for actor validation errors | 814ebd3 |
| 1 (GREEN) | Implement actor validation in import_csv_session | 8141ea3 |

## Decisions Made

- **Same guard for both failure types:** `actor_errors` added to the existing `unresolved` guard — both block session creation, combined in a single `validation_required` response. No new response status needed.
- **Movie step preserved on actor failure:** The movie-pick step is already added before the actor resolution block; only the actor step is conditional on `actor_id is not None`.
- **Credit-mismatch deferred to phase 6:** Rows 113–114 (actors exist in TMDB but not credited in that film) are out of scope here — treated the same as name-mismatch failures (both surface as `actor_not_found`).

## Deviations from Plan

None — plan executed exactly as written.

## Acceptance Criteria Verification

- `grep -c "actor_errors" backend/app/routers/game.py` → 4 (declaration, append, guard, response)
- `grep "actor_not_found" backend/app/routers/game.py` → line 720 (1 match)
- `grep "test_csv_actor_validation_errors" backend/tests/test_game.py` → line 1489 (1 match)
- `grep "actor_tmdb_id.*None" backend/app/routers/game.py | grep "steps_data.append"` → empty (no silent null append)
- Test runs: SKIPPED locally (asyncpg), must PASS in Docker

## Self-Check: PASSED

Files exist:
- backend/app/routers/game.py — FOUND
- backend/tests/test_game.py — FOUND

Commits:
- 814ebd3 — test(05-07): add failing test
- 8141ea3 — feat(05-07): implement actor validation
