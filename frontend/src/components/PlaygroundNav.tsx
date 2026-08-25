import type { DemoTenant, PlaygroundPage } from '../types/playground'

type SidebarProps = {
  page: PlaygroundPage
  onNavigate: (page: PlaygroundPage) => void
}

const NAV_ITEMS: { id: PlaygroundPage; label: string }[] = [
  { id: 'playground', label: 'Playground' },
  { id: 'documents', label: 'Documents' },
  { id: 'operations', label: 'Operations' },
  { id: 'compare', label: 'Compare Runs' },
  { id: 'evaluation', label: 'Evaluation' },
  { id: 'status', label: 'System Status' },
  { id: 'architecture', label: 'Architecture' },
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
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
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
        <button
          type="button"
          className="sidebar__external sidebar__external--button"
          onClick={() => onNavigate('architecture')}
        >
          Architecture
        </button>
      </div>
    </nav>
  )
}

type TenantSelectorProps = {
  tenants: DemoTenant[]
  selectedId: string
  loading: boolean
  error: string | null
  onChange: (tenantId: string) => void
}

export function TenantSelector({
  tenants,
  selectedId,
  loading,
  error,
  onChange,
}: TenantSelectorProps) {
  return (
    <div className="tenant-selector">
      <label className="tenant-selector__label" htmlFor="demo-tenant">
        Tenant
      </label>
      <select
        id="demo-tenant"
        className="tenant-selector__select"
        value={selectedId}
        disabled={loading || tenants.length === 0}
        onChange={(event) => onChange(event.target.value)}
      >
        {tenants.length === 0 ? <option value="">No demo tenants seeded</option> : null}
        {tenants.map((tenant) => (
          <option key={tenant.id} value={tenant.id}>
            {tenant.name} — {tenant.short_label}
          </option>
        ))}
      </select>
      {error ? <p className="tenant-selector__error">{error}</p> : null}
    </div>
  )
}
