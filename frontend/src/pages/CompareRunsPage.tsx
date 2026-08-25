import { useRef, useState } from 'react'

import { compareAgentRuns } from '../api/demo'
import { PlaygroundApiError } from '../api/playground'
import { LoadingBlock } from '../components/AsyncState'
import { ExecutionTrace } from '../components/ExecutionTrace'
import { RetrievalPipelineInline } from '../components/RetrievalModeInfo'
import {
  ADVANCED_SUMMARY,
  RETRIEVAL_TRADEOFF_NOTE,
  STANDARD_SUMMARY,
} from '../lib/retrievalModes'
import type { AgentResponse, ExecutionDetails } from '../types/agent'

type CompareRunsPageProps = {
  tenantId: string
  disabled?: boolean
}

type ObservedMetric = {
  label: string
  left: string
  right: string
}

function formatMs(value?: number | null): string | null {
  if (value == null) {
    return null
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} s`
  }
  return `${Math.round(value)} ms`
}

function formatCost(value?: number | null): string | null {
  if (value == null) {
    return null
  }
  return `$${value.toFixed(6)}`
}

function formatTokens(value?: number | null): string | null {
  if (value == null) {
    return null
  }
  return value.toLocaleString()
}

function buildObservedMetrics(
  standard: AgentResponse,
  advanced: AgentResponse,
): ObservedMetric[] {
  const left = standard.execution_details
  const right = advanced.execution_details
  const rows: ObservedMetric[] = []

  const leftLatency = formatMs(left?.timing?.total_ms)
  const rightLatency = formatMs(right?.timing?.total_ms)
  if (leftLatency != null || rightLatency != null) {
    rows.push({
      label: 'Latency',
      left: leftLatency ?? '—',
      right: rightLatency ?? '—',
    })
  }

  const leftCandidates = left?.retrieval?.candidate_count
  const rightCandidates = right?.retrieval?.candidate_count
  if (leftCandidates != null || rightCandidates != null) {
    rows.push({
      label: 'Candidates',
      left: leftCandidates != null ? String(leftCandidates) : '—',
      right: rightCandidates != null ? String(rightCandidates) : '—',
    })
  }

  const leftRerank = left?.retrieval?.reranker_enabled
  const rightRerank = right?.retrieval?.reranker_enabled
  if (leftRerank != null || rightRerank != null) {
    rows.push({
      label: 'Reranker',
      left: leftRerank == null ? '—' : leftRerank ? 'Yes' : 'No',
      right: rightRerank == null ? '—' : rightRerank ? 'Yes' : 'No',
    })
  }

  const leftRewrites = left?.retrieval?.query_rewrites?.length
  const rightRewrites = right?.retrieval?.query_rewrites?.length
  if (leftRewrites != null || rightRewrites != null) {
    rows.push({
      label: 'Query rewrites',
      left: leftRewrites != null ? String(leftRewrites) : '0',
      right: rightRewrites != null ? String(rightRewrites) : '0',
    })
  }

  const leftSources = (left?.sources ?? left?.retrieval?.context_chunks)?.length
  const rightSources = (right?.sources ?? right?.retrieval?.context_chunks)?.length
  if (leftSources != null || rightSources != null) {
    rows.push({
      label: 'Sources',
      left: leftSources != null ? String(leftSources) : '—',
      right: rightSources != null ? String(rightSources) : '—',
    })
  }

  const leftTokens = formatTokens(left?.llm_usage?.total_tokens)
  const rightTokens = formatTokens(right?.llm_usage?.total_tokens)
  if (leftTokens != null || rightTokens != null) {
    rows.push({
      label: 'Tokens',
      left: leftTokens ?? '—',
      right: rightTokens ?? '—',
    })
  }

  const leftCost = formatCost(left?.cost?.estimated_total_cost_usd)
  const rightCost = formatCost(right?.cost?.estimated_total_cost_usd)
  if (leftCost != null || rightCost != null) {
    rows.push({
      label: 'Cost',
      left: leftCost ?? '—',
      right: rightCost ?? '—',
    })
  }

  return rows
}

function strategyLabel(details?: ExecutionDetails | null): string | null {
  return details?.retrieval?.strategy ?? null
}

export function CompareRunsPage({ tenantId, disabled }: CompareRunsPageProps) {
  const [question, setQuestion] = useState('What does E-100 mean?')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [standard, setStandard] = useState<AgentResponse | null>(null)
  const [advanced, setAdvanced] = useState<AgentResponse | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [showTraces, setShowTraces] = useState(false)
  const runningLockRef = useRef(false)

  async function handleCompare() {
    if (running || disabled || runningLockRef.current) {
      return
    }

    const trimmed = question.trim()
    if (!trimmed || !tenantId.trim()) {
      return
    }

    runningLockRef.current = true
    setRunning(true)
    setError(null)
    setStandard(null)
    setAdvanced(null)
    setShowTraces(false)

    try {
      const result = await compareAgentRuns(tenantId, trimmed)
      setStandard(result.standard)
      setAdvanced(result.advanced)
      setNote(result.note)

      if (result.standard.route !== 'knowledge' || result.advanced.route !== 'knowledge') {
        setError(
          'Comparison is intended for knowledge/RAG questions. One or both runs routed elsewhere.',
        )
      }
    } catch (err) {
      if (err instanceof PlaygroundApiError) {
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Comparison failed.')
      }
    } finally {
      setRunning(false)
      runningLockRef.current = false
    }
  }

  const observed = standard && advanced ? buildObservedMetrics(standard, advanced) : []

  return (
    <div className="compare-page">
      <header className="page-header">
        <h2 className="page-header__title">Compare Runs</h2>
        <p className="page-header__subtitle">
          Run the same knowledge question with Standard vs Advanced retrieval. This performs two
          AI executions and is rate-limited more strictly.
        </p>
      </header>

      <div className="compare-mode-cards">
        <article className="compare-mode-card">
          <p className="compare-mode-card__badge">Standard</p>
          <h3 className="compare-mode-card__title">Fast hybrid retrieval</h3>
          <p className="compare-mode-card__summary">{STANDARD_SUMMARY}</p>
          <p className="compare-mode-card__label">Best suited for</p>
          <ul className="compare-mode-card__list">
            <li>Straightforward knowledge questions</li>
            <li>Lower latency</li>
            <li>Lower compute</li>
          </ul>
          <p className="compare-mode-card__label">Pipeline</p>
          <p className="compare-mode-card__pipeline-text">
            Hybrid Retrieval → Reranking → Context → LLM
          </p>
          <RetrievalPipelineInline mode="standard" />
        </article>

        <article className="compare-mode-card compare-mode-card--accent">
          <p className="compare-mode-card__badge">Advanced</p>
          <h3 className="compare-mode-card__title">Multi-query retrieval + reranking</h3>
          <p className="compare-mode-card__summary">{ADVANCED_SUMMARY}</p>
          <p className="compare-mode-card__label">Best suited for</p>
          <ul className="compare-mode-card__list">
            <li>Ambiguous questions</li>
            <li>Broader retrieval coverage</li>
            <li>Harder grounding problems</li>
          </ul>
          <p className="compare-mode-card__label">Tradeoff</p>
          <ul className="compare-mode-card__list">
            <li>More retrieval work (query rewrite + multi-query hybrid)</li>
            <li>Potentially higher latency / token usage / compute</li>
            <li>Does not guarantee a better answer</li>
          </ul>
          <RetrievalPipelineInline mode="advanced" />
        </article>
      </div>

      <p className="eval-disclaimer">{RETRIEVAL_TRADEOFF_NOTE}</p>

      <div className="compare-form">
        <label htmlFor="compare-question" className="tenant-selector__label">
          Knowledge question
        </label>
        <textarea
          id="compare-question"
          className="composer__textarea"
          value={question}
          disabled={running || disabled}
          aria-label="Knowledge question for comparison"
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={running || disabled || !question.trim()}
          onClick={() => void handleCompare()}
        >
          {running ? 'Comparing…' : 'Compare Standard vs Advanced'}
        </button>
      </div>

      {running ? (
        <LoadingBlock title="Running Standard and Advanced…" compact />
      ) : null}

      {error ? <p className="page-error">{error}</p> : null}
      {note ? <p className="page-note">{note}</p> : null}

      {standard && advanced ? (
        <>
          <section className="compare-answers" aria-label="Compared answers">
            <h3 className="compare-observed__title">Answers</h3>
            <div className="compare-summary">
              <article className="compare-summary__card">
                <h4 className="compare-summary__title">Standard</h4>
                <p className="compare-summary__answer">{standard.answer || 'No answer returned.'}</p>
              </article>
              <article className="compare-summary__card compare-summary__card--accent">
                <h4 className="compare-summary__title">Advanced</h4>
                <p className="compare-summary__answer">{advanced.answer || 'No answer returned.'}</p>
              </article>
            </div>
          </section>

          {observed.length > 0 ? (
            <section className="compare-observed">
              <h3 className="compare-observed__title">Observed differences</h3>
              <div className="table-wrap">
                <table className="data-table compare-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Standard</th>
                      <th>Advanced</th>
                    </tr>
                  </thead>
                  <tbody>
                    {observed.map((row) => (
                      <tr
                        key={row.label}
                        className={
                          row.left !== row.right ? 'compare-table__row--diff' : undefined
                        }
                      >
                        <th>{row.label}</th>
                        <td>{row.left}</td>
                        <td>{row.right}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(strategyLabel(standard.execution_details) ||
                strategyLabel(advanced.execution_details)) && (
                <p className="page-note">
                  Strategies:{' '}
                  {strategyLabel(standard.execution_details) ?? '—'} vs{' '}
                  {strategyLabel(advanced.execution_details) ?? '—'}
                </p>
              )}
            </section>
          ) : null}

          <div className="compare-traces-toggle">
            <button
              type="button"
              className="button button--secondary"
              onClick={() => setShowTraces((current) => !current)}
            >
              {showTraces ? 'Hide execution traces' : 'Show execution traces'}
            </button>
          </div>

          {showTraces ? (
            <div className="compare-traces">
              <section>
                <h3>Standard Execution Trace</h3>
                <ExecutionTrace details={standard.execution_details} />
              </section>
              <section>
                <h3>Advanced Execution Trace</h3>
                <ExecutionTrace details={advanced.execution_details} />
              </section>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
