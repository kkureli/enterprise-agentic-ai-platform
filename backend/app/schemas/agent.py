from pydantic import BaseModel, Field

from app.agents.state import AgentRoute, RetrievalMode


class AgentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    retrieval_mode: RetrievalMode = "standard"


class AgentResponse(BaseModel):
    route: AgentRoute
    answer: str
