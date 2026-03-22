# Phase 6: New Features - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Feature additions and UI improvements to CinemaChain before production deployment. Nine discrete items: TMDB actor name resolution fix, movie selection splash window, session settings menu consolidation, chain history search, TMDB external links, in-app settings/config page, Rotten Tomatoes research, home page session card stats update, and Now Playing tile stats expansion.

</domain>

<decisions>
## Implementation Decisions

### Item 1 — TMDB Actor Name in Chain (CSV Import Override)
- **D-01:** Affects only the CSV import path where a raw TMDB ID is entered as an actor override — all other paths already resolve actor names correctly
- **D-02:** If the actor name is not stored locally, query TMDB to resolve it before displaying in the chain history
- **D-03:** Display the resolved actor name everywhere the chain step is shown (chain history table, session steps)

### Item 2 — Movie Selection Splash Window
- **D-04:** Fully replaces the current simple confirmation dialog — no fallback to the old dialog
- **D-05:** Splash displays: movie poster, title, TMDB rating, MPAA rating, runtime, and full TMDB `overview` field (no truncation)
- **D-06:** Splash includes a Radarr checkbox, selected by default
- **D-07:** If Radarr checkbox is checked → session advances AND Radarr download request is sent (existing behavior)
- **D-08:** If Radarr checkbox is unchecked → session still advances but NO Radarr request is made (user plans to watch elsewhere)
- **D-09:** Splash is triggered when the user selects an unwatched movie from the Eligible Movies panel

### Item 3 — Session Settings Menu Consolidation
- **D-10:** The existing session dropdown menu (currently holds "Export CSV" and "Delete Last Step") gains two new items: "Archive Session" and "Edit Session Name"
- **D-11:** "Archive Session" moves from the home page session card to this menu only — remove the archive button/action from the home page entirely
- **D-12:** "Archive Session" requires a confirmation dialog before executing
- **D-13:** "Edit Session Name" opens a modal with a text field pre-populated with the current session name

### Item 4 — Chain History Search
- **D-14:** A search input is added above the chain history table
- **D-15:** Filters in real-time as the user types — non-matching rows are hidden
- **D-16:** Searches both movie names AND actor names simultaneously in the chain

### Item 5 — TMDB External Links
- **D-17:** Every movie and actor that has a TMDB ID gets a link to their TMDB page
- **D-18:** Links open in a new browser tab
- **D-19:** Link surfaces: Eligible Movies table, Chain History table, new Movie Selection Splash (Item 2)
- **D-20:** NOT added to the Eligible Actors grid (not in scope)

### Item 6 — In-App Settings / Config Page
- **D-21:** A new Settings page is added to the app (accessible via NavBar or settings icon)
- **D-22:** On first launch (or if TMDB credentials are absent), a full blocking onboarding screen is shown — the app does not function without TMDB credentials, so no dismissal
- **D-23:** TMDB API key and base URL are the only required values; all other settings are optional
- **D-24:** On first launch, if a `.env` file exists, its values are read and used to pre-populate the settings page automatically (one-time migration)
- **D-25:** Settings are stored in the PostgreSQL DB — encrypted at rest if encryption is straightforward to implement (e.g., Fernet/AES via `cryptography` library); if implementation cost is high, store as plaintext in DB as a minimum
- **D-26:** Settings include: TMDB API key, Radarr URL + API key + default quality profile, Sonarr URL + API key, Plex token + URL, scheduled job timing (when to run nightly sync), nightly sync movie/actor pull limits
- **D-27:** `.env` remains supported as a fallback for deployments that prefer it, but DB-stored settings take precedence when present

### Item 7 — Rotten Tomatoes Ratings (Research-First)
- **D-28:** Researcher agent investigates third-party aggregator options for RT scores (e.g., OMDb API, MDBList, Streaming Availability API, or similar)
- **D-29:** Researcher presents options with pros/cons (reliability, cost, rate limits, data freshness) before any implementation decision is made
- **D-30:** Implementation is NOT committed — user decides after reviewing research findings; if no clean solution exists, this item is dropped from Phase 6

