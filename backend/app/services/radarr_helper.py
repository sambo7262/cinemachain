"""Shared Radarr helper — importable from any router without circular import risk."""
from __future__ import annotations

import logging

from app.services.radarr import RadarrClient

logger = logging.getLogger(__name__)


async def _request_radarr(tmdb_id: int, radarr: RadarrClient) -> dict:
    """Two-step Radarr add flow: check existence, then lookup + add.

    Returns a status dict rather than raising — callers must not let a
    Radarr failure produce a 500.
    """
    try:
        if await radarr.movie_exists(tmdb_id):
            return {"status": "already_in_radarr"}
        movie_payload = await radarr.lookup_movie(tmdb_id)
        if not movie_payload:
            return {"status": "not_found_in_radarr"}
        movie_payload["monitored"] = True
        movie_payload["addOptions"] = {"searchForMovie": True}
        movie_payload["rootFolderPath"] = await radarr.get_root_folder()
        movie_payload["qualityProfileId"] = await radarr.get_quality_profile_id()
        await radarr.add_movie(movie_payload)
        return {"status": "queued"}
    except Exception as exc:
        logger.warning("Radarr request failed for tmdb_id=%s: %s", tmdb_id, exc)
        return {"status": "error"}
