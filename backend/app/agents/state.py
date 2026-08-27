from typing import Annotated, Any, Literal, TypedDict
from uuid import UUID

from app.agents.execution_trace import merge_execution_details

AgentRoute = Literal[
    "knowledge",
    "sql",
    "tool",
    "unsupported",
]
RetrievalMode = Literal["standard", "advanced"]
ReadCapability = Literal["knowledge", "sql", "tool"]
ResponseLanguage = Literal["en", "tr"]


class AgentState(TypedDict, total=False):
    tenant_id: UUID
    tenant_slug: str
    query: str
    retrieval_mode: RetrievalMode
    response_language: ResponseLanguage

    requires_approval: bool
    pending_action: dict
    approval_granted: bool
    action_result: dict

    # Primary route for API/backward compatibility (first planned capability).
    route: AgentRoute
    planned_routes: list[AgentRoute]
    requires_synthesis: bool
    may_require_write: bool
    # When True, the tool branch only runs MCP read tools (composite fan-out).
    tool_read_only: bool

    generated_sql: str

    rag_answer: str
    tool_answer: str
    sql_answer: str
    synthesis_answer: str
    final_answer: str

    # Sprint 3 A2A structured evidence (dict payloads from Pydantic model_dump).
    a2a_intelligence_evidence: dict[str, Any]
    a2a_risk_result: dict[str, Any]
    a2a_follow_up_task: dict[str, Any]

    execution_details: Annotated[dict[str, Any], merge_execution_details]
