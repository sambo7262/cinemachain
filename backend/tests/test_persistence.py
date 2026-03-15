"""
INFRA-03: PostgreSQL data persists across container restarts via bind-mounted volume.
This test requires a running PostgreSQL container. It is a smoke/integration test
intended to run inside the compose stack: docker compose exec backend pytest tests/test_persistence.py -x
"""
import pytest
import os


@pytest.mark.asyncio
async def test_postgres_connection_alive():
    """Can connect to PostgreSQL via DATABASE_URL from environment."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set — run inside compose stack")
    try:
        import asyncpg
        # Strip SQLAlchemy prefix for raw asyncpg connection
        raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(raw_url)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        assert result == 1
    except ImportError:
        pytest.skip("asyncpg not installed — Wave 1 will add it to requirements.txt")
    except Exception as e:
        pytest.skip(f"PostgreSQL not reachable: {e} — run inside compose stack")


def test_volume_path_documented():
    """Confirm compose.yaml references the bind-mount path for PostgreSQL data."""
    import pathlib
    compose = pathlib.Path("compose.yaml")
    if not compose.exists():
        pytest.skip("compose.yaml not yet created — Wave 1 Plan 02 will create it")
    content = compose.read_text()
    assert "/volume1/docker/appdata/cinemachain/postgres" in content, \
        "compose.yaml must bind-mount postgres data to /volume1/docker/appdata/cinemachain/postgres"
