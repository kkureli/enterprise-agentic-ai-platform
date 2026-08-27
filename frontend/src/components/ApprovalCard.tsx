import { useState } from 'react'

import { approveAgentAction, AgentApiError } from '../api/agent'
import type { ExecutionDetails, PendingAction } from '../types/agent'

type ApprovalCardProps = {
  tenantId: string
  threadId: string
  pendingAction: PendingAction
  onResolved: (
    approved: boolean,
    answer: string,
    executionDetails?: ExecutionDetails | null,
  ) => void
}

function formatPriority(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1).toLowerCase()
}

function formatActionTitle(toolName: string): string {
  if (toolName === 'create_maintenance_ticket') {
    return 'Create maintenance ticket?'
  }
  if (toolName === 'create_github_issue') {
    return 'Open GitHub Issue?'
  }

  return `Approve action: ${toolName.replaceAll('_', ' ')}`
}

function asText(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) {
    return value.trim()
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return null
}

export function ApprovalCard({
  tenantId,
  threadId,
  pendingAction,
  onResolved,
}: ApprovalCardProps) {
  const [pending, setPending] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const args = pendingAction.arguments
  const isGithub = pendingAction.tool_name === 'create_github_issue'
  const title = asText(args.title)
  const company = asText(args.company_query)
  const assetCode = asText(args.asset_code)
  const issue = asText(args.issue)
  const priority = asText(args.priority)
  const labels = Array.isArray(args.labels)
    ? args.labels.map((item) => String(item)).filter(Boolean)
    : []

  async function handleDecision(approved: boolean) {
    setPending(true)
    setLocalError(null)

    try {
      const response = await approveAgentAction(tenantId, threadId, approved)
      onResolved(approved, response.answer, response.execution_details)
    } catch (error) {
      const message =
        error instanceof AgentApiError
          ? error.message
          : 'Approval request failed. Please try again.'
      setLocalError(message)
      setPending(false)
    }
  }

  return (
    <div className="approval-card" role="region" aria-label="Action approval required">
      <div className="approval-card__header">
        <span className="approval-card__icon" aria-hidden="true">
          !
        </span>
        <h3 className="approval-card__title">{formatActionTitle(pendingAction.tool_name)}</h3>
      </div>

      <dl className="approval-card__details">
        {isGithub && title ? (
          <>
            <dt>Title</dt>
            <dd>{title}</dd>
          </>
        ) : null}
        {isGithub && company ? (
          <>
            <dt>Company</dt>
            <dd>{company}</dd>
          </>
        ) : null}
        {isGithub && labels.length > 0 ? (
          <>
            <dt>Labels</dt>
            <dd>{labels.join(', ')}</dd>
          </>
        ) : null}
        {assetCode ? (
          <>
            <dt>Asset</dt>
            <dd>{assetCode}</dd>
          </>
        ) : null}
        {issue ? (
          <>
            <dt>Issue</dt>
            <dd>{issue}</dd>
          </>
        ) : null}
        {priority ? (
          <>
            <dt>Priority</dt>
            <dd>{formatPriority(priority)}</dd>
          </>
        ) : null}
      </dl>

      <p className="approval-card__hint">
        {isGithub
          ? 'Approving creates a real GitHub Issue in the project repository via MCP. Rejecting performs no external write.'
          : 'Review the details above. Approving will execute this action through the backend approval workflow.'}
      </p>

      {localError ? <p className="approval-card__error">{localError}</p> : null}

      <div className="approval-card__actions">
        <button
          type="button"
          className="button button--secondary"
          disabled={pending}
          onClick={() => handleDecision(false)}
        >
          {pending ? 'Processing…' : 'Reject'}
        </button>
        <button
          type="button"
          className="button button--primary"
          disabled={pending}
          onClick={() => handleDecision(true)}
        >
          {pending ? 'Processing…' : 'Approve'}
        </button>
      </div>
    </div>
  )
}
