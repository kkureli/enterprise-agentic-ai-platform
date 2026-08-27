"""Tests for high-risk → HITL GitHub escalation wiring."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents.a2a.github_escalation import (
    build_github_escalation_pending_action,
    github_escalation_dedupe_key,
)
from app.agents.a2a.pipeline import A2APipelineResult
from app.agents.a2a.schemas import (
    CompanyIntelligenceResult,
    EntityResolution,
    EvidenceItem,
    RiskAssessmentResult,
)
from app.agents.a2a_risk_node import a2a_risk_node
from app.agents.graph import finalize_node, route_after_a2a


def test_github_escalation_dedupe_key() -> None:
    assert (
        github_escalation_dedupe_key(
            tenant_slug="Northstar-Commercial",
            company_query="Microsoft",
            risk_level="high",
        )
        == "northstar-commercial:microsoft:external_risk:high"
    )
    assert (
        github_escalation_dedupe_key(
            tenant_slug="northstar-commercial",
            company_query="Microsoft",
            risk_level="medium",
        )
        == "northstar-commercial:microsoft:external_risk:medium"
    )


def test_build_github_escalation_pending_action() -> None:
    risk = RiskAssessmentResult(
        risk_level="medium",
        confidence=0.75,
        reasons=["at_risk signals"],
        recommended_actions=["Escalate"],
    )
    payload = build_github_escalation_pending_action(
        tenant_slug="northstar-commercial",
        company_query="Microsoft",
        risk=risk,
        assessment_answer="Risk level: medium",
        response_language="en",
    )
    assert payload["requires_approval"] is True
    assert payload["pending_action"]["tool_name"] == "create_github_issue"
    args = payload["pending_action"]["arguments"]
    assert args["tenant_slug"] == "northstar-commercial"
    assert args["dedupe_key"].endswith(":external_risk:medium")
    assert "[Risk:MEDIUM]" in args["title"]
    assert "MEDIUM risk detected" in payload["tool_answer"]


def test_route_after_a2a_prioritizes_synthesis_then_approval() -> None:
    assert (
        route_after_a2a({"requires_synthesis": True, "requires_approval": True})
        == "synthesize"
    )
    assert route_after_a2a({"requires_approval": True}) == "approval"
    assert route_after_a2a({}) == "finalize"


def test_finalize_keeps_a2a_answer_with_github_action() -> None:
    result = finalize_node(
        {
            "a2a_answer": "Risk level: high\nConfidence: 0.90",
            "tool_answer": "GitHub issue created successfully: https://example/issues/1",
            "action_result": {"external_url": "https://example/issues/1"},
            "approval_granted": True,
        }
    )
    assert "Risk level: high" in result["final_answer"]
    assert "GitHub issue created" in result["final_answer"]


@pytest.mark.asyncio
async def test_a2a_risk_node_requests_hitl_on_high(monkeypatch) -> None:
    async def fake_rag(**kwargs):
        return SimpleNamespace(answer="Contract note.")

    async def fake_pipeline(**kwargs):
        risk = RiskAssessmentResult(
            risk_level="high",
            confidence=0.91,
            reasons=["Account at_risk"],
            recommended_actions=["Open escalation"],
        )
        intel = CompanyIntelligenceResult(
            company_query="Microsoft",
            entity=EntityResolution(
                company_name="Microsoft",
                domain="microsoft.com",
                unresolved=False,
            ),
            search_queries=["Microsoft"],
            evidence=[EvidenceItem(summary="Public profile.", source_type="web")],
            findings=["Profile collected."],
            evidence_sufficient=True,
        )
        return A2APipelineResult(
            company_query="Microsoft",
            intelligence=intel,
            risk=risk,
            answer="Risk level: high\nConfidence: 0.91",
            a2a_follow_up_used=False,
        )

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "northstar-commercial",
            "query": "Assess Microsoft external risks.",
            "response_language": "en",
            "planned_routes": ["external_risk_assessment"],
        }
    )
    assert result["requires_approval"] is True
    assert result["pending_action"]["tool_name"] == "create_github_issue"
    assert result["a2a_answer"].startswith("Risk level: high")


@pytest.mark.asyncio
async def test_a2a_risk_node_requests_hitl_on_medium(monkeypatch) -> None:
    async def fake_rag(**kwargs):
        return SimpleNamespace(answer="Contract note.")

    async def fake_pipeline(**kwargs):
        risk = RiskAssessmentResult(
            risk_level="medium",
            confidence=0.75,
            reasons=["Account watch signals"],
            recommended_actions=["Monitor closely"],
        )
        intel = CompanyIntelligenceResult(
            company_query="Microsoft",
            entity=EntityResolution(
                company_name="Microsoft",
                domain="microsoft.com",
                unresolved=False,
            ),
            search_queries=["Microsoft"],
            evidence=[EvidenceItem(summary="Public profile.", source_type="web")],
            findings=["Profile collected."],
            evidence_sufficient=True,
        )
        return A2APipelineResult(
            company_query="Microsoft",
            intelligence=intel,
            risk=risk,
            answer="Risk level: medium\nConfidence: 0.75",
            a2a_follow_up_used=False,
        )

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "northstar-commercial",
            "query": "Assess Microsoft external risks.",
            "response_language": "en",
            "planned_routes": ["external_risk_assessment"],
        }
    )
    assert result["requires_approval"] is True
    assert result["pending_action"]["tool_name"] == "create_github_issue"
    assert "MEDIUM" in result["tool_answer"]


@pytest.mark.asyncio
async def test_a2a_medium_risk_reject_never_calls_github_mcp(monkeypatch):
    """Reject path must finalize without executing create_github_issue."""

    async def fake_planner(state):
        return {
            "route": "external_risk_assessment",
            "planned_routes": ["external_risk_assessment"],
            "requires_synthesis": False,
            "may_require_write": False,
            "tool_read_only": False,
            "execution_details": {
                "graph_path": ["planner"],
                "selected_capabilities": ["external_risk_assessment"],
                "route": "external_risk_assessment",
            },
        }

    async def fake_a2a(state):
        return {
            "a2a_answer": "Risk level: medium\nConfidence: 0.75",
            "a2a_risk_result": {"risk_level": "medium", "confidence": 0.75},
            "requires_approval": True,
            "pending_action": {
                "tool_name": "create_github_issue",
                "arguments": {
                    "title": "[Risk:MEDIUM] Microsoft",
                    "body": "Escalate",
                    "tenant_slug": "northstar-commercial",
                    "dedupe_key": "northstar-commercial:microsoft:external_risk:medium",
                    "company_query": "Microsoft",
                },
            },
            "tool_answer": "MEDIUM risk detected. Approval is required to open a GitHub Issue.",
            "execution_details": {"graph_path": ["a2a_risk"]},
        }

    mcp_calls = {"n": 0}

    async def fake_execute(tenant_id, pending_action):
        mcp_calls["n"] += 1
        raise AssertionError("approved_action must not run after reject")

    from app.agents import graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "a2a_risk_node", fake_a2a)
    monkeypatch.setattr(
        "app.agents.approved_action_node.execute_approved_action",
        fake_execute,
    )

    compiled = graph_module.build_agent_graph().compile(checkpointer=InMemorySaver())
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    first = await compiled.ainvoke(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "northstar-commercial",
            "query": "Assess Microsoft external risks.",
            "retrieval_mode": "standard",
            "response_language": "en",
        },
        config=config,
    )
    assert "__interrupt__" in first or first.get("requires_approval")

    # Resume with explicit reject.
    result = await compiled.ainvoke(
        Command(resume={"approved": False}),
        config=config,
    )
    assert mcp_calls["n"] == 0
    assert result.get("approval_granted") is False
    assert "rejected" in result["final_answer"].lower() or "reddedildi" in result[
        "final_answer"
    ].lower()
    assert "Risk level: medium" in result["final_answer"]


@pytest.mark.asyncio
async def test_a2a_medium_risk_approve_calls_github_executor(monkeypatch):
    async def fake_planner(state):
        return {
            "route": "external_risk_assessment",
            "planned_routes": ["external_risk_assessment"],
            "requires_synthesis": False,
            "may_require_write": False,
            "tool_read_only": False,
            "execution_details": {
                "graph_path": ["planner"],
                "route": "external_risk_assessment",
            },
        }

    async def fake_a2a(state):
        return {
            "a2a_answer": "Risk level: medium\nConfidence: 0.75",
            "requires_approval": True,
            "pending_action": {
                "tool_name": "create_github_issue",
                "arguments": {
                    "title": "[Risk:MEDIUM] Microsoft",
                    "body": "Escalate",
                    "tenant_slug": "northstar-commercial",
                    "dedupe_key": "northstar-commercial:microsoft:external_risk:medium",
                    "company_query": "Microsoft",
                    "risk_level": "medium",
                },
            },
            "tool_answer": "MEDIUM risk detected.",
            "execution_details": {"graph_path": ["a2a_risk"]},
        }

    async def fake_execute(tenant_id, pending_action):
        assert pending_action["tool_name"] == "create_github_issue"
        return {
            "tool_name": "create_github_issue",
            "deduplicated": False,
            "external_url": "https://github.com/kkureli/enterprise-agentic-ai-platform/issues/99",
            "external_id": "99",
            "risk_escalation_id": str(uuid4()),
            "provider": "github",
            "status": "open",
        }

    from app.agents import graph as graph_module

    monkeypatch.setattr(graph_module, "planner_node", fake_planner)
    monkeypatch.setattr(graph_module, "a2a_risk_node", fake_a2a)
    monkeypatch.setattr(
        "app.agents.approved_action_node.execute_approved_action",
        fake_execute,
    )

    compiled = graph_module.build_agent_graph().compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": str(uuid4())}}
    await compiled.ainvoke(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "northstar-commercial",
            "query": "Assess Microsoft external risks.",
            "retrieval_mode": "standard",
            "response_language": "en",
        },
        config=config,
    )
    result = await compiled.ainvoke(Command(resume={"approved": True}), config=config)
    assert result.get("approval_granted") is True
    assert "issues/99" in result["final_answer"]
    assert "Risk level: medium" in result["final_answer"]


@pytest.mark.asyncio
async def test_a2a_risk_node_skips_hitl_on_low(monkeypatch) -> None:
    async def fake_rag(**kwargs):
        return SimpleNamespace(answer=None)

    async def fake_pipeline(**kwargs):
        risk = RiskAssessmentResult(
            risk_level="low",
            confidence=0.6,
            reasons=["Healthy signals"],
            recommended_actions=["Continue monitoring"],
        )
        return A2APipelineResult(
            company_query="Spotify",
            intelligence=None,
            risk=risk,
            answer="Risk level: low",
            a2a_follow_up_used=False,
        )

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "tenant_slug": "northstar-commercial",
            "query": "Spotify risk",
            "response_language": "en",
            "planned_routes": ["external_risk_assessment"],
        }
    )
    assert "requires_approval" not in result
    assert "pending_action" not in result
