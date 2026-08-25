import { useState } from 'react'

import {
  listAssets,
  listMaintenanceRecords,
  listMaintenanceTickets,
} from '../api/playground'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState'
import { StatusBadge } from '../components/StatusBadge'
import { useCachedResource } from '../hooks/useCachedResource'
import { TTL, cacheKeyOperations } from '../lib/requestCache'
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

type OperationsBundle = {
  assets: Asset[]
  records: MaintenanceRecord[]
  tickets: MaintenanceTicket[]
}

async function fetchOperationsBundle(tenantId: string): Promise<OperationsBundle> {
  const [assets, records, tickets] = await Promise.all([
    listAssets(tenantId),
    listMaintenanceRecords(tenantId),
    listMaintenanceTickets(tenantId),
  ])
  return { assets, records, tickets }
}

export function OperationsPage({ tenantId, onAskAboutAsset }: OperationsPageProps) {
  const [tab, setTab] = useState<OpsTab>('assets')
  const { data, error, status, isRefreshing, reload } = useCachedResource({
    key: cacheKeyOperations(tenantId),
    ttlMs: TTL.operations,
    fetcher: () => fetchOperationsBundle(tenantId),
  })

  const assets = data?.assets ?? []
  const records = data?.records ?? []
  const tickets = data?.tickets ?? []

  const emptyForTab =
    (tab === 'assets' && assets.length === 0) ||
    (tab === 'history' && records.length === 0) ||
    (tab === 'tickets' && tickets.length === 0)

  return (
    <div className="operations-page">
      <header className="page-header">
        <h2 className="page-header__title">Operations</h2>
        <p className="page-header__subtitle">
          Read-only explorer for tenant-scoped assets, history, and tickets. Writes go through
          AI / HITL.
          {isRefreshing ? ' · Refreshing…' : null}
        </p>
      </header>

      {status === 'loading' ? (
        <LoadingBlock title="Loading operations data…" compact />
      ) : null}

      {status === 'error' ? (
        <ErrorBlock
          title="Unable to load operations data."
          message={error}
          onRetry={() => void reload(true)}
        />
      ) : null}

      {status === 'success' ? (
        <>
          <div className="ops-tabs" role="tablist" aria-label="Operations tables">
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
                className={
                  tab === id ? 'ops-tabs__button ops-tabs__button--active' : 'ops-tabs__button'
                }
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {emptyForTab ? (
            <EmptyBlock
              title={`No ${tab === 'history' ? 'maintenance history' : tab} for this tenant.`}
            />
          ) : null}

          {tab === 'assets' && assets.length > 0 ? (
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
                          aria-label={`Ask AI about ${asset.asset_code}`}
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

          {tab === 'history' && records.length > 0 ? (
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

          {tab === 'tickets' && tickets.length > 0 ? (
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
        </>
      ) : null}
    </div>
  )
}
