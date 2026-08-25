import { useState, type ReactNode } from 'react'

import { modeLabel } from '../lib/retrievalModes'
import type { ExecutionDetails, RetrievalChunkDetail } from '../types/agent'

type ExecutionTraceProps = {
  details?: ExecutionDetails | null
}

function formatMs(value?: number | null): string | null {
  if (value == null) {
    return null
  }

  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`
  }

  return `${value.toFixed(0)} ms`
}

function formatTokens(value?: number | null): string | null {
  if (value == null) {
    return null
  }

  return value.toLocaleString()
}

function formatCost(value?: number | null): string | null {
  if (value == null) {
    return null
  }

  return `$${value.toFixed(6)}`
}

function routeLabel(route?: string | null): string {
  switch (route) {
    case 'knowledge':
      return 'Knowledge / RAG'
    case 'sql':
      return 'Structured Data / SQL'
    case 'tool':
      return 'Live Tools / MCP'
    case 'unsupported':
      return 'Unsupported'
    default:
      return route ?? '—'
  }
}

function nodeLabel(node: string): string {
  const labels: Record<string, string> = {
    router: 'Router',
    rag: 'RAG',
    sql: 'SQL',
    tool: 'Tool',
    approval: 'Approval',
    approved_action: 'Approved Action',
    finalize: 'Finalize',
    fallback: 'Fallback',
  }

  return labels[node] ?? node
}

function ChunkInspector({ chunk, title }: { chunk: RetrievalChunkDetail; title?: string }) {
  const [open, setOpen] = useState(false)

  return (
    <article className="trace-chunk">
      <div className="trace-chunk__header">
        <div>
          <strong>{title ?? chunk.filename}</strong>
          <p className="trace-chunk__meta">
            <span className="trace-mono">chunk {chunk.chunk_index}</span>
            {chunk.document_id ? (
              <>
                {' · '}
                <span className="trace-mono">{chunk.document_id.slice(0, 8)}</span>
              </>
            ) : null}
            {chunk.score != null ? ` · Score ${chunk.score.toFixed(3)}` : ''}
            {chunk.rerank_score != null ? ` · Rerank ${chunk.rerank_score.toFixed(3)}` : ''}
          </p>
        </div>
        <button type="button" className="button button--secondary button--small" onClick={() => setOpen(!open)}>
          {open ? 'Hide chunk' : 'Show chunk'}
        </button>
      </div>
      {open ? <pre className="trace-chunk__text">{chunk.text}</pre> : null}
    </article>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="trace-section">
      <h4 className="trace-section__title">{title}</h4>
      {children}
    </section>
  )
}

function Kv({
  label,
  value,
  mono,
}: {
  label: string
  value?: string | number | boolean | null
  mono?: boolean
}) {
  if (value == null || value === '') {
    return null
  }

  return (
    <>
      <dt>{label}</dt>
      <dd className={mono ? 'trace-mono' : undefined}>
        {typeof value === 'boolean' ? (value ? 'true' : 'false') : value}
      </dd>
    </>
  )
}

export function ExecutionTrace({ details }: ExecutionTraceProps) {
  if (!details) {
    return null
  }

  const timing = details.timing
  const usage = details.llm_usage
  const cost = details.cost
  const retrieval = details.retrieval
  const sql = details.sql
  const tools = details.tools
  const hitl = details.hitl
  const cache = details.cache
  const sources = details.sources ?? []
  const graphPath = details.graph_path ?? []

  const hasOverview =
    details.route ||
    cache ||
    usage ||
    timing?.total_ms != null ||
    cost?.estimated_total_cost_usd != null

  return (
    <details className="execution-trace">
      <summary className="execution-trace__summary">Execution Trace</summary>

      <div className="execution-trace__body">
        {hasOverview ? (
          <Section title="Overview">
            <dl className="trace-kv">
              <Kv label="Route" value={routeLabel(details.route)} />
              <Kv
                label="Retrieval"
                value={
                  retrieval?.strategy
                    ? `${modeLabel(retrieval.retrieval_mode)} · ${retrieval.strategy}`
                    : retrieval?.retrieval_mode
                      ? modeLabel(retrieval.retrieval_mode)
                      : null
                }
              />
              <Kv
                label="Cache"
                value={cache ? (cache.cache_hit ? 'HIT' : 'MISS') : null}
              />
              <Kv label="LLM calls" value={usage?.llm_call_count} />
              <Kv label="Total latency" value={formatMs(timing?.total_ms)} />
              <Kv label="Tokens" value={formatTokens(usage?.total_tokens)} />
              <Kv
                label={cost?.label ?? 'Estimated cost'}
                value={formatCost(cost?.estimated_total_cost_usd)}
              />
              <Kv label="Observability ID" value={details.observability_id} mono />
            </dl>
          </Section>
        ) : null}

        {graphPath.length > 0 ? (
          <Section title="Graph">
            <ol className="graph-path">
              {graphPath.map((node, index) => (
                <li key={`${node}-${index}`} className="graph-path__item">
                  <span className="graph-path__node trace-mono">{nodeLabel(node)}</span>
                  {index < graphPath.length - 1 ? (
                    <span className="graph-path__arrow" aria-hidden="true">
                      ↓
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          </Section>
        ) : null}

        {retrieval ? (
          <Section title="Retrieval">
            <dl className="trace-kv">
              <Kv label="Mode" value={modeLabel(retrieval.retrieval_mode)} />
              <Kv label="Strategy" value={retrieval.strategy} />
              {retrieval.dense_weight != null ? (
                <Kv label="Dense" value="Enabled" />
              ) : null}
              {retrieval.sparse_weight != null ? (
                <Kv label="Sparse" value="Enabled" />
              ) : null}
              <Kv label="Dense weight" value={retrieval.dense_weight} />
              <Kv label="Sparse weight" value={retrieval.sparse_weight} />
              <Kv
                label="Query rewrites"
                value={
                  retrieval.query_rewrites?.length
                    ? `${retrieval.query_rewrites.length} · ${retrieval.query_rewrites.join(' | ')}`
                    : null
                }
              />
              <Kv label="Candidate chunks" value={retrieval.candidate_count} />
              <Kv
                label="Reranker"
                value={
                  retrieval.reranker_enabled == null
                    ? null
                    : retrieval.reranker_enabled
                      ? 'Yes'
                      : 'No'
                }
              />
              <Kv label="Context chunks" value={retrieval.final_chunk_count} />
            </dl>
          </Section>
        ) : null}

        {sources.length > 0 || (retrieval?.context_chunks?.length ?? 0) > 0 ? (
          <Section title="Sources">
            <p className="trace-note">
              Chunks actually used for grounding. Expand to verify indexed text.
            </p>
            {(sources.length > 0 ? sources : retrieval?.context_chunks ?? []).map((chunk) => (
              <ChunkInspector
                key={`${chunk.document_id}-${chunk.chunk_index}`}
                chunk={chunk}
              />
            ))}
          </Section>
        ) : null}

        {retrieval?.retrieved_candidates && retrieval.retrieved_candidates.length > 0 ? (
          <Section title="Retrieved candidates">
            <p className="trace-note">Final retrieved set before answer generation.</p>
            {retrieval.retrieved_candidates.map((chunk) => (
              <ChunkInspector
                key={`candidate-${chunk.document_id}-${chunk.chunk_index}`}
                chunk={chunk}
              />
            ))}
          </Section>
        ) : null}

        {sql ? (
          <Section title="SQL">
            <dl className="trace-kv">
              <Kv label="Validation" value={sql.validation_status} />
              <Kv
                label="Tables"
                value={sql.tables_used?.length ? sql.tables_used.join(', ') : null}
              />
              <Kv label="Tenant scoped" value={sql.tenant_scope_verified} />
              <Kv label="Read only" value={sql.read_only_verified} />
              <Kv label="Rows" value={sql.row_count} />
              <Kv label="Generation" value={formatMs(sql.generation_duration_ms)} />
              <Kv label="Execution" value={formatMs(sql.execution_duration_ms)} />
            </dl>
            {sql.generated_sql ? (
              <pre className="trace-code">{sql.generated_sql}</pre>
            ) : null}
          </Section>
        ) : null}

        {tools ? (
          <Section title="Tools">
            <dl className="trace-kv">
              <Kv label="MCP server" value={tools.mcp_server} mono />
              <Kv label="Tool" value={tools.tool_name} mono />
              <Kv label="Type" value={tools.tool_type} />
              <Kv label="Requires approval" value={tools.requires_approval} />
              <Kv label="Approval status" value={tools.approval_status} />
              <Kv label="Duration" value={formatMs(tools.execution_duration_ms)} />
            </dl>
            {tools.arguments ? (
              <pre className="trace-code">{JSON.stringify(tools.arguments, null, 2)}</pre>
            ) : null}
            {tools.result_preview ? (
              <pre className="trace-code">{tools.result_preview}</pre>
            ) : null}
          </Section>
        ) : null}

        {hitl ? (
          <Section title="Human Approval">
            <dl className="trace-kv">
              <Kv label="Required" value={hitl.required} />
              <Kv label="Approved" value={hitl.approved} />
            </dl>
            {hitl.action_result ? (
              <pre className="trace-code">{JSON.stringify(hitl.action_result, null, 2)}</pre>
            ) : null}
          </Section>
        ) : null}

        {timing && Object.values(timing).some((value) => value != null) ? (
          <Section title="Performance">
            <dl className="trace-kv">
              <Kv label="Total" value={formatMs(timing.total_ms)} />
              <Kv label="Router" value={formatMs(timing.router_ms)} />
              <Kv label="Retrieval" value={formatMs(timing.retrieval_ms)} />
              <Kv label="Reranking" value={formatMs(timing.reranking_ms)} />
              <Kv label="SQL generation" value={formatMs(timing.sql_generation_ms)} />
              <Kv label="SQL execution" value={formatMs(timing.sql_execution_ms)} />
              <Kv label="Tool execution" value={formatMs(timing.tool_execution_ms)} />
              <Kv label="LLM generation" value={formatMs(timing.llm_generation_ms)} />
            </dl>
          </Section>
        ) : null}

        {usage || cost ? (
          <Section title="Tokens & Cost">
            <dl className="trace-kv">
              <Kv label="Model / deployment" value={usage?.model} />
              <Kv label="LLM calls" value={usage?.llm_call_count} />
              <Kv label="Input tokens" value={formatTokens(usage?.input_tokens)} />
              <Kv label="Output tokens" value={formatTokens(usage?.output_tokens)} />
              <Kv label="Total tokens" value={formatTokens(usage?.total_tokens)} />
              <Kv label="Estimated LLM cost" value={formatCost(cost?.estimated_llm_cost_usd)} />
              <Kv
                label="Estimated total cost"
                value={formatCost(cost?.estimated_total_cost_usd)}
              />
            </dl>
            <p className="trace-note">
              Estimated cost is approximate for portfolio display, not an Azure invoice.
              Deep tracing remains in Langfuse.
            </p>
          </Section>
        ) : null}
      </div>
    </details>
  )
}
