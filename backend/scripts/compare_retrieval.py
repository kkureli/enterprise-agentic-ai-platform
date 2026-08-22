import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.document import Document
from app.services.reranker_service import rerank_chunks
from app.services.retrieval_service import (
    retrieve_dense,
    retrieve_hybrid,
    retrieve_sparse,
)

QUERIES = [
    "What does error code AX-4317 indicate?",
    "How often should preventive maintenance be performed?",
    "When is scheduled machine servicing required?",
    "How many paid vacation days do employees receive?",
]


def print_results(title, results):
    print(f"\n{title}")

    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.filename} (score={result.score:.4f})")


def print_reranked_results(title, results):
    print(f"\n{title}")

    for index, result in enumerate(results, start=1):
        print(
            f"{index}. {result.filename} "
            f"(rrf={result.retrieval_score:.4f}, "
            f"rerank={result.rerank_score:.4f})"
        )


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

            dense_results = await retrieve_dense(
                tenant_id=tenant_id,
                query=query,
                limit=5,
            )

            sparse_results = await retrieve_sparse(
                tenant_id=tenant_id,
                query=query,
                limit=5,
            )

            hybrid_results = await retrieve_hybrid(
                tenant_id=tenant_id,
                query=query,
                limit=5,
            )

            reranked_results = await rerank_chunks(
                query=query,
                chunks=hybrid_results,
                limit=5,
            )

            print_results("DENSE", dense_results)
            print_results("SPARSE", sparse_results)
            print_results("HYBRID", hybrid_results)
            print_reranked_results("RERANKED", reranked_results)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
