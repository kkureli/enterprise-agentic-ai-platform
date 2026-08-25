import { useEffect, useId, useRef, useState } from 'react'

import {
  ADVANCED_PATH_IDS,
  E100_TENANT_MEANINGS,
  INGESTION_STEPS,
  RAG_PIPELINE_NODES,
  STANDARD_PATH_IDS,
  modeBadgeLabel,
  type PipelineModeBadge,
  type RagPipelineNode,
} from '../lib/ragArchitecture'
import type { PlaygroundPage } from '../types/playground'

type RagPipelineExplorerProps = {
  onNavigate: (page: PlaygroundPage) => void
}

function ModeBadge({ mode }: { mode: PipelineModeBadge }) {
  return (
    <span className={`rag-mode-badge rag-mode-badge--${mode}`}>
      {modeBadgeLabel(mode)}
    </span>
  )
}

function FlowArrow() {
  return (
    <div className="rag-flow__arrow" aria-hidden="true">
      ↓
    </div>
  )
}

function Inspector({ node }: { node: RagPipelineNode }) {
  return (
    <aside className="rag-inspector" aria-live="polite">
      <div className="rag-inspector__header">
        <h4 className="rag-inspector__title">{node.name}</h4>
        <ModeBadge mode={node.usedIn} />
      </div>
      <dl className="rag-inspector__dl">
        <dt>Purpose</dt>
        <dd>{node.purpose}</dd>
        <dt>Implementation</dt>
        <dd>{node.implementation}</dd>
        <dt>Input</dt>
        <dd>{node.input}</dd>
        <dt>Output</dt>
        <dd>{node.output}</dd>
        <dt>Used in</dt>
        <dd>{modeBadgeLabel(node.usedIn)}</dd>
        <dt>Tenant isolation</dt>
        <dd>{node.tenantIsolation}</dd>
        <dt>Performance tradeoff</dt>
        <dd>{node.performance}</dd>
        {node.tech ? (
          <>
            <dt>Stack</dt>
            <dd>{node.tech}</dd>
          </>
        ) : null}
      </dl>
    </aside>
  )
}

