from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.rag import (
    RagRequest,
    RagResponse,
    RagRetrievedChunkRead,
    RagSourceRead,
)
from app.services.rag_service import answer_question
from app.services.retrieval_service import RetrievalFilters

router = APIRouter(
    prefix="/tenants/{tenant_id}/rag",
    tags=["RAG"],
)


@router.post(
    "",
    response_model=RagResponse,
)
async def rag(
    tenant_id: UUID,
    payload: RagRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    result = await answer_question(
        tenant_id=tenant_id,
        question=payload.question,
        limit=payload.limit,
        filters=RetrievalFilters(
            document_id=payload.document_id,
            filename=payload.filename,
        ),
        retrieval_mode=payload.retrieval_mode,
    )

    return RagResponse(
        answer=result.answer,
        sources=[
            RagSourceRead(
                document_id=source.document_id,
                filename=source.filename,
                chunk_index=source.chunk_index,
                score=source.score,
            )
            for source in result.sources
        ],
        retrieved_chunks=[
            RagRetrievedChunkRead(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                score=chunk.score,
                text=chunk.text,
            )
            for chunk in result.retrieved_chunks
        ],
    )
