import type { DemoTenant, PlaygroundPage } from '../types/playground'

export type TenantLoadStatus = 'loading' | 'success' | 'error'

type SidebarProps = {
  page: PlaygroundPage
  onNavigate: (page: PlaygroundPage) => void
}

const NAV_ITEMS: { id: PlaygroundPage; label: string; icon: string }[] = [
  {
    id: 'playground',
    label: 'Playground',
    icon: 'M8 4h8a2 2 0 012 2v12a2 2 0 01-2 2H8a2 2 0 01-2-2V6a2 2 0 012-2zm1 4h6v1.5H9V8zm0 3.5h6V13H9v-1.5zm0 3.5h4V16.5H9V15z',
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: 'M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zm7 1.5V9h4.5L14 4.5z',
  },
  {
    id: 'operations',
    label: 'Operations',
    icon: 'M4 6h16v2H4V6zm0 5h10v2H4v-2zm0 5h16v2H4v-2z',
  },
  {
    id: 'compare',
    label: 'Compare Runs',
    icon: 'M5 19V9h3v10H5zm6 0V5h3v14h-3zm6 0v-7h3v7h-3z',
  },
  {
    id: 'evaluation',
    label: 'Evaluation',
    icon: 'M5 19h14v2H5v-2zM7 15l3.2-4.2 2.4 1.8L18 6.5l1.4 1.1-6.1 8.2-2.5-1.9L8.2 17 7 15z',
  },
  {
    id: 'status',
    label: 'System Status',
    icon: 'M12 4a8 8 0 100 16 8 8 0 000-16zm0 3.2a1 1 0 011 1V13a1 1 0 11-2 0V8.2a1 1 0 011-1zm0 8.3a1.1 1.1 0 110 2.2 1.1 1.1 0 010-2.2z',
  },
  {
    id: 'architecture',
    label: 'Architecture',
    icon: 'M4 5h6v5H4V5zm10 0h6v5h-6V5zM9 14h6v5H9v-5zM7 10h2v4H7v-4zm8 0h2v4h-2v-4z',
  },
]

export function Sidebar({ page, onNavigate }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="Playground navigation">
      <p className="sidebar__label">Explore</p>
      <ul className="sidebar__list">
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={
                page === item.id ? 'sidebar__link sidebar__link--active' : 'sidebar__link'
              }
              aria-current={page === item.id ? 'page' : undefined}
              onClick={() => onNavigate(item.id)}
            >
              <svg className="sidebar__icon" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="currentColor" d={item.icon} />
              </svg>
              <span>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>

      <div className="sidebar__footer">
        <a
          className="sidebar__external"
          href="https://github.com/kkureli/enterprise-agentic-ai-platform"
          target="_blank"
          rel="noreferrer"
        >
          View Source
        </a>
      </div>
    </nav>
  )
}

type TenantSelectorProps = {
  tenants: DemoTenant[]
  selectedId: string
  status: TenantLoadStatus
  error: string | null
  onChange: (tenantId: string) => void
  onRetry: () => void
}

export function TenantSelector({
  tenants,
  selectedId,
  status,
  error,
  onChange,
  onRetry,
}: TenantSelectorProps) {
  const isLoading = status === 'loading'
  const isError = status === 'error'
  const isEmpty = status === 'success' && tenants.length === 0

  return (
    <div className="tenant-selector">
      <div className="tenant-selector__row">
        <label className="tenant-selector__label" htmlFor="demo-tenant">
          Tenant
        </label>
        {isLoading ? (
          <span className="tenant-selector__hint" aria-live="polite">
            Loading demo tenants…
          </span>
        ) : null}
      </div>

      <select
        id="demo-tenant"
        className="tenant-selector__select"
        value={isLoading || isError || isEmpty ? '' : selectedId}
        disabled={isLoading || isError || isEmpty}
        aria-busy={isLoading}
        onChange={(event) => onChange(event.target.value)}
      >
        {isLoading ? <option value="">Starting demo environment…</option> : null}
        {isError ? <option value="">Unable to load tenants</option> : null}
        {isEmpty ? <option value="">No demo tenants are available</option> : null}
        {status === 'success'
          ? tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name} — {tenant.short_label}
              </option>
            ))
          : null}
      </select>

      {isLoading ? (
        <p className="tenant-selector__note">
          Cloud demo may take a few seconds after being idle.
        </p>
      ) : null}

      {isError ? (
        <div className="tenant-selector__error-row">
          <p className="tenant-selector__error">
            {error ?? 'Unable to load demo tenants.'}
          </p>
          <button
            type="button"
            className="button button--secondary button--small"
            disabled={isLoading}
            onClick={onRetry}
            aria-label="Retry loading demo tenants"
          >
            Retry
          </button>
        </div>
      ) : null}

      {isEmpty ? (
        <p className="tenant-selector__note">No demo tenants are available.</p>
      ) : null}
    </div>
  )
}
