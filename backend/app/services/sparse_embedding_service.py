from functools import lru_cache

from fastembed import SparseTextEmbedding
from qdrant_client.models import SparseVector

SPARSE_MODEL_NAME = "Qdrant/bm25"


@lru_cache
def get_sparse_embedding_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(
        model_name=SPARSE_MODEL_NAME,
    )


def embed_sparse_documents(
    texts: list[str],
) -> list[SparseVector]:
    model = get_sparse_embedding_model()

    embeddings = model.embed(texts)

    return [
        SparseVector(
            indices=embedding.indices.tolist(),
            values=embedding.values.tolist(),
        )
        for embedding in embeddings
    ]


def embed_sparse_query(
    text: str,
) -> SparseVector:
    model = get_sparse_embedding_model()

    embedding = next(iter(model.query_embed(text)))

    return SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )
