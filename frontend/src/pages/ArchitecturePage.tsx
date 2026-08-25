import { RagPipelineExplorer } from '../components/RagPipelineExplorer'
import type { PlaygroundPage } from '../types/playground'

const FLOW = [
  { name: 'Frontend', value: 'Azure Static Web Apps' },
  { name: 'Backend', value: 'Azure Container Apps' },
  { name: 'Agent orchestration', value: 'LangGraph' },
]

const DEPENDENCIES = [
  { name: 'Neon', value: 'PostgreSQL' },
  { name: 'Qdrant', value: 'Vector store' },
  { name: 'Redis', value: 'Cache & rate limits' },
  { name: 'Azure OpenAI', value: 'LLM + embeddings' },
  { name: 'MCP', value: 'Live tools' },
  { name: 'Langfuse', value: 'Observability' },
]

type ArchitecturePageProps = {
  onNavigate: (page: PlaygroundPage) => void
}

export function ArchitecturePage({ onNavigate }: ArchitecturePageProps) {
  return (
    <div className="architecture-page">
      <header className="page-header">
        <h2 className="page-header__title">Architecture</h2>
        <p className="page-header__subtitle">
          System topology plus an inspectable map of the real multi-tenant RAG pipeline.
        </p>
      </header>

      <section className="arch-system" aria-labelledby="system-architecture-heading">
        <h3 id="system-architecture-heading" className="eval-section__title">
          System Architecture
        </h3>

        <div className="arch-flow">
          {FLOW.map((layer, index) => (
            <div key={layer.name} className="arch-flow__item">
              <div className="arch-card">
                <h4 className="arch-card__title">{layer.name}</h4>
                <p className="arch-card__value">{layer.value}</p>
              </div>
              {index < FLOW.length - 1 ? (
                <div className="arch-flow__arrow" aria-hidden="true">
                  ↓
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <h4 className="eval-section__title arch-deps-title">Dependencies</h4>
        <div className="arch-deps">
          {DEPENDENCIES.map((item) => (
            <article key={item.name} className="arch-card">
              <h4 className="arch-card__title">{item.name}</h4>
              <p className="arch-card__value">{item.value}</p>
            </article>
          ))}
        </div>

        <p className="page-note">
          Redis is used only for short-lived RAG caching and tenant agent rate limiting. LangGraph
          checkpoints and application data stay in PostgreSQL. Vectors stay in Qdrant with
          tenant_id payload filters.
        </p>

        <p className="page-note">
          The in-app Execution Trace panel shows a safe, curated per-request summary (route, graph
          path, retrieval, SQL, tools, tokens, estimated cost). Langfuse remains the deep
          production observability system and is not called from the public frontend.
        </p>
      </section>

      <hr className="arch-divider" />

      <RagPipelineExplorer onNavigate={onNavigate} />
    </div>
  )
}
