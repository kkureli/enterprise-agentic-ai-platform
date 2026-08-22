from typing import Literal
from uuid import UUID

from app.core.config import settings
from app.services.multi_query_retrieval_service import retrieve_multi_query
from app.services.reranker_service import RerankedChunk, rerank_chunks
from app.services.retrieval_service import (
    RetrievalFilters,
    RetrievedChunk,
    get_candidate_limit,
    retrieve_hybrid,
)


def _chunk_key(chunk: RetrievedChunk | RerankedChunk) -> tuple[str, int]:
    return (
        chunk.document_id,
        chunk.chunk_index,
    )


def fuse_base_and_reranker_rankings(
    base_chunks: list[RetrievedChunk],
    reranked_chunks: list[RerankedChunk],
    limit: int,
) -> list[RetrievedChunk]:
    base_ranks = {_chunk_key(chunk): rank for rank, chunk in enumerate(base_chunks, start=1)}
    reranker_ranks = {
        _chunk_key(chunk): rank for rank, chunk in enumerate(reranked_chunks, start=1)
    }

    chunks_by_key = {_chunk_key(chunk): chunk for chunk in base_chunks}

    scores: dict[tuple[str, int], float] = {}

    for key in chunks_by_key:
        score = 0.0

        if key in base_ranks:
            score += settings.hybrid_rank_weight / (settings.final_rrf_k + base_ranks[key])

        if key in reranker_ranks:
            score += settings.reranker_rank_weight / (settings.final_rrf_k + reranker_ranks[key])

        scores[key] = score

    ranked_keys = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    return [
        RetrievedChunk(
            score=scores[key],
            document_id=chunks_by_key[key].document_id,
            filename=chunks_by_key[key].filename,
            chunk_index=chunks_by_key[key].chunk_index,
            text=chunks_by_key[key].text,
        )
        for key in ranked_keys[:limit]
    ]


async def retrieve_for_rag(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    candidate_limit = get_candidate_limit(limit)

    hybrid_candidates = await retrieve_hybrid(
        tenant_id=tenant_id,
        query=query,
        limit=candidate_limit,
        filters=filters,
    )

    reranked_candidates = await rerank_chunks(
        query=query,
        chunks=hybrid_candidates,
        limit=len(hybrid_candidates),
    )

    return fuse_base_and_reranker_rankings(
        base_chunks=hybrid_candidates,
        reranked_chunks=reranked_candidates,
        limit=limit,
    )


async def retrieve_multi_query_for_rag(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    candidate_limit = get_candidate_limit(limit)

    candidates = await retrieve_multi_query(
        tenant_id=tenant_id,
        query=query,
        limit=candidate_limit,
        filters=filters,
    )

    reranked = await rerank_chunks(
        query=query,
        chunks=candidates,
        limit=len(candidates),
    )

    return fuse_base_and_reranker_rankings(
        base_chunks=candidates,
        reranked_chunks=reranked,
        limit=limit,
    )


RetrievalMode = Literal["standard", "advanced"]


async def retrieve_for_rag_mode(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    mode: RetrievalMode = "standard",
) -> list[RetrievedChunk]:
    if mode == "advanced":
        return await retrieve_multi_query_for_rag(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
            filters=filters,
        )

    return await retrieve_for_rag(
        tenant_id=tenant_id,
        query=query,
        limit=limit,
        filters=filters,
    )
