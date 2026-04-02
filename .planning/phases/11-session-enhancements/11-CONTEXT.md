# Phase 11: Session Enhancements — Context

**Gathered:** 2026-03-31
**Status:** Ready for research

<domain>
## Phase Boundary

Add two in-session decision-making tools to Game Mode's eligible movies list:

1. **Save for later** — bookmark any movie during a session as a reminder. Persists for the full session lifetime, survives page refresh and device switches, stacks with existing filters.
2. **Shortlist** — select 2–6 (or 1) movies within the current movie-selection step to compare. Auto-clears when a movie is picked. Resets per-step, not per-session.

Both are Game Mode only. No changes to Query Mode or any other page.
</domain>

<decisions>
## Implementation Decisions

### D-01: Feature distinction — Save vs Shortlist

Two separate features with different scopes and lifecycles:

**Save for later ("Save"):**
- Purpose: cross-step bookmark — "I want to watch this if it comes up again"
- Lifecycle: persists for the entire session; auto-removed only when the saved movie is picked and added to the chain (it leaves the eligible list anyway); user can also manually toggle off
- Scope: session-wide, survives actor selection, step advances, page refreshes, and device changes
- Analogy: a wishlist that persists until consumed or dismissed

**Shortlist:**
- Purpose: per-step comparison — narrow eligible movies to 2–6 candidates for the current pick
- Lifecycle: auto-clears when a movie is selected (added to chain); resets for every new movie-selection step
- Scope: step-scoped; if user picks an actor and returns to movie selection, shortlist persists until a movie is actually selected
- Analogy: a "finalist" tray — valid only during active decision-making for the current step

### D-02: Persistence — backend storage (not localStorage)

Both Save and Shortlist must survive page refresh AND work across devices/browsers. This rules out localStorage and requires backend storage.

**Data model:**
- New `SessionSave` table: `session_id (FK)`, `tmdb_id`, `saved_at` — stores saved movies per session
- New `SessionShortlist` table: `session_id (FK)`, `tmdb_id` — stores current shortlist per session; cleared when `request_movie` is called (movie selected)

Rationale: two tables keeps lifecycle logic clean — saves accumulate, shortlist is cleared on movie selection. A single table with a `type` column would require more careful clearing logic.

**API surface (new endpoints):**
- `POST /sessions/{id}/saves/{tmdb_id}` — save a movie
- `DELETE /sessions/{id}/saves/{tmdb_id}` — un-save a movie
- `GET /sessions/{id}/saves` — list saved tmdb_ids (for hydrating UI on load)
- `POST /sessions/{id}/shortlist/{tmdb_id}` — add to shortlist
- `DELETE /sessions/{id}/shortlist/{tmdb_id}` — remove from shortlist
- `DELETE /sessions/{id}/shortlist` — clear entire shortlist ("Clear All" button)
- `GET /sessions/{id}/shortlist` — list shortlisted tmdb_ids
- Existing `POST /sessions/{id}/request_movie` — clears shortlist table as a side effect

### D-03: Save affordance

- **Movie row:** star icon overlaid on the poster thumbnail (bottom-left or bottom-right corner of poster). Outline star = unsaved; filled gold star = saved.
- **Row treatment when saved:** subtle gold tint/highlight on the movie row (not just icon — the whole row gets a faint warm background, e.g. `bg-yellow-50/30` or equivalent shadcn token).
- **Splash dialog:** small star icon toggle in the dialog header area (corner of poster or top-right of dialog). Same filled/outline state.
- **No full "Save" button** in splash — icon only (keeps splash uncluttered; two action buttons already exist in Query Mode splash; Game Mode splash has different buttons).

### D-04: Shortlist affordance

- **Movie row:** separate icon from the save star — use a checklist/compare icon (e.g. `ListCheck` or `CheckSquare` from lucide-react). Outline = not shortlisted; filled/active = shortlisted. Positioned separately from the save star on the poster overlay (or adjacent column).
- **Toggle:** click to add, click again to remove. Works like save toggle.
- **Filter:** "Shortlist" filter option in the eligible movies filter area (alongside the existing "All Movies / Unwatched Only" toggle). When active, shows only shortlisted movies. Stacks with all other filters (genre, MPAA, runtime, saved).
- **Clear All button:** appears in the filter area when shortlist filter is active, or always visible when shortlist has items. Calls `DELETE /sessions/{id}/shortlist`.

### D-05: Filter stacking

Both "Saved" and "Shortlist" filters stack with all existing filters:
- Genre checkboxes (MovieFilterSidebar)
- MPAA checkboxes
- Runtime range slider
- Unwatched Only toggle
- Search input

