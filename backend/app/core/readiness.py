from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


async def check_postgres() -> bool:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False


async def check_redis() -> bool:
    redis = Redis.from_url(settings.redis_url)

    try:
        return bool(await redis.ping())
    except Exception:
        return False
    finally:
        await redis.aclose()


async def check_qdrant() -> bool:
    client = AsyncQdrantClient(url=settings.qdrant_url)

    try:
        await client.get_collections()
        return True
    except Exception:
        return False
    finally:
        await client.close()
