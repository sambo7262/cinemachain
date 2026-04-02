# Phase 7: Production Deployment — Context

**Gathered:** 2026-03-22 (updated; originally 2026-03-18)
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up secrets, harden the Docker Compose setup, remove dead code (Plex/Sonarr references), expose all tunable config parameters, and write a comprehensive README so that any Docker Compose user can deploy CinemaChain safely — not just Synology NAS users.

This phase does NOT add new features. It makes the existing app deployable, safe to share, and self-documenting.

</domain>

<decisions>
## Implementation Decisions

### Distribution Audience
- Target: **any Docker Compose user** on any Linux/Mac/Windows Docker host — not Synology-only
- compose.yaml must work without Synology-specific assumptions as default behavior
- Synology users should still work with minor .env overrides (no separate file needed)

### compose.yaml Genericization
- **Volume paths:** Use `${DATA_DIR:-./data}` variable substitution throughout compose.yaml
  - Default: `./data` — works on any host, no config required
  - Override: user sets `DATA_DIR=/volume1/docker/appdata/cinemachain` in their .env for NAS
  - This serves both audiences from a single compose.yaml with no changes to the file
- **Network:** Remove `synobridge` external network dependency. Replace with a compose-managed internal bridge network (e.g., `cinemachain-net`). Compose creates it automatically — zero user setup.
  - Backend reaches Radarr/Plex via LAN IPs in env vars (not Docker DNS), so network change has no functional impact
  - README documents that NAS users who want synobridge can add it as a secondary network
- **PUID/PGID:** Keep — good practice on any Linux host, not Synology-specific
  - Default to `PUID=1000 PGID=1000` in .env.example (standard Linux user)
  - Synology users override with their actual IDs from `id username`

### Dead Code Removal (Plex & Sonarr)
- Plex integration (PLEX_TOKEN, PLEX_URL) and Sonarr (SONARR_URL, SONARR_API_KEY) were fully removed from the codebase
- These env vars are **stale** — remove them from:
  - `.env.example`
  - `compose.yaml` environment section
  - `backend/app/settings.py` — `plex_token`, `plex_url`, `sonarr_url`, `sonarr_api_key` are still **required** fields; app won't start without them even though nothing calls them
- **Confirmed still present as of 2026-03-22:** all four fields in `backend/app/settings.py`, all four in `compose.yaml` environment section

### MDBList API Key (Phase 6.1 addition)
- **D-05:** MDBList API key is DB-stored via the in-app settings service (not an env var) — no `.env.example` entry needed
- No action required in this phase — correctly handled at the application layer

### Secrets Cleanup
- **CRITICAL:** `.env.example` currently has real credentials committed (TMDB API key, Plex token, Radarr/Sonarr API keys, real LAN IPs) — these must be replaced with placeholder values
- Replace all real values with clear placeholders, e.g.:
  - `TMDB_API_KEY=your_tmdb_api_key_here`
  - `RADARR_API_KEY=your_radarr_api_key_here`
  - `RADARR_URL=http://YOUR_NAS_IP:7878`
  - `DB_PASSWORD=choose_a_strong_password`
- Verify `.gitignore` covers `.env` (already does — confirm)

### Full Config Parameter Exposure in .env.example
All tunable parameters must be documented in `.env.example` with descriptions. Includes:
- **TMDB_CACHE_TIME** — time of nightly cache run (e.g., `03:00`)
- **TMDB_CACHE_TOP_N** — number of top movies to pre-fetch in nightly run (default 5000)
- **TMDB_CACHE_TOP_ACTORS** — number of popular actors to pre-warm (default 1500; from Phase 04-08, may be hardcoded — expose if so)
- **TMDB_CACHE_RUN_ON_STARTUP** — whether to run DB refresh on app launch (true/false)
- **SETTINGS_ENCRYPTION_KEY** — Fernet key for encrypting sensitive settings stored in DB (optional; leave empty to store unencrypted). Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Added in Phase 6** — currently present in `backend/.env.example` but missing from root `.env.example`
- **RADARR_QUALITY_PROFILE** — Radarr quality profile name to assign requests (default: `HD+`). Currently in `backend/app/settings.py` but missing from root `.env.example`
- **DATA_DIR** — host path for all volume bind mounts (default: `./data`)
- **PUID / PGID** — user IDs for file ownership (default: 1000/1000)
- Each var needs a one-line comment describing what it does and where to get the value

