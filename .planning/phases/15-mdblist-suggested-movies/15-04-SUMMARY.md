---
plan: 15-04
status: complete
---

## Summary
- Added `tmdb_suggestions_seed_count: string | null` to `SettingsDTO` in `api.ts`
- Added `getSessionSuggestions(sessionId)` to `api` export in `api.ts`
- Added `showSuggestedOnly` state + `suggestionIds` Set (from `useQuery` keyed on `current_movie_tmdb_id`) to `GameSession.tsx`
- Updated `filteringByMark` to include `showSuggestedOnly`
- Added `.filter((m) => !showSuggestedOnly || suggestionIds.has(m.tmdb_id))` to filter chain
- Added `useEffect` to reset `showSuggestedOnly` on step advance (current_movie_tmdb_id change)
- Added conditional `✦ Suggested` toggle button (only rendered when `suggestionIds.size > 0`)
- Added `tmdb_suggestions_seed_count: ""` to `emptyForm` in `Settings.tsx`
- Added "Suggested Movies" Card section with seed depth number input (1–20, default 5)

## Verification
- `npm run build` — zero TypeScript errors, built in 6.39s
- Commit: ebe332f
