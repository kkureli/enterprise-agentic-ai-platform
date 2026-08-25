from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.core.config import settings
from app.services.multi_query_retrieval_service import retrieve_multi_query
from app.services.query_expansion_service import expand_query
from app.services.reranker_service import RerankedChunk, rerank_chunks
from app.services.retrieval_service import (
    RetrievalFilters,
    RetrievedChunk,
    get_candidate_limit,
    get_retrieval_weights,
    retrieve_hybrid,
)


def _chunk_key(chunk: RetrievedChunk | RerankedChunk) -> tuple[str, int]:
    return (
        chunk.document_id,
        chunk.chunk_index,
    )


@dataclass
class RetrievedChunkDetail:
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieval_method: str | None = None


@dataclass
class RetrievalRunResult:
    chunks: list[RetrievedChunkDetail]
    retrieval_mode: str
    strategy: str
    query_rewrites: list[str] | None
    dense_weight: float
    sparse_weight: float
    candidate_count: int
    reranker_enabled: bool
    final_chunk_count: int
    retrieval_ms: float
    reranking_ms: float
    metadata_filters: dict | None = None


def fuse_base_and_reranker_rankings(
    base_chunks: list[RetrievedChunk],
    reranked_chunks: list[RerankedChunk],
    limit: int,
    *,
    retrieval_method: str,
) -> list[RetrievedChunkDetail]:
    base_ranks = {_chunk_key(chunk): rank for rank, chunk in enumerate(base_chunks, start=1)}
    reranker_ranks = {
        _chunk_key(chunk): rank for rank, chunk in enumerate(reranked_chunks, start=1)
    }
    rerank_scores = {_chunk_key(chunk): chunk.rerank_score for chunk in reranked_chunks}
    retrieval_scores = {_chunk_key(chunk): chunk.score for chunk in base_chunks}

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
        RetrievedChunkDetail(
            score=scores[key],
            document_id=chunks_by_key[key].document_id,
            filename=chunks_by_key[key].filename,
            chunk_index=chunks_by_key[key].chunk_index,
            text=chunks_by_key[key].text,
            retrieval_score=retrieval_scores.get(key),
            rerank_score=rerank_scores.get(key),
            retrieval_method=retrieval_method,
        )
        for key in ranked_keys[:limit]
    ]


async def retrieve_for_rag(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> tuple[list[RetrievedChunkDetail], int, float, float]:
    import time

    candidate_limit = get_candidate_limit(limit)

    retrieval_started = time.perf_counter()
    hybrid_candidates = await retrieve_hybrid(
        tenant_id=tenant_id,
        query=query,
        limit=candidate_limit,
        filters=filters,
    )
    retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)

    rerank_started = time.perf_counter()
    reranked_candidates = await rerank_chunks(
        query=query,
        chunks=hybrid_candidates,
        limit=len(hybrid_candidates),
    )
    reranking_ms = round((time.perf_counter() - rerank_started) * 1000, 2)

    fused = fuse_base_and_reranker_rankings(
        base_chunks=hybrid_candidates,
        reranked_chunks=reranked_candidates,
        limit=limit,
        retrieval_method="hybrid+rerank",
    )

    return fused, len(hybrid_candidates), retrieval_ms, reranking_ms


async def retrieve_multi_query_for_rag(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> tuple[list[RetrievedChunkDetail], list[str], int, float, float]:
    import time

    candidate_limit = get_candidate_limit(limit)

    expand_started = time.perf_counter()
    queries = await expand_query(query)
    expand_ms = round((time.perf_counter() - expand_started) * 1000, 2)

    retrieval_started = time.perf_counter()
    candidates = await retrieve_multi_query(
        tenant_id=tenant_id,
        query=query,
        limit=candidate_limit,
        filters=filters,
        precomputed_queries=queries,
    )
    retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2) + expand_ms

    rerank_started = time.perf_counter()
    reranked = await rerank_chunks(
        query=query,
        chunks=candidates,
        limit=len(candidates),
    )
    reranking_ms = round((time.perf_counter() - rerank_started) * 1000, 2)

    fused = fuse_base_and_reranker_rankings(
        base_chunks=candidates,
        reranked_chunks=reranked,
        limit=limit,
        retrieval_method="multi-query+hybrid+rerank",
    )

    return fused, queries, len(candidates), retrieval_ms, reranking_ms


RetrievalMode = Literal["standard", "advanced"]


def _filters_payload(filters: RetrievalFilters | None) -> dict | None:
    if filters is None:
        return None

    payload = {
        "document_id": str(filters.document_id) if filters.document_id else None,
        "filename": filters.filename,
    }

    if payload["document_id"] is None and payload["filename"] is None:
        return None

    return payload


async def retrieve_for_rag_mode(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    mode: RetrievalMode = "standard",
) -> RetrievalRunResult:
    dense_weight, sparse_weight = get_retrieval_weights(query)

    if mode == "advanced":
        (
            chunks,
            queries,
            candidate_count,
            retrieval_ms,
            reranking_ms,
        ) = await retrieve_multi_query_for_rag(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
            filters=filters,
        )
        rewrites = queries[1:] if len(queries) > 1 else []
        return RetrievalRunResult(
            chunks=chunks,
            retrieval_mode=mode,
            strategy="advanced hybrid multi-query with reranker fusion",
            query_rewrites=rewrites or None,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            candidate_count=candidate_count,
            reranker_enabled=True,
            final_chunk_count=len(chunks),
            retrieval_ms=retrieval_ms,
            reranking_ms=reranking_ms,
            metadata_filters=_filters_payload(filters),
        )

    chunks, candidate_count, retrieval_ms, reranking_ms = await retrieve_for_rag(
        tenant_id=tenant_id,
        query=query,
        limit=limit,
        filters=filters,
    )

    return RetrievalRunResult(
        chunks=chunks,
        retrieval_mode=mode,
        strategy="standard hybrid retrieval with reranker fusion",
        query_rewrites=None,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
        candidate_count=candidate_count,
        reranker_enabled=True,
        final_chunk_count=len(chunks),
        retrieval_ms=retrieval_ms,
        reranking_ms=reranking_ms,
        metadata_filters=_filters_payload(filters),
    )