export function RagPipelineExplorer({ onNavigate }: RagPipelineExplorerProps) {
  const [selectedId, setSelectedId] = useState(RAG_PIPELINE_NODES[0]?.id ?? '')
  const headingId = useId()
  const inspectorRef = useRef<HTMLDivElement>(null)
  const userSelectedRef = useRef(false)
  const selected =
    RAG_PIPELINE_NODES.find((node) => node.id === selectedId) ?? RAG_PIPELINE_NODES[0]

  const mainFlow = RAG_PIPELINE_NODES.filter((node) => node.usedIn !== 'side')
  const cacheNode = RAG_PIPELINE_NODES.find((node) => node.id === 'rag-cache')

  function selectNode(id: string) {
    userSelectedRef.current = true
    setSelectedId(id)
  }

  useEffect(() => {
    if (!userSelectedRef.current || !inspectorRef.current) {
      return
    }
    inspectorRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedId])

  return (
    <section className="rag-explorer" aria-labelledby={headingId}>
      <header className="page-header">
        <h3 id={headingId} className="page-header__title">
          RAG Pipeline Explorer
        </h3>
        <p className="page-header__subtitle">
          Inspectable map of the live knowledge path: hybrid dense + sparse retrieval, optional
          multi-query expansion, cross-encoder reranking, and grounded answer generation.
        </p>
      </header>

      <div className="rag-timing-split">
        <article className="rag-timing-card">
          <p className="rag-timing-card__eyebrow">Ingestion time</p>
          <p className="rag-timing-card__body">
            Document → chunks → dense + sparse representations → Qdrant upsert
          </p>
        </article>
        <article className="rag-timing-card rag-timing-card--query">
          <p className="rag-timing-card__eyebrow">Query time</p>
          <p className="rag-timing-card__body">
            Question → retrieval → reranking → context → grounded LLM answer
          </p>
        </article>
      </div>

      <div className="rag-path-summary">
        <article className="rag-path-card">
          <div className="rag-path-card__header">
            <h4>Standard path</h4>
            <ModeBadge mode="standard" />
          </div>
          <p className="rag-path-card__line">
            Query → Dense + Sparse → Hybrid Fusion → Reranking → Context → LLM
          </p>
          <p className="page-note">
            Single-query hybrid retrieval with cross-encoder reranking. Optimized for lower
            latency and compute.
          </p>
          <ol className="rag-path-card__steps">
            {STANDARD_PATH_IDS.filter((id) => id !== 'rag-cache').map((id) => {
              const node = RAG_PIPELINE_NODES.find((item) => item.id === id)
              return node ? <li key={id}>{node.shortLabel}</li> : null
            })}
          </ol>
        </article>

        <article className="rag-path-card rag-path-card--advanced">
          <div className="rag-path-card__header">
            <h4>Advanced path</h4>
            <ModeBadge mode="advanced" />
          </div>
          <p className="rag-path-card__line">
            Query → Query Rewrite / Multi-Query → Dense + Sparse → Fusion → Reranking → Context →
            LLM
          </p>
          <p className="page-note">
            Adds query rewriting and multi-query hybrid fusion before the same reranking stage.
            Broader coverage; usually higher latency — not guaranteed better answers.
          </p>
          <ol className="rag-path-card__steps">
            {ADVANCED_PATH_IDS.filter((id) => id !== 'rag-cache').map((id) => {
              const node = RAG_PIPELINE_NODES.find((item) => item.id === id)
              return node ? <li key={id}>{node.shortLabel}</li> : null
            })}
          </ol>
        </article>
      </div>

      <div className="rag-explorer__layout">
        <div className="rag-flow" role="list" aria-label="RAG pipeline stages">
          {mainFlow.map((node, index) => {
            const next = mainFlow[index + 1]
            const isDensePair =
              node.id === 'dense-retrieval' && next?.id === 'sparse-retrieval'
            const skipArrowAfterSparse = node.id === 'sparse-retrieval'

            return (
              <div key={node.id} className="rag-flow__item" role="listitem">
                <button
                  type="button"
                  className={
                    selected?.id === node.id
                      ? 'rag-node rag-node--selected'
                      : 'rag-node'
                  }
                  aria-pressed={selected?.id === node.id}
                  onClick={() => selectNode(node.id)}
                >
                  <span className="rag-node__name">{node.name}</span>
                  <span className="rag-node__meta">
                    <ModeBadge mode={node.usedIn} />
                    {node.tech ? <span className="rag-node__tech">{node.tech}</span> : null}
                  </span>
                </button>

                {node.id === 'agent-router' && cacheNode ? (
                  <div className="rag-cache-branch">
                    <div className="rag-cache-branch__label">Side path after RAG entry</div>
                    <button
                      type="button"
                      className={
                        selected?.id === cacheNode.id
                          ? 'rag-node rag-node--side rag-node--selected'
                          : 'rag-node rag-node--side'
                      }
                      aria-pressed={selected?.id === cacheNode.id}
                      onClick={() => selectNode(cacheNode.id)}
                    >
                      <span className="rag-node__name">{cacheNode.name}</span>
                      <span className="rag-node__meta">
                        <ModeBadge mode="side" />
                        <span className="rag-node__tech">Redis / Upstash</span>
                      </span>
                      <span className="rag-cache-branch__fork">
                        HIT → cached RagResult · MISS → retrieval pipeline
                      </span>
                    </button>
                  </div>
                ) : null}

                {isDensePair ? (
                  <div className="rag-parallel" aria-hidden="true">
                    <span className="rag-parallel__plus">+</span>
                    <span className="rag-parallel__hint">parallel</span>
                  </div>
                ) : null}

                {!isDensePair && !skipArrowAfterSparse && index < mainFlow.length - 1 ? (
                  <FlowArrow />
                ) : null}

                {node.id === 'sparse-retrieval' && index < mainFlow.length - 1 ? (
                  <FlowArrow />
                ) : null}
              </div>
            )
          })}
        </div>

        <div className="rag-inspector-col" ref={inspectorRef}>
          {selected ? <Inspector node={selected} /> : null}
        </div>
      </div>

      <section className="rag-isolation" aria-labelledby="tenant-isolation-heading">
        <h4 id="tenant-isolation-heading" className="eval-section__title">
          Tenant isolation at retrieval
        </h4>
        <p className="page-note">
          Every Qdrant retrieval is constrained by a <code className="trace-mono">tenant_id</code>{' '}
          payload filter. Answers come from live tenant-scoped retrieval — not frontend
          hardcoding.
        </p>

        <div className="rag-isolation__flow">
          <article className="arch-card">
            <h5 className="arch-card__title">Tenant</h5>
            <p className="arch-card__value">Atlas Manufacturing</p>
          </article>
          <div className="rag-flow__arrow" aria-hidden="true">
            ↓
          </div>
          <article className="arch-card">
            <h5 className="arch-card__title">Qdrant filter</h5>
            <p className="arch-card__value trace-mono">tenant_id = &lt;Atlas UUID&gt;</p>
          </article>
          <div className="rag-flow__arrow" aria-hidden="true">
            ↓
          </div>
          <article className="arch-card">
            <h5 className="arch-card__title">Result set</h5>
            <p className="arch-card__value">Only Atlas chunks</p>
          </article>
        </div>

        <div className="rag-e100">
          <p className="rag-e100__title">
            Same code <code className="trace-mono">E-100</code> · different tenant-grounded meaning
          </p>
          <div className="rag-e100__grid">
            {E100_TENANT_MEANINGS.map((item) => (
              <article key={item.tenant} className="rag-e100__card">
                <h5>{item.tenant}</h5>
                <p>{item.meaning}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="rag-ingestion" aria-labelledby="ingestion-heading">
        <h4 id="ingestion-heading" className="eval-section__title">
          Document ingestion
        </h4>
        <p className="page-note">
          Document metadata lives in PostgreSQL. Chunk vectors live in Qdrant with a{' '}
          <code className="trace-mono">tenant_id</code> payload. After successful ingestion, the
          tenant RAG knowledge version is incremented so Redis-cached answers for prior knowledge
          are logically invalidated.
        </p>
        <div className="rag-ingestion__flow">
          {INGESTION_STEPS.map((step, index) => (
            <div key={step.name} className="rag-ingestion__item">
              <article className="arch-card">
                <h5 className="arch-card__title">{step.name}</h5>
                <p className="arch-card__value">{step.detail}</p>
              </article>
              {index < INGESTION_STEPS.length - 1 ? (
                <div className="rag-flow__arrow" aria-hidden="true">
                  ↓
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <section className="rag-trace-link">
        <div>
          <h4 className="eval-section__title">Architecture vs Execution Trace</h4>
          <p className="page-note">
            Architecture is the static system design. Execution Trace shows the actual
            request-specific path, chunks, latency, tokens, tools, and estimated cost for a live
            run.
          </p>
        </div>
        <div className="rag-trace-link__actions">
          <button
            type="button"
            className="button button--primary"
            onClick={() => onNavigate('playground')}
          >
            See this pipeline in a live request
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => onNavigate('compare')}
          >
            Compare Standard vs Advanced
          </button>
        </div>
      </section>
    </section>
  )
}
