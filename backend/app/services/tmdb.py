import asyncio

import httpx


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            params={"api_key": api_key},
            timeout=10.0,
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

    async def close(self) -> None:
        await self._client.aclose()
