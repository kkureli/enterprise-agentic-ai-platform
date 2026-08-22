from uuid import UUID, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    Modifier,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings


def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.qdrant_url,
    )


async def ensure_collection(
    client: AsyncQdrantClient,
    vector_size: int,
) -> None:
    exists = await client.collection_exists(
        collection_name=settings.qdrant_collection_name,
    )

    if exists:
        return

    await client.create_collection(
        collection_name=settings.qdrant_collection_name,
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
