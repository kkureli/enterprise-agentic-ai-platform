import { useCallback, useEffect, useRef, useState } from 'react'

import { AgentApiError, runAgent } from './api/agent'
import {
  getTenantId,
  setStoredTenantName,
  setTenantId,
} from './api/config'
import { listDemoTenants } from './api/playground'
import { Sidebar, TenantSelector } from './components/PlaygroundNav'
import { ArchitecturePage } from './pages/ArchitecturePage'
import { CompareRunsPage } from './pages/CompareRunsPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { OperationsPage } from './pages/OperationsPage'
import { PlaygroundChat } from './pages/PlaygroundChat'
import { SystemStatusPage } from './pages/SystemStatusPage'
import type { AgentResponse, ChatMessage, ExecutionDetails, RetrievalMode } from './types/agent'
import type { DemoTenant, PlaygroundPage } from './types/playground'

const CLIENT_COOLDOWN_MS = 1500

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
    executionDetails: response.execution_details,
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
  const [page, setPage] = useState<PlaygroundPage>('playground')
  const [tenants, setTenants] = useState<DemoTenant[]>([])
  const [tenantsLoading, setTenantsLoading] = useState(true)
  const [tenantsError, setTenantsError] = useState<string | null>(null)
  const [selectedTenantId, setSelectedTenantId] = useState(getTenantId())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('standard')
  const [isSending, setIsSending] = useState(false)
  const [cooldownActive, setCooldownActive] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const tenantsLoadedRef = useRef(false)
  const sendingLockRef = useRef(false)
  const cooldownTimerRef = useRef<number | null>(null)

  const aiBusy = isSending || cooldownActive

  useEffect(() => {
    if (tenantsLoadedRef.current) {
      return
    }

    tenantsLoadedRef.current = true
    let cancelled = false

    async function loadTenants() {
      setTenantsLoading(true)
      setTenantsError(null)

      try {
        const demoTenants = await listDemoTenants()

        if (cancelled) {
          return
        }

        setTenants(demoTenants)

        if (demoTenants.length === 0) {
          setSelectedTenantId('')
          return
        }

        const existing = demoTenants.find((tenant) => tenant.id === getTenantId())
        const next = existing ?? demoTenants[0]

        setSelectedTenantId(next.id)
        setTenantId(next.id)
        setStoredTenantName(next.name)
      } catch (error) {
        if (!cancelled) {
          setTenantsError(
            error instanceof Error ? error.message : 'Failed to load demo tenants.',
          )
        }
      } finally {
        if (!cancelled) {
          setTenantsLoading(false)
        }
      }
    }

    void loadTenants()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current != null) {
        window.clearTimeout(cooldownTimerRef.current)
      }
    }
  }, [])

  const selectedTenant =
    tenants.find((tenant) => tenant.id === selectedTenantId) ?? null

  function handleTenantChange(tenantId: string) {
    const tenant = tenants.find((item) => item.id === tenantId)

    if (!tenant) {
      return
    }

    setSelectedTenantId(tenant.id)
    setTenantId(tenant.id)
    setStoredTenantName(tenant.name)
    setMessages([])
    setInput('')
    setPage('playground')
  }

  const sendQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()

      if (!trimmed || sendingLockRef.current || !selectedTenantId || cooldownActive) {
        return
      }

      sendingLockRef.current = true

      const userMessage: ChatMessage = {
        id: createId(),
        role: 'user',
        content: trimmed,
      }

      const assistantPlaceholder = loadingMessage()

      setMessages((current) => [...current, userMessage, assistantPlaceholder])
      setInput('')
      setIsSending(true)
      setPage('playground')

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
        sendingLockRef.current = false
        setCooldownActive(true)
        if (cooldownTimerRef.current != null) {
          window.clearTimeout(cooldownTimerRef.current)
        }
        cooldownTimerRef.current = window.setTimeout(() => {
          setCooldownActive(false)
          cooldownTimerRef.current = null
        }, CLIENT_COOLDOWN_MS)
      }
    },
    [cooldownActive, retrievalMode, selectedTenantId],
  )

  function handleApprovalResolved(
    messageId: string,
    approved: boolean,
    answer: string,
    executionDetails?: ExecutionDetails | null,
  ) {
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
          executionDetails: executionDetails ?? source?.executionDetails,
          status: 'completed',
        })
      }

      return updated
    })
  }

  function handleAskAboutAsset(assetCode: string) {
    void sendQuestion(`What is the current operational status of ${assetCode}?`)
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo" aria-hidden="true">
            EA
          </div>
          <div>
            <h1 className="app-header__title">Enterprise Agentic AI Playground</h1>
            <p className="app-header__subtitle">
              Explore multi-tenant RAG, SQL, MCP tools, and human approval
            </p>
          </div>
        </div>

        <TenantSelector
          tenants={tenants}
          selectedId={selectedTenantId}
          loading={tenantsLoading}
          error={tenantsError}
          onChange={handleTenantChange}
        />
      </header>

      <div className="app-layout">
        <Sidebar page={page} onNavigate={setPage} />

        <main className="app-main">
          {!selectedTenant && page !== 'architecture' && page !== 'evaluation' && page !== 'status' ? (
            <div className="page-empty">
              <h2>Demo tenants unavailable</h2>
              <p>
                Seed the playground tenants, then reload. The public demo only exposes Atlas
                Manufacturing, Borealis Cold Chain, and Helios Energy Services.
              </p>
            </div>
          ) : null}

          {selectedTenant && page === 'playground' ? (
            <PlaygroundChat
              tenantName={selectedTenant.name}
              messages={messages}
              input={input}
              retrievalMode={retrievalMode}
              isSending={aiBusy}
              messagesEndRef={messagesEndRef}
              onInputChange={setInput}
              onRetrievalModeChange={setRetrievalMode}
              onSubmit={() => sendQuestion(input)}
              onSelectPrompt={(prompt) => sendQuestion(prompt)}
              onApprovalResolved={handleApprovalResolved}
            />
          ) : null}

          {selectedTenant && page === 'documents' ? (
            <DocumentsPage tenantId={selectedTenant.id} />
          ) : null}

          {selectedTenant && page === 'operations' ? (
            <OperationsPage
              tenantId={selectedTenant.id}
              onAskAboutAsset={handleAskAboutAsset}
            />
          ) : null}

          {selectedTenant && page === 'compare' ? (
            <CompareRunsPage disabled={aiBusy} />
          ) : null}

          {page === 'evaluation' ? <EvaluationPage /> : null}

          {page === 'status' ? <SystemStatusPage /> : null}

          {page === 'architecture' ? <ArchitecturePage /> : null}
        </main>
      </div>
    </div>
  )
}
