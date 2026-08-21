from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm_service import get_chat_model
from app.services.retrieval_service import RetrievedChunk, retrieve_chunks

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


@dataclass
class RagRetrievedChunk:
    document_id: str
    filename: str
    chunk_index: int
    score: float
    text: str


@dataclass
class RagResult:
    answer: str
    sources: list[RagSource]
    retrieved_chunks: list[RagRetrievedChunk]


def build_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        (
            f"[Source {index}]\n"
            f"Filename: {chunk.filename}\n"
            f"Chunk: {chunk.chunk_index}\n"
            f"Content: {chunk.text}"
        )
        for index, chunk in enumerate(chunks, start=1)
    )


async def answer_question(
    tenant_id: UUID,
    question: str,
    limit: int = 5,
) -> RagResult:
    chunks = await retrieve_chunks(
        tenant_id=tenant_id,
        query=question,
        limit=limit,
    )

    if not chunks:
        return RagResult(
            answer=("The provided documents do not contain enough information."),
            sources=[],
            retrieved_chunks=[],
        )

    context = build_context(chunks)

    user_prompt = f"""
Question:
{question}

Context:
{context}
""".strip()

    model = get_chat_model().with_structured_output(GroundedAnswer)

    result = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", user_prompt),
        ]
    )

    valid_source_ids: list[int] = []

    for source_id in result.used_sources:
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
            )
        )

    retrieved_chunks = [
        RagRetrievedChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            score=chunk.score,
            text=chunk.text,
        )
        for chunk in chunks
    ]

    return RagResult(
        answer=result.answer,
        sources=sources,
        retrieved_chunks=retrieved_chunks,
    )
