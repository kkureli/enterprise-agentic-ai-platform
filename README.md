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

**Sprint 8 — Azure Deployment & CI/CD: in progress (Phase 8A packaging complete)**

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
- Backend production Docker packaging (uv + uvicorn; no secrets in image)
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

    RagAPI --> RagCache[RAG Response Cache]
    RagCache --> Redis
    AgentAPI --> RateLimit[Agent Rate Limit]
    RateLimit --> Redis

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
- Redis (RAG response cache + agent rate limiting)
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

Use **separate** untracked env files (do not mix local and cloud URLs in one file):

```bash
cp .env.example .env.development   # local Docker Postgres / Redis / Qdrant
cp .env.example .env.production    # Neon / Qdrant Cloud / Upstash (local test only)
```

Always select the file explicitly with `uv run --env-file ...`. Settings do **not**
auto-load a shared `.env`.

Local development should use:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_ai
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true
RAG_CACHE_TTL_SECONDS=300
AGENT_RATE_LIMIT_REQUESTS=30
AGENT_RATE_LIMIT_WINDOW_SECONDS=60
QDRANT_URL=http://localhost:6333
CHECKPOINT_BACKEND=memory
```

Fill Azure OpenAI / Langfuse keys in `.env.development` as needed. Never commit
real secrets. Never put both localhost and cloud `QDRANT_URL` values in the same file.

### 4. Run migrations

```bash
uv run --env-file .env.development alembic upgrade head
```

Against Neon (from your machine, using production config):

```bash
uv run --env-file .env.production alembic upgrade head
```

### 5. Start the API

```bash
uv run --env-file .env.development uvicorn app.main:app --reload
```

Local test against cloud services:

```bash
uv run --env-file .env.production uvicorn app.main:app
```

### 6. Start the frontend (Sprint 7)

From the repository root:

```bash
cd frontend
cp .env.example .env.development
cp .env.example .env.production
npm install
npm run dev
```

Vite loads `.env.development` for `npm run dev` and `.env.production` for
`npm run build`. Local API base:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_TENANT_ID=
```

If `VITE_TENANT_ID` is empty, the playground loads demo tenants from
`GET /api/v1/demo/tenants` after seeding.

Seed the public demo playground (idempotent):

```bash
cd backend
PYTHONPATH=. uv run --env-file .env.development python scripts/seed_demo_playground.py
```

Useful URLs:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Playground UI: `http://localhost:5173`
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
PYTHONPATH=backend uv run --project backend --env-file backend/.env.development python -m evals.retrieval.run_evaluation
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
PYTHONPATH=backend uv run --project backend --env-file backend/.env.development python -m evals.agent.run_router_evaluation
```

End-to-end agent evaluation (with Langfuse tracing):

```bash
cd ~/Desktop/enterprise-agentic-ai-platform &&
PYTHONPATH=backend uv run --project backend --env-file backend/.env.development python -m evals.agent.run_agent_evaluation
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
backend job: dependency install → Ruff lint → Ruff format check → pytest
backend-image job: Docker build only (no push, no Azure credentials)
```

## Production packaging (Sprint 8 Phase 8A)

Backend container image (build from **repository root** so MCP is included):

```bash
docker build -f backend/Dockerfile -t enterprise-agentic-ai-backend .
```

- Image runs uvicorn on `0.0.0.0:${PORT:-8000}`
- Same container includes the stdio MCP server under `/app/mcp`
- Linux image uses **CPU-only PyTorch** (no CUDA/NVIDIA wheels)
- Secrets are injected at runtime via environment variables (see `backend/.env.example`)
- `/health` is liveness-compatible; `/ready` requires PostgreSQL and Qdrant.
  Redis is reported and may mark the app `degraded` without returning 503,
  because RAG cache and agent rate limiting fail open.
- Redis / Upstash: short-lived tenant-aware RAG response caching and
  lightweight agent rate limiting only (not application state or checkpoints)
- Azure OpenAI and Langfuse are **not** required for process liveness
- Frontend production builds use `VITE_API_BASE_URL` at build time
- Container-local document storage (`DOCUMENT_STORAGE_PATH`) is **not** durable —
  production object storage (Azure Blob) is Phase 8B
- No new application-hosting Azure resources were provisioned in Phase 8A.
  Existing Azure AI Foundry, Application Insights, and Log Analytics resources
  remain in use. The FastAPI backend and React frontend have not yet been
  deployed to Azure.

Phase 8B cost target: ~$0 fixed monthly (Static Web Apps Free, Container Apps
scale-to-zero, Neon/Qdrant/Upstash free tiers). Avoid AKS, GPU, always-on
compute, and paid managed databases for this portfolio demo.

Preparation for Phase 8B is documented in [`docs/phase-8b-runbook.md`](docs/phase-8b-runbook.md)
(checkpointer config, Neon migrations, ACA/SWA steps). **No new hosting/data
resources have been provisioned yet.**
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

### In progress

- **Sprint 8** — Azure deployment & CI/CD
  - Phase 8A (packaging) complete
  - Phase 8B (Azure provision / deploy) not started

### Planned

- **Sprint 9–10** — Multimodal demo, portfolio polish

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
