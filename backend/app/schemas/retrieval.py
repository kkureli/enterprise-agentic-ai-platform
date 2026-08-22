from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=10)

    document_id: UUID | None = None
    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
    )


class RetrievedChunkRead(BaseModel):
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str
