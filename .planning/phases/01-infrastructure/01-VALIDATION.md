---
phase: 1
slug: infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `backend/pytest.ini` — Wave 0 installs |
| **Quick run command** | `docker compose exec backend pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec backend pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec backend pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose exec backend pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + all manual checks done
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | INFRA-01 | integration | `docker compose exec backend pytest tests/test_health.py -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | INFRA-02 | integration | `docker compose exec backend pytest tests/test_settings.py -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INFRA-01 | smoke | `docker compose ps --format json \| jq '.[].Status'` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | INFRA-02 | manual | see Manual-Only Verifications | manual-only | ⬜ pending |
| 1-01-05 | 01 | 1 | INFRA-03 | integration | `docker compose exec backend pytest tests/test_persistence.py -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | INFRA-04 | manual | `curl -f http://<tailscale-ip>/health` from another device | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_health.py` — stubs for INFRA-01 (`GET /health` returns `{"status":"ok","db":"ok"}`)
- [ ] `backend/tests/test_settings.py` — stubs for INFRA-02 (settings load from .env, no hardcoded values)
- [ ] `backend/tests/test_persistence.py` — stubs for INFRA-03 (PostgreSQL survives container restart)
- [ ] `backend/tests/conftest.py` — shared fixtures (async DB session, test client)
- [ ] `backend/pytest.ini` — pytest configuration (`asyncio_mode = auto`)
- [ ] `pytest pytest-asyncio httpx` added to `backend/requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No credentials in image layers | INFRA-02 | Requires Docker inspect from host | Run `docker inspect cinemachain-backend` and verify no API keys appear in Env or Cmd |
| UI reachable via Tailscale | INFRA-04 | Requires a second device on Tailscale network | From phone or laptop: `curl http://<tailscale-ip>/health` or open in browser |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
