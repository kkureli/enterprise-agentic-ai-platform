from uuid import uuid4

import pytest

from app.services.rag_cache_service import (
    build_rag_cache_key,
    get_cached_rag_result,
    get_rag_cache_version,
    increment_rag_cache_version,
    set_cached_rag_result,
)
from app.services.rag_service import (
    RagResult,
    RagRetrievedChunk,
    RagSource,
    answer_question,
)
from app.services.rate_limit_service import check_agent_rate_limit


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.fail_get = False
        self.fail_set = False
        self.fail_incr = False

    async def get(self, key: str):
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        if self.fail_set:
            raise RuntimeError("redis set failed")
        self.store[key] = value

    async def incr(self, key: str) -> int:
        if self.fail_incr:
            raise RuntimeError("redis incr failed")
        current = int(self.store.get(key, "0")) + 1
        self.store[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        return True


def _sample_result(answer: str = "cached answer") -> RagResult:
    return RagResult(
        answer=answer,
        sources=[
            RagSource(
                document_id="doc-1",
                filename="manual.pdf",
                chunk_index=0,
                score=0.9,
            )
        ],
        retrieved_chunks=[
            RagRetrievedChunk(
                document_id="doc-1",
                filename="manual.pdf",
                chunk_index=0,
                score=0.9,
                text="hydraulic pressure loss",
            )
        ],
    )


@pytest.mark.asyncio
async def test_rag_cache_miss_executes_pipeline(monkeypatch):
    fake_redis = FakeRedis()
    tenant_id = uuid4()
    calls = {"retrieve": 0, "llm": 0}

    monkeypatch.setattr(
        "app.services.rag_cache_service.get_redis",
        lambda: fake_redis,
    )
    monkeypatch.setattr(
        "app.core.config.settings.redis_enabled",
        True,
    )

    async def fake_retrieve(**kwargs):
        calls["retrieve"] += 1
        return []

    monkeypatch.setattr(
        "app.services.rag_service.retrieve_for_rag_mode",
        fake_retrieve,
    )

    result = await answer_question(
        tenant_id=tenant_id,
        question="What is AX-4317?",
        retrieval_mode="standard",
    )

    assert calls["retrieve"] == 1
    assert "do not contain enough information" in result.answer


@pytest.mark.asyncio
async def test_rag_cache_hit_skips_pipeline(monkeypatch):
    fake_redis = FakeRedis()
    tenant_id = uuid4()
    calls = {"retrieve": 0}

    monkeypatch.setattr(
        "app.services.rag_cache_service.get_redis",
        lambda: fake_redis,
    )

    await set_cached_rag_result(
        tenant_id=tenant_id,
        question="What is AX-4317?",
        result=_sample_result("from cache"),
        limit=5,
        retrieval_mode="standard",
    )

    async def fake_retrieve(**kwargs):
        calls["retrieve"] += 1
        return []

    monkeypatch.setattr(
        "app.services.rag_service.retrieve_for_rag_mode",
        fake_retrieve,
    )

    result = await answer_question(
        tenant_id=tenant_id,
        question="What is AX-4317?",
        retrieval_mode="standard",
    )

    assert calls["retrieve"] == 0
    assert result.answer == "from cache"
    assert result.sources[0].filename == "manual.pdf"


@pytest.mark.asyncio
async def test_rag_cache_key_is_tenant_separated():
    tenant_a = uuid4()
    tenant_b = uuid4()

    key_a = build_rag_cache_key(
        tenant_a,
        "same question",
        version=0,
        retrieval_mode="standard",
        limit=5,
    )
    key_b = build_rag_cache_key(
        tenant_b,
        "same question",
        version=0,
        retrieval_mode="standard",
        limit=5,
    )

    assert key_a != key_b
    assert str(tenant_a) in key_a
    assert str(tenant_b) in key_b


@pytest.mark.asyncio
async def test_document_ingestion_increments_cache_version(monkeypatch):
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    monkeypatch.setattr(
        "app.services.rag_cache_service.get_redis",
        lambda: fake_redis,
    )

    assert await get_rag_cache_version(tenant_id) == 0

    await increment_rag_cache_version(tenant_id)
    assert await get_rag_cache_version(tenant_id) == 1

    await set_cached_rag_result(
        tenant_id=tenant_id,
        question="pressure loss?",
        result=_sample_result("v0 answer"),
        limit=5,
        retrieval_mode="standard",
    )

    await increment_rag_cache_version(tenant_id)

    cached = await get_cached_rag_result(
        tenant_id=tenant_id,
        question="pressure loss?",
        limit=5,
        retrieval_mode="standard",
    )
    assert cached is None


@pytest.mark.asyncio
async def test_redis_cache_failure_does_not_break_rag(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.fail_get = True
    fake_redis.fail_set = True
    tenant_id = uuid4()

    monkeypatch.setattr(
        "app.services.rag_cache_service.get_redis",
        lambda: fake_redis,
    )

    async def fake_retrieve(**kwargs):
        return []

    monkeypatch.setattr(
        "app.services.rag_service.retrieve_for_rag_mode",
        fake_retrieve,
    )

    result = await answer_question(
        tenant_id=tenant_id,
        question="What failed?",
        retrieval_mode="standard",
    )

    assert "do not contain enough information" in result.answer


@pytest.mark.asyncio
async def test_rate_limit_allows_below_limit(monkeypatch):
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    monkeypatch.setattr(
        "app.services.rate_limit_service.get_redis",
        lambda: fake_redis,
    )
    monkeypatch.setattr(
        "app.core.config.settings.redis_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.core.config.settings.agent_rate_limit_requests",
        3,
    )
    monkeypatch.setattr(
        "app.core.config.settings.agent_rate_limit_window_seconds",
        60,
    )

    assert await check_agent_rate_limit(tenant_id) is True
    assert await check_agent_rate_limit(tenant_id) is True
    assert await check_agent_rate_limit(tenant_id) is True


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_false(monkeypatch):
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    monkeypatch.setattr(
        "app.services.rate_limit_service.get_redis",
        lambda: fake_redis,
    )
    monkeypatch.setattr(
        "app.core.config.settings.redis_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.core.config.settings.agent_rate_limit_requests",
        2,
    )
    monkeypatch.setattr(
        "app.core.config.settings.agent_rate_limit_window_seconds",
        60,
    )

    assert await check_agent_rate_limit(tenant_id) is True
    assert await check_agent_rate_limit(tenant_id) is True
    assert await check_agent_rate_limit(tenant_id) is False


@pytest.mark.asyncio
async def test_rate_limit_redis_failure_fails_open(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.fail_incr = True
    tenant_id = uuid4()

    monkeypatch.setattr(
        "app.services.rate_limit_service.get_redis",
        lambda: fake_redis,
    )
    monkeypatch.setattr(
        "app.core.config.settings.redis_enabled",
        True,
    )

    assert await check_agent_rate_limit(tenant_id) is True


@pytest.mark.asyncio
async def test_agent_endpoint_returns_429_when_rate_limited(client, monkeypatch):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Rate Limit Tenant"},
    )
    tenant_id = tenant_response.json()["id"]

    async def deny_rate_limit(_tenant_id):
        return False

    monkeypatch.setattr(
        "app.api.v1.agent.check_agent_rate_limit",
        deny_rate_limit,
    )

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "Test agent request",
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
