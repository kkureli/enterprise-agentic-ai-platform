"""Focused tests for multi-capability orchestration."""

from __future__ import annotations

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.execution_trace import merge_execution_details
from app.agents.graph import (
    after_capability,
    route_after_planner,
    route_after_tool,
)
from app.agents.router import RoutePlan, finalize_plan, normalize_planned_routes
from app.services.mcp_client import call_maintenance_tool


def test_normalize_planned_routes_dedupes_and_drops_unsupported_mix():
    assert normalize_planned_routes(["knowledge", "knowledge", "tool"]) == [
        "knowledge",
        "tool",
    ]
    assert normalize_planned_routes(["unsupported", "sql"]) == ["sql"]
    assert normalize_planned_routes(["unsupported"]) == ["unsupported"]
    assert normalize_planned_routes([]) == ["unsupported"]


def test_finalize_plan_sets_synthesis_for_multi_route():
    plan = finalize_plan(RoutePlan(routes=["knowledge", "sql", "tool"], requires_synthesis=False))
    assert plan.routes == ["knowledge", "sql", "tool"]
    assert plan.requires_synthesis is True


def test_route_after_planner_single_fast_path():
    assert (
        route_after_planner(
            {
                "planned_routes": ["knowledge"],
                "requires_synthesis": False,
            }
        )
        == "rag"
    )
    assert (
        route_after_planner(
            {
                "planned_routes": ["unsupported"],
            }
        )
        == "fallback"
    )


def test_route_after_planner_fanout_sends():
    sends = route_after_planner(
        {
            "planned_routes": ["knowledge", "sql", "tool"],
            "requires_synthesis": True,
            "tool_read_only": True,
            "query": "composite",
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
        }
    )
    assert isinstance(sends, list)
    assert [send.node for send in sends] == ["rag", "sql", "tool"]


def test_after_capability_and_tool_routing():
    assert after_capability({"requires_synthesis": True}) == "synthesize"
    assert after_capability({"requires_synthesis": False}) == "finalize"
    assert route_after_tool({"requires_approval": True, "requires_synthesis": True}) == "approval"
    assert route_after_tool({"requires_synthesis": True}) == "synthesize"
    assert route_after_tool({}) == "finalize"


def test_merge_preserves_multi_capability_sections():
    left = {
        "graph_path": ["planner"],
        "selected_capabilities": ["knowledge", "sql"],
        "route": "knowledge",
        "retrieval": {"strategy": "hybrid"},
        "timing": {"planner_ms": 10.0},
    }
    right = {
        "graph_path": ["sql"],
        "selected_capabilities": ["sql"],
        "route": "sql",
        "sql": {"row_count": 2, "validation_status": "passed"},
        "timing": {"sql_execution_ms": 5.0},
    }
    merged = merge_execution_details(left, right)
    assert merged["retrieval"]["strategy"] == "hybrid"
    assert merged["sql"]["row_count"] == 2
    assert merged["selected_capabilities"] == ["knowledge", "sql"]
    assert merged["route"] == "knowledge"
    assert merged["graph_path"] == ["planner", "sql"]
    assert merged["timing"]["planner_ms"] == 10.0
    assert merged["timing"]["sql_execution_ms"] == 5.0


@pytest.mark.asyncio
async def test_mcp_read_requires_tenant_slug():
    with pytest.raises(ValueError, match="tenant_slug"):
        await call_maintenance_tool("get_asset_status", {"asset_id": "MACHINE-42"})


@pytest.mark.asyncio
async def test_mcp_read_is_tenant_scoped():
    atlas = await call_maintenance_tool(
        "get_asset_status",
        {"asset_id": "MACHINE-42"},
        tenant_slug="atlas-manufacturing",
    )
    borealis = await call_maintenance_tool(
        "get_asset_status",
        {"asset_id": "MACHINE-42"},
        tenant_slug="borealis-cold-chain",
    )
    atlas_payload = atlas.structured_content
    borealis_payload = borealis.structured_content
    assert atlas_payload["status"] == "warning"
    assert atlas_payload["tenant_slug"] == "atlas-manufacturing"
    assert borealis_payload["status"] == "unknown"
    assert borealis_payload["tenant_slug"] == "borealis-cold-chain"


