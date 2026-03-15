---
phase: 3
slug: movie-game
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `pytest.ini` / `vite.config.ts` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v && npm run test --prefix frontend` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v && npm run test --prefix frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Plan 03-01 creates two test files: `test_game.py` (19 stubs, GAME-01 through GAME-08) and `test_radarr.py` (9 stubs, GAME-08 RadarrClient unit tests). All downstream plan verify commands reference these files.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | GAME-01..08 | stub-collect | `pytest tests/test_game.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 0 | GAME-08 | stub-collect | `pytest tests/test_radarr.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 3-05-01 | 05 | 2 | GAME-01,04 | unit | `pytest tests/test_game.py -k "create_session or active_session or pause or resume or end_session or import_csv" -x -q` | ❌ W0 | ⬜ pending |
| 3-05-02 | 05 | 2 | GAME-01 | unit | `pytest tests/ -x -q -k "not test_game and not test_radarr"` | existing | ⬜ pending |
| 3-06-01 | 06 | 3 | GAME-02,03,05 | unit | `pytest tests/test_game.py -k "eligible_actors or eligible_movies or all_movies or watched_not_selectable or sort_movies" -x -q` | ❌ W0 | ⬜ pending |
| 3-06-02 | 06 | 3 | GAME-06,07,08 | unit | `pytest tests/test_game.py -k "pick_actor or request_movie or skip_radarr" -x -q` | ❌ W0 | ⬜ pending |
| 3-07-01 | 07 | 2 | GAME-01 | build | `npm run build --prefix frontend` | N/A | ⬜ pending |
| 3-08-01 | 08 | 3 | GAME-02..08 | build | `npm run build --prefix frontend` | N/A | ⬜ pending |
| 3-09-01 | 09 | 4 | GAME-01,08 | unit+build | `pytest tests/ -x -q && npm run build --prefix frontend` | existing | ⬜ pending |
| 3-10-01 | 10 | 5 | GAME-08 | e2e-manual | manual checkpoint | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Plan 03-01 creates the Wave 0 test stubs. All stubs live in two files:

- [x] `tests/test_game.py` — 19 stubs covering GAME-01 through GAME-08 (session lifecycle, eligible actors/movies, pick-actor, request-movie, sort, filter, import-csv)
- [x] `tests/test_radarr.py` — 9 stubs covering RadarrClient unit behavior (movie_exists, add_movie, lookup_movie, root folder, quality profile)

These two files replace the previously planned separate per-feature files (`test_game_session.py`, `test_eligible_actors.py`, etc.). All verify commands in plans 03-05 and 03-06 use `-k` filters against `test_game.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full game UI flow — start, pick actor, pick movie, advance session | GAME-08 | Requires browser interaction and Radarr integration in dev environment | Open browser, start game from movie library, pick actor, pick movie, verify Radarr queue entry appears |
| Movie sorting by genre/rating/runtime | GAME-05 | Visual sort behavior requires browser | Verify sort dropdowns (By Rating, By Runtime, By Genre) change order of Eligible Movies panel |
| Watched/unwatched badge display | GAME-05 | Visual badge requires browser | Toggle unwatched-only filter, verify watched badges appear on all-movies view |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all test file references (test_game.py, test_radarr.py)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
