"""
DATA-01: GET /movies/{id} returns poster, rating, year, genres sourced from TMDB (first call hits TMDB).
DATA-02: GET /actors/{id}/filmography returns cast credits from TMDB.
DATA-03: Second GET /movies/{id} is served from DB cache — no second TMDB call.

Wave 1 (Plan 02-03) implements the routes and TMDB service.
These tests become green after Plan 02-03 executes.
"""
import pytest


@pytest.mark.asyncio
async def test_fetch_movie_details(client):
    """DATA-01: GET /movies/550 returns title, poster_path, vote_average, year, genres."""
    response = await client.get("/movies/550")
    assert response.status_code == 200
    body = response.json()
    assert "title" in body
    assert "poster_path" in body
    assert "vote_average" in body
    assert "year" in body
    assert "genres" in body


@pytest.mark.asyncio
async def test_fetch_actor_credits(client):
    """DATA-02: GET /actors/819/filmography returns actor name and list of movie credits."""
    response = await client.get("/actors/819/filmography")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "credits" in body
    assert isinstance(body["credits"], list)


@pytest.mark.asyncio
async def test_movie_cached_on_repeat_request(client):
    """DATA-03: Second GET /movies/{id} returns same data without a second TMDB API call.
    Implementation verifies by checking fetched_at timestamp is not updated on second call.
    """
    r1 = await client.get("/movies/550")
    assert r1.status_code == 200
    fetched_at_1 = r1.json().get("fetched_at")

    r2 = await client.get("/movies/550")
    assert r2.status_code == 200
    fetched_at_2 = r2.json().get("fetched_at")

    # fetched_at must not change — data came from DB cache, not a new TMDB call
    assert fetched_at_1 == fetched_at_2, "fetched_at changed on repeat request — cache miss"
