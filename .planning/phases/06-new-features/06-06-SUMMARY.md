---
phase: 06-new-features
plan: "06"
subsystem: ui
tags: [react, shadcn, tanstack-query, settings, onboarding, lucide-react]

# Dependency graph
requires:
  - phase: 06-01
    provides: GET/PUT /api/settings and GET /api/settings/status backend endpoints

provides:
  - Settings page at /settings route with Card sections for TMDB, Radarr, Sonarr, Plex, Sync Schedule
  - OnboardingScreen component that blocks app when TMDB not configured
  - Onboarding gate in App.tsx with loading guard (no flash on startup)
  - NavBar Settings icon link with aria-label and 44px touch target
  - api.ts SettingsDTO, SettingsStatusDTO interfaces plus getSettings/saveSettings/getSettingsStatus functions

affects: [06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Settings form: single formData state object mirroring SettingsDTO, nullToEmpty() helper for null-to-string coercion"
    - "Onboarding gate: query settingsStatus in App root, return null during load, render OnboardingScreen when tmdb_configured=false"
    - "Migration notice: localStorage flag cinemachain_env_notice_dismissed to show once"

key-files:
  created:
    - frontend/src/components/OnboardingScreen.tsx
    - frontend/src/pages/Settings.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/App.tsx
    - frontend/src/components/NavBar.tsx

key-decisions:
  - "App.tsx queries settingsStatus at root level (not inside routes) so gate works before any route renders"
  - "Loading guard returns null (not spinner) to prevent flash — matches plan spec Pitfall 6"
  - "OnboardingScreen renders directly (not inside NotificationProvider) since it replaces the whole app"

patterns-established:
  - "Settings form coerces null API values to empty strings via nullToEmpty() helper for controlled inputs"
  - "Onboarding gate pattern: useQuery at App root, return null on loading, render blocking component on unconfigured"

requirements-completed: [ITEM-6-frontend]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 6 Plan 06: Settings & Onboarding Frontend Summary

**In-app settings page with Card-grouped fields, full-viewport onboarding gate, and NavBar settings link using tanstack-query for load/save**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T07:13:48Z
- **Completed:** 2026-03-22T07:15:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Settings page at /settings with five Card sections (TMDB required, Radarr, Sonarr, Plex, Sync Schedule), required field validation, success/error feedback, and .env migration notice
- OnboardingScreen blocks the entire app with a full-viewport Card when TMDB credentials are absent, invalidates settingsStatus on save to unblock automatically
- App.tsx onboarding gate with loading guard prevents flash; NavBar gains Settings icon link with proper 44px touch target and aria-label

## Task Commits

Each task was committed atomically:

1. **Task 1: API functions + OnboardingScreen + Settings page** - `078616a` (feat)
2. **Task 2: App.tsx onboarding gate + /settings route + NavBar link** - `4a9969d` (feat)

**Plan metadata:** (committed below)

## Files Created/Modified
- `frontend/src/lib/api.ts` - Added SettingsDTO, SettingsStatusDTO interfaces and getSettings/saveSettings/getSettingsStatus API functions
- `frontend/src/components/OnboardingScreen.tsx` - Blocking full-viewport onboarding with TMDB field entry and validation
- `frontend/src/pages/Settings.tsx` - Full settings page with five Card sections, form state, validation, success/error feedback, migration notice
- `frontend/src/App.tsx` - Added settingsStatus query, onboarding gate with loading guard, /settings route
- `frontend/src/components/NavBar.tsx` - Added Settings icon link (SettingsIcon from lucide-react) with aria-label and 44px touch target

## Decisions Made
- App.tsx queries settingsStatus at the root level before rendering routes so the gate works before any route is reached
- Loading guard returns `null` (no spinner) to prevent onboarding flash on startup — as specified in the plan
- OnboardingScreen renders directly outside NotificationProvider since it replaces the entire app shell; after saving it invalidates the settingsStatus query to trigger re-render automatically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Settings infrastructure fully wired: API types, page, gate, NavBar link all in place
- Plans 06-07, 06-08, 06-09 can rely on /settings route and settingsStatus query existing

---
*Phase: 06-new-features*
*Completed: 2026-03-22*
