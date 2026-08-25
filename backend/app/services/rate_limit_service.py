"""Redis-backed rate limits for the public demo.

Ordinary limits (tenant/client/global/compare/write) fail open when Redis is
unavailable so local development remains usable.

The hard daily demo budget fails closed when PUBLIC_DEMO_MODE is enabled so a
Redis outage cannot remove the final cost ceiling.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import settings
from app.services.client_identity import LimitDecision
from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)


async def _incr_with_ttl(key: str, window_seconds: int) -> int | None:
    redis = get_redis()
    if redis is None:
        return None

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    return int(count)


async def _window_retry_after(window_seconds: int) -> int:
    now = int(time.time())
    elapsed = now % window_seconds
    return max(1, window_seconds - elapsed)


async def check_fixed_window_limit(
    *,
    key: str,
    limit: int,
    window_seconds: int,
    fail_open: bool,
    exceeded_reason: str,
) -> LimitDecision:
    if not settings.redis_enabled:
        if fail_open:
            return LimitDecision(allowed=True)
        return LimitDecision(
            allowed=False,
            retry_after_seconds=60,
            reason="Demo protections temporarily unavailable.",
            status_code=503,
        )

    try:
        count = await _incr_with_ttl(key, window_seconds)
    except Exception:
        logger.warning("Redis rate-limit failure key=%s", key, exc_info=True)
        if fail_open:
            return LimitDecision(allowed=True)
        return LimitDecision(
            allowed=False,
            retry_after_seconds=60,
            reason="Demo protections temporarily unavailable.",
            status_code=503,
        )

    if count is None:
        if fail_open:
            return LimitDecision(allowed=True)
        return LimitDecision(
            allowed=False,
            retry_after_seconds=60,
            reason="Demo protections temporarily unavailable.",
            status_code=503,
        )

    if count > limit:
        return LimitDecision(
            allowed=False,
            retry_after_seconds=await _window_retry_after(window_seconds),
            reason=exceeded_reason,
            status_code=429,
        )

    return LimitDecision(allowed=True)


async def check_tenant_rate_limit(tenant_id: UUID, *, units: int = 1) -> LimitDecision:
    window = settings.agent_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:agent:{tenant_id}:{window_id}"
    if units < 1:
        units = 1

    decision = LimitDecision(allowed=True)
    for _ in range(units):
        decision = await check_fixed_window_limit(
            key=key,
            limit=settings.agent_rate_limit_requests,
            window_seconds=window,
            fail_open=True,
            exceeded_reason="Tenant demo request limit reached. Try again shortly.",
        )
        if not decision.allowed:
            return decision
    return decision


# Backwards-compatible alias used by earlier code/tests.
async def check_agent_rate_limit(tenant_id: UUID) -> bool:
    decision = await check_tenant_rate_limit(tenant_id)
    return decision.allowed


async def check_client_rate_limit(client_hash: str, *, units: int = 1) -> LimitDecision:
    window = settings.client_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:client:{client_hash}:{window_id}"
    if units < 1:
        units = 1

    decision = LimitDecision(allowed=True)
    for _ in range(units):
        decision = await check_fixed_window_limit(
            key=key,
            limit=settings.client_rate_limit_requests,
            window_seconds=window,
            fail_open=True,
            exceeded_reason="Client demo request limit reached. Try again shortly.",
        )
        if not decision.allowed:
            return decision
    return decision


async def check_global_ai_rate_limit(*, units: int = 1) -> LimitDecision:
    window = settings.global_ai_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:global_ai:{window_id}"

    if units < 1:
        units = 1

    # Conservative: increment once per call unit by looping atomic incr.
    decision = LimitDecision(allowed=True)
    for _ in range(units):
        decision = await check_fixed_window_limit(
            key=key,
            limit=settings.global_ai_rate_limit_requests,
            window_seconds=window,
            fail_open=True,
            exceeded_reason="Global demo AI request limit reached. Try again later.",
        )
        if not decision.allowed:
            return decision
    return decision


async def check_compare_rate_limit(client_hash: str) -> LimitDecision:
    window = settings.compare_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:compare:{client_hash}:{window_id}"
    return await check_fixed_window_limit(
        key=key,
        limit=settings.compare_rate_limit_requests,
        window_seconds=window,
        fail_open=True,
        exceeded_reason="Compare Runs limit reached. Try again in a few minutes.",
    )


async def check_write_rate_limit(client_hash: str) -> LimitDecision:
    window = settings.demo_write_rate_limit_window_seconds
    window_id = int(time.time()) // window
    key = f"rate_limit:write:{client_hash}:{window_id}"
    return await check_fixed_window_limit(
        key=key,
        limit=settings.demo_write_rate_limit_requests,
        window_seconds=window,
        fail_open=True,
        exceeded_reason="Demo write-action limit reached. Try again later.",
    )


async def check_daily_ai_budget(*, units: int = 1) -> LimitDecision:
    """Hard daily request ceiling. Fail closed in PUBLIC_DEMO_MODE."""

    fail_open = not settings.public_demo_mode
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"demo_budget:ai_requests:{day}"
    # Expire shortly after day boundary (36h safety TTL).
    ttl_seconds = 36 * 3600

    if units < 1:
        units = 1

    decision = LimitDecision(allowed=True)
    for _ in range(units):
        decision = await check_fixed_window_limit(
            key=key,
            limit=settings.demo_daily_ai_request_limit,
            window_seconds=ttl_seconds,
            fail_open=fail_open,
            exceeded_reason=(
                "Public demo AI usage limit has been reached for today."
            ),
        )
        if not decision.allowed:
            if decision.status_code == 429:
                # Next UTC midnight approximate retry hint.
                now = datetime.now(UTC)
                seconds = (
                    24 * 3600
                    - (now.hour * 3600 + now.minute * 60 + now.second)
                )
                decision.retry_after_seconds = max(60, seconds)
            return decision
    return decision


async def demo_usage_status() -> str:
    """Coarse public status only."""

    if not settings.redis_enabled:
        return "available"

    redis = get_redis()
    if redis is None:
        return "limited" if settings.public_demo_mode else "available"

    day = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"demo_budget:ai_requests:{day}"

    try:
        value = await redis.get(key)
        count = int(value) if value is not None else 0
    except Exception:
        return "limited" if settings.public_demo_mode else "available"

    if count >= settings.demo_daily_ai_request_limit:
        return "limited"

    # Soft signal when >80% of daily budget used.
    if count >= int(settings.demo_daily_ai_request_limit * 0.8):
        return "limited"

    return "available"
