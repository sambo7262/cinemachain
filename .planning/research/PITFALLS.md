# Pitfalls Research

**Domain:** Home media companion app (Plex/arr-stack integration)
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH (based on community reports, GitHub issues, and official documentation)

---

## Critical Pitfalls

### Pitfall 1: Plex Webhooks Use multipart/form-data, Not application/json

**What goes wrong:**
Your webhook endpoint receives POST requests from Plex and the body appears empty or unparseable. Standard JSON body parsers (Express `express.json()`, Flask's `request.json`, FastAPI's JSON body) silently fail to extract the payload, resulting in null/empty event data. The app either crashes or ignores all webhook events.

**Why it happens:**
Plex sends webhooks as `multipart/form-data` with the JSON payload embedded in a field named `payload`, plus an optional second part containing a JPEG thumbnail. Most web frameworks default to parsing `application/json` or `application/x-www-form-urlencoded`, not multipart. This is a non-obvious, undocumented-first-encounter gotcha that has spawned a dedicated proxy project (`plex-webhook-proxy`) just to work around it.

**How to avoid:**
- Use a multipart form parser (e.g., `multer` for Node.js, `python-multipart` for FastAPI/Starlette, `werkzeug`'s multipart support for Flask).
- Extract the `payload` field from the multipart body and parse it as JSON.
- Log the raw `Content-Type` header of the first few incoming webhook requests during development to confirm the format.
- Explicitly ignore the `thumb` part to avoid storing unnecessary binary data.

**Warning signs:**
- Webhook endpoint returns 200 but nothing happens downstream.
- Parsed body is `None`, `{}`, or `undefined`.
- No log output from event handlers despite confirmed Plex playback.

**Phase to address:** Phase 1 (initial Plex webhook integration)

---

### Pitfall 2: TMDB Rate Limiting Hits Unexpectedly on Bulk Operations

**What goes wrong:**
During the Movie Game's actor-chain traversal, the app fires multiple TMDB `/person/{id}/movie_credits` and `/movie/{id}/credits` requests in rapid succession. At 50 requests/second (per IP), a 5-step chain that fans out across cast members can exhaust the limit in under a second. Responses start returning HTTP 429, the game session breaks mid-chain, and users see errors or silent empty results.

**Why it happens:**
TMDB enforces a hard limit of 50 requests/second per IP address. The limit is per-IP regardless of how many app instances are running. Sequential traversal without delay or caching will hit this during any burst query. The problem is invisible in development (low traffic, single user) but surfaces immediately under real game load or if the filmography cache is cold.

**How to avoid:**
- Implement a local in-memory or Redis cache for all TMDB responses. TMDB explicitly encourages local caching. Recommended TTL: 24 hours for person/movie credits (stable data), 7 days for movie metadata.
- Use an exponential backoff + retry strategy for 429 responses.
- For game traversal specifically, pre-fetch and cache actor filmographies eagerly when a movie is first viewed in Plex rather than on-demand during gameplay.
- Add jitter to TTLs (e.g., 86400 ± 3600 seconds) to prevent cache stampedes on NAS restart.
- Never fire concurrent TMDB requests without a semaphore or rate-limiter (e.g., `p-limit` for Node.js, `asyncio.Semaphore` for Python).

**Warning signs:**
- HTTP 429 errors in logs during game sessions.
- Game chain resolution takes dramatically longer on cache miss.
- TMDB returns `status_code: 25` ("Your request count is over the allowed limit").

**Phase to address:** Phase 1 (TMDB integration) and Phase 2 (game feature)

---

### Pitfall 3: Plex media.scrobble Is the Wrong Event for "Watched" — and It's Unreliable

**What goes wrong:**
The app listens for `media.scrobble` to mark content as watched. But `media.scrobble` only fires when playback passes the 90% threshold during an active stream. It does not fire when a user manually marks content as watched in the Plex UI. It also occasionally fails to fire at all due to Plex server bugs, requiring a server restart to restore webhook delivery. Multi-user setups generate scrobbles for every user on the server, not just the owner, polluting watch history.

**Why it happens:**
Plex's webhook system has longstanding reliability issues: `media.play` sometimes never fires; stopping and restarting playback on the same title causes inconsistent delivery. There is no webhook for manual "mark as watched" actions — only active playback events are covered. The webhook payload includes `Account` info (user ID, title) but naive implementations that don't filter by account will mix all users' history together.

**How to avoid:**
- Always filter webhook payloads by `payload.Account.id` or `payload.Account.title` against a configured owner account to avoid multi-user contamination.
- Implement a fallback: periodically poll the Plex API (`/library/sections/{id}/all?type=1&includeGuids=1`) to reconcile watched state for content that missed the scrobble event.
- Treat the webhook as a best-effort trigger, not a guaranteed delivery mechanism. Design the watch-history toggle as an independent manual override that doesn't depend on webhook state.
- Log all received webhook event types on startup to confirm delivery is working; alert if no events arrive within a configurable idle window during known active playback periods.

**Warning signs:**
- Watch history is inconsistent between Plex UI and the app.
- Manually marked items are never reflected in the app.
- Multiple users' content appears in a single user's history.
- Webhook events stop arriving entirely until Plex server restart.

**Phase to address:** Phase 1 (Plex integration) and Phase 2 (watch history toggle)

---

### Pitfall 4: Radarr/Sonarr API Returns 400/422 on Duplicate — Apps Treat It as a Fatal Error

**What goes wrong:**
When adding a movie to Radarr that already exists in the library (e.g., user requests a film that was already downloaded), the API returns a 400 or 422 error with a message like `"This movie has already been added"`. Apps that treat any non-2xx as a failure will surface this as an error to the user, creating confusion. Additionally, Radarr's strict tag validation (as of v6+) rejects tag labels containing anything other than `a-z`, `0-9`, and hyphens — integrations using patterns like `"ID - Name"` for auto-tagging silently fail.

**Why it happens:**
The Radarr/Sonarr APIs are not fully idempotent for add operations. The "already exists" response is semantically a success condition from a user-request perspective, but it uses an HTTP error code. This is a known design issue in the arr-stack ecosystem. The tag validation tightening in Radarr v6 broke several downstream integrations (including Overseerr/Seerr) without a major version signal.

**How to avoid:**
- Check if a movie/series already exists in Radarr/Sonarr before attempting to add it: `GET /api/v3/movie?tmdbId={id}` (Radarr) or `GET /api/v3/series?tvdbId={id}` (Sonarr). If already present, skip the add and optionally trigger a search command instead.
- Treat 400/422 responses that contain "already been added" in the body as success, not failure.
- Sanitize all tag names to lowercase alphanumeric + hyphens only before sending to Radarr v6+ API.
- Pin the Radarr/Sonarr API version in integration code and test against version upgrades.

**Warning signs:**
- Users report "error" when requesting a movie that clearly exists in their library.
- Logs show 400 responses with "already added" body text being surfaced as user-facing errors.
- Movie requests silently fail after Radarr upgrade with no error in app logs.

**Phase to address:** Phase 2 (Radarr/Sonarr request integration)

---

### Pitfall 5: Docker Permissions on Synology NAS (PUID/PGID and ACL Conflicts)

**What goes wrong:**
Containers cannot read or write to mapped volumes on the NAS. PostgreSQL data directory is unwritable, causing the database to fail on startup. Application log or upload directories throw `Permission denied`. Sometimes the issue is inverted: containers run as root inside and create files that the NAS DSM user cannot manage.

**Why it happens:**
Synology DSM uses POSIX ACLs, not just standard Unix permissions. Docker containers operate on Unix permissions only and ignore ACLs. Permissions granted via DSM ACLs to a specific user do not propagate into containers. The correct fix is to grant permissions to the "Everyone" group or explicitly set PUID/PGID environment variables matching the NAS user running Docker. Additionally, boolean environment variables in DSM's Compose stack editor must use `1`/`0` instead of `true`/`false`, or deployment fails silently.

**How to avoid:**
- Create a dedicated `docker` system user on the Synology NAS and note its UID/GID (`id dockeruser`).
- Set `PUID` and `PGID` environment variables in all containers to match this user.
- Set folder permissions via DSM to grant read/write to "Everyone" or the specific docker user — not just via ACL rules.
- Use `chown -R PUID:PGID /path/to/volume` on the host before first container start.
- For PostgreSQL: ensure the data volume is owned by UID 999 (the default `postgres` user inside the official Postgres Docker image) or use the `POSTGRES_USER` override with matching host permissions.
- Synology's port 5432 is internally reserved — use a non-standard host port (e.g., `5433:5432`) in `docker-compose.yml`.

**Warning signs:**
- Container exits immediately with `Permission denied` on volume path.
- PostgreSQL logs: `FATAL: data directory "/var/lib/postgresql/data" has wrong ownership`.
- Files written by container appear as owned by `root` or an unknown UID on the NAS.

**Phase to address:** Phase 0 (infrastructure setup)

---

### Pitfall 6: Synology Docker Resource Exhaustion — OOM Kills the Entire Stack

**What goes wrong:**
Under load (e.g., game session with cold TMDB cache making many API calls, Plex scanning a large library, PostgreSQL running a large query), containers consume unbounded memory. The NAS kernel's OOM killer terminates a container — sometimes the PostgreSQL container — silently. The database comes back in a corrupted or inconsistent state, and other containers that depend on it also die. The NAS may become inaccessible via SSH until a hard reboot.

**Why it happens:**
Docker on Synology NAS (often with 2-8GB RAM, shared with DSM and other processes) does not set memory limits by default. A single container with a memory leak or a burst-heavy workload can consume all available RAM. The sawtooth memory pattern (grow until OOM kill, restart, repeat) is common in long-running containers without limits. Some older Synology kernels have cgroup limitations that make Docker memory limits ineffective, though this is less common on DSM 7+.

**How to avoid:**
- Set explicit `mem_limit` (Docker Compose) on every container: `mem_limit: 512m` for the app, `mem_limit: 256m` for PostgreSQL on light workloads.
- Set `restart: unless-stopped` (not `always`) to prevent infinite restart loops from masking real errors.
- Configure PostgreSQL `shared_buffers`, `work_mem`, and `max_connections` conservatively in `postgresql.conf` or via environment variables (`POSTGRES_MAX_CONNECTIONS=20`).
- Add health checks to Docker Compose so dependent containers don't start if PostgreSQL is unhealthy.
- Monitor container stats: `docker stats` or install Portainer on the NAS for a visual overview.

**Warning signs:**
- Container randomly restarts with no log output.
- PostgreSQL log shows `out of memory` or sudden termination without shutdown sequence.
- NAS becomes unresponsive when multiple media-related containers are active simultaneously.

**Phase to address:** Phase 0 (infrastructure) and ongoing operations

---

### Pitfall 7: Game Session State Corruption from Concurrent Requests or NAS Restart

**What goes wrong:**
The Movie Game tracks used actors per session to prevent cycles in the chain traversal. If session state is stored only in application memory (not persisted), a container restart — extremely common on a NAS due to OOM kills, DSM updates, or power events — silently wipes all active game sessions. Users mid-game lose their state. Worse, if two browser tabs or API calls for the same session arrive concurrently, the "used actors" set can be read, modified, and written back by two handlers simultaneously, creating a race condition that allows actor reuse.

**Why it happens:**
Stateful in-process session storage is fragile in containerized environments. NAS deployments have higher restart frequency than cloud VMs. Concurrent requests to the same session (possible if the client retries a request) create race conditions on mutable session objects without locking.

**How to avoid:**
- Persist game session state to PostgreSQL, not in-memory. Use a `game_sessions` table with `session_id`, `used_actor_ids` (array or JSONB), `current_movie_id`, `created_at`, `updated_at`.
- Use database-level locking (`SELECT ... FOR UPDATE`) when reading and modifying session state to prevent race conditions.
- Add session expiry (e.g., TTL of 2 hours of inactivity) with a cleanup job to prevent session table bloat.
- On client side, disable the "submit move" button after submission until the server response arrives (prevents double-submit races).

**Warning signs:**
- Game sessions disappear after any container restart.
- Users report being able to reuse an actor that was already played.
- Session state diverges between client and server after a network hiccup causes a retry.

**Phase to address:** Phase 2 (game feature design)

---

### Pitfall 8: Sonarr Season Numbering Mismatches (TVDB vs. Scene Ordering)

**What goes wrong:**
The app sends a request to Sonarr to download "Season 17" of a show. Sonarr searches for and downloads "Season 16" instead (or fails to find anything). The mismatch is silent — no error is returned, the wrong content downloads. For anime, absolute episode numbering conflicts with TVDB season ordering cause entire season offsets.

**Why it happens:**
Sonarr uses TVDB as its canonical source but many release groups follow "Scene" naming conventions that differ from TVDB. Sonarr uses TheXEM to bridge this gap, but XEM coverage is incomplete and often delayed. Specifically: a show listed as S17 on TVDB may be S16 in Scene, so requesting S17 from Sonarr returns Scene S16 content. Additionally, TVDB has a 1–3 hour API cache, Sonarr's Skyhook adds another few hours on top, and Sonarr only refreshes series metadata every 12 hours — so recently added or updated shows can be stale.

**How to avoid:**
- When integrating with Sonarr, always use the Sonarr-internal series/season identifiers (from `GET /api/v3/series`) rather than user-visible season numbers from TMDB or your own database.
- Do not assume TMDB season numbers == Sonarr season numbers for any show.
- For anime specifically, check whether the series uses absolute episode ordering in Sonarr before constructing requests.
- Surface the "request submitted to Sonarr" confirmation rather than claiming the download is guaranteed, since matching may still fail.

**Warning signs:**
- Wrong season downloads without any error response from Sonarr.
- Anime episodes are offset by a constant number (e.g., always 12 episodes behind/ahead).
- Sonarr shows the series with a different season count than TMDB.

**Phase to address:** Phase 2 (Sonarr integration)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store TMDB responses without TTL | Simpler cache code | Stale movie/actor data; cast changes not reflected | Never — always set TTL |
| Hardcode Plex token in config file committed to repo | Fast dev setup | Token exposed in git history; requires credential rotation | Never in version-controlled files |
| Use in-memory dict for game session state | Zero infra overhead | All sessions lost on any restart; no concurrency safety | Prototype only, never production |
| Trust Plex scrobble as sole watch-history source | Simple event-driven design | Missed scrobbles silently leave content unmarked | Only if manual override toggle also exists |
| Skip PUID/PGID setup "for now" on Synology | Faster initial setup | Recurring permission errors; root-owned files in NAS volumes | Never past proof-of-concept |
| No memory limits on Docker containers | Simpler compose file | Single container OOM can crash entire NAS stack | Never on shared NAS |
| Treat all Radarr/Sonarr non-2xx as errors | Simple error handling | Duplicate-add errors surface as false failures to users | Never |
| Single TMDB API key for all requests, no retry | Simple code | 429 blackout kills game sessions mid-play | Only for very low-volume personal use |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| TMDB API | Firing unbatched concurrent requests during game traversal | Serialize TMDB requests with a rate limiter; cache aggressively (24h TTL for credits) |
| TMDB API | Assuming filmography data is static | Actor credits change (new releases, corrections); refresh cache periodically, not indefinitely |
| TMDB API | Exposing API key client-side to work around rate limits | Keep key server-side; proxy all TMDB requests through your backend |
| Plex Webhooks | Parsing body as JSON directly | Plex sends `multipart/form-data`; extract the `payload` field, then parse as JSON |
| Plex Webhooks | Not filtering by account ID | All managed users on the Plex server generate scrobbles; filter to owner account |
| Plex Webhooks | Using scrobble as the only "watched" trigger | `media.scrobble` doesn't fire for manually marked items; implement polling fallback |
| Plex Webhooks | Not handling webhook delivery failures | No retry mechanism; design for idempotency and reconciliation |
| Radarr API | Treating 400/422 "already added" as an error | Check for existence first with `GET /movie?tmdbId=`; treat "already exists" response as success |
| Radarr API | Using tags with spaces or special characters (v6+) | Sanitize to `[a-z0-9-]` only; Radarr v6 rejects non-conforming tag names |
| Sonarr API | Using TMDB/user-visible season numbers in requests | Always use Sonarr-internal season IDs; TVDB and Scene numbering frequently diverge |
| Sonarr API | Assuming freshly added series metadata is current | TVDB cache + Skyhook cache + Sonarr refresh = up to ~15 hour staleness for new shows |
| Synology Docker | Not setting PUID/PGID matching NAS user | Containers cannot access volume data; files owned by wrong user |
| Synology Docker | Exposing PostgreSQL on port 5432 | Port is internally reserved on Synology; use `5433:5432` or any other host port |
| Synology Docker | Using `true`/`false` in Compose env vars via DSM UI | DSM stack editor requires `1`/`0` for booleans; `true` may cause deployment failures |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Cold TMDB cache during game traversal | Game session takes 10–30+ seconds to resolve a 4-step chain | Pre-warm cache on Plex library scan; cache all credits on first access | Every container restart wipes in-memory cache |
| Unbounded PostgreSQL connections from app | `FATAL: remaining connection slots are reserved` errors | Set `max_connections` in Postgres; use connection pooling (pgBouncer or app-level pool) | When multiple game sessions run simultaneously |
| Plex library API called on every page load | Slow UI; Plex server CPU spikes | Cache library metadata locally; invalidate on webhook events | Large libraries (1000+ items) |
| Synchronous TMDB calls blocking webhook handler | Webhook responses time out; Plex retries delivery, creating duplicate events | Process webhook payloads asynchronously (queue or background task) | Any Plex webhook that triggers TMDB lookups |
| N+1 TMDB queries for actor filmography listing | Each actor in a movie triggers a separate API call | Batch-fetch or pre-cache all cast member credits when a movie is added to the game | Any game with > 5 cast members |
| No index on watch history table | Watch status queries slow as history grows | Index on `(user_id, media_id)` and `watched_at` columns | After a few hundred entries on NAS-class hardware |
| Docker volumes on same disk as DSM system | I/O contention between OS and database | Use a dedicated volume/disk for Docker data if NAS has multiple drives | Heavy concurrent Plex + PostgreSQL I/O |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Plex token in `docker-compose.yml` committed to git | Token exposed in repo history; full Plex library access for anyone with the token | Use `.env` file excluded via `.gitignore`; reference as `${PLEX_TOKEN}` in compose |
| TMDB API key in source code or logs | Key abuse; rate limit exhaustion under attacker's IP | Environment variable only; never log full request URLs that include the key |
| Radarr/Sonarr API keys in client-side JavaScript | Attacker can add arbitrary content to your download queue | All arr-stack API calls must be server-side only |
| Webhook endpoint with no authentication | Anyone on your network (or internet if port-forwarded) can inject fake watch events | Validate `X-Plex-Signature` header on incoming webhooks (HMAC-SHA1 of payload + shared secret) |
| PostgreSQL port exposed on host interface without firewall | Database accessible from local network without credentials | Bind PostgreSQL Docker port to `127.0.0.1` only: `127.0.0.1:5433:5432` |
| Running all containers as root (no PUID/PGID) | Container breakout gives root access to NAS filesystem | Set non-root PUID/PGID; use `user:` directive in Compose |
| Storing Plex watch tokens in browser localStorage | XSS attack can exfiltrate token | Use httpOnly session cookies for any Plex-derived auth state |

---

## "Looks Done But Isn't" Checklist

- [ ] **Plex webhook parsing:** Tested with actual Plex server (not a mock JSON POST) — Plex's multipart format differs from naive JSON webhook testing tools.
- [ ] **Watch history "mark as watched" toggle:** Manually marking watched in Plex UI reflects in app — requires polling fallback, not just webhook.
- [ ] **TMDB cache persistence:** Cache survives container restart — in-memory cache is wiped on every NAS reboot; needs Redis or DB-backed storage.
- [ ] **Radarr duplicate handling:** Requesting a movie already in Radarr shows "already in library" — not a generic error message.
- [ ] **Multi-user filtering:** Another Plex managed user watching content does NOT appear in the primary user's app history.
- [ ] **Game session persistence:** Active game session survives container restart mid-play — requires DB-backed session store.
- [ ] **Sonarr season request:** Requesting a specific season downloads the correct season (not season N-1) — verify with a show known to have TVDB/Scene offset.
- [ ] **PostgreSQL startup order:** App container waits for PostgreSQL health check before starting — `depends_on: condition: service_healthy` in Compose.
- [ ] **Memory limits set:** `docker stats` shows no container consuming > configured limit under game load — no unbounded containers.
- [ ] **Secrets not in repo:** `git log --all -p | grep PLEX_TOKEN` returns nothing — no accidental token commits in history.
- [ ] **Webhook delivery confirmed:** Plex webhook fires and is received after Plex server restart — delivery stops without restart in some Plex builds.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-----------------|--------------|
| Plex multipart/form-data parsing | Phase 1 — Plex webhook listener implementation | Send a real Plex webhook event; confirm payload fields are extracted |
| TMDB rate limiting in game traversal | Phase 1 (cache layer) + Phase 2 (game feature) | Simulate 10 concurrent game moves; confirm no 429 errors in logs |
| Plex scrobble unreliability / manual mark gap | Phase 1 (webhook) + Phase 2 (watch toggle) | Manually mark item watched in Plex; confirm app reflects it |
| Radarr/Sonarr duplicate 400/422 | Phase 2 — arr-stack request integration | Attempt to add already-existing movie; confirm UI shows "already in library" |
| Docker permissions on Synology (PUID/PGID) | Phase 0 — infrastructure setup | Restart containers cold; confirm no permission errors in logs |
| Synology OOM / resource exhaustion | Phase 0 (limits) + Phase 3 (load testing) | Run `docker stats` under game session load; confirm limits are respected |
| Game session state corruption | Phase 2 — game feature design | Restart container mid-session; confirm session resumes or fails gracefully |
| Sonarr season numbering mismatch | Phase 2 — Sonarr integration | Request a known offset show (e.g., animated series); verify correct season queued |

---

## Sources

- [TMDB Rate Limiting Official Docs](https://developer.themoviedb.org/docs/rate-limiting) — HIGH confidence (official)
- [TMDB Community: Discover and Details Rate Limiting](https://www.themoviedb.org/talk/6571b5547eb5f200ea7f8057) — HIGH confidence (official forum)
- [TMDB Community: Local Cache & Storage of API Data](https://www.themoviedb.org/talk/52c0d75719c2951bf418ce77) — HIGH confidence (official forum, confirms caching is permitted and encouraged)
- [Plex Webhooks Official Documentation](https://support.plex.tv/articles/115002267687-webhooks/) — HIGH confidence (official)
- [Plex Forum: BUG: Not all webhooks are triggered](https://forums.plex.tv/t/bug-not-all-webhooks-are-triggered/808869) — HIGH confidence (confirmed bug thread)
- [Plex Forum: Media.play webhook never fires](https://forums.plex.tv/t/media-play-webhook-never-fires/577433) — HIGH confidence (community-confirmed issue)
- [GitHub: Lots and lots of duplicate scrobbles — Plex-Trakt-Scrobbler](https://github.com/trakt/Plex-Trakt-Scrobbler/issues/315) — HIGH confidence (reproducible issue with workarounds)
- [Plex Forum: Webhooks not passing all payload details](https://forums.plex.tv/t/webhooks-not-passing-all-the-payload-details/570987?page=2) — MEDIUM confidence (community reports)
- [GitHub: plex-webhook-proxy — unwrapping Plex multipart requests](https://github.com/jfklingler/plex-webhook-proxy) — HIGH confidence (dedicated tool exists for this problem)
- [Radarr Troubleshooting — Servarr Wiki](https://wiki.servarr.com/radarr/troubleshooting) — HIGH confidence (official)
- [GitHub: Radarr/Sonarr Tag Creation Fails with 400 Error — Overseerr](https://github.com/sct/overseerr/issues/4306) — HIGH confidence (reproducible, version-specific)
- [GitHub: All requests to Add Movie to Radarr failing — Overseerr](https://github.com/sct/overseerr/issues/3751) — HIGH confidence
- [Sonarr FAQ — Servarr Wiki](https://wiki.servarr.com/sonarr/faq) — HIGH confidence (official, documents XEM/TVDB numbering)
- [Sonarr Forum: Season and Episodes mismatch TVDB & Plex](https://forums.sonarr.tv/t/season-and-episodes-mismatch-tvdb-plex/38032) — HIGH confidence (widely reported)
- [GitHub: Episodes incorrectly reordering — Sonarr](https://github.com/Sonarr/Sonarr/issues/3785) — HIGH confidence
- [Marius Hosting: Synology Common Docker Issues and Fixes](https://mariushosting.com/synology-common-docker-issues-and-fixes/) — HIGH confidence (Synology-specific, widely referenced)
- [DrFrankenstein: Setting up restricted Docker user and obtaining IDs](https://drfrankenstein.co.uk/step-2-setting-up-a-restricted-docker-user-and-obtaining-ids/) — HIGH confidence (Synology-specific guide)
- [SynoForum: Safe memory limit for Docker containers](https://www.synoforum.com/threads/what-is-a-safe-memory-limit-for-docker-containers.7566/) — MEDIUM confidence (community forum)
- [GitHub: Plex Token as Docker secret — Plex-Auto-Languages](https://github.com/RemiRigal/Plex-Auto-Languages/issues/11) — MEDIUM confidence
- [GitGuardian: 8.5% of Docker Images Expose API and Private Keys](https://blog.gitguardian.com/8docker-images-api-and-private-keys/) — HIGH confidence (research-backed)
- [Plex Scrobbling Everyone Watch History — Trakt Forums](https://forums.trakt.tv/t/plex-scrobbling-everyone-watch-history/53788) — HIGH confidence (multi-user scrobble contamination, confirmed)
