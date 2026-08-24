# Enterprise Agentic AI Platform

A production-oriented, multi-tenant platform for building enterprise LLM, RAG, and agentic AI workflows.

The project is being developed incrementally with a focus on software engineering quality, tenant isolation, observability, evaluation, enterprise tool integration, and deployability.

## Current Status

**Sprint 0 — Repository & Architecture Foundation: completed**

**Sprint 1 — Enterprise Knowledge Ingestion & RAG v1: completed**

**Sprint 2 — Advanced Retrieval & Evaluation: completed**

**Sprint 3 — LangGraph Agent Orchestration: completed**

**Sprint 4 — MCP & Enterprise Tool Integration: completed**

**Sprint 5 — SQL Agent, Security & Human-in-the-Loop: completed**

**Sprint 6 — Evaluation, Langfuse & Production Observability: completed**

**Sprint 7 — React UI & Production UX: completed**

Implemented so far:

- FastAPI backend with tenant-scoped APIs
- Async SQLAlchemy 2 + PostgreSQL + Alembic
- Operational models: `assets`, `maintenance_records`, `maintenance_tickets`
- Redis and Qdrant infrastructure
- Document upload, parsing, chunking, and Azure OpenAI embeddings
- Dense + sparse hybrid retrieval with weighted RRF, reranking, multi-query RAG
- Retrieval evaluation (Recall@K, MRR, nDCG@K) with persisted results
- LangGraph routes: `knowledge` / `sql` / `tool` / `unsupported`
- NL → SQL pipeline with SQLGlot validation, tenant scoping, and read-only transactions
- Separate MCP server under `/mcp` (stdio); host intercepts write tools for HITL
- Real maintenance-ticket persistence after human approval (`interrupt` / `Command(resume=...)`)
- Agent approval API with `thread_id` checkpoints (`InMemorySaver` — development only)
- Langfuse tracing for LangGraph runs and nested LLM calls (latency, tokens, model, cost)
- 24-case agent golden dataset with router and end-to-end evaluation
- React + TypeScript chat frontend with HITL approval card and route indicators
- Health/readiness endpoints, Ruff, pytest (21 passing), and GitHub Actions CI

Current agent orchestration:

```text
START → LLM Router
          ├── knowledge → RAG Node → Finalize → END
          ├── sql → SQL Node → Finalize → END
          ├── tool → MCP Tool Node
          │            ├── read → Finalize → END
          │            └── write → Approval → Approved Action / Reject → Finalize → END
          └── unsupported → Fallback → END
```

Checkpoints use `InMemorySaver` for local development and must be replaced with
persistent storage before production. JWT/RBAC and cloud deployment remain planned.

More detail: [`docs/project-plan.md`](docs/project-plan.md) · [`docs/architecture.md`](docs/architecture.md)

## Architecture

```mermaid
flowchart TD
    Client[API Client / Swagger]

    Client --> FastAPI[FastAPI Application]

    FastAPI --> TenantAPI[Tenant API]
    FastAPI --> UserAPI[User API]
    FastAPI --> DocumentAPI[Document API]
    FastAPI --> RetrievalAPI[Retrieval API]
    FastAPI --> RagAPI[RAG API]
    FastAPI --> AgentAPI[Agent API]
    FastAPI --> HealthAPI[Health & Readiness API]

    TenantAPI --> Session[SQLAlchemy AsyncSession]
    UserAPI --> Session
    DocumentAPI --> Session

    Session --> Engine[SQLAlchemy Async Engine]
    Engine --> AsyncPG[asyncpg]
    AsyncPG --> PostgreSQL[(PostgreSQL)]

    DocumentAPI --> Storage[Local Document Storage]
    DocumentAPI --> Qdrant[(Qdrant)]
    RetrievalAPI --> Qdrant
    RagAPI --> Qdrant
    RagAPI --> Azure[Azure OpenAI]
    AgentAPI --> LangGraph[LangGraph Router]
    LangGraph --> RagAPI
    LangGraph --> SQLAgent[SQL Agent]
    SQLAgent --> PostgreSQL
    LangGraph --> MCPClient[MCP Client stdio]
    MCPClient --> MCPServer[MCP Server /mcp]
    LangGraph --> HITL[HITL Approval]
    HITL --> PostgreSQL
    LangGraph --> Azure
    AgentAPI --> Langfuse[Langfuse Tracing]
    LangGraph --> Langfuse

    HealthAPI --> PostgreSQL
    HealthAPI --> Redis[(Redis)]
    HealthAPI --> Qdrant

    Alembic[Alembic Migrations] --> PostgreSQL

    Pytest[pytest Integration Tests] --> FastAPI
    Ruff[Ruff Lint & Format] --> FastAPI

    GitHub[GitHub Actions CI]
    GitHub --> Ruff
    GitHub --> Pytest
```

