import { useState } from 'react'

import { approveAgentAction, AgentApiError } from '../api/agent'
import type { ExecutionDetails, PendingAction } from '../types/agent'

type ApprovalCardProps = {
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

  return `Approve action: ${toolName.replaceAll('_', ' ')}`
}

export function ApprovalCard({ threadId, pendingAction, onResolved }: ApprovalCardProps) {
  const [pending, setPending] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const args = pendingAction.arguments

  async function handleDecision(approved: boolean) {
    setPending(true)
    setLocalError(null)

    try {
      const response = await approveAgentAction(threadId, approved)
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
        {args.asset_code ? (
          <>
            <dt>Asset</dt>
            <dd>{args.asset_code}</dd>
          </>
        ) : null}
        {args.issue ? (
          <>
            <dt>Issue</dt>
            <dd>{args.issue}</dd>
          </>
        ) : null}
        {args.priority ? (
          <>
            <dt>Priority</dt>
            <dd>{formatPriority(args.priority)}</dd>
          </>
        ) : null}
      </dl>

      <p className="approval-card__hint">
        Review the details above. Approving will execute this action through the backend approval
        workflow.
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
