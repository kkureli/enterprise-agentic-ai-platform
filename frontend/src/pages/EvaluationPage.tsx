import { useEffect, useState } from 'react'

import { fetchEvaluations, type DemoEvaluations } from '../api/demo'

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function EvaluationPage() {
  const [data, setData] = useState<DemoEvaluations | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const payload = await fetchEvaluations()
        if (!cancelled) {
          setData(payload)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load evaluations.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p className="page-note">Loading evaluation metrics…</p>
  }

  if (error || !data) {
    return <p className="page-error">{error ?? 'Evaluation metrics unavailable.'}</p>
  }

  return (
    <div className="evaluation-page">
      <header className="page-header">
        <h2 className="page-header__title">Evaluation</h2>
        <p className="page-header__subtitle">
          Regression metrics from curated evaluation runs — not a live production SLA claim.
        </p>
      </header>

      <p className="page-note">{data.disclaimer}</p>

      <section className="eval-section">
        <h3 className="eval-section__title">Agent Evaluation</h3>
        <p className="page-note">Dataset size: {data.agent.total_cases} cases</p>
        <div className="metric-grid">
          <article className="metric-card">
            <h4>Route Accuracy</h4>
            <p className="metric-card__value">{pct(data.agent.route_accuracy)}</p>
          </article>
          <article className="metric-card">
            <h4>Approval Accuracy</h4>
            <p className="metric-card__value">{pct(data.agent.approval_accuracy)}</p>
          </article>
          <article className="metric-card">
            <h4>Execution Success</h4>
            <p className="metric-card__value">{pct(data.agent.execution_success_rate)}</p>
          </article>
          <article className="metric-card">
            <h4>Workflow Pass</h4>
            <p className="metric-card__value">{pct(data.agent.end_to_end_pass_rate)}</p>
          </article>
        </div>
      </section>

      <section className="eval-section">
        <h3 className="eval-section__title">Retrieval Evaluation</h3>
        <p className="page-note">
          Dataset size: {data.retrieval.num_queries} queries · k={data.retrieval.eval_k}
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Recall@{data.retrieval.eval_k}</th>
                <th>MRR</th>
                <th>nDCG@{data.retrieval.eval_k}</th>
              </tr>
            </thead>
            <tbody>
              {data.retrieval.strategies.map((strategy) => (
                <tr key={strategy.name}>
                  <td>{strategy.name}</td>
                  <td>{pct(strategy.recall_at_k)}</td>
                  <td>{strategy.mrr.toFixed(3)}</td>
                  <td>{strategy.ndcg_at_k.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
