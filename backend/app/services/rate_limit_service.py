import logging
import time
from uuid import UUID

from app.core.config import settings
from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)


async def check_agent_rate_limit(tenant_id: UUID) -> bool:
    """Return True if the request is allowed.

    Fail-open policy (demo/portfolio): if Redis is disabled or unavailable,
    allow the request so the agent remains usable. Stricter production
    environments may fail closed or enforce limits at an API gateway.
    """
    if not settings.redis_enabled:
        return True

    redis = get_redis()

    if redis is None:
        logger.warning(
            "Redis unavailable for rate limiting; allowing request tenant_id=%s",
            tenant_id,
        )
        return True

    window = settings.agent_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:agent:{tenant_id}:{window_id}"

    try:
        count = await redis.incr(key)

        if count == 1:
            await redis.expire(key, window)

        if count > settings.agent_rate_limit_requests:
            logger.warning(
                "Agent rate limit exceeded tenant_id=%s count=%s limit=%s window=%ss",
                tenant_id,
                count,
                settings.agent_rate_limit_requests,
                window,
            )
            return False

        return True
    except Exception:
        logger.warning(
            "Redis rate-limit failure; allowing request tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return True
