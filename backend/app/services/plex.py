import asyncio
import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import AsyncSessionLocal
from app.models import WatchEvent

logger = logging.getLogger(__name__)


def _sync_plex_watched(plex_url: str, plex_token: str) -> list[dict]:
    """Synchronous Plex library fetch. Must be run via run_in_executor.

    Returns list of {"tmdb_id": int} dicts for every watched movie in the
    Plex Movies library that has a tmdb:// GUID.
    """
    from plexapi.server import PlexServer  # imported here to avoid import-time side effects

    plex = PlexServer(plex_url, plex_token)
    movies = plex.library.section("Movies").search()
    results = []
    for m in movies:
        if not m.isWatched:
            continue
        tmdb_id = None
        for guid in m.guids:
            if guid.id.startswith("tmdb://"):
                try:
                    tmdb_id = int(guid.id.split("//")[1])
                except (IndexError, ValueError):
                    continue
                break
        if tmdb_id is not None:
            results.append({"tmdb_id": tmdb_id})
    return results


async def _upsert_watch_events(
    watched_items: list[dict],
    source: str = "plex_sync",
) -> int:
    """Bulk-upsert watch_events rows. Returns count of rows processed."""
    if not watched_items:
        return 0

    async with AsyncSessionLocal() as db:
        for item in watched_items:
            stmt = (
                pg_insert(WatchEvent)
                .values(
                    tmdb_id=item["tmdb_id"],
                    movie_id=None,  # movies may not be in DB yet; FK is nullable
                    source=source,
                    watched_at=datetime.utcnow(),
                )
                .on_conflict_do_nothing(index_elements=["tmdb_id"])
            )
            await db.execute(stmt)
        await db.commit()

    return len(watched_items)


async def sync_on_startup(plex_url: str, plex_token: str) -> None:
    """Async coroutine for the main.py lifespan startup hook.

    Wraps the synchronous PlexAPI call in run_in_executor so it does not
    block the event loop. Plex being unavailable is non-fatal: logs a
    warning and returns.
    """
    loop = asyncio.get_event_loop()
    try:
        watched_items = await loop.run_in_executor(
            None, _sync_plex_watched, plex_url, plex_token
        )
        count = await _upsert_watch_events(watched_items, source="plex_sync")
        logger.info("Plex startup sync complete: %d watched movies synced", count)
    except Exception as exc:
        logger.warning("Plex startup sync failed (non-fatal): %s", exc)
