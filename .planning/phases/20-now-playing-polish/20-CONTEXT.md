# Phase 20 Context — Now Playing Polish & Layout Alignment

## Phase Goal
Enrich the Now Playing screen with full movie metadata; fix mobile portrait over-padding app-wide; repair PosterWall visibility on desktop.

---

## Decision 1: Now Playing Metadata — Data Source

**Decision:** Backend must embed the current movie's full detail directly in the `GameSessionDTO` response as a `current_movie_detail` field (or equivalent).

**Why:** `allEligibleMovies` is only fetched when `isWatched === true` (enabled gate in the query). Pre-watch, `allEligibleMovies` is empty so `currentMovie` lookup returns null — all metadata is hidden. This is a bug. The fix is not to relax the fetch gate but to source current movie data from the session response itself.

**What to embed:** `year`, `runtime`, `mpaa_rating`, `overview`, `imdb_rating`, `rt_score`, `rt_audience_score`, `metacritic_score`, `vote_average` — all fields already stored in the movies table.

**No new DB data needed.** Everything is already in the DB; it just needs to be included in the session response.

---

## Decision 2: Now Playing Metadata — Display

**Decision:** Below the poster + title, always show (both pre-watch and post-watch states):
- Metadata row: MPAA badge, year, runtime (e.g. "1h 52m")
- Ratings row: `RatingsBadge` showing all available ratings (IMDB, RT Tomatometer, RT Audience, Metacritic) — use "card" variant or a suitable variant that includes these four
- Overview text: clamped to ~3 lines with a "Read more" inline expand; collapses cleanly if null (no placeholder text)

**Consistency:** Same metadata visible regardless of watched state — user may want to read the overview before or after watching.

---

## Decision 3: Content Padding — App-Wide Mobile Fix

**Problem:** App.tsx uses `px-6` (24px) unconditionally. Nav uses `px-4 sm:px-6` (16px mobile, 24px sm+). Pages (GameSession, SearchPage) add their own `px-4 sm:px-6` on top of the App.tsx wrapper. On mobile portrait (~375px), effective side padding is ~40px per side — ~21% of screen width wasted.

**Decision:** Change App.tsx content wrapper from `px-6` to `px-4 sm:px-6` to match nav exactly.

**Scope:** All pages. Remove redundant per-page horizontal padding from:
- GameSession main content area (`px-4 sm:px-6`)
- SearchPage content area (`px-4 py-4 sm:px-6 sm:py-6` → remove the horizontal px, keep vertical py)
- Any other page with its own horizontal padding nested inside App.tsx wrapper

**Exception:** GameSession sub-header (`border-b px-4 sm:px-6 py-3`) — leave untouched. User confirmed it fits well as a secondary header with its own inset.

**Larger screens:** No changes needed; over-padding is not perceptible at wider viewports.

---

## Decision 4: PosterWall Desktop Visibility (Bug Fix)

**Problem:** PosterWall is not visible on desktop despite `hidden sm:block` being correct (hidden on mobile portrait, visible sm+). Likely cause: `bg-background` on App.tsx outer div or GameSession outer div is blocking the `fixed inset-0 z-[1]` poster wall from showing through the transparent content area. Needs targeted investigation.

**Decision:**
- Mobile portrait (< 640px): keep hidden — `hidden sm:block` is correct, no change
- Desktop/tablet (≥ 640px): fix the z-stacking or background-block issue so the PosterWall renders visibly behind the content

**Approach for planner:** Investigate whether removing `bg-background` from GameSession's outer div (since the header already provides it and the PosterWall + dark overlay replaces the page background) resolves the issue. If App.tsx outer div's `bg-background` is the cause (visible on sides outside 1400px constraint), that can stay — it only matters that the GameSession content area is transparent where the poster wall should show through.

---

## Code Context

| Location | Relevance |
|---|---|
| `frontend/src/App.tsx:41` | `max-w-[1400px] mx-auto px-6 w-full flex-1` — change `px-6` to `px-4 sm:px-6` |
| `frontend/src/components/NavBar.tsx:14` | `px-4 sm:px-6` — target alignment for content padding |
| `frontend/src/pages/GameSession.tsx:533` | `min-h-screen flex flex-col bg-background` — bg-background here may block PosterWall |
| `frontend/src/pages/GameSession.tsx:538` | Sub-header `px-4 sm:px-6` — do NOT change |
| `frontend/src/pages/GameSession.tsx:599` | `px-4 sm:px-6 py-4 w-full` — remove px-4/px-6, keep py-4 |
| `frontend/src/pages/GameSession.tsx:607–694` | Now Playing hub — add metadata from `current_movie_detail` |
| `frontend/src/pages/GameSession.tsx:626` | `allEligibleMovies.find(...)` — replace with `session.current_movie_detail` |
| `frontend/src/pages/SearchPage.tsx:245` | `px-4 py-4 sm:px-6 sm:py-6` — strip horizontal px only |
| `frontend/src/components/PosterWall.tsx:42` | `fixed inset-0 z-[1] overflow-hidden hidden sm:block` — correct as-is |
| `frontend/src/components/RatingsBadge.tsx:31` | VARIANT_KEYS — "card" shows imdb, rt, rt_audience, metacritic, vote_average |
| `backend/app/routers/game.py` | Session response — add current_movie_detail embedding |
