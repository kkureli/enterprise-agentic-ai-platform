"""LangGraph node for external_risk_assessment (A2A pipeline)."""

from __future__ import annotations

from app.agents.a2a import run_a2a_external_risk_pipeline
from app.agents.a2a.github_escalation import build_github_escalation_pending_action
from app.agents.execution_trace import node_trace
from app.agents.state import AgentState
from app.services.rag_service import answer_question


async def _maybe_load_rag_context(state: AgentState) -> str | None:
    """Use RAG evidence when the knowledge node did not already run.

    Single-route external risk should still see contracts / account reviews.
    When ``knowledge`` is also planned, leave RAG to the parallel rag node /
    synthesis path to avoid a duplicate retrieval.
    """

    existing = (state.get("rag_answer") or "").strip()
    if existing:
        return existing

    planned = list(state.get("planned_routes") or [])
    if "knowledge" in planned:
        return None

    result = await answer_question(
        tenant_id=state["tenant_id"],
        question=state["query"],
        retrieval_mode=state.get("retrieval_mode", "standard"),
        response_language=state.get("response_language"),
    )
    answer = (result.answer or "").strip()
    return answer or None


async def a2a_risk_node(state: AgentState) -> dict:
    rag_answer = await _maybe_load_rag_context(state)
    response_language = state.get("response_language") or "en"

    result = await run_a2a_external_risk_pipeline(
        tenant_id=state["tenant_id"],
        question=state["query"],
        rag_answer=rag_answer,
        response_language=response_language,
    )

    a2a_trace: dict = {
        "company_query": result.company_query,
        "follow_up_used": result.a2a_follow_up_used,
        "rag_context_used": bool(rag_answer),
    }
    if result.risk is not None:
        a2a_trace["risk_level"] = result.risk.risk_level
        a2a_trace["confidence"] = result.risk.confidence

    updates: dict = {
        "a2a_answer": result.answer,
        **result.state_updates(),
        **node_trace(
            "a2a_risk",
            route="external_risk_assessment",
            a2a=a2a_trace,
        ),
    }
    # Persist enriched RAG only when this node loaded it (single-route path).
    if rag_answer and not (state.get("rag_answer") or "").strip():
        updates["rag_answer"] = rag_answer

    # HIGH risk → HITL before any GitHub write (MCP create_github_issue).
    if result.risk is not None and result.risk.risk_level == "high":
        tenant_slug = state.get("tenant_slug") or "unknown"
        hitl = build_github_escalation_pending_action(
            tenant_slug=tenant_slug,
            company_query=result.company_query,
            risk=result.risk,
            assessment_answer=result.answer,
            response_language=response_language,
        )
        updates.update(hitl)
        updates["execution_details"] = {
            **updates.get("execution_details", {}),
            "hitl": {
                "required": True,
                "approved": None,
                "pending_action": hitl["pending_action"],
            },
            "tools": {
                "mcp_server": "github",
                "tool_name": "create_github_issue",
                "tool_type": "write",
                "requires_approval": True,
                "approval_status": "pending",
                "tenant_slug": tenant_slug,
                "arguments": {
                    key: value
                    for key, value in hitl["pending_action"]["arguments"].items()
                    if key not in {"body", "tenant_slug"}
                },
            },
        }

    return updates
