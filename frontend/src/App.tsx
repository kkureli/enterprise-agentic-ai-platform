import { useCallback, useEffect, useRef, useState } from 'react'

import { AgentApiError, runAgent } from './api/agent'
import { getTenantId, isTenantConfigured, setTenantId } from './api/config'
import { ChatComposer } from './components/ChatComposer'
import { ChatMessageItem } from './components/ChatMessage'
import { EmptyState } from './components/EmptyState'
import type { AgentResponse, ChatMessage, RetrievalMode } from './types/agent'

function createId(): string {
  return crypto.randomUUID()
}

function responseToMessage(response: AgentResponse, retrievalMode: RetrievalMode): ChatMessage {
  return {
    id: createId(),
    role: 'assistant',
    content: response.answer,
    route: response.route,
    status: response.status,
    pendingAction: response.pending_action,
    threadId: response.thread_id,
    retrievalMode,
  }
}

function loadingMessage(): ChatMessage {
  return {
    id: createId(),
    role: 'assistant',
    content: '',
    isLoading: true,
  }
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('standard')
  const [isSending, setIsSending] = useState(false)
  const [tenantInput, setTenantInput] = useState(getTenantId())
  const [tenantReady, setTenantReady] = useState(isTenantConfigured())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()

      if (!trimmed || isSending || !tenantReady) {
        return
      }

      const userMessage: ChatMessage = {
        id: createId(),
        role: 'user',
        content: trimmed,
      }

      const assistantPlaceholder = loadingMessage()

      setMessages((current) => [...current, userMessage, assistantPlaceholder])
      setInput('')
      setIsSending(true)

      try {
        const response = await runAgent(trimmed, retrievalMode)
        const assistantMessage = responseToMessage(response, retrievalMode)

        setMessages((current) =>
          current.map((message) =>
            message.id === assistantPlaceholder.id ? assistantMessage : message,
          ),
        )
      } catch (error) {
        const errorText =
          error instanceof AgentApiError
            ? error.message
            : 'Something went wrong. Please try again.'

        setMessages((current) =>
          current.map((message) =>
            message.id === assistantPlaceholder.id
              ? {
                  id: message.id,
                  role: 'assistant',
                  content: errorText,
                  error: true,
                }
              : message,
          ),
        )
      } finally {
        setIsSending(false)
      }
    },
    [isSending, retrievalMode, tenantReady],
  )

  function handleApprovalResolved(messageId: string, approved: boolean, answer: string) {
    setMessages((current) => {
      const updated = current.map((message) =>
        message.id === messageId
          ? {
              ...message,
              approvalResolved: approved ? ('approved' as const) : ('rejected' as const),
              status: 'completed' as const,
            }
          : message,
      )

      if (answer.trim()) {
        const source = current.find((message) => message.id === messageId)
        updated.push({
          id: createId(),
          role: 'assistant',
          content: answer,
          route: source?.route,
          threadId: source?.threadId,
          retrievalMode: source?.retrievalMode,
          status: 'completed',
        })
      }

      return updated
    })
  }

  function handleSaveTenant() {
    const trimmed = tenantInput.trim()

    if (!trimmed) {
      return
    }

    setTenantId(trimmed)
    setTenantReady(true)
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo" aria-hidden="true">
            EA
          </div>
          <div>
            <h1 className="app-header__title">Enterprise Operations Assistant</h1>
            <p className="app-header__subtitle">Knowledge · Data · Tools · Human approval</p>
          </div>
        </div>

        {!tenantReady ? (
          <div className="tenant-config">
            <label className="tenant-config__label" htmlFor="tenant-id">
              Tenant ID
            </label>
            <input
              id="tenant-id"
              className="tenant-config__input"
              value={tenantInput}
              placeholder="Paste local tenant UUID"
              onChange={(event) => setTenantInput(event.target.value)}
            />
            <button type="button" className="button button--secondary" onClick={handleSaveTenant}>
              Connect
            </button>
          </div>
        ) : (
          <div className="tenant-config tenant-config--connected">
            <span className="tenant-config__status">Connected</span>
            <code className="tenant-config__id">{getTenantId()}</code>
          </div>
        )}
      </header>

      <main className="chat-panel">
        <div className="chat-panel__messages">
          {messages.length === 0 ? (
            <EmptyState onSelectPrompt={(prompt) => sendQuestion(prompt)} />
          ) : (
            messages.map((message) => (
              <ChatMessageItem
                key={message.id}
                message={message}
                onApprovalResolved={handleApprovalResolved}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <ChatComposer
          value={input}
          retrievalMode={retrievalMode}
          disabled={isSending || !tenantReady}
          onChange={setInput}
          onRetrievalModeChange={setRetrievalMode}
          onSubmit={() => sendQuestion(input)}
        />
      </main>
    </div>
  )
}
