from __future__ import annotations

import httpx


class RadarrClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Api-Key": api_key},
            timeout=15.0,
        )

    async def movie_exists(self, tmdb_id: int) -> bool:
        """Check if movie is in Radarr. Filters in Python to handle Radarr bug #6086
        where GET /api/v3/movie?tmdbId=X may return all movies on older installs."""
        r = await self._client.get("/api/v3/movie", params={"tmdbId": tmdb_id})
        r.raise_for_status()
        return any(m.get("tmdbId") == tmdb_id for m in r.json())

    async def lookup_movie(self, tmdb_id: int) -> dict | None:
        """GET /api/v3/movie/lookup?term=tmdb:{id} — returns Radarr's full movie object
        including titleSlug, images, qualityProfileId required for POST /api/v3/movie."""
        r = await self._client.get(
            "/api/v3/movie/lookup",
            params={"term": f"tmdb:{tmdb_id}"},
        )
        r.raise_for_status()
        results = r.json()
        return results[0] if results else None

    async def add_movie(self, payload: dict) -> dict:
        """POST /api/v3/movie. Radarr returns 400 when movie already exists — treat as success."""
        r = await self._client.post("/api/v3/movie", json=payload)
        if r.status_code == 400:
            return {"status": "already_exists"}
        r.raise_for_status()
        return r.json()

    async def get_root_folder(self) -> str:
        """GET /api/v3/rootfolder — return first configured folder path."""
        r = await self._client.get("/api/v3/rootfolder")
        r.raise_for_status()
        folders = r.json()
        return folders[0]["path"] if folders else "/movies"

    async def get_quality_profile_id(self) -> int:
        """GET /api/v3/qualityprofile — return first profile id."""
        r = await self._client.get("/api/v3/qualityprofile")
        r.raise_for_status()
        profiles = r.json()
        return profiles[0]["id"] if profiles else 1

    async def close(self) -> None:
        await self._client.aclose()
