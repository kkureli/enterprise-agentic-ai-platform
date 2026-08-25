from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm_service import get_chat_model
from app.services.rag_cache_service import (
    get_cached_rag_result,
    set_cached_rag_result,
)
from app.services.rag_retrieval_service import (
    RetrievalMode,
    RetrievalRunResult,
    RetrievedChunkDetail,
    retrieve_for_rag_mode,
)
from app.services.retrieval_service import RetrievalFilters

SYSTEM_PROMPT = """
You are an enterprise knowledge assistant.

Answer the user's question using only the provided context.

Rules:
- Do not use outside knowledge.
- Do not invent facts.
- If the context does not contain enough information,
  say that the provided documents do not contain enough information.
- Only cite sources that directly support the answer.
- Return the source numbers that support the answer.
- Answer clearly and concisely.
""".strip()


class GroundedAnswer(BaseModel):
    answer: str
    used_sources: list[int] = Field(default_factory=list)


@dataclass
class RagSource:
    document_id: str
    filename: str
    chunk_index: int
    score: float
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieval_method: str | None = None
    text: str = ""


@dataclass
class RagRetrievedChunk:
    document_id: str
    filename: str
    chunk_index: int
    score: float
    text: str
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieval_method: str | None = None


@dataclass
class RagResult:
    answer: str
    sources: list[RagSource]
    retrieved_chunks: list[RagRetrievedChunk]
    cache_hit: bool = False
    retrieval: RetrievalRunResult | None = None
    llm_generation_ms: float | None = None


def build_context(chunks: list[RetrievedChunkDetail]) -> str:
    return "\n\n".join(
        (
            f"[Source {index}]\n"
            f"Filename: {chunk.filename}\n"
            f"Chunk: {chunk.chunk_index}\n"
            f"Content: {chunk.text}"
        )
        for index, chunk in enumerate(chunks, start=1)
    )


def _to_rag_chunks(chunks: list[RetrievedChunkDetail]) -> list[RagRetrievedChunk]:
    return [
        RagRetrievedChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            score=chunk.score,
            text=chunk.text,
            retrieval_score=chunk.retrieval_score,
            rerank_score=chunk.rerank_score,
            retrieval_method=chunk.retrieval_method,
        )
        for chunk in chunks
    ]


async def answer_question(
    tenant_id: UUID,
    question: str,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    retrieval_mode: RetrievalMode = "standard",
) -> RagResult:
    import time

    cached = await get_cached_rag_result(
        tenant_id=tenant_id,
        question=question,
        limit=limit,
        retrieval_mode=retrieval_mode,
        filters=filters,
    )

    if cached is not None:
        cached.cache_hit = True
        return cached

    run = await retrieve_for_rag_mode(
        tenant_id=tenant_id,
        query=question,
        limit=limit,
        filters=filters,
        mode=retrieval_mode,
    )

    chunks = run.chunks

    if not chunks:
        result = RagResult(
            answer=("The provided documents do not contain enough information."),
            sources=[],
            retrieved_chunks=[],
            cache_hit=False,
            retrieval=run,
        )
        await set_cached_rag_result(
            tenant_id=tenant_id,
            question=question,
            result=result,
            limit=limit,
            retrieval_mode=retrieval_mode,
            filters=filters,
        )
        return result

    context = build_context(chunks)

    user_prompt = f"""
Question:
{question}

Context:
{context}
""".strip()

    model = get_chat_model().with_structured_output(GroundedAnswer)

    llm_started = time.perf_counter()
    grounded = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", user_prompt),
        ]
    )
    llm_generation_ms = round((time.perf_counter() - llm_started) * 1000, 2)

    valid_source_ids: list[int] = []

    for source_id in grounded.used_sources:
        if 1 <= source_id <= len(chunks):
            if source_id not in valid_source_ids:
                valid_source_ids.append(source_id)

    sources = []

    for source_id in valid_source_ids:
        chunk = chunks[source_id - 1]

        sources.append(
            RagSource(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                score=chunk.score,
                retrieval_score=chunk.retrieval_score,
                rerank_score=chunk.rerank_score,
                retrieval_method=chunk.retrieval_method,
                text=chunk.text,
            )
        )

    result = RagResult(
        answer=grounded.answer,
        sources=sources,
        retrieved_chunks=_to_rag_chunks(chunks),
        cache_hit=False,
        retrieval=run,
        llm_generation_ms=llm_generation_ms,
    )

    await set_cached_rag_result(
        tenant_id=tenant_id,
        question=question,
        result=result,
        limit=limit,
        retrieval_mode=retrieval_mode,
        filters=filters,
    )

    return result
