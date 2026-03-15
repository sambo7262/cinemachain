# Phase 1: Infrastructure - Research

**Researched:** 2026-03-14
**Domain:** Docker Compose on Synology NAS — PostgreSQL, FastAPI skeleton, Tailscale sidecar
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | App runs as Docker Compose stack (backend + PostgreSQL + frontend containers) | Docker Compose v2 multi-service patterns; Synology Container Manager confirms Compose v2 native support; healthcheck-gated startup pattern documented |
| INFRA-02 | All API keys and config managed via .env (TMDB, Plex, Radarr, Sonarr) | python-dotenv + .env pattern; Compose `env_file` / variable substitution; security patterns for secrets-not-in-images |
| INFRA-03 | PostgreSQL data persists via Docker volumes across restarts | Bind-mount pattern to `/volume1/docker/appdata/cinemachain/postgres`; PUID/PGID alignment for PostgreSQL UID 999; healthcheck gating |
| INFRA-04 | App is accessible via Tailscale IP/hostname on the home network | Tailscale sidecar with `TS_USERSPACE=true`; `network_mode: service:tailscale` pattern; Tailscale Serve config for HTTPS endpoint |
</phase_requirements>

---

## Summary

Phase 1 delivers the foundation that every subsequent phase builds on: a Docker Compose stack running on the Synology NAS with PostgreSQL persisting to a bind-mounted volume, a FastAPI backend skeleton, a frontend placeholder container, and a Tailscale sidecar providing remote access. No application logic ships in this phase — only the plumbing.

The Synology NAS environment introduces three non-obvious constraints that must be addressed in Compose configuration before any container can function correctly: (1) PUID/PGID must match the NAS user running Docker — DSM uses POSIX ACLs that Docker ignores; (2) PostgreSQL must not bind to host port 5432, which is internally reserved on Synology — use 5433; and (3) the Tailscale sidecar requires `TS_USERSPACE=true` because the kernel TUN device is unavailable in DSM containers without it, causing the tunnel to silently never form.

Memory limits are mandatory, not optional. A NAS without container memory limits risks OOM kills that can crash the entire stack and leave PostgreSQL in an inconsistent state. `restart: unless-stopped` (not `always`) prevents infinite restart loops from masking real errors.

**Primary recommendation:** Write `compose.yaml` addressing all Synology constraints upfront — PUID/PGID, port 5433, `TS_USERSPACE=true`, `mem_limit` on every service, health-check-gated startup — then verify the stack cold-boots cleanly before Phase 2 begins.

---

## Standard Stack

### Core

| Library / Image | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| python:3.12-slim | 3.12 | Backend base image | ~130MB vs ~1GB full image; LTS; PlexAPI requires >= 3.10 |
| FastAPI | 0.115.x | HTTP server + future webhook receiver | Async-native ASGI; handles multipart POST for Plex webhooks; 38% Python dev adoption 2025 |
| Uvicorn | 0.30.x | ASGI server | Standard pairing with FastAPI; minimal memory footprint |
| PostgreSQL | 16-alpine | Persistent data store | Game session join queries require richer query support than SQLite; alpine image reduces size |
| tailscale/tailscale | latest | Remote access sidecar | Zero-trust peer-to-peer; avoids Synology QuickConnect routing through Synology servers |
| python-dotenv | 1.0.x | Load .env into environment | Keeps secrets out of images and Compose files |
| SQLAlchemy (async) | 2.x | ORM + DB session management | asyncpg driver; async session factory; supports Alembic migrations |
| asyncpg | 0.29.x | PostgreSQL async driver | Required for SQLAlchemy async with PostgreSQL |
| Alembic | 1.13.x | Database migrations | Schema version control; run `alembic upgrade head` on startup |
| pydantic-settings | 2.x | Typed settings from environment | Validates all env vars at startup; catches missing keys before runtime failures |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.x | Multipart form parser for FastAPI | Required now so Plex webhook endpoint is wire-ready in Phase 2 |
| httpx | 0.27.x | Async HTTP client | Needed for health-check probes and future service integrations |
| pytest + pytest-asyncio | latest | Test async FastAPI routes | Phase 1 skeleton testing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| postgres:16-alpine | postgres:16 | Full image is ~300MB larger with no benefit for this use case |
| Tailscale sidecar | Synology QuickConnect | QuickConnect routes traffic through Synology servers; Tailscale is peer-to-peer and operator-controlled |
| Tailscale sidecar | VPN (WireGuard direct) | Requires manual key management and firewall rules; Tailscale handles this automatically |
| Alembic | Inline CREATE TABLE | Alembic provides upgrade/downgrade history; essential before data exists |
| python:3.12-slim | python:3.12-alpine | Alpine uses musl libc; some compiled Python packages (notably asyncpg) require glibc; slim is safer |

