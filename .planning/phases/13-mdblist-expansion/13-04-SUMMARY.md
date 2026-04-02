---
phase: 13-mdblist-expansion
plan: "04"
subsystem: frontend
tags: [mdblist, backfill, settings, quota, polling]
dependency_graph:
  requires:
    - frontend/src/lib/api.ts (apiFetch pattern)
    - POST /api/mdblist/backfill/start (Plan 02)
    - GET /api/mdblist/backfill/status (Plan 02)
  provides:
    - Settings page backfill trigger UI with confirm dialog, progress bar, quota display
  affects:
    - frontend/src/pages/Settings.tsx
    - frontend/src/lib/api.ts
tech_stack:
  added: []
  patterns:
    - useState + useEffect polling (2s interval via setInterval)
    - api.mdblist namespace added to existing api object in api.ts
    - Tailwind progress bar: bg-primary inside bg-muted track, h-2 rounded-full
key_files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/pages/Settings.tsx
decisions:
  - Used backfillDone boolean (separate from backfillRunning) to distinguish "never run" from "just finished" — avoids showing Done state on page load
  - On-mount status fetch populates quota display even when no backfill is running
  - Confirm dialog built as inline conditional div (no shadcn AlertDialog) — consistent with simple Settings page style
metrics:
  duration: "~12 minutes"
  completed: "2026-03-31T00:00:00Z"
  tasks_completed: 1
  tasks_total: 2
  files_created: 0
  files_modified: 2
---

# Phase 13 Plan 04: Backfill Trigger UI Summary

Backfill trigger UI in Settings with confirm dialog, 2s-polling progress bar, quota counter, and completion message — wired to the Plan 02 backfill endpoints.

## What Was Built

**`frontend/src/lib/api.ts`** — Added `api.mdblist` namespace:

- `startBackfill()`: POST `/mdblist/backfill/start` — returns `{ started: boolean; total: number }`
- `getBackfillStatus()`: GET `/mdblist/backfill/status` — returns `{ running, fetched, total, calls_used_today, daily_limit }`

**`frontend/src/pages/Settings.tsx`** — Added inside the MDBList card, below the API key field:

**State added:**
- `backfillRunning: boolean` — drives button disabled state and polling
- `backfillStatus: { fetched, total, calls_used_today, daily_limit } | null` — current job + quota data
- `showConfirm: boolean` — controls confirm dialog visibility
- `backfillDone: boolean` — true after backfill completes this session, drives "Done" message

**Effects added:**
- On mount: calls `getBackfillStatus()` to pre-populate quota display and resume in-progress backfill if running
- On `backfillRunning`: polls `getBackfillStatus()` every 2000ms; sets `backfillDone=true` and clears interval when `running` goes false

**Handlers added:**
- `handleBackfillClick()`: fetches fresh status, then sets `showConfirm=true`
- `handleBackfillConfirm()`: calls `startBackfill()`, sets `backfillRunning=true`

**UI elements:**
- "Refresh Ratings Data" button — disabled and shows "Refreshing..." while `backfillRunning`
- Confirm dialog (inline div): estimated movie count, calls_used_today / daily_limit quota, yellow warning when estimated > remaining quota, Confirm + Cancel buttons
- Progress bar: `bg-primary` fill inside `bg-muted` track, `h-2 rounded-full`, width = `fetched/total * 100%`
- Progress text: "{fetched} of {total} movies updated"
- Quota counter: "{calls_used_today} / {daily_limit} API calls today"
- Completion message: "Done — {fetched} movies updated." when backfill finishes

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All UI elements are wired to live API endpoints (provided by Plan 02). The progress bar and quota counter will reflect real server state once Plan 01 migration is applied and data exists.

## Self-Check: PASSED

- frontend/src/lib/api.ts: FOUND
- frontend/src/pages/Settings.tsx: FOUND
- Commit 453c388: FOUND
- TypeScript: compiles with 0 errors
