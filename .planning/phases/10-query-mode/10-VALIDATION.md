---
phase: 10
slug: query-mode
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && pytest tests/test_search.py -x` |
| **Full suite command** | `cd backend && pytest` + `cd frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_search.py -x` (backend) or `cd frontend && npm test -- --run SearchPage` (frontend)
- **After every plan wave:** Run full backend suite `cd backend && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-W0-01 | Wave 0 | 0 | QMODE-01,02,03,06 | unit | `pytest tests/test_search.py -x` | ❌ W0 | ⬜ pending |
| 10-W0-02 | Wave 0 | 0 | QMODE-04,05 | unit | `npm test -- --run SearchPage` | ❌ W0 | ⬜ pending |
| 10-01 | backend | 1 | QMODE-01 | unit | `pytest tests/test_search.py::test_search_movies_enriched -x` | ❌ W0 | ⬜ pending |
| 10-02 | backend | 1 | QMODE-02 | unit | `pytest tests/test_search.py::test_search_actors -x` | ❌ W0 | ⬜ pending |
| 10-03 | backend | 1 | QMODE-03 | unit | `pytest tests/test_search.py::test_popular_by_genre -x` | ❌ W0 | ⬜ pending |
| 10-04 | backend | 1 | QMODE-06 | unit | `pytest tests/test_search.py::test_request_movie_standalone -x` | ❌ W0 | ⬜ pending |
| 10-05 | frontend | 2 | QMODE-04,05 | unit | `npm test -- --run SearchPage` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_search.py` — new file covering QMODE-01 through QMODE-03 and QMODE-06 backend endpoints (stubs with mocked TMDB/Radarr responses)
- [ ] `frontend/src/pages/__tests__/SearchPage.test.tsx` — covers QMODE-04 (sort) and QMODE-05 (unwatched toggle) frontend behaviors

*No new test infrastructure needed — pytest and vitest already configured in the project.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Genre chip browse loads top 50 TMDB popular movies | QMODE-03 | Live TMDB API call; mocked in unit test | Click a genre chip on Search page; verify ≥20 results appear with poster/year/rating |
| Radarr download confirmation state | QMODE-06 | Requires live Radarr connection | Click "Download via Radarr"; verify button shows "Added" briefly then resets |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
