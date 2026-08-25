from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings


def to_psycopg_conninfo(database_url: str) -> str:
    """Convert SQLAlchemy async URLs to a psycopg connection string."""

    url = database_url
    for prefix in (
        "postgresql+asyncpg://",
        "postgres+asyncpg://",
        "postgresql+psycopg://",
        "postgres+psycopg://",
    ):
        if url.startswith(prefix):
            url = "postgresql://" + url[len(prefix) :]
            break

    # asyncpg often uses ssl=require; psycopg expects sslmode=require.
    url = url.replace("ssl=require", "sslmode=require")
    url = url.replace("ssl=true", "sslmode=require")
    return url


def create_memory_checkpointer() -> InMemorySaver:
    return InMemorySaver()


async def create_postgres_checkpointer(
    database_url: str | None = None,
) -> tuple[Any, AsyncConnectionPool]:
    """Create an AsyncPostgresSaver backed by the application PostgreSQL database.

    Uses the same DATABASE_URL as the app (Neon in Phase 8B). Callers must close
    the returned connection pool on shutdown.
    """

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    conninfo = to_psycopg_conninfo(database_url or settings.database_url)

    pool = AsyncConnectionPool(
        conninfo=conninfo,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
    )
    await pool.open()

    checkpointer = AsyncPostgresSaver(conn=pool)
    await checkpointer.setup()

    return checkpointer, pool
