import { getApiBaseUrl } from './config'
import { PlaygroundApiError } from './playground'
import type { AgentResponse } from '../types/agent'

function mapLimitDetail(detail: string, status: number, retryAfter?: number): string {
  if (status === 429 && retryAfter && Number.isFinite(retryAfter)) {
    return `Demo request limit reached. Try again in ${retryAfter} seconds.`
  }
  return detail
}

export type DemoEvaluations = {
  disclaimer: string
  agent: {
    total_cases: number
    route_accuracy: number
    approval_accuracy: number
    execution_success_rate: number
    end_to_end_pass_rate: number
    required_capability_recall?: number | null
    exact_capability_set_accuracy?: number | null
    unnecessary_capability_rate?: number | null
    per_capability_execution_success?: number | null
    synthesis_required_fact_coverage?: number | null
    tenant_correctness?: number | null
    composite_cases?: number | null
  }
  retrieval: {
    num_queries: number
    eval_k: number
    strategies: Array<{
      name: string
      recall_at_k: number
      mrr: number
      ndcg_at_k: number
    }>
  }
}

export type DemoUsage = {
  status: 'available' | 'limited' | string
}

export type SystemStatus = {
  overall: string
  components: Array<{
    name: string
    status: string
    role?: string | null
  }>
}

export type CompareResponse = {
  question: string
  standard: AgentResponse
  advanced: AgentResponse
  note: string
}

async function parseJson<T>(response: Response): Promise<T> {
  let payload: unknown

  try {
    payload = await response.json()
  } catch {
    throw new PlaygroundApiError('Received an invalid response from the server.', response.status)
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : 'Request failed.'

    const retryHeader = response.headers.get('Retry-After')
    const retryAfter = retryHeader ? Number(retryHeader) : undefined
    const normalized = Number.isFinite(retryAfter) ? retryAfter : undefined

    throw new PlaygroundApiError(
      mapLimitDetail(detail, response.status, normalized),
      response.status,
      normalized,
    )
  }

  return payload as T
}

export async function fetchEvaluations(): Promise<DemoEvaluations> {
  const response = await fetch(`${getApiBaseUrl()}/demo/evaluations`)
  return parseJson<DemoEvaluations>(response)
}

export async function fetchDemoUsage(): Promise<DemoUsage> {
  const response = await fetch(`${getApiBaseUrl()}/demo/usage`)
  return parseJson<DemoUsage>(response)
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${getApiBaseUrl()}/demo/status`)
  return parseJson<SystemStatus>(response)
}

export async function compareAgentRuns(
  tenantId: string,
  question: string,
): Promise<CompareResponse> {
  const id = tenantId.trim()

  if (!id) {
    throw new PlaygroundApiError('Tenant is not selected.', 0)
  }

  const response = await fetch(`${getApiBaseUrl()}/tenants/${id}/agent/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  return parseJson<CompareResponse>(response)
}
