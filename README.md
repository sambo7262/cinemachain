# CinemaChain

A chain-based movie discovery engine. Navigate cinema through shared actors — pick a movie, choose an actor from its cast, explore their filmography, pick your next movie, and keep the chain going. Never repeat an actor within a session.

Built for home media enthusiasts running Radarr. When you find a movie you want to watch, CinemaChain sends it straight to your Radarr download queue.

---

## Features

- **Actor-chain Movie Game** — discover movies through shared cast connections
- **Multi-session support** — name, archive, export/import sessions as CSV
- **Radarr integration** — request movies directly from the game
- **Nightly TMDB cache** — pre-fetches popular movie and actor data for fast browsing
- **Responsive UI** — works on desktop, tablet, and phone
- **Docker Compose deployment** — single command setup

---

## Prerequisites

- Docker and Docker Compose (v2)
- A TMDB account (free) for API access
- Radarr running and accessible on your network (for movie requests)

---

## Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/sambo7262/cinemachain.git && cd cinemachain
   ```

2. Copy the environment template:
   ```
   cp .env.example .env
   ```

3. Edit `.env` with your values — at minimum: `DB_PASSWORD`, `TMDB_API_KEY`, `RADARR_URL`, `RADARR_API_KEY`

4. Start the stack:
   ```
   docker compose up -d
   ```

5. Open the UI: `http://localhost:3111`

6. (First run) Configure any additional settings in the in-app Settings page

> **Note:** First startup may take a few minutes as the database initializes and the TMDB cache begins populating.

---

## Getting API Keys

### TMDB

1. Create a free account at [themoviedb.org](https://www.themoviedb.org)
2. Go to Settings > API > Request an API Key
3. Copy the "API Key (v3 auth)" value
4. Set `TMDB_API_KEY` in your `.env`

### Radarr

1. Open your Radarr web UI
2. Go to Settings > General > Security
3. Copy the API Key
4. Set `RADARR_URL` (e.g., `http://192.168.1.100:7878`) and `RADARR_API_KEY` in your `.env`

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_PASSWORD` | Yes | — | PostgreSQL password for the cinemachain database user |
| `TMDB_API_KEY` | Yes | — | TMDB API key (v3) for movie and actor metadata |
| `RADARR_URL` | Yes | — | URL of your Radarr instance (e.g., `http://192.168.1.100:7878`) |
| `RADARR_API_KEY` | Yes | — | Radarr API key for sending download requests |
| `DATA_DIR` | No | `./data` | Host path for all volume bind-mounts |
| `PUID` | No | `1000` | User ID for file ownership in containers |
| `PGID` | No | `1000` | Group ID for file ownership in containers |
| `RADARR_QUALITY_PROFILE` | No | `HD+` | Radarr quality profile name for requested movies |
| `TMDB_CACHE_TIME` | No | `03:00` | Time (UTC, 24h) to run the nightly TMDB cache refresh |
| `TMDB_CACHE_TOP_N` | No | `5000` | Number of top-voted movies to pre-cache nightly |
| `TMDB_CACHE_TOP_ACTORS` | No | `1500` | Number of popular actors to pre-warm in the nightly cache |
| `TMDB_CACHE_RUN_ON_STARTUP` | No | `false` | Run cache refresh on app startup (useful for first deploy) |
| `SETTINGS_ENCRYPTION_KEY` | No | (empty) | Fernet key for encrypting DB-stored settings (see `.env.example` for generation command) |

---

## Architecture

```
                    +-------------------+
                    |    Frontend       |
                    |  (React + Nginx)  |
                    |   :3111 -> :80    |
                    +--------+----------+
                             |
                             v
                    +-------------------+
                    |    Backend        |
                    | (FastAPI + Uvicorn)|
                    |   :8111 -> :8000  |
                    +--------+----------+
                             |
                +------------+------------+
                |                         |
                v                         v
      +-------------------+    +--------------------+
      |   PostgreSQL      |    |   External APIs    |
      |   :5433 (local)   |    |  TMDB / Radarr     |
      +-------------------+    +--------------------+
```

The frontend is a React SPA served by Nginx. It communicates with the FastAPI backend, which manages game sessions, caches TMDB data in PostgreSQL, and forwards movie requests to Radarr.

---

## Troubleshooting

**1. Database not starting**

Check `docker compose logs postgres`. Ensure `DB_PASSWORD` is set in `.env`. If changing the password after first run, delete the postgres data directory (`$DATA_DIR/postgres`).

**2. Radarr requests failing**

Verify `RADARR_URL` is reachable from the Docker host (not `localhost` — use the LAN IP). Check `RADARR_API_KEY` is correct. Backend and Radarr must be on the same network or have routable connectivity.

**3. TMDB data not loading**

Confirm `TMDB_API_KEY` is valid. Check backend logs: `docker compose logs backend`. On first startup, set `TMDB_CACHE_RUN_ON_STARTUP=true` to populate the cache immediately.

**4. Permission errors on volumes**

Ensure `PUID` and `PGID` match the user running Docker. On Linux: `id $(whoami)`. On Synology NAS: `id your_docker_username` via SSH.

**5. Port conflicts**

Backend uses 8111, frontend uses 3111, Postgres uses 5433. If any conflict, edit `compose.yaml` ports section (change only the left/host side).

---

## NAS Users (Synology, UNRAID, etc.)

The default configuration works on any Docker host. NAS users may want to override `DATA_DIR` to use a persistent storage path (e.g., `DATA_DIR=/volume1/docker/appdata/cinemachain` on Synology). `PUID`/`PGID` should match your NAS Docker user.
