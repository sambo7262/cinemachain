---
phase: 17
slug: backend-scheduler-settings-audit
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-01
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ && cd ../frontend && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | IMDB-01 | unit | `cd backend && python -m pytest tests/ -k imdb -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | SCHED-02 | unit | `cd backend && python -m pytest tests/ -k pool -x -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 1 | SCHED-01 | unit | `cd backend && python -m pytest tests/ -k scheduler -x -q` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 2 | SCHED-03 | unit | `cd backend && python -m pytest tests/ -k settings -x -q` | ❌ W0 | ⬜ pending |
| 17-05-01 | 05 | 2 | SCHED-03 | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_phase17.py` — stubs for IMDB-01, SCHED-01, SCHED-02, SCHED-03

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Settings UI sections render correctly with masked API keys | SCHED-03 | Frontend visual | Open Settings page; verify TMDB/MDBList/Radarr sections visible; API key fields show masked input |
| DB Health section refreshes live stats | SCHED-03 | Frontend interaction | Click "Refresh Stats" button; verify table rows and table sizes appear |
| On-demand TMDB run button triggers job | SCHED-01 | Integration | Click "Run Now" in TMDB section; verify 200 response + logs show job started |
| MDBList scheduled job fires at configured time | SCHED-01 | Time-based | Set `mdblist_schedule_time` to near-future time; verify job fires and logs outcome |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
