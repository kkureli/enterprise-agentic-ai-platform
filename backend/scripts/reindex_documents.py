import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.document import Document
from app.services.document_ingestion import ingest_document


async def reindex_documents() -> None:
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Document).where(
                    Document.status == "indexed",
                )
            )

            documents = result.scalars().all()

            print(f"Found {len(documents)} indexed documents.")

            for document in documents:
                file_path = (
                    Path(settings.document_storage_path)
                    / str(document.tenant_id)
                    / str(document.id)
                    / document.filename
                )

                if not file_path.exists():
                    print(f"SKIP {document.filename}: file not found at {file_path}")
                    continue

                chunk_count = await ingest_document(
                    tenant_id=document.tenant_id,
                    document_id=document.id,
                    filename=document.filename,
                    file_path=file_path,
                )

                print(f"INDEXED {document.filename}: {chunk_count} chunks")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reindex_documents())
