# Phase 19: v2 Bug Fixes & Polish — Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve bugs and deliver polish items accumulated during v2 development (Phases 13–18). The one explicit new feature is a rating dialog on mark-as-watched. Everything else is bug fixes, UI polish, and requirements-checklist housekeeping. No new capabilities beyond what is enumerated here.

</domain>

<decisions>
## Implementation Decisions

### A. Rating Dialog — Feature

**D-01: Trigger** — Dialog appears immediately after the user taps "Mark as Watched" (before backend confirms). Mark-watched PATCH fires first; dialog appears simultaneously. No intermediate state.

**D-02: Input style** — Horizontal slider, range 1–10. No labels at the extremes — just the numeric current value displayed above the slider.

**D-03: Dialog content** — Movie poster thumbnail + title at the top. Slider below. Save and Skip buttons at the bottom.

**D-04: Buttons** — Two explicit buttons: "Save" (submits rating via PATCH /movies/{id}/rating) and "Skip" (dismisses dialog, leaves prior rating untouched).

**D-05: Slider default** — Pre-fill with existing rating if one exists; default to 7 for unrated movies.

**D-06: Submission** — Two separate calls: (1) PATCH /movies/{tmdb_id}/watched fires immediately on button tap, (2) PATCH /movies/{tmdb_id}/rating fires only on Save. Skip fires no rating call.

**D-07: Re-watch behaviour** — Dialog always appears, even if movie was previously rated. Slider pre-fills with existing rating so user can update or skip.

**D-08: Skip behaviour** — Skip leaves prior rating untouched. If no prior rating exists, skip leaves it null.

**D-09: Shared component** — Extract a `RatingSlider` component (slider + Save/Skip buttons) reused in both:
- The new mark-as-watched rating dialog (GameSession + SearchPage)
- The WatchHistoryPage splash dialog (currently has its own rating input — unify to this component)

**D-10: Locations** — Dialog appears in both GameSession (Mark as Watched button) and SearchPage / Query Mode (Mark as Watched in movie splash).

---

### B. Mobile Bugs

**D-11: Nav horizontal scrolling** — Top nav overflows on mobile causing horizontal scroll. Reduce font size and/or padding of nav links at small breakpoints so all items fit without scrolling. Settings icon must always be visible without scrolling.

**D-12: Ratings badges bleeding off page** — When adding a movie to the chain (or in any card view), ratings badges and metadata overflow the card width on mobile. Fix: stack badges and metadata vertically below the poster on mobile breakpoints rather than laying out horizontally.

**D-13: Global padding reduction** — Reduce left/right page padding by approximately 20% across the app. Currently too much whitespace on the sides; content should use the available width better. Apply to all pages: GameSession, SearchPage, WatchHistoryPage, session grid (home).

**D-14: Session grid home page padding** — Session cards on the home/lobby page have too much padding causing text wraps in session titles/icons. Reduce padding inside session tiles.

**D-15: Watch History mobile portrait — missing images/icons/ratings** — On mobile portrait, Watch History shows no images, icons, or ratings. Fix: drop the genre field at this breakpoint and use the freed space to show poster + ratings. Widen content slightly if needed.

---

### C. Non-Mobile Bugs

**D-16: Search/filter persists across steps** — In GameSession eligible movies, search text and active filters are not cleared when the user advances to the next step (picks actor → picks movie). All filters including search text must be reset to default when the session advances to a new step.

**D-17: Filter/search scoped to current page only** — When filtering or searching eligible movies, results only include movies on the current page. Fix: search and filter must operate across ALL eligible movies (not just the loaded page). The existing cross-page save/shortlist pattern (fetching all results when filters are active) should be extended to cover search text and all other filters.

---

### D. Bug / Polish Items

**D-18: NR filter toggle** — Add a toggle to exclude 'NR'-tagged movies from eligible movies. Important constraint: movies with a NULL/missing MPAA rating must NOT be excluded — only movies where `mpaa_rating == "NR"` should be filtered. This is because many movies simply haven't been backfilled yet and filtering them would hide legitimate content.

**D-19: Star/shortlist buttons — position and responsiveness** — Move save (star) and shortlist buttons to the right side of the movie tile card (currently overlaid on the poster image, hard to tap). Improve response speed: button state should update immediately on tap (optimistic UI) with no perceived lag.

**D-20: Badge tooltips** — All rating badges (RT, IMDB, TMDB, MDB, Letterboxd, personal rating) must have tooltips that identify the source/meaning. Tooltips should appear on hover (desktop) and long-press (mobile if feasible via shadcn Tooltip component).

**D-21: All sorts default to DESC** — Every sort selector across the app (GameSession eligible movies, SearchPage, WatchHistoryPage) should default to descending order when a sort column is first selected. Currently some default to ASC.

**D-22: Session grid tile — remove "steps" text** — Remove the step count text from session tiles on the home/lobby page. It adds noise without value.

**D-23: Session grid tile — shrink Continue button, add current movie poster** — The Continue button on active session tiles is too large. Shrink it and add a small poster thumbnail of the current step's movie alongside it to give visual context.

---

### E. Session Settings Menu

**D-24: Menu item order** — Reorder the session settings dropdown to:
1. Export CSV
2. Edit Session Name
3. Delete Last Step
4. Archive Session

