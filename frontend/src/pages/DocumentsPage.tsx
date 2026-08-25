import { useState } from 'react'

import { inspectDocument, listDocuments } from '../api/playground'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState'
import { StatusBadge } from '../components/StatusBadge'
import { useCachedResource } from '../hooks/useCachedResource'
import {
  TTL,
  cacheKeyDocumentInspect,
  cacheKeyDocuments,
  cachedFetch,
} from '../lib/requestCache'
import type { DocumentInspect } from '../types/playground'

type DocumentsPageProps = {
  tenantId: string
}

export function DocumentsPage({ tenantId }: DocumentsPageProps) {
  const {
    data: documents,
    error,
    status,
    isRefreshing,
    reload,
  } = useCachedResource({
    key: cacheKeyDocuments(tenantId),
    ttlMs: TTL.documents,
    fetcher: () => listDocuments(tenantId),
  })

  const [selected, setSelected] = useState<DocumentInspect | null>(null)
  const [inspectingId, setInspectingId] = useState<string | null>(null)
  const [inspectError, setInspectError] = useState<string | null>(null)

  async function handleInspect(documentId: string) {
    setInspectingId(documentId)
    setInspectError(null)

    try {
      const detail = await cachedFetch(
        cacheKeyDocumentInspect(tenantId, documentId),
        () => inspectDocument(tenantId, documentId),
        { ttlMs: TTL.documentInspect },
      )
      setSelected(detail)
    } catch (err) {
      setInspectError(err instanceof Error ? err.message : 'Failed to inspect document.')
    } finally {
      setInspectingId(null)
    }
  }

  return (
    <div className="documents-page">
      <header className="page-header">
        <h2 className="page-header__title">Documents</h2>
        <p className="page-header__subtitle">
          Pre-seeded tenant knowledge only. Indexed content is shown from Qdrant chunks — no
          public uploads.
          {isRefreshing ? ' · Refreshing…' : null}
        </p>
      </header>

      {status === 'loading' ? (
        <LoadingBlock title="Loading documents…" compact />
      ) : null}

      {status === 'error' ? (
        <ErrorBlock
          title="Unable to load documents."
          message={error}
          onRetry={() => void reload(true)}
        />
      ) : null}

      {status === 'success' && (documents?.length ?? 0) === 0 ? (
        <EmptyBlock title="No documents indexed for this tenant yet." />
      ) : null}

      {status === 'success' && documents && documents.length > 0 ? (
        <div className="document-grid">
          {documents.map((document) => {
            const chunkCount =
              selected?.document.id === document.id ? selected.chunks.length : null

            return (
              <article key={document.id} className="document-card">
                <h3 className="document-card__title">{document.filename}</h3>
                <div className="document-card__meta-row">
                  <StatusBadge status={document.status} />
                  <span className="document-card__meta">
                    {chunkCount != null
                      ? `${chunkCount} indexed chunk${chunkCount === 1 ? '' : 's'}`
                      : 'Chunks on inspect'}
                  </span>
                </div>
                <p className="document-card__meta">
                  Updated {new Date(document.updated_at).toLocaleString()}
                </p>
                <button
                  type="button"
                  className="button button--secondary button--small"
                  disabled={inspectingId != null}
                  aria-label={`Inspect ${document.filename}`}
                  onClick={() => void handleInspect(document.id)}
                >
                  {inspectingId === document.id ? 'Inspecting…' : 'Inspect'}
                </button>
              </article>
            )
          })}
        </div>
      ) : null}

      {inspectError ? <p className="page-error">{inspectError}</p> : null}

      {selected ? (
        <section className="document-inspect">
          <h3 className="document-inspect__title">{selected.document.filename}</h3>
          <p className="document-inspect__note">{selected.note}</p>
          <dl className="document-inspect__meta">
            <dt>Status</dt>
            <dd>
              <StatusBadge status={selected.document.status} />
            </dd>
            <dt>Indexed chunks</dt>
            <dd>{selected.chunks.length}</dd>
            <dt>Updated</dt>
            <dd>{new Date(selected.document.updated_at).toLocaleString()}</dd>
            <dt>Document ID</dt>
            <dd className="details-panel__mono">{selected.document.id}</dd>
          </dl>

          <div className="chunk-list">
            {selected.chunks.map((chunk) => (
              <article key={chunk.chunk_index} className="chunk-card">
                <h4 className="chunk-card__title">
                  {chunk.filename || selected.document.filename}
                  <span className="chunk-card__index trace-mono">
                    chunk {chunk.chunk_index}
                  </span>
                </h4>
                <pre className="chunk-card__text">{chunk.text}</pre>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
