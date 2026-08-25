import { useCallback, useEffect, useRef, useState } from 'react'

import { AgentApiError, runAgent } from './api/agent'
import {
  getTenantId,
  setStoredTenantName,
  setTenantId,
} from './api/config'
import { listDemoTenants } from './api/playground'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './components/AsyncState'
import { Sidebar, TenantSelector, type TenantLoadStatus } from './components/PlaygroundNav'
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

const TENANT_OPTIONAL_PAGES: PlaygroundPage[] = ['architecture', 'evaluation', 'status']

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
  const [tenantStatus, setTenantStatus] = useState<TenantLoadStatus>('loading')
  const [tenantsError, setTenantsError] = useState<string | null>(null)
  const [selectedTenantId, setSelectedTenantId] = useState(getTenantId())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('standard')
  const [isSending, setIsSending] = useState(false)
  const [cooldownActive, setCooldownActive] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sendingLockRef = useRef(false)
  const cooldownTimerRef = useRef<number | null>(null)
  const loadGenerationRef = useRef(0)

  const aiBusy = isSending || cooldownActive
  const needsTenant = !TENANT_OPTIONAL_PAGES.includes(page)

  const loadTenants = useCallback(async () => {
    const generation = ++loadGenerationRef.current
    setTenantStatus('loading')
    setTenantsError(null)

    try {
      const demoTenants = await listDemoTenants()

      if (generation !== loadGenerationRef.current) {
        return
      }

      setTenants(demoTenants)
      setTenantStatus('success')

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
      if (generation !== loadGenerationRef.current) {
        return
      }

      setTenants([])
      setTenantStatus('error')
      setTenantsError(
        error instanceof Error ? error.message : 'Unable to load demo tenants.',
      )
    }
  }, [])

  useEffect(() => {
    void loadTenants()
  }, [loadTenants])

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

  function renderTenantGatedContent() {
    if (tenantStatus === 'loading') {
      return (
        <LoadingBlock
          title="Starting demo environment…"
          subtitle="Loading demo tenants. Cloud demo may take a few seconds after being idle."
        />
      )
    }

    if (tenantStatus === 'error') {
      return (
        <ErrorBlock
          title="Unable to load demo tenants."
          message={tenantsError}
          onRetry={() => void loadTenants()}
          retrying={false}
        />
      )
    }

    if (tenants.length === 0) {
      return (
        <EmptyBlock
          title="No demo tenants are available."
          message="The public demo expects Atlas Manufacturing, Borealis Cold Chain, and Helios Energy Services."
        />
      )
    }

    if (!selectedTenant) {
      return (
        <EmptyBlock
          title="No demo tenants are available."
          message="Select a tenant from the header to continue."
        />
      )
    }

    if (page === 'playground') {
      return (
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
      )
    }

    if (page === 'documents') {
      return <DocumentsPage tenantId={selectedTenant.id} />
    }

    if (page === 'operations') {
      return (
        <OperationsPage
          tenantId={selectedTenant.id}
          onAskAboutAsset={handleAskAboutAsset}
        />
      )
    }

    if (page === 'compare') {
      return <CompareRunsPage disabled={aiBusy} />
    }

    return null
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo" aria-hidden="true">
            EA
          </div>
          <div>
            <div className="app-header__title-row">
              <h1 className="app-header__title">Enterprise Agentic AI Playground</h1>
              <span className="live-badge">Live Demo</span>
            </div>
            <p className="app-header__subtitle">
              Multi-tenant RAG · SQL · MCP · HITL
            </p>
          </div>
        </div>

        <TenantSelector
          tenants={tenants}
          selectedId={selectedTenantId}
          status={tenantStatus}
          error={tenantsError}
          onChange={handleTenantChange}
          onRetry={() => void loadTenants()}
        />
      </header>

      <div className="app-layout">
        <Sidebar page={page} onNavigate={setPage} />

        <main className="app-main">
          <div className="app-main__inner">
            {needsTenant ? renderTenantGatedContent() : null}
            {page === 'evaluation' ? <EvaluationPage /> : null}
            {page === 'status' ? <SystemStatusPage /> : null}
            {page === 'architecture' ? <ArchitecturePage onNavigate={setPage} /> : null}
          </div>
        </main>
      </div>
    </div>
  )
}
