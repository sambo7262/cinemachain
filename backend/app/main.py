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
from app.routers import game as game_router
from app.routers import search as search_router
from app.routers.settings import router as settings_router
from app.routers import mdblist as mdblist_router
from app.routers import cache as cache_router
from app.routers.mdblist import mdblist_nightly_job
from app.services import settings_service
from app.services.cache import nightly_cache_job
from app.services.settings_service import bootstrap_encryption_key, re_encrypt_plaintext_settings
from app.services.tmdb import TMDBClient
from app.services.radarr import RadarrClient
from app.settings import settings
from app.utils.log_filter import ScrubSecretsFilter
from app.utils.masking import register_secret, _active_secrets

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger().addFilter(ScrubSecretsFilter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. Bootstrap encryption key (must run before any DB access touches secrets)
    bootstrap_encryption_key()

    # 1. Verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 1b. Migrate .env settings to DB on first startup (no-op if already populated)
    #     + re-encrypt any plaintext secret rows left from before encryption was configured
    async with AsyncSessionLocal() as db:
        migrated = await settings_service.migrate_env_to_db(db)
        if migrated:
            logger.info("Migrated .env settings to database")
        await re_encrypt_plaintext_settings(db)
        await db.commit()

    # 2. Initialize TMDB client (shared across all requests via app.state)
    # Load tmdb_api_key from DB (user may have updated it via Settings UI after first run)
    async with AsyncSessionLocal() as db:
        tmdb_api_key = await settings_service.get_setting(db, "tmdb_api_key") or settings.tmdb_api_key
    tmdb_client = TMDBClient(api_key=tmdb_api_key)
    app.state.tmdb_client = tmdb_client
    app.state.tmdb_cache_top_n = settings.tmdb_cache_top_n
    app.state.tmdb_cache_top_actors = settings.tmdb_cache_top_actors
    logger.info("TMDBClient initialized")
    logger.warning(
        "TMDB now uses Bearer token auth. If TMDB calls fail with 401, update "
        "tmdb_api_key in Settings to your TMDB 'API Read Access Token' (long JWT), "
        "not the v3 API Key. See Settings page for details."
    )

    # 3. Initialize Radarr client (shared across all requests via app.state)
    radarr_client = RadarrClient(
        base_url=settings.radarr_url,
        api_key=settings.radarr_api_key,
        quality_profile=settings.radarr_quality_profile,
    )
    app.state.radarr_client = radarr_client
    logger.info("RadarrClient initialized")

    # 3b. Register live API keys for log scrubbing
    async with AsyncSessionLocal() as db:
        for key_name in ("tmdb_api_key", "radarr_api_key", "mdblist_api_key"):
            val = await settings_service.get_setting(db, key_name)
            if val:
                register_secret(val)
    logger.info("Registered %d API keys for log scrubbing", len(_active_secrets))

    # 4. Start APScheduler for nightly TMDB cache job and MDBList nightly job
    cache_time_parts = settings.tmdb_cache_time.split(":")
    cache_hour = int(cache_time_parts[0])
    cache_minute = int(cache_time_parts[1])

    # Read MDBList schedule time from DB (set in Settings UI)
    async with AsyncSessionLocal() as db:
        mdb_schedule_time = await settings_service.get_setting(db, "mdblist_schedule_time") or "04:00"

    mdb_parts = mdb_schedule_time.split(":")
    mdb_hour = int(mdb_parts[0])
    mdb_minute = int(mdb_parts[1])

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        nightly_cache_job,
        trigger=CronTrigger(hour=cache_hour, minute=cache_minute, timezone="America/Los_Angeles"),
        kwargs={"tmdb": tmdb_client, "top_n": settings.tmdb_cache_top_n, "top_actors": settings.tmdb_cache_top_actors},
        id="nightly_tmdb_cache",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        mdblist_nightly_job,
        trigger=CronTrigger(hour=mdb_hour, minute=mdb_minute, timezone="America/Los_Angeles"),
        id="nightly_mdblist",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("APScheduler started — TMDB nightly at %02d:%02d LA time", cache_hour, cache_minute)
    logger.info("APScheduler: MDBList nightly at %02d:%02d LA time", mdb_hour, mdb_minute)

    # 5. Optional startup cache run (set TMDB_CACHE_RUN_ON_STARTUP=true to trigger immediately)
    if settings.tmdb_cache_run_on_startup:
        logger.info("TMDB_CACHE_RUN_ON_STARTUP=true — triggering cache job now")
        asyncio.create_task(nightly_cache_job(tmdb=tmdb_client, top_n=settings.tmdb_cache_top_n, top_actors=settings.tmdb_cache_top_actors))

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
app.include_router(search_router.router)
app.include_router(game_router.router)
app.include_router(settings_router)
app.include_router(mdblist_router.router)
app.include_router(cache_router.router)
