from typing import Literal, TypedDict
from uuid import UUID

AgentRoute = Literal["knowledge", "tool", "unsupported"]
RetrievalMode = Literal["standard", "advanced"]


class AgentState(TypedDict, total=False):
    tenant_id: UUID
    query: str
    retrieval_mode: RetrievalMode

    route: AgentRoute

    rag_answer: str
    tool_answer: str
    final_answer: str