@pytest.mark.asyncio
async def test_composite_graph_fanout_synthesis_and_trace(monkeypatch):
    async def fake_planner(state):
        return {
            "route": "knowledge",
            "planned_routes": ["knowledge", "sql", "tool"],
            "requires_synthesis": True,
            "may_require_write": False,
            "tool_read_only": True,
            "execution_details": {
                "graph_path": ["planner"],
                "selected_capabilities": ["knowledge", "sql", "tool"],
                "route": "knowledge",
            },
        }

    async def fake_rag(state):
        return {
            "rag_answer": "E-100 means lubrication pressure below threshold.",
            "execution_details": {
                "graph_path": ["rag"],
                "retrieval": {"strategy": "hybrid", "retrieval_mode": "standard"},
                "sources": [],
            },
        }

    async def fake_sql(state):
        return {
            "sql_answer": "MACHINE-42 has 2 related maintenance records.",
            "generated_sql": "SELECT 1",
            "execution_details": {
                "graph_path": ["sql"],
                "sql": {
                    "generated_sql": "SELECT 1",
                    "validation_status": "passed",
                    "row_count": 2,
                    "tenant_scope_verified": True,
                    "read_only_verified": True,
                },
            },
        }

    async def fake_tool(state):
        assert state.get("tool_read_only") is True
        return {
            "tool_answer": "MACHINE-42 is currently in warning state.",
            "execution_details": {
                "graph_path": ["tool"],
                "tools": {
                    "mcp_server": "maintenance",
                    "tool_name": "get_asset_status",
                    "tool_type": "read",
                    "tenant_slug": state["tenant_slug"],
                },
            },
        }

    async def fake_synthesis(state):
        assert state.get("rag_answer")
        assert state.get("sql_answer")
        assert state.get("tool_answer")
        return {
            "synthesis_answer": (
                "E-100 is a lubrication pressure issue; MACHINE-42 has prior "
                "maintenance history and is currently in warning."
            ),
            "execution_details": {"graph_path": ["synthesize"]},
        }

    monkeypatch.setattr("app.agents.graph.planner_node", fake_planner)
    monkeypatch.setattr("app.agents.graph.rag_node", fake_rag)
    monkeypatch.setattr("app.agents.graph.sql_node", fake_sql)
    monkeypatch.setattr("app.agents.graph.mcp_tool_node", fake_tool)
    monkeypatch.setattr("app.agents.graph.synthesis_node", fake_synthesis)

    # Rebuild graph with patched callables by re-importing build after patch.
    from app.agents import graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "rag_node", fake_rag)
    monkeypatch.setattr(graph_module, "sql_node", fake_sql)
    monkeypatch.setattr(graph_module, "mcp_tool_node", fake_tool)
    monkeypatch.setattr(graph_module, "synthesis_node", fake_synthesis)

    builder = graph_module.build_agent_graph()
    compiled = builder.compile(checkpointer=InMemorySaver())

    tenant_id = uuid4()
    result = await compiled.ainvoke(
        {
            "tenant_id": tenant_id,
            "tenant_slug": "atlas-manufacturing",
            "query": (
                "What does E-100 mean, has MACHINE-42 had related maintenance "
                "issues before, and what is its current operational status?"
            ),
            "retrieval_mode": "standard",
        },
        config={"configurable": {"thread_id": str(uuid4())}},
    )

    assert result["requires_synthesis"] is True
    assert set(result["planned_routes"]) == {"knowledge", "sql", "tool"}
    assert "E-100" in result["final_answer"] or "lubrication" in result["final_answer"].lower()
    path = result["execution_details"]["graph_path"]
    assert "planner" in path
    assert "rag" in path
    assert "sql" in path
    assert "tool" in path
    assert "synthesize" in path
    assert "finalize" in path
    assert result["execution_details"]["retrieval"]["strategy"] == "hybrid"
    assert result["execution_details"]["sql"]["row_count"] == 2
    assert result["execution_details"]["tools"]["tool_name"] == "get_asset_status"


