---
phase: 11
slug: session-enhancements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && pytest tests/test_game.py -x -q` |
| **Full suite command** | `cd backend && pytest -x -q && cd ../frontend && npm run test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_game.py -x -q`
- **After every plan wave:** Run `cd backend && pytest -x -q && cd ../frontend && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | SESS-01/02 | migration | `cd backend && alembic upgrade head && alembic downgrade -1` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | SESS-01/02 | unit | `cd backend && pytest tests/test_game.py -k "save" -x -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | SESS-03 | unit | `cd backend && pytest tests/test_game.py -k "shortlist" -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | SESS-01 | integration | `cd backend && pytest tests/test_game.py -k "save" -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 2 | SESS-02 | integration | `cd backend && pytest tests/test_game.py -k "request_movie" -x -q` | ✅ | ⬜ pending |
| 11-03-01 | 03 | 2 | SESS-03/04 | integration | `cd backend && pytest tests/test_game.py -k "shortlist" -x -q` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 3 | SESS-01 | e2e | manual — visual star icon on movie rows | N/A | ⬜ pending |
| 11-04-02 | 04 | 3 | SESS-02 | e2e | manual — save persists after page refresh | N/A | ⬜ pending |
| 11-05-01 | 05 | 3 | SESS-03/04 | e2e | manual — shortlist filter reduces movie list | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_game.py` — add stubs for SESS-01 through SESS-04 (save/shortlist endpoints)
- [ ] `backend/alembic/versions/0010_session_saves_shortlist.py` — migration file created by Wave 1

*Existing pytest infrastructure covers all backend test patterns. No new framework installs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Star icon renders on poster overlay | SESS-01 | CSS/visual | Load game session, verify star icon visible on each movie row thumbnail |
| Saved row gets amber tint | SESS-01 | CSS/visual | Save a movie, verify row background has amber tint |
| Shortlisted row gets blue tint | SESS-04 | CSS/visual | Shortlist a movie, verify row background has blue tint |
| Save persists after page refresh | SESS-02 | Browser state | Save a movie, refresh page, verify star is still filled gold |
| Shortlist auto-clears after movie pick | SESS-03 | Game flow | Add to shortlist, pick a movie, verify shortlist is empty next step |
| Splash dialog star icon | SESS-01 | Visual/dialog | Open splash dialog, verify star icon present and toggleable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
