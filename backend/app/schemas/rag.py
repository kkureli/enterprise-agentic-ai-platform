from pydantic import BaseModel, Field


class RagRequest(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
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