@pytest.mark.asyncio
async def test_single_route_skips_synthesis(monkeypatch):
    async def fake_planner(state):
        return {
            "route": "knowledge",
            "planned_routes": ["knowledge"],
            "requires_synthesis": False,
            "may_require_write": False,
            "tool_read_only": False,
            "execution_details": {
                "graph_path": ["planner"],
                "selected_capabilities": ["knowledge"],
                "route": "knowledge",
            },
        }

    async def fake_rag(state):
        return {
            "rag_answer": "AX-4317 indicates hydraulic pressure loss.",
            "execution_details": {"graph_path": ["rag"]},
        }

    called = {"synthesis": 0}

    async def fake_synthesis(state):
        called["synthesis"] += 1
        return {"synthesis_answer": "should not run"}

    from app.agents import graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "rag_node", fake_rag)
    monkeypatch.setattr(graph_module, "synthesis_node", fake_synthesis)

    compiled = graph_module.build_agent_graph().compile(checkpointer=InMemorySaver())
    result = await compiled.ainvoke(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
            "query": "What does AX-4317 mean?",
            "retrieval_mode": "standard",
        },
        config={"configurable": {"thread_id": str(uuid4())}},
    )
    assert called["synthesis"] == 0
    assert result["final_answer"] == "AX-4317 indicates hydraulic pressure loss."
    assert "synthesize" not in result["execution_details"]["graph_path"]


@pytest.mark.asyncio
async def test_hitl_after_composite_write_gate(monkeypatch):
    async def fake_planner(state):
        return {
            "route": "knowledge",
            "planned_routes": ["knowledge", "sql", "tool"],
            "requires_synthesis": True,
            "may_require_write": True,
            "tool_read_only": True,
            "execution_details": {
                "graph_path": ["planner"],
                "selected_capabilities": ["knowledge", "sql", "tool"],
            },
        }

    async def fake_rag(state):
        return {
            "rag_answer": "Procedure says isolate and inspect.",
            "execution_details": {"graph_path": ["rag"]},
        }

    async def fake_sql(state):
        return {
            "sql_answer": "Two prior corrective records.",
            "execution_details": {"graph_path": ["sql"]},
        }

    async def fake_tool(state):
        return {"tool_answer": "Status warning.", "execution_details": {"graph_path": ["tool"]}}

    async def fake_synthesis(state):
        return {
            "synthesis_answer": "Intervention is warranted based on evidence.",
            "execution_details": {"graph_path": ["synthesize"]},
        }

    async def fake_write_gate(state):
        return {
            "requires_approval": True,
            "pending_action": {
                "tool_name": "create_maintenance_ticket",
                "arguments": {
                    "asset_code": "MACHINE-42",
                    "issue": "Hydraulic pressure loss",
                    "priority": "high",
                },
            },
            "tool_answer": "This action requires human approval before execution.",
            "execution_details": {"graph_path": ["write_gate"]},
        }

    from app.agents import graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "rag_node", fake_rag)
    monkeypatch.setattr(graph_module, "sql_node", fake_sql)
    monkeypatch.setattr(graph_module, "mcp_tool_node", fake_tool)
    monkeypatch.setattr(graph_module, "synthesis_node", fake_synthesis)
    monkeypatch.setattr(graph_module, "write_gate_node", fake_write_gate)

    compiled = graph_module.build_agent_graph().compile(checkpointer=InMemorySaver())
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = await compiled.ainvoke(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "atlas-manufacturing",
            "query": (
                "Based on MACHINE-42 status, history, and procedure, create a "
                "maintenance ticket if intervention is required."
            ),
            "retrieval_mode": "standard",
        },
        config=config,
    )
    assert result.get("__interrupt__")
    assert result["pending_action"]["tool_name"] == "create_maintenance_ticket"
    assert result.get("rag_answer")
    assert result.get("sql_answer")
    assert result.get("tool_answer")
    assert result.get("synthesis_answer")

    from langgraph.types import Command

    # Reject path
    rejected = await compiled.ainvoke(
        Command(resume={"approved": False}),
        config=config,
    )
    assert rejected["final_answer"] == "The action was rejected by the user."
    assert rejected.get("synthesis_answer")
