---
phase: 12-mobile-movie-list-redesign
plan: "01"
status: complete
subsystem: frontend
tags: [mobile, responsive, card-layout, sort-dropdown, gamesession]
dependency_graph:
  requires: [11-session-enhancements]
  provides: [card-based-eligible-movies-list, sort-dropdown]
  affects: [frontend/src/pages/GameSession.tsx]
tech_stack:
  added: []
  patterns: [shadcn-Select, absolute-overlay-icons, flex-card-layout]
key_files:
  modified:
    - frontend/src/pages/GameSession.tsx
decisions:
  - "Removed handleSortClick/sortIndicator — replaced by dropdown value split on '_' to set sortCol+sortDir"
  - "Save/shortlist icons moved to absolute poster overlays with bg-black/40 backdrop for contrast on any poster"
  - "Watched badge dropped from card layout per plan decisions"
  - "Row 4 placeholder comment reserved for Phase 13 MDBList/IMDB data"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-01T00:26:35Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 12 Plan 01: Mobile Movie List Redesign — Sort Dropdown + Card List

Card-based eligible-movies list with absolute poster icon overlays and shadcn Select sort dropdown replacing column header clicks.

## Completed Tasks

### Task 1: Add Select import and sort dropdown to filter bar

- Imported `Select, SelectContent, SelectItem, SelectTrigger, SelectValue` from `@/components/ui/select`
- Removed `handleSortClick` and `sortIndicator` helper functions (dead code)
- Added 10-option sort dropdown (5 fields × asc/desc: Rating, Year, Runtime, MPAA, RT) to filter bar before the Random button
- `onValueChange` splits value on `_` to destructure `[col, dir]`, then sets `sortCol`, `sortDir`, and resets `moviesPage` to 1
- Commit: `a5fce08`

### Task 2: Replace table with card list

- Removed `<div className="rounded-md border border-border overflow-x-auto">` + full `<table>` block
- Added `<div className="space-y-1.5">` wrapper with per-movie `<div className="flex gap-3 rounded-md border border-border">`
- Left zone: `relative flex-shrink-0 w-16` with `w-16 h-24 rounded-l-md` poster img
  - Save button: `absolute bottom-1 left-1` with `bg-black/40` backdrop; Star icon `fill-amber-400` when saved, `text-white` otherwise
  - Shortlist button: `absolute bottom-1 right-1` with `bg-black/40` backdrop; `opacity-40 pointer-events-none` at cap of 6; ListCheck icon `fill-blue-400` when shortlisted, `text-white` otherwise
- Right zone 4-row layout:
  - Row 1: title (`font-medium text-sm truncate`) + TMDB ExternalLink icon
  - Row 2: via actor (italic, muted, truncate)
  - Row 3: ratings strip — left: ★ TMDB score (`text-amber-400`) + 🍅 RT% (each only when non-null); right: year · runtime · MPAA (each only when non-null)
  - Row 4: comment placeholder reserved for Phase 13 MDBList/IMDB data
- Watched badge dropped
- `cn()` uses literal class strings `"bg-amber-500/10"` and `"bg-blue-500/10"` (not interpolated)
- Commit: `ee2a16a`

## Verification Results

```
$ npx tsc --noEmit
(exit 0 — no output)

$ npm run build
✓ 1912 modules transformed.
dist/assets/index-p0JBkbDa.js  476.33 kB │ gzip: 144.34 kB
✓ built in 4.06s

$ grep -n "overflow-x-auto|min-w-max|<table|<thead|<tbody" GameSession.tsx (eligible-movies section)
(no matches in eligible-movies section — only actors table remains, which is a separate section)

$ grep -n "space-y-1.5|absolute bottom-1 left-1|absolute bottom-1 right-1" GameSession.tsx
1016: space-y-1.5
1042: absolute bottom-1 left-1
1050: absolute bottom-1 right-1

$ grep -n "handleSortClick|sortIndicator" GameSession.tsx
(no matches)
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/pages/GameSession.tsx` — exists and modified
- Commit `a5fce08` — confirmed in git log
- Commit `ee2a16a` — confirmed in git log
- `space-y-1.5` present at line 1016
- `absolute bottom-1 left-1` present at line 1042
- `absolute bottom-1 right-1` present at line 1050
- No `handleSortClick` or `sortIndicator` in file
- No `overflow-x-auto` or `min-w-max` in eligible-movies section
