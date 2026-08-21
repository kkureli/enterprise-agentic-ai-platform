from uuid import UUID, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

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
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


async def index_document_chunks(
    tenant_id: UUID,
    document_id: UUID,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings must have the same length.")

    if not chunks:
        return

    vector_size = len(embeddings[0])

    client = get_qdrant_client()

    try:
        await ensure_collection(
            client=client,
            vector_size=vector_size,
        )

        points = []

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            point_id = uuid5(
                document_id,
                str(index),
            )

            points.append(
                PointStruct(
                    id=str(point_id),
                    vector=embedding,
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
