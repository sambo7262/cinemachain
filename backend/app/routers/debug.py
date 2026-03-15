from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actor, Movie, WatchEvent

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/watch-events")
async def debug_watch_events(db: AsyncSession = Depends(get_db)):
    """Debug: watch_events summary — count by source + 10 most recent rows."""
    counts_result = await db.execute(
        select(WatchEvent.source, func.count().label("count"))
        .group_by(WatchEvent.source)
    )
    counts = [{"source": row.source, "count": row.count} for row in counts_result]

    recent_result = await db.execute(
        select(WatchEvent).order_by(WatchEvent.watched_at.desc()).limit(10)
    )
    recent = [
        {
            "id": we.id,
            "tmdb_id": we.tmdb_id,
            "source": we.source,
            "watched_at": we.watched_at.isoformat() if we.watched_at else None,
        }
        for we in recent_result.scalars()
    ]

    return {"totals": counts, "recent": recent}


@router.get("/db-summary")
async def debug_db_summary(db: AsyncSession = Depends(get_db)):
    """Debug: row counts for all four tables."""
    movies = await db.scalar(select(func.count()).select_from(Movie))
    actors = await db.scalar(select(func.count()).select_from(Actor))
    watch_events = await db.scalar(select(func.count()).select_from(WatchEvent))

    return {
        "movies": movies,
        "actors": actors,
        "watch_events": watch_events,
    }
