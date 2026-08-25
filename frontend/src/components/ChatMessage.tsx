import { ApprovalCard } from './ApprovalCard'
import { DetailsPanel } from './DetailsPanel'
import { ExecutionTrace } from './ExecutionTrace'
import { RouteBadge } from './RouteBadge'
import type { ChatMessage } from '../types/agent'

type ChatMessageProps = {
  message: ChatMessage
  onApprovalResolved: (
    messageId: string,
    approved: boolean,
    answer: string,
    executionDetails?: import('../types/agent').ExecutionDetails | null,
  ) => void
}

export function ChatMessageItem({ message, onApprovalResolved }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <article className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}`}>
      <div className="chat-message__meta">
        <span className="chat-message__role">{isUser ? 'You' : 'Assistant'}</span>
        {!isUser && message.route ? <RouteBadge route={message.route} /> : null}
        {message.error ? <span className="chat-message__error-label">Error</span> : null}
      </div>

      <div className={`chat-message__bubble ${message.error ? 'chat-message__bubble--error' : ''}`}>
        {message.isLoading ? (
          <span className="chat-message__loading">
            <span className="chat-message__dot" />
            <span className="chat-message__dot" />
            <span className="chat-message__dot" />
            Thinking…
          </span>
        ) : (
          <p className="chat-message__text">{message.content}</p>
        )}
      </div>

      {!isUser &&
      message.status === 'approval_required' &&
      message.pendingAction &&
      message.threadId &&
      !message.approvalResolved ? (
        <ApprovalCard
          threadId={message.threadId}
          pendingAction={message.pendingAction}
          onResolved={(approved, answer, executionDetails) =>
            onApprovalResolved(message.id, approved, answer, executionDetails)
          }
        />
      ) : null}

      {!isUser && message.approvalResolved ? (
        <p className="chat-message__approval-status">
          {message.approvalResolved === 'approved' ? 'Action approved.' : 'Action rejected.'}
        </p>
      ) : null}

      {!isUser && !message.isLoading ? (
        <ExecutionTrace details={message.executionDetails} />
      ) : null}

      {!isUser && !message.isLoading ? (
        <DetailsPanel
          route={message.route}
          retrievalMode={message.retrievalMode}
          threadId={message.threadId}
        />
      ) : null}
    </article>
  )
}
