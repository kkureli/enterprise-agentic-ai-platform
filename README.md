# Enterprise Agentic AI Platform

A production-oriented, multi-tenant platform for building enterprise LLM, RAG, and agentic AI workflows.

The project is being developed incrementally with a focus on software engineering quality, tenant isolation, observability, evaluation, enterprise tool integration, and deployability.

## Current Status

**Sprint 0 — Repository & Architecture Foundation: completed**  
**Sprint 1 — Enterprise Knowledge Ingestion & RAG v1: completed**  
**Sprint 2 — Advanced Retrieval & Evaluation: completed**

Implemented so far:

- FastAPI backend with tenant-scoped APIs
- Async SQLAlchemy 2 + PostgreSQL + Alembic
- Redis and Qdrant infrastructure
- Document upload, parsing, chunking, and Azure OpenAI embeddings
- Dense + sparse hybrid retrieval with weighted RRF
- Query-aware dense/sparse weighting
- CrossEncoder reranking with retrieval-aware final rank fusion
- Multi-query expansion and multi-query hybrid retrieval
- Standard and Advanced RAG retrieval modes
- Retrieval evaluation (Recall@K, MRR, nDCG@K) with persisted results
- Health/readiness endpoints, Ruff, pytest, and GitHub Actions CI

Current RAG retrieval paths:

```text
Standard (default):
Query → Hybrid Retrieval → CrossEncoder → Rank Fusion → Top-K → LLM

Advanced:
Query → Query Expansion → Multi-Query Hybrid → CrossEncoder (original query)
  → Final Rank Fusion → Top-K → LLM
```

LangGraph agent orchestration, MCP integrations, human-in-the-loop workflows,
full observability, frontend development, and cloud deployment remain planned
for upcoming sprints.

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
 └── Documents / Vector Chunks
```

Each user and document belongs to one tenant through `tenant_id`.  
Retrieval and RAG always apply tenant filters in Qdrant.

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

### Data & Infrastructure

- PostgreSQL
- Redis
- Qdrant
- Docker Compose
- Azure OpenAI (embeddings + chat)
- FastEmbed BM25 (sparse)
- CrossEncoder reranker

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
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── scripts/
│   └── tests/
├── docs/
├── evals/
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

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Start the API

```bash
uv run uvicorn app.main:app --reload
```

Useful URLs:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
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

## Testing

Tests use a dedicated PostgreSQL database:

```text
agentic_ai_test
```

Run:

```bash
cd backend && uv run pytest -q
```

### Retrieval evaluation

```bash
cd ~/Desktop/enterprise-agentic-ai-platform &&
PYTHONPATH=backend uv run --project backend --env-file backend/.env python -m evals.retrieval.run_evaluation
```

Results are written to `evals/results/retrieval_results.json`.

The current golden set is intentionally small (15 queries) and should not be
treated as a large-scale production benchmark.

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

### Planned

- **Sprint 3** — LangGraph agent orchestration
- **Sprint 4** — MCP & enterprise tool integration
- **Sprint 5** — SQL agent, security & human-in-the-loop
- **Sprint 6** — Observability & broader evaluation gates
- **Sprint 7–10** — Frontend, Azure deployment, multimodal demo, portfolio polish

## Design Principles

- Multi-tenancy and explicit tenant boundaries
- Async I/O and database migrations
- Testability and CI enforcement
- Measurable retrieval quality
- Secure tool execution and human approval for sensitive actions (planned)
- Reproducible local development

## License

No license has been selected yet.
