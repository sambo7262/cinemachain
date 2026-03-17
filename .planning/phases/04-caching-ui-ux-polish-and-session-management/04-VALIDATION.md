---
phase: 4
slug: caching-ui-ux-polish-and-session-management
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-17
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `pytest backend/tests/ -x -q` |
| **Full suite command** | `pytest backend/tests/ && cd frontend && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/ -x -q`
- **After every plan wave:** Run `pytest backend/tests/ && cd frontend && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | CACHE-01 | unit | `pytest backend/tests/test_cache.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | CACHE-01 | integration | `pytest backend/tests/test_cache.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | CACHE-02 | unit | `pytest backend/tests/test_cache.py::test_lazy_enrich -x -q` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 0 | UX-06 | unit | `cd frontend && npm run test -- RadarrBanner` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 0 | UX-06 | unit | `cd frontend && npm run test -- RadarrBanner` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | UX-06 | integration | `cd frontend && npm run test -- RadarrBanner` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 1 | UX-07 | manual | see manual verifications | — | ⬜ pending |
| 4-03-02 | 03 | 1 | UX-08 | manual | see manual verifications | — | ⬜ pending |
| 4-03-03 | 03 | 1 | UX-09 | manual | see manual verifications | — | ⬜ pending |
| 4-04-01 | 04 | 1 | SESSION-01 | integration | `pytest backend/tests/test_session_mgmt.py -x -q` | ❌ W0 | ⬜ pending |
| 4-04-02 | 04 | 1 | SESSION-02 | integration | `pytest backend/tests/test_session_mgmt.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_cache.py` — stubs for CACHE-01, CACHE-02 nightly job and lazy enrichment (Plan 01 Task 3)
- [ ] `backend/tests/test_session_mgmt.py` — stubs for SESSION-01 (delete last step), SESSION-02 (delete archived session) (Plan 01 Task 3)
- [ ] `frontend/src/__tests__/RadarrBanner.test.tsx` — stubs for UX-06 notification banner (Plan 01 Task 4)
- [ ] `backend/tests/conftest.py` — verify shared fixtures are compatible with new test files

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Session home displays active movie poster thumbnail | UX-07 | Visual layout check; image URL resolution from DB | Navigate to session home, confirm hero poster renders at 120px wide, left-anchored |
| Actor/movie images load at every session step | UX-08 | Cross-page visual regression; TMDB image URL correctness | Step through a session chain: actor grid, movie grid, chain history — verify no broken images |
| Radarr banner doesn't overlap game controls | UX-09 | Positional rendering; depends on real Radarr connection | Trigger a Radarr add; confirm banner is top-of-viewport, auto-dismisses after 5s, × closes it |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
