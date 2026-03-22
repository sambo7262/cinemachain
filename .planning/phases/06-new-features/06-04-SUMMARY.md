---
phase: 06-new-features
plan: "04"
subsystem: frontend
tags: [dialog, ui, radarr, movie-selection]
dependency_graph:
  requires: [06-02, 06-03]
  provides: [movie-splash-dialog, skip-radarr-support]
  affects: [GameSession.tsx, api.ts]
tech_stack:
  added: []
  patterns: [shadcn Dialog, Checkbox, controlled state, async mutation]
key_files:
  created: []
  modified:
    - frontend/src/pages/GameSession.tsx
    - frontend/src/lib/api.ts
decisions:
  - "Random pick 'Request This Movie' closes random dialog then opens splash (consistent UX — user sees full movie info before confirming)"
  - "Radarr notification suppressed when skip_radarr is true (no misleading toast)"
  - "handleMovieConfirm refactored to open-only; handleSplashConfirm handles all API logic"
metrics:
  duration: "3m 15s"
  completed: "2026-03-22"
  tasks_completed: 1
  files_changed: 1
---

# Phase 06 Plan 04: Movie Selection Splash Dialog Summary

Movie selection splash dialog replaces window.confirm with a rich Dialog showing poster (w-32), TMDB rating/MPAA/runtime/year badges, full overview text, TMDB external link, and Radarr checkbox — controlled by splashOpen/splashMovie/radarrChecked state in GameSession.tsx.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Movie Selection Splash Dialog | 58c42dc | frontend/src/pages/GameSession.tsx |

## What Was Built

- **Splash Dialog:** `Dialog open={splashOpen}` with `max-w-2xl` DialogContent
- **Poster:** `https://image.tmdb.org/t/p/w185{poster_path}` at `w-32 rounded-md object-cover`; fallback "No poster" placeholder
- **Badge row:** TMDB rating (with Star icon), MPAA rating, runtime (Xh Ym format), year — all `variant="outline" text-xs`
- **Overview:** Full text, no truncation, `text-sm leading-relaxed`
- **TMDB link:** `ExternalLink w-3 h-3` with proper `aria-label` including movie title and "opens in new tab"
- **Radarr checkbox:** `id="radarr-checkbox"` with `htmlFor` label, checked by default, description copy from UI-SPEC
- **Buttons:** "Keep Browsing" (outline) dismisses, "Add to Session" (default/primary) triggers `handleSplashConfirm`
- **API:** `skip_radarr` param added to `requestMovie`, `renameSession` PATCH function added

## API Changes

`api.requestMovie` signature extended:
```typescript
body: { movie_tmdb_id: number; movie_title: string; skip_actor?: boolean; skip_radarr?: boolean }
```

`api.renameSession` added:
```typescript
renameSession: (sessionId: number, name: string) => apiFetch<GameSessionDTO>(...)
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- `skip_radarr` and `renameSession` were already present in `api.ts` HEAD (committed by another parallel wave 2 agent). The Edit tool confirmed the values matched, resulting in no net change to api.ts in this commit.
- Random Pick "Request This Movie" button simplified from async try/catch to synchronous close + open splash pattern.

## Self-Check: PASSED

- frontend/src/pages/GameSession.tsx: FOUND
- Commit 58c42dc: FOUND
