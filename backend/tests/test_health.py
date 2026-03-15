"""
INFRA-01: GET /health returns {"status": "ok", "db": "ok"} when backend + PostgreSQL are running.
Wave 1 (Plan 03) implements the endpoint. This test becomes green after Plan 03 executes.
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    """GET /health must return 200 with {status: ok, db: ok}."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


@pytest.mark.asyncio
async def test_health_db_connected(client):
    """Health endpoint must verify DB connectivity, not just return a static response."""
    response = await client.get("/health")
    assert response.status_code == 200
    # If db is "error", the DB connection is broken even though HTTP returned 200
    assert response.json().get("db") != "error"
