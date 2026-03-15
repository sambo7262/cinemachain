# Stack Research

**Domain:** Home media companion app (Plex/arr-stack integration)
**Researched:** 2026-03-14
**Confidence:** HIGH (core stack), MEDIUM (version pinning for less-active libs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Runtime | LTS, PlexAPI requires >=3.10; broad library support |
| FastAPI | 0.115.x | HTTP server (webhook receiver + API) | Async-native (ASGI), auto-generated OpenAPI docs, handles multipart POST for Plex webhooks; 38% adoption among Python devs in 2025, up from 29% |
| Uvicorn | 0.30.x | ASGI server | Standard pairing with FastAPI; minimal memory footprint vs gunicorn |
| SQLite (via Python stdlib) | 3.x (bundled) | Persistent storage for watch history, actor graph cache | Zero-dependency, single file, survives Docker restarts via bind mount |
| requests-cache | 1.3.0 | HTTP-level caching for TMDB API calls | SQLite backend by default, drop-in replacement for `requests.Session`, sub-ms cache hits, no Redis needed |
| Docker + Docker Compose | Compose v2 | Container runtime | Supported natively by Synology Container Manager (DSM 7.2+) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PlexAPI | 4.18.0 | Plex server interaction (library queries, watch history, alert listener) | Primary integration for fetching recently watched, searching library, triggering playback; `pip install plexapi[alert]` for notification listener |
| tmdbv3api | 1.9.0 | TMDB API client (actor filmography, movie metadata, cast lookup) | Actor-chain traversal and movie metadata enrichment; lightweight, well-tested |
| pyarr | 5.2.0 | Radarr + Sonarr API client | Sending movie/TV add requests; returns JSON; supports Radarr >=4.3.2 and Sonarr >=3.0.10 |
| python-dotenv | 1.0.x | Environment variable management | Load API keys from `.env` file; keeps secrets out of compose files |
| pydantic | 2.x | Data validation and models | FastAPI uses it natively; model Plex webhook payloads and TMDB responses |
| httpx | 0.27.x | Async HTTP client | Use instead of `requests` for any async code paths in FastAPI route handlers |
| diskcache | 5.6.x | Advanced disk-based cache (optional) | If you need TTL-based caching beyond what requests-cache provides (e.g., actor graph nodes) |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker Compose v2 | Local dev and NAS deployment | Use `compose.yaml` (preferred filename over `docker-compose.yml`) |
| python:3.12-slim | Base Docker image | ~130MB vs ~1GB full image; avoids unnecessary system libs |
| Tailscale sidecar (tailscale/tailscale) | Remote access over Tailscale network | Sidecar pattern in Compose; set `TS_USERSPACE=true` for Synology DSM |
| pytest + pytest-asyncio | Testing | FastAPI's async handlers need async test support |
| ruff | Linting/formatting | Fast, single-tool replacement for flake8 + isort + black |

---

## Installation

```bash
# Core dependencies
pip install fastapi uvicorn[standard] plexapi[alert] tmdbv3api pyarr python-dotenv pydantic httpx requests-cache

# Optional advanced caching
pip install diskcache

# Dev tools
pip install pytest pytest-asyncio ruff
```

Example `requirements.txt` with pinned versions:
```
fastapi==0.115.6
uvicorn[standard]==0.30.6
plexapi==4.18.0
tmdbv3api==1.9.0
pyarr==5.2.0
python-dotenv==1.0.1
pydantic==2.9.2
httpx==0.27.2
requests-cache==1.3.0
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| FastAPI | Flask | If you want a more minimal WSGI app and don't need async; Flask is still solid but lacks native async concurrency |
| FastAPI | Litestar | If you want a more opinionated async framework with stronger typing; smaller community |
| tmdbv3api | tmdbsimple (2.9.2) | tmdbsimple is also maintained (copyright 2013-2025) and covers full API surface; choose if tmdbv3api has missing endpoints |
| tmdbv3api | `themoviedb` (leandcesar) | More modern async-friendly wrapper; use if you go fully async on TMDB calls |
| pyarr | Direct `httpx` calls to Radarr/Sonarr REST API | pyarr's last release is July 2023; if the API shape has drifted, raw httpx calls to `/api/v3/` endpoints with `X-Api-Key` header are equally simple and more reliable |
| SQLite + requests-cache | Redis | Only needed if you add multi-process workers or need pub/sub; overkill for single-user NAS app |
| Tailscale sidecar | Synology QuickConnect | QuickConnect is Synology-proprietary and routes through Synology servers; Tailscale is zero-trust peer-to-peer |
| Uvicorn | Gunicorn + Uvicorn workers | Only if you scale to multiple workers; single-user app doesn't need it |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Django | Massive overhead for a single-user companion app with ~5 routes; ORM and auth system are unnecessary weight | FastAPI |
| celery + Redis | Overkill task queue; no background jobs needed for this use case | FastAPI background tasks (`BackgroundTasks`) or asyncio |
| PostgreSQL | Heavier resource consumption than SQLite; no benefit for single-user local data | SQLite |
| pytmdb3 / tmdb3 | Abandoned; last commit 2014-2016 | tmdbv3api or tmdbsimple |
| PyPI package `cinemagoer` (formerly IMDbPY) | Scrapes IMDb, not an official API; fragile, against ToS | TMDB API (official, free, well-maintained) |
| plex_notify / custom webhook scripts | Ad-hoc; PlexAPI's `plexapi[alert]` and a FastAPI endpoint cover all webhook needs cleanly | PlexAPI + FastAPI |
| linuxserver/plex Docker image | Only needed to run Plex itself; CinemaChain is a companion app, not the media server | Your own `python:3.12-slim` image |

---

## Synology NAS Specific Notes

### Container Manager (DSM 7.2+)

- DSM 7.2 introduced **Container Manager**, which replaces the old Docker package and supports Docker Compose v2 natively from the UI.
- Use `compose.yaml` (Compose v2 preferred filename) in your project root.
- Deploy by uploading or cloning to a NAS share (e.g., `/volume1/docker/cinemachain/`) and importing via Container Manager UI, or SSH + `docker compose up -d`.

### Resource Constraints

- Recommend setting memory limits in `compose.yaml` to protect NAS stability. A lightweight FastAPI + SQLite app typically uses 80–150MB RAM at idle.
- Example limits for a DS923+ or similar (8GB+ RAM NAS):
  ```yaml
  deploy:
    resources:
      limits:
        memory: 256m
  ```
- For older/lower-RAM NAS (DS720+, DS418), use `memory: 128m` and avoid Redis entirely.
- CPU limiting is less critical for a low-traffic single-user app; skip unless you observe issues.

### Volume Mounts

```yaml
volumes:
  - /volume1/docker/cinemachain/data:/app/data   # SQLite DB + cache files
  - /volume1/docker/cinemachain/.env:/app/.env    # API keys (never bake into image)
```

### Tailscale Integration (Sidecar Pattern)

The recommended approach for Synology DSM 7 is the **Tailscale sidecar** pattern — a separate Tailscale container in the same Compose project, with your app container using `network_mode: service:tailscale` to share its network interface.

```yaml
services:
  tailscale:
    image: tailscale/tailscale:latest
    hostname: cinemachain
    environment:
      - TS_AUTHKEY=${TS_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=true          # REQUIRED for Synology DSM — kernel TUN not available
      - TS_SERVE_CONFIG=/config/ts-serve.json
    volumes:
      - /volume1/docker/cinemachain/tailscale:/var/lib/tailscale
    restart: unless-stopped

  cinemachain:
    build: .
    network_mode: service:tailscale   # Share Tailscale's network namespace
    depends_on:
      - tailscale
    volumes:
      - /volume1/docker/cinemachain/data:/app/data
      - /volume1/docker/cinemachain/.env:/app/.env
    restart: unless-stopped
```

`TS_USERSPACE=true` is **mandatory** on Synology — the kernel TUN device is not available in DSM containers; without it, the tunnel is never created.

The app listens on `127.0.0.1:8000` inside the shared network namespace; Tailscale Serve exposes it at `https://cinemachain.<tailnet>.ts.net`.

---

## API Integration Patterns

### TMDB API

**Client:** `tmdbv3api` 1.9.0 (`pip install tmdbv3api`)

**Auth:** Free API key from developer.themoviedb.org (no OAuth needed for read-only).

**Rate limits:** ~40–50 requests/second per IP (no daily cap). Respect HTTP 429 with exponential backoff.

**Caching strategy:** Wrap all TMDB calls in a `requests-cache` session with a SQLite backend and a TTL of 24–72 hours. Movie/actor data changes infrequently.

```python
import requests_cache
from tmdbv3api import TMDb, Movie, Person

requests_cache.install_cache(
    "tmdb_cache",
    backend="sqlite",
    expire_after=86400,  # 24 hours
    urls_expire_after={"api.themoviedb.org/3/person*": 3600 * 72}
)

tmdb = TMDb()
tmdb.api_key = os.environ["TMDB_API_KEY"]

movie = Movie()
person = Person()

# Actor filmography for chain traversal:
credits = person.movie_credits(person_id)  # returns cast + crew credits
# Movie cast lookup:
cast = movie.credits(movie_id)
```

**Key endpoints for CinemaChain:**
- `GET /person/{id}/movie_credits` — all movies an actor appeared in
- `GET /movie/{id}/credits` — full cast/crew for a movie
- `GET /search/person?query=` — find actor by name
- `GET /search/movie?query=` — find movie by title

### Plex API + Webhooks

**Client:** `plexapi` 4.18.0 (`pip install plexapi[alert]`)

**Auth:** Token-based. Retrieve your token from Plex Web App > Account > Authorized Devices, or via `MyPlexAccount`.

**Requirements:** Plex Pass subscription is **required** for webhooks. Plex Media Server >= 1.3.4.

**Watch history:**

```python
from plexapi.server import PlexServer

plex = PlexServer("http://192.168.x.x:32400", PLEX_TOKEN)

# Recently watched movies:
history = plex.library.section("Movies").history(maxresults=50)

# Full account history:
account_history = plex.history()
```

**Webhook receiver (FastAPI):**

Plex sends a `multipart/form-data` POST. The JSON payload is in the `payload` field; some events also attach a JPEG thumbnail as a second part.

```python
from fastapi import FastAPI, Request, Form
import json

app = FastAPI()

@app.post("/plex/webhook")
async def plex_webhook(payload: str = Form(...)):
    data = json.loads(payload)
    event = data.get("event")           # e.g., "media.scrobble"
    metadata = data.get("Metadata", {})
    title = metadata.get("title")
    media_type = metadata.get("type")   # "movie" or "episode"

    if event == "media.scrobble":
        # User finished watching — persist to SQLite
        ...
    return {"status": "ok"}
```

**Key events for CinemaChain:**
- `media.scrobble` — item marked as watched (fires at ~90% playback)
- `media.play` / `media.stop` — for session tracking if needed
- `library.new` — new item added to library

**Alert listener** (server-push notifications, alternative to webhooks):
```python
from plexapi.alert import AlertListener
listener = AlertListener(plex, callback=my_handler)
listener.start()
```

### Radarr/Sonarr APIs

**Client:** `pyarr` 5.2.0 OR direct `httpx` calls (see note below).

**Auth:** `X-Api-Key` header. Key found in: Settings → General → Security.

**Base URL pattern:** `http://<nas-ip>:<port>/api/v3/`

**pyarr usage:**

```python
from pyarr import RadarrAPI, SonarrAPI

radarr = RadarrAPI(host_url="http://192.168.x.x:7878", api_key=RADARR_KEY)
sonarr = SonarrAPI(host_url="http://192.168.x.x:8989", api_key=SONARR_KEY)

# Look up movie by TMDB ID before adding:
results = radarr.lookup_movie(term=f"tmdb:{tmdb_id}")
movie = results[0]

# Add movie to Radarr:
radarr.add_movie(
    db_id=tmdb_id,
    quality_profile_id=1,
    root_dir="/volume1/media/movies",
    monitored=True,
    search_for_movie=True
)

# Add TV show to Sonarr by TVDB ID:
sonarr.add_series(
    tvdb_id=tvdb_id,
    quality_profile_id=1,
    root_dir="/volume1/media/tv",
    monitored=True,
    search_for_missing_episodes=True
)
```

**Direct httpx fallback** (use if pyarr proves stale):

```python
import httpx

headers = {"X-Api-Key": RADARR_KEY}
# Lookup by TMDB ID:
resp = httpx.get(f"{RADARR_URL}/api/v3/movie/lookup", params={"term": f"tmdb:{tmdb_id}"}, headers=headers)
movie_data = resp.json()[0]

# Add movie:
httpx.post(f"{RADARR_URL}/api/v3/movie", json={
    "tmdbId": tmdb_id,
    "title": movie_data["title"],
    "year": movie_data["year"],
    "qualityProfileId": 1,
    "rootFolderPath": "/volume1/media/movies",
    "monitored": True,
    "addOptions": {"searchForMovie": True}
}, headers=headers)
```

**Note on pyarr:** Last release July 2023. The library is stable for Radarr v4.3.2+ and Sonarr v3.0.10+. If you encounter issues with newer Radarr/Sonarr versions, fall back to direct httpx calls — the Servarr REST API is well-documented at https://radarr.video/docs/api/ and https://wiki.servarr.com/sonarr/api.

---

## Sources

- [PlexAPI on PyPI](https://pypi.org/project/PlexAPI/) — HIGH confidence (official package page, v4.18.0 confirmed)
- [Python-PlexAPI Documentation](https://python-plexapi.readthedocs.io/en/latest/introduction.html) — HIGH confidence (official docs)
- [Plex Webhooks Support Article](https://support.plex.tv/articles/115002267687-webhooks/) — HIGH confidence (official Plex docs)
- [tmdbv3api on PyPI](https://pypi.org/project/tmdbv3api/) — HIGH confidence (official package, v1.9.0)
- [TMDB API Rate Limiting Docs](https://developer.themoviedb.org/docs/rate-limiting) — HIGH confidence (official TMDB developer docs)
- [TMDB Wrappers & Libraries](https://developer.themoviedb.org/docs/wrappers-and-libraries) — MEDIUM confidence (TMDB lists community libs but doesn't officially endorse one)
- [pyarr on PyPI](https://pypi.org/project/pyarr/) — HIGH confidence for v5.2.0; MEDIUM confidence on currency (last release July 2023)
- [pyarr GitHub](https://github.com/totaldebug/pyarr) — MEDIUM confidence (stable but potentially behind latest Radarr/Sonarr API versions)
- [Radarr API Docs](https://radarr.video/docs/api/) — HIGH confidence (official Radarr docs)
- [Servarr Wiki](https://wiki.servarr.com/) — HIGH confidence (official *arr documentation)
- [requests-cache on PyPI](https://pypi.org/project/requests-cache/) — HIGH confidence (v1.3.0, actively maintained)
- [FastAPI vs Flask 2025 (strapi.io)](https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison) — MEDIUM confidence (third-party blog but well-sourced benchmarks)
- [Tailscale Sidecar for Synology NAS (tatey.com, March 2026)](https://tatey.com/2026/03/08/tailscale-sidecar-pattern-for-synology-nas-with-dsm-7-and-container-manager/) — HIGH confidence (very recent, DSM 7 specific, covers TS_USERSPACE requirement)
- [Tailscale Docker Docs](https://tailscale.com/kb/1282/docker) — HIGH confidence (official Tailscale docs)
- [Synology Container Manager](https://www.synology.com/en-br/dsm/feature/docker) — HIGH confidence (official Synology page)
- [Docker Memory Limits on Synology (SynoForum)](https://www.synoforum.com/threads/what-is-a-safe-memory-limit-for-docker-containers.7566/) — MEDIUM confidence (community forum)
- [awesome-arr (GitHub)](https://github.com/Ravencentric/awesome-arr) — MEDIUM confidence (community curated list; useful for discovering ecosystem tools)
