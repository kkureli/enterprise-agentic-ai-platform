# Enterprise Agentic AI Platform — Project Plan

This document tracks the implementation roadmap for the **Enterprise Agentic AI Platform**.

The project is intentionally built in incremental sprints. A capability is only marked as complete after it is implemented and verified locally.

**Current progress:** Sprint 0 ✅ · Sprint 1 ✅ · Sprint 2 ✅ · Sprint 3 ✅ · Sprint 4 ✅ · Sprint 5+ ⬜ planned

## Status Legend

- ✅ Completed
- 🟡 In progress
- ⬜ Planned

---

# Sprint 0 — Repository & Architecture Foundation

**Goal:** Establish a production-oriented backend foundation before building AI workflows.

## Completed

- ✅ Monorepo structure
- ✅ Python 3.12 + `uv`
- ✅ FastAPI application
- ✅ Environment configuration with Pydantic Settings
- ✅ Docker Compose infrastructure
  - PostgreSQL
  - Redis
  - Qdrant
- ✅ `/health` endpoint
- ✅ `/ready` endpoint
- ✅ Async SQLAlchemy 2 setup
- ✅ `asyncpg`
- ✅ Alembic migrations
- ✅ Tenant model
- ✅ Tenant REST API
- ✅ User model
- ✅ Tenant → User relationship
- ✅ Tenant-scoped user queries
- ✅ Dedicated PostgreSQL test database
- ✅ Critical integration tests
- ✅ Ruff linting and formatting
- ✅ GitHub Actions CI
- ✅ Initial architecture documentation

## Foundation Architecture

```text
Client
  ↓
FastAPI
  ↓
Pydantic
  ↓
SQLAlchemy AsyncSession
  ↓
asyncpg
  ↓
PostgreSQL

Redis   → cache / transient state foundation
Qdrant  → vector retrieval foundation
```

---

# Sprint 1 — Enterprise Knowledge Ingestion & RAG v1

**Goal:** Build the first complete tenant-isolated RAG pipeline.

## 1.1 Document Management

- ✅ Tenant-scoped `Document` model
- ✅ Alembic migration
- ✅ File upload endpoint
- ✅ PDF/TXT validation
- ✅ Local document storage
- ✅ SHA-256 checksum
- ✅ PostgreSQL document metadata
- ✅ Document processing status

Current metadata:

```text
Document
├── id
├── tenant_id
├── filename
├── content_type
├── file_size_bytes
├── checksum_sha256
├── status
├── created_at
└── updated_at
```

## 1.2 Parsing

- ✅ TXT parsing
- ✅ PDF parsing with `pypdf`
- ✅ Empty document detection
- ✅ Parse error handling

## 1.3 Chunking

- ✅ `langchain-text-splitters`
- ✅ `RecursiveCharacterTextSplitter`
- ✅ Configurable chunk size
- ✅ Configurable overlap

Current defaults:

```text
chunk_size    = 1000
chunk_overlap = 150
```

## 1.4 Embeddings

- ✅ Azure OpenAI embedding integration
- ✅ `AzureOpenAIEmbeddings`
- ✅ Document embedding function
- ✅ Query embedding function
- ✅ Real Azure deployment verified

Current flow:

```text
Chunk Text
   ↓
Azure OpenAI Embedding Deployment
   ↓
Dense Vector
```

## 1.5 Qdrant Indexing

- ✅ Qdrant collection creation
- ✅ Dense vector indexing
- ✅ Chunk payload metadata
- ✅ Tenant metadata
- ✅ Document metadata
- ✅ Real Azure embeddings indexed
- ✅ End-to-end ingestion pipeline

Current Qdrant point:

```text
Point
├── id
├── dense vector
└── payload
    ├── tenant_id
    ├── document_id
    ├── filename
    ├── chunk_index
    └── text
```

End-to-end ingestion:

```text
Upload
  ↓
Store File
  ↓
Parse
  ↓
Chunk
  ↓
Azure Embeddings
  ↓
Qdrant
  ↓
Document.status = indexed
```

## 1.6 Semantic Retrieval

- ✅ Query embeddings
- ✅ Dense semantic search
- ✅ Qdrant tenant filter
- ✅ Top-K results
- ✅ Retrieval service
- ✅ Retrieval REST API
- ✅ Semantic ranking verified with multiple unrelated documents

Current retrieval:

```text
User Query
    ↓
Azure Query Embedding
    ↓
Qdrant Dense Search
    +
tenant_id filter
    ↓
Top-K Relevant Chunks
```

## 1.7 RAG Generation

