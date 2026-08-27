from uuid import uuid4

import pytest

from app.agents.a2a.company_extract import extract_company_query
from app.agents.a2a.pipeline import run_a2a_external_risk_pipeline
from app.agents.a2a.schemas import (
    CompanyIntelligenceResult,
    EntityResolution,
    EvidenceItem,
    RiskAssessmentResult,
)


def test_extract_company_query_known_brands() -> None:
    assert extract_company_query("Spotify'ın dış risklerini araştır.") == "Spotify"
    assert extract_company_query("Assess Microsoft external risks") == "Microsoft"
    assert extract_company_query("What is the weather?") is None


@pytest.mark.asyncio
async def test_a2a_pipeline_end_to_end_with_mocks(monkeypatch) -> None:
    async def fake_intelligence(**kwargs):
        return CompanyIntelligenceResult(
            company_query="Microsoft",
            entity=EntityResolution(
                company_name="Microsoft",
                domain="microsoft.com",
                internal_customer_id="CUST-MICROSOFT",
                unresolved=False,
            ),
            search_queries=["Microsoft risk"],
            evidence=[
                EvidenceItem(summary="Public profile evidence.", source_type="web")
            ],
            findings=["External profile collected."],
            evidence_sufficient=True,
        )

    async def fake_risk(**kwargs):
        return (
            RiskAssessmentResult(
                risk_level="high",
                confidence=0.9,
                reasons=["at_risk account health"],
                recommended_actions=["Escalate"],
                needs_more_evidence=False,
            ),
            kwargs.get("intelligence"),
            True,
        )

    monkeypatch.setattr(
        "app.agents.a2a.pipeline.run_company_intelligence",
        fake_intelligence,
    )
    monkeypatch.setattr(
        "app.agents.a2a.pipeline.run_risk_assessment",
        fake_risk,
    )

    result = await run_a2a_external_risk_pipeline(
        tenant_id=uuid4(),
        question="Assess Microsoft external risks",
        response_language="en",
    )
    assert result.company_query == "Microsoft"
    assert result.risk is not None
    assert result.risk.risk_level == "high"
    assert result.a2a_follow_up_used is True
    assert "Risk level: high" in result.answer
    assert "a2a_risk_result" in result.state_updates()


@pytest.mark.asyncio
async def test_a2a_pipeline_formats_turkish_answer(monkeypatch) -> None:
    async def fake_intelligence(**kwargs):
        assert kwargs["response_language"] == "tr"
        return CompanyIntelligenceResult(
            company_query="Spotify",
            entity=EntityResolution(
                company_name="Spotify",
                domain="spotify.com",
                unresolved=False,
            ),
            search_queries=["Spotify risk"],
            evidence=[EvidenceItem(summary="Profil.", source_type="web")],
            findings=["Kamuya açık profil toplandı."],
            evidence_sufficient=True,
        )

    async def fake_risk(**kwargs):
        assert kwargs["response_language"] == "tr"
        return (
            RiskAssessmentResult(
                risk_level="medium",
                confidence=0.7,
                reasons=["Rekabet yoğunluğu yüksek."],
                recommended_actions=["Rekabet ortamını izleyin."],
                needs_more_evidence=False,
            ),
            kwargs.get("intelligence"),
            False,
        )

    monkeypatch.setattr(
        "app.agents.a2a.pipeline.run_company_intelligence",
        fake_intelligence,
    )
    monkeypatch.setattr(
        "app.agents.a2a.pipeline.run_risk_assessment",
        fake_risk,
    )

    result = await run_a2a_external_risk_pipeline(
        tenant_id=uuid4(),
        question="Spotify'ın dış risklerini araştır.",
        response_language="tr",
    )
    assert "Risk seviyesi: orta" in result.answer
    assert "Gerekçeler:" in result.answer
    assert "Rekabet yoğunluğu yüksek." in result.answer
    assert "Şirket: Spotify" in result.answer


@pytest.mark.asyncio
async def test_a2a_pipeline_unresolved_company(monkeypatch) -> None:
    result = await run_a2a_external_risk_pipeline(
        tenant_id=uuid4(),
        question="Assess UnknownCorp external risks",
        response_language="en",
    )
    assert result.company_query is None
    assert result.risk is None
    assert "Could not resolve" in result.answer
