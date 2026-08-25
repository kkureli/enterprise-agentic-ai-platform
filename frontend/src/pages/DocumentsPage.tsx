import { useEffect, useState } from 'react'

import { inspectDocument, listDocuments } from '../api/playground'
import type { DocumentInspect, DocumentSummary } from '../types/playground'

type DocumentsPageProps = {
  tenantId: string
}

export function DocumentsPage({ tenantId }: DocumentsPageProps) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [selected, setSelected] = useState<DocumentInspect | null>(null)
  const [loading, setLoading] = useState(true)
  const [inspecting, setInspecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      setSelected(null)

      try {
        const items = await listDocuments(tenantId)
        if (!cancelled) {
          setDocuments(items)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load documents.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [tenantId])

  async function handleInspect(documentId: string) {
    setInspecting(true)
    setError(null)

    try {
      const detail = await inspectDocument(tenantId, documentId)
      setSelected(detail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to inspect document.')
    } finally {
      setInspecting(false)
    }
  }

  if (loading) {
    return <p className="page-note">Loading documents…</p>
  }

  return (
    <div className="documents-page">
      <header className="page-header">
        <h2 className="page-header__title">Documents</h2>
        <p className="page-header__subtitle">
          Pre-seeded tenant knowledge only. Indexed content is shown from Qdrant chunks — no
          public uploads.
        </p>
      </header>

      {error ? <p className="page-error">{error}</p> : null}

      <div className="document-grid">
        {documents.map((document) => (
          <article key={document.id} className="document-card">
            <h3 className="document-card__title">{document.filename}</h3>
            <p className="document-card__meta">
              Status: <strong>{document.status}</strong>
            </p>
            <p className="document-card__meta">
              Updated: {new Date(document.updated_at).toLocaleString()}
            </p>
            <button
              type="button"
              className="button button--secondary"
              disabled={inspecting}
              onClick={() => handleInspect(document.id)}
            >
              Inspect
            </button>
          </article>
        ))}
      </div>

      {documents.length === 0 ? (
        <p className="page-note">No documents indexed for this tenant yet.</p>
      ) : null}

      {selected ? (
        <section className="document-inspect">
          <h3 className="document-inspect__title">{selected.document.filename}</h3>
          <p className="document-inspect__note">{selected.note}</p>
          <dl className="document-inspect__meta">
            <dt>Status</dt>
            <dd>{selected.document.status}</dd>
            <dt>Chunks</dt>
            <dd>{selected.chunks.length}</dd>
            <dt>Document ID</dt>
            <dd className="details-panel__mono">{selected.document.id}</dd>
          </dl>

          <div className="chunk-list">
            {selected.chunks.map((chunk) => (
              <article key={chunk.chunk_index} className="chunk-card">
                <h4 className="chunk-card__title">Chunk {chunk.chunk_index}</h4>
                <pre className="chunk-card__text">{chunk.text}</pre>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
