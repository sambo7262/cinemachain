# Phase 13 Context — MDBList Expansion

**Phase goal:** Research the full MDBList basic tier API surface and implement IMDB ratings + any other high-value data throughout the app.
**Requirements:** MDBLIST-01, MDBLIST-02, MDBLIST-03

---

## Decision 1: Ratings Badge Strip (MDBLIST-02 + visual design)

### What to build
Replace the single `🍅 RT%` inline text with a flex-wrap badge strip showing all available rating sources. Each badge = SVG icon + score in natural format.

### Rating sources (all from MDBList response `ratings` array)
| Source | Display | Natural format | Example |
|--------|---------|----------------|---------|
| IMDB | SVG logo | decimal (1–10) | 7.8 |
| RT Tomatometer | Tomato SVG | percentage | 94% |
| RT Audience | Popcorn bucket SVG | percentage | 87% |
| Metacritic | MC logo SVG | percentage | 81% |
| MDB Average | MDB logo SVG | decimal (1–10) | 7.4 |
| TMDB | TMDB logo SVG | decimal (1–10) | 7.6 |
| Letterboxd | LB logo SVG | decimal (0–5) | 3.9 |

### Icon strategy
- SVG logos for all sources first
- Fall back to styled text abbreviation (e.g., `MC`, `LB`, `MDB`) for any that look visually off after implementation
- Research: look for free/open SVG assets for each platform; Heroicons/Lucide won't have these, check Simple Icons (simpleicons.org) — has IMDB, RT, Metacritic, Letterboxd, TMDB

### Where badges appear
**Eligible movie cards (game mode):** 4 badges only — IMDB, RT Tomatometer, RT Audience, Metacritic
**Splash dialog (all contexts):** All 7 badges
**Now Playing tile:** Replace current `🍅 RT%` — show IMDB + Tomatometer at minimum (space-constrained)
**SearchPage results + splash:** Same rules as GameSession equivalents

### Missing score handling
Hidden entirely — do not render badge if value is null/unavailable. Most popular sources (IMDB, RT) will be present for nearly all movies.

### Score format rules
- Scores shown in their **native scale** — no normalization to percentage
- IMDB: `7.8` (one decimal)
- RT scores: `94%` (integer %)
- Metacritic: `81%` (integer %)
- MDB average: `7.4` (one decimal)
- TMDB: `7.6` (one decimal)
- Letterboxd: `3.9` (one decimal, 0–5 scale)

---

## Decision 2: Additional High-Value Data (MDBLIST-03)

### Store imdb_id on movies
- MDBList API response includes `imdbid` field (e.g., `"tt0111161"`) — capture and store in a new `imdb_id` column on the `Movie` model
- This is the IMDB tt-identifier, not a numeric rating

### Replace TMDB external links with IMDB
Current `themoviedb.org/movie/{tmdb_id}` external links exist at 4 locations:
1. `GameSession.tsx:1079` — eligible movie card link
2. `GameSession.tsx:1224` — splash dialog link
3. `SearchPage.tsx:555` — search page splash link
4. `ChainHistory.tsx:89` — chain history movie link

All 4 replace with `https://www.imdb.com/title/{imdb_id}` when `imdb_id` is available. Fall back to TMDB link if `imdb_id` is null (graceful degradation).

### Actor external links — unchanged
`ChainHistory.tsx:129` actor links stay on TMDB (`/person/{tmdb_id}`). Storing `imdb_person_id` deferred — not worth the scope for a link swap.

---

## Decision 3: Backfill & Quota Management

### DB migration approach
- Add new columns to `Movie` (all nullable): `imdb_id`, `imdb_rating`, `metacritic_score`, `letterboxd_score`, `mdb_avg_score`
- One-time migration step: reset `rt_score = NULL` for all existing rows so backfill re-fetches everyone and populates all new fields in one pass
- `rt_audience_score` already exists — backfill will repopulate it too

### New settings table columns for quota tracking
- `mdblist_calls_today: int` — incremented on every API call
- `mdblist_calls_reset_date: date` — date of last reset; when today > reset_date, counter resets to 0

### On-demand backfill trigger in Settings
1. Button: "Refresh Ratings Data"
2. On click: show confirm dialog with:
   - Estimated API calls = count of movies with any NULL new field
   - Current quota status: `X of 10,000 calls used today`
   - Warning if estimated calls > remaining quota
3. User confirms → POST `/mdblist/backfill/start`
4. Button disables, progress bar appears
5. Frontend polls `GET /mdblist/backfill/status` every 2s
6. Status response: `{ running: bool, fetched: int, total: int, calls_used_today: int, daily_limit: int }`
7. Progress bar + counter update until `running: false`
8. On complete: show "Done — X movies updated" + updated quota display

### Polling interval
2 seconds. Single-user NAS app — polling lag imperceptible.

### Nightly backfill (existing `backfill_rt_scores`)
- Rename/extend to `backfill_mdblist_scores` — fetches all missing fields in one API call per movie
- Trigger condition: any of the new fields is NULL (not just `rt_score`)
- Increments `mdblist_calls_today` counter
- Stops on 429 as before

---

## Deferred Ideas (captured, not in scope for Phase 13)

These came up during discussion — capture for future phases:

- **MDBList recommendations → Suggested Movies tab** — cross-reference MDBList "recommended" data with eligible actors in game mode; surface as a tab when alignments exist. Significant feature, own phase.
- **Watched list sync to MDBList** — POST watched movies from all sessions/modes to a MDBList list; enables MDBList personalized recommendations. New integration direction, own phase.
- **MDBList vs TMDB fallback / redundancy** — evaluate using MDBList as a fallback for TMDB enrichment or vice versa. Architectural change, own phase.
- **IMDB actor links** — store `imdb_person_id` (from TMDB `/person/{id}/external_ids`) and swap actor links in ChainHistory. Small phase.
- **Tier upgrade evaluation** — researcher should document MDBList paid tier limits (10k/day currently configured) and note whether the ratings expansion + future features warrant a tier upgrade.

---

## Code Context

### Existing MDBList service
- `backend/app/services/mdblist.py` — `fetch_rt_scores()`, `backfill_rt_scores()`, `_fetch_and_store_rt()`
- API: `GET https://mdblist.com/api/?apikey={key}&tm={tmdb_id}`
- Response has `ratings` array: each item has `source` (string) and `value` (int)
- Response top-level has `imdbid` field

### Current Movie model columns
`rt_score: int | null`, `rt_audience_score: int | null` — both use `0` as "fetched, no data" sentinel (distinguishes from `null` = "never fetched")

### Frontend RT display locations
- `GameSession.tsx:624` — Now Playing tile
- `GameSession.tsx:1104` — eligible movie card
- `GameSession.tsx:1199` — splash dialog
- `SearchPage.tsx` — search results + splash

### Settings page
- `frontend/src/pages/Settings.tsx` — add backfill button + quota display here
- `backend/app/routers/settings.py` — existing settings router; add backfill endpoints here or in new `mdblist.py` router
