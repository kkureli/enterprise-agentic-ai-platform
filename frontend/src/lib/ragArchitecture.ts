export type PipelineModeBadge = 'both' | 'standard' | 'advanced' | 'side'

export type RagPipelineNode = {
  id: string
  name: string
  shortLabel: string
  purpose: string
  implementation: string
  input: string
  output: string
  usedIn: PipelineModeBadge
  tenantIsolation: string
  performance: string
  tech?: string
}

/** Query-time stages matching retrieve_for_rag_mode + answer_question. */
export const RAG_PIPELINE_NODES: RagPipelineNode[] = [
  {
    id: 'user-query',
    name: 'User Query',
    shortLabel: 'Query',
    purpose: 'Tenant-scoped natural-language question entering the agent graph.',
    implementation: 'Submitted through the Playground or Compare Runs API with an explicit retrieval_mode.',
    input: 'Question text + tenant context + retrieval mode',
    output: 'Agent graph state',
    usedIn: 'both',
    tenantIsolation: 'Tenant ID is attached before routing; retrieval never runs without it.',
    performance: 'Negligible — client/network only.',
  },
  {
    id: 'agent-router',
    name: 'Planner',
    shortLabel: 'Planner',
    purpose:
      'Selective capability planner for the agent graph. For knowledge questions it selects the RAG capability (alone or as part of a composite plan).',
    implementation:
      'LangGraph planner node with structured RoutePlan (planned_routes, requires_synthesis, may_require_write).',
    input: 'User query + tenant context',
    output: 'One or more capabilities; knowledge route continues into the RAG pipeline below',
    usedIn: 'both',
    tenantIsolation: 'Tenant context is attached before planning; RAG retrieval remains tenant-scoped.',
    performance: 'Adds one planner LLM call before retrieval on knowledge paths.',
    tech: 'LangGraph · Azure OpenAI',
  },
  {
    id: 'rag-cache',
    name: 'RAG Cache Check',
    shortLabel: 'Cache',
    purpose: 'Short-lived Redis lookup for an identical knowledge answer before running retrieval.',
    implementation:
      'Tenant-aware, retrieval-mode-aware, and knowledge-version-aware cache. Logical invalidation via per-tenant version increment after successful document ingestion.',
    input: 'Normalized question identity + tenant + retrieval mode',
    output: 'HIT → cached RagResult · MISS → continue retrieval pipeline',
    usedIn: 'side',
    tenantIsolation: 'Cache entries are scoped per tenant; versions isolate knowledge epochs.',
    performance: 'HIT avoids embedding, retrieval, reranking, and answer LLM work.',
    tech: 'Redis / Upstash',
  },
  {
    id: 'query-rewrite',
    name: 'Query Rewrite / Multi-Query',
    shortLabel: 'Multi-Query',
    purpose: 'Generates alternative query formulations to widen recall on ambiguous questions.',
    implementation:
      'Advanced-only: LLM expands up to a configured number of paraphrases, then hybrid retrieval runs per query and results are fused with weighted multi-query RRF.',
    input: 'Original user query',
    output: 'Original query + rewritten queries',
    usedIn: 'advanced',
    tenantIsolation: 'Rewrites preserve identifiers; retrieval still applies tenant_id filters.',
    performance: 'Extra LLM expansion plus multiple hybrid retrieval passes — higher latency/compute.',
    tech: 'Azure OpenAI',
  },
  {
    id: 'dense-retrieval',
    name: 'Dense Retrieval',
    shortLabel: 'Dense',
    purpose: 'Semantic nearest-neighbor search over chunk embeddings.',
    implementation:
      'Query embedded with Azure OpenAI embeddings, searched against the Qdrant dense vector named “dense”, filtered by tenant_id.',
    input: 'Query text (or rewritten query)',
    output: 'Ranked dense candidate chunks',
    usedIn: 'both',
    tenantIsolation: 'Qdrant filter requires matching tenant_id payload on every point.',
    performance: 'Embedding call + vector search; cost scales with candidate depth.',
    tech: 'Azure OpenAI · Qdrant Cloud',
  },
  {
    id: 'sparse-retrieval',
    name: 'Sparse Retrieval',
    shortLabel: 'Sparse',
    purpose: 'Lexical / keyword-oriented retrieval for exact codes and sparse terms.',
    implementation:
      'BM25 sparse vectors (FastEmbed Qdrant/bm25) queried against the Qdrant sparse vector named “sparse”, filtered by tenant_id.',
    input: 'Query text (or rewritten query)',
    output: 'Ranked sparse candidate chunks',
    usedIn: 'both',
    tenantIsolation: 'Same tenant_id Qdrant filter as dense retrieval.',
    performance: 'Local sparse encode + vector search; strong on identifiers like E-100.',
    tech: 'Qdrant Cloud · BM25',
  },
  {
    id: 'hybrid-fusion',
    name: 'Hybrid Fusion',
    shortLabel: 'Hybrid',
    purpose: 'Combines dense and sparse rankings into a single candidate list.',
    implementation:
      'Weighted Reciprocal Rank Fusion (RRF). Default conceptual weights favor dense (e.g. 0.7/0.3); identifier-heavy queries rebalance toward sparse via configuration.',
    input: 'Dense + sparse ranked sets',
    output: 'Fused candidate chunks',
    usedIn: 'both',
    tenantIsolation: 'Operates only on already tenant-filtered candidates.',
    performance: 'CPU-cheap ranking fusion; candidate pool size drives later rerank cost.',
  },
  {
    id: 'reranker',
    name: 'Cross-Encoder Reranking',
    shortLabel: 'Rerank',
    purpose: 'Reorders hybrid candidates with a pairwise relevance model before final context selection.',
    implementation:
      'sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2). Hybrid ranks and reranker ranks are fused again with weighted RRF before truncating to the answer limit.',
    input: 'Hybrid (or multi-query fused) candidates + original query',
    output: 'Reranked / fused top candidates',
    usedIn: 'both',
    tenantIsolation: 'Reranks tenant-filtered candidates only; does not cross tenants.',
    performance: 'Adds model inference over the candidate set — usually the largest retrieval-time cost after multi-query.',
  },
  {
    id: 'context-selection',
    name: 'Context Selection',
    shortLabel: 'Context',
    purpose: 'Chooses the final chunks that ground the LLM answer.',
    implementation:
      'Top-N fused chunks become context. Execution Trace distinguishes candidate_count (retrieval pool) from final_chunk_count / context chunks and cited sources.',
    input: 'Fused reranked candidates',
    output: 'Context chunks for answer generation',
    usedIn: 'both',
    tenantIsolation: 'Context can only contain chunks already constrained by tenant_id.',
    performance: 'Smaller context lowers token cost; larger depth improves recall at higher cost.',
  },
  {
    id: 'llm-answer',
    name: 'LLM Answer Generation',
    shortLabel: 'LLM',
    purpose: 'Produces a grounded answer from selected context only.',
    implementation:
      'Azure OpenAI chat model with structured grounded output (answer + used source indices). Sources are validated against retrieved chunks before return.',
    input: 'Question + numbered context chunks',
    output: 'Grounded answer + cited sources',
    usedIn: 'both',
    tenantIsolation: 'Answer grounded only in tenant-scoped context; no cross-tenant documents.',
    performance: 'Dominant answer-generation latency and token cost.',
    tech: 'Azure OpenAI',
  },
]

