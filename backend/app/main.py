import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.routers import health
from app.routers import movies as movies_router
from app.routers import actors as actors_router
from app.routers import debug as debug_router
from app.routers import game as game_router
from app.services.tmdb import TMDBClient
from app.services.radarr import RadarrClient
from app.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 2. Initialize TMDB client (shared across all requests via app.state)
    tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)
    app.state.tmdb_client = tmdb_client
    logger.info("TMDBClient initialized")

    # 3. Initialize Radarr client (shared across all requests via app.state)
    radarr_client = RadarrClient(
        base_url=settings.radarr_url,
        api_key=settings.radarr_api_key,
        quality_profile=settings.radarr_quality_profile,
    )
    app.state.radarr_client = radarr_client
    logger.info("RadarrClient initialized")

    yield

    # Shutdown
    await tmdb_client.close()
    await radarr_client.close()
    await engine.dispose()


app = FastAPI(title="CinemaChain", lifespan=lifespan)

app.include_router(health.router)
app.include_router(movies_router.router)
app.include_router(actors_router.router)
app.include_router(debug_router.router)
app.include_router(game_router.router)
