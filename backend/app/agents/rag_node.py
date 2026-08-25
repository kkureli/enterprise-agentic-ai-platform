import time

from app.agents.execution_trace import elapsed_ms, node_trace
from app.agents.state import AgentState
from app.core.config import settings
from app.services.rag_service import answer_question


def _chunk_payload(chunk) -> dict:
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "chunk_index": chunk.chunk_index,
        "text": getattr(chunk, "text", ""),
        "score": chunk.score,
        "retrieval_score": getattr(chunk, "retrieval_score", None),
        "rerank_score": getattr(chunk, "rerank_score", None),
        "retrieval_method": getattr(chunk, "retrieval_method", None),
    }


async def rag_node(state: AgentState) -> dict:
    started = time.perf_counter()

    result = await answer_question(
        tenant_id=state["tenant_id"],
        question=state["query"],
        retrieval_mode=state.get("retrieval_mode", "standard"),
    )

    timing: dict = {}
    retrieval_payload = None
    sources_payload = [_chunk_payload(source) for source in result.sources]

    if result.retrieval is not None:
        run = result.retrieval
        timing["retrieval_ms"] = run.retrieval_ms
        timing["reranking_ms"] = run.reranking_ms
        retrieved_candidates = [_chunk_payload(chunk) for chunk in run.chunks]
        retrieval_payload = {
            "retrieval_mode": run.retrieval_mode,
            "strategy": run.strategy,
            "query_rewrites": run.query_rewrites,
            "dense_weight": run.dense_weight,
            "sparse_weight": run.sparse_weight,
            "metadata_filters": run.metadata_filters,
            "candidate_count": run.candidate_count,
            "reranker_enabled": run.reranker_enabled,
            "final_chunk_count": run.final_chunk_count,
            "retrieved_candidates": retrieved_candidates,
            "context_chunks": [_chunk_payload(chunk) for chunk in result.retrieved_chunks],
        }

    if result.llm_generation_ms is not None:
        timing["llm_generation_ms"] = result.llm_generation_ms

    timing.setdefault("retrieval_ms", timing.get("retrieval_ms"))
    _ = elapsed_ms(started)

    return {
        "rag_answer": result.answer,
        **node_trace(
            "rag",
            route="knowledge",
            cache={
                "cache_hit": result.cache_hit,
                "cache_ttl_seconds": settings.rag_cache_ttl_seconds,
            },
            retrieval=retrieval_payload,
            sources=sources_payload,
            timing=timing or None,
        ),
    }
