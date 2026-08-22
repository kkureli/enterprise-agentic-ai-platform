# Architecture

## Current Architecture — Sprint 0–3

The platform currently provides a multi-tenant FastAPI backend with document
ingestion, hybrid retrieval, reranking, multi-query RAG modes, retrieval
evaluation, and a **router-based LangGraph agent**. SQL Agent, MCP tools,
HITL, conversation memory, and Langfuse remain planned.

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
    DocumentAPI --> Embed[Azure OpenAI Embeddings]
    Embed --> Qdrant[(Qdrant Dense + Sparse)]

    RetrievalAPI --> Hybrid[Hybrid Retrieval]
    RagAPI --> Mode{retrieval_mode}
    Mode -->|standard| HybridRerank[Hybrid + Reranker + Fusion]
    Mode -->|advanced| MultiQuery[Multi-Query Hybrid + Reranker + Fusion]
    HybridRerank --> Chat[Azure OpenAI Chat]
    MultiQuery --> Chat

    AgentAPI --> Graph[LangGraph Router Graph]
    Graph -->|knowledge| RagReuse[Reuse RAG Pipeline]
    Graph -->|unsupported| Fallback[Fallback Node]
    RagReuse --> Mode

    Hybrid --> Qdrant
    HybridRerank --> Qdrant
    MultiQuery --> Qdrant

    HealthAPI --> PostgreSQL
    HealthAPI --> Redis[(Redis)]
    HealthAPI --> Qdrant

    Alembic[Alembic Migrations] --> PostgreSQL
    Evals[Retrieval Eval Runner] --> Qdrant
    Evals --> Results[evals/results/retrieval_results.json]
```

## Request Path

A normal database-backed API request currently follows this path:

```text
HTTP Request
    ↓
FastAPI Route
    ↓
Pydantic Validation
    ↓
FastAPI Dependency Injection
    ↓
SQLAlchemy AsyncSession
    ↓
SQLAlchemy Async Engine
    ↓
asyncpg
    ↓
PostgreSQL
```

`AsyncSession` is created per request through the `get_db` FastAPI dependency.

## RAG Retrieval Paths

### Standard (default)

```text
Query
  ↓
Dense + Sparse Hybrid Retrieval
  ↓
Weighted RRF
  ↓
CrossEncoder Reranker
  ↓
Final Rank Fusion
  ↓
Top-K Chunks
  ↓
Azure OpenAI Chat
  ↓
Grounded Answer + Sources
```

### Advanced

```text
Query
  ↓
Query Expansion
  ↓
Multi-Query Hybrid Retrieval
  ↓
Multi-Query RRF + Deduplication
  ↓
CrossEncoder (original user query)
  ↓
Final Rank Fusion
  ↓
Top-K Chunks
  ↓
Azure OpenAI Chat
  ↓
Grounded Answer + Sources
```

CrossEncoder always receives the original user query. Expansion queries are used
only for candidate retrieval.

## Agent Orchestration (Sprint 3)

The agent layer is a **router-based LangGraph graph**, not a full multi-agent
supervisor. RAG is invoked as an existing capability; retrieval and generation
are not reimplemented inside the graph.

### Implemented graph

```text
START
  ↓
LLM Router (structured output)
  ├── knowledge → RAG Node → Finalize → END
  └── unsupported → Fallback → END
```

### Shared state

```text
AgentState
├── tenant_id
├── query
├── retrieval_mode   # standard | advanced
├── route            # knowledge | unsupported
├── rag_answer
└── final_answer
```

### Request path

```text
POST /api/v1/tenants/{tenant_id}/agent
  ↓
Validate tenant + payload
  ↓
agent_graph.ainvoke({ tenant_id, query, retrieval_mode })
  ↓
{ route, answer }
```

Failure handling:

- invalid `retrieval_mode` → HTTP 422
- graph execution exception → HTTP 503 (`Agent execution failed.`)

### What is intentionally not implemented yet

- SQL Agent
- MCP tool agent
- Human-in-the-loop approvals
- Multi-agent supervisor orchestration
- Conversation memory / checkpoint persistence
- Langfuse / full observability traces
- Automatic retry policies

## Multi-Tenant Data Model

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    TENANT ||--o{ DOCUMENT : owns

    TENANT {
        uuid id PK
        string name
        datetime created_at
        datetime updated_at
    }

    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string full_name
        datetime created_at
        datetime updated_at
    }

    DOCUMENT {
        uuid id PK
        uuid tenant_id FK
        string filename
        string content_type
        int file_size_bytes
        string checksum_sha256
        string status
        datetime created_at
        datetime updated_at
    }
```

User email uniqueness is tenant-scoped:

