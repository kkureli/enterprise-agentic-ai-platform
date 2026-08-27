from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.a2a.company_intelligence_agent import run_company_intelligence
from app.agents.a2a.entity_resolution import resolve_company_row
from app.agents.a2a.schemas import CompanyIntelligenceResult, EntityResolution, EvidenceItem


def _company(**overrides):
    base = {
        "internal_customer_id": "CUST-SPOTIFY",
        "company_name": "Spotify",
        "official_name": "Spotify AB",
        "domain": "spotify.com",
        "aliases": "Spotify Inc,Spotify Technology",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_company_row_matches_spotify_identity() -> None:
    company = _company()
    assert resolve_company_row(company, "Spotify") is not None
    assert resolve_company_row(company, "spotify.com") is not None
    assert resolve_company_row(company, "CUST-SPOTIFY") is not None
    assert resolve_company_row(company, "Spotify Inc") is not None


def test_resolve_company_row_rejects_other_brand() -> None:
    company = _company()
    assert resolve_company_row(company, "Siemens") is None
    assert resolve_company_row(company, "microsoft.com") is None


@pytest.mark.asyncio
async def test_run_company_intelligence_refuses_unresolved_entity(monkeypatch) -> None:
    async def fake_resolve(*, tenant_id, company_query):
        return EntityResolution(unresolved=True, resolution_confidence=0.0)

    monkeypatch.setattr(
        "app.agents.a2a.company_intelligence_agent.resolve_company_entity",
        fake_resolve,
    )

    result = await run_company_intelligence(
        tenant_id=uuid4(),
        company_query="Unknown Corp",
    )
    assert isinstance(result, CompanyIntelligenceResult)
    assert result.evidence_sufficient is False
    assert result.evidence == []
    assert "unresolved" in (result.notes or "").lower()


@pytest.mark.asyncio
async def test_run_company_intelligence_happy_path_with_mocks(monkeypatch) -> None:
    async def fake_resolve(*, tenant_id, company_query):
        return EntityResolution(
            internal_customer_id="CUST-SPOTIFY",
            company_name="Spotify",
            official_name="Spotify AB",
            domain="spotify.com",
            resolution_confidence=0.98,
            unresolved=False,
        )

    async def fake_plan(**kwargs):
        return ["Spotify AB", "Spotify financing news"]

    async def fake_collect(**kwargs):
        return [
            EvidenceItem(
                summary="Spotify is a music streaming company.",
                source_type="web",
                source_url="https://en.wikipedia.org/wiki/Spotify",
                source_title="Spotify",
                confidence=0.8,
            )
        ]

    class FakeFindings:
        findings = ["Public profile describes Spotify as a streaming company."]
        evidence_sufficient = True
        notes = None

    async def fake_findings(**kwargs):
        return FakeFindings()

    monkeypatch.setattr(
        "app.agents.a2a.company_intelligence_agent.resolve_company_entity",
        fake_resolve,
    )
    monkeypatch.setattr(
        "app.agents.a2a.company_intelligence_agent._plan_search_queries",
        fake_plan,
    )
    monkeypatch.setattr(
        "app.agents.a2a.company_intelligence_agent.collect_public_evidence",
        fake_collect,
    )
    monkeypatch.setattr(
        "app.agents.a2a.company_intelligence_agent._synthesize_findings",
        fake_findings,
    )

    result = await run_company_intelligence(
        tenant_id=uuid4(),
        company_query="Spotify",
        research_focus="external risks",
        response_language="tr",
    )
    assert result.entity.company_name == "Spotify"
    assert result.evidence_sufficient is True
    assert result.search_queries
    assert result.evidence[0].source_type == "web"
    assert "streaming" in result.findings[0].lower()
