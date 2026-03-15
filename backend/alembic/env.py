import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base
from app.settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)

    async def run_async() -> None:
        async with connectable.connect() as conn:
            await conn.run_sync(context.run_migrations)
        await connectable.dispose()

    asyncio.run(run_async())


run_migrations_online()
