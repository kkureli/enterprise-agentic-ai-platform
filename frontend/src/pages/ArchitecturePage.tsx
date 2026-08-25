const LAYERS = [
  { name: 'Frontend', value: 'Azure Static Web Apps' },
  { name: 'Backend', value: 'Azure Container Apps' },
  { name: 'Agent orchestration', value: 'LangGraph' },
  { name: 'Knowledge retrieval', value: 'Qdrant Cloud' },
  { name: 'Structured operational data', value: 'Neon PostgreSQL' },
  { name: 'Short-lived cache / rate limiting', value: 'Upstash Redis' },
  { name: 'LLM + embeddings', value: 'Azure OpenAI / Foundry' },
  { name: 'Observability', value: 'Langfuse' },
  { name: 'Tools', value: 'MCP' },
]

export function ArchitecturePage() {
  return (
    <div className="architecture-page">
      <header className="page-header">
        <h2 className="page-header__title">Architecture</h2>
        <p className="page-header__subtitle">
          Portfolio topology for the Enterprise Agentic AI Platform demo.
        </p>
      </header>

      <div className="arch-flow">
        {LAYERS.map((layer, index) => (
          <div key={layer.name} className="arch-flow__item">
            <div className="arch-card">
              <h3 className="arch-card__title">{layer.name}</h3>
              <p className="arch-card__value">{layer.value}</p>
            </div>
            {index < LAYERS.length - 1 ? <div className="arch-flow__arrow" aria-hidden="true">↓</div> : null}
          </div>
        ))}
      </div>

      <p className="page-note">
        Redis is used only for short-lived RAG caching and tenant agent rate limiting. LangGraph
        checkpoints and application data stay in PostgreSQL. Vectors stay in Qdrant with
        tenant_id payload filters.
      </p>

      <p className="page-note">
        The in-app Execution Trace panel shows a safe, curated per-request summary (route, graph
        path, retrieval, SQL, tools, tokens, estimated cost). Langfuse remains the deep production
        observability system and is not called from the public frontend.
      </p>
    </div>
  )
}
