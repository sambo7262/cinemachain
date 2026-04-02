from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request

from app.services.cache import _cache_state, nightly_cache_job
from app.settings import settings as app_settings

router = APIRouter(prefix="/cache", tags=["cache"])


@router.post("/run-now")
async def run_cache_now(background_tasks: BackgroundTasks, request: Request):
    """Trigger TMDB nightly cache job immediately as a background task."""
    if _cache_state.running:
        return {"running": True}
    tmdb = request.app.state.tmdb_client
    background_tasks.add_task(
        nightly_cache_job,
        tmdb=tmdb,
        top_n=getattr(request.app.state, "tmdb_cache_top_n", app_settings.tmdb_cache_top_n),
        top_actors=getattr(request.app.state, "tmdb_cache_top_actors", app_settings.tmdb_cache_top_actors),
    )
    return {"started": True}


@router.get("/status")
async def cache_status():
    """Return TMDB cache job run status."""
    return {
        "running": _cache_state.running,
        "last_run_at": _cache_state.last_run_at.isoformat() if _cache_state.last_run_at else None,
        "last_run_duration_s": _cache_state.last_run_duration_s,
    }