**Installation (backend Dockerfile):**
```bash
pip install fastapi==0.115.6 uvicorn[standard]==0.30.6 sqlalchemy[asyncio]==2.0.x asyncpg==0.29.x alembic==1.13.x pydantic-settings==2.x python-dotenv==1.0.1 python-multipart httpx==0.27.2
```

---

## Architecture Patterns

### Recommended Project Structure

```
cinemachain/
├── compose.yaml                     # Compose v2 preferred filename
├── .env                             # Secrets (gitignored)
├── .env.example                     # Template with placeholder values (committed)
├── .gitignore                       # Must include .env, volumes/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                   # Async Alembic env for asyncpg
│   │   └── versions/                # Migration files
│   └── app/
│       ├── main.py                  # FastAPI app init, router mounting, lifespan
│       ├── db.py                    # Async engine, session factory
│       ├── settings.py              # pydantic-settings config (reads from .env)
│       ├── models/                  # SQLAlchemy ORM models (empty in Phase 1)
│       ├── routers/
│       │   └── health.py            # GET /health → {"status": "ok", "db": "ok"}
│       └── dependencies.py          # DB session dependency injection
├── frontend/
│   ├── Dockerfile                   # Nginx serving static placeholder
│   └── index.html                   # "CinemaChain — coming soon" placeholder
└── volumes/
    ├── postgres/                    # gitignored; bind-mounted DB data
    └── tailscale/                   # gitignored; Tailscale state persistence
```

### Pattern 1: Synology-Safe Docker Compose

**What:** A complete `compose.yaml` that addresses all known Synology constraints upfront.

**When to use:** Always — every service in the stack must include these settings.

```yaml
# compose.yaml
# Source: STATE.md + PITFALLS.md (project research)
#
# SYNOLOGY CONSTRAINTS ADDRESSED:
#   - PUID/PGID set on all services (DSM ACLs ≠ Unix perms)
#   - PostgreSQL host port 5433 (not 5432 — reserved on Synology)
#   - TS_USERSPACE=true on Tailscale sidecar (no kernel TUN in DSM)
#   - mem_limit on every container (prevent OOM kills)
#   - restart: unless-stopped (not always — avoids masking real errors)
#   - healthcheck-gated depends_on for PostgreSQL

services:
  tailscale:
    image: tailscale/tailscale:latest
    container_name: cinemachain-tailscale
    hostname: cinemachain
    restart: unless-stopped
    mem_limit: 128m
    environment:
      - TS_AUTHKEY=${TS_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=true        # MANDATORY on Synology DSM — no kernel TUN
      - TS_SERVE_CONFIG=/config/ts-serve.json
    volumes:
      - /volume1/docker/appdata/cinemachain/tailscale:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
      - NET_RAW

  backend:
    build: ./backend
    container_name: cinemachain-backend
    restart: unless-stopped
    mem_limit: 512m
    network_mode: service:tailscale    # Share Tailscale's network namespace
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - DATABASE_URL=postgresql+asyncpg://cinema:${DB_PASSWORD}@postgres:5432/cinemachain
      - TMDB_API_KEY=${TMDB_API_KEY}
      - PLEX_TOKEN=${PLEX_TOKEN}
      - PLEX_URL=${PLEX_URL}
      - RADARR_URL=${RADARR_URL}
      - RADARR_API_KEY=${RADARR_API_KEY}
      - SONARR_URL=${SONARR_URL}
      - SONARR_API_KEY=${SONARR_API_KEY}
    volumes:
      - /volume1/docker/appdata/cinemachain/backend:/app/data
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

  frontend:
    build: ./frontend
    container_name: cinemachain-frontend
    restart: unless-stopped
    mem_limit: 64m
    ports:
      - "3000:80"
    depends_on:
      - backend

  postgres:
    image: postgres:16-alpine
    container_name: cinemachain-postgres
    restart: unless-stopped
    mem_limit: 256m
    ports:
      - "127.0.0.1:5433:5432"    # 5432 reserved on Synology; bind to loopback only
    environment:
      - POSTGRES_USER=cinema
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=cinemachain
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - /volume1/docker/appdata/cinemachain/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cinema -d cinemachain"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

### Pattern 2: FastAPI App Skeleton with Lifespan

**What:** Minimal FastAPI app with health endpoint, DB connection verification, and proper async lifespan.

**When to use:** Phase 1 backend — wire this up before any application logic.

```python
# app/main.py
# Source: FastAPI official docs + project architecture research
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import engine
from app.routers import health

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # Shutdown: dispose engine
    await engine.dispose()

