---
phase: 5
slug: bug-fixes
status: draft
nyquist_compliant: false
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
| BUG-1 | 01 | 1 | BUG-1 | integration | `cd backend && python -m pytest tests/test_game_chain_actor.py -x -q` | ❌ W0 | ⬜ pending |
| BUG-2 | 01 | 1 | BUG-2 | manual | visual inspection on mobile viewport | N/A | ⬜ pending |
| BUG-3 | 01 | 1 | BUG-3 | integration | `cd backend && python -m pytest tests/test_eligibility.py -x -q` | ❌ W0 | ⬜ pending |
| BUG-4 | 01 | 1 | BUG-4 | integration | `cd backend && python -m pytest tests/test_csv_import.py -x -q` | ❌ W0 | ⬜ pending |
| ENH-1 | 01 | 1 | ENH-1 | integration | `cd backend && python -m pytest tests/test_actor_precache.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_game_chain_actor.py` — stubs for BUG-1 chain actor recording
- [ ] `backend/tests/test_eligibility.py` — stubs for BUG-3 eligibility query correctness
- [ ] `backend/tests/test_csv_import.py` — stubs for BUG-4 CSV round-trip validation
- [ ] `backend/tests/test_actor_precache.py` — stubs for ENH-1 background prefetch trigger

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Portrait mode card fields visible | BUG-2 | Visual layout — requires browser/device | Open game session on mobile, switch to portrait, verify title/actor/rating/runtime/MPAA all visible on MovieCard |
| Home page button alignment | BUG-2 | Visual layout | Open home page on mobile (320–375px width), verify buttons aligned |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