### Item 8 — Home Page Session Card Stats
- **D-31:** Session cards on the home page currently show deprecated "steps" stat — replace with the same stats shown on the session home page: watched count, total runtime, and started date
- **D-32:** Stats display inline on the session card (not a separate row or modal)

### Item 9 — Now Playing Tile Additional Stats
- **D-33:** The "Now Playing" tile on the session home page currently shows limited info — add runtime, MPAA rating, and TMDB rating to the tile
- **D-34:** These fields are already available on the Movie model and in session response data — frontend display change only

### Claude's Discretion
- Exact visual design of the Movie Selection Splash (layout, spacing, poster size)
- Encryption library choice for Item 6 (Fernet is idiomatic for Python/FastAPI)
- Whether settings page lives at `/settings` route or as a modal/drawer
- TMDB link icon style (external link icon next to title vs clickable title text)

</decisions>

<specifics>
## Specific Ideas

- Item 2 splash: "more polish" than the current dialog — should feel like a proper preview card, not a confirmation prompt
- Item 6 onboarding: blocking full-screen, not a dismissible banner — TMDB is non-negotiable for app function
- Item 6 migration: reading `.env` on first launch was user's reaction ("great idea") — this should be transparent and automatic, not a manual import step
- Item 7: user wants to understand options before committing — researcher should present a comparison table of aggregator options

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above.

### Existing session settings menu
- `frontend/src/pages/GameSession.tsx` — current dropdown menu with Export CSV + Delete Last Step; extend this for Items 3, 5
- `frontend/src/pages/GameLobby.tsx` — home page session cards; remove archive button (Item 3), update stats display (Item 8)
- `frontend/src/components/ChainHistory.tsx` — chain history table; add search (Item 4), TMDB links (Item 5)

### Backend
- `backend/app/routers/game.py` — eligible-movies, request-movie endpoints; splash data (Item 2), Radarr conditional (Item 2)
- `backend/app/services/tmdb.py` (or equivalent) — TMDB client; actor name resolution (Item 1), overview field (Item 2)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MovieFilterSidebar.tsx`: existing filter/sidebar pattern — may inform Movie Splash layout
- `shadcn Dialog`: already installed and used for Delete Last Step confirmation — reuse for Item 2 splash, Item 3 archive confirmation, Item 3 name edit modal
- `shadcn DropdownMenu`: already used for the session settings menu — extend in place for Items 3
- `NotificationContext / RadarrNotificationBanner`: existing Radarr notification plumbing — Item 2 Radarr checkbox hooks into the same request flow

### Established Patterns
- TMDB links follow `/person/{id}` and `/movie/{id}` URL structure on themoviedb.org
- Actor name resolution already works in normal gameplay via `_resolve_actor_tmdb_id` — Item 1 fix applies this to the CSV import path
- Session stats (watched count, runtime) are already computed in `GameSessionResponse` — Item 8 is a frontend display change only

### Integration Points
- Item 6 settings page will need a new DB table (`app_settings` or `config`) and a new backend router (`/settings`)
- Item 6 `.env` migration: `pydantic-settings` already reads `.env` in `settings.py` — the migration can read from the existing settings object on startup and write to DB if DB config is absent

</code_context>

<deferred>
## Deferred Ideas

- Query Mode (QUERY-01 through QUERY-07) — original v1 requirements, explicitly cleared from Phase 6 scope by user; defer to a future milestone if desired
- Eligible Actors grid TMDB links — user scoped Item 5 to eligible movies, chain history, and movie splash only
- Sonarr integration beyond what already exists — no new Sonarr work in Phase 6
- RT implementation — only committed to research; actual implementation deferred pending findings

</deferred>

---

*Phase: 06-new-features*
*Context gathered: 2026-03-22*
