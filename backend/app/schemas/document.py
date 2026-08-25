from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentChunkRead(BaseModel):
    chunk_index: int
    text: str
    filename: str
    document_id: str


class DocumentInspectRead(BaseModel):
    document: DocumentRead
    chunks: list[DocumentChunkRead]
    note: str = "Indexed content / chunks"
