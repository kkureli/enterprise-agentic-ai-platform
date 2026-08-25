from uuid import UUID, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    Modifier,
    PayloadSchemaType,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings


def get_qdrant_client() -> AsyncQdrantClient:
    if settings.qdrant_api_key:
        return AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    return AsyncQdrantClient(
        url=settings.qdrant_url,
    )


async def ensure_collection(
    client: AsyncQdrantClient,
    vector_size: int,
) -> None:
    collection_name = settings.qdrant_collection_name

    exists = await client.collection_exists(
        collection_name=collection_name,
    )

    if not exists:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    modifier=Modifier.IDF,
                )
            },
        )

    collection = await client.get_collection(
        collection_name=collection_name,
    )

    if "tenant_id" not in collection.payload_schema:
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="tenant_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )


async def index_document_chunks(
    tenant_id: UUID,
    document_id: UUID,
    filename: str,
    chunks: list[str],
    dense_embeddings: list[list[float]],
    sparse_embeddings: list[SparseVector],
) -> None:
    if len(chunks) != len(dense_embeddings):
        raise ValueError("Chunks and dense embeddings must have the same length.")

    if len(chunks) != len(sparse_embeddings):
        raise ValueError("Chunks and sparse embeddings must have the same length.")

    if not chunks:
        return

    vector_size = len(dense_embeddings[0])

    client = get_qdrant_client()

    try:
        await ensure_collection(
            client=client,
            vector_size=vector_size,
        )

        points = []

        for index, (
            chunk,
            dense_embedding,
            sparse_embedding,
        ) in enumerate(
            zip(
                chunks,
                dense_embeddings,
                sparse_embeddings,
                strict=True,
            )
        ):
            point_id = uuid5(
                document_id,
                str(index),
            )

            points.append(
                PointStruct(
                    id=str(point_id),
                    vector={
                        "dense": dense_embedding,
                        "sparse": sparse_embedding,
                    },
                    payload={
                        "tenant_id": str(tenant_id),
                        "document_id": str(document_id),
                        "filename": filename,
                        "chunk_index": index,
                        "text": chunk,
                    },
                )
            )

        await client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
        )

    finally:
        await client.close()


async def list_document_chunks(
    tenant_id: UUID,
    document_id: UUID,
) -> list[dict]:
    """Return indexed chunk payloads for a tenant-scoped document."""

    client = get_qdrant_client()

    try:
        exists = await client.collection_exists(
            collection_name=settings.qdrant_collection_name,
        )

        if not exists:
            return []

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=str(tenant_id)),
                ),
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                ),
            ]
        )

        chunks: list[dict] = []
        next_offset = None

        while True:
            points, next_offset = await client.scroll(
                collection_name=settings.qdrant_collection_name,
                scroll_filter=query_filter,
                limit=100,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                chunks.append(
                    {
                        "chunk_index": int(payload.get("chunk_index", 0)),
                        "text": str(payload.get("text", "")),
                        "filename": str(payload.get("filename", "")),
                        "document_id": str(payload.get("document_id", document_id)),
                    }
                )

            if next_offset is None:
                break

        chunks.sort(key=lambda item: item["chunk_index"])
        return chunks

    finally:
        await client.close()
