---
phase: 5
slug: bug-fixes
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-21
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` / `frontend/vite.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ && cd ../frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ && cd ../frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| BUG-1 | 01 | 1 | BUG-1 | integration | `cd backend && python -m pytest tests/test_game.py -x -q -k "test_bug1"` | ❌ W0 | ⬜ pending |
| BUG-2 | 01 | 1 | BUG-2 | manual | visual inspection on mobile viewport | N/A | ⬜ pending |
| BUG-3 | 01 | 1 | BUG-3 | integration | `cd backend && python -m pytest tests/test_game.py -x -q -k "test_bug3"` | ❌ W0 | ⬜ pending |
| BUG-4 | 01 | 1 | BUG-4 | integration | `cd backend && python -m pytest tests/test_game.py -x -q -k "test_bug4"` | ❌ W0 | ⬜ pending |
| ENH-1 | 01 | 1 | ENH-1 | integration | `cd backend && python -m pytest tests/test_game.py -x -q -k "test_enh1"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All stubs are appended to the existing test file — no new separate test files are created.

- [ ] `backend/tests/test_game.py` — append stubs for BUG-1 chain actor recording (`test_bug1_auto_actor_single`, `test_bug1_disambiguation_multiple`)
- [ ] `backend/tests/test_game.py` — append stub for BUG-3 eligibility query correctness (`test_bug3_eligibility_scoped_to_current_movie`)
- [ ] `backend/tests/test_game.py` — append stubs for BUG-4 CSV round-trip validation (`test_bug4_csv_actor_name_canonical`, `test_bug4_csv_roundtrip`)
- [ ] `backend/tests/test_game.py` — append stub for ENH-1 background prefetch trigger (`test_enh1_actor_precache_triggered`)

Wave 0 is complete when `python -m pytest tests/test_game.py --collect-only` exits 0 and lists all six new test names.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Portrait mode card fields visible | BUG-2 | Visual layout — requires browser/device | Open game session on mobile, switch to portrait, verify title/actor/rating/runtime/MPAA all visible on MovieCard |
| Home page button alignment | BUG-2 | Visual layout | Open home page on mobile (320–375px width), verify buttons aligned |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (all stubs go to test_game.py)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
