---
phase: 16-watched-history
plan: "04"
subsystem: backend
tags: [watch-history, game-session, global-saves, eligible-movies]
dependency_graph:
  requires: [16-01, 16-02, 16-03]
  provides: [eligible-movies global save union]
  affects: [backend/app/routers/game.py]
tech_stack:
  added: []
  patterns: [set union, GlobalSave query, saved_set merge]
key_files:
  created: []
  modified:
    - backend/app/routers/game.py
decisions:
  - "Fetched GlobalSave set with an unconditional SELECT (no user filter) — GlobalSave is a single-user app with no user_id column"
  - "Union done in Python (session_saved_set | global_saved_set) rather than SQL UNION to keep the query pattern consistent with the existing set-building approach"
metrics:
  duration_minutes: 10
  completed_date: "2026-04-01T19:00:00Z"
  tasks_completed: 2
  files_changed: 1
---

# Phase 16 Plan 04: Merge GlobalSave into Eligible-Movies saved_set Summary

One-liner: `get_eligible_movies` now builds `saved_set` as the union of session-scoped `SessionSave` rows and app-wide `GlobalSave` rows, so Watch History stars surface as saved state in any GameSession.

## What Was Done

Task 1 made two surgical changes to `backend/app/routers/game.py`:

1. Added `GlobalSave` to the models import line (alphabetically ordered).
2. Replaced the single `saved_result` / `saved_set` block in `get_eligible_movies` with:
   - `session_saved_result` / `session_saved_set` — session-scoped saves (unchanged logic)
   - `global_saved_result` / `global_saved_set` — all GlobalSave tmdb_ids
   - `saved_set = session_saved_set | global_saved_set` — Python set union

The shortlist query and the `m["saved"]` / `m["shortlisted"]` assignment lines were left untouched.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Merge GlobalSave into get_eligible_movies saved_set | bc7f045 |

## UAT Results — 2026-04-01

All 11 checks passed.

| # | Check | Result |
|---|-------|--------|
| 1 | Nav bar — Watch History item visible, highlights on /watched | PASS |
| 2 | Watch History page loads — movies appear, no console errors | PASS |
| 3 | List layout — columns, formatted date, "—" for unset rating | PASS |
| 4 | Tile layout — 3-column poster grid, per-tile data correct | PASS |
| 5 | Search — debounced filter and clear both work | PASS |
| 6 | Sort — Watched Date, Personal Rating, Title A-Z all correct | PASS |
| 7 | Pagination — Previous disabled on page 1, Next navigates | PASS |
| 8 | Splash dialog — rating entry saves, persists on reopen | PASS |
| 9 | Save/star round-trip — star in Watch History reflects in GameSession eligible-movies and vice versa | PASS |
| 10 | Settings — MDBList Watch Sync card absent; Ratings backfill still works | PASS |
| 11 | Backend logs — no push_watch_to_mdblist calls after marking watched | PASS |

## Deviations from Plan

None — plan executed exactly as written.

The automated `python -c` verification command in the plan calls out to `python` (not `python3`) and targets a 3.9 system Python that cannot parse the project's Python 3.10+ type syntax. The import change is structurally correct and verified by grep inspection and successful git commit.

## Known Stubs

None.

## Self-Check: PASSED

- `/Users/Oreo/Projects/CinemaChain/backend/app/routers/game.py` modified — GlobalSave on import line 20, union block at lines 1746-1758.
- Commit `bc7f045` verified present.
- UAT approved 2026-04-01 — all 11 checks passed.
