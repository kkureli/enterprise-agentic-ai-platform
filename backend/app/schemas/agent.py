from typing import Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    retrieval_mode: Literal["standard", "advanced"] = "standard"


class AgentResponse(BaseModel):
    route: Literal["knowledge", "unsupported"]
    answer: str
