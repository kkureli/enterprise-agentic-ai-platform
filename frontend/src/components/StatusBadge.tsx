type StatusBadgeProps = {
  status: string
}

const LABEL_MAP: Record<string, string> = {
  operational: 'Operational',
  warning: 'Warning',
  maintenance: 'Maintenance',
  open: 'Open',
  closed: 'Completed',
  completed: 'Completed',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  critical: 'Critical',
  indexed: 'Indexed',
  healthy: 'Healthy',
  degraded: 'Degraded',
  unavailable: 'Unavailable',
  available: 'Available',
  unknown: 'Unknown',
}

function toLabel(status: string): string {
  const key = status.toLowerCase()
  if (LABEL_MAP[key]) {
    return LABEL_MAP[key]
  }

  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase()

  return (
    <span className={`status-badge status-badge--${normalized}`}>{toLabel(status)}</span>
  )
}
