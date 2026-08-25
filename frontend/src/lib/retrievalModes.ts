import type { RetrievalMode } from '../types/agent'

export type PipelineStep = string

export const STANDARD_SUMMARY =
  'Fast hybrid retrieval with reranking for normal queries.'

export const ADVANCED_SUMMARY =
  'Deeper multi-query retrieval with reranking for harder questions.'

export const STANDARD_HELPER = 'Hybrid retrieval + reranking · optimized for speed'

export const ADVANCED_HELPER =
  'Multi-query hybrid + reranking · optimized for retrieval depth'

export const RETRIEVAL_TRADEOFF_NOTE =
  'Retrieval depth is a tradeoff. Advanced mode performs additional query rewriting and multi-query retrieval work that may improve grounding on difficult queries, but can increase latency and compute cost.'

export const STANDARD_CAPABILITIES = [
  'Dense semantic retrieval',
  'Sparse / lexical retrieval',
  'Hybrid fusion (RRF)',
  'Tenant-scoped metadata filtering',
  'Cross-encoder reranking',
  'Lower latency / lower compute than Advanced',
] as const

export const ADVANCED_CAPABILITIES = [
  'Everything in Standard',
  'Query rewriting / multi-query retrieval',
  'Hybrid retrieval per rewritten query',
  'Fusion across queries',
  'Cross-encoder reranking',
  'Broader candidate coverage; usually higher latency / compute',
] as const

export const STANDARD_PIPELINE: PipelineStep[] = [
  'Query',
  'Dense + Sparse Retrieval',
  'Hybrid Fusion',
  'Reranking',
  'Top Context',
  'LLM',
]

export const ADVANCED_PIPELINE: PipelineStep[] = [
  'Query',
  'Query Rewrite / Multi-Query',
  'Dense + Sparse Retrieval',
  'Multi-query Fusion',
  'Reranking',
  'Top Context',
  'LLM',
]

export function modeLabel(mode: string | null | undefined): string {
  if (mode === 'standard') {
    return 'Standard'
  }
  if (mode === 'advanced') {
    return 'Advanced'
  }
  return mode ?? '—'
}

export function helperForMode(mode: RetrievalMode): string {
  return mode === 'advanced' ? ADVANCED_HELPER : STANDARD_HELPER
}
