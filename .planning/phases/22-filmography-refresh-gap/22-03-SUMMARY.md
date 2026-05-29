---
phase: 22-filmography-refresh-gap
plan: 03
subsystem: ui
tags: [react, typescript, settings, cache, tmdb, manual-refresh]

# Dependency graph
requires:
  - phase: 22-filmography-refresh-gap
    provides: "POST /cache/actors/refresh-now backend endpoint (Plan 22-02, executed in parallel worktree)"
provides:
  - "api.cache.refreshActorsNow() client method on the frontend api namespace"
  - "Refresh actor filmographies button in the Settings TMDB Card, sibling to Run TMDB Cache Now"
  - "Shared cacheRunning state machine drives disable + label for both cache-action buttons"
affects:
  - "22-04 (human verification — verifies button triggers force refresh on live NAS and Devil Wears Prada 2 appears in Meryl Streep filmography)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared backend _cache_state.running → single React useState mirrors both cache-action endpoints"
    - "Sibling buttons inside same space-y-2 div share the trailing 'Last run:' timestamp paragraph"

key-files:
  created: []
  modified:
    - "frontend/src/lib/api.ts (+1 line — refreshActorsNow inside api.cache namespace)"
    - "frontend/src/pages/Settings.tsx (+18 lines — handleRefreshActorsNow handler + second Button JSX)"

key-decisions:
  - "Reuse cacheRunning / cacheLastRunAt / cacheLastDurationS state machine across both buttons — backend shares _cache_state, so a single polling effect covers both endpoints; introducing per-endpoint state would have been wasted complexity (Decision 5 in CONTEXT.md)"
  - "Place new button as a sibling INSIDE the existing space-y-2 pt-1 div so the shared 'Last run:' line below covers either run; gap between buttons handled via className=ml-2 on the new button"
  - "Silently swallow errors in handler (matches handleRunCacheNow convention) — polling effect re-enables the button on next status tick when running=false, so a thrown 409/network error degrades gracefully"
  - "Did NOT create new vitest specs — plan acceptance criteria explicitly waive new tests for this plan (behaviour is human-verified end-to-end in Plan 22-04)"

patterns-established:
  - "Twin cache-action buttons pattern: when a backend endpoint shares the same in-memory state guard as an existing endpoint, the frontend can expose a second trigger with zero new state machinery"

requirements-completed: [STALE-03]

# Metrics
duration: ~25min
completed: 2026-05-29
---

# Phase 22 Plan 03: Manual Actor Filmography Refresh Button Summary

**Refresh actor filmographies button wired into Settings, reusing the existing cacheRunning state machine to drive disable + 'Refreshing...' label without new polling infrastructure**

## Performance

- **Duration:** ~25 min (includes path-recovery from initial absolute-path mistake — see Issues Encountered)
- **Started:** 2026-05-29T21:08:00Z
- **Completed:** 2026-05-29T21:33:00Z
- **Tasks:** 2 (both complete)
- **Files modified:** 2

## Accomplishments

- `api.cache.refreshActorsNow()` exposes the new Plan 22-02 endpoint with the same `{started?, running?}` response shape as `runNow()`
- "Refresh actor filmographies" button rendered in the TMDB Card directly beside "Run TMDB Cache Now", spaced with `ml-2`
- New button disables and flips its label to "Refreshing..." while `cacheRunning` is true — both buttons share state because the backend shares `_cache_state` between both endpoints
- Shared "Last run:" / duration paragraph below the buttons covers either run, no UI duplication
- TypeScript build (`npx tsc --noEmit`) passes cleanly

## Task Commits

Each task was committed atomically on `worktree-agent-a530e16fd90373a59`:

1. **Task 1: Add api.cache.refreshActorsNow()** — `88ecbd5` (feat)
2. **Task 2: Add Refresh actor filmographies button to Settings** — `eefa8d8` (feat)

Plan metadata commit appended after this SUMMARY is written.

## Files Created/Modified

