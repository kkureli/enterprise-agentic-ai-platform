from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from app.agents.execution_trace import (
    TokenUsageCallback,
    build_execution_details,
    estimate_cost,
    merge_execution_details,
)
from app.schemas.execution import LlmUsageDetails


def test_merge_execution_details_appends_graph_path_and_timings():
    left = {
        "graph_path": ["router"],
        "timing": {"router_ms": 12.0},
        "route": "knowledge",
    }
    right = {
        "graph_path": ["rag", "finalize"],
        "timing": {"retrieval_ms": 40.0},
        "cache": {"cache_hit": False, "cache_ttl_seconds": 300},
    }

    merged = merge_execution_details(left, right)

    assert merged["graph_path"] == ["router", "rag", "finalize"]
    assert merged["timing"]["router_ms"] == 12.0
    assert merged["timing"]["retrieval_ms"] == 40.0
    assert merged["cache"]["cache_hit"] is False


def test_token_usage_callback_aggregates_calls():
    callback = TokenUsageCallback()

    first = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="ok",
                        usage_metadata={
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "total_tokens": 15,
                        },
                    )
                )
            ]
        ]
    )
    second = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="ok",
                        usage_metadata={
                            "input_tokens": 20,
                            "output_tokens": 8,
                            "total_tokens": 28,
                        },
                    )
                )
            ]
        ]
    )

    callback.on_llm_end(first)
    callback.on_llm_end(second)

    details = callback.to_details()
    assert details.llm_call_count == 2
    assert details.input_tokens == 30
    assert details.output_tokens == 13
    assert details.total_tokens == 43


def test_estimate_cost_uses_config_pricing(monkeypatch):
    monkeypatch.setattr("app.agents.execution_trace.settings.llm_input_cost_per_1m_tokens", 1.0)
    monkeypatch.setattr("app.agents.execution_trace.settings.llm_output_cost_per_1m_tokens", 2.0)

    usage = LlmUsageDetails(
        model="gpt-4.1-mini",
        llm_call_count=1,
        input_tokens=1_000_000,
        output_tokens=500_000,
        total_tokens=1_500_000,
    )

    cost = estimate_cost(usage)
    assert cost is not None
    assert cost.estimated_llm_cost_usd == 2.0
    assert cost.estimated_embedding_cost_usd is None
    assert cost.estimated_total_cost_usd == 2.0
    assert cost.label == "Estimated cost"


def test_build_execution_details_omits_secrets():
    usage = TokenUsageCallback()
    usage.llm_call_count = 1
    usage.input_tokens = 10
    usage.output_tokens = 5
    usage.total_tokens = 15

    details = build_execution_details(
        {
            "graph_path": ["router", "sql", "finalize"],
            "sql": {
                "generated_sql": "SELECT 1 FROM assets WHERE tenant_id = :tenant_id",
                "validation_status": "passed",
                "tables_used": ["assets"],
                "tenant_scope_verified": True,
                "read_only_verified": True,
                "row_count": 1,
            },
            "tools": {
                "mcp_server": "maintenance",
                "tool_name": "get_asset_status",
                "arguments": {"asset_code": "MACHINE-42"},
                "result_preview": "{'status': 'warning'}",
                "tool_type": "read",
            },
        },
        route="sql",
        usage=usage,
        total_ms=123.4,
        observability_id="thread-1",
    )

    payload = details.model_dump()
    serialized = str(payload).lower()

    assert details.route == "sql"
    assert details.graph_path == ["router", "sql", "finalize"]
    assert details.sql is not None
    assert details.sql.generated_sql is not None
    assert details.tools is not None
    assert details.observability_id == "thread-1"
    assert "api_key" not in serialized
    assert "database_url" not in serialized
    assert "redis" not in serialized
    assert "password" not in serialized


def test_knowledge_trace_includes_retrieval_and_cache_fields():
    usage = TokenUsageCallback()

    details = build_execution_details(
        {
            "graph_path": ["router", "rag", "finalize"],
            "cache": {"cache_hit": True, "cache_ttl_seconds": 300},
            "retrieval": {
                "retrieval_mode": "standard",
                "strategy": "standard hybrid retrieval with reranker fusion",
                "dense_weight": 0.7,
                "sparse_weight": 0.3,
                "candidate_count": 10,
                "reranker_enabled": True,
                "final_chunk_count": 2,
                "retrieved_candidates": [],
                "context_chunks": [],
            },
            "sources": [
                {
                    "document_id": "doc-1",
                    "filename": "equipment-error-codes.txt",
                    "chunk_index": 0,
                    "text": "E-100 lubrication pressure",
                    "score": 0.91,
                }
            ],
        },
        route="knowledge",
        usage=usage,
        total_ms=10.0,
    )

    assert details.cache is not None
    assert details.cache.cache_hit is True
    assert details.retrieval is not None
    assert details.retrieval.reranker_enabled is True
    assert details.sources is not None
    assert details.sources[0].filename == "equipment-error-codes.txt"
