---
phase: 06-new-features
plan: 05
subsystem: frontend
tags: [ui, session-management, archive, rename, dropdown, dialog]
requires: [06-02, 06-04]
provides: [archive-confirm-dialog, edit-name-modal, session-dropdown-extended]
affects: [frontend/src/pages/GameSession.tsx]
tech-stack:
  added: []
  patterns: [useMutation, shadcn Dialog, shadcn DropdownMenu]
key-files:
  created: []
  modified:
    - frontend/src/pages/GameSession.tsx
decisions:
  - Pre-populate editNameValue from session.name when menu item clicked
  - archiveMutation closes dialog before mutate() to avoid flicker on navigate
  - renameMutation error surfaces inline below Input, not via toast
metrics:
  duration: 1
  completed: 2026-03-22T14:40:01Z
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 6 Plan 05: Session Settings Menu — Archive + Edit Name Summary

**One-liner:** Archive confirm dialog and Edit Session Name modal added to session dropdown in GameSession.tsx, backed by existing `api.archiveSession` and `api.renameSession`.

## What Was Built

Extended the existing session DropdownMenu in `GameSession.tsx` with two new actions separated by a `DropdownMenuSeparator`:

- **Edit Session Name** — opens a modal pre-populated with the current session name; supports Enter key to submit; shows inline required-field and duplicate-name errors
- **Archive Session** — opens a destructive confirmation dialog with warning copy; navigates home on success

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Session menu extension + Archive confirm + Edit name modal | df5d7ef | frontend/src/pages/GameSession.tsx |

## Decisions Made

- **Pre-populate on menu open:** `editNameValue` is set to `session?.name ?? ""` when the Edit Session Name item is clicked, ensuring the Input is ready for editing immediately.
- **Close dialog before mutate (archive):** `setArchiveConfirmOpen(false)` is called before `archiveMutation.mutate()` to avoid the dialog lingering during navigation.
- **Inline error for rename conflict:** Error from `renameMutation.onError` is surfaced as `text-red-500 text-xs` below the Input, matching the existing validation pattern in GameLobby.tsx.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `frontend/src/pages/GameSession.tsx` exists and modified
- [x] Commit `df5d7ef` exists
- [x] TypeScript check: `npx tsc --noEmit` — no errors
- [x] Grep confirms all required strings present: `archiveConfirmOpen`, `editNameOpen`, `Archive this session?`, `Edit Session Name`, `Save Name`, `Keep Session`, `Discard Changes`
