---
phase: 14
slug: mdblist-watched-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_mdblist.py -x` |
| **Full suite command** | `pytest backend/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_mdblist.py -x`
- **After every plan wave:** Run `pytest backend/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | MDBSYNC-01 | unit stub | `pytest backend/tests/test_mdblist.py::test_realtime_push_enqueued_on_mark_watched -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | MDBSYNC-01 | unit stub | `pytest backend/tests/test_mdblist.py::test_realtime_push_enqueued_on_query_mode_watched -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 0 | MDBSYNC-01 | unit stub | `pytest backend/tests/test_mdblist.py::test_realtime_push_skipped_when_unconfigured -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 0 | MDBSYNC-01 | unit stub | `pytest backend/tests/test_mdblist.py::test_synced_at_written_on_success_only -x` | ❌ W0 | ⬜ pending |
| 14-01-05 | 01 | 0 | MDBSYNC-02 | unit stub | `pytest backend/tests/test_mdblist.py::test_bulk_sync_queries_unsynced -x` | ❌ W0 | ⬜ pending |
| 14-01-06 | 01 | 0 | MDBSYNC-02 | unit stub | `pytest backend/tests/test_mdblist.py::test_watched_sync_status_endpoint -x` | ❌ W0 | ⬜ pending |
| 14-01-07 | 01 | 0 | MDBSYNC-02 | unit stub | `pytest backend/tests/test_settings.py::test_settings_accepts_mdblist_list_id -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_mdblist.py` — append MDBSYNC-01 and MDBSYNC-02 stubs (asyncpg-skip pattern)
- [ ] `backend/tests/test_settings.py` — append `test_settings_accepts_mdblist_list_id` stub

*Existing test files extended — no new files required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-time push fires on NAS when marking watched | MDBSYNC-01 | Requires live MDBList list + API key configured | Mark a movie watched in game mode; check NAS container logs for push log line; verify movie appears in MDBList list |
| Bulk sync pushes all 150+ existing WatchEvents | MDBSYNC-02 | Requires live NAS with real WatchEvent rows | Run bulk sync from Settings; confirm progress bar reaches 100%; check MDBList list for movies |
| Settings list ID field saves and loads | MDBSYNC-02 | Frontend Settings page interaction | Enter a list ID, save, reload page — field shows saved value |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