- `frontend/src/lib/api.ts` — added `refreshActorsNow: () => apiFetch<{ started?: boolean; running?: boolean }>("/cache/actors/refresh-now", { method: "POST" })` inside the existing `cache: { ... }` namespace, between `runNow` and `getStatus`
- `frontend/src/pages/Settings.tsx` — added `handleRefreshActorsNow` async handler directly after `handleRunCacheNow` (line 283); added second `<Button>` inside the existing `<div className="space-y-2 pt-1">` block (line ~431) with `className="ml-2"` for horizontal spacing

## Diff Summary

### `frontend/src/lib/api.ts`

```diff
   cache: {
     runNow: () => apiFetch<{ started?: boolean; running?: boolean }>("/cache/run-now", { method: "POST" }),
+    refreshActorsNow: () => apiFetch<{ started?: boolean; running?: boolean }>("/cache/actors/refresh-now", { method: "POST" }),
     getStatus: () => apiFetch<{ running: boolean; last_run_at: string | null; last_run_duration_s: number | null }>("/cache/status"),
   },
```

### `frontend/src/pages/Settings.tsx` — handler

```diff
   const handleRunCacheNow = async () => {
     try {
       await api.cache.runNow()
       setCacheRunning(true)
     } catch {
       // silently fail
     }
   }

+  const handleRefreshActorsNow = async () => {
+    try {
+      await api.cache.refreshActorsNow()
+      setCacheRunning(true)
+    } catch {
+      // silently fail — user will see button re-enabled on next poll
+    }
+  }
+
   const handleRefreshDbHealth = async () => {
```

### `frontend/src/pages/Settings.tsx` — JSX

```diff
   {/* TMDB on-demand run */}
   <div className="space-y-2 pt-1">
     <Button
       variant="outline"
       size="sm"
       disabled={cacheRunning}
       onClick={handleRunCacheNow}
     >
       {cacheRunning ? "Running..." : "Run TMDB Cache Now"}
     </Button>
+    <Button
+      variant="outline"
+      size="sm"
+      disabled={cacheRunning}
+      onClick={handleRefreshActorsNow}
+      className="ml-2"
+    >
+      {cacheRunning ? "Refreshing..." : "Refresh actor filmographies"}
+    </Button>
     {cacheLastRunAt && (
       <p className="text-xs text-muted-foreground">
         Last run: {new Date(cacheLastRunAt).toLocaleString()}
         {cacheLastDurationS != null ? ` (${cacheLastDurationS.toFixed(0)}s)` : ""}
       </p>
     )}
   </div>
```

## Verification

### Acceptance grep checks (Task 1 — api.ts)

| Check | Expected | Actual |
|---|---|---|
| `refreshActorsNow` present | 1 hit | 1 hit (line 403) |
| `/cache/` path count | 3 (run-now, actors/refresh-now, status) | 3 |
| `runNow` signature preserved | exact match | exact match |

### Acceptance grep checks (Task 2 — Settings.tsx)

| Check | Expected | Actual |
|---|---|---|
| `const handleRefreshActorsNow = async` | 1 hit | 1 hit (line 283) |
| `await api.cache.refreshActorsNow()` | 1 hit | 1 hit (line 285) |
| `"Refresh actor filmographies"` label | 1 hit | 1 hit (line 438) |
| `"Refreshing..."` running-state label | ≥1 hit | 2 hits (line 438 new button + line 504 existing MDBList backfill — unrelated) |
| `onClick={handleRefreshActorsNow}` | 1 hit | 1 hit (line 435) |
| `disabled={cacheRunning}` count | ≥2 | 2 |
| `"Run TMDB Cache Now"` preserved | 1 hit | 1 hit (line 429) |
| `<Button` total tags | prior + 1 | 8 (was 7) |
| Polling effect `if (!cacheRunning) return` intact | present | present (line 176) |

### Type safety + tests

