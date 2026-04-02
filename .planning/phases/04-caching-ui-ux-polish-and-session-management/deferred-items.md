# Deferred Items — Phase 04 Caching, UI/UX Polish & Session Management

## Future Enhancement: Local Poster Image Caching

- **Suggested during:** Phase 04 bug-fix session (2026-03-17)
- **Idea:** Download and cache TMDB movie poster images locally during the nightly TMDB sync, rather than serving `image.tmdb.org` URLs directly in the frontend.
- **Rationale:**
  - Posters are static — they never change once fetched
  - Eliminates runtime dependency on TMDB CDN for image availability
  - Posters load instantly from local storage instead of a remote CDN
  - Aligns with the existing pattern of pulling all movie metadata locally
- **Proposed approach:**
  - During nightly sync, download each movie's `poster_path` to a local directory (e.g., `/static/posters/{tmdb_id}.jpg`) if not already cached
  - Store the local path in the `movies` table (new `poster_local_path` column, nullable)
  - Frontend prefers the local URL (`/static/posters/{tmdb_id}.jpg`) and falls back to the TMDB CDN URL when local is absent
  - Cache invalidation: re-download only if `poster_path` on the TMDB record changes (unlikely but detectable via sync diff)
- **Not addressed in Phase 04 because:** Out of scope — requires a new DB column, sync loop change, and static file serving config. Good candidate for a future polish phase.

## Nightly Sync: Backfill Movie Stubs (title / year / poster_path)

- **Identified during:** Phase 04 bug-fix session (2026-03-17)
- **Problem:** `_ensure_movie_cast_in_db` inserts Movie stubs with `title=""` and `year=None` when a movie is first encountered via a cast fetch. The `_ensure_actor_credits_in_db` upsert now backfills these fields on-demand per actor, but the combined eligible-movies view (no actor filter) serves cached DB data and won't trigger the backfill.
- **Fix:** Add a pass to the nightly TMDB sync that finds Movie rows where `title=""` or `year IS NULL` or `poster_path IS NULL` and fetches full details from `GET /movie/{tmdb_id}` to populate them. The nightly sync is the right primary conduit for data accuracy — on-demand backfill is a fallback only.
- **Why nightly sync:** Guarantees all stubs are resolved overnight so users never see blank titles/posters in the combined view, regardless of which actors they've filtered by.
