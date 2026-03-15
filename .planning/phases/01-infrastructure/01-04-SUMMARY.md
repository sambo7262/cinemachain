---
phase: 01-infrastructure
plan: 04
subsystem: infra
tags: [tailscale, docker-compose, ts-serve, volumes, nginx, postgres]

# Dependency graph
requires:
  - phase: 01-02
    provides: "compose.yaml with tailscale service and volume structure"
  - phase: 01-03
    provides: "FastAPI backend with GET /health endpoint"
provides:
  - "frontend/ts-serve.json: Tailscale Serve config routing HTTPS 443 to backend port 8000"
  - "volumes/tailscale/.gitkeep and volumes/postgres/.gitkeep: directory structure in repo"
  - "compose.yaml tailscale service with ts-serve.json volume mount"
  - "Verified running stack (pending NAS cold-boot by operator)"
affects:
  - 02-data-foundation
  - all future phases requiring deployed stack

# Tech tracking
tech-stack:
  added: [tailscale-serve-config]
  patterns:
    - "ts-serve.json HTTPS proxy pattern: TCP 443 HTTPS → Web handler → Proxy http://127.0.0.1:8000"
    - "Tailscale Serve config mounted read-only into container at /config/ts-serve.json"
    - "volumes/.gitkeep pattern: track directory structure without committing NAS bind-mount data"
    - ".gitignore volumes/*/.gitkeep negation: exclude volume data, preserve directory markers"

key-files:
  created:
    - frontend/ts-serve.json
    - volumes/tailscale/.gitkeep
    - volumes/postgres/.gitkeep
  modified:
    - compose.yaml
    - .gitignore

key-decisions:
  - "ts-serve.json uses placeholder <tailnet> — operator must replace with actual tailnet domain name from Tailscale admin console"
  - ".gitignore updated: volumes/*/* excluded, volumes/*/.gitkeep allowed — enables directory structure tracking without NAS data"
  - "ts-serve.json Web key hostname uses cinemachain (matches compose.yaml hostname: cinemachain field)"

patterns-established:
  - "Tailscale Serve config: Web key hostname must match container hostname field in compose.yaml"
  - "ts-serve.json mounted read-only at TS_SERVE_CONFIG path inside Tailscale container"

requirements-completed: [INFRA-04]

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 1 Plan 04: Tailscale Serve Config and Stack Boot Summary

**Tailscale Serve config (ts-serve.json) wired to backend, volume directory markers committed, compose.yaml updated — NAS cold-boot and Tailscale verification pending operator action**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-15T05:41:57Z
- **Completed:** 2026-03-15T05:50:00Z
- **Tasks:** 1 of 3 auto-tasks completed; blocked at NAS authentication gate
- **Files modified:** 4

## Accomplishments

- Created `frontend/ts-serve.json` with correct Tailscale Serve structure: TCP 443 HTTPS, Web handler proxying `/` to `http://127.0.0.1:8000`
- Added `./frontend/ts-serve.json:/config/ts-serve.json:ro` volume mount to tailscale service in `compose.yaml`
- Created `volumes/tailscale/.gitkeep` and `volumes/postgres/.gitkeep` to track directory structure in repo
- Fixed `.gitignore` to allow `.gitkeep` tracking inside `volumes/` while still excluding NAS data files

## Task Commits

1. **Task 1: Tailscale Serve config, volume placeholders, compose.yaml mount** — `589e0b0` (feat)

Task 2 (cold-boot) and Task 3 (checkpoint:human-verify) require NAS execution — see User Setup Required below.

## Files Created/Modified

- `frontend/ts-serve.json` — Tailscale Serve routing config; operator must replace `<tailnet>` with actual tailnet domain
- `compose.yaml` — tailscale service gains `./frontend/ts-serve.json:/config/ts-serve.json:ro` volume mount
- `volumes/tailscale/.gitkeep` — placeholder for NAS bind-mount directory tracking
- `volumes/postgres/.gitkeep` — placeholder for NAS bind-mount directory tracking
- `.gitignore` — updated `volumes/` pattern from blanket exclusion to allow `.gitkeep` files