## Multi-Tenant Model

```text
Tenant
 ├── Users
 ├── Documents / Vector Chunks
 └── Operational data
      ├── Assets
      ├── Maintenance Records
      └── Maintenance Tickets
```

Each user, document, and operational row belongs to one tenant through `tenant_id`.  
Retrieval/RAG apply tenant filters in Qdrant; SQL agent queries must filter by `:tenant_id`.

User email uniqueness is scoped per tenant:

```text
UNIQUE (tenant_id, email)
```

## Tech Stack

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2 Async
- asyncpg
- Alembic
- SQLGlot (SQL validation)

### Data & Infrastructure

- PostgreSQL
- Redis
- Qdrant
- Docker Compose
- Azure OpenAI (embeddings + chat)
- FastEmbed BM25 (sparse)
- CrossEncoder reranker
- LangGraph (router + HITL interrupt / resume)
- MCP (stdio tool server under `/mcp`)
- Langfuse (LangGraph + LLM tracing)

### Quality

- pytest
- pytest-asyncio
- HTTPX
- Ruff
- GitHub Actions
- Retrieval evaluation under `evals/`

## Repository Structure

```text
enterprise-agentic-ai-platform/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── scripts/
│   └── tests/
├── docs/
├── evals/
│   ├── agent/
│   ├── datasets/
│   ├── results/
│   └── retrieval/
├── frontend/
├── infra/
├── mcp/
├── .github/
│   └── workflows/
├── docker-compose.yml
└── README.md
```

## Local Development

### 1. Start infrastructure

From the repository root:

```bash
docker compose up -d
```

This starts:

- PostgreSQL on `5432`
- Redis on `6379`
- Qdrant on `6333` / `6334`

### 2. Install backend dependencies

```bash
cd backend && uv sync --dev
```

### 3. Configure environment

Create `backend/.env` from the example:

```bash
cp .env.example .env
```

The PostgreSQL URL must use the async SQLAlchemy driver:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_ai
```

Optional Langfuse tracing (agent runs and evaluations):

```text
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Start the API

```bash
uv run uvicorn app.main:app --reload
```

### 6. Start the frontend (Sprint 7)

From the repository root:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Configure `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_TENANT_ID=
```

If `VITE_TENANT_ID` is empty, enter a local tenant UUID in the UI after creating
one via `POST /api/v1/tenants`.

Useful URLs:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Chat UI: `http://localhost:5173`
- Health: `http://127.0.0.1:8000/health`
- Readiness: `http://127.0.0.1:8000/ready`
- Qdrant dashboard: `http://localhost:6333/dashboard`

## Current API

### Health

```text
GET /health
GET /ready
```

### Tenants

```text
POST /api/v1/tenants
GET  /api/v1/tenants/{tenant_id}
```

### Users

```text
POST /api/v1/tenants/{tenant_id}/users
GET  /api/v1/tenants/{tenant_id}/users
GET  /api/v1/users/{user_id}
```

### Documents

