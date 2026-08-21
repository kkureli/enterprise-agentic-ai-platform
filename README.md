# Enterprise Agentic AI Platform

A production-oriented, multi-tenant platform for building enterprise LLM, RAG, and agentic AI workflows.

The project is being developed incrementally with a focus on software engineering quality, tenant isolation, observability, evaluation, enterprise tool integration, and deployability.

## Current Status

**Sprint 0 — Repository & Architecture Foundation: completed**  
**Sprint 1 — Enterprise Knowledge Ingestion & RAG v1: completed**

Implemented so far:

- FastAPI backend
- Async SQLAlchemy 2 + asyncpg
- PostgreSQL
- Alembic migrations
- Redis infrastructure
- Qdrant vector database
- Tenant model and REST API
- User model and tenant relationship
- Tenant-scoped data isolation
- Document model and upload API
- Local document storage with SHA-256 checksums
- PDF and TXT parsing
- Recursive document chunking with LangChain
- Azure OpenAI embeddings
- Dense vector indexing in Qdrant
- Tenant-filtered semantic retrieval
- Retrieval REST API
- Azure OpenAI chat model integration
- Grounded RAG generation
- LLM-selected source citations
- Retrieved-chunk inspection for debugging and evaluation
- Health and readiness endpoints
- Integration tests with a dedicated PostgreSQL test database
- Ruff linting and formatting
- GitHub Actions CI

Current end-to-end RAG flow:

```text
Document Upload
      ↓
Parsing
      ↓
Chunking
      ↓
Azure OpenAI Embeddings
      ↓
Qdrant Indexing
      ↓
Tenant-Scoped Retrieval
      ↓
Azure OpenAI Chat Model
      ↓
Grounded Answer
      ↓
Selected Sources + Retrieved Chunks

## Architecture

```mermaid
flowchart TD
    Client[API Client / Swagger]

    Client --> FastAPI[FastAPI Application]

    FastAPI --> TenantAPI[Tenant API]
    FastAPI --> UserAPI[User API]
    FastAPI --> HealthAPI[Health & Readiness API]

    TenantAPI --> Session[SQLAlchemy AsyncSession]
    UserAPI --> Session

    Session --> Engine[SQLAlchemy Async Engine]
    Engine --> AsyncPG[asyncpg]
    AsyncPG --> PostgreSQL[(PostgreSQL)]

    HealthAPI --> PostgreSQL
    HealthAPI --> Redis[(Redis)]
    HealthAPI --> Qdrant[(Qdrant)]

    Alembic[Alembic Migrations] --> PostgreSQL

    Pytest[pytest Integration Tests] --> FastAPI
    Ruff[Ruff Lint & Format] --> FastAPI

    GitHub[GitHub Actions CI]
    GitHub --> Ruff
    GitHub --> Pytest
```

More detail is available in [`docs/architecture.md`](docs/architecture.md).

## Multi-Tenant Model

The current data model establishes the first tenant boundary:

```text
Tenant
 └── Users
```

Each user belongs to one tenant through `tenant_id`.

User email uniqueness is scoped per tenant:

```text
UNIQUE (tenant_id, email)
```

This means:

```text
Tenant A + kaan@example.com  ✅
Tenant B + kaan@example.com  ✅
Tenant A + kaan@example.com  ❌ duplicate inside the same tenant
```

The same tenant boundary will later be extended to documents, retrieval, agent state, tools, and authorization.

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

### Quality

- pytest
- pytest-asyncio
- HTTPX
- Ruff
- GitHub Actions

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
│   │   └── schemas/
│   └── tests/
├── docs/
├── evals/
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

## Testing

Tests use a dedicated PostgreSQL database:

```text
agentic_ai_test
```

Run:

```bash
uv run pytest -q
```

The test suite currently covers the critical foundation flows, including tenant creation, duplicate constraints, user creation, and tenant-scoped user isolation.

## Code Quality

Run linting:

```bash
uv run ruff check app tests
```

Check formatting:

```bash
uv run ruff format --check app tests
```

Format automatically:

```bash
uv run ruff format app tests
```

## CI

GitHub Actions runs on pushes and pull requests to `master` and `main`.

The backend pipeline performs:

```text
dependency install
        ↓
Ruff lint
        ↓
Ruff format check
        ↓
pytest against PostgreSQL test DB
```

## Roadmap

### Sprint 1 — Enterprise Knowledge Ingestion & RAG v1

Planned:

- Tenant-scoped document model
- Document upload
- Parsing and chunking
- Embeddings
- Qdrant vector storage
- Tenant-filtered retrieval
- Grounded LLM answers with citations

### Sprint 2 — Advanced Retrieval & Evaluation

Planned:

- Hybrid retrieval
- Reranking
- Retrieval evaluation
- Golden datasets
- Recall / MRR / nDCG

### Sprint 3–6 — Agentic AI & Reliability

Planned:

- LangGraph orchestration
- MCP tool integration
- SQL/data agent
- Human-in-the-loop flows
- Agent permissions
- Langfuse / OpenTelemetry
- Evaluation and regression gates

### Sprint 7–10 — Productization

Planned:

- React frontend
- Production UX
- Azure deployment
- CI/CD expansion
- Manufacturing-oriented multimodal use case
- Portfolio evidence and demos

## Design Principles

The project is being built around several production concerns from the beginning:

- Multi-tenancy
- Explicit tenant boundaries
- Async I/O
- Database migrations
- Testability
- CI enforcement
- Observability
- Evaluation
- Secure tool execution
- Human approval for sensitive actions
- Reproducible local development

## License

No license has been selected yet.
