type CacheEntry<T> = {
  value: T
  expiresAt: number
}

const store = new Map<string, CacheEntry<unknown>>()
const inflight = new Map<string, Promise<unknown>>()

export const TTL = {
  /** Demo tenant catalog — effectively session-long. */
  tenants: 30 * 60_000,
  /** Packaged evaluation JSON — session-long. */
  evaluations: 30 * 60_000,
  /** Readiness probes — short. */
  status: 20_000,
  /** Tenant document list. */
  documents: 60_000,
  /** Document chunk inspection. */
  documentInspect: 5 * 60_000,
  /** Assets / maintenance / tickets. */
  operations: 30_000,
} as const

function now(): number {
  return Date.now()
}

export function peekCache<T>(key: string): T | undefined {
  const entry = store.get(key) as CacheEntry<T> | undefined
  if (!entry) {
    return undefined
  }
  if (entry.expiresAt <= now()) {
    return undefined
  }
  return entry.value
}

/** Return cached value even if stale (for SWR). */
export function peekCacheStale<T>(key: string): T | undefined {
  const entry = store.get(key) as CacheEntry<T> | undefined
  return entry?.value
}

export function setCache<T>(key: string, value: T, ttlMs: number): void {
  store.set(key, {
    value,
    expiresAt: now() + Math.max(0, ttlMs),
  })
}

export function invalidateCache(key: string): void {
  store.delete(key)
  inflight.delete(key)
}

export function invalidateCachePrefix(prefix: string): void {
  for (const key of store.keys()) {
    if (key.startsWith(prefix)) {
      store.delete(key)
    }
  }
  for (const key of inflight.keys()) {
    if (key.startsWith(prefix)) {
      inflight.delete(key)
    }
  }
}

export function invalidateTenantScopedCaches(tenantId: string): void {
  const id = tenantId.trim()
  if (!id) {
    return
  }
  invalidateCache(`documents:${id}`)
  invalidateCache(`operations:${id}`)
  invalidateCachePrefix(`document:${id}:`)
}

type CachedFetchOptions = {
  ttlMs: number
  /** When true, ignore TTL and always call the network (still updates cache). */
  force?: boolean
}

/**
 * In-memory GET cache with in-flight dedupe.
 * Safe for idempotent reads only — never use for POST /agent.
 */
export async function cachedFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: CachedFetchOptions,
): Promise<T> {
  if (!options.force) {
    const fresh = peekCache<T>(key)
    if (fresh !== undefined) {
      return fresh
    }

    const pending = inflight.get(key) as Promise<T> | undefined
    if (pending) {
      return pending
    }
  }

  const request = fetcher()
    .then((value) => {
      setCache(key, value, options.ttlMs)
      return value
    })
    .finally(() => {
      inflight.delete(key)
    })

  inflight.set(key, request)
  return request
}

export function cacheKeyDocuments(tenantId: string): string {
  return `documents:${tenantId}`
}

export function cacheKeyOperations(tenantId: string): string {
  return `operations:${tenantId}`
}

export function cacheKeyDocumentInspect(tenantId: string, documentId: string): string {
  return `document:${tenantId}:${documentId}`
}

export function devLogTiming(label: string, startedAt: number): void {
  if (!import.meta.env.DEV) {
    return
  }
  const ms = Math.round(performance.now() - startedAt)
  console.debug(`[perf] ${label}: ${ms}ms`)
}
