from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=2,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Shared factory for background tasks (scheduler, background_tasks) — separate from request sessions
_bg_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