Stacking logic: eligible movies must satisfy ALL active filters simultaneously. No override modes.

Filter UI: add "Saved ★" and "Shortlist ✓" as toggle buttons in the filter bar, matching the style of the existing "All Movies / Unwatched Only" toggle button.

### D-06: Shortlist lifecycle — auto-clear on movie selection

When `request_movie` is called (user picks a movie and adds it to the chain):
- Backend clears the `SessionShortlist` table for that session as part of the request_movie handler
- Frontend clears shortlist state from TanStack Query cache (`queryClient.invalidateQueries(["shortlist", sid])`)
- The cleared shortlist is transparent to the user — next step starts with an empty shortlist

Save list is NOT cleared on movie selection (only the picked movie leaves the eligible list naturally).

### D-07: Saved movie when picked

When a movie is saved AND then selected as the pick:
- The `SessionSave` row is deleted as part of the `request_movie` handler (same side effect as shortlist clear)
- Rationale: the movie is now in the chain — no longer needs to be bookmarked as a reminder
- Un-save is also available manually at any time

### D-08: Gold row treatment for saved movies

Saved movies in the eligible list get a subtle warm background on their table row. Suggested: `bg-amber-500/10` (10% amber overlay) on the `<tr>` — visible but not distracting. The filled gold star icon is the primary indicator; the row tint is a secondary affordance to help the eye find saved movies when scrolling.

The shortlisted rows get a different secondary treatment — suggested: `bg-blue-500/10` (subtle blue tint) to distinguish from saved. Both can be active simultaneously (saved + shortlisted movie gets both, or a combined treatment — Claude's discretion during implementation).

</decisions>

<code_context>
## Relevant Existing Code

### Frontend — reusable

**`GameSession.tsx`** (`frontend/src/pages/GameSession.tsx`)
- Eligible movies table: `allEligibleMovies`, `allMovies` toggle, sort/filter, `moviesPage`, `debouncedSearch`
- Filter sidebar: `MovieFilterSidebar` already wired via `filters` / `setFilters` state
- Movie row rendering: lines ~830–960 (table body, poster thumbnail, title cell, etc.)
- `handleMovieConfirm` (or equivalent) — where `request_movie` is called; shortlist/save clear hooks here
- `queryClient.invalidateQueries` already used for eligible movies and actors

**`MovieFilterSidebar.tsx`** (`frontend/src/components/MovieFilterSidebar.tsx`)
- Current filters: genre checkboxes, MPAA checkboxes, runtime range slider
- `FilterState` and `DEFAULT_FILTER_STATE` exported — may need extending for saved/shortlist toggles, or new toggle buttons can live outside the sidebar

**`api.ts`** (`frontend/src/lib/api.ts`)
- All new endpoints need typed API functions added here
- `EligibleMovieDTO` — check if it needs `saved: boolean` and `shortlisted: boolean` fields added (for icon state hydration)

### Backend — reusable / extendable

**`GET /sessions/{id}/eligible_movies`** (`backend/app/routers/game.py`)
- Returns `PaginatedMoviesDTO` with `EligibleMovieDTO` items
- Needs `saved` and `shortlisted` boolean fields added to each item (join against `SessionSave` and `SessionShortlist` tables)
- Alternatively: frontend fetches save/shortlist lists separately and merges client-side (avoids modifying the main eligible movies query)

**`request_movie` handler** (`backend/app/routers/game.py`)
- Where movie is picked and added to chain
- Add: delete `SessionShortlist` rows for this session + delete `SessionSave` row for the picked tmdb_id

**`Session` model** (`backend/app/models/__init__.py`)
- `SessionSave` and `SessionShortlist` tables need to be added here with FK to `Session.id`

### Data models to create

```python
class SessionSave(Base):
    __tablename__ = "session_saves"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    tmdb_id: Mapped[int] = mapped_column()
    saved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("session_id", "tmdb_id"),)

class SessionShortlist(Base):
    __tablename__ = "session_shortlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    tmdb_id: Mapped[int] = mapped_column()
    __table_args__ = (UniqueConstraint("session_id", "tmdb_id"),)
```

Both cascade-delete when the parent Session is deleted.

### Icons (lucide-react — already installed)

- Save: `Star` (outline = unsaved, filled gold = saved)
- Shortlist: `ListCheck` or `CheckSquare` (outline = not shortlisted, filled = shortlisted)
- Clear shortlist: `X` or `Trash2`

</code_context>
