"""Risk Agent — assess risk from SQL/RAG/external evidence with A2A follow-up."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.a2a.company_intelligence_agent import run_company_intelligence
from app.agents.a2a.entity_resolution import resolve_company_entity
from app.agents.a2a.schemas import (
    A2AFollowUpTask,
    CompanyIntelligenceResult,
    EvidenceItem,
    RiskAssessmentResult,
)
from app.db.session import SessionLocal
from app.models.company import Company, CompanyPayment, CompanyRevenue, CompanyTransaction
from app.services.language_detection import format_response_language_instruction
from app.services.llm_service import get_chat_model

_RISK_PROMPT = """
You are the Risk Agent for an enterprise commercial portfolio.

Assess risk using ONLY the provided evidence blocks (SQL/internal, RAG, and
external A2A intelligence). Do not invent facts.

Rules:
- risk_level must be one of: low, medium, high (English enum values only)
- confidence is between 0 and 1
- reasons and recommended_actions must be grounded in evidence
- Write every reason and recommended_action in the requested response language
  (Turkish or English). Do not mix languages in those fields.
- If external/public evidence is missing or too thin for a confident call,
  set needs_more_evidence=true and provide a follow_up_task aimed at the
  company_intelligence agent with a concrete research request.
- If evidence is already sufficient, needs_more_evidence=false and
  follow_up_task=null.
