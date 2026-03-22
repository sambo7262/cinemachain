---
phase: 6
slug: new-features
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && pytest tests/ -x -q` |
| **Full suite command** | `cd backend && pytest tests/ && cd ../frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ && cd ../frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | Item 1 actor name | unit | `pytest tests/test_game.py::test_csv_actor_name_resolved -x -q` | :x: W0 | :white_large_square: pending |
| 6-02-01 | 02 | 1 | Item 2 overview migration | unit | `pytest tests/test_game.py::test_eligible_movie_overview_field -x -q` | :x: W0 | :white_large_square: pending |
| 6-03-01 | 03 | 1 | Item 3 session name PATCH | unit | `pytest tests/test_game.py::test_rename_session -x -q` | :x: W0 | :white_large_square: pending |
| 6-04-01 | 04 | 2 | Item 6 settings model | unit | `pytest tests/test_settings.py::test_db_overrides_env -x -q` | :x: W0 | :white_large_square: pending |
| 6-05-01 | 05 | 2 | Item 6 settings router | unit | `pytest tests/test_settings.py::test_db_overrides_env -x -q` | :x: W0 | :white_large_square: pending |
| 6-06-01 | 06 | 3 | Frontend components | manual | Visual inspection | N/A | :white_large_square: pending |

*Status: :white_large_square: pending · :white_check_mark: green · :x: red · :warning: flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_game.py` — stubs for actor name resolution (Item 1), overview field (Item 2), skip_radarr (Item 2), rename session (Item 3)
- [ ] `backend/tests/test_settings.py` — stubs for AppSettings DB override of .env (Item 6)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Movie Selection Splash visual quality | Item 2 | UI polish judgment | Open session, select eligible movie, verify poster, overview, MPAA, runtime all appear |
| Onboarding screen blocks app without TMDB key | Item 6 | Requires env manipulation | Remove TMDB key from DB/env, reload app, verify blocking screen appears |
| Settings .env migration runs once | Item 6 | One-time startup behavior | Fresh DB with .env present, start app, verify settings populated in DB |
| Chain History search filters correctly | Item 4 | Frontend interaction | Type actor/movie name in search, verify non-matching rows hidden |
| TMDB links open in new tab | Item 5 | Browser behavior | Click TMDB link in eligible movies table, chain history — verify new tab |
| RT ratings display (if implemented) | Item 7 | Requires live API | View movie in eligible list, verify RT score shown if MDBList returns data |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
