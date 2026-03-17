---
phase: 04-caching-ui-ux-polish-and-session-management
plan: "04"
subsystem: frontend
tags: [notification, context, ui, layout, ux]
dependencies:
  requires: [04-01]
  provides: [NotificationContext, RadarrNotificationBanner, 1400px-layout, Now-Playing-poster]
  affects: [App.tsx, GameSession.tsx, GameLobby.tsx, NavBar.tsx, api.ts]
tech-stack:
  added: []
  patterns: [React context for global notification state, auto-dismiss timer with useRef, TMDB poster URL construction]
key-files:
  created:
    - frontend/src/contexts/NotificationContext.tsx
    - frontend/src/components/RadarrNotificationBanner.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/NavBar.tsx
    - frontend/src/pages/GameSession.tsx
    - frontend/src/pages/GameLobby.tsx
    - frontend/src/lib/api.ts
decisions:
  - "showRadarr() uses canonical message strings ('Already in Radarr' / 'Movie Queued for Download') to match must_haves truths exactly"
  - "radarrFallbackFiredRef and fallback useEffect removed entirely — global context handles deduplication via timer reset"
  - "Now Playing card poster uses TMDB w185 image tier (185px wide) at 120px display — correct resolution for 2x DPI"
  - "defaultTab changed from 'watched' to 'search' for both initial state and + Start a new session button"
metrics:
  duration_seconds: 185
  completed_date: "2026-03-17T23:57:20Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 7
---

# Phase 4 Plan 04: UX Polish — Notification Context, Poster, Layout Summary

**One-liner:** Global Radarr notification context with 5s auto-dismiss banner, Now Playing movie poster (120x180px), 1400px layout, and Watch History tab removal.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create NotificationContext and RadarrNotificationBanner | 7cd313d | NotificationContext.tsx, RadarrNotificationBanner.tsx |
| 2 | Update App.tsx, NavBar, GameSession.tsx, GameLobby.tsx, api.ts | b754e5a | App.tsx, NavBar.tsx, GameSession.tsx, GameLobby.tsx, api.ts |

## What Was Built

**NotificationContext.tsx** — React context providing `radarrMessage`, `showRadarr()`, and `dismissRadarr()`. `showRadarr()` resets a 5s auto-dismiss timer on every call (deduplication built-in). `useNotification()` throws if used outside the provider.

**RadarrNotificationBanner.tsx** — Full-width banner mounted immediately below NavBar in App.tsx. Returns `null` when `radarrMessage` is null (zero layout shift). `bg-blue-600 text-white` styling; X button calls `dismissRadarr()`.

**App.tsx** — Rewritten to wrap entire tree in `NotificationProvider`, mount `RadarrNotificationBanner` as a sibling after `NavBar`, and constrain page content with `max-w-[1400px] mx-auto px-6`.

**NavBar.tsx** — Inner container widened from `max-w-4xl` to `max-w-[1400px]` to align with the app content width.

**GameSession.tsx** — `radarrStatus` useState and `radarrFallbackFiredRef` useRef removed. Fallback useEffect removed. `useNotification()` imported; `showRadarr("Already in Radarr")` and `showRadarr("Movie Queued for Download")` replace the old `setRadarrStatus()` calls in `handleMovieConfirm`. Now Playing card now has a flex row layout: TMDB poster image (w-[120px] h-[180px] rounded-md object-cover) on the left; grey placeholder `div` at identical dimensions when `poster_path` is null.

**GameLobby.tsx** — Watch History tab removed: `watchedMovies` useQuery deleted, `TabsList` changed from `grid-cols-3` to `grid-cols-2`, `TabsTrigger value="watched"` and its `TabsContent` removed, `defaultTab` type narrowed to `"search" | "csv"`, initial value and `+ Start a new session` button handler both set to `"search"`.

**api.ts** — Added `deleteLastStep`, `deleteSession`, and `getSuggestions` methods.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- NotificationContext.tsx: FOUND
- RadarrNotificationBanner.tsx: FOUND
- 04-04-SUMMARY.md: FOUND
- Commit 7cd313d: FOUND
- Commit b754e5a: FOUND
