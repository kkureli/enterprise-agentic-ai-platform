import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route", "answer"),
    [
        (
            "knowledge",
            "AX-4317 indicates hydraulic pressure loss.",
        ),
        (
            "unsupported",
            "This request is not supported yet.",
        ),
    ],
)
async def test_agent_returns_graph_result(
    client,
    monkeypatch,
    route,
    answer,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": f"Agent {route} Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    class FakeGraph:
        async def ainvoke(self, state):
            return {
                **state,
                "route": route,
                "final_answer": answer,
            }

    monkeypatch.setattr(
        "app.api.v1.agent.agent_graph",
        FakeGraph(),
    )

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "Test agent request",
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == route
    assert data["answer"] == answer


@pytest.mark.asyncio
async def test_agent_invalid_retrieval_mode_returns_422(
    client,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Agent Validation Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "What does AX-4317 mean?",
            "retrieval_mode": "experimental",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_execution_failure_returns_503(
    client,
    monkeypatch,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Agent Failure Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    class FailingGraph:
        async def ainvoke(self, state):
            raise RuntimeError("Simulated graph failure")

    monkeypatch.setattr(
        "app.api.v1.agent.agent_graph",
        FailingGraph(),
    )

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": "What does AX-4317 mean?",
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Agent execution failed."
