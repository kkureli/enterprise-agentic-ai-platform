"""Focused tests for public-demo cost protections and portfolio demo APIs."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.agent import AgentRequest
from app.services.client_identity import LimitDecision
from app.services.evaluation_summary import load_evaluation_summary
from app.services.rate_limit_service import (
    check_client_rate_limit,
    check_compare_rate_limit,
    check_daily_ai_budget,
    check_global_ai_rate_limit,
    check_tenant_rate_limit,
    check_write_rate_limit,
)


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.fail_incr = False
        self.fail_get = False

    async def get(self, key: str):
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.store.get(key)

    async def incr(self, key: str) -> int:
        if self.fail_incr:
            raise RuntimeError("redis incr failed")
        current = int(self.store.get(key, "0")) + 1
        self.store[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        return True


def _patch_redis(monkeypatch, fake: FakeRedis) -> None:
    monkeypatch.setattr(
        "app.services.rate_limit_service.get_redis",
        lambda: fake,
    )
    monkeypatch.setattr("app.core.config.settings.redis_enabled", True)


@pytest.mark.asyncio
async def test_client_rate_limit_exceeded(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.client_rate_limit_requests", 2)
    monkeypatch.setattr("app.core.config.settings.client_rate_limit_window_seconds", 60)

    assert (await check_client_rate_limit("abc")).allowed
    assert (await check_client_rate_limit("abc")).allowed
    denied = await check_client_rate_limit("abc")
    assert denied.allowed is False
    assert denied.status_code == 429
    assert denied.retry_after_seconds is not None


@pytest.mark.asyncio
async def test_tenant_rate_limit_still_works(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.agent_rate_limit_requests", 1)
    monkeypatch.setattr("app.core.config.settings.agent_rate_limit_window_seconds", 60)
    tenant_id = uuid4()

    assert (await check_tenant_rate_limit(tenant_id)).allowed
    denied = await check_tenant_rate_limit(tenant_id)
    assert denied.allowed is False


@pytest.mark.asyncio
async def test_global_ai_rate_limit(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.global_ai_rate_limit_requests", 2)
    monkeypatch.setattr("app.core.config.settings.global_ai_rate_limit_window_seconds", 3600)

    assert (await check_global_ai_rate_limit(units=1)).allowed
    assert (await check_global_ai_rate_limit(units=1)).allowed
    denied = await check_global_ai_rate_limit(units=1)
    assert denied.allowed is False


@pytest.mark.asyncio
async def test_compare_rate_limit_stricter(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.compare_rate_limit_requests", 1)
    monkeypatch.setattr("app.core.config.settings.compare_rate_limit_window_seconds", 300)

    assert (await check_compare_rate_limit("cmp")).allowed
    denied = await check_compare_rate_limit("cmp")
    assert denied.allowed is False
    assert "Compare" in (denied.reason or "")


@pytest.mark.asyncio
async def test_write_rate_limit(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.demo_write_rate_limit_requests", 1)
    monkeypatch.setattr("app.core.config.settings.demo_write_rate_limit_window_seconds", 3600)

    assert (await check_write_rate_limit("writer")).allowed
    denied = await check_write_rate_limit("writer")
    assert denied.allowed is False


@pytest.mark.asyncio
async def test_daily_budget_exceeded(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.demo_daily_ai_request_limit", 1)
    monkeypatch.setattr("app.core.config.settings.public_demo_mode", True)

    assert (await check_daily_ai_budget(units=1)).allowed
    denied = await check_daily_ai_budget(units=1)
    assert denied.allowed is False
    assert "today" in (denied.reason or "").lower()


@pytest.mark.asyncio
async def test_daily_budget_fail_closed_in_public_demo(monkeypatch):
    fake = FakeRedis()
    fake.fail_incr = True
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.public_demo_mode", True)

    denied = await check_daily_ai_budget(units=1)
    assert denied.allowed is False
    assert denied.status_code == 503


@pytest.mark.asyncio
async def test_daily_budget_fail_open_outside_public_demo(monkeypatch):
    fake = FakeRedis()
    fake.fail_incr = True
    _patch_redis(monkeypatch, fake)
    monkeypatch.setattr("app.core.config.settings.public_demo_mode", False)

    allowed = await check_daily_ai_budget(units=1)
    assert allowed.allowed is True


def test_oversized_prompt_rejected_before_agent():
    with pytest.raises(ValidationError):
        AgentRequest(question="x" * 2001, retrieval_mode="standard")


@pytest.mark.asyncio
async def test_agent_endpoint_returns_429_when_tenant_limited(client, monkeypatch):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Rate Limit Tenant"},
    )
    tenant_id = tenant_response.json()["id"]

    async def deny_tenant(_tenant_id, **_kwargs):
        return LimitDecision(
            allowed=False,
            retry_after_seconds=42,
            reason="Tenant demo request limit reached. Try again shortly.",
            status_code=429,
        )

    async def allow(*_args, **_kwargs):
        return LimitDecision(allowed=True)

    monkeypatch.setattr("app.api.v1.agent.check_tenant_rate_limit", deny_tenant)
    monkeypatch.setattr("app.api.v1.agent.check_client_rate_limit", allow)
    monkeypatch.setattr("app.api.v1.agent.check_global_ai_rate_limit", allow)
    monkeypatch.setattr("app.api.v1.agent.check_daily_ai_budget", allow)

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "Test agent request",
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "42"
    assert "limit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oversized_prompt_http_validation(client):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Prompt Size Tenant"},
    )
    tenant_id = tenant_response.json()["id"]

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "q" * 2001,
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_evaluations_endpoint_sanitized(client):
    response = await client.get("/api/v1/demo/evaluations")
    assert response.status_code == 200
    data = response.json()

    assert "disclaimer" in data
    assert data["agent"]["total_cases"] == 33
    assert data["agent"]["route_accuracy"] == 1.0
    assert data["agent"]["required_capability_recall"] == 1.0
    assert data["agent"]["composite_cases"] == 9
    assert "strategies" in data["retrieval"]
    serialized = str(data).lower()
    assert "azure" not in serialized
    assert "api_key" not in serialized
    assert "prompt" not in serialized


@pytest.mark.asyncio
async def test_system_status_exposes_no_secrets(client, monkeypatch):
    async def ok():
        return True

    monkeypatch.setattr("app.api.v1.demo.check_postgres", ok)
    monkeypatch.setattr("app.api.v1.demo.check_qdrant", ok)
    monkeypatch.setattr("app.api.v1.demo.check_redis", ok)
    monkeypatch.setattr("app.core.config.settings.redis_enabled", True)
    monkeypatch.setattr(
        "app.core.config.settings.azure_openai_endpoint",
        "https://example.openai.azure.com",
    )
    monkeypatch.setattr(
        "app.core.config.settings.azure_openai_deployment",
        "gpt-demo",
    )

    response = await client.get("/api/v1/demo/status")
    assert response.status_code == 200
    body = response.text.lower()
    assert "postgresql+asyncpg" not in body
    assert "redis://" not in body
    assert "api_key" not in body
    assert "openai.azure.com" not in body
    data = response.json()
    names = {item["name"] for item in data["components"]}
    assert {"Backend", "PostgreSQL", "Qdrant", "Redis", "AI service"} <= names


def test_evaluation_summary_matches_packaged_metrics():
    summary = load_evaluation_summary()
    assert summary.agent.total_cases == 33
    assert summary.agent.route_accuracy == 1.0
    assert summary.agent.required_capability_recall == 1.0
    assert summary.agent.composite_cases == 9
    assert summary.retrieval.num_queries == 15
    assert any(s.name == "Hybrid" for s in summary.retrieval.strategies)
