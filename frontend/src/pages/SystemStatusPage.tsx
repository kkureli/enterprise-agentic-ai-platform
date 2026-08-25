import { useEffect, useState } from 'react'

import { fetchSystemStatus, type SystemStatus } from '../api/demo'

export function SystemStatusPage() {
  const [data, setData] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const payload = await fetchSystemStatus()
        if (!cancelled) {
          setData(payload)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load system status.')
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
    return <p className="page-note">Checking system status…</p>
  }

  if (error || !data) {
    return <p className="page-error">{error ?? 'System status unavailable.'}</p>
  }

  return (
    <div className="status-page">
      <header className="page-header">
        <h2 className="page-header__title">System Status</h2>
        <p className="page-header__subtitle">
          Safe readiness view for the public demo. No connection strings or secrets are exposed.
        </p>
      </header>

      <p className="status-overall">
        Overall: <strong>{data.overall}</strong>
      </p>

      <div className="status-grid">
        {data.components.map((component) => (
          <article key={component.name} className="status-card">
            <div className="status-card__header">
              <h3>{component.name}</h3>
              <span className={`status-badge status-badge--${component.status.toLowerCase()}`}>
                {component.status}
              </span>
            </div>
            {component.role ? <p className="status-card__role">{component.role}</p> : null}
          </article>
        ))}
      </div>
    </div>
  )
}