app = FastAPI(title="CinemaChain", lifespan=lifespan)
app.include_router(health.router)
```

```python
# app/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncGenerator
from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=5,          # Appropriate for single-user NAS
    max_overflow=2,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

```python
# app/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    tmdb_api_key: str
    plex_token: str
    plex_url: str
    radarr_url: str
    radarr_api_key: str
    sonarr_url: str
    sonarr_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### Pattern 3: Tailscale Sidecar Network Sharing

**What:** The backend container uses `network_mode: service:tailscale`, meaning it shares the Tailscale container's network namespace. The backend listens on the Tailscale IP, not a direct host port.

**When to use:** Always — this is the mandatory pattern for Synology DSM where Tailscale cannot use kernel TUN.

**Key details:**
- Frontend uses host ports directly (port 3000 on host NIC) — it does NOT join the Tailscale network namespace because it needs to be accessible from the LAN as well as Tailscale.
- Backend is reachable at `https://cinemachain.<tailnet>.ts.net` via Tailscale Serve after configuring `ts-serve.json`.
- Tailscale state must be persisted to a volume (`/var/lib/tailscale`) or the node re-authenticates on every restart.

**Tailscale Serve config (ts-serve.json):**
```json
{
  "TCP": {
    "443": {
      "HTTPS": true
    }
  },
  "Web": {
    "cinemachain.tailnet-name.ts.net:443": {
      "Handlers": {
        "/": {
          "Proxy": "http://127.0.0.1:8000"
        }
      }
    }
  }
}
```

### Pattern 4: PostgreSQL Volume Ownership

**What:** The official `postgres:16-alpine` image runs as UID 999 (the `postgres` user inside the container). The NAS bind-mount directory must be owned by UID 999 or PostgreSQL fails to start with `wrong ownership`.

**When to use:** Before first `docker compose up`.

```bash
# Run on NAS via SSH before first start:
mkdir -p /volume1/docker/appdata/cinemachain/postgres
chown -R 999:999 /volume1/docker/appdata/cinemachain/postgres

# Verify backend data dir is accessible:
mkdir -p /volume1/docker/appdata/cinemachain/backend
chown -R ${PUID}:${PGID} /volume1/docker/appdata/cinemachain/backend
```

### Pattern 5: Health Endpoint

**What:** A `/health` endpoint that verifies the database connection — used by monitoring tools and as a phase success gate.

```python
# app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db

router = APIRouter()

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
```

### Anti-Patterns to Avoid

- **Port 5432 on host:** Synology internally reserves this port. The Compose file must use `5433:5432` on the host side. Using 5432 causes a silent bind failure.
- **`restart: always`:** Causes infinite restart loops when there's a real error (wrong DB password, missing env var). Use `restart: unless-stopped`.
- **No `mem_limit`:** A single OOM-killed container on a NAS can crash the whole stack. Set limits before the first deploy.
- **Docker named volumes for PostgreSQL data:** On Synology, prefer host bind-mounts to `/volume1/docker/appdata/...` so data is visible in DSM File Station and survives Docker package reinstalls.
- **`TS_USERSPACE` omitted:** The Tailscale tunnel silently never forms. The container starts, reports healthy, but `tailscale status` shows no devices. There is no error — it just doesn't work.
- **Boolean `true`/`false` in DSM Compose editor:** DSM's Container Manager UI requires `1`/`0` for boolean env vars. Use numeric booleans in all env references that may pass through the DSM UI.
- **`.env` committed to git:** TMDB and Radarr API keys in repo history. Verify `.gitignore` includes `.env` before the first commit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database migrations | Manual `CREATE TABLE` scripts | Alembic | Schema version tracking; safe `upgrade head` on container start; supports rollback |
| Settings validation | Manual `os.getenv()` with conditionals | pydantic-settings `BaseSettings` | Type validation, missing-key errors at startup, not at runtime |
| PostgreSQL health gating | `sleep 10` in entrypoint | Compose `depends_on: condition: service_healthy` with `pg_isready` healthcheck | `sleep` is racey; healthcheck is deterministic |
| Async DB sessions | Manual connection management | SQLAlchemy async session factory with `async_sessionmaker` | Proper connection pooling, context management, no leaked connections |
| Secrets management | Env vars baked into Dockerfile | `.env` file + `env_file` or variable substitution in Compose | Secrets never enter image layers or image history |

