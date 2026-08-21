from pydantic import BaseModel


class RetrievalRequest(BaseModel):
    query: str
    limit: int = 5


class RetrievedChunkRead(BaseModel):
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str
