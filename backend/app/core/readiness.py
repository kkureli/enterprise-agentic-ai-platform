from qdrant_client import AsyncQdrantClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.redis_service import ping_redis


async def check_postgres() -> bool:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False


async def check_redis() -> bool:
    return await ping_redis()


async def check_qdrant() -> bool:
    if settings.qdrant_api_key:
        client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    else:
        client = AsyncQdrantClient(url=settings.qdrant_url)

    try:
        await client.get_collections()
        return True
    except Exception:
        return False
    finally:
        await client.close()
