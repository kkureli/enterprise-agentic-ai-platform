"""Selective multi-capability planner (replaces mutually exclusive router)."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field, field_validator

from app.agents.execution_trace import node_trace
from app.agents.state import AgentRoute, AgentState, ReadCapability
from app.services.llm_service import get_chat_model

READ_ROUTES: frozenset[str] = frozenset({"knowledge", "sql", "tool", "external_risk_assessment"})


class RoutePlan(BaseModel):
    """Structured selective plan for one user question."""

    routes: list[AgentRoute] = Field(default_factory=list)
    requires_synthesis: bool = False
    may_require_write: bool = False

    @field_validator("routes")
    @classmethod
    def _normalize_routes(cls, value: list[AgentRoute]) -> list[AgentRoute]:
        return normalize_planned_routes(value)


def normalize_planned_routes(routes: list[AgentRoute] | None) -> list[AgentRoute]:
    """Deduplicate while preserving order; drop unsupported when mixed with reads."""
    if not routes:
        return ["unsupported"]

    ordered: list[AgentRoute] = []
    seen: set[str] = set()
    for route in routes:
        if route in seen:
            continue
        seen.add(route)
        ordered.append(route)

    read_selected = [route for route in ordered if route in READ_ROUTES]
    if read_selected:
        return read_selected

    if "unsupported" in ordered:
        return ["unsupported"]

    return ["unsupported"]


def finalize_plan(plan: RoutePlan) -> RoutePlan:
    routes = normalize_planned_routes(plan.routes)
    requires_synthesis = len(routes) >= 2
    may_require_write = bool(plan.may_require_write)
    # Writes are never part of parallel evidence gathering.
    if requires_synthesis:
        may_require_write = may_require_write
    return RoutePlan(
        routes=routes,
        requires_synthesis=requires_synthesis,
        may_require_write=may_require_write,
    )


PLANNER_SYSTEM_PROMPT = """
You are a selective planner for an enterprise AI operations platform.

Select the minimum set of capabilities required to answer the user question.
Do NOT select every capability by default.

Questions may be in English or Turkish. Route by intent, not by language.
Turkish and English questions with the same meaning must select the same capabilities.
Capability names and underlying systems remain English
(knowledge/sql/tool/external_risk_assessment).

Valid capability routes:
- knowledge: enterprise documents, policies, manuals, procedures, error-code meaning,
  contracts, customer notes, account reviews
- sql: historical / structured operational data in PostgreSQL (counts, lists, history,
  tickets) AND commercial account data (companies, revenue, transactions, payments,
  account health)
- tool: live operational MCP tools (current asset status) and/or creating a maintenance ticket
- external_risk_assessment: external/public company intelligence + risk assessment (A2A).
  Use for outside risk, financing developments, public reputation/risk investigation —
  NOT for internal revenue/SQL-only or internal contract/RAG-only questions.
- unsupported: no available capability applies

Rules:
1. Ordinary questions should select exactly ONE capability.
2. Select multiple capabilities ONLY when the user clearly needs more than one
   information source in the same question.
3. Deduplicate. Never list the same route twice.
4. Set requires_synthesis=true only when two or more read capabilities are selected.
5. Set may_require_write=true ONLY when the user asks to create/open a maintenance
   ticket or explicitly requests a write action. Do not set it for status/history
   questions alone.
6. If the question mixes ticket creation with evidence gathering, include the
   needed read capabilities AND set may_require_write=true.
7. Prefer sql for historical maintenance records and lists; prefer tool for
   CURRENT live operational status of a specific asset.
8. Prefer knowledge for "what does X mean" / procedures / documentation.
9. Prefer external_risk_assessment for external/public risk investigation.
   If the user also needs internal structured data and/or contracts in the same
   question, combine sql and/or knowledge WITH external_risk_assessment.
10. Do NOT select external_risk_assessment for simple internal revenue, payment,
    account-health SQL questions, or pure document lookup.

Examples:

"What does E-100 mean?"
→ routes=["knowledge"], requires_synthesis=false, may_require_write=false