### Docker Hub Strategy
- Keep `sambo7262/cinemachain-backend:latest` and `sambo7262/cinemachain-frontend:latest` namespaces
- Mark both repos as **public** on Docker Hub so users can pull without login
- No namespace change or new org needed
- Makefile `rebuild` target stays as-is for the author's build workflow

### README
- **Depth:** Full getting-started guide — someone unfamiliar with the stack can follow it
- **Integrations covered:** TMDB (how to get API key) and Radarr (how to get API key + URL) — NOT Plex, NOT Sonarr (removed)
- **Contents:**
  1. What CinemaChain is — brief feature overview (Movie Game, actor chain mechanic)
  2. Screenshots or description of the UI
  3. Prerequisites (Docker + Docker Compose, Radarr running, TMDB account)
  4. Step-by-step setup: clone → copy .env.example → fill vars → docker compose up
  5. Variable reference (what each .env var does)
  6. Architecture overview (brief diagram or list: frontend → backend → PostgreSQL; backend → TMDB API, Radarr API)
  7. Troubleshooting section (common issues: DB not starting, Radarr not reachable, API key wrong)
- README is committed to the repo root and pushed

### Security Review Scope
- **Full audit:**
  - Grep source code for hardcoded credentials, IPs, or API keys
  - Verify `.gitignore` covers `.env` (and `.env.local`, etc.)
  - Confirm port bindings: backend (8111) and frontend (3111) on all interfaces (correct for LAN/Tailscale access); Postgres (5433) bound to `127.0.0.1` only (correct)
  - Confirm Docker images don't bake in secrets at build time (Dockerfile inspection)
  - Remove any debug endpoints or credentials from application code if found
- **Port changes:** None — current bindings are correct as-is

### Claude's Discretion
- Exact README formatting and section ordering
- Whether to use a simple ASCII architecture diagram or prose description
- How to handle the `DATA_DIR` variable in compose.yaml if Docker Compose version has any syntax constraints
- Exact placeholder text for .env.example values

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current infrastructure state
- `compose.yaml` — current compose file; genericize volumes/network
- `.env.example` — current env template; scrub real credentials, add missing vars

### Project requirements
- `.planning/REQUIREMENTS.md` — PROD-01, PROD-02, PROD-03 success criteria
- `.planning/ROADMAP.md` §Phase 5 — Success criteria and dependencies

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Makefile` — existing build targets (rebuild, up, logs); extend for any new convenience targets
- `compose.yaml` — existing compose file to be modified in-place (not replaced)
- `.env.example` — existing template to be updated

### Established Patterns
- Secrets via .env + .gitignore — already in place; this phase hardens and documents it
- `TMDB_CACHE_*` env var naming convention — follow same pattern for any newly exposed vars
- `sambo7262/cinemachain-*` image naming — keep as-is

### Integration Points
- `backend/app/settings.py` — `plex_token`, `plex_url`, `sonarr_url`, `sonarr_api_key` confirmed as required fields; must be removed (or made optional then removed) here first, then remove from `compose.yaml` and root `.env.example`
- `backend/app/services/plex.py` + `backend/tests/test_plex_webhook.py` — Plex service file still exists; assess whether to keep (dead code) or delete
- Root `.env.example` and `compose.yaml` must stay in sync — every env var passed in compose must be documented

</code_context>

<specifics>
## Specific Ideas

- User wants all tunable parameters surfaced in `.env.example` — not just API keys, but operational knobs (cache schedule, pre-fetch counts, startup behavior)
- README should be written for someone who knows Docker but may not know the arr stack deeply
- Documentation committed and pushed to the repo as part of phase execution

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-production-deployment*
*Context gathered: 2026-03-22*