- ✅ Azure OpenAI chat model deployment
- ✅ RAG service
- ✅ Retrieve relevant chunks
- ✅ Construct grounded context
- ✅ System prompt
- ✅ Generate answer from retrieved context
- ✅ Refuse / qualify when context is insufficient

Target flow:

```text
Question
   ↓
Retriever
   ↓
Top-K Chunks
   ↓
Prompt + Context
   ↓
Azure OpenAI Chat Model
   ↓
Grounded Answer
```

## 1.8 Sources & Citations

- ✅ Return source metadata with each answer
- ✅ `document_id`
- ✅ `filename`
- ✅ `chunk_index`
- ✅ Retrieval score where useful

Target response:

```json
{
  "answer": "Employees receive 20 working days of paid annual leave.",
  "sources": [
    {
      "document_id": "...",
      "filename": "vacation-policy.txt",
      "chunk_index": 0
    }
  ]
}
```

## 1.9 Critical RAG Tests

Keep coverage focused on high-value behavior.

- ✅ Tenant A must never retrieve Tenant B chunks
- ✅ Invalid documents must fail safely
- ✅ Retrieval must return relevant results
- ✅ RAG response must include sources
- ✅ CI must remain green

## Sprint 1 Definition of Done

Sprint 1 is complete when this works end-to-end:

```text
Tenant uploads PDF/TXT
        ↓
Document parsed
        ↓
Document chunked
        ↓
Chunks embedded
        ↓
Vectors stored in Qdrant
        ↓
User asks question
        ↓
Tenant-scoped retrieval
        ↓
LLM generates grounded answer
        ↓
Answer returned with sources
```

---

# Sprint 2 — Advanced Retrieval & Evaluation

**Status: ✅ Completed**

**Goal:** Upgrade basic dense RAG into a measurable production retrieval system.

## 2.1 Hybrid Retrieval

- ✅ Dense retrieval with Azure OpenAI embeddings
- ✅ Sparse / lexical retrieval with FastEmbed BM25
- ✅ Dense + sparse hybrid retrieval
- ✅ Weighted Reciprocal Rank Fusion (RRF)
- ✅ Query-aware dense/sparse weighting
  - default: dense `0.7` / sparse `0.3`
  - strong identifier queries (e.g. `AX-4317`): dense `0.5` / sparse `0.5`
- ✅ Tenant-scoped Qdrant filtering
- ✅ Optional metadata filters (`document_id`, `filename`)
- ✅ Centralized retrieval settings in `app/core/config.py`

Chunk identity remains `(document_id, chunk_index)`.

## 2.2 Reranking & Final Fusion

- ✅ CrossEncoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- ✅ Retrieval-aware final rank fusion
  - hybrid / multi-query base ranking is not replaced by CrossEncoder alone
  - base ranking + CrossEncoder ranking are fused with weighted rank-based RRF
- ✅ Raw hybrid scores are never mixed with raw CrossEncoder scores

## 2.3 Multi-Query Retrieval

- ✅ LLM query expansion (up to 3 alternatives; original query preserved)
- ✅ Important identifiers preserved during expansion
- ✅ Multi-query hybrid retrieval
- ✅ Candidate deduplication
- ✅ Query-level weighted RRF
  - original query weighted higher than expanded variants
- ✅ CrossEncoder always scores against the **original user query**

## 2.4 Production RAG Modes

Request field: `retrieval_mode` on `POST /api/v1/tenants/{tenant_id}/rag`

| Mode | Default | Path |
|------|---------|------|
| `standard` | yes | Hybrid → CrossEncoder → final rank fusion → Top-K → LLM |
| `advanced` | no | Query expansion → Multi-Query Hybrid → CrossEncoder (original query) → final fusion → Top-K → LLM |

Invalid modes are rejected with HTTP 422.

### Standard path

```text
Query
  ↓
Hybrid Retrieval (dense + sparse, query-aware weights, weighted RRF)
  ↓
CrossEncoder
  ↓
Rank Fusion (base ranking + reranker ranking)
  ↓
Top-K
  ↓
LLM grounded answer
```

### Advanced path

```text
Query
  ↓
Query Expansion
  ↓
Multi-Query Hybrid Retrieval
  ↓
Multi-Query RRF + deduplication
  ↓
CrossEncoder (original user query)
  ↓
Final Rank Fusion
  ↓
Top-K
  ↓
LLM grounded answer
```

## 2.5 Retrieval Evaluation

- ✅ Golden retrieval dataset: `evals/datasets/retrieval_golden.jsonl`
- ✅ Metrics: Recall@K, MRR, nDCG@K
- ✅ Strategy comparison runner: `evals/retrieval/run_evaluation.py`
- ✅ Persisted benchmark artifact: `evals/results/retrieval_results.json`

