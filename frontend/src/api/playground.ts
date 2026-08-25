import { getApiBaseUrl } from './config'
import type {
  Asset,
  DemoTenant,
  DocumentInspect,
  DocumentSummary,
  MaintenanceRecord,
  MaintenanceTicket,
} from '../types/playground'

export class PlaygroundApiError extends Error {
  status: number
  retryAfter?: number

  constructor(message: string, status: number, retryAfter?: number) {
    super(message)
    this.name = 'PlaygroundApiError'
    this.status = status
    this.retryAfter = retryAfter
  }
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
    throw new PlaygroundApiError(
      detail,
      response.status,
      Number.isFinite(retryAfter) ? retryAfter : undefined,
    )
  }

  return payload as T
}

export async function listDemoTenants(): Promise<DemoTenant[]> {
  const response = await fetch(`${getApiBaseUrl()}/demo/tenants`)
  return parseJson<DemoTenant[]>(response)
}

export async function listDocuments(tenantId: string): Promise<DocumentSummary[]> {
  const response = await fetch(`${getApiBaseUrl()}/tenants/${tenantId}/documents`)
  return parseJson<DocumentSummary[]>(response)
}

export async function inspectDocument(
  tenantId: string,
  documentId: string,
): Promise<DocumentInspect> {
  let response: Response

  try {
    response = await fetch(`${getApiBaseUrl()}/tenants/${tenantId}/documents/${documentId}`)
  } catch {
    throw new PlaygroundApiError(
      'Unable to reach the server while loading document chunks.',
      0,
    )
  }

  return parseJson<DocumentInspect>(response)
}

export async function listAssets(tenantId: string): Promise<Asset[]> {
  const response = await fetch(`${getApiBaseUrl()}/tenants/${tenantId}/assets`)
  return parseJson<Asset[]>(response)
}

export async function listMaintenanceRecords(
  tenantId: string,
): Promise<MaintenanceRecord[]> {
  const response = await fetch(`${getApiBaseUrl()}/tenants/${tenantId}/maintenance-records`)
  return parseJson<MaintenanceRecord[]>(response)
}

export async function listMaintenanceTickets(
  tenantId: string,
): Promise<MaintenanceTicket[]> {
  const response = await fetch(`${getApiBaseUrl()}/tenants/${tenantId}/maintenance-tickets`)
  return parseJson<MaintenanceTicket[]>(response)
}
