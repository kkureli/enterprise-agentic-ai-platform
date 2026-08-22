import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.document import Document
from app.services.retrieval_service import RetrievalFilters, retrieve_hybrid


async def main():
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
                select(Document.tenant_id)
                .where(Document.filename == "vacation-policy.txt")
                .limit(1)
            )

            tenant_id = result.scalar_one()

        results = await retrieve_hybrid(
            tenant_id=tenant_id,
            query="How often should preventive maintenance be performed?",
            limit=5,
            filters=RetrievalFilters(
                filename="vacation-policy.txt",
            ),
        )

        for index, result in enumerate(results, start=1):
            print(f"{index}. {result.filename} (score={result.score:.4f})")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
