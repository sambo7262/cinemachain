# Phase 17 Context — Backend Scheduler, Settings Audit & IMDB Movie Links

**Phase goal:** Harden the nightly backfill so the DB catches up and stays current; audit and expand the Settings page into a proper system management tool; swap ChainHistory movie links from TMDB to IMDB.
**Requirements:** SCHED-01, SCHED-02, SCHED-03, IMDB-01

---

## Background: DB State at Phase 17 Start

Queried against live NAS DB (57,836 movies / 48,595 actors):

| Metric | Count | % |
|---|---|---|
| TMDB fully cached (fetched + genres) | 6,678 | 12% |
| MDBList ever fetched | 3,008 | 5% |
| Missing overview | 51,168 | 88% |
| Missing MPAA rating | 56,818 | 98% |
| Missing IMDB ID | 46,930 | 81% |
| Missing IMDB rating | 47,463 | 82% |
| Missing RT score | 52,563 | 91% |
| Actors with filmography fetched | 1,644 | 3% |

**Root cause of gaps:** Movies enter the DB as lightweight stubs when actor filmographies are fetched during gameplay (`_ensure_actor_credits_in_db`). Stubs contain title/year/poster/vote data but no genres, overview, MPAA, or MDBList fields. Enrichment only happens via (a) the nightly job for top-N movies, (b) on-demand when a movie appears in an active game. The stub/MPAA/overview backfill passes were capped at 2,000/run — far too low to clear a 57k backlog. MDBList backfill was manual-only and had barely been run.

**DB size:** 57 MB total (movies: 17 MB, credits: 23 MB, actors: 8.7 MB). Will grow as overviews and MDBList data fill in, but manageable.

---

## Decision 1: IMDB Movie Links in ChainHistory (IMDB-01)

### Scope change from requirement
The original requirement included `imdb_person_id` on actors. **Actor IMDB links are dropped** — the complexity of fetching and backfilling 48k actors is not worth it for the link improvement.

**Scope is movies only.**

### What's needed
`ChainHistory.tsx` already has IMDB-first link logic:
```tsx
href={step.movie_imdb_id
  ? `https://www.imdb.com/title/${step.movie_imdb_id}`
  : `https://www.themoviedb.org/movie/${step.movie_tmdb_id}`}
