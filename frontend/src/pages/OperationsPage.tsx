import { useEffect, useState } from 'react'

import {
  listAssets,
  listMaintenanceRecords,
  listMaintenanceTickets,
} from '../api/playground'
import { StatusBadge } from '../components/StatusBadge'
import type {
  Asset,
  MaintenanceRecord,
  MaintenanceTicket,
} from '../types/playground'

type OperationsPageProps = {
  tenantId: string
  onAskAboutAsset: (assetCode: string) => void
}

type OpsTab = 'assets' | 'history' | 'tickets'

export function OperationsPage({ tenantId, onAskAboutAsset }: OperationsPageProps) {
  const [tab, setTab] = useState<OpsTab>('assets')
  const [assets, setAssets] = useState<Asset[]>([])
  const [records, setRecords] = useState<MaintenanceRecord[]>([])
  const [tickets, setTickets] = useState<MaintenanceTicket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const [assetRows, recordRows, ticketRows] = await Promise.all([
          listAssets(tenantId),
          listMaintenanceRecords(tenantId),
          listMaintenanceTickets(tenantId),
        ])

        if (!cancelled) {
          setAssets(assetRows)
          setRecords(recordRows)
          setTickets(ticketRows)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load operations data.')
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
  }, [tenantId])

  if (loading) {
    return <p className="page-note">Loading operations data…</p>
  }

  return (
    <div className="operations-page">
      <header className="page-header">
        <h2 className="page-header__title">Operations</h2>
        <p className="page-header__subtitle">
          Read-only explorer for tenant-scoped assets, history, and tickets. Writes go through
          AI / HITL.
        </p>
      </header>

      {error ? <p className="page-error">{error}</p> : null}

      <div className="ops-tabs" role="tablist">
        {(
          [
            ['assets', 'Assets'],
            ['history', 'Maintenance History'],
            ['tickets', 'Tickets'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'ops-tabs__button ops-tabs__button--active' : 'ops-tabs__button'}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'assets' ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset Code</th>
                <th>Name</th>
                <th>Location</th>
                <th>Status</th>
                <th>Active Error</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td>
                    <code>{asset.asset_code}</code>
                  </td>
                  <td>{asset.name}</td>
                  <td>{asset.location}</td>
                  <td>
                    <StatusBadge status={asset.status} />
                  </td>
                  <td>{asset.active_error_code ?? '—'}</td>
                  <td>
                    <button
                      type="button"
                      className="button button--secondary button--small"
                      onClick={() => onAskAboutAsset(asset.asset_code)}
                    >
                      Ask AI
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === 'history' ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Description</th>
                <th>Date</th>
                <th>Technician</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>
                    <code>{record.asset_code ?? '—'}</code>
                  </td>
                  <td>{record.description}</td>
                  <td>{record.maintenance_date}</td>
                  <td>{record.technician}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === 'tickets' ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Issue</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id}>
                  <td>
                    <code>{ticket.asset_code ?? '—'}</code>
                  </td>
                  <td>
                    <StatusBadge status={ticket.priority} />
                  </td>
                  <td>
                    <StatusBadge status={ticket.status} />
                  </td>
                  <td>{ticket.issue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
