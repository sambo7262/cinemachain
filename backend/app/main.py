import asyncio
import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import engine, AsyncSessionLocal
from app.routers import health
from app.routers import movies as movies_router
from app.routers import actors as actors_router
from app.routers import debug as debug_router
from app.routers import game as game_router
from app.routers.settings import router as settings_router
from app.services import settings_service
from app.services.cache import nightly_cache_job
from app.services.tmdb import TMDBClient
from app.services.radarr import RadarrClient
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 1b. Migrate .env settings to DB on first startup (no-op if already populated)
    async with AsyncSessionLocal() as db:
        migrated = await settings_service.migrate_env_to_db(db)
        if migrated:
            logger.info("Migrated .env settings to database")
        await db.commit()

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

    # 4. Start APScheduler for nightly TMDB cache job
    cache_time_parts = settings.tmdb_cache_time.split(":")
    cache_hour = int(cache_time_parts[0])
    cache_minute = int(cache_time_parts[1])

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        nightly_cache_job,
        trigger=CronTrigger(hour=cache_hour, minute=cache_minute, timezone="UTC"),
        kwargs={"tmdb": tmdb_client, "top_n": settings.tmdb_cache_top_n},
        id="nightly_tmdb_cache",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("APScheduler started — nightly cache at %02d:%02d UTC", cache_hour, cache_minute)

    # 5. Optional startup cache run (set TMDB_CACHE_RUN_ON_STARTUP=true to trigger immediately)
    if settings.tmdb_cache_run_on_startup:
        logger.info("TMDB_CACHE_RUN_ON_STARTUP=true — triggering cache job now")
        asyncio.create_task(nightly_cache_job(tmdb=tmdb_client, top_n=settings.tmdb_cache_top_n))

    # 6. Static files — ensure /static/posters/ exists and mount it
    os.makedirs("static/posters", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("StaticFiles mounted at /static/")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await tmdb_client.close()
    await radarr_client.close()
    await engine.dispose()


app = FastAPI(title="CinemaChain", lifespan=lifespan)

app.include_router(health.router)
app.include_router(movies_router.router)
app.include_router(actors_router.router)
app.include_router(debug_router.router)
app.include_router(game_router.router)
app.include_router(settings_router)
