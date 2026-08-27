"""Tests for high-risk → HITL GitHub escalation wiring."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

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
        )
        == "northstar-commercial:microsoft:external_risk:high"
    )


def test_build_github_escalation_pending_action() -> None:
    risk = RiskAssessmentResult(
        risk_level="high",
        confidence=0.9,
        reasons=["at_risk"],
        recommended_actions=["Escalate"],
    )
    payload = build_github_escalation_pending_action(
        tenant_slug="northstar-commercial",
        company_query="Microsoft",
        risk=risk,
        assessment_answer="Risk level: high",
        response_language="en",
    )
    assert payload["requires_approval"] is True
    assert payload["pending_action"]["tool_name"] == "create_github_issue"
    args = payload["pending_action"]["arguments"]
    assert args["tenant_slug"] == "northstar-commercial"
    assert args["dedupe_key"].endswith(":external_risk:high")
    assert "Microsoft" in args["title"]


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
async def test_a2a_risk_node_skips_hitl_on_medium(monkeypatch) -> None:
    async def fake_rag(**kwargs):
        return SimpleNamespace(answer=None)

    async def fake_pipeline(**kwargs):
        risk = RiskAssessmentResult(
            risk_level="medium",
            confidence=0.6,
            reasons=["Limited signals"],
            recommended_actions=["Monitor"],
        )
        return A2APipelineResult(
            company_query="Spotify",
            intelligence=None,
            risk=risk,
            answer="Risk level: medium",
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
