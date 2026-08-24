from typing import Any, Literal

from pydantic import BaseModel

from app.agents.state import AgentRoute, RetrievalMode


class AgentRequest(BaseModel):
    question: str
    retrieval_mode: RetrievalMode = "standard"


class AgentResponse(BaseModel):
    thread_id: str
    status: Literal[
        "completed",
        "approval_required",
    ]
    route: AgentRoute
    answer: str
    pending_action: dict[str, Any] | None = None


class AgentApprovalRequest(BaseModel):
    approved: bool
