---
phase: 13
slug: mdblist-expansion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/test_mdblist.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x && cd frontend && npm test -- --run` |
| **Estimated runtime** | ~15 seconds (backend quick), ~45 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_mdblist.py -x`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Req | Test Type | Automated Command | File Exists | Status |
|---------|-----|-----------|-------------------|-------------|--------|
| MDBList parser — all 6 fields | MDBLIST-01 | unit | `pytest tests/test_mdblist.py::test_parse_all_rating_sources -x` | ❌ W0 | ⬜ pending |
| `score_average` → `mdb_avg_score` | MDBLIST-01 | unit | `pytest tests/test_mdblist.py::test_score_average_stored -x` | ❌ W0 | ⬜ pending |
| `imdbid` → `imdb_id` | MDBLIST-01 | unit | `pytest tests/test_mdblist.py::test_imdbid_stored -x` | ❌ W0 | ⬜ pending |
| Backfill status endpoint | MDBLIST-02 | unit | `pytest tests/test_mdblist.py::test_backfill_status_schema -x` | ❌ W0 | ⬜ pending |
| RatingsBadge renders (card variant) | MDBLIST-03 | vitest | `cd frontend && npm test -- --run` | ❌ W0 | ⬜ pending |
| RatingsBadge hides null/0 scores | MDBLIST-03 | vitest | `cd frontend && npm test -- --run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_mdblist.py` — stubs for all MDBLIST-01/02/03 backend behaviors (asyncpg-skip pattern)
- [ ] `frontend/src/components/__tests__/RatingsBadge.test.tsx` — stubs for badge render + null-hide logic

*Both files created as Wave 0 stubs; all tests skip locally and run green in Docker.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ratings badges render correctly in browser with real data | MDBLIST-02/03 | Visual layout, SVG rendering | Open GameSession eligible movies on NAS; verify badge strip wraps correctly on mobile |
| Backfill progress bar advances correctly | MDBLIST-01 | UI animation/polling | Trigger backfill from Settings; confirm counter increments and bar fills |
| IMDB external links open correct movie pages | MDBLIST-03 | External navigation | Click IMDB link on splash; confirm `imdb.com/title/tt...` opens |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
