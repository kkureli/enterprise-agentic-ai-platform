import { useCallback, useEffect, useState } from 'react'

import { fetchSystemStatus, type SystemStatus } from '../api/demo'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState'
import { StatusBadge } from '../components/StatusBadge'

type LoadStatus = 'loading' | 'success' | 'error'

export function SystemStatusPage() {
  const [data, setData] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')

  const load = useCallback(async () => {
    setStatus('loading')
    setError(null)

    try {
      const payload = await fetchSystemStatus()
      setData(payload)
      setStatus('success')
    } catch (err) {
      setData(null)
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to load system status.')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="status-page">
      <header className="page-header">
        <h2 className="page-header__title">System Status</h2>
        <p className="page-header__subtitle">
          Safe readiness view for the public demo. No connection strings or secrets are exposed.
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
          onRetry={() => void load()}
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
