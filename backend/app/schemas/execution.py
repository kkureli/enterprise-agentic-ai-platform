from typing import Any, Literal

from pydantic import BaseModel, Field


class RetrievalChunkDetail(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float | None = None
    retrieval_score: float | None = None
    rerank_score: float | None = None
    retrieval_method: str | None = None


class RetrievalDetails(BaseModel):
    retrieval_mode: str | None = None
    strategy: str | None = None
    query_rewrites: list[str] | None = None
    dense_weight: float | None = None
    sparse_weight: float | None = None
    metadata_filters: dict[str, Any] | None = None
    candidate_count: int | None = None
    reranker_enabled: bool | None = None
    final_chunk_count: int | None = None
    retrieved_candidates: list[RetrievalChunkDetail] = Field(default_factory=list)
    context_chunks: list[RetrievalChunkDetail] = Field(default_factory=list)


class CacheDetails(BaseModel):
    cache_hit: bool
    cache_ttl_seconds: int | None = None


class SqlDetails(BaseModel):
    generated_sql: str | None = None
    validation_status: Literal["passed", "failed"] | None = None
    tables_used: list[str] | None = None
    tenant_scope_verified: bool | None = None
    read_only_verified: bool | None = None
    row_count: int | None = None
    execution_duration_ms: float | None = None
    generation_duration_ms: float | None = None


class ToolDetails(BaseModel):
    mcp_server: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result_preview: str | None = None
    tool_type: Literal["read", "write"] | None = None
    execution_duration_ms: float | None = None
    requires_approval: bool | None = None
    approval_status: str | None = None
    action_result: dict[str, Any] | None = None
    tenant_slug: str | None = None


class HitlDetails(BaseModel):
    required: bool | None = None
    approved: bool | None = None
    pending_action: dict[str, Any] | None = None
    action_result: dict[str, Any] | None = None


class LlmUsageDetails(BaseModel):
    model: str | None = None
    llm_call_count: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class CostDetails(BaseModel):
    estimated_llm_cost_usd: float | None = None
    estimated_embedding_cost_usd: float | None = None
    estimated_total_cost_usd: float | None = None
    label: str = "Estimated cost"


class TimingDetails(BaseModel):
    total_ms: float | None = None
    router_ms: float | None = None
    planner_ms: float | None = None
    retrieval_ms: float | None = None
    reranking_ms: float | None = None
    sql_generation_ms: float | None = None
    sql_execution_ms: float | None = None
    tool_execution_ms: float | None = None
    llm_generation_ms: float | None = None
    synthesis_ms: float | None = None
    write_gate_ms: float | None = None


class ExecutionDetails(BaseModel):
    route: str | None = None
    selected_capabilities: list[str] = Field(default_factory=list)
    graph_path: list[str] = Field(default_factory=list)
    retrieval: RetrievalDetails | None = None
    sources: list[RetrievalChunkDetail] | None = None
    sql: SqlDetails | None = None
    tools: ToolDetails | None = None
    hitl: HitlDetails | None = None
    cache: CacheDetails | None = None
    llm_usage: LlmUsageDetails | None = None
    cost: CostDetails | None = None
    timing: TimingDetails | None = None
    observability_id: str | None = None
