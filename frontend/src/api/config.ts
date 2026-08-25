const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

/** Optional local/dev fallback only — never overrides a selected demo tenant. */
const configuredTenantId = import.meta.env.VITE_TENANT_ID?.trim() ?? ''

const TENANT_STORAGE_KEY = 'enterprise-agentic-ai.tenant-id'
const TENANT_NAME_KEY = 'enterprise-agentic-ai.tenant-name'

export function getApiBaseUrl(): string {
  return apiBaseUrl.replace(/\/$/, '')
}

/**
 * Active playground tenant ID.
 * Priority: session selection (set from demo tenant selector) → optional VITE_TENANT_ID fallback.
 * VITE_TENANT_ID must never override a selected demo tenant.
 */
export function getTenantId(): string {
  const selected = sessionStorage.getItem(TENANT_STORAGE_KEY)?.trim() ?? ''
  if (selected) {
    return selected
  }

  return configuredTenantId
}

export function setTenantId(tenantId: string): void {
  sessionStorage.setItem(TENANT_STORAGE_KEY, tenantId.trim())
}

export function clearTenantId(): void {
  sessionStorage.removeItem(TENANT_STORAGE_KEY)
}

export function getStoredTenantName(): string {
  return sessionStorage.getItem(TENANT_NAME_KEY)?.trim() ?? ''
}

export function setStoredTenantName(name: string): void {
  sessionStorage.setItem(TENANT_NAME_KEY, name.trim())
}

export function clearStoredTenantName(): void {
  sessionStorage.removeItem(TENANT_NAME_KEY)
}

export function isTenantConfigured(): boolean {
  return getTenantId().length > 0
}
