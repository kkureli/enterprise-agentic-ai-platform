from uuid import UUID

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
            "tool",
            "MACHINE-42 is currently in warning state.",
        ),
        (
            "unsupported",
            "This request is not supported yet.",
        ),
        (
            "sql",
            "MACHINE-42 has 2 maintenance records.",
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
        async def ainvoke(self, state, config=None):
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

    assert data["status"] == "completed"
    assert data["route"] == route
    assert data["answer"] == answer
    assert data["thread_id"]
    assert data["pending_action"] is None


@pytest.mark.asyncio
async def test_agent_write_action_requires_approval(
    client,
    monkeypatch,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Agent Approval Tenant"},
    )
    tenant_id = tenant_response.json()["id"]

    pending_action = {
        "tool_name": "create_maintenance_ticket",
        "arguments": {
            "asset_code": "MACHINE-42",
            "issue": "Hydraulic pressure loss",
            "priority": "high",
        },
    }

    class FakeGraph:
        async def ainvoke(self, state, config=None):
            return {
                **state,
                "route": "tool",
                "requires_approval": True,
                "pending_action": pending_action,
                "tool_answer": ("This action requires human approval before execution."),
                "__interrupt__": [object()],
            }

    monkeypatch.setattr(
        "app.api.v1.agent.agent_graph",
        FakeGraph(),
    )

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/agent",
        json={
            "question": ("Create a high-priority maintenance ticket for MACHINE-42."),
            "retrieval_mode": "standard",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "approval_required"
    assert data["route"] == "tool"
    assert data["thread_id"]
    assert data["pending_action"] == pending_action


@pytest.mark.asyncio
async def test_agent_approval_resumes_execution(
    client,
    monkeypatch,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Agent Resume Tenant"},
    )
    tenant_id = tenant_response.json()["id"]

    class FakeSnapshot:
        values = {
            "tenant_id": UUID(tenant_id),
        }
        next = ("approval",)

    class FakeGraph:
        async def aget_state(self, config):
            return FakeSnapshot()

        async def ainvoke(self, command, config=None):
            return {
                "route": "tool",
                "final_answer": ("Maintenance ticket was created successfully."),
            }

    monkeypatch.setattr(
        "app.api.v1.agent.agent_graph",
        FakeGraph(),
    )

    thread_id = "test-approval-thread"

    response = await client.post(
        (f"/api/v1/tenants/{tenant_id}/agent/{thread_id}/approval"),
        json={
            "approved": True,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["thread_id"] == thread_id
    assert data["status"] == "completed"
    assert data["route"] == "tool"
    assert data["answer"] == "Maintenance ticket was created successfully."


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
        async def ainvoke(self, state, config=None):
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
