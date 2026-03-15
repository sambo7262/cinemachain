import pytest
from httpx import AsyncClient, ASGITransport

# app import is deferred so this conftest can be collected before backend is implemented.
# Plans 02/03 create app/main.py — at that point imports succeed and fixtures activate.

@pytest.fixture
async def client():
    try:
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    except ImportError:
        pytest.skip("app.main not yet implemented — Wave 1 will create it")

@pytest.fixture
def db_url():
    """Returns the DATABASE_URL env var for persistence tests."""
    import os
    return os.getenv("DATABASE_URL", "postgresql+asyncpg://cinema:changeme@localhost:5432/cinemachain")
