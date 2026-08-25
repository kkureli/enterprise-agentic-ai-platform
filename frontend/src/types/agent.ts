export type AgentRoute = 'knowledge' | 'sql' | 'tool' | 'unsupported'

export type AgentStatus = 'completed' | 'approval_required'

export type RetrievalMode = 'standard' | 'advanced'

export type PendingAction = {
  tool_name: string
  arguments: Record<string, string>
}

export type RetrievalChunkDetail = {
  document_id: string
  filename: string
  chunk_index: number
  text: string
  score?: number | null
  retrieval_score?: number | null
  rerank_score?: number | null
  retrieval_method?: string | null
}

export type ExecutionDetails = {
  route?: string | null
  selected_capabilities?: string[]
  graph_path?: string[]
  retrieval?: {
    retrieval_mode?: string | null
    strategy?: string | null
    query_rewrites?: string[] | null
    dense_weight?: number | null
    sparse_weight?: number | null
    metadata_filters?: Record<string, unknown> | null
    candidate_count?: number | null
    reranker_enabled?: boolean | null
    final_chunk_count?: number | null
    retrieved_candidates?: RetrievalChunkDetail[]
    context_chunks?: RetrievalChunkDetail[]
  } | null
  sources?: RetrievalChunkDetail[] | null
  sql?: {
    generated_sql?: string | null
    validation_status?: string | null
    tables_used?: string[] | null
    tenant_scope_verified?: boolean | null
    read_only_verified?: boolean | null
    row_count?: number | null
    execution_duration_ms?: number | null
    generation_duration_ms?: number | null
  } | null
  tools?: {
    mcp_server?: string | null
    tool_name?: string | null
    arguments?: Record<string, unknown> | null
    result_preview?: string | null
    tool_type?: 'read' | 'write' | null
    execution_duration_ms?: number | null
    requires_approval?: boolean | null
    approval_status?: string | null
    action_result?: Record<string, unknown> | null
    tenant_slug?: string | null
  } | null
  hitl?: {
    required?: boolean | null
    approved?: boolean | null
    pending_action?: Record<string, unknown> | null
    action_result?: Record<string, unknown> | null
  } | null
  cache?: {
    cache_hit: boolean
    cache_ttl_seconds?: number | null
  } | null
  llm_usage?: {
    model?: string | null
    llm_call_count?: number
    input_tokens?: number | null
    output_tokens?: number | null
    total_tokens?: number | null
  } | null
  cost?: {
    estimated_llm_cost_usd?: number | null
    estimated_embedding_cost_usd?: number | null
    estimated_total_cost_usd?: number | null
    label?: string
  } | null
  timing?: {
    total_ms?: number | null
    router_ms?: number | null
    planner_ms?: number | null
    retrieval_ms?: number | null
    reranking_ms?: number | null
    sql_generation_ms?: number | null
    sql_execution_ms?: number | null
    tool_execution_ms?: number | null
    llm_generation_ms?: number | null
    synthesis_ms?: number | null
    write_gate_ms?: number | null
  } | null
  observability_id?: string | null
}

export type AgentResponse = {
  thread_id: string
  status: AgentStatus
  route: AgentRoute
  planned_routes?: AgentRoute[] | null
  requires_synthesis?: boolean | null
  answer: string
  pending_action: PendingAction | null
  execution_details?: ExecutionDetails | null
}

export type ChatMessageRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatMessageRole
  content: string
  route?: AgentRoute
  status?: AgentStatus
  pendingAction?: PendingAction | null
  threadId?: string
  retrievalMode?: RetrievalMode
  executionDetails?: ExecutionDetails | null
  error?: boolean
  approvalResolved?: 'approved' | 'rejected'
  isLoading?: boolean
}
