import { useCallback, useEffect, useRef, useState } from 'react'

import { cachedFetch, peekCache, peekCacheStale } from '../lib/requestCache'

type ResourceStatus = 'idle' | 'loading' | 'success' | 'error'

type UseCachedResourceOptions<T> = {
  key: string | null
  fetcher: () => Promise<T>
  ttlMs: number
  enabled?: boolean
  /** Soft-refresh when only stale cache exists. Default true. */
  revalidate?: boolean
}

type UseCachedResourceResult<T> = {
  data: T | null
  error: string | null
  status: ResourceStatus
  isRefreshing: boolean
  reload: (force?: boolean) => Promise<void>
}

/**
 * Stale-while-revalidate style resource loader.
 * Cached data renders immediately; background refresh does not flash a full loading state.
 */
export function useCachedResource<T>({
  key,
  fetcher,
  ttlMs,
  enabled = true,
  revalidate = true,
}: UseCachedResourceOptions<T>): UseCachedResourceResult<T> {
  const fetcherRef = useRef(fetcher)

  useEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  const initial = key ? peekCacheStale<T>(key) : undefined
  const [data, setData] = useState<T | null>(initial ?? null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<ResourceStatus>(() => {
    if (!enabled || !key) {
      return 'idle'
    }
    return initial !== undefined ? 'success' : 'loading'
  })
  const [isRefreshing, setIsRefreshing] = useState(false)
  const generationRef = useRef(0)

  const reload = useCallback(
    async (force = false) => {
      if (!key || !enabled) {
        return
      }

      const generation = ++generationRef.current
      const fresh = peekCache<T>(key)
      const stale = peekCacheStale<T>(key)
      const hasAny = stale !== undefined

      if (!force && fresh !== undefined) {
        setData(fresh)
        setStatus('success')
        setError(null)
        return
      }

      if (hasAny && !force) {
        setData(stale ?? null)
        setStatus('success')
        setIsRefreshing(true)
      } else {
        setStatus('loading')
        setError(null)
      }

      try {
        const value = await cachedFetch(key, () => fetcherRef.current(), {
          ttlMs,
          force: force || !hasAny,
        })

        if (generation !== generationRef.current) {
          return
        }

        setData(value)
        setStatus('success')
        setError(null)
      } catch (err) {
        if (generation !== generationRef.current) {
          return
        }

        if (!hasAny) {
          setData(null)
          setStatus('error')
        }
        setError(err instanceof Error ? err.message : 'Request failed.')
      } finally {
        if (generation === generationRef.current) {
          setIsRefreshing(false)
        }
      }
    },
    [enabled, key, ttlMs],
  )

  useEffect(() => {
    if (!enabled || !key) {
      return
    }

    const fresh = peekCache<T>(key)
    if (fresh !== undefined) {
      setData(fresh)
      setStatus('success')
      setError(null)
      return
    }

    const stale = peekCacheStale<T>(key)
    if (stale !== undefined) {
      setData(stale)
      setStatus('success')
      if (revalidate) {
        void reload(false)
      }
      return
    }

    void reload(true)
  }, [enabled, key, revalidate, reload])

  return {
    data,
    error,
    status,
    isRefreshing,
    reload,
  }
}

export type { ResourceStatus }
