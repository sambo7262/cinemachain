---
phase: 12-mobile-movie-list-redesign
type: context
status: complete
requirements: [MOB-01, MOB-02, MOB-03]
---

# Phase 12 Context — Mobile Movie List Redesign

## Goal
Replace the wide horizontal table in the eligible-movies list with a card-style list that works at every viewport without horizontal scrolling. Applies to desktop and mobile — this is a universal redesign, not a mobile-only responsive patch.

## Decision Log

### Layout: Wide table → card list

The current `<table>` with `min-w-max` and 9 columns is replaced with a vertically-stacked card list. Each card has two zones:

**Left zone — Poster column:**
- Poster image fills the full left side, taller than the current 72px since row height grows with content
- Save star icon: absolute bottom-left overlay on poster (same as pre-Phase-11 original, restored)
- Shortlist icon: absolute bottom-right overlay on poster
- No change to icon behavior or colors (amber star, blue ListCheck)

**Right zone — Content column (4 rows top-to-bottom):**
1. **Title** — full weight, normal size
2. **Via actor** — smaller font, muted color (directly below title)
3. **Ratings + metadata strip** — two sides in one row:
   - Left: ratings with icons — `★ 8.1` (TMDB) · `🍅 94%` (RT)
   - Right: metadata — `1994 · 142m · R`
4. **Future ratings row** — reserved for MDBList/IMDB data in Phase 13; leave space or add as empty row now

**Dropped:** "Watched" badge — watched movies are filtered out in game mode so the badge is never needed.

### Sort controls

Column header clicks go away with the table. Replace with a **sort dropdown** in the filter bar (alongside the existing Saved ★ / Shortlist / Clear Shortlist buttons):

- Dropdown label: "Sort: Rating ↓" (shows current field + direction)
- Fields: Rating, Year, Runtime, MPAA, RT (all 5 kept)
- Direction toggle: clicking the same field flips asc/desc (same logic as current `handleSortClick`)
- Style: matches the existing Button/outline pattern used for other filter controls; use a `<select>` or shadcn DropdownMenu

### Scope

- **GameSession.tsx eligible-movies section only** — actors tab, chain history, splash dialog, filter sidebar are untouched
- Desktop gets the same card layout (not a responsive-only change)
- No backend changes required — data shape is identical

## Code Context

**File:** `frontend/src/pages/GameSession.tsx`

Current table structure (to be replaced):
```tsx
<div className="rounded-md border border-border overflow-x-auto">
  <table className="min-w-max w-full text-sm">
    <thead>...</thead>  // 9 column headers, sortable
    <tbody>
      {filteredMovies.map((movie) => (
        <tr>  // 9 <td> cells per row
          <td> poster </td>
          <td> star+shortlist icons </td>
          <td> title + TMDB link </td>
          <td> via actor </td>
          <td> ★ rating </td>
          <td> year </td>
          <td> runtime </td>
          <td> mpaa </td>
          <td> rt score </td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

Current sort state: `sortCol` ("rating"|"year"|"runtime"|"mpaa"|"rt"), `sortDir` ("asc"|"desc")
Current sort handler: `handleSortClick(col)` — toggles direction if same col, resets to desc if new col

Sort dropdown needs to expose the same `sortCol`/`sortDir` state. No backend changes.

**Existing icons in scope:** `Star`, `ListCheck` (lucide-react, already imported)

## Requirements

- **MOB-01:** Eligible movies list renders on 320px–768px with no horizontal scrolling
- **MOB-02:** All key data fields (title, actor, year, runtime, rating, RT, MPAA) visible without scrolling
- **MOB-03:** Sort controls work without column header clicks
