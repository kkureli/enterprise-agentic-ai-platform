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


class AgentState(TypedDict, total=False):
    tenant_id: UUID
    query: str
    retrieval_mode: RetrievalMode

    requires_approval: bool
    pending_action: dict
    approval_granted: bool
    action_result: dict

    route: AgentRoute

    generated_sql: str

    rag_answer: str
    tool_answer: str
    sql_answer: str
    final_answer: str

    execution_details: Annotated[dict[str, Any], merge_execution_details]
