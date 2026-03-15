---
phase: 3
slug: movie-game
status: draft
nyquist_compliant: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | GAME-01 | unit | `pytest tests/test_game_session.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | GAME-01 | unit | `pytest tests/test_game_session.py::test_create_session -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | GAME-02 | unit | `pytest tests/test_eligible_actors.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | GAME-03 | unit | `pytest tests/test_eligible_movies.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 2 | GAME-04 | unit | `pytest tests/test_game_session.py::test_actor_exclusion -x -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 2 | GAME-05 | unit | `pytest tests/test_movie_filter.py -x -q` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 2 | GAME-06 | unit | `pytest tests/test_radarr_client.py -x -q` | ❌ W0 | ⬜ pending |
| 3-04-02 | 04 | 3 | GAME-07 | integration | `pytest tests/test_game_api.py -x -q` | ❌ W0 | ⬜ pending |
| 3-05-01 | 05 | 3 | GAME-08 | e2e-manual | N/A | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_game_session.py` — stubs for GAME-01, GAME-04
- [ ] `tests/test_eligible_actors.py` — stubs for GAME-02
- [ ] `tests/test_eligible_movies.py` — stubs for GAME-03, GAME-05
- [ ] `tests/test_movie_filter.py` — stubs for GAME-05
- [ ] `tests/test_radarr_client.py` — stubs for GAME-06
- [ ] `tests/test_game_api.py` — stubs for GAME-07
- [ ] `tests/conftest.py` — shared fixtures (DB session, mock TMDB/Radarr clients)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full game UI flow — start, pick actor, pick movie, advance session | GAME-08 | Requires browser interaction and Radarr integration in dev environment | Open browser, start game from movie library, pick actor, pick movie, verify Radarr queue entry appears |
| Movie sorting by genre/TMDB rating/aggregated rating | GAME-05 | Visual sort behavior requires browser | Verify sort dropdowns change order of Eligible Movies panel |
| Watched/unwatched badge display | GAME-05 | Visual badge requires browser | Toggle unwatched-only filter, verify watched badges appear on all-movies view |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
