import asyncio
from dataclasses import dataclass
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.services.retrieval_service import RetrievedChunk

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class RerankedChunk:
    document_id: str
    filename: str
    chunk_index: int
    text: str
    retrieval_score: float
    rerank_score: float


@lru_cache
def get_reranker() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL_NAME)


async def rerank_chunks(
    query: str,
    chunks: list[RetrievedChunk],
    limit: int = 5,
) -> list[RerankedChunk]:
    if not chunks:
        return []

    model = get_reranker()

    pairs = [(query, chunk.text) for chunk in chunks]

    scores = await asyncio.to_thread(
        model.predict,
        pairs,
    )

    reranked = [
        RerankedChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            retrieval_score=chunk.score,
            rerank_score=float(score),
        )
        for chunk, score in zip(
            chunks,
            scores,
            strict=True,
        )
    ]

    reranked.sort(
        key=lambda chunk: chunk.rerank_score,
        reverse=True,
    )

    return reranked[:limit]
