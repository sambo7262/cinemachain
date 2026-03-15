from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # Shutdown: dispose connection pool
    await engine.dispose()


app = FastAPI(title="CinemaChain", lifespan=lifespan)
app.include_router(health.router)
