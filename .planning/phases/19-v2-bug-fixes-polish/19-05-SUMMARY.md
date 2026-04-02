---
phase: 19-v2-bug-fixes-polish
plan: 05
subsystem: ui
tags: [react, tailwind, shadcn, radix-ui, react-query, optimistic-ui, tooltips]

# Dependency graph
requires:
  - phase: 19-v2-bug-fixes-polish
    provides: Plan 03 needsAllResults variable and excludeNR query key used in optimistic updates
provides:
  - Save/shortlist buttons repositioned to right-side column on movie cards (easy tap on mobile)
  - Optimistic UI for save/shortlist mutations (immediate state update before server response)
  - RatingsBadge tooltip on each badge identifying the data source
  - Session grid tiles with no step count text
  - Active session tiles with poster thumbnail + compact Continue button
affects: [GameSession.tsx, RatingsBadge.tsx, GameLobby.tsx]

# Tech tracking
tech-stack:
  added: ["@radix-ui/react-tooltip ^1.2.8", "shadcn tooltip component"]
  patterns:
    - "Optimistic UI via onMutate + setQueriesData (partial key match) + onSettled invalidate"
    - "Radix Tooltip wrapped around each badge span in RatingsBadge"

key-files:
  created:
    - frontend/src/components/ui/tooltip.tsx
  modified:
    - frontend/src/pages/GameSession.tsx
    - frontend/src/components/RatingsBadge.tsx
    - frontend/src/pages/GameLobby.tsx

key-decisions:
  - "Used queryClient.setQueriesData with partial key { queryKey: ['eligibleMovies', sid] } to avoid key-mismatch when query key has many parameters"
  - "TooltipProvider placed at the div wrapper level (not globally) in RatingsBadge for locality"

patterns-established:
  - "Optimistic mutation pattern: onMutate cancels + updates cache, onSettled invalidates"

requirements-completed: [v2BUG-01]

# Metrics
duration: 18min
completed: 2026-04-02
---

# Phase 19 Plan 05: UI Polish Summary

**Save/shortlist buttons moved to right-side column with optimistic UI, rating badge tooltips via Radix, session tiles de-cluttered with poster thumbnail replacing step count**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-02T00:00:00Z
- **Completed:** 2026-04-02T00:18:00Z
- **Tasks:** 2
- **Files modified:** 4 (+ 1 created)

## Accomplishments
- Movie cards in GameSession now have a clean right-side action column (star + check icons) instead of overlaid poster buttons — much easier to tap on mobile
- All 4 save/shortlist mutations (save, unsave, addToShortlist, removeFromShortlist) use optimistic UI via onMutate so state updates immediately on tap
- RatingsBadge wraps each badge in a Radix Tooltip showing the source label on hover
- GameLobby session tiles no longer show step count; active sessions show a 32x48px poster thumbnail of the current movie next to a compact Continue button

## Task Commits

Each task was committed atomically:

1. **Task 1: Reposition save/shortlist buttons with optimistic UI** - `72f0e6a` (feat)
2. **Task 2: Badge tooltips, remove step count, add poster to active tiles** - `996bbd5` (feat)
3. **Chore: Add @radix-ui/react-tooltip dependency** - `6209184` (chore)

## Files Created/Modified
- `frontend/src/pages/GameSession.tsx` - Moved save/shortlist buttons to right-side action column; added optimistic onMutate to all 4 save/shortlist mutations
- `frontend/src/components/RatingsBadge.tsx` - Wrapped each badge span in Tooltip with TooltipProvider
- `frontend/src/components/ui/tooltip.tsx` - New shadcn Tooltip component (Radix-based)
- `frontend/src/pages/GameLobby.tsx` - Removed step count span; updated Continue button; added poster thumbnail
- `frontend/package.json` / `package-lock.json` - Added @radix-ui/react-tooltip dependency

## Decisions Made
- Used `queryClient.setQueriesData` with partial key `{ queryKey: ["eligibleMovies", sid] }` rather than `setQueryData` with the exact full key, to avoid fragility when the query key array has many parameters that could drift between the query and the mutation.
- `TooltipProvider` is placed inside the `RatingsBadge` component return (wrapping the badge row), not globally in the app. This keeps the tooltip config local and avoids coupling to a global provider.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved shadcn-generated tooltip.tsx to correct path**
- **Found during:** Task 2 (Badge tooltips)
- **Issue:** `npx shadcn add tooltip` wrote the file to `frontend/@/components/ui/tooltip.tsx` instead of `frontend/src/components/ui/tooltip.tsx` due to shadcn's path resolution
- **Fix:** Moved the file to the correct `src/` path; TypeScript compiled clean after move
- **Files modified:** frontend/src/components/ui/tooltip.tsx (created at correct path)
- **Verification:** `tsc --noEmit` returned no errors
- **Committed in:** 996bbd5 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — path issue)
**Impact on plan:** Minor path correction only; no scope changes.

## Issues Encountered
- shadcn CLI wrote tooltip.tsx to `frontend/@/components/ui/` instead of `frontend/src/components/ui/` — resolved by moving the file.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All D-19, D-20, D-22, D-23 UX polish items are complete
- Phase 19 plan 05 is the final plan in the wave — v2 polish pass is done

---
*Phase: 19-v2-bug-fixes-polish*
*Completed: 2026-04-02*
