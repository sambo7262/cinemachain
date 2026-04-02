---
phase: 021-pre-deploy-hardening
plan: "02"
subsystem: devops
tags: [env-cleanup, git-ops, release-prep]
dependency_graph:
  requires: []
  provides: [clean-env-examples, git-cleanup-checklist]
  affects: [backend/.env.example, .env.example]
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/phases/021-pre-deploy-hardening/21-GIT-CLEANUP.md
  modified:
    - backend/.env.example
    - .env.example
decisions:
  - "Removed Plex, Sonarr, Tailscale fields from backend/.env.example — those integrations are not part of v2"
  - "Updated SETTINGS_ENCRYPTION_KEY comment to reflect auto-generation behavior introduced in Phase 18"
  - "Git cleanup checklist is a human-only document; no destructive git commands were run by the executor"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-02"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 21 Plan 02: Env Cleanup and Git Checklist Summary

Removed orphaned Plex/Sonarr/Tailscale fields from backend/.env.example and updated the SETTINGS_ENCRYPTION_KEY comment in both .env.example files to reflect the auto-generation behavior introduced in Phase 18; wrote a human-readable git cleanup checklist for squashing v2 history and tagging v2.0.

## What Was Done

### Task 1: Clean .env.example files

`backend/.env.example` previously contained three dead sections:
- `# Plex` (PLEX_TOKEN, PLEX_URL)
- `# Sonarr` (SONARR_URL, SONARR_API_KEY)
- `# Tailscale` (TS_AUTHKEY)

All three sections and their surrounding blank lines were removed. The active v2 sections remain intact: Database, TMDB, Radarr, Synology NAS, Settings encryption key, TMDB nightly cache.

The `SETTINGS_ENCRYPTION_KEY` comment in `backend/.env.example` was updated to match the new wording (auto-generated on first run, written to `data/.encryption_key`).

The root `.env.example` encryption section heading was changed from "Settings Encryption (optional)" to "Settings Encryption" and the four comment lines were replaced to accurately describe the auto-generation behavior instead of instructing users to generate a key manually.

### Task 2: Write git cleanup checklist

`.planning/phases/021-pre-deploy-hardening/21-GIT-CLEANUP.md` was created. It contains:
- Pre-flight checklist (clean working tree, count of commits being squashed)
- Step 1: `git reset --soft v1.0` + full v2.0 commit message
- Step 2: Post-squash verification commands
- Step 3: `git push --force origin main`
- Step 4: Tag creation (`v2.0`, `latest`) and push
- Step 5: Remote verification checklist

No destructive git commands were executed during plan execution.

## Acceptance Criteria Results

| Criterion | Result |
| --------- | ------ |
| `grep -c "PLEX" backend/.env.example` = 0 | PASS |
| `grep -c "SONARR" backend/.env.example` = 0 | PASS |
| `grep -c "TS_AUTHKEY" backend/.env.example` = 0 | PASS |
| `grep -c "Tailscale" backend/.env.example` = 0 | PASS |
| DATABASE_URL still present in backend/.env.example | PASS |
| RADARR_URL still present in backend/.env.example | PASS |
| TMDB_API_KEY still present in backend/.env.example | PASS |
| `grep "Auto-generated and persisted on first run" .env.example` matches | PASS |
| `grep "data/.encryption_key" .env.example` matches | PASS |
| "(optional)" removed from encryption section heading | PASS |
| SETTINGS_ENCRYPTION_KEY= still present in .env.example | PASS |
| 21-GIT-CLEANUP.md contains `git reset --soft v1.0` | PASS |
| 21-GIT-CLEANUP.md contains `git push --force origin main` | PASS |
| 21-GIT-CLEANUP.md contains `git tag v2.0` | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- backend/.env.example verified (no Plex/Sonarr/Tailscale, active sections intact)
- .env.example verified (Auto-generated comment present, SETTINGS_ENCRYPTION_KEY= kept)
- 21-GIT-CLEANUP.md verified (all required commands present)
- Commits: 5444e5d (env cleanup), 5fd8bdd (git checklist)