"E-100 ne anlama geliyor?"
→ routes=["knowledge"], requires_synthesis=false, may_require_write=false

"Which assets have warnings?"
→ routes=["sql"], requires_synthesis=false, may_require_write=false

"Hangi varlıklarda uyarı var?"
→ routes=["sql"], requires_synthesis=false, may_require_write=false

"What is Spotify's annual revenue?"
→ routes=["sql"], requires_synthesis=false, may_require_write=false

"Spotify'ın cirosu nedir?"
→ routes=["sql"], requires_synthesis=false, may_require_write=false

"What does the Spotify MSA say about termination?"
→ routes=["knowledge"], requires_synthesis=false, may_require_write=false

"Assess Microsoft external risks."
→ routes=["external_risk_assessment"], requires_synthesis=false, may_require_write=false

"Spotify'ın dış risklerini araştır."
→ routes=["external_risk_assessment"], requires_synthesis=false, may_require_write=false

"Evaluate Spotify using internal data, contract terms, and current external risks."
→ routes=["sql","knowledge","external_risk_assessment"], requires_synthesis=true,
  may_require_write=false

"Spotify'ın iç verilerini, sözleşmesini ve güncel dış risklerini değerlendir."
→ routes=["sql","knowledge","external_risk_assessment"], requires_synthesis=true,
  may_require_write=false

"What is MACHINE-42's current status?"
→ routes=["tool"], requires_synthesis=false, may_require_write=false

"MACHINE-42'nin güncel durumu nedir?"
→ routes=["tool"], requires_synthesis=false, may_require_write=false

"Create a high-priority maintenance ticket for MACHINE-42 because of hydraulic pressure loss."
→ routes=["tool"], requires_synthesis=false, may_require_write=true

"MACHINE-42 için hidrolik basınç kaybı nedeniyle yüksek öncelikli bakım kaydı oluştur."
→ routes=["tool"], requires_synthesis=false, may_require_write=true

"Use the enterprise system to create a ticket for MACHINE-42."
→ routes=["tool"], requires_synthesis=false, may_require_write=true

"What does E-100 mean and what is MACHINE-42's status?"
→ routes=["knowledge","tool"], requires_synthesis=true, may_require_write=false

"E-100 ne demek ve MACHINE-42'nin durumu nedir?"
→ routes=["knowledge","tool"], requires_synthesis=true, may_require_write=false

"What does E-100 mean and MACHINE-42 history + current status?"
→ routes=["knowledge","sql","tool"], requires_synthesis=true, may_require_write=false

"Send an email to the maintenance manager."
→ routes=["unsupported"], requires_synthesis=false, may_require_write=false

"Bakım müdürüne e-posta gönder."
→ routes=["unsupported"], requires_synthesis=false, may_require_write=false

Return only the structured plan.
""".strip()


async def planner_node(state: AgentState) -> dict:
    started = time.perf_counter()

    model = get_chat_model().with_structured_output(RoutePlan)
    raw = await model.ainvoke(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("human", state["query"]),
        ]
    )
    plan = finalize_plan(raw if isinstance(raw, RoutePlan) else RoutePlan.model_validate(raw))

    primary: AgentRoute = plan.routes[0]
    tool_read_only = plan.requires_synthesis and "tool" in plan.routes
    planner_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "route": primary,
        "planned_routes": plan.routes,
        "requires_synthesis": plan.requires_synthesis,
        "may_require_write": plan.may_require_write,
        "tool_read_only": tool_read_only,
        **node_trace(
            "planner",
            route=primary,
            selected_capabilities=[r for r in plan.routes if r in READ_ROUTES],
            timing={"planner_ms": planner_ms, "router_ms": planner_ms},
        ),
    }


# Backward-compatible alias for older imports/evals.
router_node = planner_node

__all__ = [
    "RoutePlan",
    "READ_ROUTES",
    "normalize_planned_routes",
    "finalize_plan",
    "planner_node",
    "router_node",
    "ReadCapability",
]
