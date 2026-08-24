import type { AgentRoute } from '../types/agent'

const ROUTE_LABELS: Record<AgentRoute, string> = {
  knowledge: 'Knowledge',
  sql: 'Data',
  tool: 'Tool',
  unsupported: 'Unsupported',
}

type RouteBadgeProps = {
  route: AgentRoute
}

export function RouteBadge({ route }: RouteBadgeProps) {
  return <span className={`route-badge route-badge--${route}`}>{ROUTE_LABELS[route]}</span>
}
