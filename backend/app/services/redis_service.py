import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_redis() -> None:
    global _redis

    if not settings.redis_enabled:
        _redis = None
        logger.info("Redis disabled; skipping client init")
        return

    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def close_redis() -> None:
    global _redis

    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis | None:
    return _redis


async def ping_redis() -> bool:
    if not settings.redis_enabled:
        return False

    client = _redis

    if client is not None:
        try:
            return bool(await client.ping())
        except Exception:
            return False

    redis = Redis.from_url(settings.redis_url)

    try:
        return bool(await redis.ping())
    except Exception:
        return False
    finally:
        await redis.aclose()
