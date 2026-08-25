import { useEffect, useId, useRef, useState } from 'react'

import {
  ORCHESTRATION_NODES,
  type OrchestrationNode,
} from '../lib/orchestrationArchitecture'

function Inspector({ node }: { node: OrchestrationNode }) {
  return (
    <aside className="rag-inspector" aria-live="polite">
      <div className="rag-inspector__header">
        <h4 className="rag-inspector__title">{node.name}</h4>
        <span className="rag-mode-badge rag-mode-badge--both">Orchestration</span>
      </div>
      <dl className="rag-inspector__dl">
        <dt>Purpose</dt>
        <dd>{node.purpose}</dd>
        <dt>Input</dt>
        <dd>{node.input}</dd>
        <dt>Output</dt>
        <dd>{node.output}</dd>
        <dt>When used</dt>
        <dd>{node.whenUsed}</dd>
        <dt>Performance tradeoff</dt>
        <dd>{node.performance}</dd>
        <dt>Tenant isolation impact</dt>
        <dd>{node.tenantIsolation}</dd>
        <dt>Safety impact</dt>
        <dd>{node.safety}</dd>
      </dl>
    </aside>
  )
}

export function OrchestrationExplorer() {
  const [selectedId, setSelectedId] = useState(ORCHESTRATION_NODES[0]?.id ?? '')
  const headingId = useId()
  const inspectorRef = useRef<HTMLDivElement>(null)
  const userSelectedRef = useRef(false)
  const selected =
    ORCHESTRATION_NODES.find((node) => node.id === selectedId) ?? ORCHESTRATION_NODES[0]

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
    <section className="orch-explorer" aria-labelledby={headingId}>
      <header className="page-header">
        <h3 id={headingId} className="page-header__title">
          Multi-Capability Orchestration
        </h3>
        <p className="page-header__subtitle">
          Bounded selective orchestration: the planner chooses only required capabilities.
          Independent reads can fan out in parallel; synthesis joins grounded evidence; writes
          stay HITL-gated.
        </p>
      </header>

      <div className="orch-path-grid">
        <article className="orch-path-card">
          <h4 className="orch-path-card__title">Single capability</h4>
          <ol className="orch-path-card__steps">
            <li>User Question</li>
            <li>Planner</li>
            <li>Selected capability (RAG · SQL · or MCP)</li>
            <li>Finalize</li>
          </ol>
          <p className="page-note">Fast path — synthesis is skipped when only one capability runs.</p>
        </article>
        <article className="orch-path-card">
          <h4 className="orch-path-card__title">Composite</h4>
          <ol className="orch-path-card__steps">
            <li>User Question</li>
            <li>Planner → selected capabilities</li>
            <li>Parallel read fan-out (RAG · SQL · MCP Read)</li>
            <li>Grounded Synthesis</li>
            <li>Optional Write Gate / HITL</li>
            <li>Finalize</li>
          </ol>
          <p className="page-note">
            Not every capability runs for every query. This is structured fan-out / join, not an
            unrestricted autonomous agent loop.
          </p>
        </article>
      </div>

      <div className="rag-explorer__layout">
        <div className="rag-flow" role="list" aria-label="Orchestration stages">
          {ORCHESTRATION_NODES.map((node, index) => (
            <div key={node.id} className="rag-flow__item" role="listitem">
              <button
                type="button"
                className={
                  selectedId === node.id ? 'rag-node rag-node--selected' : 'rag-node'
                }
                onClick={() => selectNode(node.id)}
                aria-pressed={selectedId === node.id}
              >
                <span className="rag-node__name">{node.name}</span>
                <span className="rag-node__meta">
                  <span className="rag-mode-badge rag-mode-badge--both">Orchestration</span>
                </span>
              </button>
              {index < ORCHESTRATION_NODES.length - 1 ? (
                <div className="rag-flow__arrow" aria-hidden="true">
                  ↓
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <div className="rag-inspector-col" ref={inspectorRef}>
          {selected ? <Inspector node={selected} /> : null}
        </div>
      </div>
    </section>
  )
}
