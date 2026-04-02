from __future__ import annotations

import httpx


class RadarrClient:
    def __init__(self, base_url: str, api_key: str, quality_profile: str = "HD+") -> None:
        self._quality_profile = quality_profile
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
        """GET /api/v3/qualityprofile — return id of profile matching self._quality_profile name."""
        r = await self._client.get("/api/v3/qualityprofile")
        r.raise_for_status()
        profiles = r.json()
        for profile in profiles:
            if profile["name"] == self._quality_profile:
                return profile["id"]
        # Fallback: log warning and use first profile if named profile not found
        import logging
        logging.getLogger(__name__).warning(
            "Radarr quality profile %r not found; falling back to first profile", self._quality_profile
        )
        return profiles[0]["id"] if profiles else 1

    async def test_connection(self) -> dict:
        """Test Radarr connectivity, API key, and quality profile.
        Returns {"ok": bool, "error": str|None, "warning": str|None}.
        """
        # Step 1+2: URL reachable + key valid
        try:
            r = await self._client.get("/api/v3/system/status")
        except httpx.ConnectError:
            return {"ok": False, "error": f"Cannot reach Radarr at {self._client.base_url} — check the URL and that Radarr is running", "warning": None}
        except httpx.TimeoutException:
            return {"ok": False, "error": f"Radarr at {self._client.base_url} timed out — check the URL and that Radarr is running", "warning": None}
        if r.status_code == 401:
            return {"ok": False, "error": "Radarr rejected the API key — check Settings > General > Security in Radarr", "warning": None}
        if r.status_code != 200:
            return {"ok": False, "error": f"Radarr returned unexpected status {r.status_code}", "warning": None}

        # Step 3: Quality profile check
        try:
            pr = await self._client.get("/api/v3/qualityprofile")
            pr.raise_for_status()
            profiles = pr.json()
            names = [p["name"] for p in profiles]
            if self._quality_profile not in names:
                return {"ok": True, "error": None, "warning": f"Quality profile '{self._quality_profile}' not found — available profiles: {names}"}
        except Exception:
            return {"ok": True, "error": None, "warning": "Could not verify quality profile"}

        return {"ok": True, "error": None, "warning": None}

    async def close(self) -> None:
        await self._client.aclose()
