---
phase: 2
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| **Config file** | `backend/pytest.ini` (`asyncio_mode = auto`) |
| **Quick run command** | `cd backend && pytest tests/test_tmdb.py tests/test_plex_webhook.py -x -q` |
| **Full suite command** | `cd backend && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q --ignore=tests/test_persistence.py`
- **After every plan wave:** Run `cd backend && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-??-01 | TBD | 0 | DATA-01,02,03 | unit | `pytest tests/test_tmdb.py -x` | ❌ W0 | ⬜ pending |
| 02-??-02 | TBD | 0 | DATA-04 | unit | `pytest tests/test_plex_sync.py -x` | ❌ W0 | ⬜ pending |
| 02-??-03 | TBD | 0 | DATA-05 | integration | `pytest tests/test_plex_webhook.py -x` | ❌ W0 | ⬜ pending |
| 02-??-04 | TBD | 0 | DATA-06 | unit | `pytest tests/test_movies.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_tmdb.py` — stubs for DATA-01 (`test_fetch_movie_details`), DATA-02 (`test_fetch_actor_credits`), DATA-03 (`test_movie_cached_on_repeat_request`)
- [ ] `backend/tests/test_plex_sync.py` — stub for DATA-04 (`test_startup_sync_marks_watched`)
- [ ] `backend/tests/test_plex_webhook.py` — stub for DATA-05 (`test_scrobble_marks_watched`)
- [ ] `backend/tests/test_movies.py` — stub for DATA-06 (`test_manual_mark_watched`)

*Existing infrastructure (`conftest.py` if present, `pytest.ini`, `pytest-asyncio`) requires no changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Plex watch sync populates DB on app startup | DATA-04 | Requires live Plex server + real library | Start app, check `/health` or DB for watch_events rows matching known watched movies |
| Webhook fires and marks movie watched | DATA-05 | Requires live Plex scrobble event | Watch a movie past 90% in Plex, confirm watch_event row created in DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
