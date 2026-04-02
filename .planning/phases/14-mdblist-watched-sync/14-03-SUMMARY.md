---
phase: 14-mdblist-watched-sync
plan: "03"
subsystem: frontend
tags: [mdblist, settings, watched-sync, ui]
dependency_graph:
  requires: [14-02]
  provides: [MDBList Watch Sync UI, WatchedSyncStatusDTO, startWatchedSync, getWatchedSyncStatus]
  affects: [frontend/src/lib/api.ts, frontend/src/pages/Settings.tsx]
tech_stack:
  added: []
  patterns: [polling useEffect at 2s interval, confirm dialog before destructive action, progress bar with percentage]
key_files:
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/pages/Settings.tsx
decisions:
  - MDBList Watch Sync card placed between the existing MDBList card and Sync Schedule card for logical grouping
  - Confirm dialog only shown when syncStatus is available (status fetch happens on click before dialog renders)
  - Progress bar and done message hidden while confirm dialog is open (avoids visual clutter)
metrics:
  duration_minutes: 10
  completed_date: "2026-04-01"
  tasks_completed: 1
  files_modified: 2
---

# Phase 14 Plan 03: MDBList Watch Sync UI Summary

MDBList Watch Sync card added to Settings page — list ID input saved via existing settings API, sync button with confirm dialog showing unsynced count and quota, polling progress bar, and completion message.

## What Was Built

### api.ts changes

- Added `mdblist_list_id: string | null` to `SettingsDTO`
- Added `export interface WatchedSyncStatusDTO` with `running`, `synced`, `total`, `calls_used_today`, `daily_limit`
- Added `startWatchedSync()` calling `POST /mdblist/watched-sync/start`
- Added `getWatchedSyncStatus()` calling `GET /mdblist/watched-sync/status`

### Settings.tsx changes

- Added `mdblist_list_id: ""` to `emptyForm` initial state
- Added four watched-sync state variables: `syncRunning`, `syncStatus`, `syncDone`, `showSyncConfirm`
- On-mount useEffect now also checks watched sync status and resumes polling if already running
- New polling useEffect fires every 2000ms while `syncRunning` is true
- `handleSyncClick`: fetches current status, opens confirm dialog, clears done flag
- `handleSyncConfirm`: calls `startWatchedSync`, sets `syncRunning = true`
- New "MDBList Watch Sync" Card inserted between the MDBList card and Sync Schedule card

### UI card contents

- `<Input id="mdblist-list-id">` for list ID entry (saved via Save Settings)
- "Sync Watched History" button (disabled while syncing)
- Confirm dialog: unsynced count, quota used/total, quota-exceeded warning, Cancel + Sync Now buttons
- Progress bar: fills to percentage of `synced / total`
- Completion message: "Done — N movies synced." in green
- Quota counter: `calls_used_today / daily_limit API calls today`

## Deviations from Plan

None — plan executed exactly as written.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | API functions and Settings Watch Sync UI | Complete | 1eb26a9 |
| 2 | Verify MDBList Watch Sync feature | Awaiting human verification | — |

## Self-Check

- [x] `frontend/src/lib/api.ts` modified and committed
- [x] `frontend/src/pages/Settings.tsx` modified and committed
- [x] Verification grep: PASS
- [x] TypeScript compile: zero errors
- [x] Commit 1eb26a9 exists
