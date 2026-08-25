import { fetchSystemStatus } from '../api/demo'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState'
import { StatusBadge } from '../components/StatusBadge'
import { useCachedResource } from '../hooks/useCachedResource'
import { TTL } from '../lib/requestCache'

export function SystemStatusPage() {
  const { data, error, status, isRefreshing, reload } = useCachedResource({
    key: 'system-status',
    ttlMs: TTL.status,
    fetcher: fetchSystemStatus,
  })

  return (
    <div className="status-page">
      <header className="page-header">
        <h2 className="page-header__title">System Status</h2>
        <p className="page-header__subtitle">
          Safe readiness view for the public demo. No connection strings or secrets are exposed.
          First request after idle may take several seconds (serverless cold start).
          {isRefreshing ? ' · Refreshing…' : null}
        </p>
      </header>

      {status === 'loading' ? (
        <LoadingBlock
          title="Checking system status…"
          subtitle="Cloud demo may take a few seconds after being idle."
          compact
        />
      ) : null}

      {status === 'error' ? (
        <ErrorBlock
          title="Unable to load system status."
          message={error}
          onRetry={() => void reload(true)}
        />
      ) : null}

      {status === 'success' && data ? (
        <>
          <p className="status-overall">
            Overall: <StatusBadge status={data.overall} />
          </p>

          {data.components.length === 0 ? (
            <EmptyBlock title="No status components reported." />
          ) : (
            <div className="status-grid">
              {data.components.map((component) => (
                <article key={component.name} className="status-card">
                  <div className="status-card__header">
                    <h3>{component.name}</h3>
                    <StatusBadge status={component.status} />
                  </div>
                  {component.role ? <p className="status-card__role">{component.role}</p> : null}
                </article>
              ))}
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
