---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "06"
subsystem: frontend
tags: [session-management, ux, delete, dialog, dropdown-menu]
dependency_graph:
  requires: ["04-01", "04-03", "04-04"]
  provides: ["SESSION-01", "SESSION-02"]
  affects: ["frontend/src/pages/GameSession.tsx", "frontend/src/pages/ArchivedSessions.tsx"]
tech_stack:
  added: []
  patterns:
    - shadcn Dialog for destructive confirmation (no window.confirm)
    - DropdownMenu for session action consolidation (Export CSV + Delete Last Step)
    - useMutation with queryClient.invalidateQueries for optimistic list removal
key_files:
  modified:
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/ArchivedSessions.tsx
decisions:
  - "Export CSV migrated from standalone header button into DropdownMenu actions menu alongside Delete Last Step"
  - "Delete Last Step disabled when session.steps.length <= 1 (cannot undo starting movie)"
  - "ArchivedSessions uses deleteSessionId: number | null pattern — single Dialog shared across all rows, opened by setting the target session ID"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-03-17"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 4 Plan 06: Session Delete Actions — Frontend Summary

**One-liner:** Wired DELETE endpoints to frontend via shadcn Dialog confirmation — GameSession gets a `...` actions menu (Export CSV + Delete Last Step), ArchivedSessions gets a per-row Delete Session button with confirmation dialog.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add session actions DropdownMenu and Delete Last Step Dialog | 542377a | frontend/src/pages/GameSession.tsx |
| 2 | Add Delete Session button and Dialog to ArchivedSessions | 999267f | frontend/src/pages/ArchivedSessions.tsx |

## What Was Built

### Task 1 — GameSession.tsx

- Added `MoreHorizontal` lucide icon + `DropdownMenu` + `Dialog` imports
- Added `deleteStepOpen: boolean` state
- Added `deleteLastStepMutation` (calls `api.deleteLastStep(sid)`, invalidates session query, closes dialog on success)
- Replaced standalone Export CSV button with `DropdownMenu` trigger (MoreHorizontal icon, `aria-label="Session actions"`)
- DropdownMenu contains: Export CSV item + separator + Delete Last Step item (disabled when `session.steps.length <= 1`)
- Delete Last Step Dialog: title "Delete Last Step", body as specified, cancel "Keep Step", confirm "Delete Step" variant="destructive"

### Task 2 — ArchivedSessions.tsx

- Added `useState`, `useMutation`, `useQueryClient` imports + `Dialog` component imports
- Added `deleteSessionId: number | null` state (null = dialog closed, session ID = dialog open for that session)
- Added `deleteSessionMutation` (calls `api.deleteSession(id)`, invalidates archivedSessions query, resets state on success)
- Added Delete Session button per session row beside View button
- Delete Session Dialog: title "Delete Session", body as specified, cancel "Keep Session", confirm "Delete Session" variant="destructive"

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] `frontend/src/pages/GameSession.tsx` — modified, committed at 542377a
- [x] `frontend/src/pages/ArchivedSessions.tsx` — modified, committed at 999267f
- [x] TypeScript: 0 errors (`npx tsc --noEmit --skipLibCheck` passes clean)
- [x] All must_haves satisfied:
  - Session home page has `...` actions menu button (MoreHorizontal icon) with Export CSV and Delete Last Step items
  - Delete Last Step triggers a shadcn Dialog with title "Delete Last Step" and confirm button "Delete Step"
  - After confirmed delete, session home page re-renders with the prior movie as current (via queryClient.setQueryData + invalidateQueries)
  - Delete Last Step menu item is disabled when session.steps.length <= 1
  - ArchivedSessions page has a "Delete Session" button per session
  - Delete Session triggers a shadcn Dialog with title "Delete Session" and confirm button "Delete Session"
  - After confirmed delete, session is removed from the archived list (via invalidateQueries archivedSessions)

## Self-Check: PASSED
