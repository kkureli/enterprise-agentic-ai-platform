from app.agents.a2a.schemas import (
    A2AFollowUpTask,
    CompanyIntelligenceResult,
    EntityResolution,
    EvidenceItem,
    RiskAssessmentResult,
)
from app.agents.state import AgentState


def test_company_intelligence_and_risk_schemas_roundtrip() -> None:
    intelligence = CompanyIntelligenceResult(
        company_query="Spotify external risks",
        entity=EntityResolution(
            internal_customer_id="CUST-SPOTIFY",
            company_name="Spotify",
            official_name="Spotify AB",
            domain="spotify.com",
            resolution_confidence=0.95,
        ),
        search_queries=["Spotify financing news 2025", "Spotify AB risk"],
        evidence=[
            EvidenceItem(
                summary="Synthetic demo evidence placeholder.",
                source_type="web",
                source_url="https://example.com/spotify",
                confidence=0.7,
            )
        ],
        findings=["No blocking legal event in demo evidence."],
        evidence_sufficient=True,
    )
    risk = RiskAssessmentResult(
        risk_level="high",
        confidence=0.91,
        reasons=["Late payment posture in internal account data."],
        recommended_actions=["Open HITL-approved escalation ticket."],
        needs_more_evidence=True,
        follow_up_task=A2AFollowUpTask(
            from_agent="risk",
            to_agent="company_intelligence",
            task="Research financing developments in the last 12 months.",
            company_query="Spotify",
            reason="External evidence insufficient for final risk call.",
        ),
    )

    intel_payload = intelligence.model_dump()
    risk_payload = risk.model_dump()

    assert intel_payload["entity"]["domain"] == "spotify.com"
    assert risk_payload["risk_level"] == "high"
    assert risk_payload["follow_up_task"]["to_agent"] == "company_intelligence"

    restored_intel = CompanyIntelligenceResult.model_validate(intel_payload)
    restored_risk = RiskAssessmentResult.model_validate(risk_payload)
    assert restored_intel.entity.company_name == "Spotify"
    assert restored_risk.follow_up_task is not None
    assert restored_risk.follow_up_task.from_agent == "risk"


def test_agent_state_accepts_a2a_fields() -> None:
    state: AgentState = {
        "query": "Assess Spotify external risks",
        "response_language": "en",
        "a2a_intelligence_evidence": {"company_query": "Spotify"},
        "a2a_risk_result": {"risk_level": "medium", "confidence": 0.5},
        "a2a_follow_up_task": {
            "from_agent": "risk",
            "to_agent": "company_intelligence",
            "task": "Gather more financing evidence.",
        },
    }
    assert state["a2a_risk_result"]["risk_level"] == "medium"
