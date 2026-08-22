import asyncio
from uuid import UUID

from app.core.config import settings
from app.services.query_expansion_service import expand_query
from app.services.retrieval_service import (
    RetrievalFilters,
    RetrievedChunk,
    retrieve_hybrid,
)


async def retrieve_multi_query(
    tenant_id: UUID,
    query: str,
    limit: int = 10,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    queries = await expand_query(query)

    result_sets = await asyncio.gather(
        *[
            retrieve_hybrid(
                tenant_id=tenant_id,
                query=current_query,
                limit=limit,
                filters=filters,
            )
            for current_query in queries
        ]
    )

    scores: dict[tuple[str, int], float] = {}
    chunks: dict[tuple[str, int], RetrievedChunk] = {}

    for query_index, results in enumerate(result_sets):
        query_weight = (
            settings.original_query_weight if query_index == 0 else settings.expanded_query_weight
        )

        for rank, chunk in enumerate(results, start=1):
            key = (
                chunk.document_id,
                chunk.chunk_index,
            )

            scores[key] = scores.get(key, 0.0) + (
                query_weight / (settings.multi_query_rrf_k + rank)
            )

            chunks[key] = chunk

    ranked_keys = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    return [
        RetrievedChunk(
            score=scores[key],
            document_id=chunks[key].document_id,
            filename=chunks[key].filename,
            chunk_index=chunks[key].chunk_index,
            text=chunks[key].text,
        )
        for key in ranked_keys[:limit]
    ]
