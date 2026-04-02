from __future__ import annotations

import asyncio

import httpx

# IMPORTANT -- TMDB Read Access Token required:
# TMDBClient now uses Bearer token authentication (Authorization header).
# The stored tmdb_api_key must be the "API Read Access Token" from your TMDB account
# API settings page (the long JWT starting with eyJ...), NOT the v3 "API Key" (short hex).
# After deploying this phase, update the TMDB API key field in CinemaChain Settings.
# See: https://developer.themoviedb.org/docs/authentication-application


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str) -> None:
        # NOTE: api_key parameter now expects the TMDB "API Read Access Token" (v4 auth, long JWT),
        # NOT the v3 "API Key" (short hex string). Users must update their stored value in Settings.
        # See: https://developer.themoviedb.org/docs/authentication-application
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=60.0, read=90.0, write=30.0, pool=10.0),
        )
        self._sem = asyncio.Semaphore(10)

    async def fetch_movie(self, tmdb_id: int) -> dict:
        """Fetch movie details with cast credits in a single call.

        Returns the raw TMDB response dict. Credits are under response["credits"]["cast"]
        due to append_to_response nesting — NOT response["cast"].
        """
        async with self._sem:
            r = await self._client.get(
                f"/movie/{tmdb_id}",
                params={"append_to_response": "credits"},
            )
            r.raise_for_status()
            return r.json()

    async def fetch_actor_credits(self, person_id: int) -> dict:
        """Fetch an actor's movie credits.

        Returns dict with .cast[] containing movie entries.
        """
        async with self._sem:
            r = await self._client.get(f"/person/{person_id}/movie_credits")
            r.raise_for_status()
            return r.json()

    async def fetch_person(self, person_id: int) -> dict:
        """Fetch actor/person details (name, profile_path, etc).

        Returns dict with name, profile_path and other person metadata.
        """
        async with self._sem:
            r = await self._client.get(f"/person/{person_id}")
            r.raise_for_status()
            return r.json()

    async def search_person(self, name: str) -> dict | None:
        """Search TMDB for a person by name. Returns the top result dict or None."""
        async with self._sem:
            r = await self._client.get("/search/person", params={"query": name})
            r.raise_for_status()
            results = r.json().get("results", [])
            return results[0] if results else None

    async def discover_movies(self, genre_id: int, page: int = 1) -> dict:
        """Fetch TMDB Discover results for a genre. Returns raw response dict with 'results' key."""
        async with self._sem:
            r = await self._client.get(
                "/discover/movie",
                params={"sort_by": "popularity.desc", "with_genres": genre_id, "page": page},
            )
            r.raise_for_status()
            return r.json()

    async def fetch_recommendations(self, tmdb_id: int) -> dict:
        """Fetch TMDB movie recommendations. Returns raw response with results[].

        Each result has 'id' (TMDB movie ID). Page 1 returns ~20 results.
        Pagination not needed — page 1 is sufficient for suggestion ranking.
        """
        async with self._sem:
            r = await self._client.get(f"/movie/{tmdb_id}/recommendations")
            r.raise_for_status()
            return r.json()

    async def test_connection(self) -> None:
        """Test TMDB API key by hitting /authentication. Raises on failure."""
        r = await self._client.get("/authentication")
        r.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