export const STANDARD_PATH_IDS = [
  'user-query',
  'agent-router',
  'rag-cache',
  'dense-retrieval',
  'sparse-retrieval',
  'hybrid-fusion',
  'reranker',
  'context-selection',
  'llm-answer',
] as const

export const ADVANCED_PATH_IDS = [
  'user-query',
  'agent-router',
  'rag-cache',
  'query-rewrite',
  'dense-retrieval',
  'sparse-retrieval',
  'hybrid-fusion',
  'reranker',
  'context-selection',
  'llm-answer',
] as const

export const INGESTION_STEPS = [
  { name: 'Document', detail: 'Uploaded / seeded tenant file' },
  { name: 'Parse', detail: 'Extract plain text' },
  { name: 'Chunk', detail: 'Overlapping text chunks' },
  { name: 'Dense Embedding', detail: 'Azure OpenAI embeddings' },
  { name: 'Sparse Representation', detail: 'BM25 sparse vectors' },
  { name: 'Qdrant Upsert', detail: 'tenant_id + document metadata payload' },
  { name: 'Indexed Chunks', detail: 'Ready for tenant-scoped retrieval' },
] as const

export const E100_TENANT_MEANINGS = [
  {
    tenant: 'Atlas Manufacturing',
    meaning: 'Lubrication pressure below safe operating threshold',
  },
  {
    tenant: 'Borealis Cold Chain',
    meaning: 'Evaporator coil temperature sensor communication failure',
  },
  {
    tenant: 'Helios Energy Services',
    meaning: 'Power inverter communication timeout with site controller',
  },
] as const

export function modeBadgeLabel(mode: PipelineModeBadge): string {
  switch (mode) {
    case 'standard':
      return 'Standard'
    case 'advanced':
      return 'Advanced'
    case 'side':
      return 'Side path'
    default:
      return 'Both'
  }
}
