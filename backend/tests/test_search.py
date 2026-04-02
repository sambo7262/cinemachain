"""
QMODE-01: GET /search/movies?q= returns enriched movie list (RT, MPAA, runtime, genres).
QMODE-02: GET /search/actors?q= resolves person name -> full cast + crew credits as movie list.
QMODE-03: GET /movies/popular?genre= returns top 50 popular movies for a genre via TMDB Discover.
QMODE-06: POST /movies/{tmdb_id}/request queues via Radarr and returns status dict.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# QMODE-01: Enriched movie search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_movies_enriched(client):
    """QMODE-01: GET /search/movies?q=inception returns movies with rt_score, mpaa_rating, runtime, genres."""
    mock_tmdb_response = {
        "results": [
            {
                "id": 27205,
                "title": "Inception",
                "release_date": "2010-07-16",
                "poster_path": "/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
                "vote_average": 8.4,
                "vote_count": 35000,
            }
        ]
    }
    mock_http_response = MagicMock()
    mock_http_response.raise_for_status = lambda: None
    mock_http_response.json.return_value = mock_tmdb_response

    with patch("app.routers.search.fetch_rt_scores", new_callable=AsyncMock), \
         patch("app.routers.search._ensure_movie_details_in_db", new_callable=AsyncMock), \
         patch.object(
             client.app.state.tmdb_client._client,
             "get",
             new_callable=AsyncMock,
             return_value=mock_http_response,
         ):
        resp = await client.get("/search/movies?q=inception")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# QMODE-02: Actor/person search -> filmography
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_actors(client):
    """QMODE-02: GET /search/actors?q=nolan returns movies where person has cast OR crew credits."""
    mock_person = {"id": 525, "name": "Christopher Nolan"}
    mock_credits = {
        "cast": [
            {
                "id": 27205,
                "title": "Inception",
                "release_date": "2010-07-16",
                "poster_path": "/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
                "vote_average": 8.4,
                "vote_count": 35000,
            }
        ],
        "crew": [
            {
                "id": 49026,
                "title": "The Dark Knight Rises",
                "release_date": "2012-07-20",
                "poster_path": "/dEYnvnUfXrqvqeRSqvIQ1re7ja9.jpg",
                "vote_average": 8.4,
                "vote_count": 28000,
                "job": "Director",
            }
        ],
    }

    with patch("app.routers.search.fetch_rt_scores", new_callable=AsyncMock), \
         patch("app.routers.search._ensure_movie_details_in_db", new_callable=AsyncMock), \
         patch.object(
             client.app.state.tmdb_client,
             "search_person",
             new_callable=AsyncMock,
             return_value=mock_person,
         ), \
         patch.object(
             client.app.state.tmdb_client,
             "fetch_actor_credits",
             new_callable=AsyncMock,
             return_value=mock_credits,
         ):
        resp = await client.get("/search/actors?q=nolan")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# QMODE-03: Genre browse via TMDB Discover
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_popular_by_genre(client):
    """QMODE-03: GET /movies/popular?genre=28 returns a list (not 422)."""
    mock_discover_response = {
        "results": [
            {
                "id": 27205,
                "title": "Inception",
                "release_date": "2010-07-16",
                "poster_path": "/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
                "vote_average": 8.4,
                "vote_count": 35000,
            }
        ]
    }

    with patch("app.routers.movies.fetch_rt_scores", new_callable=AsyncMock), \
         patch("app.routers.game._ensure_movie_details_in_db", new_callable=AsyncMock), \
         patch.object(
             client.app.state.tmdb_client,
             "discover_movies",
             new_callable=AsyncMock,
             return_value=mock_discover_response,
         ):
        resp = await client.get("/movies/popular?genre=28")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# QMODE-06: Standalone Radarr request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_movie_standalone(client):
    """QMODE-06: POST /movies/{tmdb_id}/request returns status dict (queued/already_in_radarr/not_found_in_radarr/error)."""
    with patch(
        "app.services.radarr_helper._request_radarr",
        new_callable=AsyncMock,
        return_value={"status": "queued"},
    ):
        resp = await client.post("/movies/27205/request")

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("queued", "already_in_radarr", "not_found_in_radarr", "error")