Evaluated strategies:

- Dense
- Sparse
- Hybrid
- Hybrid + Reranker
- Multi-Query Hybrid
- Multi-Query + Reranker

### Sprint 2 benchmark (from `evals/results/retrieval_results.json`)

Evaluated at `2026-08-22T18:12:54.291506+00:00` · `eval_k = 3` · `15` golden queries.

| Strategy | Recall@3 | MRR | nDCG@3 |
|----------|----------|-----|--------|
| Dense | 1.0000 | 1.0000 | 1.0000 |
| Sparse | 0.9333 | 0.9000 | 0.9087 |
| Hybrid | 1.0000 | 1.0000 | 0.9946 |
| Hybrid + Reranker | 1.0000 | 1.0000 | 0.9946 |
| Multi-Query Hybrid | 1.0000 | 1.0000 | 1.0000 |
| Multi-Query + Reranker | 1.0000 | 1.0000 | 1.0000 |

> Note: this evaluation corpus is intentionally small and should not be presented as a large-scale production benchmark. It is a reproducible Sprint 2 portfolio artifact for ranking behavior and regression visibility.

## Sprint 2 Definition of Done

Sprint 2 is complete when:

```text
Dense / Sparse / Hybrid retrieval works under tenant isolation
        ↓
Query-aware hybrid weighting and RRF are configurable
        ↓
CrossEncoder + final rank fusion protects against reranker regressions
        ↓
Multi-query advanced path is available via retrieval_mode
        ↓
Retrieval metrics are measurable and persisted
```

Remaining regression-gate automation (CI-enforced retrieval checks) is deferred to later reliability work and is not required for Sprint 2 completion.

---

# Sprint 3 — LangGraph Agent Orchestration

**Status: ✅ Completed**

**Goal:** Introduce the first stateful orchestration layer over the existing RAG capability.

This sprint delivers a **router-based LangGraph orchestration graph**, not a full
multi-agent supervisor architecture. MCP tools were added in Sprint 4. SQL Agent,
HITL, conversation memory, and Langfuse remain planned for later sprints.

## 3.1 Graph & Shared State

- ✅ LangGraph `StateGraph` orchestration
- ✅ Shared `AgentState` (`tenant_id`, `query`, `retrieval_mode`, `route`, `rag_answer`, `final_answer`)
- ✅ Compiled graph entrypoint: `agent_graph`

## 3.2 LLM Router

- ✅ LLM-based router with structured output
- ✅ Routes (as delivered in Sprint 3):
  - `knowledge` — answerable from enterprise documents / knowledge base
  - `unsupported` — capabilities not yet available
- ✅ Conditional edges from router to specialist / fallback nodes
- ✅ Sprint 4 extended routes with `tool` (see Sprint 4)

## 3.3 Specialist & Response Nodes

- ✅ RAG specialist node that **reuses** `answer_question()` from the existing RAG pipeline
  - does not reimplement retrieval or generation inside LangGraph
  - propagates `retrieval_mode` (`standard` / `advanced`)
- ✅ Finalize node (knowledge path)
- ✅ Fallback node for unsupported requests

## 3.4 Implemented Graph (Sprint 3 baseline)

```text
START
  ↓
LLM Router
  ├── knowledge → RAG Node → Finalize → END
  └── unsupported → Fallback → END
```

Sprint 4 adds the `tool` → MCP Tool Node path; see Sprint 4 for the current graph.

## 3.5 Agent API

- ✅ `POST /api/v1/tenants/{tenant_id}/agent`
- ✅ Request: `question`, optional `retrieval_mode` (default `standard`)
- ✅ Response: `{ route, answer }`
- ✅ Tenant 404 when tenant is missing
- ✅ Invalid `retrieval_mode` → HTTP 422
- ✅ Controlled graph execution failure handling → HTTP 503 (`Agent execution failed.`)

## 3.6 Critical Agent Tests

- ✅ Successful graph result mapping for `knowledge` and `unsupported`
- ✅ Invalid `retrieval_mode` validation (422)
- ✅ Graph execution failure maps to 503

## Sprint 3 Definition of Done

Sprint 3 is complete when:

```text
Agent request enters LangGraph
        ↓
LLM router classifies knowledge vs unsupported
        ↓
Knowledge path reuses existing RAG (standard/advanced)
        ↓
Unsupported path returns controlled fallback
        ↓
API returns route + answer, with 422/503 guards
```

