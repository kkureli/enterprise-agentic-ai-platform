from hashlib import sha256
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
CHUNK_SIZE = 1024 * 1024  # 1 MB


async def save_document_file(
    file: UploadFile,
    tenant_id: UUID,
    document_id: UUID,
) -> tuple[str, int, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    safe_filename = Path(file.filename).name
    extension = Path(safe_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and TXT files are supported.",
        )

    directory = Path(settings.document_storage_path) / str(tenant_id) / str(document_id)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = directory / safe_filename

    hasher = sha256()
    file_size = 0

    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    async with aiofiles.open(file_path, "wb") as output:
        while chunk := await file.read(CHUNK_SIZE):
            file_size += len(chunk)

            if file_size > max_bytes:
                await output.close()
                file_path.unlink(missing_ok=True)

                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds {settings.max_upload_size_mb} MB limit.",
                )

            hasher.update(chunk)
            await output.write(chunk)

    return (
        safe_filename,
        file_size,
        hasher.hexdigest(),
    )