**Key insight:** The NAS environment makes "just hard-code it for now" choices very costly — a misconfigured Compose file means a wasted debugging session over SSH. Get the patterns right in the first commit.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL Fails to Start — Wrong Volume Ownership
**What goes wrong:** PostgreSQL logs `FATAL: data directory "/var/lib/postgresql/data" has wrong ownership`. Container exits immediately.
**Why it happens:** The official `postgres:16-alpine` image runs as UID 999 inside the container. The bind-mounted host directory is owned by a different UID (often root or the NAS admin user).
**How to avoid:** Run `chown -R 999:999 /volume1/docker/appdata/cinemachain/postgres` on the NAS via SSH before the first `docker compose up`. Never mount the directory as root.
**Warning signs:** Container exits on first start with no output after "database system is shut down" or the FATAL ownership message.

### Pitfall 2: Tailscale Sidecar Forms No Tunnel (Missing TS_USERSPACE)
**What goes wrong:** The Tailscale container starts and reports healthy, but `tailscale status` shows the node as offline. The backend is never reachable over Tailscale. No error is logged.
**Why it happens:** Synology DSM does not expose the kernel TUN device to Docker containers. Without `TS_USERSPACE=true`, Tailscale attempts to use kernel TUN, silently fails, and reports as if running.
**How to avoid:** Always set `TS_USERSPACE=true` in the Tailscale service environment. Verify after startup: `docker exec cinemachain-tailscale tailscale status` should show the node online.
**Warning signs:** Container is up but Tailscale dashboard shows device as offline or disconnected.

### Pitfall 3: Port 5432 Already Bound on Synology
**What goes wrong:** `docker compose up` fails with `bind: address already in use` for port 5432, or PostgreSQL starts but is unreachable.
**Why it happens:** Synology DSM internally reserves port 5432. Any attempt to bind a host port 5432 fails.
**How to avoid:** Always use `127.0.0.1:5433:5432` in Compose. Never use 5432 as the host port on Synology.
**Warning signs:** Compose reports port conflict at startup; `ss -tlnp | grep 5432` on the NAS shows DSM already owns it.

### Pitfall 4: Backend Starts Before PostgreSQL Is Ready
**What goes wrong:** Backend container starts, Alembic attempts `upgrade head`, PostgreSQL connection fails because the DB is still initializing. Alembic exits with error; backend restarts; eventual consistency may or may not work out.
**Why it happens:** `depends_on: [postgres]` only waits for the container to start, not for PostgreSQL to be accepting connections. First-boot PostgreSQL initialization takes 5–20 seconds.
**How to avoid:** Use `depends_on: postgres: condition: service_healthy` combined with a proper `healthcheck` using `pg_isready`. Set `start_period: 30s` on the PostgreSQL healthcheck to allow initialization time.
**Warning signs:** Alembic errors in backend logs immediately after first start; backend eventually comes up after several restarts.

### Pitfall 5: OOM Kill Destabilizes the Stack
**What goes wrong:** Under any burst load (even a NAS background task), a container without memory limits consumes all available RAM. The kernel OOM killer terminates a container — often PostgreSQL. The database may be in an inconsistent state on recovery.
**Why it happens:** Docker on Synology NAS does not set memory limits by default. NAS RAM is shared with DSM and other running packages.
**How to avoid:** Set `mem_limit` on every container in `compose.yaml`: 512m for backend, 256m for PostgreSQL, 128m for Tailscale, 64m for frontend placeholder.
**Warning signs:** Container restart with no log output; `docker events` shows OOM kill events.