**Not in Sprint 3 (delivered later or still planned):** MCP Agent (Sprint 4),
SQL Agent, HITL approvals, supervisor orchestration, conversation memory,
retries/persistence, or Langfuse tracing.

---

# Sprint 4 — MCP & Enterprise Tool Integration

**Status: ✅ Completed**

**Goal:** Allow agents to interact with enterprise operational tools through a
controlled MCP integration, without claiming real external system persistence
or Sprint 5 security/HITL features.

## 4.1 MCP Server Project

- ✅ Separate MCP server package under `/mcp`
- ✅ Local stdio transport between backend and MCP server
- ✅ MCP does **not** expose REST endpoints; tools are invoked over MCP protocol
- ✅ Structured tool outputs (Pydantic models → structured content)

## 4.2 Implemented MCP Tools

| Tool | Purpose | Persistence |
|------|---------|-------------|
| `get_asset_status` | Current operational status for an asset | Read from in-memory demo data |
| `get_maintenance_history` | Maintenance history for an asset | Read from in-memory demo data |
| `create_maintenance_ticket` | Create a maintenance ticket | **Simulated write** — does **not** persist to a DB or external enterprise API |

## 4.3 Backend MCP Client

- ✅ `maintenance_mcp_session()` — stdio client session to `/mcp/server.py`
- ✅ Tool discovery via `list_tools()`
- ✅ Tool execution via `call_tool()`
- ✅ Structured MCP tool outputs consumed by the agent

## 4.4 LangGraph Tool Route

- ✅ Router route types: `knowledge` | `tool` | `unsupported`
- ✅ MCP Tool Node integrated into the LangGraph graph
- ✅ LLM tool binding using discovered MCP tool schemas
- ✅ Tool-calling loop:

```text
User request
  ↓
LLM tool selection (bound MCP schemas)
  ↓
MCP execution (call_tool)
  ↓
ToolMessage
  ↓
LLM final answer
```

Routing responsibilities:

- The **router** first selects the capability category (`knowledge` / `tool` / `unsupported`).
- The **MCP Tool Node's LLM** then selects the specific MCP tool.
- MCP itself does not create REST endpoints.

## 4.5 Current Graph

```text
START
  ↓
LLM Router
  ├── knowledge → RAG Node → Finalize → END
  ├── tool → MCP Tool Node → Finalize → END
  └── unsupported → Fallback → END
```

## 4.6 Agent API

- ✅ `POST /api/v1/tenants/{tenant_id}/agent` supports the `tool` route
- ✅ Response continues to return `{ route, answer }`

## 4.7 Tests

- ✅ 18 tests currently pass (`cd backend && uv run pytest -q`)

## Sprint 4 Definition of Done

Sprint 4 is complete when:

```text
MCP server runs as a separate /mcp project over stdio
        ↓
Backend discovers tools via list_tools()
        ↓
Router can select the tool capability route
        ↓
MCP Tool Node binds schemas, calls MCP, returns ToolMessage → final answer
        ↓
create_maintenance_ticket is documented as simulated (no DB / external API write)
        ↓
Agent API returns route + answer for tool requests; tests remain green
```

**Not in Sprint 4 (still planned):** write persistence to a real DB or enterprise
API, HITL/approval gates, SQL agent & SQL security, JWT/RBAC, real external
enterprise system integration, conversation memory, or Langfuse.

---

# Sprint 5 — SQL Agent, Security & Human-in-the-Loop

**Status: ⬜ Planned**

**Goal:** Introduce controlled data access and approval-sensitive actions.

## SQL / Data Agent

- ⬜ Natural language → database intent
- ⬜ Read-only SQL execution
- ⬜ Query validation
- ⬜ Result formatting
- ⬜ Tenant data isolation

## Security

- ⬜ JWT authentication
- ⬜ RBAC
- ⬜ Tenant context from authenticated identity
- ⬜ Tool permissions
- ⬜ Prompt injection defenses
- ⬜ Input validation
- ⬜ Audit trail
- ⬜ SQL security controls

## Human-in-the-Loop

- ⬜ Pause before sensitive actions
- ⬜ Human approval
- ⬜ Resume workflow
- ⬜ Redis-backed transient workflow state

## Enterprise Write Persistence (planned)

- ⬜ Persist write/action tools (e.g. tickets) to a DB or real external enterprise API
- ⬜ Real external enterprise system integration beyond local MCP demo data

---

# Sprint 6 — Evaluation, Reliability & Observability

**Goal:** Make the AI system measurable and debuggable in production-like conditions.

