from pathlib import Path
from uuid import UUID

from app.services.document_chunker import chunk_document
from app.services.document_parser import parse_document
from app.services.embedding_service import embed_documents
from app.services.vector_store import index_document_chunks


async def ingest_document(
    tenant_id: UUID,
    document_id: UUID,
    filename: str,
    file_path: Path,
) -> int:
    text = await parse_document(file_path)

    chunks = chunk_document(text)

    if not chunks:
        raise ValueError("Document produced no chunks.")

    embeddings = await embed_documents(chunks)

    await index_document_chunks(
        tenant_id=tenant_id,
        document_id=document_id,
        filename=filename,
        chunks=chunks,
        embeddings=embeddings,
    )

    return len(chunks)
