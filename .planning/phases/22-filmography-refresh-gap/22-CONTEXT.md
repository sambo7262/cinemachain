# Phase 22 Context: Filmography Refresh Gap

**Phase goal:** Close the actor-filmography staleness gap so newly-released movies appear for cached actors. Today the `filmography_fetched` short-circuit means an actor's TMDB credits are frozen at first-fetch time forever; the nightly cache job is also a no-op against cached actors. Add a `filmography_fetched_at` timestamp + TTL, force-refresh top popular actors nightly, lazily re-fetch on-demand when stale, and expose a manual refresh button in Settings.

**Requirements:** STALE-01 (timestamp + nightly refresh), STALE-02 (on-demand TTL self-heal), STALE-03 (manual refresh button)

---

## Origin — real-world bug report (2026-05-29)

User played a chain that landed on **Hoppers** (Meryl Streep). Meryl appeared as eligible actor for the next step. Clicking her filmography showed her movies — but **The Devil Wears Prada 2** (released within the previous 4 weeks) was missing.

Investigation traced this to two compounding behaviours:

1. **`_ensure_actor_credits_in_db` short-circuits on cached actors** — `backend/app/routers/game.py:425`
   ```python
   if existing_actor is not None and existing_actor.filmography_fetched:
       # only re-runs if blank-title stubs exist; otherwise returns immediately
   ```
2. **Nightly cache job is a no-op against cached actors** — `backend/app/services/cache.py:404`
   The nightly loops over top popular actors calling `_ensure_actor_credits_in_db(...)` but the short-circuit above turns the whole pass into nothing for any actor already in the DB.

Net effect: an actor's TMDB filmography is frozen at first-cache-time forever. New TMDB releases for cached actors are invisible.

---

## Decision 1 — Schema change: add `filmography_fetched_at`

**Decision:** Add `filmography_fetched_at TIMESTAMP NULL` to the `actors` table via Alembic migration **0019**.

- Nullable column. **No backfill.** Existing rows get `NULL`.
- `NULL` semantically = "no timestamp yet under the new TTL regime" = treated as stale.
- Whenever code flips `filmography_fetched` to `True`, it must also set `filmography_fetched_at = NOW()` in the same transaction.

**Why no backfill to `NOW()`?** Backfilling to "fresh today" would mean nothing happens until the next nightly run — actors stay stale for up to 14+ days after deploy. Backfilling to "30 days ago" would create a thundering herd against TMDB on first interaction. Leaving `NULL` lets the on-demand path self-heal lazily as users actually interact with each actor, and the nightly job catches the rest within 24h.

**Why a separate column instead of reusing `fetched_at`?** `fetched_at` tracks when the actor row was *created* (set at insert). `filmography_fetched_at` tracks when their credits were last fully fetched. Different semantics, both useful.

---

## Decision 2 — TTL value: 14 days

**Decision:** TTL = **14 days**.

- 7 days: too aggressive, more TMDB load without much benefit (TMDB updates within a day of release)
- 14 days: fits a typical 2-week release cadence; catches releases within ~2 weeks of TMDB ingestion
- 30 days: too conservative for the user's expectation of seeing recent releases

**Where TTL lives:** module-level constant in `game.py` (e.g. `FILMOGRAPHY_TTL_DAYS = 14`) for now — not a settings field. If we later want it user-configurable, promote to settings then.

---

## Decision 3 — On-demand refresh: synchronous, not stale-while-revalidate

**Decision:** When `_ensure_actor_credits_in_db` finds a stale or NULL `filmography_fetched_at`, it re-fetches **synchronously** — the caller blocks on TMDB.

**Considered and rejected:** stale-while-revalidate (return cached data instantly, spawn a `BackgroundTask` to refresh, so user sees fresh data on *next* click).

**Why rejected:** the user's stated requirement is that the fix must "apply to all active games." With SWR, a player mid-chain who clicks Meryl would see the *same* stale list, then have to navigate away and back to see DWP2 appear. That's surprising and exactly the UX failure we're trying to fix.

**Latency tradeoff accepted:** one TMDB call (~200–500ms) per stale actor per 14 days. Bounded by chain length (~20 actors max) and frequency (once per 14 days per actor). Acceptable for a one-time interaction cost that produces correct data.

**Mitigations preserved:**
- Short-circuit unchanged for actors fetched within TTL → fresh actors stay instant
- Per-actor TMDB call uses existing rate-limit semaphore → no thundering herd
- TMDB failure handling unchanged (try/except returns gracefully with cached data)

