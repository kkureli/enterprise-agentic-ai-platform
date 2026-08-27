"""End-to-end A2A external risk pipeline.

Wired into LangGraph via `a2a_risk_node` / route `external_risk_assessment`.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.agents.a2a.company_extract import extract_company_query
from app.agents.a2a.company_intelligence_agent import run_company_intelligence
from app.agents.a2a.risk_agent import run_risk_assessment
from app.agents.a2a.schemas import CompanyIntelligenceResult, RiskAssessmentResult


@dataclass
class A2APipelineResult:
    company_query: str | None
    intelligence: CompanyIntelligenceResult | None
    risk: RiskAssessmentResult | None
    answer: str
    a2a_follow_up_used: bool = False

    def state_updates(self) -> dict:
        """Payload suitable for merging into AgentState."""

        updates: dict = {}
        if self.intelligence is not None:
            updates["a2a_intelligence_evidence"] = self.intelligence.model_dump()
        if self.risk is not None:
            updates["a2a_risk_result"] = self.risk.model_dump()
            if self.risk.follow_up_task is not None:
                updates["a2a_follow_up_task"] = self.risk.follow_up_task.model_dump()
        return updates


def _format_risk_level(level: str, response_language: str) -> str:
    if response_language != "tr":
        return level
    return {"low": "düşük", "medium": "orta", "high": "yüksek"}.get(level, level)


def _format_risk_answer(
    *,
    risk: RiskAssessmentResult,
    intelligence: CompanyIntelligenceResult | None,
    response_language: str,
    follow_up_used: bool,
) -> str:
    level_label = _format_risk_level(risk.risk_level, response_language)

    if response_language == "tr":
        lines = [
            f"Risk seviyesi: {level_label}",
            f"Güven: {risk.confidence:.2f}",
        ]
        if risk.reasons:
            lines.append("Gerekçeler:")
            lines.extend(f"- {reason}" for reason in risk.reasons)
        if risk.recommended_actions:
            lines.append("Önerilen aksiyonlar:")
            lines.extend(f"- {action}" for action in risk.recommended_actions)
        if follow_up_used:
            lines.append(
                "Not: Risk Agent, Company Intelligence Agent'a "
                "A2A follow-up research görevi gönderdi."
            )
        if intelligence and intelligence.entity.company_name:
            lines.append(
                f"Şirket: {intelligence.entity.company_name} "
                f"({intelligence.entity.domain or 'n/a'})"
            )
        return "\n".join(lines)

    lines = [
        f"Risk level: {level_label}",
        f"Confidence: {risk.confidence:.2f}",
    ]
    if risk.reasons:
        lines.append("Reasons:")
        lines.extend(f"- {reason}" for reason in risk.reasons)
    if risk.recommended_actions:
        lines.append("Recommended actions:")
        lines.extend(f"- {action}" for action in risk.recommended_actions)
    if follow_up_used:
        lines.append(
            "Note: Risk Agent delegated an A2A follow-up research task to Company Intelligence."
        )
    if intelligence and intelligence.entity.company_name:
        lines.append(
            f"Entity: {intelligence.entity.company_name} "
            f"({intelligence.entity.domain or 'n/a'})"
        )
    return "\n".join(lines)


async def run_a2a_external_risk_pipeline(
    *,
    tenant_id: UUID,
    question: str,
    company_query: str | None = None,
    rag_answer: str | None = None,
    response_language: str = "en",
    allow_a2a_follow_up: bool = True,
) -> A2APipelineResult:
    """Run Company Intelligence → Risk (+ optional A2A follow-up)."""

    resolved_company = company_query or extract_company_query(question)
    if not resolved_company:
        message = (
            "Şirket entity'si çözülemedi; A2A risk değerlendirmesi yapılamadı."
            if response_language == "tr"
            else "Could not resolve a company entity; A2A risk assessment was not run."
        )
        return A2APipelineResult(
            company_query=None,
            intelligence=None,
            risk=None,
            answer=message,
            a2a_follow_up_used=False,
        )

    intelligence = await run_company_intelligence(
        tenant_id=tenant_id,
        company_query=resolved_company,
        research_focus=question,
        response_language=response_language,
    )
    if intelligence.entity.unresolved:
        message = (
            f"{resolved_company} için entity resolution başarısız; "
            "yanlış şirket araştırması yapılmadı."
            if response_language == "tr"
            else (
                f"Entity resolution failed for {resolved_company}; "
                "refusing wrong-company research."
            )
        )
        return A2APipelineResult(
            company_query=resolved_company,
            intelligence=intelligence,
            risk=None,
            answer=message,
            a2a_follow_up_used=False,
        )

    risk, intelligence_used, follow_up_used = await run_risk_assessment(
        tenant_id=tenant_id,
        company_query=resolved_company,
        question=question,
        rag_answer=rag_answer,
        intelligence=intelligence,
        response_language=response_language,
        allow_a2a_follow_up=allow_a2a_follow_up,
    )
    if intelligence_used is not None:
        intelligence = intelligence_used

    return A2APipelineResult(
        company_query=resolved_company,
        intelligence=intelligence,
        risk=risk,
        answer=_format_risk_answer(
            risk=risk,
            intelligence=intelligence,
            response_language=response_language,
            follow_up_used=follow_up_used,
        ),
        a2a_follow_up_used=follow_up_used,
    )
