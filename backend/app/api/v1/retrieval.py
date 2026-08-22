from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.retrieval import RetrievalRequest, RetrievedChunkRead
from app.services.retrieval_service import (
    RetrievalFilters,
    retrieve_chunks,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/retrieval",
    tags=["Retrieval"],
)


@router.post(
    "",
    response_model=list[RetrievedChunkRead],
)
async def retrieve(
    tenant_id: UUID,
    payload: RetrievalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    results = await retrieve_chunks(
        tenant_id=tenant_id,
        query=payload.query,
        limit=payload.limit,
        filters=RetrievalFilters(
            document_id=payload.document_id,
            filename=payload.filename,
        ),
    )

    return [
        RetrievedChunkRead(
            score=result.score,
            document_id=result.document_id,
            filename=result.filename,
            chunk_index=result.chunk_index,
            text=result.text,
        )
        for result in results
    ]
