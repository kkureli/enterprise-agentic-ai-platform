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


class AgentState(TypedDict, total=False):
    tenant_id: UUID
    tenant_slug: str
    query: str
    retrieval_mode: RetrievalMode

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

    execution_details: Annotated[dict[str, Any], merge_execution_details]
