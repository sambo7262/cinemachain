---
phase: 021-pre-deploy-hardening
plan: 01
subsystem: settings
tags: [api-validation, settings, backend, frontend]
dependency_graph:
  requires: []
  provides: [POST /settings/validate, POST /settings/validate/{service}, per-card test buttons]
  affects: [frontend/src/pages/Settings.tsx, backend/app/routers/settings.py]
tech_stack:
  added: []
  patterns: [masked-sentinel resolution, structured service result dicts, per-card validation state]
key_files:
  created: []
  modified:
    - backend/app/services/tmdb.py
    - backend/app/services/radarr.py
    - backend/app/services/mdblist.py
    - backend/app/routers/settings.py
    - frontend/src/lib/api.ts
    - frontend/src/pages/Settings.tsx
decisions:
  - "Used standalone test_mdblist_connection() function (not class method) to match existing module pattern"
  - "TMDBClient and RadarrClient both have close() methods — used try/finally pattern to ensure cleanup"
  - "onSuccess made async to support await api.validateAllServices() after save"
  - "Silent fallback to initialValidation on validateAllServices failure — settings were still saved"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-04-02"
  tasks: 2
  files_modified: 6
---

# Phase 21 Plan 01: API Key Test-Connection Buttons Summary

API key validation (test-connection) added for all three services (TMDB, Radarr, MDBList) — per-card test buttons with green/yellow/red feedback states plus auto-validate on save using masked sentinel resolution to test stored DB keys without requiring re-entry.

## What Was Done

### Task 1: Backend — service test methods + validate endpoint

Added `test_connection()` to `TMDBClient` in `tmdb.py` — hits `/authentication` endpoint, raises on failure.

Added `test_connection()` to `RadarrClient` in `radarr.py` — three-step check: URL reachable, API key accepted (system/status), quality profile exists. Returns structured `{"ok", "error", "warning"}` dict. Profile mismatch is a warning not an error.

Added `test_mdblist_connection(api_key)` standalone function in `mdblist.py` — lightweight call to `https://mdblist.com/api/user` endpoint.

Added to `settings.py`:
- `ValidateRequest` and `ServiceResult` Pydantic models
- `_resolve_key()` helper that falls back to stored DB value when submitted value is a masked sentinel or None
- `_test_tmdb()`, `_test_radarr()`, `_test_mdblist()` private async helpers
- `POST /settings/validate` — tests all three services, returns `dict[str, ServiceResult]`
- `POST /settings/validate/{service}` — tests a single named service, returns `ServiceResult`

### Task 2: Frontend — per-card test buttons + auto-validate on save

Added to `api.ts`:
- `ServiceValidationResult` interface and `ValidateAllResponse` type
- `api.validateService(service, settings)` — POST to `/settings/validate/{service}`
- `api.validateAllServices(settings)` — POST to `/settings/validate`

Added to `Settings.tsx`:
- `ValidationState` type with `idle | testing | ok | error | warning` status
- `ValidationBadge` component — outline button with dynamic label + optional error/warning message below
- Per-service state: `tmdbValidation`, `radarrValidation`, `mdblistValidation`
- `handleTest(service)` — sets testing state, calls API, updates state with result
- `saveMutation.onSuccess` made async — after save, auto-validates all three services and updates per-card state
- `ValidationBadge` placed at bottom of TMDB, MDBList, and Radarr cards

## Acceptance Criteria

All criteria passed:
- `test_connection` in tmdb.py: 1 match
- `test_connection` in radarr.py: 1 match
- `test_mdblist_connection` in mdblist.py: 1 match
- `validate_all` in settings.py: 1 match
- `validate_service` in settings.py: 1 match
- `_resolve_key` in settings.py: 7 matches
- `ServiceResult` in settings.py: 18 matches
- `is_masked_sentinel` used in key resolution: confirmed
- `/authentication` in tmdb.py: confirmed
- `system/status` in radarr.py: confirmed
- `mdblist.com/api/user` in mdblist.py: confirmed
- `ValidationState` in Settings.tsx: 6 matches
- `ValidationBadge` in Settings.tsx: 4 matches (1 definition + 3 usages)
- `validateService` in api.ts: 1 match
- `validateAllServices` in api.ts: 1 match
- TypeScript compilation: 0 errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
