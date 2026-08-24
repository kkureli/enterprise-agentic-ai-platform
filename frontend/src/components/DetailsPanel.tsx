import type { AgentRoute, RetrievalMode } from '../types/agent'

type DetailsPanelProps = {
  route?: AgentRoute
  retrievalMode?: RetrievalMode
  threadId?: string
}

export function DetailsPanel({ route, retrievalMode, threadId }: DetailsPanelProps) {
  if (!route && !retrievalMode && !threadId) {
    return null
  }

  return (
    <details className="details-panel">
      <summary>Details</summary>
      <dl className="details-panel__list">
        {route ? (
          <>
            <dt>Route</dt>
            <dd>{route}</dd>
          </>
        ) : null}
        {retrievalMode ? (
          <>
            <dt>Retrieval mode</dt>
            <dd>{retrievalMode}</dd>
          </>
        ) : null}
        {threadId ? (
          <>
            <dt>Thread ID</dt>
            <dd className="details-panel__mono">{threadId}</dd>
          </>
        ) : null}
      </dl>
    </details>
  )
}
