from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RagRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=10)
    retrieval_mode: Literal["standard", "advanced"] = "standard"

    document_id: UUID | None = None
    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
    )


class RagSourceRead(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float


class RagRetrievedChunkRead(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float
    text: str


class RagResponse(BaseModel):
    answer: str
    sources: list[RagSourceRead]
    retrieved_chunks: list[RagRetrievedChunkRead]
