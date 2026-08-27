from uuid import uuid4

import pytest

from app.agents.a2a.risk_agent import run_risk_assessment
from app.agents.a2a.schemas import (
    A2AFollowUpTask,
    CompanyIntelligenceResult,
    EntityResolution,
    EvidenceItem,
    RiskAssessmentResult,
)


@pytest.mark.asyncio
async def test_risk_agent_a2a_follow_up_then_final_assessment(monkeypatch) -> None:
    async def fake_internal(*, tenant_id, company_query):
        return [
            EvidenceItem(
                summary="Account Microsoft health=at_risk score=42.",
                source_type="sql",
                source_title="companies.account_health",
                confidence=0.95,
            )
        ]

    assessments = {
        "calls": 0,
    }

    async def fake_assess(**kwargs):
        assessments["calls"] += 1
        if assessments["calls"] == 1:
            return RiskAssessmentResult(
                risk_level="high",
                confidence=0.6,
                reasons=["Internal account is at_risk but external context is missing."],
                recommended_actions=["Gather financing developments."],
                needs_more_evidence=True,
                follow_up_task=A2AFollowUpTask(
                    from_agent="risk",
                    to_agent="company_intelligence",
                    task="Research financing developments in the last 12 months.",
                    company_query="Microsoft",
                    reason="External evidence insufficient.",
                ),
            )
        return RiskAssessmentResult(
            risk_level="high",
            confidence=0.91,
            reasons=["Late payments plus adverse external financing signals."],
            recommended_actions=["Escalate with HITL approval."],
            needs_more_evidence=False,
            follow_up_task=None,
        )

    async def fake_intelligence(**kwargs):
        assert "financing" in (kwargs.get("research_focus") or "").lower()
        return CompanyIntelligenceResult(
            company_query="Microsoft",
            entity=EntityResolution(
                company_name="Microsoft",
                domain="microsoft.com",
                internal_customer_id="CUST-MICROSOFT",
                unresolved=False,
            ),
            search_queries=["Microsoft financing 2025"],
            evidence=[
                EvidenceItem(
                    summary="Public demo evidence about financing posture.",
                    source_type="web",
                    confidence=0.7,
                )
            ],
            findings=["Additional financing context collected via A2A."],
            evidence_sufficient=True,
        )

    monkeypatch.setattr(
        "app.agents.a2a.risk_agent.collect_internal_company_evidence",
        fake_internal,
    )
    monkeypatch.setattr("app.agents.a2a.risk_agent._assess_risk", fake_assess)
    monkeypatch.setattr(
        "app.agents.a2a.risk_agent.run_company_intelligence",
        fake_intelligence,
    )

    risk, intelligence, follow_up_used = await run_risk_assessment(
        tenant_id=uuid4(),
        company_query="Microsoft",
        question="Assess Microsoft external and internal risk.",
        allow_a2a_follow_up=True,
    )

    assert assessments["calls"] == 2
    assert intelligence is not None
    assert intelligence.findings
    assert risk.risk_level == "high"
    assert risk.confidence == 0.91
    assert risk.needs_more_evidence is False
    assert follow_up_used is True


@pytest.mark.asyncio
async def test_risk_agent_skips_follow_up_when_disabled(monkeypatch) -> None:
    async def fake_internal(*, tenant_id, company_query):
        return []

    async def fake_assess(**kwargs):
        return RiskAssessmentResult(
            risk_level="medium",
            confidence=0.5,
            reasons=["Thin evidence."],
            recommended_actions=[],
            needs_more_evidence=True,
            follow_up_task=A2AFollowUpTask(
                from_agent="risk",
                to_agent="company_intelligence",
                task="Need more research",
                company_query="Spotify",
            ),
        )

    called = {"intel": False}

    async def fake_intelligence(**kwargs):
        called["intel"] = True
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        "app.agents.a2a.risk_agent.collect_internal_company_evidence",
        fake_internal,
    )
    monkeypatch.setattr("app.agents.a2a.risk_agent._assess_risk", fake_assess)
    monkeypatch.setattr(
        "app.agents.a2a.risk_agent.run_company_intelligence",
        fake_intelligence,
    )

    risk, intelligence, follow_up_used = await run_risk_assessment(
        tenant_id=uuid4(),
        company_query="Spotify",
        question="Spotify risk?",
        allow_a2a_follow_up=False,
    )
    assert called["intel"] is False
    assert intelligence is None
    assert risk.needs_more_evidence is True
    assert follow_up_used is False