- Keep company identity exact; never blend companies.
""".strip()


class _RiskDraft(BaseModel):
    risk_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    needs_more_evidence: bool = False
    follow_up_research_task: str | None = None
    follow_up_reason: str | None = None


async def collect_internal_company_evidence(
    *,
    tenant_id: UUID,
    company_query: str,
) -> list[EvidenceItem]:
    """Load synthetic CRM/SQL evidence for a resolved company."""

    entity = await resolve_company_entity(tenant_id=tenant_id, company_query=company_query)
    if entity.unresolved or not entity.internal_customer_id:
        return []

    async with SessionLocal() as session:
        company = await session.scalar(
            select(Company).where(
                Company.tenant_id == tenant_id,
                Company.internal_customer_id == entity.internal_customer_id,
            )
        )
        if company is None:
            return []

        revenue_rows = (
            await session.execute(
                select(CompanyRevenue).where(
                    CompanyRevenue.tenant_id == tenant_id,
                    CompanyRevenue.company_id == company.id,
                )
            )
        ).scalars().all()
        transactions = (
            await session.execute(
                select(CompanyTransaction).where(
                    CompanyTransaction.tenant_id == tenant_id,
                    CompanyTransaction.company_id == company.id,
                )
            )
        ).scalars().all()
        payments = (
            await session.execute(
                select(CompanyPayment).where(
                    CompanyPayment.tenant_id == tenant_id,
                    CompanyPayment.company_id == company.id,
                )
            )
        ).scalars().all()

    evidence: list[EvidenceItem] = [
        EvidenceItem(
            summary=(
                f"Account {company.company_name} ({company.internal_customer_id}, "
                f"{company.domain}) health={company.account_health} "
                f"score={company.health_score}."
            ),
            source_type="sql",
            source_title="companies.account_health",
            confidence=0.95,
        )
    ]
    for row in revenue_rows:
        evidence.append(
            EvidenceItem(
                summary=(
                    f"Revenue {row.metric} {row.period_label}: "
                    f"{row.amount} {row.currency}."
                ),
                source_type="sql",
                source_title="company_revenue",
                confidence=0.95,
            )
        )
    for row in transactions[:5]:
        evidence.append(
            EvidenceItem(
                summary=(
                    f"Transaction {row.reference}: {row.txn_type} "
                    f"{row.amount} {row.currency} status={row.status}."
                ),
                source_type="sql",
                source_title="transactions",
                confidence=0.9,
            )
        )
    for row in payments[:5]:
        evidence.append(
            EvidenceItem(
                summary=(
                    f"Payment {row.reference}: {row.amount} {row.currency} "
                    f"method={row.method} status={row.status}."
                ),
                source_type="sql",
                source_title="payments",
                confidence=0.9,
            )
        )
    return evidence


def _evidence_block(title: str, items: list[EvidenceItem]) -> str:
    if not items:
        return f"### {title}\n(none)"
    lines = [f"### {title}"]
    for item in items:
        lines.append(
            f"- [{item.source_type}] {item.source_title or 'n/a'}: {item.summary}"
        )
    return "\n".join(lines)


async def _assess_risk(
    *,
    company_query: str,
    question: str,
    sql_evidence: list[EvidenceItem],
    rag_evidence: list[EvidenceItem],
    external_evidence: list[EvidenceItem],
    response_language: str = "en",
) -> RiskAssessmentResult:
    model = get_chat_model().with_structured_output(_RiskDraft)
    draft = await model.ainvoke(
        [
            ("system", _RISK_PROMPT),
            (
                "human",
                (
                    f"{format_response_language_instruction(response_language)}\n"
                    f"User question: {question}\n"
                    f"Company query: {company_query}\n\n"
                    f"{_evidence_block('SQL / internal evidence', sql_evidence)}\n\n"
                    f"{_evidence_block('RAG evidence', rag_evidence)}\n\n"
                    f"{_evidence_block('External A2A intelligence', external_evidence)}\n"
                ),
            ),
        ]
    )
    parsed = draft if isinstance(draft, _RiskDraft) else _RiskDraft.model_validate(draft)
    level = parsed.risk_level if parsed.risk_level in {"low", "medium", "high"} else "medium"

    follow_up = None
    if parsed.needs_more_evidence and parsed.follow_up_research_task:
        follow_up = A2AFollowUpTask(
            from_agent="risk",
            to_agent="company_intelligence",
            task=parsed.follow_up_research_task.strip(),
            company_query=company_query,
            reason=parsed.follow_up_reason,
        )

    return RiskAssessmentResult(
        risk_level=level,  # type: ignore[arg-type]
        confidence=parsed.confidence,
        reasons=parsed.reasons,
        recommended_actions=parsed.recommended_actions,
        evidence_refs=[*sql_evidence, *rag_evidence, *external_evidence],
        needs_more_evidence=parsed.needs_more_evidence,
        follow_up_task=follow_up,
    )


async def run_risk_assessment(
    *,
    tenant_id: UUID,
    company_query: str,
    question: str,
    rag_answer: str | None = None,
    intelligence: CompanyIntelligenceResult | None = None,
    response_language: str = "en",
    allow_a2a_follow_up: bool = True,
) -> tuple[RiskAssessmentResult, CompanyIntelligenceResult | None, bool]:
    """Run Risk Agent; optionally delegate one A2A follow-up research task.

    Returns (final_risk, intelligence_used, a2a_follow_up_executed).
    """

    sql_evidence = await collect_internal_company_evidence(
        tenant_id=tenant_id,
        company_query=company_query,
    )
    rag_evidence: list[EvidenceItem] = []
    if rag_answer and rag_answer.strip():
        rag_evidence.append(
            EvidenceItem(
                summary=rag_answer.strip()[:1500],
                source_type="rag",
                source_title="rag_answer",
                confidence=0.8,
            )
        )

    intelligence_used = intelligence
    external_evidence: list[EvidenceItem] = []
    if intelligence_used is not None:
        external_evidence.extend(intelligence_used.evidence)
        for finding in intelligence_used.findings:
            external_evidence.append(
                EvidenceItem(
                    summary=finding,
                    source_type="a2a",
                    source_title="company_intelligence.findings",
                    confidence=0.7,
                )
            )

    first = await _assess_risk(
        company_query=company_query,
        question=question,
        sql_evidence=sql_evidence,
        rag_evidence=rag_evidence,
        external_evidence=external_evidence,
        response_language=response_language,
    )

    if not (
        allow_a2a_follow_up
        and first.needs_more_evidence
        and first.follow_up_task is not None
    ):
        return first, intelligence_used, False

    # A2A delegation: Risk → Company Intelligence → Risk (single bounded hop).
    follow = first.follow_up_task
    intelligence_used = await run_company_intelligence(
        tenant_id=tenant_id,
        company_query=follow.company_query or company_query,
        research_focus=follow.task,
        response_language=response_language,
    )
    external_evidence = [
        *intelligence_used.evidence,
        *[
            EvidenceItem(
                summary=finding,
                source_type="a2a",
                source_title="company_intelligence.follow_up",
                confidence=0.7,
            )
            for finding in intelligence_used.findings
        ],
    ]
    final = await _assess_risk(
        company_query=company_query,
        question=question,
        sql_evidence=sql_evidence,
        rag_evidence=rag_evidence,
        external_evidence=external_evidence,
        response_language=response_language,
    )
    # Prevent unbounded loops even if the model asks again.
    if final.needs_more_evidence:
        final.needs_more_evidence = False
        final.follow_up_task = None
        if not final.reasons:
            final.reasons = list(first.reasons)
        follow_up_note = (
            "A2A follow-up araştırması tamamlandı; mevcut kanıtlarla devam edildi."
            if response_language == "tr"
            else "A2A follow-up research completed; proceeding with available evidence."
        )
        final.reasons = [
            *final.reasons,
            follow_up_note,
        ]
    else:
        final.follow_up_task = follow

    return final, intelligence_used, True