---

## Decision 4 — Nightly cache job: `force_refresh=True`

**Decision:** Add a `force_refresh: bool = False` parameter to `_ensure_actor_credits_in_db`. When `True`, the short-circuit is bypassed regardless of TTL/flag state. The nightly cache job (`backend/app/services/cache.py:404`) passes `force_refresh=True`.

**Effect:** every top popular actor refreshed nightly, regardless of cache state. ~5,000 TMDB calls per night, well within budget. Self-heals all popular actors within 24h of any new release.

---

## Decision 5 — Manual refresh: Settings button

**Decision:** Add a "Refresh actor filmographies" button to the Settings page, in or near the existing cache controls. Triggers `POST /cache/actors/refresh-now` (new endpoint) which kicks off a one-shot force-refresh pass of all top popular actors using the same loop as nightly.

**Why:** belt-and-suspenders. Gives the user a "fix it now" lever if they ever suspect data is stale (e.g., after a long gap between play sessions, or while testing this very feature). Cheap to implement — re-uses the nightly job's loop body.

**UX:** Reuses the existing cache-refresh button pattern (`POST /cache/run-now`). Same visual feedback (running indicator, completion message). Concurrent-run guard via `_cache_state.running` flag prevents double-trigger.

---

## Decision 6 — Symmetric movies coverage

**Considered:** should we also TTL-refresh movie details (`_ensure_movie_details_in_db`)?

**Decision:** No separate movie fix needed. The actor-credits refresh **does** pull the full TMDB filmography list, which includes any new movies the actor has appeared in. New movies are upserted into the `movies` table as stubs via the same code path. So refreshing an actor's filmography automatically covers "new movies in their catalogue."

Movie-level metadata (genres, runtime, MPAA) is already enriched lazily on first access via `_ensure_movie_details_in_db` — so a freshly-discovered movie stub gets its metadata when the user first interacts with it. No additional refresh logic needed at the movie level.

---

## Decision 7 — Scope: actor filmographies only, not movie casts

**Decision:** This phase touches `_ensure_actor_credits_in_db` and the actor-filmography refresh path **only**. It does NOT touch `_ensure_movie_cast_in_db` (which fetches a movie's cast list).

**Why:** the reported bug is about an actor's filmography being stale, not a movie's cast being stale. A movie's cast doesn't really change after release. Keeping scope narrow reduces regression risk for a "this is working great" codebase.

---

## Regression risk register

| Risk | Mitigation |
|------|------------|
| Latency added to on-demand actor clicks for stale actors | Synchronous fetch is one TMDB call (~200–500ms), bounded once per 14 days per actor; existing rate-limit semaphore intact |
| TMDB rate limit blowup from nightly force-refresh | Top 5k actors at 0.05s sleep per call ≈ 4–5 min total; well within TMDB free-tier budget |
| Schema migration breaks existing data | Nullable column, no backfill, no destructive change; migration 0019 is purely additive |
| First post-deploy interaction triggers refresh storm | Bounded by user-driven interaction — only actors the user actually clicks get fetched; nightly catches the long tail |
| Background pre-fetch (game.py:659) becomes much slower if it triggers refreshes | Background path already uses `_bg_session_factory` + try/except; tolerant of long calls |

---

## Out of scope (deferred to future phases)

- Configurable TTL via settings UI (currently module constant)
- Per-actor manual refresh button in eligible-actors row UI
- Cast staleness (movie-level cast refresh)
- Watch-history filmography sync (separate concern)

---

## Implementation hints for planner

- Migration: `backend/alembic/versions/20260529_0019_filmography_fetched_at.py`
- Model: `backend/app/models/__init__.py:53` — add `filmography_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)`
- Core change: `backend/app/routers/game.py:410-505` — extend `_ensure_actor_credits_in_db` with `force_refresh` param + TTL check; set timestamp on line 504 alongside `filmography_fetched=True`
- Nightly: `backend/app/services/cache.py:404` — add `force_refresh=True`
- New endpoint: `POST /cache/actors/refresh-now` in `backend/app/routers/cache.py` (or wherever the existing `/cache/run-now` lives)
- Frontend: `frontend/src/pages/Settings.tsx` — add button + mutation + visual feedback near existing cache controls
- API client: `frontend/src/lib/api.ts` — add `refreshActorFilmographies()` function