### Pitfall 6: Secrets in Docker Image Layers
**What goes wrong:** API keys are passed as `ARG` or `ENV` in the Dockerfile and baked into image layers, which are inspectable even on a "private" image.
**Why it happens:** Convenience during development. Common mistake with `COPY .env .` inside the Dockerfile.
**How to avoid:** Never `COPY .env` in Dockerfile. Pass all secrets via `environment:` in Compose, sourced from `.env` via variable substitution. Verify: `docker inspect cinemachain-backend | grep API_KEY` should show the key value (from runtime env), but `docker history cinemachain-backend` should not.
**Warning signs:** `.env` file appears in `docker image inspect` layer data.

---

## Code Examples

Verified patterns from project research:

### Backend Dockerfile (Phase 1 Skeleton)
```dockerfile
# Source: project STACK.md research (python:3.12-slim standard pattern)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Do NOT COPY .env — secrets come from Compose environment
EXPOSE 8000

CMD ["bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### Frontend Placeholder Dockerfile
```dockerfile
# Source: Phase 1 goal — minimal nginx serving a placeholder
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
```

### .env.example (Committed to Repo)
```bash
# Source: INFRA-02 requirement — all secrets from .env
# Copy to .env and fill in values. Never commit .env.

# Database
DB_PASSWORD=changeme

# Synology NAS user IDs — get via SSH: id your_docker_user
PUID=1000
PGID=1000

# Tailscale
TS_AUTHKEY=tskey-auth-xxxxx

# TMDB
TMDB_API_KEY=

# Plex
PLEX_TOKEN=
PLEX_URL=http://192.168.x.x:32400

# Radarr
RADARR_URL=http://192.168.x.x:7878
RADARR_API_KEY=

# Sonarr
SONARR_URL=http://192.168.x.x:8989
SONARR_API_KEY=
```

### Alembic Async Configuration
```python
# alembic/env.py (async pattern for asyncpg)
# Source: FastAPI + Async SQLAlchemy setup guide (project architecture research)
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.settings import settings
from app.models import Base  # Import all models so Alembic sees them

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_async_engine(settings.database_url)

    async def run_async():
        async with connectable.connect() as conn:
            await conn.run_sync(context.run_migrations)
        await connectable.dispose()

    asyncio.run(run_async())

run_migrations_online()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose.yml` filename | `compose.yaml` (preferred) | Docker Compose v2 (2022) | Container Manager UI shows warning with old filename; use new one |
| `depends_on: [service]` | `depends_on: condition: service_healthy` | Compose v2 | Old form does not wait for readiness; new form uses healthcheck |
| `deploy.resources.limits.memory` | `mem_limit` (top-level shorthand) | Compose v2 | Both work; `mem_limit` is simpler for single-stack deployments |
| SQLite for simplicity | PostgreSQL 16 | Decided 2026-03-14 | Game session join queries require PostgreSQL; SQLite overridden |
| Named Docker volumes | Host bind-mounts to `/volume1/...` | Synology best practice | Bind-mounts are visible in DSM File Station; survive Docker package reinstalls |

**Deprecated/outdated:**
- `version: "3.9"` top-level key in `compose.yaml`: Obsolete in Compose v2; omit it. Container Manager on DSM 7.2+ uses Compose v2 which ignores or warns on the version key.

---

## Open Questions

1. **PUID/PGID values**
   - What we know: Must match the NAS user running Docker containers
   - What's unclear: The actual numeric UID/GID on this specific Synology NAS
   - Recommendation: Run `id your_docker_username` via SSH on the NAS during task execution and set in `.env`. Document this as a setup prerequisite.

2. **Tailscale auth key type (one-time vs reusable)**
   - What we know: `TS_AUTHKEY` accepts both one-time auth keys and reusable/pre-authorized keys
   - What's unclear: Whether the operator has an existing Tailscale account and which key type to use
   - Recommendation: Use a reusable, pre-authorized key tagged `tag:server` to avoid re-authentication after container recreation. Document this in the setup task.

3. **Tailscale Serve domain name**
   - What we know: The serve config references `cinemachain.<tailnet>.ts.net`
   - What's unclear: The actual tailnet name
   - Recommendation: The `ts-serve.json` should use the actual tailnet hostname. The task can instruct the operator to run `tailscale status` to get the domain and substitute it.

4. **Frontend technology for later phases**
   - What we know: Phase 1 delivers a placeholder only (static HTML)
   - What's unclear: Whether Vue or React will be used when the frontend is built in Phase 3
   - Recommendation: The Phase 1 frontend Dockerfile uses plain nginx + HTML. The build system choice (Vite + Vue vs Create React App) is deferred to Phase 3, consistent with "resource-conscious for NAS" constraint. No Node runtime in Phase 1.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (to be installed) |
| Config file | `backend/pytest.ini` — Wave 0 gap |
| Quick run command | `docker compose exec backend pytest tests/ -x -q` |
| Full suite command | `docker compose exec backend pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `docker compose up -d` brings all containers healthy | smoke | `docker compose ps --format json \| jq '.[].Status'` — all show `healthy` or `running` | ❌ Wave 0 |
| INFRA-01 | `GET /health` returns `{"status":"ok","db":"ok"}` | integration | `docker compose exec backend pytest tests/test_health.py -x` | ❌ Wave 0 |
| INFRA-02 | No credentials present in image layers | security | `docker inspect cinemachain-backend \| grep -v API_KEY` (manual check) | manual-only |
| INFRA-02 | App starts with placeholder `.env` values | integration | `docker compose exec backend pytest tests/test_settings.py -x` | ❌ Wave 0 |
| INFRA-03 | PostgreSQL data persists across container restart | integration | Restart sequence + `SELECT 1` from a pre-seeded row | ❌ Wave 0 |
| INFRA-04 | UI reachable on Tailscale IP | smoke | `curl -f https://cinemachain.<tailnet>.ts.net/health` (manual from another device) | manual-only |

