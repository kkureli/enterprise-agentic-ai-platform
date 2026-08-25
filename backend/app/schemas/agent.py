from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.agents.state import AgentRoute, RetrievalMode
from app.core.config import settings
from app.schemas.execution import ExecutionDetails


class AgentRequest(BaseModel):
    question: str = Field(min_length=1)
    retrieval_mode: RetrievalMode = "standard"

    @field_validator("question")
    @classmethod
    def validate_question_length(cls, value: str) -> str:
        max_chars = settings.max_agent_question_chars
        if len(value) > max_chars:
            raise ValueError(f"Question exceeds maximum length of {max_chars} characters.")
        return value


class AgentResponse(BaseModel):
    thread_id: str
    status: Literal[
        "completed",
        "approval_required",
    ]
    route: AgentRoute
    answer: str
    pending_action: dict[str, Any] | None = None
    execution_details: ExecutionDetails | None = None


class AgentApprovalRequest(BaseModel):
    approved: bool


class AgentCompareRequest(BaseModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def validate_question_length(cls, value: str) -> str:
        max_chars = settings.max_agent_question_chars
        if len(value) > max_chars:
            raise ValueError(f"Question exceeds maximum length of {max_chars} characters.")
        return value


class AgentCompareResponse(BaseModel):
    question: str
    standard: AgentResponse
    advanced: AgentResponse
    note: str = (
        "Comparison runs the same question with standard and advanced "
        "retrieval. Only knowledge/RAG routes are intended for comparison."
    )
