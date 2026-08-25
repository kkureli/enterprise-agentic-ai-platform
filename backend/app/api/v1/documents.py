from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.schemas.document import DocumentRead
from app.services.document_ingestion import ingest_document
from app.services.document_parser import DocumentParseError
from app.services.document_storage import save_document_file
from app.services.rag_cache_service import increment_rag_cache_version

router = APIRouter(
    prefix="/tenants/{tenant_id}/documents",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    tenant_id: UUID,
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    document_id = uuid4()

    filename, file_size, checksum = await save_document_file(
        file=file,
        tenant_id=tenant_id,
        document_id=document_id,
    )

    file_path = Path(settings.document_storage_path) / str(tenant_id) / str(document_id) / filename

    try:
        await ingest_document(
            tenant_id=tenant_id,
            document_id=document_id,
            filename=filename,
            file_path=file_path,
        )
    except DocumentParseError as exc:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    document = Document(
        id=document_id,
        tenant_id=tenant_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        status="indexed",
    )

    db.add(document)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    await db.refresh(document)
    await increment_rag_cache_version(tenant_id)

    return document