- `cd frontend && npx tsc --noEmit` → **EXIT 0** (clean)
- `cd frontend && npx vitest run` → 3 test files failed / 4 passed (8 tests failed / 16 passed). **All 8 failures are pre-existing and unrelated to this plan** — they live in `ChainHistory.test.tsx`, `RatingsBadge.test.tsx`, and `GameLobby.test.tsx`, none of which import api.cache, Settings.tsx, or any file modified by this plan. These are known intentionally-RED TDD stubs / drift from prior phases (per STATE.md decisions 03.2-01, 04.2-01). Plan 22-03 acceptance criteria explicitly waive new tests for this plan: end-to-end behaviour is human-verified in Plan 22-04.

## Decisions Made

None beyond the plan — Decision 5 in CONTEXT.md already covered the architectural choice to reuse `cacheRunning` and the shared `_cache_state`. Execution mirrored the existing "Run TMDB Cache Now" pattern exactly as specified.

## Deviations from Plan

None — plan executed exactly as written. Both tasks landed with the prescribed handler shape, button props, and JSX placement.

**Total deviations:** 0
**Impact on plan:** No scope creep, no auto-fixes required.

## Issues Encountered

**Worktree path-routing mistake (recovered, no impact on output):**
During Task 1's initial Edit call, I used the absolute path `/Users/Oreo/Projects/CinemaChain/frontend/src/lib/api.ts` — that resolved to the **main repo** checkout, not the worktree's path at `.claude/worktrees/agent-a530e16fd90373a59/frontend/src/lib/api.ts` (per the documented #3099 trap in `worktree-path-safety.md`). The first commit landed on `main` instead of the worktree branch. Recovery:

1. `git reset --soft HEAD~1` in the main checkout to undo the errant commit
2. `git restore --staged` + `git checkout --` to revert api.ts in main back to baseline
3. Re-applied the Edit using the correct worktree absolute path
4. Symlinked `frontend/node_modules` from main into the worktree (worktree spawned without dev deps installed) so `npx tsc --noEmit` could resolve types
5. Re-committed Task 1 on the worktree branch using `git -C "$WT_ROOT"` to immunise against cwd drift for the rest of the session
6. Verified main repo working tree returned to baseline (`grep -c refreshActorsNow ...` = 0; only pre-existing modifications to `.planning/STATE.md` remain, which are the orchestrator's pre-spawn state)

No code lost, no duplicate commits, no contamination of the parallel 22-02 worktree. The worktree branch's commit history (`88ecbd5` → `eefa8d8`) is clean and correctly scoped to this plan.

## User Setup Required

None — purely a code change. Plan 22-04 will exercise the new button end-to-end on the live NAS as part of human verification.

## Next Phase Readiness

- Frontend is wired to `POST /cache/actors/refresh-now`. Once Plan 22-02 (backend endpoint, parallel worktree) lands and Docker rebuild deploys both changes to the NAS, the manual refresh button is functional end-to-end.
- Plan 22-04 (Wave 3, human verification) is unblocked from a frontend perspective: it can verify the Settings button triggers the force-refresh pass, see "Refreshing..." state, watch the shared "Last run:" timestamp update, and confirm Meryl Streep's filmography now contains *The Devil Wears Prada 2*.

## Self-Check: PASSED

- File `frontend/src/lib/api.ts` exists with `refreshActorsNow` at line 403 — FOUND
- File `frontend/src/pages/Settings.tsx` exists with `handleRefreshActorsNow` handler at line 283 and JSX button at line ~431 — FOUND
- Commit `88ecbd5` (Task 1) — FOUND in worktree-agent-a530e16fd90373a59 history
- Commit `eefa8d8` (Task 2) — FOUND in worktree-agent-a530e16fd90373a59 history
- TypeScript build (`npx tsc --noEmit`) — EXIT 0
- Existing test suite shows no new failures introduced by this plan (8 pre-existing failures in unrelated component test files)

---
*Phase: 22-filmography-refresh-gap*
*Plan: 03*
*Completed: 2026-05-29*
