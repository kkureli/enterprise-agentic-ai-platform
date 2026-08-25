export type DemoTenant = {
  id: string
  name: string
  description: string
  short_label: string
}

export type DocumentSummary = {
  id: string
  tenant_id: string
  filename: string
  content_type: string
  file_size_bytes: number
  checksum_sha256: string
  status: string
  created_at: string
  updated_at: string
}

export type DocumentChunk = {
  chunk_index: number
  text: string
  filename: string
  document_id: string
}

export type DocumentInspect = {
  document: DocumentSummary
  chunks: DocumentChunk[]
  note: string
}

export type Asset = {
  id: string
  tenant_id: string
  asset_code: string
  name: string
  location: string
  status: string
  active_error_code: string | null
  created_at: string
  updated_at: string
}

export type MaintenanceRecord = {
  id: string
  tenant_id: string
  asset_id: string
  asset_code: string | null
  maintenance_date: string
  maintenance_type: string
  description: string
  technician: string
  created_at: string
}

export type MaintenanceTicket = {
  id: string
  tenant_id: string
  asset_id: string
  asset_code: string | null
  issue: string
  priority: string
  status: string
  created_at: string
  updated_at: string
}

export type PlaygroundPage =
  | 'playground'
  | 'documents'
  | 'operations'
  | 'compare'
  | 'evaluation'
  | 'status'
  | 'architecture'

export type PromptCategory =
  | 'Knowledge / RAG'
  | 'Structured Data / SQL'
  | 'Live Tools / MCP'
  | 'Human Approval / HITL'
  | 'Composite / Synthesis'
  | 'Tenant Isolation'

/** Display order for Playground example cards. */
export const PROMPT_CATEGORY_ORDER: PromptCategory[] = [
  'Knowledge / RAG',
  'Structured Data / SQL',
  'Live Tools / MCP',
  'Human Approval / HITL',
  'Composite / Synthesis',
]
