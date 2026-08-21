from dataclasses import dataclass
from uuid import UUID

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.services.embedding_service import embed_query
from app.services.vector_store import get_qdrant_client


@dataclass
class RetrievedChunk:
    score: float
    document_id: str
    filename: str
    chunk_index: int
    text: str


async def retrieve_chunks(
    tenant_id: UUID,
    query: str,
    limit: int = 5,
) -> list[RetrievedChunk]:
    query_vector = await embed_query(query)

    client = get_qdrant_client()

    try:
        result = await client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(
                            value=str(tenant_id),
                        ),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )

        chunks: list[RetrievedChunk] = []

        for point in result.points:
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

    finally:
        await client.close()
