import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.document import Document
from app.services.multi_query_retrieval_service import retrieve_multi_query
from app.services.retrieval_service import retrieve_hybrid

QUERIES = [
    "When is scheduled machine servicing required?",
    "What should technicians inspect after AX-4317 occurs?",
]


def print_results(title, results):
    print(f"\n{title}")

    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.filename} (score={result.score:.4f})")


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
                select(Document.tenant_id).where(Document.status == "indexed").limit(1)
            )

            tenant_id = result.scalar_one()

        for query in QUERIES:
            print("\n" + "=" * 70)
            print(f"QUERY: {query}")

            hybrid_results = await retrieve_hybrid(
                tenant_id=tenant_id,
                query=query,
                limit=5,
            )

            multi_query_results = await retrieve_multi_query(
                tenant_id=tenant_id,
                query=query,
                limit=5,
            )

            print_results(
                "HYBRID",
                hybrid_results,
            )

            print_results(
                "MULTI-QUERY HYBRID",
                multi_query_results,
            )

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