- ⬜ Langfuse integration
- ⬜ OpenTelemetry
- ⬜ LLM tracing
- ⬜ Retrieval tracing
- ⬜ Tool-call tracing
- ⬜ Latency metrics
- ⬜ Token usage
- ⬜ Cost tracking
- ⬜ Agent success/failure metrics
- ⬜ RAG answer evaluation
- ⬜ Golden datasets
- ⬜ Regression gates
- ⬜ Model comparison
- ⬜ Prompt/version tracking

---

# Sprint 7 — React UI & Production UX

**Goal:** Provide a usable interface for enterprise knowledge and agent workflows.

- ⬜ React frontend
- ⬜ Tenant-aware application shell
- ⬜ Document upload UI
- ⬜ Document status UI
- ⬜ Chat interface
- ⬜ Source/citation rendering
- ⬜ Agent execution status
- ⬜ Human approval UI
- ⬜ Retrieval/debug view where useful
- ⬜ Error/loading states

---

# Sprint 8 — Azure Deployment & CI/CD

**Goal:** Move the system from local Docker development to cloud deployment.

Planned target infrastructure:

```text
FastAPI          → Azure-hosted compute
PostgreSQL       → Azure Database for PostgreSQL
File Storage     → Azure Blob Storage
Embeddings / LLM → Azure OpenAI / Microsoft Foundry
Qdrant           → Qdrant Cloud or managed deployment
Redis            → Managed Redis
Observability    → Langfuse / OpenTelemetry
```

Tasks:

- ⬜ Production Docker images
- ⬜ Azure infrastructure
- ⬜ Secret management
- ⬜ Production environment configuration
- ⬜ Database migration deployment
- ⬜ CI/CD deployment pipeline
- ⬜ Health/readiness deployment checks
- ⬜ HTTPS / production networking
- ⬜ Cloud persistence verification

---

# Sprint 9 — Multimodal Manufacturing Use Case

**Goal:** Add a manufacturing-oriented scenario demonstrating multimodal AI capability.

- ⬜ Manufacturing demo data
- ⬜ Image understanding
- ⬜ RAG grounding
- ⬜ Agent/tool workflow
- ⬜ Operational, non-safety-critical demo scenario

---

# Sprint 10 — Portfolio Polish & Evidence

**Goal:** Turn the implementation into strong engineering evidence.

- ✅ Architecture diagrams
- ✅ Updated README
- ⬜ Demo screenshots
- ⬜ Demo video
- ⬜ Performance evidence
- ✅ Retrieval evaluation results
- ⬜ Cost/latency measurements
- ⬜ Security design summary
- ⬜ Deployment architecture
- ⬜ CV-ready project bullets
- ⬜ Interview explanation material

---

# Sprint 11 — AI Code Review / Repository Intelligence Agent

**Goal:** Build a public repository-focused AI engineering project demonstrating AI-assisted software development workflows.

- ⬜ Repository ingestion
- ⬜ Code-aware retrieval
- ⬜ Diff analysis
- ⬜ Merge-request / pull-request review
- ⬜ Local model option
- ⬜ Cloud model option
- ⬜ Structured review comments
- ⬜ Evaluation dataset
- ⬜ CI integration
- ⬜ Model/review quality comparison

---

# Overall Target Architecture

The diagram below is the long-term target. Sprints 3–4 currently implement a
router-based LangGraph path (`knowledge` → RAG, `tool` → local MCP tools over
stdio, `unsupported` → fallback). SQL Agent, HITL, write persistence to real
enterprise systems, and full observability remain planned.

```text
                         User
                          │
                          ▼
                      React UI
                          │
                          ▼
                       FastAPI
                          │
                    Auth / Tenant
                          │
                          ▼
                     LangGraph
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
             RAG       SQL Agent    MCP Tools
              │           │           │
              ▼           ▼           ▼
           Qdrant     PostgreSQL   Enterprise APIs
              │
              ▼
        Azure OpenAI / Foundry

              LangGraph
                  │
          ┌───────┴────────┐
          ▼                ▼
        Redis          Human Approval

                  │
                  ▼
          Langfuse / OpenTelemetry
                  │
                  ▼
             Evaluation Layer
```

---

# Engineering Principles

Throughout all sprints:

- Do not mark planned functionality as implemented.
- Preserve tenant isolation at every data boundary.
- Prefer clear service boundaries over large API route functions.
- Keep AI providers replaceable where practical.
- Measure retrieval and generation quality instead of relying only on demos.
- Use human approval for sensitive tool actions.
- Treat PostgreSQL as the relational source of truth.
- Treat Qdrant as a retrieval index, not the primary application database.
- Keep secrets out of Git.
- Maintain reproducible local development.
- Keep CI green before moving forward.
