# Architecture Research

**Domain:** Home media companion app (Plex/arr-stack integration)
**Researched:** 2026-03-14
**Confidence:** HIGH (core patterns), MEDIUM (specific schema designs), LOW (marked inline)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │  TMDB API    │  │  Radarr API  │  │ Sonarr   │  │ Plex Media│  │
│  │ api.tmdb.org │  │ :7878/api/v3 │  │:8989/v3  │  │  Server   │  │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └─────┬─────┘  │
└─────────│────────────────-│───────────────│───────────────│─────────┘
          │                 │               │               │
          │                 │               │               │ webhook POST
          ▼                 ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DOCKER COMPOSE STACK                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  BACKEND (FastAPI / Python)                   │  │
│  │                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │  /webhook/plex  │  │  /api/game/*    │  │ /api/query/*│  │  │
│  │  │  (multipart)    │  │  (game session) │  │ (search/req)│  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘  │  │
│  │           │                    │                   │         │  │
│  │  ┌────────▼────────────────────▼───────────────────▼──────┐  │  │
│  │  │              Service Layer                              │  │  │
│  │  │  TMDBService | PlexService | RadarrService | GameSvc   │  │  │
│  │  └────────────────────────────┬────────────────────────────┘  │  │
│  └───────────────────────────────│────────────────────────────────┘  │
│                                  │                                  │
│  ┌───────────────────────────────▼────────────────────────────────┐ │
│  │                    PostgreSQL                                   │ │
│  │  filmography_cache | watch_history | game_sessions | actors    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  FRONTEND (React/Vue)                        │   │
│  │   Movie Game Mode  |  Query Mode  |  Request Status          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| FastAPI Backend | REST API, webhook listener, orchestration | Python 3.11+, uvicorn, asyncpg |
| TMDBService | Fetch + cache movie/actor metadata | httpx async client, PostgreSQL cache table |
| PlexService | Webhook parsing, history queries | python-multipart, plexapi (optional) |
| RadarrService | Movie request submission | httpx POST to `/api/v3/movie` |
| SonarrService | TV show request submission | httpx POST to `/api/v3/series` |
| GameService | Session state, actor chain logic | Pure Python + DB queries |
| PostgreSQL | Persistent data store | postgres:16-alpine, bind-mounted volume |
| Frontend | Two-mode UI (Game + Query) | React or Vue, fetch/axios |

---

## Recommended Project Structure

```
cinemachain/
├── docker-compose.yml
├── .env
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   └── app/
│       ├── main.py                  # FastAPI app init, router mounting
│       ├── db.py                    # async engine, session factory
│       ├── settings.py              # pydantic-settings config
│       ├── models/
│       │   ├── filmography.py       # Movie, Person, MovieCast ORM models
│       │   ├── watch_history.py     # WatchEvent ORM model
│       │   └── game.py              # GameSession, UsedActor ORM models
│       ├── schemas/
│       │   ├── tmdb.py              # Pydantic request/response schemas
│       │   ├── game.py
│       │   └── plex_webhook.py      # Typed Plex payload schema
│       ├── services/
│       │   ├── tmdb.py              # TMDB API client + cache logic
│       │   ├── radarr.py            # Radarr API client
│       │   ├── sonarr.py            # Sonarr API client
│       │   ├── plex.py              # Webhook parsing + history
│       │   └── game.py              # Game session business logic
│       ├── routers/
│       │   ├── webhook.py           # POST /webhook/plex
│       │   ├── game.py              # GET/POST /api/game/*
│       │   └── query.py             # GET/POST /api/query/*
│       └── dependencies.py          # DB session, service injection
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── views/
│       │   ├── GameMode.vue         # Actor chain game UI
│       │   └── QueryMode.vue        # Search + request UI
│       └── components/
│           ├── MovieCard.vue
│           └── ActorSelector.vue
└── volumes/
    └── postgres/                    # bind-mounted DB data (gitignored)
```

---

## Architectural Patterns

### Pattern 1: TMDB Data Caching

TMDB allows local caching for "reasonable periods." The terms require attribution but permit personal/non-commercial caching.

**Rate limits:** ~50 requests/second (practical ceiling; original 40/10s limit removed Dec 2019).

**What to cache:**
- `GET /3/movie/{id}` — movie details (title, overview, release_date, poster_path, imdb_id)
- `GET /3/movie/{id}/credits` — cast list (person id, name, character, order, profile_path)
- `GET /3/person/{id}` — actor biography, profile image
- `GET /3/person/{id}/movie_credits` — actor filmography (all movies they appeared in)

**TTL strategy (recommended):**

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Movie details | 7 days | Changes rarely after release |
| Movie credits | 14 days | Very stable |
| Person details | 7 days | Stable |
| Person movie_credits | 3 days | Can grow with new releases |
| Search results | 1 hour | More volatile |

**Implementation pattern:**

```python
async def get_movie_credits(self, tmdb_id: int) -> list[CastMember]:
    # Check DB cache first
    cached = await db.get_cached_credits(tmdb_id)
    if cached and cached.fetched_at > datetime.now() - timedelta(days=14):
        return cached.cast
    # Miss: fetch from TMDB
    data = await self.client.get(f"/3/movie/{tmdb_id}/credits")
    await db.upsert_credits(tmdb_id, data["cast"])
    return data["cast"]
```

**`append_to_response` pattern** (reduces API calls):
`GET /3/movie/{id}?append_to_response=credits` returns movie + credits in one call. Use this when first-time populating a movie record.

---

### Pattern 2: Plex Webhook Handling

Plex sends webhooks as **multipart/form-data** POST requests, NOT JSON. The JSON payload is in a form field named `payload`. Requires active **Plex Pass** on the admin account.

**Event types relevant to CinemaChain:**

| Event | Fires When | Use Case |
|-------|-----------|----------|
| `media.scrobble` | Media watched past 90% mark | Mark movie as watched, trigger next game prompt |
| `media.play` | Playback starts | Optional: track in-progress |
| `media.stop` | Playback stops | Optional: partial watch logging |

**Payload structure:**

```json
{
  "event": "media.scrobble",
  "user": true,
  "owner": true,
  "Account": {
    "id": 12345,
    "title": "username",
    "thumb": "https://..."
  },
  "Server": {
    "title": "MyPlexServer",
    "uuid": "abc123..."
  },
  "Player": {
    "title": "My TV",
    "uuid": "player-uuid",
    "publicAddress": "1.2.3.4",
    "local": true
  },
  "Metadata": {
    "type": "movie",
    "title": "The Matrix",
    "year": 2026,
    "ratingKey": "12345",
    "key": "/library/metadata/12345",
    "thumb": "/library/metadata/12345/thumb/...",
    "grandparentTitle": null,
    "originallyAvailableAt": "1999-03-31",
    "Guid": [
      {"id": "imdb://tt0133093"},
      {"id": "tmdb://603"}
    ]
  }
}
```

**FastAPI receiver pattern:**

```python
from fastapi import APIRouter, Form, Request
import json

router = APIRouter()

@router.post("/webhook/plex")
async def plex_webhook(payload: str = Form(...)):
    data = json.loads(payload)
    event = data.get("event")

    if event == "media.scrobble":
        metadata = data.get("Metadata", {})
        if metadata.get("type") == "movie":
            # Extract TMDB ID from Guid list
            tmdb_id = None
            for guid in metadata.get("Guid", []):
                if guid["id"].startswith("tmdb://"):
                    tmdb_id = int(guid["id"].replace("tmdb://", ""))
            await handle_movie_watched(tmdb_id, metadata)
```

**Key notes:**
- `python-multipart` must be installed for FastAPI Form() to work
- Filter by `Metadata.type == "movie"` to skip TV episodes
- TMDB ID is embedded in `Metadata.Guid[]` array (modern Plex versions)
- `media.scrobble` (90% threshold) is the correct event for "watched" — not `media.stop`

---

### Pattern 3: Game Session State

The actor-chain game tracks: current session, which actors have been used, which movies are eligible for each actor, and the current "starting movie" (last watched).

**State machine:**
```
[Plex scrobble: movie X watched]
        │
        ▼
[Fetch credits for movie X from cache]
        │
        ▼
[Create new GameSession with starting_movie_id=X]
        │
        ▼
[Frontend polls: GET /api/game/session/{id}/actors]
        │   (returns cast of current movie, filtered by unused)
        ▼
[User selects actor A]
        │
        ▼
[Mark actor A as used, fetch actor A's filmography]
        │
        ▼
[Frontend: GET /api/game/session/{id}/movies?actor_id=A]
        │   (returns movies of actor A not yet seen in session)
        ▼
[User selects movie M → POST to Radarr]
        │
        ▼
[Update session: current_movie_id = M, add A to used_actors]
        │
        ▼
[Loop from "Fetch credits for movie M"]
```

**PostgreSQL schema:**

```sql
-- Game sessions
CREATE TABLE game_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at    TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'active',  -- active | ended
    starting_movie_tmdb_id  INTEGER REFERENCES movies(tmdb_id),
    current_movie_tmdb_id   INTEGER REFERENCES movies(tmdb_id)
);

-- Actors used in a session (prevents re-use)
CREATE TABLE session_used_actors (
    session_id  UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    person_id   INTEGER NOT NULL,  -- TMDB person_id
    used_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, person_id)
);

-- Movies seen/played in a session chain
CREATE TABLE session_movie_chain (
    session_id    UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    tmdb_id       INTEGER NOT NULL,
    position      INTEGER NOT NULL,  -- order in chain
    actor_link_id INTEGER,           -- actor who connected to this movie
    added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, tmdb_id)
);
```

**Eligibility query** (movies an actor can lead to, excluding already-used in session):

```sql
SELECT mc.movie_tmdb_id
FROM movie_cast mc
WHERE mc.person_id = :actor_id
  AND mc.movie_tmdb_id NOT IN (
      SELECT tmdb_id FROM session_movie_chain WHERE session_id = :session_id
  );
```

---

### Pattern 4: Radarr/Sonarr Request Flow

**Radarr movie request flow:**

```
1. GET /api/v3/qualityprofile  → pick profile ID
2. GET /api/v3/rootfolder      → pick root folder path
3. GET /api/v3/movie/lookup?term=tmdb:{tmdb_id}  → confirm movie exists
4. POST /api/v3/movie          → add + search
```

**POST /api/v3/movie request body:**

```json
{
  "title": "The Matrix",
  "tmdbId": 603,
  "year": 1999,
  "qualityProfileId": 1,
  "rootFolderPath": "/volume1/data/media/movies",
  "monitored": true,
  "addOptions": {
    "searchForMovie": true
  },
  "minimumAvailability": "announced"
}
```

**Python pattern using httpx:**

```python
class RadarrService:
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Api-Key": api_key}
        )

    async def request_movie(self, tmdb_id: int, title: str, year: int) -> dict:
        # Get first quality profile and root folder
        profiles = await self.client.get("/api/v3/qualityprofile")
        folders = await self.client.get("/api/v3/rootfolder")

        payload = {
            "tmdbId": tmdb_id,
            "title": title,
            "year": year,
            "qualityProfileId": profiles.json()[0]["id"],
            "rootFolderPath": folders.json()[0]["path"],
            "monitored": True,
            "addOptions": {"searchForMovie": True},
            "minimumAvailability": "announced",
        }
        resp = await self.client.post("/api/v3/movie", json=payload)
        resp.raise_for_status()
        return resp.json()
```

**Sonarr equivalent** uses `/api/v3/series` with `tvdbId` instead of `tmdbId`, and requires `seasonFolder: true` and a `seasons` array.

**Duplicate handling:** Radarr returns HTTP 400 if movie already exists. Catch this and return the existing record instead of raising.

---

## Data Flow

### Movie Game Flow

```
1. Plex fires media.scrobble for movie X
         │
         ▼
2. POST /webhook/plex
   - Parse multipart payload
   - Extract TMDB ID from Metadata.Guid[]
   - Write to watch_history table
   - Create new game_session (starting_movie = X)
   - Emit SSE or store "session_ready" flag
         │
         ▼
3. Frontend polls GET /api/game/active-session
   - Returns session_id + current movie details
         │
         ▼
4. GET /api/game/session/{id}/actors
   - Query movie_cast WHERE movie_tmdb_id = current_movie
   - Filter out person_ids in session_used_actors
   - Fetch actor details from persons cache
   - Return: [{person_id, name, profile_path, character}]
         │
         ▼
5. User picks actor A
   POST /api/game/session/{id}/select-actor  {actor_id: A}
   - INSERT into session_used_actors
   - Return actor's eligible movies (from person_movie_credits cache)
         │
         ▼
6. GET /api/game/session/{id}/movies?actor_id=A
   - Query person_movie_credits WHERE person_id = A
   - Exclude movies in session_movie_chain
   - Return: [{tmdb_id, title, year, poster_path}]
         │
         ▼
7. User picks movie M
   POST /api/game/session/{id}/select-movie  {tmdb_id: M}
   - POST to Radarr /api/v3/movie (request download)
   - INSERT into session_movie_chain (position++)
   - UPDATE game_sessions SET current_movie_tmdb_id = M
   - Pre-fetch M's credits if not cached
         │
         ▼
8. Return to step 4 with new current movie = M
```

### Query Mode Flow

```
1. User types search query
   GET /api/query/search?q=matrix
         │
         ▼
2. Backend calls TMDB GET /3/search/movie?query=matrix
   (not cached — search results are volatile)
         │
         ▼
3. User selects result → GET /api/query/movie/{tmdb_id}
   - Check filmography_cache for full movie record
   - If miss or stale: fetch GET /3/movie/{id}?append_to_response=credits
   - Upsert to cache
   - Return enriched movie details
         │
         ▼
4. Frontend displays movie card with cast
         │
         ▼
5. User clicks "Request"
   POST /api/query/request  {tmdb_id, media_type}
   - media_type=movie → RadarrService.request_movie()
   - media_type=tv    → SonarrService.request_series()
   - Return {status: "requested", radarr_id: ...}
```

### Plex Webhook Flow

```
Plex Server
    │
    │  POST http://cinemachain-backend:8000/webhook/plex
    │  Content-Type: multipart/form-data
    │  Body: payload=<JSON string>
    ▼
FastAPI @router.post("/webhook/plex")
    │
    ├── Parse Form(payload) → json.loads()
    ├── Check event type:
    │     media.scrobble  → process
    │     media.play      → ignore (or log)
    │     other           → ignore
    │
    ├── Filter: Metadata.type == "movie"
    │
    ├── Extract tmdb_id from Metadata.Guid[]
    │     guid["id"].startswith("tmdb://")
    │
    ├── INSERT watch_history (tmdb_id, title, viewed_at, plex_rating_key)
    │
    ├── Create/update game_session
    │
    └── Return HTTP 200 OK (Plex ignores response body)
```

---

## Key Database Schema Patterns

```sql
-- ─────────────────────────────────────────
-- FILMOGRAPHY CACHE
-- ─────────────────────────────────────────

CREATE TABLE movies (
    tmdb_id         INTEGER PRIMARY KEY,
    imdb_id         TEXT,
    title           TEXT NOT NULL,
    year            INTEGER,
    overview        TEXT,
    poster_path     TEXT,
    backdrop_path   TEXT,
    runtime_min     INTEGER,
    genres          JSONB,              -- [{id, name}]
    raw_tmdb_data   JSONB,              -- full API response for future fields
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    credits_fetched_at TIMESTAMPTZ      -- NULL = credits not yet fetched
);

CREATE TABLE persons (
    tmdb_id         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    profile_path    TEXT,
    biography       TEXT,
    filmography_fetched_at TIMESTAMPTZ, -- NULL = filmography not fetched
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE movie_cast (
    movie_tmdb_id   INTEGER NOT NULL REFERENCES movies(tmdb_id),
    person_id       INTEGER NOT NULL REFERENCES persons(tmdb_id),
    character_name  TEXT,
    cast_order      INTEGER,            -- lower = more prominent role
    PRIMARY KEY (movie_tmdb_id, person_id)
);

CREATE INDEX idx_movie_cast_person ON movie_cast(person_id);
CREATE INDEX idx_movie_cast_movie  ON movie_cast(movie_tmdb_id);

-- ─────────────────────────────────────────
-- WATCH HISTORY
-- ─────────────────────────────────────────

CREATE TABLE watch_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tmdb_id         INTEGER REFERENCES movies(tmdb_id),
    title           TEXT NOT NULL,      -- denormalized for safety
    plex_rating_key TEXT,               -- Plex's internal media ID
    viewed_at       TIMESTAMPTZ NOT NULL,
    source          TEXT DEFAULT 'plex_webhook',
    raw_payload     JSONB               -- store raw Plex metadata for debug
);

CREATE INDEX idx_watch_history_viewed ON watch_history(viewed_at DESC);

-- ─────────────────────────────────────────
-- GAME SESSION STATE
-- ─────────────────────────────────────────

CREATE TABLE game_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at                TIMESTAMPTZ,
    status                  TEXT NOT NULL DEFAULT 'active',
    trigger_watch_id        UUID REFERENCES watch_history(id),
    starting_movie_tmdb_id  INTEGER REFERENCES movies(tmdb_id),
    current_movie_tmdb_id   INTEGER REFERENCES movies(tmdb_id),
    chain_length            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE session_used_actors (
    session_id  UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    person_id   INTEGER NOT NULL,
    used_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, person_id)
);

CREATE TABLE session_movie_chain (
    session_id    UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    tmdb_id       INTEGER NOT NULL REFERENCES movies(tmdb_id),
    position      INTEGER NOT NULL,
    actor_link_id INTEGER,             -- person_id that bridged to this movie
    requested_at  TIMESTAMPTZ,         -- NULL = not yet requested via Radarr
    radarr_id     INTEGER,             -- Radarr's internal movie ID after request
    PRIMARY KEY (session_id, tmdb_id)
);
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Key Endpoints | Notes |
|---------|---------------------|---------------|-------|
| TMDB API | Async httpx client, cache-first | `GET /3/movie/{id}`, `GET /3/movie/{id}/credits`, `GET /3/person/{id}/movie_credits`, `GET /3/search/movie` | ~50 req/s limit; Bearer token auth; cache filmography 3-14 days; attribution required |
| Plex Webhooks | FastAPI POST endpoint, multipart/form-data | `POST /webhook/plex` (inbound) | Requires Plex Pass; payload field is JSON string in form data; filter on `media.scrobble` + `type==movie` |
| Plex HTTP API (optional) | python-plexapi or direct GET | `GET /status/sessions/history/all?X-Plex-Token=` | Returns XML; use for initial history backfill if needed |
| Radarr API | Async httpx client | `GET /api/v3/qualityprofile`, `GET /api/v3/rootfolder`, `GET /api/v3/movie/lookup?term=tmdb:{id}`, `POST /api/v3/movie` | `X-Api-Key` header auth; 400 on duplicate (handle gracefully) |
| Sonarr API | Async httpx client | `GET /api/v3/qualityprofile`, `GET /api/v3/rootfolder`, `GET /api/v3/series/lookup?term=tvdb:{id}`, `POST /api/v3/series` | Same pattern as Radarr; uses `tvdbId` not `tmdbId` |

### Docker Compose (Synology NAS)

```yaml
# docker-compose.yml
version: "3.9"

networks:
  cinemachain:
    driver: bridge

services:
  backend:
    build: ./backend
    container_name: cinemachain-backend
    restart: unless-stopped
    networks: [cinemachain]
    ports:
      - "8000:8000"
    volumes:
      - /volume1/docker/appdata/cinemachain/backend:/app/data
    environment:
      - PUID=1000          # run: id your_docker_user
      - PGID=1000
      - DATABASE_URL=postgresql+asyncpg://cinema:${DB_PASSWORD}@postgres:5432/cinemachain
      - TMDB_API_KEY=${TMDB_API_KEY}
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=${RADARR_API_KEY}
      - SONARR_URL=http://sonarr:8989
      - SONARR_API_KEY=${SONARR_API_KEY}
    command: >
      bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build: ./frontend
    container_name: cinemachain-frontend
    restart: unless-stopped
    networks: [cinemachain]
    ports:
      - "3000:80"
    depends_on: [backend]

  postgres:
    image: postgres:16-alpine
    container_name: cinemachain-postgres
    restart: unless-stopped
    networks: [cinemachain]
    volumes:
      - /volume1/docker/appdata/cinemachain/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=cinema
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=cinemachain
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cinema -d cinemachain"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Synology-specific notes:**
- Use `/volume1/docker/appdata/cinemachain/` for all app config/data (not Docker named volumes)
- Use `/volume1/data/media/` as the shared root for Radarr/Sonarr/Plex (enables hardlinking)
- Get PUID/PGID via SSH: `id your_docker_username`
- Radarr and Sonarr are reachable by service name within the shared network (e.g., `http://radarr:7878`) only if they are in the same Docker Compose stack or connected network
- If Radarr/Sonarr run in a separate stack, use host IP or `host.docker.internal` instead

### FastAPI + SQLAlchemy Async Setup

```python
# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncGenerator

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://...
    echo=False,
    pool_size=5,            # appropriate for single-user NAS
    max_overflow=2,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Open Source Reference Projects

These projects demonstrate patterns directly applicable to CinemaChain:

- **Overseerr / Seerr** (seerr-team/seerr): Full media request manager for Plex/Jellyfin. Node.js + TypeScript + PostgreSQL/SQLite. Three-tier service architecture with dedicated client classes per external API, per-endpoint TTL caching (12h for movie details), TypeORM repository pattern. Best reference for Radarr/Sonarr integration flow and TMDB transformation pipeline.

- **python-plexapi** (pkkid/python-plexapi): Official Python bindings for Plex. Use for initial library scan / watch history backfill. Key methods: `library.search(unwatched=False)`, `history(maxresults=50, mindate=...)`, `recentlyAddedMovies()`.

- **ArrAPI** (Kometa-Team/ArrAPI): Lightweight Python wrapper for Radarr + Sonarr. `RadarrAPI(baseurl, apikey).add_movie(root_folder, quality_profile, tmdb_id=603, search=True)` — simplest integration path.

- **plex-suggester** (TheInfamousToTo/plex-suggester): FastAPI + Plex integration with actor/cast display. Shows lazy-loading actor images from TMDB profile_path.

---

## Sources

- [Plex Webhooks Official Documentation](https://support.plex.tv/articles/115002267687-webhooks/) — HIGH confidence, official source
- [Plex Pro Week '25: Webhooks 101](https://www.plex.tv/blog/plex-pro-week-25-webhooks-101/) — HIGH confidence
- [Building a scrobbler using Plex webhooks](https://www.coryd.dev/posts/2024/building-a-scrobbler-using-plex-webhooks-edge-functions-and-blob-storage) — HIGH confidence, shows exact payload parsing
- [TMDB API Getting Started](https://developer.themoviedb.org/reference/intro/getting-started) — HIGH confidence, official
- [TMDB Movie Credits Reference](https://developer.themoviedb.org/reference/movie-credits) — HIGH confidence, official
- [TMDB FAQ / Caching Policy](https://developer.themoviedb.org/docs/faq) — HIGH confidence, official
- [Radarr OpenAPI Spec](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/Radarr.Api.V3/openapi.json) — HIGH confidence, source of truth
- [ArrAPI Radarr Documentation](https://arrapi.kometa.wiki/en/latest/radarr.html) — HIGH confidence
- [Overseerr/Seerr Architecture (DeepWiki)](https://deepwiki.com/sct/overseerr/5-api-and-integration) — MEDIUM confidence, AI-generated wiki but well-sourced
- [Seerr GitHub](https://github.com/seerr-team/seerr) — HIGH confidence, official repo
- [FastAPI + Async SQLAlchemy + Docker Setup Guide](https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/) — HIGH confidence
- [TRaSH Guides: Synology Setup](https://trash-guides.info/File-and-Folder-Structure/How-to-set-up/Synology/) — HIGH confidence, widely referenced in the arr-stack community
- [Plex Session History API (Plexopedia)](https://www.plexopedia.com/plex-media-server/api/server/session-history/) — MEDIUM confidence, community-documented
- [python-plexapi Documentation](https://python-plexapi.readthedocs.io/en/latest/modules/library.html) — HIGH confidence, official library docs
- [TMDB Caching Community Discussion](https://www.themoviedb.org/talk/5bd3a0fd0e0a2622da00b695) — MEDIUM confidence, community forum
