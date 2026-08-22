import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from app.core.config import settings
from app.models.document import Document
from app.services.multi_query_retrieval_service import retrieve_multi_query
from app.services.rag_retrieval_service import (
    retrieve_for_rag,
    retrieve_multi_query_for_rag,
)
from app.services.retrieval_service import (
    RetrievedChunk,
    retrieve_dense,
    retrieve_hybrid,
    retrieve_sparse,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from evals.retrieval.metrics import ndcg_at_k, recall_at_k, reciprocal_rank

DATASET_PATH = Path("evals/datasets/retrieval_golden.jsonl")
RESULTS_PATH = Path("evals/results/retrieval_results.json")
EVAL_K = 3

Retriever = Callable[
    [object, str, int],
    Awaitable[list[RetrievedChunk]],
]


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


async def get_tenant_id():
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

            return result.scalar_one()

    finally:
        await engine.dispose()


async def evaluate_strategy(
    name: str,
    retriever,
    dataset: list[dict],
    tenant_id,
) -> dict[str, float]:
    recalls = []
    reciprocal_ranks = []
    ndcgs = []

    print(f"\n{name} — {len(dataset)} queries\n")

    for case in dataset:
        results = await retriever(
            tenant_id=tenant_id,
            query=case["query"],
            limit=EVAL_K,
        )

        retrieved_documents = [result.filename for result in results]

        relevant_documents = case["relevant_documents"]

        recall = recall_at_k(
            retrieved_documents,
            relevant_documents,
            EVAL_K,
        )

        rr = reciprocal_rank(
            retrieved_documents,
            relevant_documents,
        )

        ndcg = ndcg_at_k(
            retrieved_documents,
            relevant_documents,
            EVAL_K,
        )

        recalls.append(recall)
        reciprocal_ranks.append(rr)
        ndcgs.append(ndcg)

        print(f"{case['id']:<28} R@{EVAL_K}={recall:.3f} RR={rr:.3f} nDCG={ndcg:.3f}")

    return {
        "recall": mean(recalls),
        "mrr": mean(reciprocal_ranks),
        "ndcg": mean(ndcgs),
    }


async def main():
    dataset = load_dataset()
    tenant_id = await get_tenant_id()

    strategies = {
        "Dense": retrieve_dense,
        "Sparse": retrieve_sparse,
        "Hybrid": retrieve_hybrid,
        "Hybrid + Reranker": retrieve_for_rag,
        "Multi-Query Hybrid": retrieve_multi_query,
        "Multi-Query + Reranker": retrieve_multi_query_for_rag,
    }

    summaries = {}

    for name, retriever in strategies.items():
        summaries[name] = await evaluate_strategy(
            name=name,
            retriever=retriever,
            dataset=dataset,
            tenant_id=tenant_id,
        )

    print("\n" + "=" * 72)
    print(f"{'Strategy':<22}{'Recall@3':>12}{'MRR':>12}{'nDCG@3':>12}")
    print("-" * 72)

    for name, scores in summaries.items():
        print(
            f"{name:<22}"
            f"{scores['recall']:>12.4f}"
            f"{scores['mrr']:>12.4f}"
            f"{scores['ndcg']:>12.4f}"
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "eval_k": EVAL_K,
        "num_queries": len(dataset),
        "dataset_path": str(DATASET_PATH),
        "strategies": {
            name: {
                f"recall@{EVAL_K}": scores["recall"],
                "mrr": scores["mrr"],
                f"ndcg@{EVAL_K}": scores["ndcg"],
            }
            for name, scores in summaries.items()
        },
    }

    RESULTS_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nWrote evaluation results to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