## Decisions Made

- ts-serve.json written with `cinemachain.<tailnet>.ts.net:443` placeholder — the `<tailnet>` portion is user-specific and must be replaced. The `cinemachain` hostname is fixed (matches `hostname: cinemachain` in compose.yaml tailscale service).
- `.gitignore` pattern changed from `volumes/` (blanket) to `volumes/*/*` with `!volumes/*/.gitkeep` negation — gitignore cannot un-ignore files inside an excluded directory, so the directory itself must be tracked while only its data contents are excluded.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed .gitignore preventing volume .gitkeep files from being committed**
- **Found during:** Task 1 (commit attempt)
- **Issue:** `.gitignore` had `volumes/` which excluded the entire directory including `.gitkeep` placeholders the plan required to be tracked
- **Fix:** Changed to `volumes/*/*` with `!volumes/*/.gitkeep` negation — excludes data files inside subdirs, allows `.gitkeep` markers
- **Files modified:** `.gitignore`
- **Verification:** `git check-ignore` confirmed `.gitkeep` no longer ignored; `git add volumes/tailscale/.gitkeep` succeeded
- **Committed in:** `589e0b0` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix necessary to satisfy plan artifact requirement for volume directory tracking. No scope creep.

## Issues Encountered

Task 2 (cold-boot sequence) could not execute: Docker is not available in the development environment and no `.env` file with real credentials exists. This is expected — the stack runs on the Synology NAS. The plan's `user_setup` frontmatter documents the required NAS configuration steps.

## User Setup Required

The operator must complete these steps on the NAS before the stack can boot:

**Step 1 — NAS SSH setup (one-time):**
```bash
ssh your_nas_user@<nas-ip>
mkdir -p /volume1/docker/appdata/cinemachain/postgres \
         /volume1/docker/appdata/cinemachain/tailscale \
         /volume1/docker/appdata/cinemachain/backend
chown -R 999:999 /volume1/docker/appdata/cinemachain/postgres
id your_docker_username  # note uid and gid for PUID/PGID
```

**Step 2 — Edit ts-serve.json (replace tailnet placeholder):**
Open `frontend/ts-serve.json` and replace `<tailnet>` with your actual tailnet domain.
Find it at: Tailscale Admin Console → Machines → look for `cinemachain.<tailnet>.ts.net`

**Step 3 — Create .env file on NAS:**
```bash
cp .env.example .env
# Fill in: DB_PASSWORD, PUID, PGID, TS_AUTHKEY, TMDB_API_KEY, PLEX_TOKEN,
#           PLEX_URL, RADARR_URL, RADARR_API_KEY, SONARR_URL, SONARR_API_KEY
```

**Step 4 — Get TS_AUTHKEY:**
Tailscale Admin Console → Settings → Keys → Generate auth key (reusable, pre-authorized)

**Step 5 — Cold-boot the stack:**
```bash
docker compose up -d --build
docker compose ps  # wait for postgres healthy, all containers running
docker compose exec backend curl -s http://localhost:8000/health
# Expected: {"status":"ok","db":"ok"}
docker compose exec backend pytest tests/ -v
```

**Step 6 — Verify Tailscale remote access (from another device on your Tailscale network):**
```bash
curl https://cinemachain.<your-tailnet>.ts.net/health
# Expected: {"status":"ok","db":"ok"}
```

## Next Phase Readiness

- All repo artifacts for Phase 1 are committed — stack configuration is complete
- Phase 2 (Data Foundation) can begin planning once the operator confirms the stack boots successfully
- Blocker: operator must complete NAS setup and confirm stack health before Phase 2 execution

---
*Phase: 01-infrastructure*
*Completed: 2026-03-15*
