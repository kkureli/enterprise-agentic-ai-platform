"""Unit tests for the A2A risk LangGraph node."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.a2a.pipeline import A2APipelineResult
from app.agents.a2a.schemas import (
    CompanyIntelligenceResult,
    EntityResolution,
    EvidenceItem,
    RiskAssessmentResult,
)
from app.agents.a2a_risk_node import a2a_risk_node


def _pipeline_result(*, answer: str = "Risk level: medium\nConfidence: 0.80") -> A2APipelineResult:
    intel = CompanyIntelligenceResult(
        company_query="Microsoft",
        entity=EntityResolution(
            company_name="Microsoft",
            domain="microsoft.com",
            unresolved=False,
        ),
        search_queries=["Microsoft risk"],
        evidence=[EvidenceItem(summary="Public profile.", source_type="web")],
        findings=["Profile collected."],
        evidence_sufficient=True,
    )
    risk = RiskAssessmentResult(
        risk_level="medium",
        confidence=0.8,
        reasons=["Limited public risk signals"],
        recommended_actions=["Monitor"],
        needs_more_evidence=False,
    )
    return A2APipelineResult(
        company_query="Microsoft",
        intelligence=intel,
        risk=risk,
        answer=answer,
        a2a_follow_up_used=False,
    )


@pytest.mark.asyncio
async def test_a2a_risk_node_maps_pipeline_to_state(monkeypatch) -> None:
    called = {"rag": 0}

    async def fake_rag(**kwargs):
        called["rag"] += 1
        return SimpleNamespace(answer="MSA termination note.")

    async def fake_pipeline(**kwargs):
        assert kwargs["question"] == "Assess Microsoft external risks."
        assert kwargs["response_language"] == "en"
        assert kwargs["rag_answer"] == "MSA termination note."
        return _pipeline_result()

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "query": "Assess Microsoft external risks.",
            "response_language": "en",
            "planned_routes": ["external_risk_assessment"],
        }
    )
    assert called["rag"] == 1
    assert result["a2a_answer"].startswith("Risk level: medium")
    assert result["rag_answer"] == "MSA termination note."
    assert result["a2a_risk_result"]["risk_level"] == "medium"
    assert result["execution_details"]["a2a"]["rag_context_used"] is True


@pytest.mark.asyncio
async def test_a2a_risk_node_skips_rag_when_knowledge_also_planned(monkeypatch) -> None:
    called = {"rag": 0}

    async def fake_rag(**kwargs):
        called["rag"] += 1
        return SimpleNamespace(answer="should not run")

    async def fake_pipeline(**kwargs):
        assert kwargs["rag_answer"] is None
        return _pipeline_result()

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "query": "Evaluate Spotify with contracts and external risks.",
            "response_language": "en",
            "planned_routes": ["sql", "knowledge", "external_risk_assessment"],
        }
    )
    assert called["rag"] == 0
    assert "rag_answer" not in result
    assert result["execution_details"]["a2a"]["rag_context_used"] is False


@pytest.mark.asyncio
async def test_a2a_risk_node_reuses_existing_rag_answer(monkeypatch) -> None:
    called = {"rag": 0}

    async def fake_rag(**kwargs):
        called["rag"] += 1
        return SimpleNamespace(answer="should not run")

    async def fake_pipeline(**kwargs):
        assert kwargs["rag_answer"] == "Existing RAG evidence."
        return _pipeline_result()

    monkeypatch.setattr("app.agents.a2a_risk_node.answer_question", fake_rag)
    monkeypatch.setattr(
        "app.agents.a2a_risk_node.run_a2a_external_risk_pipeline",
        fake_pipeline,
    )

    result = await a2a_risk_node(
        {
            "tenant_id": uuid4(),
            "query": "Assess Microsoft external risks.",
            "response_language": "en",
            "planned_routes": ["external_risk_assessment"],
            "rag_answer": "Existing RAG evidence.",
        }
    )
    assert called["rag"] == 0
    assert "rag_answer" not in result
    assert result["execution_details"]["a2a"]["rag_context_used"] is True
