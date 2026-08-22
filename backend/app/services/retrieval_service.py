import asyncio
import re
from dataclasses import dataclass
from uuid import UUID

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.services.embedding_service import embed_query
from app.services.sparse_embedding_service import embed_sparse_query
from app.services.vector_store import get_qdrant_client


@dataclass
class RetrievedChunk:
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str


STRONG_IDENTIFIER_PATTERN = re.compile(
    r"\b[A-Z]{2,4}[-_]\d{3,6}\b",
)


def get_retrieval_weights(query: str) -> tuple[float, float]:
    if STRONG_IDENTIFIER_PATTERN.search(query):
        return (
            settings.dense_identifier_weight,
            settings.sparse_identifier_weight,
        )

    return (
        settings.dense_retrieval_weight,
        settings.sparse_retrieval_weight,
    )


def get_candidate_limit(limit: int) -> int:
    return max(
        limit * settings.retrieval_candidate_multiplier,
        settings.retrieval_candidate_min,
    )


@dataclass
class RetrievalFilters:
    document_id: UUID | None = None
    filename: str | None = None


def build_retrieval_filter(
    tenant_id: UUID,
    filters: RetrievalFilters | None = None,
) -> Filter:
    conditions = [
        FieldCondition(
            key="tenant_id",
            match=MatchValue(
                value=str(tenant_id),
            ),
        )
    ]

    if filters is not None:
        if filters.document_id is not None:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=str(filters.document_id),
                    ),
                )
            )

        if filters.filename is not None:
            conditions.append(
                FieldCondition(
                    key="filename",
                    match=MatchValue(
                        value=filters.filename,
                    ),
                )
            )

    return Filter(must=conditions)


def map_results(points) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []

    for point in points:
        payload = point.payload or {}

        chunks.append(
            RetrievedChunk(
                score=point.score,
                document_id=str(payload["document_id"]),
                filename=str(payload["filename"]),
                chunk_index=int(payload["chunk_index"]),
                text=str(payload["text"]),
            )
        )

    return chunks


async def retrieve_dense(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    query_vector = await embed_query(query)

    client = get_qdrant_client()

    try:
        result = await client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            using="dense",
            query_filter=build_retrieval_filter(
                tenant_id=tenant_id,
                filters=filters,
            ),
            limit=limit,
            with_payload=True,
        )

        return map_results(result.points)

    finally:
        await client.close()


async def retrieve_sparse(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    query_vector = embed_sparse_query(query)

    client = get_qdrant_client()

    try:
        result = await client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            using="sparse",
            query_filter=build_retrieval_filter(
                tenant_id=tenant_id,
                filters=filters,
            ),
            limit=limit,
            with_payload=True,
        )

        return map_results(result.points)

    finally:
        await client.close()


async def retrieve_hybrid(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    candidate_limit = get_candidate_limit(limit)

    dense_results, sparse_results = await asyncio.gather(
        retrieve_dense(
            tenant_id=tenant_id,
            query=query,
            limit=candidate_limit,
            filters=filters,
        ),
        retrieve_sparse(
            tenant_id=tenant_id,
            query=query,
            limit=candidate_limit,
            filters=filters,
        ),
    )

    dense_weight, sparse_weight = get_retrieval_weights(query)

    scores: dict[tuple[str, int], float] = {}
    chunks: dict[tuple[str, int], RetrievedChunk] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        key = (
            chunk.document_id,
            chunk.chunk_index,
        )

        scores[key] = scores.get(key, 0.0) + (dense_weight / (settings.rrf_k + rank))

        chunks[key] = chunk

    for rank, chunk in enumerate(sparse_results, start=1):
        key = (
            chunk.document_id,
            chunk.chunk_index,
        )

        scores[key] = scores.get(key, 0.0) + (sparse_weight / (settings.rrf_k + rank))

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


async def retrieve_chunks(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    return await retrieve_hybrid(
        tenant_id=tenant_id,
        query=query,
        limit=limit,
        filters=filters,
    )