```text
UNIQUE (tenant_id, email)
```

## Tenant Isolation

Documents, retrieval, and RAG are tenant-scoped.

Qdrant queries always include a `tenant_id` payload filter. Optional metadata
filters (`document_id`, `filename`) compose with that tenant boundary.

Conceptually:

```text
Tenant A
 ├── Documents A*
 └── Chunks A*

Tenant B
 ├── Documents B*
 └── Chunks B*
```

A request for Tenant A must never return Tenant B chunks.

## Infrastructure

Local infrastructure is orchestrated through Docker Compose.

### PostgreSQL

Current responsibility:

- Tenant data
- User data
- Document metadata
- Relational application state

### Redis

Currently provisioned and validated through the readiness endpoint.

Planned responsibilities (not yet implemented):

- Caching
- Transient agent state
- Checkpoint support
- Rate limiting

### Qdrant

Current responsibility:

- Dense embeddings
- Sparse BM25 vectors
- Tenant-scoped hybrid retrieval
- Metadata filtering

Qdrant remains a retrieval index, not the primary application database.

## Health Model

```text
GET /health
GET /ready
```

`/health` verifies that the application process is running.

`/ready` verifies critical infrastructure dependencies:

```text
PostgreSQL
Redis
Qdrant
```

## Database Migrations

Schema evolution is managed with Alembic.

Current migration history includes:

```text
create tenants table
        ↓
create users table
        ↓
create documents table
```

## Testing Architecture

Integration tests use a dedicated PostgreSQL database:

```text
agentic_ai_test
```

Retrieval evaluation is separate from unit/integration tests:

```text
evals/datasets/retrieval_golden.jsonl
        ↓
evals/retrieval/run_evaluation.py
        ↓
evals/results/retrieval_results.json
```

The golden set is intentionally small and is a reproducible Sprint 2 artifact,
not a large-scale production benchmark.

Critical agent API tests cover graph result mapping, invalid `retrieval_mode`
validation (422), and controlled graph failure handling (503).

## CI Architecture

GitHub Actions executes the backend quality gate on pushes and pull requests.

```mermaid
flowchart LR
    Push[Push / Pull Request] --> Checkout[Checkout]
    Checkout --> UV[Install uv + Python]
    UV --> Dependencies[Install Dependencies]
    Dependencies --> Lint[Ruff Lint]
    Lint --> Format[Ruff Format Check]
    Format --> Tests[pytest]
    Tests --> Postgres[(PostgreSQL Test DB)]
```

## Current Technology Stack

### Application

- Python 3.12
- FastAPI
- Pydantic
- LangChain text splitters / Azure OpenAI integrations
- LangGraph (router-based agent orchestration)

### Persistence & Retrieval

- SQLAlchemy 2 Async
- asyncpg
- PostgreSQL
- Alembic
- Qdrant (dense + sparse)
- FastEmbed BM25
- CrossEncoder reranker

### Infrastructure

- Docker Compose
- Redis
- Azure OpenAI

### Quality

- pytest
- pytest-asyncio
- HTTPX
- Ruff
- GitHub Actions
- Retrieval evaluation under `evals/`

## Planned Target Architecture

The following remains the longer-term direction. Sprint 3 delivers only the
router-based LangGraph entrypoint above; supervisor-style multi-agent flows,
MCP tools, SQL agent, HITL, and observability expansion are **not** current
implementation:

```mermaid
flowchart TD
    User[User / React UI]
    User --> API[FastAPI API]

    API --> Auth[Auth / Tenant Context]
    API --> Graph[LangGraph Orchestrator]

    Graph --> RAG[RAG / Retrieval]
    Graph --> Tools[Enterprise Tools]
    Graph --> SQL[SQL / Data Agent]
    Graph --> HITL[Human Approval]

    RAG --> Qdrant[(Qdrant)]
    RAG --> LLM[Azure OpenAI / AI Foundry]

    Tools --> MCP[MCP Servers]
    MCP --> External[Enterprise APIs / Systems]

    SQL --> PostgreSQL[(PostgreSQL)]

    Graph --> Redis[(Redis State / Cache)]
    Graph --> Observability[Langfuse / OpenTelemetry]
    Graph --> Evals[Evaluation Layer]
```

Planned components such as MCP tools, HITL, React UI, cloud deployment, and
supervisor-style agent expansion will only be marked as implemented after their
corresponding sprint is completed.

## Architecture Principles

The project is designed around:

- Tenant isolation
- Explicit data ownership
- Async I/O
- Schema migrations
- Testability
- CI enforcement
- Measurable retrieval quality
- Observability (planned expansion)
- Secure tool execution (planned)
- Human approval for sensitive actions (planned)
- Reproducible local environments
