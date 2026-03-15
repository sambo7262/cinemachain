import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import GameSession, WatchEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _maybe_advance_session(tmdb_id: int, db: AsyncSession) -> None:
    """Advance active game session when the session's current queued movie is watched.

    CRITICAL: Only advances status='active' sessions — paused sessions are intentionally excluded.
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.status == "active")
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if session and session.current_movie_tmdb_id == tmdb_id:
        session.status = "awaiting_continue"
        await db.commit()
        logger.info(
            "Session %d awaiting_continue — tmdb_id=%d watched", session.id, tmdb_id
        )


def _extract_tmdb_id(metadata: dict) -> int | None:
    """Extract tmdb_id from Plex webhook Metadata.

    Handles both new Plex Movie agent (Guid list) and legacy agent (guid string).
    Returns None if no tmdb:// GUID is found.
    """
    # New agent: Metadata.Guid is a list of {"id": "tmdb://550"}
    guid_list = metadata.get("Guid", [])
    for g in guid_list:
        gid = g.get("id", "") if isinstance(g, dict) else str(g)
        if gid.startswith("tmdb://"):
            try:
                return int(gid.split("//")[1])
            except (IndexError, ValueError):
                continue

    # Legacy agent: Metadata.guid is a string like "com.plexapp.agents.themoviedb://550?lang=en"
    legacy = metadata.get("guid", "")
    if "themoviedb://" in legacy:
        try:
            part = legacy.split("themoviedb://")[1].split("?")[0]
            return int(part)
        except (IndexError, ValueError):
            pass

    return None


@router.post("/plex")
async def plex_webhook(
    payload: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """DATA-05: Receive Plex playback completion events.

    CRITICAL: Must use Form(...) not Body(...). Plex sends multipart/form-data
    with the JSON encoded in the 'payload' form field.
    """
    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Plex webhook received non-JSON payload — ignoring")
        return {"status": "ok"}

    if event.get("event") != "media.scrobble":
        return {"status": "ok"}

    metadata = event.get("Metadata", {})
    if metadata.get("type") != "movie":
        return {"status": "ok"}

    tmdb_id = _extract_tmdb_id(metadata)
    if tmdb_id is None:
        logger.warning("Plex scrobble event has no tmdb:// GUID — cannot mark watched")
        return {"status": "ok"}

    stmt = pg_insert(WatchEvent).values(
        tmdb_id=tmdb_id,
        movie_id=None,
        source="plex_webhook",
        watched_at=datetime.utcnow(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)
    await db.commit()

    logger.info("Scrobble: tmdb_id=%d marked watched via plex_webhook", tmdb_id)

    await _maybe_advance_session(tmdb_id, db)
    return {"status": "ok"}