```
The frontend is fully wired. The gap is that `StepResponse` (backend Pydantic model) does not include `movie_imdb_id` — so the frontend always falls back to TMDB.

### Fix
Add `movie_imdb_id: str | None = None` to `StepResponse` in `game.py` and populate it from `Movie.imdb_id` when building the steps query. No migration needed — `Movie.imdb_id` already exists (populated by MDBList).

### Coverage dependency
81% of movies have no `imdb_id` today. Links will fall back to TMDB for those until MDBList backfill runs broadly (Decision 2). The TMDB fallback is intentional and permanent for any movie MDBList cannot find.

---

## Decision 2: Nightly Scheduler Redesign (SCHED-01)

### Two separate APScheduler jobs — not one monolithic job
MDBList and TMDB are separate services with separate rate limits, separate scheduling needs, and separate status tracking. They run as independent `AsyncIOScheduler` entries.

Both jobs use **`timezone="America/Los_Angeles"`** (see Decision 4 for timezone rationale).

---

### Job A: TMDB Nightly Cache (existing, hardened)

**Changes to `nightly_cache_job`:**

1. **Raise all backfill pass limits** from 2,000 → 25,000. TMDB has no documented daily limit — only a ~40 req/s soft cap. Current sleep of 0.05s = 20 req/s is well under that. The 2,000 limits were arbitrary conservatism; 25,000 clears the backlog in 2–3 nights.

2. **Add 429 backoff handling.** Currently absent. Add exponential retry (start at 5s, cap at 60s) on any 429 response. Log the backoff clearly.

3. **Priority ordering for all passes:** `ORDER BY <missing_field> NULLS FIRST, vote_count DESC NULLS LAST`. Most popular movies get enriched first within each missing-data group.

4. **On-demand trigger endpoint:** `POST /cache/run-now` — fires `nightly_cache_job` immediately as a background task. Returns `{"started": true}` or `{"running": true}` if already in progress. Mirrors the MDBList backfill pattern. Paired with `GET /cache/status` returning `{running, last_run_at, last_run_duration_s}`.

**Passes that remain (with raised limits):**
- TMDB discover: top-N movies enriched (configurable via `tmdb_cache_top_n`)
- Actor pre-fetch: top-K actors (configurable via `tmdb_cache_top_actors`)
- Stub backfill: 25,000 movies with `genres IS NULL`, ordered by priority
- MPAA backfill: 25,000 movies with `mpaa_rating IS NULL OR mpaa_rating = ''`, ordered by priority
- Overview backfill: covered by stub pass (`_ensure_movie_details_in_db` fills genres + overview together) — **remove as separate pass**
- Poster download: unchanged
- RT score backfill: unchanged (calls `backfill_rt_scores` from mdblist service — keep as-is since MDBList job will cover this going forward)

---

### Job B: MDBList Nightly Backfill (new scheduled job)

**What it fills:** `imdb_id`, `imdb_rating`, `rt_score`, `rt_audience_score`, `metacritic_score`, `letterboxd_score`, `mdb_avg_score` — all in one API call per movie.

**Rate limit:** 25,000 calls/day free tier, 1 req/s to stay within limits. At 1 req/s, 25,000 calls = ~7 hours. 2–3 nightly runs cover the entire 57k backlog.

**Priority ordering:** `mdblist_fetched_at IS NULL` first (never fetched), then `mdblist_fetched_at < NOW() - INTERVAL '90 days'` (stale), ordered by `vote_count DESC NULLS LAST` within each group. Most popular movies get refreshed first.

**Re-fetch threshold:** 90 days. After the backlog is cleared, each nightly run only touches movies that have never been fetched or were last fetched more than 90 days ago. Keeps ratings current without re-fetching the whole DB every night.

**Self-limiting:** Respects daily quota tracked in `app_settings` (`mdblist_calls_today` / `mdblist_calls_reset_date`). If a manual backfill has already consumed today's quota, the scheduled run is a no-op. Same quota tracking logic already in `mdblist.py` — reuse it.

**Job time:** Configurable via `mdblist_schedule_time` setting (stored in `app_settings`, exposed in Settings UI). Default: `04:00` LA time (1 hour after the TMDB job at `03:00`).

---

## Decision 3: DB Connection Pool (SCHED-02)

Replace current `db.py` engine config with:

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=60,
    connect_args={"command_timeout": 60},
    echo=False,
)
```

**Rationale:**
- `pool_size=10, max_overflow=5` (was 5/2): Two long overnight jobs + web requests need headroom. 15 max connections is comfortable without straining a 256 MB Postgres container.
- `pool_pre_ping=True`: Catches stale connections after NAS disk sleep/idle before they error mid-request.
- `pool_recycle=1800`: Replaces connections idle > 30 min — important for a NAS that may sit idle for hours between game sessions.
- `pool_timeout=60`: Single-user app can afford to wait 60s for a connection during a heavy backfill run (up from 30s default).
- `connect_args={"command_timeout": 60}`: Per-statement timeout via asyncpg. Prevents runaway queries from holding connections indefinitely.

---

## Decision 4: Settings Audit & Settings Page Overhaul (SCHED-03)

### Timezone fix
- Add `TZ=America/Los_Angeles` to the `backend` service environment in `compose.yaml`
- Change both CronTrigger instances to `timezone="America/Los_Angeles"`
- All job time inputs in the Settings UI are labeled as "Los Angeles time"
- `.env.example` comments updated to remove "UTC" references

### Schema cleanup
- **Remove `tmdb_base_url`** from `SettingsResponse`, `SettingsUpdateRequest`, `_ENV_KEYS_TO_MIGRATE`, and the migration default. Hardcode `https://api.themoviedb.org/3` directly in `TMDBClient.BASE_URL` (already there). No user-facing use case for changing it.
- **`mdblist_calls_today` / `mdblist_calls_reset_date`** stay in `app_settings` as internal operational keys. Not exposed in `SettingsResponse` — they're read/written by the backfill logic, not the user.
- **`tmdb_cache_run_on_startup`** stays `.env`-only (deploy-time flag). Replaced in the UI by the on-demand run button.

