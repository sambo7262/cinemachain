---
plan: 11-02
status: complete
---

## Summary
Implemented frontend Save/Shortlist features for Phase 11.

## Completed
- Extended EligibleMovieDTO with saved/shortlisted boolean fields in api.ts
- Added 5 new API functions: saveMovie, unsaveMovie, addToShortlist, removeFromShortlist, clearShortlist
- Added showSavedOnly and showShortlistOnly state variables
- Added 5 TanStack Query mutations with eligibleMovies query invalidation
- Added toggleSave, toggleShortlist helper functions + shortlistedCount computed value
- Extended filteredMovies chain with saved/shortlisted filter passes
- Added Saved/Shortlist toggle buttons and Clear Shortlist button to filter bar
- Applied amber/blue row tints to saved/shortlisted movies (literal Tailwind classes)
- Added Star/ListCheck icon overlays on poster cells with stopPropagation
- Updated splash dialog DialogHeader with save star toggle
- Added filter-aware empty state messages
- Added setShowShortlistOnly(false) reset after successful movie pick

## Verification Results

TypeScript check: PASS (no errors)

Build output:
```
vite v6.4.1 building for production...
✓ 1908 modules transformed.
dist/index.html                   0.47 kB │ gzip:   0.30 kB
dist/assets/index-D0jFnoP0.css   29.42 kB │ gzip:   6.04 kB
dist/assets/index-CQIBSsEg.js   454.33 kB │ gzip: 138.38 kB
✓ built in 4.15s
```

Grep checks:
- showSavedOnly: present at lines 45, 188, 868, 957, 960
- toggleSave/toggleShortlist: present at lines 412, 420, 1063, 1073, 1171
- bg-amber-500/10 and bg-blue-500/10: literal strings at lines 1046, 1047
- saveMovie/addToShortlist: present in api.ts at lines 290, 296

## Commits
- 064eb01: feat(11-02): extend EligibleMovieDTO and add save/shortlist API functions
- 9b89ca0: feat(11): frontend save/shortlist — icons, mutations, filter toggles, row tints, splash star

## Known Stubs
None — all fields wired to actual API calls. The backend endpoints are implemented in Phase 11 Plan 01.
