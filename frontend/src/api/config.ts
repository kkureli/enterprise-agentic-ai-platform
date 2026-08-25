const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

const configuredTenantId = import.meta.env.VITE_TENANT_ID?.trim() ?? ''

const TENANT_STORAGE_KEY = 'enterprise-agentic-ai.tenant-id'
const TENANT_NAME_KEY = 'enterprise-agentic-ai.tenant-name'

export function getApiBaseUrl(): string {
  return apiBaseUrl.replace(/\/$/, '')
}

export function getTenantId(): string {
  if (configuredTenantId) {
    return configuredTenantId
  }

  return sessionStorage.getItem(TENANT_STORAGE_KEY)?.trim() ?? ''
}

export function setTenantId(tenantId: string): void {
  sessionStorage.setItem(TENANT_STORAGE_KEY, tenantId.trim())
}

export function getStoredTenantName(): string {
  return sessionStorage.getItem(TENANT_NAME_KEY)?.trim() ?? ''
}

export function setStoredTenantName(name: string): void {
  sessionStorage.setItem(TENANT_NAME_KEY, name.trim())
}

export function isTenantConfigured(): boolean {
  return getTenantId().length > 0
}