```text
POST /api/v1/tenants/{tenant_id}/documents
GET  /api/v1/tenants/{tenant_id}/documents/{document_id}
```

### Retrieval

```text
POST /api/v1/tenants/{tenant_id}/retrieval
```

### RAG

```text
POST /api/v1/tenants/{tenant_id}/rag
```

RAG accepts `retrieval_mode`:

- `"standard"` (default) — hybrid + reranker + final fusion
- `"advanced"` — multi-query hybrid + reranker + final fusion

### Agent

```text
POST /api/v1/tenants/{tenant_id}/agent
POST /api/v1/tenants/{tenant_id}/agent/{thread_id}/approval
```

Router-based LangGraph orchestration with `knowledge`, `sql`, `tool`, and
`unsupported` routes. Agent responses include `thread_id` and `status`
(`completed` | `approval_required`). Write actions pause for human approval;
resume with `{ "approved": true|false }`. Graph execution failures map to HTTP 503.

## Testing

Tests use a dedicated PostgreSQL database:

```text
agentic_ai_test
```

Run:

```bash
cd backend && uv run pytest -q
```

21 tests currently pass.

### Retrieval evaluation

```bash
cd ~/Desktop/enterprise-agentic-ai-platform &&
PYTHONPATH=backend uv run --project backend --env-file backend/.env python -m evals.retrieval.run_evaluation
```

Results are written to `evals/results/retrieval_results.json`.

The current golden set is intentionally small (15 queries) and should not be
treated as a large-scale production benchmark.

### Agent evaluation

24-case golden dataset at `evals/agent/golden_dataset.json` covering knowledge,
SQL, MCP/tool, HITL write actions, and unsupported requests.

Router-only evaluation:

```bash
cd ~/Desktop/enterprise-agentic-ai-platform &&
PYTHONPATH=backend uv run --project backend --env-file backend/.env python -m evals.agent.run_router_evaluation
```

End-to-end agent evaluation (with Langfuse tracing):

```bash
cd ~/Desktop/enterprise-agentic-ai-platform &&
PYTHONPATH=backend uv run --project backend --env-file backend/.env python -m evals.agent.run_agent_evaluation
```

Results are written to `evals/results/agent_evaluation.json`.

Current regression benchmark on this small dataset: **24/24** route accuracy,
**24/24** approval accuracy, **24/24** execution success, **24/24** end-to-end
pass rate. These are local regression results — not production-wide accuracy claims.

## Code Quality

```bash
cd backend
uv run ruff check app tests
uv run ruff format --check app tests
uv run ruff format app tests
```

## CI

GitHub Actions runs on pushes and pull requests to `master` and `main`.

```text
dependency install → Ruff lint → Ruff format check → pytest
```

## Roadmap

### Completed

- **Sprint 0** — Repository & architecture foundation
- **Sprint 1** — Enterprise knowledge ingestion & RAG v1
- **Sprint 2** — Advanced retrieval & evaluation
- **Sprint 3** — LangGraph agent orchestration (router graph)
- **Sprint 4** — MCP & enterprise tool integration
- **Sprint 5** — SQL agent, SQL security & human-in-the-loop
- **Sprint 6** — Evaluation, Langfuse & production observability
- **Sprint 7** — React chat UI & production UX

### Planned

- **Sprint 8–10** — Azure deployment, multimodal demo, portfolio polish

Production deployment, persistent checkpoint storage, JWT/RBAC, and persistent
chat history are not complete.

### Screenshots

Screenshots of the chat UI are not committed in this repository. Capture locally
after running `npm run dev` in `frontend/`.

## Design Principles

- Multi-tenancy and explicit tenant boundaries
- Async I/O and database migrations
- Testability and CI enforcement
- Measurable retrieval and agent quality
- Langfuse observability for agent debugging
- Secure SQL execution and human approval for sensitive write actions
- Reproducible local development

## License

No license has been selected yet.
