---
phase: 10-query-mode
plan: "04"
subsystem: frontend
tags: [search, splash-dialog, state-machine, radarr, watched]
dependency_graph:
  requires: [10-03]
  provides: [QMODE-04, QMODE-05, QMODE-06]
  affects: [frontend/src/pages/SearchPage.tsx]
tech_stack:
  added: []
  patterns: [controlled-state-machine, per-branch-setTimeout, stale-closure-avoidance]
key_files:
  created: []
  modified:
    - frontend/src/pages/SearchPage.tsx
decisions:
  - "setTimeout placed per-branch in try block (not in finally) to avoid stale closure pitfall with already_in_radarr"
  - "Error paragraph moved inside DialogFooter with w-full so it spans the full footer width"
metrics:
  duration: "12 minutes"
  completed: "2026-03-31T18:13:19Z"
  tasks_completed: 1
  files_changed: 1
---

# Phase 10 Plan 04: Splash Dialog Action Button State Machine Audit — Summary

Audited and hardened the splash dialog action button state machine in `SearchPage.tsx` to exactly match the UI-SPEC contract. Four deviations were found and fixed.

## What Was Audited

Full audit of the `Dialog` component section in `SearchPage.tsx` (lines 496–635), covering:

- "Download via Radarr" button label states (default / loading / queued / already_in_radarr)
- "Watch Online" button label states (default / loading / watched)
- Error display placement and markup
- Dialog `onOpenChange` reset behavior
- Timeout durations
- Button disabled states during any loading
- `already_in_radarr` no-auto-reset guarantee

## Result: 4 Deviations Fixed

### 1. Dialog close did not reset loading flags

**Found:** `onOpenChange` only called `setRadarrStatus(null)`. `radarrLoading` and `watchedLoading` were left dirty if the user closed mid-request.

**Fix:** Added `setRadarrLoading(false)` and `setWatchedLoading(false)` alongside `setRadarrStatus(null)` inside the `if (!open)` branch.

### 2. Button disabled states only guarded their own loading flag

**Found:** Radarr button had `disabled={radarrLoading}` and Watch Online button had `disabled={watchedLoading}`. Neither guarded against the other button's loading state.

**Fix:** Both buttons now use `disabled={radarrLoading || watchedLoading}` per spec.

### 3. Error paragraph placed outside DialogFooter

**Found:** The `<p className="text-sm text-destructive">` was rendered between the poster/overview block and `<DialogFooter>` — outside the footer entirely.

**Fix:** Moved the error paragraph inside `<DialogFooter>` as its first child, with `w-full` so it spans the full-width row above the action buttons.

### 4. `already_in_radarr` auto-reset bug (stale closure)

**Found:** The Radarr handler used a `finally` block with `if (radarrStatus !== "error") { setTimeout(..., 2000) }`. This check read the stale closure value of `radarrStatus` (always `null` at the time `finally` ran, since `setRadarrStatus` is async). The condition was always `null !== "error" = true`, so the 2-second auto-reset fired for `already_in_radarr` — violating the spec.

**Fix:** Removed the `setTimeout` from `finally`. Each branch in `try` now owns its own `setTimeout` exactly where the spec requires it:
- `queued` branch: `setRadarrStatus("queued")` + `setTimeout(() => setRadarrStatus(null), 2000)`
- `already_in_radarr` branch: `setRadarrStatus("already_in_radarr")` — no setTimeout
- `error` branch: `setRadarrStatus("error")` — no setTimeout

The Watch Online handler also had its `setTimeout` in `finally`; moved it into the `try` block after `setRadarrStatus("watched")` for consistency and clarity.

## Items Confirmed Correct (no changes)

- Timeout duration is 2000ms (not 3000ms)
- All button labels match the UI-SPEC exactly
- Close button is never disabled
- Error message text matches spec exactly: "Request failed. Try again or check Radarr."

## Verification

```
TypeScript: npx tsc --noEmit  →  0 errors
Tests:      npm test -- --run SearchPage  →  5/5 passed
```

## Commit

`50a79fe` — fix(10-04): harden splash action button state machine per UI-SPEC

## Deviations from Plan

None — the plan anticipated this task as a verification-and-fix pass. All four issues above were deviations in the previously written code (from Plan 10-03), caught and corrected here as intended.

## Self-Check: PASSED

- `frontend/src/pages/SearchPage.tsx` — confirmed modified
- Commit `50a79fe` — confirmed in git log
- TypeScript clean — confirmed
- 5 tests passing — confirmed