### New settings keys (added to SettingsResponse + SettingsUpdateRequest)
| Key | Type | Default | Purpose |
|---|---|---|---|
| `mdblist_schedule_time` | string (HH:MM) | `04:00` | MDBList job fire time (LA time) |
| `mdblist_refetch_days` | int | `90` | Days before a fetched movie is considered stale |

### Settings UI principles
- **Editable:** All values requiring user input (API keys, URLs, job times, limits, thresholds)
- **API key fields:** Password-style inputs — masked by default, pasteable/writable but not readable in UI. Applies to: `tmdb_api_key`, `radarr_api_key`, `mdblist_api_key`
- **Base URLs not user-controlled:** Hidden entirely (e.g. `tmdb_base_url` removed)
- **Visible operational stats:** Calls used today, daily limit, next quota reset time — shown as read-only status alongside each service's settings section

### Settings page sections (restructured)

**TMDB**
- API key (masked)
- Cache time (LA time)
- Top N movies / Top K actors (numeric inputs)
- On-demand run button + last run status (mirrors MDBList backfill UI)

**MDBList**
- API key (masked)
- Schedule time (LA time)
- Stale refetch threshold (days)
- Calls used today / daily limit / next reset (read-only)
- On-demand run button + status (existing, unchanged)

**Radarr**
- URL, API key (masked), quality profile

**DB Health** *(new section — on-demand query)*
Two sub-panels, both refreshed by a single "Refresh Stats" button:

*Row-level health:*
| Metric | Count | % |
|---|---|---|
| Total movies | — | — |
| Missing overview | — | — |
| Missing MPAA | — | — |
| Missing IMDB ID | — | — |
| Missing IMDB rating | — | — |
| Missing RT score | — | — |
| Never MDBList fetched | — | — |
| Total actors | — | — |

*Table sizes:*
| Table | Size |
|---|---|
| Total DB | — |
| movies | — |
| credits | — |
| actors | — |
| watch_events | — |

New endpoint: `GET /settings/db-health` — runs both stat queries and returns JSON. Not cached — always live query.

---

## Deferred Ideas

- **User timezone configurability:** `TZ=America/Los_Angeles` is hardcoded in `compose.yaml`. Users in other timezones can change it manually. A UI timezone picker is not in scope.
- **IMDB actor links:** Actor `imdb_person_id` backfill dropped entirely. Not worth complexity for 48k actors.
- **RT score backfill removal from TMDB job:** Currently `nightly_cache_job` calls `backfill_rt_scores` (which uses MDBList internally). Once the MDBList scheduled job is running, this pass becomes redundant. Leaving it in for now — research/planner to flag if it causes double-counting.

---

## Code Context

### Files changed
| File | Change |
|---|---|
| `backend/app/db.py` | Pool settings (pool_size, max_overflow, pre_ping, recycle, timeout, command_timeout) |
| `backend/app/main.py` | Add MDBList scheduler job; LA timezone on both CronTriggers; `POST /cache/run-now` wiring |
| `backend/app/routers/game.py` | Add `movie_imdb_id: str | None = None` to `StepResponse`; populate from Movie join |
| `backend/app/routers/settings.py` | Add new keys; remove `tmdb_base_url`; add `GET /settings/db-health` endpoint |
| `backend/app/routers/mdblist.py` | Add scheduled backfill variant with priority ordering + re-fetch threshold |
| `backend/app/services/cache.py` | Raise limits to 25k; add 429 backoff; priority ordering on all passes; remove overview pass |
| `backend/app/services/settings_service.py` | Remove `tmdb_base_url` from `_ENV_KEYS_TO_MIGRATE` |
| `backend/app/services/tmdb.py` | No change (BASE_URL already hardcoded) |
| `compose.yaml` | Add `TZ=America/Los_Angeles` to backend service |
| `backend/.env.example` | Add `tmdb_cache_top_actors`; remove UTC references from comments |
| `frontend/src/pages/Settings.tsx` | Major restructure per section layout above |

### New endpoints
| Endpoint | Purpose |
|---|---|
| `POST /cache/run-now` | Trigger TMDB nightly job immediately |
| `GET /cache/status` | `{running, last_run_at, last_run_duration_s}` |
| `GET /settings/db-health` | Live DB row stats + table sizes |

### No new migrations needed
All schema changes are settings/logic only. `movie_imdb_id` in `StepResponse` reads from the existing `Movie.imdb_id` column.
