import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "development"


@pytest.mark.asyncio
async def test_ready_reports_degraded_when_redis_down(client, monkeypatch):
    async def postgres_ok():
        return True

    async def qdrant_ok():
        return True

    async def redis_down():
        return False

    monkeypatch.setattr("app.main.check_postgres", postgres_ok)
    monkeypatch.setattr("app.main.check_qdrant", qdrant_ok)
    monkeypatch.setattr("app.main.check_redis", redis_down)
    monkeypatch.setattr("app.core.config.settings.redis_enabled", True)

    response = await client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["degraded"] is True
    assert data["services"]["postgres"] is True
    assert data["services"]["qdrant"] is True
    assert data["services"]["redis"] is False