Current order has Delete Last Step before Edit Session Name — swap them.

**D-25: Delete Last Step — atomic two-step revert** — "Delete Last Step" must revert to the movie state before the actor was selected, in a single action. Current behavior deletes only the movie step, leaving the preceding actor step in place — which keeps the actor flagged as "used" even though the movie was undone.

**Fix:** When the last step is a movie step (actor_tmdb_id is null) AND the preceding step is an actor step (actor_tmdb_id is not null), delete BOTH steps atomically and revert `current_movie_tmdb_id` to the movie_tmdb_id of the actor step (which is the same movie the actor was picked from). Result: user is returned to the movie-watched state with the actor available for re-selection.

**Example:** Chain is `[Inception] → [Leo DiCaprio from Inception] → [Titanic] → [Kate Winslet from Titanic] → [Wonder Woman]`. User taps Delete Last Step while on Wonder Woman. Expected outcome: Wonder Woman step AND the "Kate Winslet from Titanic" step are both deleted. Session reverts to Titanic, with Kate Winslet available to pick again.

**Edge case:** If the last step is already an actor step (actor was picked but no movie yet chosen), delete only that actor step. No movie step to remove.

---

### F. Requirements Housekeeping

**D-26: Mark as done in REQUIREMENTS.md** — The following requirements are implemented in code but unchecked. Phase 19 updates the checkboxes:
- NAV-01, NAV-02, NAV-03 (3-item nav implemented in NavBar.tsx)
- QMODE-06 (Radarr request from SearchPage splash implemented)
- SESS-01, SESS-02, SESS-03, SESS-04 (save/shortlist implemented in Phase 11)
- MDBLIST-02 (IMDB ratings in RatingsBadge component)
- SUGGEST-02 (suggestions have same actions as regular movies — Phase 15)
- WATCHED-01, WATCHED-02, WATCHED-03 (WatchHistoryPage implemented — Phase 16)

**D-27: Mark MDBSYNC-01/02 as superseded** — Phase 14 MDBList watched-sync was intentionally removed in Phase 16. These requirements are superseded, not deferred. Add a note in REQUIREMENTS.md.

**D-28: Mark IMDB-01 partially done** — ChainHistory movie links point to IMDB (with TMDB fallback) — done. Actor IMDB links (`imdb_person_id`) were explicitly deferred in Phase 17 CONTEXT (backfill cost not worth it). Mark movie-link portion done; actor-link portion explicitly deferred with rationale.

### Claude's Discretion
- Exact slider component implementation (shadcn Slider or custom)
- Rating dialog animation/transition style
- Tooltip implementation details (shadcn Tooltip)
- Exact breakpoint values for mobile layout fixes
- How "optimistic UI" is implemented for star/shortlist buttons (local state vs. mutation state)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core files modified by this phase
- `frontend/src/components/NavBar.tsx` — current nav implementation
- `frontend/src/pages/GameSession.tsx` — mark-watched, filter/search, step advance, settings menu, delete last step
- `frontend/src/pages/SearchPage.tsx` — mark-watched (Query Mode), Radarr request
- `frontend/src/pages/WatchHistoryPage.tsx` — existing rating editor (to be replaced by shared component)
- `frontend/src/lib/api.ts` — API calls including markWatchedOnline, setMovieRating
- `frontend/src/components/RatingsBadge.tsx` — badge variants and tooltip targets
- `backend/app/routers/game.py` — delete_last_step endpoint, mark_current_watched endpoint, eligible movies filter
- `backend/app/routers/movies.py` — mark_movie_watched, set_movie_rating endpoints
- `backend/app/models/__init__.py` — WatchEvent.rating field
- `.planning/REQUIREMENTS.md` — requirements checklist to update

### Reference implementations
- `frontend/src/pages/WatchHistoryPage.tsx` — existing personal rating input pattern (splice into RatingSlider)
- `backend/app/routers/game.py:2206` — delete_last_step current implementation (to be fixed per D-25)
- `backend/app/routers/game.py:1340` — used_actor_tmdb_ids derivation (actor exclusion logic)

</canonical_refs>

<specifics>
## Specific Ideas

- **Delete Last Step example (D-25):** "If Gal Gadot was used to get to Wonder Woman, deleting the step should restore Gal Gadot as selectable in one action — not two."
- **NR filter (D-18):** "We want to filter out NR-tagged content (making-of docs, etc.) but must NOT filter movies with NULL MPAA — those are just not yet backfilled."
- **Padding (D-13):** "About 20% reduction on left/right — we leave a lot of unused space on either side."
- **Nav overflow (D-11):** "There is horizontal scrolling for Settings on mobile — elements are right up against each other."

</specifics>

<deferred>
## Deferred Ideas

- Actor IMDB links (`imdb_person_id` on Actor model) — deferred in Phase 17, remains deferred
- DB metadata gap tooling (audit/re-enrichment of missing overviews/ratings) — user waived for this phase
- "Query Mode" nav label rename (nav says "Search") — user waived for this phase

</deferred>

---

*Phase: 19-v2-bug-fixes-polish*
*Context gathered: 2026-04-02 via /gsd:discuss-phase*
