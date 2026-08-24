export type AgentRoute = 'knowledge' | 'sql' | 'tool' | 'unsupported'

export type AgentStatus = 'completed' | 'approval_required'

export type RetrievalMode = 'standard' | 'advanced'

export type PendingAction = {
  tool_name: string
  arguments: Record<string, string>
}

export type AgentResponse = {
  thread_id: string
  status: AgentStatus
  route: AgentRoute
  answer: string
  pending_action: PendingAction | null
}

export type ChatMessageRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatMessageRole
  content: string
  route?: AgentRoute
  status?: AgentStatus
  pendingAction?: PendingAction | null
  threadId?: string
  retrievalMode?: RetrievalMode
  error?: boolean
  approvalResolved?: 'approved' | 'rejected'
  isLoading?: boolean
}
