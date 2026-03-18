---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "05"
subsystem: ui
tags: [react, tailwind, fastapi, sqlalchemy, typescript, tanstack-query]

# Dependency graph
requires:
  - phase: 04-caching-ui-ux-polish-and-session-management
    provides: "04-01 through 04-04: MovieCard, MovieFilterSidebar, GameSession, backend game.py, api.ts with getSuggestions"
provides:
  - MovieCard with always-visible mpaa_rating Badge prop
  - MovieFilterSidebar refactored to plain div (no outer Collapsible), caller controls width/visibility
  - GET /sessions/{id}/suggestions backend endpoint (genre affinity algorithm, top 5 EligibleMovieResponse)
  - Suggested tab in GameSession three-tab view (Eligible Actors / Eligible Movies / Suggested)
  - Persistent desktop sidebar in Eligible Movies tab (hidden lg:block aside)
  - Mobile Filters toggle button (lg:hidden)
affects: [05-production-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Persistent sidebar: hidden lg:block aside controlled by caller, not the sidebar component itself"
    - "On-demand query: useQuery with enabled condition tied to activeTab for lazy tab data fetching"
    - "Genre affinity scoring: Python dict[str, int] frequency map from WatchEvents + session steps"

key-files:
  created: []
  modified:
    - frontend/src/components/MovieCard.tsx
    - frontend/src/components/MovieFilterSidebar.tsx
    - frontend/src/pages/GameSession.tsx
    - backend/app/routers/game.py

key-decisions:
  - "MovieFilterSidebar top-level changed from w-56 shrink-0 div to flex flex-col gap-4 p-4 — width/visibility now entirely caller-controlled"
  - "suggestions useQuery enabled only when activeTab === 'suggested' — avoids eager fetch on tab load; staleTime 30s reduces redundant refetches"
  - "Suggestions algorithm: 500 vote_count floor, genre affinity from WatchEvents + session steps genres, tie-break by vote_average desc, top 5 returned"
  - "showMobileFilters boolean state in GameSession controls aside visibility on mobile; Button lg:hidden triggers toggle"

patterns-established:
  - "Tab-gated queries: useQuery enabled tied to view+activeTab for Suggested data; pattern reusable for other lazy tabs"
  - "Persistent sidebar layout: flex flex-col lg:flex-row wrapper + hidden lg:block aside + w-full lg:w-[200px] sizing"

requirements-completed: [UX-08, UX-09]

# Metrics
duration: 20min
completed: 2026-03-17
---

# Phase 4 Plan 05: UX Polish — MPAA Badge, Persistent Sidebar, Suggested Tab Summary

**MovieCard extended with always-visible MPAA rating badge; MovieFilterSidebar made persistent on desktop with mobile toggle; three-tab GameSession view with genre-affinity suggestions endpoint (GET /sessions/{id}/suggestions)**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-17T00:00:00Z
- **Completed:** 2026-03-17T00:20:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- MovieCard now accepts `mpaa_rating?: string | null` and renders a `Badge variant="outline"` after genre badges when non-null/non-empty
- MovieFilterSidebar refactored to plain `<div className="flex flex-col gap-4 p-4">` — inner section Collapsibles (Runtime, Genre, Rating) unchanged; width/visibility delegated to caller
- GameSession Eligible Movies tab now uses `flex flex-col lg:flex-row` wrapper with persistent `<aside className="hidden lg:block">` sidebar and mobile "Filters" toggle button
- Suggested tab added as third tab alongside Eligible Actors and Eligible Movies, with loading state, "No suggestions yet" empty state, and MovieCard list with `via_actor_name` attribution
- Backend `GET /sessions/{id}/suggestions` implemented with full genre-affinity algorithm: eligible actors → candidate movies (vote_count >= 500) → genre frequency from WatchEvents + session steps → sorted top 5 EligibleMovieResponse

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend MovieCard with MPAA badge and refactor MovieFilterSidebar layout** - `f2dde04` (feat)
2. **Task 2: Add Suggested tab in GameSession, persistent sidebar layout, and backend suggestions endpoint** - `d99fc1a` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/components/MovieCard.tsx` - Added `mpaa_rating?: string | null` prop; Badge renders after genre badges
- `frontend/src/components/MovieFilterSidebar.tsx` - Top-level changed to plain flex div; removed hardcoded w-56
- `frontend/src/pages/GameSession.tsx` - activeTab union extended to include "suggested"; showMobileFilters state; MovieCard imported; suggestions useQuery; Tabs updated with third trigger + TabsContent; Eligible Movies tab layout refactored to persistent sidebar
- `backend/app/routers/game.py` - `get_suggestions` route appended after `delete_archived_session`

## Decisions Made

- MovieFilterSidebar top-level changed from `w-56 shrink-0` to `flex flex-col gap-4 p-4` — caller (GameSession) controls exact width via `<aside className="w-full lg:w-[200px] lg:flex-shrink-0">`
- suggestions useQuery enabled only when `activeTab === "suggested"` — avoids eager fetching when users never open the tab; staleTime 30s balances freshness vs redundant round-trips
- Suggestions algorithm uses 500 vote_count floor to avoid obscure films; genre affinity pulls from both lifetime WatchEvents and current session steps for personalization
- showMobileFilters state is local boolean toggled by the "Filters" Button — simple, no additional context or URL state needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — both tasks executed cleanly. All 20 backend tests passed (52 skipped locally due to asyncpg). Zero TypeScript errors reported by `tsc --noEmit --skipLibCheck`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UX-08 and UX-09 fully satisfied: MovieCard shows MPAA rating; Eligible Movies tab has persistent sidebar; Suggested tab with genre-affinity recommendations live
- Phase 5 (Production Deployment) can proceed — all Wave 3/4 UX plans complete

---
*Phase: 04-caching-ui-ux-polish-and-session-management*
*Completed: 2026-03-17*
