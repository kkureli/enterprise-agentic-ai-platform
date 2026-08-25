import { useRef, useState } from 'react'

import { compareAgentRuns } from '../api/demo'
import { PlaygroundApiError } from '../api/playground'
import { ExecutionTrace } from '../components/ExecutionTrace'
import type { AgentResponse, ExecutionDetails } from '../types/agent'

type CompareRunsPageProps = {
  disabled?: boolean
}

function metric(label: string, left?: string | number | null, right?: string | number | null) {
  const leftText = left == null || left === '' ? '—' : String(left)
  const rightText = right == null || right === '' ? '—' : String(right)
  const different = leftText !== rightText

  return (
    <tr className={different ? 'compare-table__row--diff' : undefined}>
      <th>{label}</th>
      <td>{leftText}</td>
      <td>{rightText}</td>
    </tr>
  )
}

function summarize(response: AgentResponse) {
  const details: ExecutionDetails | null | undefined = response.execution_details
  return {
    answer: response.answer,
    route: response.route,
    mode: details?.retrieval?.retrieval_mode ?? '—',
    strategy: details?.retrieval?.strategy ?? '—',
    candidates: details?.retrieval?.candidate_count ?? '—',
    finalChunks: details?.retrieval?.final_chunk_count ?? '—',
    reranker: details?.retrieval?.reranker_enabled == null
      ? '—'
      : details.retrieval.reranker_enabled
        ? 'enabled'
        : 'disabled',
    cache: details?.cache ? (details.cache.cache_hit ? 'HIT' : 'MISS') : '—',
    latency: details?.timing?.total_ms != null ? `${details.timing.total_ms} ms` : '—',
    llmCalls: details?.llm_usage?.llm_call_count ?? '—',
    inputTokens: details?.llm_usage?.input_tokens ?? '—',
    outputTokens: details?.llm_usage?.output_tokens ?? '—',
    totalTokens: details?.llm_usage?.total_tokens ?? '—',
    cost:
      details?.cost?.estimated_total_cost_usd != null
        ? `$${details.cost.estimated_total_cost_usd.toFixed(6)}`
        : '—',
    sources: details?.sources ?? details?.retrieval?.context_chunks ?? [],
  }
}

export function CompareRunsPage({ disabled }: CompareRunsPageProps) {
  const [question, setQuestion] = useState('What does E-100 mean?')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [standard, setStandard] = useState<AgentResponse | null>(null)
  const [advanced, setAdvanced] = useState<AgentResponse | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const runningLockRef = useRef(false)

  async function handleCompare() {
    if (running || disabled || runningLockRef.current) {
      return
    }

    const trimmed = question.trim()
    if (!trimmed) {
      return
    }

    runningLockRef.current = true
    setRunning(true)
    setError(null)
    setStandard(null)
    setAdvanced(null)

    try {
      const result = await compareAgentRuns(trimmed)
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

  const left = standard ? summarize(standard) : null
  const right = advanced ? summarize(advanced) : null

  return (
    <div className="compare-page">
      <header className="page-header">
        <h2 className="page-header__title">Compare Runs</h2>
        <p className="page-header__subtitle">
          Run the same knowledge question with Standard vs Advanced retrieval. This performs two
          AI executions and is rate-limited more strictly.
        </p>
      </header>

      <div className="compare-form">
        <label htmlFor="compare-question" className="tenant-selector__label">
          Knowledge question
        </label>
        <textarea
          id="compare-question"
          className="composer__textarea"
          value={question}
          disabled={running || disabled}
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

      {error ? <p className="page-error">{error}</p> : null}
      {note ? <p className="page-note">{note}</p> : null}

      {left && right ? (
        <>
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
                {metric('Answer', left.answer, right.answer)}
                {metric('Route', left.route, right.route)}
                {metric('Retrieval mode', left.mode, right.mode)}
                {metric('Strategy', left.strategy, right.strategy)}
                {metric('Candidate count', left.candidates, right.candidates)}
                {metric('Final chunks', left.finalChunks, right.finalChunks)}
                {metric('Reranker', left.reranker, right.reranker)}
                {metric('Cache', left.cache, right.cache)}
                {metric('Latency', left.latency, right.latency)}
                {metric('LLM calls', left.llmCalls, right.llmCalls)}
                {metric('Input tokens', left.inputTokens, right.inputTokens)}
                {metric('Output tokens', left.outputTokens, right.outputTokens)}
                {metric('Total tokens', left.totalTokens, right.totalTokens)}
                {metric('Estimated cost', left.cost, right.cost)}
                {metric('Sources', left.sources.length, right.sources.length)}
              </tbody>
            </table>
          </div>

          <div className="compare-traces">
            <section>
              <h3>Standard Execution Trace</h3>
              <ExecutionTrace details={standard?.execution_details} />
            </section>
            <section>
              <h3>Advanced Execution Trace</h3>
              <ExecutionTrace details={advanced?.execution_details} />
            </section>
          </div>
        </>
      ) : null}
    </div>
  )
}
