import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'

import { AgentApiError, runAgent } from './api/agent'
import {
  clearStoredTenantName,
  clearTenantId,
  getStoredTenantName,
  getTenantId,
  setStoredTenantName,
  setTenantId,
} from './api/config'
import { fetchEvaluations } from './api/demo'
import { listDemoTenants, listDocuments } from './api/playground'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './components/AsyncState'
import { HeaderSocialLinks } from './components/HeaderSocialLinks'
import { Sidebar, TenantSelector, type TenantLoadStatus } from './components/PlaygroundNav'
import { DocumentsPage } from './pages/DocumentsPage'
import { OperationsPage } from './pages/OperationsPage'
import { PlaygroundChat } from './pages/PlaygroundChat'
import {
  TTL,
  cachedFetch,
  invalidateCache,
  invalidateTenantScopedCaches,
} from './lib/requestCache'
import { logScreenView } from './lib/firebase'
import type { AgentResponse, ChatMessage, ExecutionDetails, RetrievalMode } from './types/agent'
import type { DemoTenant, PlaygroundPage } from './types/playground'

const ArchitecturePage = lazy(() =>
  import('./pages/ArchitecturePage').then((module) => ({ default: module.ArchitecturePage })),
)
const CompareRunsPage = lazy(() =>
  import('./pages/CompareRunsPage').then((module) => ({ default: module.CompareRunsPage })),
)
const EvaluationPage = lazy(() =>
  import('./pages/EvaluationPage').then((module) => ({ default: module.EvaluationPage })),
)
const SystemStatusPage = lazy(() =>
  import('./pages/SystemStatusPage').then((module) => ({ default: module.SystemStatusPage })),
)

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

function scheduleIdle(task: () => void): () => void {
  const richWindow = window as Window & {
    requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number
    cancelIdleCallback?: (handle: number) => void
  }

  if (typeof richWindow.requestIdleCallback === 'function') {
    const handle = richWindow.requestIdleCallback(() => task(), { timeout: 2500 })
    return () => richWindow.cancelIdleCallback?.(handle)
  }

  const handle = window.setTimeout(task, 400)
  return () => window.clearTimeout(handle)
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

  const loadTenants = useCallback(async (force = false) => {
    const generation = ++loadGenerationRef.current
    if (!force) {
      setTenantStatus((current) => (current === 'success' ? current : 'loading'))
    } else {
      setTenantStatus('loading')
    }
    setTenantsError(null)

    try {
      const demoTenants = await cachedFetch('demo-tenants', listDemoTenants, {
        ttlMs: TTL.tenants,
        force,
      })

      if (generation !== loadGenerationRef.current) {
        return
      }

      setTenants(demoTenants)
      setTenantStatus('success')

      if (demoTenants.length === 0) {
        setSelectedTenantId('')
        clearTenantId()
        clearStoredTenantName()
        return
      }

      const storedId = getTenantId()
      const storedName = getStoredTenantName()
      const byId = demoTenants.find((tenant) => tenant.id === storedId)
      const byName = storedName
        ? demoTenants.find((tenant) => tenant.name === storedName)
        : undefined
      const next = byId ?? byName ?? demoTenants[0]

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
    logScreenView(page)
  }, [page])

  useEffect(() => {
    if (tenantStatus !== 'success' || !selectedTenantId) {
      return
    }

    return scheduleIdle(() => {
      void cachedFetch('evaluations', fetchEvaluations, { ttlMs: TTL.evaluations })
      void cachedFetch(
        `documents:${selectedTenantId}`,
        () => listDocuments(selectedTenantId),
        { ttlMs: TTL.documents },
      )
    })
  }, [selectedTenantId, tenantStatus])

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
    setRetrievalMode('standard')
    setPage('playground')
  }

  const sendQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      const tenantId = selectedTenantId.trim()

      if (!trimmed || sendingLockRef.current || !tenantId || cooldownActive) {
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
        const response = await runAgent(tenantId, trimmed, retrievalMode)
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
    if (approved && selectedTenantId) {
      invalidateTenantScopedCaches(selectedTenantId)
      invalidateCache(`operations:${selectedTenantId}`)
    }

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
          onRetry={() => void loadTenants(true)}
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
          tenantId={selectedTenant.id}
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
      return (
        <Suspense fallback={<LoadingBlock title="Loading compare tools…" compact />}>
          <CompareRunsPage
            key={selectedTenant.id}
            tenantId={selectedTenant.id}
            disabled={aiBusy}
          />
        </Suspense>
      )
    }

    return null
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <button
            type="button"
            className="app-header__logo"
            aria-label="Go to Playground home"
            onClick={() => setPage('playground')}
          >
            EA
          </button>
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

        <div className="app-header__actions">
          <TenantSelector
            tenants={tenants}
            selectedId={selectedTenantId}
            status={tenantStatus}
            error={tenantsError}
            onChange={handleTenantChange}
            onRetry={() => void loadTenants(true)}
          />
          <HeaderSocialLinks />
        </div>
      </header>

      <div className="app-layout">
        <Sidebar page={page} onNavigate={setPage} />

        <main className="app-main">
          <div className="app-main__inner">
            {needsTenant ? renderTenantGatedContent() : null}
            <Suspense fallback={<LoadingBlock title="Loading page…" compact />}>
              {page === 'evaluation' ? <EvaluationPage /> : null}
              {page === 'status' ? <SystemStatusPage /> : null}
              {page === 'architecture' ? <ArchitecturePage onNavigate={setPage} /> : null}
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}
