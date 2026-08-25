import { fetchEvaluations } from '../api/demo'
import { ErrorBlock, LoadingBlock } from '../components/AsyncState'
import { useCachedResource } from '../hooks/useCachedResource'
import { TTL } from '../lib/requestCache'

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function EvaluationPage() {
  const { data, error, status, isRefreshing, reload } = useCachedResource({
    key: 'evaluations',
    ttlMs: TTL.evaluations,
    fetcher: fetchEvaluations,
    revalidate: false,
  })

  return (
    <div className="evaluation-page">
      <header className="page-header">
        <h2 className="page-header__title">Evaluation</h2>
        <p className="page-header__subtitle">
          Regression metrics from curated evaluation runs — not a live production SLA claim.
          {isRefreshing ? ' · Refreshing…' : null}
        </p>
      </header>

      {status === 'loading' ? (
        <LoadingBlock title="Loading evaluation metrics…" compact />
      ) : null}

      {status === 'error' ? (
        <ErrorBlock
          title="Unable to load evaluation metrics."
          message={error}
          onRetry={() => void reload(true)}
        />
      ) : null}

      {status === 'success' && data ? (
        <>
          <p className="eval-disclaimer">{data.disclaimer}</p>

          <section className="eval-section">
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
                <h4>Workflow Pass</h4>
                <p className="metric-card__value">{pct(data.agent.end_to_end_pass_rate)}</p>
              </article>
              <article className="metric-card">
                <h4>Retrieval Queries</h4>
                <p className="metric-card__value">{data.retrieval.num_queries}</p>
              </article>
            </div>
          </section>

          <section className="eval-section">
            <h3 className="eval-section__title">Retrieval strategy comparison</h3>
            <p className="page-note">
              Agent cases: {data.agent.total_cases} · k={data.retrieval.eval_k}
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
        </>
      ) : null}
    </div>
  )
}