### Sampling Rate
- **Per task commit:** `docker compose exec backend pytest tests/test_health.py -x -q`
- **Per wave merge:** `docker compose exec backend pytest tests/ -v`
- **Phase gate:** All containers healthy + `/health` returns 200 + PostgreSQL volume survives restart + Tailscale reachable before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_health.py` — covers INFRA-01 health endpoint
- [ ] `backend/tests/test_settings.py` — covers INFRA-02 settings validation
- [ ] `backend/pytest.ini` — pytest configuration
- [ ] Install: `pip install pytest pytest-asyncio httpx` added to `requirements.txt`

---

## Sources

### Primary (HIGH confidence)
- `STATE.md` (project) — Stack decisions (PostgreSQL 16, FastAPI 0.115.x, Tailscale sidecar mandatory config)
- `PITFALLS.md` (project) — Synology PUID/PGID, port 5432 reservation, OOM kill patterns, secrets pitfalls
- `STACK.md` (project) — Synology Compose patterns, Tailscale sidecar YAML, volume mount paths
- `ARCHITECTURE.md` (project) — Full Compose service definitions, FastAPI + async SQLAlchemy setup, PostgreSQL schema patterns
- [Tailscale Docker Docs](https://tailscale.com/kb/1282/docker) — Official Tailscale docs; `TS_USERSPACE` flag
- [Tailscale Sidecar for Synology NAS (tatey.com, March 2026)](https://tatey.com/2026/03/08/tailscale-sidecar-pattern-for-synology-nas-with-dsm-7-and-container-manager/) — Recent, DSM 7 specific, confirms `TS_USERSPACE=true` requirement
- [TRaSH Guides: Synology Setup](https://trash-guides.info/File-and-Folder-Structure/How-to-set-up/Synology/) — PUID/PGID, volume paths for arr-stack community
- [FastAPI + Async SQLAlchemy Setup](https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/) — DB session factory, lifespan, Alembic pattern

### Secondary (MEDIUM confidence)
- [Marius Hosting: Synology Docker Issues](https://mariushosting.com/synology-common-docker-issues-and-fixes/) — Synology-specific permission and port conflict guides
- [DrFrankenstein: Restricted Docker User Setup](https://drfrankenstein.co.uk/step-2-setting-up-a-restricted-docker-user-and-obtaining-ids/) — PUID/PGID setup walkthrough for Synology

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed in project research from official PyPI/docs sources
- Architecture: HIGH — Synology constraints confirmed with multiple sources including a March 2026 Tailscale/Synology-specific guide
- Pitfalls: HIGH — Synology port 5432 and PUID/PGID documented in project pitfalls research with official and community sources
- Validation: MEDIUM — test framework standard; specific test content is Wave 0 work, not pre-existing

**Research date:** 2026-03-14
**Valid until:** 2026-09-14 (stable infrastructure patterns; Tailscale image should be re-verified if `latest` tag is pinned)
