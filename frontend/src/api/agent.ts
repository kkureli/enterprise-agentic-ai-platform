import { getApiBaseUrl, getTenantId } from './config'
import type { AgentResponse, RetrievalMode } from '../types/agent'

export class AgentApiError extends Error {
  status: number
  retryAfter?: number

  constructor(message: string, status: number, retryAfter?: number) {
    super(message)
    this.name = 'AgentApiError'
    this.status = status
    this.retryAfter = retryAfter
  }
}

function tenantPath(): string {
  const tenantId = getTenantId()

  if (!tenantId) {
    throw new AgentApiError(
      'Tenant ID is not configured. Set VITE_TENANT_ID or enter a tenant ID in settings.',
      0,
    )
  }

  return `${getApiBaseUrl()}/tenants/${tenantId}/agent`
}

async function parseAgentResponse(response: Response): Promise<AgentResponse> {
  let payload: unknown

  try {
    payload = await response.json()
  } catch {
    throw new AgentApiError('Received an invalid response from the server.', response.status)
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

    throw new AgentApiError(
      mapHttpError(detail, response.status, retryAfter),
      response.status,
      Number.isFinite(retryAfter) ? retryAfter : undefined,
    )
  }

  if (
    typeof payload !== 'object' ||
    payload === null ||
    !('thread_id' in payload) ||
    !('status' in payload) ||
    !('route' in payload) ||
    !('answer' in payload)
  ) {
    throw new AgentApiError('Received a malformed agent response.', response.status)
  }

  return payload as AgentResponse
}

function mapHttpError(detail: string, status: number, retryAfter?: number): string {
  if (status === 404) {
    return 'Tenant not found. Verify your tenant ID.'
  }

  if (status === 409) {
    return 'This approval request is no longer pending.'
  }

  if (status === 429) {
    if (retryAfter && Number.isFinite(retryAfter)) {
      return `Demo request limit reached. Try again in ${retryAfter} seconds.`
    }
    return detail || 'Rate limit exceeded. Try again shortly.'
  }

  if (status === 503) {
    return detail || 'Agent execution failed. Please try again.'
  }

  if (status === 422) {
    return detail || 'Invalid request.'
  }

  if (status === 400) {
    return detail || 'Invalid request.'
  }

  return detail
}

export async function runAgent(
  question: string,
  retrievalMode: RetrievalMode,
): Promise<AgentResponse> {
  let response: Response

  try {
    response = await fetch(tenantPath(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        retrieval_mode: retrievalMode,
      }),
    })
  } catch {
    throw new AgentApiError(
      'Unable to reach the server. Check that the backend is running.',
      0,
    )
  }

  return parseAgentResponse(response)
}

export async function approveAgentAction(
  threadId: string,
  approved: boolean,
): Promise<AgentResponse> {
  let response: Response

  try {
    response = await fetch(`${tenantPath()}/${threadId}/approval`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ approved }),
    })
  } catch {
    throw new AgentApiError(
      'Unable to reach the server. Check that the backend is running.',
      0,
    )
  }

  return parseAgentResponse(response)
}

export function rejectAgentAction(threadId: string): Promise<AgentResponse> {
  return approveAgentAction(threadId, false)
}
