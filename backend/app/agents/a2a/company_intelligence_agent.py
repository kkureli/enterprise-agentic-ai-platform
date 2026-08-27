"""Company Intelligence Agent — public research + entity-grounded evidence."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.agents.a2a.entity_resolution import resolve_company_entity
from app.agents.a2a.schemas import CompanyIntelligenceResult, EntityResolution, EvidenceItem
from app.agents.a2a.web_research import collect_public_evidence
from app.services.language_detection import format_response_language_instruction
from app.services.llm_service import get_chat_model


class _SearchPlan(BaseModel):
    english_queries: list[str] = Field(default_factory=list, max_length=3)
    turkish_queries: list[str] = Field(default_factory=list, max_length=3)


class _Findings(BaseModel):
    findings: list[str] = Field(default_factory=list)
    evidence_sufficient: bool = True
    notes: str | None = None


_SEARCH_PLAN_PROMPT = """
You plan public-web research queries for a company intelligence agent.

Return concise search queries that preserve the company entity exactly.
Include English queries always. Include Turkish queries when the research
focus or user question is Turkish, or when Turkish-language coverage helps.
Do not invent a different company. Do not answer the research question.
""".strip()

_FINDINGS_PROMPT = """
You are the Company Intelligence Agent.

Using ONLY the provided entity and evidence snippets, produce short findings.
Do not invent facts beyond the evidence. If evidence is thin, set
evidence_sufficient=false and explain in notes.
Keep company identity exact (name/domain/internal id).
Write findings (and notes, if any) in the requested response language
(Turkish or English). Do not mix languages in those fields.
""".strip()


async def _plan_search_queries(
    *,
    company_query: str,
    entity: EntityResolution,
    research_focus: str | None,
    response_language: str,
) -> list[str]:
    model = get_chat_model().with_structured_output(_SearchPlan)
    result = await model.ainvoke(
        [
            ("system", _SEARCH_PLAN_PROMPT),
            (
                "human",
                (
                    f"Company query: {company_query}\n"
                    f"Resolved name: {entity.company_name}\n"
                    f"Official name: {entity.official_name}\n"
                    f"Domain: {entity.domain}\n"
                    f"Research focus: {research_focus or company_query}\n"
                    f"Response language hint: {response_language}\n"
                ),
            ),
        ]
    )
    plan = result if isinstance(result, _SearchPlan) else _SearchPlan.model_validate(result)
    queries: list[str] = []
    for item in [*plan.english_queries, *plan.turkish_queries]:
        cleaned = item.strip()
        if cleaned and cleaned.lower() not in {q.lower() for q in queries}:
            queries.append(cleaned)
    if entity.company_name and entity.company_name not in queries:
        queries.insert(0, entity.company_name)
    return queries[:6]


async def _synthesize_findings(
    *,
    company_query: str,
    entity: EntityResolution,
    evidence: list[EvidenceItem],
    research_focus: str | None,
    response_language: str = "en",
) -> _Findings:
    if not evidence:
        return _Findings(
            findings=[],
            evidence_sufficient=False,
            notes=(
                "Herkese açık kanıt toplanamadı."
                if response_language == "tr"
                else "No public evidence collected."
            ),
        )

    model = get_chat_model().with_structured_output(_Findings)
    evidence_block = "\n\n".join(
        (
            f"- title: {item.source_title or 'n/a'}\n"
            f"  url: {item.source_url or 'n/a'}\n"
            f"  summary: {item.summary}"
        )
        for item in evidence
    )
    result = await model.ainvoke(
        [
            ("system", _FINDINGS_PROMPT),
            (
                "human",
                (
                    f"{format_response_language_instruction(response_language)}\n"
                    f"Company query: {company_query}\n"
                    f"Research focus: {research_focus or company_query}\n"
                    f"Entity: {entity.model_dump()}\n\n"
                    f"Evidence:\n{evidence_block}"
                ),
            ),
        ]
    )
    return result if isinstance(result, _Findings) else _Findings.model_validate(result)


async def run_company_intelligence(
    *,
    tenant_id: UUID,
    company_query: str,
    research_focus: str | None = None,
    response_language: str = "en",
) -> CompanyIntelligenceResult:
    """Run Company Intelligence research for a tenant-scoped company query.

    Invoked by the A2A risk pipeline / LangGraph ``a2a_risk`` node.
    """

    entity = await resolve_company_entity(tenant_id=tenant_id, company_query=company_query)
    if entity.unresolved or not entity.company_name:
        return CompanyIntelligenceResult(
            company_query=company_query,
            entity=entity,
            search_queries=[],
            evidence=[],
            findings=[],
            evidence_sufficient=False,
            notes=(
                "Entity resolution failed or was ambiguous. "
                "Refusing to research an unresolved company."
            ),
        )

    search_queries = await _plan_search_queries(
        company_query=company_query,
        entity=entity,
        research_focus=research_focus,
        response_language=response_language,
    )
    evidence = await collect_public_evidence(
        company_name=entity.official_name or entity.company_name,
        domain=entity.domain,
        extra_queries=search_queries,
    )
    synthesized = await _synthesize_findings(
        company_query=company_query,
        entity=entity,
        evidence=evidence,
        research_focus=research_focus,
        response_language=response_language,
    )

    return CompanyIntelligenceResult(
        company_query=company_query,
        entity=entity,
        search_queries=search_queries,
        evidence=evidence,
        findings=synthesized.findings,
        evidence_sufficient=bool(evidence) and synthesized.evidence_sufficient,
        notes=synthesized.notes,
    )
