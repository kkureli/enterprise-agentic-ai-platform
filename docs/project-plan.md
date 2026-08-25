# Enterprise Agentic AI Platform — Project Plan

This document tracks the implementation roadmap for the **Enterprise Agentic AI Platform**.

The project is intentionally built in incremental sprints. A capability is only marked as complete after it is implemented and verified locally.

**Current progress:** Sprint 0 ✅ · Sprint 1 ✅ · Sprint 2 ✅ · Sprint 3 ✅ · Sprint 4 ✅ · Sprint 5 ✅ · Sprint 6 ✅ · Sprint 7 ✅ · Sprint 8 🟡 Phase 8A packaging · Sprint 9+ ⬜ planned

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
HITL and conversation memory remain planned for later sprints. Langfuse tracing
was added in Sprint 6.

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
retries/persistence, or Langfuse tracing (Sprint 6).

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
| `create_maintenance_ticket` | Create a maintenance ticket | Sprint 4: simulated / non-persisting. **Sprint 5:** host intercepts write tools, requires HITL, then persists to PostgreSQL (MCP cannot bypass approval) |

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

## 4.5 Graph at end of Sprint 4

```text
START
  ↓
LLM Router
  ├── knowledge → RAG Node → Finalize → END
  ├── tool → MCP Tool Node → Finalize → END
  └── unsupported → Fallback → END
```

Sprint 5 extends this with `sql`, HITL approval, and approved-action persistence.
See Sprint 5 for the current graph.

## 4.6 Agent API

- ✅ `POST /api/v1/tenants/{tenant_id}/agent` supports the `tool` route
- ✅ Response continues to return `{ route, answer }` (Sprint 5 adds `thread_id`, `status`, `pending_action`)

## 4.7 Tests

- ✅ Tests green at Sprint 4 close (later Sprint 5 suite: 21 passing)

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
Agent API returns route + answer for tool requests; tests remain green
```

**Not in Sprint 4 (delivered in Sprint 5 or still planned):** real write
persistence + HITL, SQL agent & SQLGlot security, JWT/RBAC, production
checkpoint storage, cloud deployment (Langfuse delivered in Sprint 6).

---

# Sprint 5 — SQL Agent, Security & Human-in-the-Loop

**Status: ✅ Completed**

**Goal:** Introduce controlled structured data access (NL → SQL), SQL validation
and tenant isolation, real maintenance-ticket persistence, and human approval
for write actions. Production deployment and persistent checkpoint storage are
**not** claimed as complete.

## 5.1 Operational PostgreSQL Models

- ✅ Alembic migration for operational maintenance tables
- ✅ Tenant-scoped SQLAlchemy models:
  - `assets` — `asset_code`, name, location, status, `active_error_code`
  - `maintenance_records` — dated history rows linked to assets
  - `maintenance_tickets` — issue / priority / status tickets linked to assets
- ✅ Seed script for local operational demo data (`scripts/seed_operational_data.py`)

```text
Tenant
 ├── Users
 ├── Documents / Vector Chunks
 └── Operational data
      ├── Assets
      ├── Maintenance Records
      └── Maintenance Tickets
```

## 5.2 Natural Language → SQL Pipeline

- ✅ `sql` LangGraph route + `sql_node`
- ✅ LLM SQL generation (`sql_generation_service`) — structured SELECT only
- ✅ SQLGlot validation (`validate_readonly_sql`) before execution
- ✅ Read-only execution with row limit (`execute_readonly_sql`)
- ✅ PostgreSQL `SET TRANSACTION READ ONLY` on the execution session
- ✅ Result → LLM natural-language answer (`sql_agent_service`)

Pipeline:

```text
User question
  ↓
generate_sql()  (LLM, structured SELECT)
  ↓
validate_readonly_sql()  (SQLGlot)
  ↓
SET TRANSACTION READ ONLY + execute with :tenant_id / LIMIT
  ↓
LLM answer grounded on returned rows
```

SQL security controls (application + DB):

- Exactly one statement; SELECT only
- Allowed tables only: `assets`, `maintenance_records`, `maintenance_tickets`
- Required `WHERE` with `:tenant_id` bind parameter (no hardcoded tenant UUIDs)
- Single-table and join queries must be tenant-scoped per table/alias
- `OR` in `WHERE` disallowed for tenant-scope bypass prevention
- Outer `LIMIT` applied by the host
- PostgreSQL read-only transaction as a second enforcement layer

## 5.3 Human-in-the-Loop Write Actions

- ✅ Write tools (e.g. `create_maintenance_ticket`) are **intercepted by the host**
  in `mcp_tool_node` — they are **not** executed via MCP `call_tool`
- ✅ MCP server write tool raises if invoked directly; approval cannot be bypassed
  through the MCP path
- ✅ Pending action stored in graph state; graph pauses with LangGraph `interrupt`
- ✅ Resume via `Command(resume={"approved": true|false})` and `thread_id` config
- ✅ Checkpointer: **`InMemorySaver` (development only)** — must be replaced with
  persistent checkpoint storage before production use
- ✅ Approval API: `POST /api/v1/tenants/{tenant_id}/agent/{thread_id}/approval`
- ✅ On approve → `approved_action_node` → `create_maintenance_ticket` persists to PostgreSQL
- ✅ On reject → controlled rejection message; no write

HITL flow:

```text
tool route → MCP Tool Node selects create_maintenance_ticket
  ↓
Host intercepts (requires_approval + pending_action)
  ↓
approval node → interrupt(...)
  ↓
API returns status=approval_required + thread_id + pending_action
  ↓
POST .../agent/{thread_id}/approval  { "approved": true|false }
  ↓
Command(resume=...) restores checkpointed thread
  ├── approved → approved_action → PostgreSQL ticket insert → finalize
  └── rejected → finalize with rejection message
```

## 5.4 Current Graph

```text
START
  ↓
LLM Router
  ├── knowledge → RAG Node → Finalize → END
  ├── sql → SQL Node → Finalize → END
  ├── tool → MCP Tool Node
  │            ├── (read tool) → Finalize → END
  │            └── (write tool) → Approval
  │                                 ├── approved → Approved Action → Finalize → END
  │                                 └── rejected → Finalize → END
  └── unsupported → Fallback → END
```

## 5.5 Agent API (Sprint 5)

- ✅ `POST /api/v1/tenants/{tenant_id}/agent`
  - returns `thread_id`, `status` (`completed` | `approval_required`), `route`, `answer`
  - optional `pending_action` when approval is required
- ✅ `POST /api/v1/tenants/{tenant_id}/agent/{thread_id}/approval`
  - body: `{ "approved": boolean }`
  - resumes the checkpointed graph; tenant must match the paused execution

## 5.6 Tests

- ✅ 21 tests currently pass (`cd backend && uv run pytest -q`)

## Sprint 5 Definition of Done

Sprint 5 is complete when:

```text
Operational models exist in PostgreSQL (assets / records / tickets)
        ↓
NL → SQL → SQLGlot validation → read-only tenant-scoped execution → answer
        ↓
sql route is wired in LangGraph
        ↓
Write MCP tools are host-intercepted and cannot bypass HITL
        ↓
interrupt + Command(resume) + thread_id approval API works
        ↓
Approved create_maintenance_ticket persists to PostgreSQL
        ↓
InMemorySaver documented as dev-only (not production-ready)
```

**Not in Sprint 5 (delivered in Sprint 6 or still planned):** Langfuse observability
(Sprint 6), JWT authentication, RBAC, Redis/Postgres persistent checkpointer for
production, cloud deployment, React approval UI, or real external enterprise APIs
beyond the local PostgreSQL + MCP demo.

---

# Sprint 6 — Evaluation, Reliability & Observability

**Status: ✅ Completed**

**Goal:** Make the agent system measurable and debuggable with Langfuse tracing
and a reproducible agent evaluation suite. Production deployment, OpenTelemetry,
and CI-enforced regression gates remain planned.

## 6.1 Langfuse Integration

- ✅ LangGraph tracing via `langfuse.langchain.CallbackHandler` on agent API runs
- ✅ Nested LLM tracing (router, RAG, SQL generation, SQL answer, MCP tool selection, final answer)
- ✅ Approval resume runs traced separately (`enterprise-agent-approval`)
- ✅ Evaluation runs traced with Langfuse callbacks and `get_client().flush()`

Trace metadata attached to runs:

- `tenant_id`
- `thread_id`
- `retrieval_mode` (initial agent request)
- `approval` (approve / reject decision on resume)

Langfuse automatically captures per-span **latency**, **token usage**, **model**,
and **cost** for nested LLM calls.

## 6.2 Failure Visibility

Failures across agent paths are visible in Langfuse traces, including:

- SQL guardrail rejections (`UnsafeSQLQueryError` from SQLGlot validation)
- LLM / graph execution errors
- MCP / tool execution failures
- HITL interrupt and approval resume flows

This supports debugging route selection, SQL validation, tool execution, and
approval workflows without relying only on API error responses.

## 6.3 Agent Golden Dataset

- ✅ 24-case golden dataset: `evals/agent/golden_dataset.json`
- ✅ Coverage:
  - 6 knowledge (RAG)
  - 6 SQL (structured PostgreSQL queries)
  - 6 MCP/tool (2 read tools + 4 HITL write actions)
  - 6 unsupported

Each case specifies `expected_route` and `expected_approval`.

## 6.4 Evaluation Runners

- ✅ Router-only evaluation: `evals/agent/run_router_evaluation.py`
  - measures route classification accuracy against the golden set
- ✅ End-to-end agent evaluation: `evals/agent/run_agent_evaluation.py`
  - invokes the full compiled LangGraph graph per case
  - checks route, approval interrupt behavior, and answer presence
  - persists results to `evals/results/agent_evaluation.json`
  - emits Langfuse traces per case

## 6.5 Current Benchmark (regression artifact)

From the latest local run on the 24-case golden dataset:

| Metric | Result |
|--------|--------|
| Route accuracy | 24/24 (100%) |
| Approval accuracy | 24/24 (100%) |
| Execution success | 24/24 (100%) |
| End-to-end pass rate | 24/24 (100%) |

> **Important:** These are **regression results on a small 24-case golden dataset**.
> They demonstrate local reproducibility and route/approval correctness — they are
> **not** production-wide accuracy or reliability claims.

## 6.6 Checkpointer Status

- ✅ LangGraph still uses **`InMemorySaver`** for development checkpoints
- ⬜ Persistent checkpoint storage for production (Postgres / Redis) remains planned

## Sprint 6 Definition of Done

Sprint 6 is complete when:

```text
Langfuse traces LangGraph runs and nested LLM calls
        ↓
Trace metadata includes tenant_id, thread_id, retrieval_mode, approval
        ↓
24-case agent golden dataset exists (knowledge / sql / tool / unsupported)
        ↓
Router and end-to-end agent evaluation runners produce persisted results
        ↓
Failures across SQL, LLM, MCP, and HITL paths are visible in Langfuse
        ↓
InMemorySaver remains documented as dev-only
```

**Not in Sprint 6 (still planned):** OpenTelemetry, CI-enforced regression
gates, model comparison, prompt/version tracking, RAG answer evaluation beyond
retrieval metrics, persistent production checkpointer, JWT/RBAC, cloud
deployment, or React approval UI.

---

# Sprint 7 — React UI & Production UX

**Status: ✅ Completed**

**Goal:** Provide a usable React chat interface for the existing FastAPI +
LangGraph agent backend, including HITL approval UX.

## 7.1 React Frontend

- ✅ React + TypeScript + Vite under `/frontend`
- ✅ Typed API client for agent and approval endpoints
- ✅ Centralized API config (`VITE_API_BASE_URL`, `VITE_TENANT_ID`)
- ✅ Development CORS for `http://localhost:5173` and `http://127.0.0.1:5173`

## 7.2 Enterprise Chat UI

- ✅ Conversation area with user/assistant messages
- ✅ Composer with send button, loading state, and empty-state example prompts
- ✅ Route/capability badges (Knowledge / Data / Tool / Unsupported)
- ✅ Standard / Advanced retrieval mode selector
- ✅ Collapsible Details panel (route, retrieval mode, thread ID)
- ✅ Error and loading UX for API/network failures

## 7.3 HITL Approval Card

- ✅ Inline approval card when `status === "approval_required"`
- ✅ Human-readable fields for `create_maintenance_ticket` (asset, issue, priority)
- ✅ Approve → `POST .../approval { approved: true }`
- ✅ Reject → `POST .../approval { approved: false }`
- ✅ No direct write execution from frontend
- ✅ No optimistic "ticket created" before approval API succeeds

## 7.4 Known Sprint 7 Limitations

- ⬜ Chat history is **frontend in-memory only** (lost on refresh)
- ⬜ Agent API does not expose RAG citations/sources — no fake citation UI added
- ⬜ No JWT/RBAC auth UI
- ⬜ No document upload UI (deferred)
- ⬜ No streaming responses
- ⬜ Screenshots not committed (capture locally for portfolio)

## Sprint 7 Definition of Done

Sprint 7 is complete when:

```text
React chat UI runs against local FastAPI backend
        ↓
User can send questions and see route + answer
        ↓
Retrieval mode selector maps to backend retrieval_mode
        ↓
Write requests show approval card and approve/reject via backend API
        ↓
Frontend build/lint pass; backend regression tests remain green
```

**Not in Sprint 7 (still planned):** Azure deployment, persistent chat history,
auth, document management UI, citation surfacing, production CORS policy.

---

# Sprint 8 — Azure Deployment & CI/CD

**Status: 🟡 In progress (Phase 8A complete — packaging only)**

**Goal:** Move the system from local Docker development to cloud deployment.

Sprint 8 is split into phases. **Phase 8A** prepares production packaging
without provisioning or deploying Azure resources. **Phase 8B** (manual /
follow-up) will finalize Azure architecture and actual deployment.

## Phase 8A — Production Packaging & Deployment Foundation ✅

- ✅ Backend production `Dockerfile` (Python 3.12 + uv + uvicorn)
- ✅ Build context is **repository root** so MCP is packaged in the same image
- ✅ Linux production deps resolve **CPU-only PyTorch** (no CUDA/NVIDIA wheels)
- ✅ Root `.dockerignore` (excludes secrets, venvs, frontend, caches, tests)
- ✅ Environment-driven config for container runtime (CORS, DB, Redis,
  Qdrant, Azure OpenAI, Langfuse, optional `MCP_SERVER_DIR`)
- ✅ Health (`/health`) and readiness (`/ready`) remain cloud-compatible
  - liveness: process alive (does **not** require Azure OpenAI or Langfuse)
  - readiness: PostgreSQL + Qdrant hard; Redis soft/degraded (RAG cache +
    agent rate limiting fail open)
- ✅ Redis used for tenant-aware RAG response caching and agent rate limiting
  (not application state / checkpoints)
- ✅ Frontend production API base URL via `VITE_API_BASE_URL` (Vite build-time)
- ✅ CI container **build-only** validation (no push, no Azure credentials)
- ⬜ FastAPI backend / React frontend not yet deployed to Azure
- ⬜ No new application-hosting Azure resources provisioned in Phase 8A
  (existing Azure AI Foundry, Application Insights, and Log Analytics remain
  in use for model/observability work)

## Phase 8B — Azure Provisioning & Deployment (planned / preparation started)

**Cost constraint:** target fixed monthly infrastructure cost ≈ **$0** for this
portfolio/demo project. Prefer free tiers / scale-to-zero. Avoid AKS, GPU,
always-on compute, paid Azure PostgreSQL, Azure Managed Redis, premium
networking, and duplicate monitoring.

Intended low-cost direction (**not provisioned yet**):

```text
Frontend         → Azure Static Web Apps Free
Backend          → Azure Container Apps Consumption (minReplicas = 0)
Embeddings / LLM → existing Azure AI Foundry / Azure OpenAI
Observability    → existing Langfuse + Application Insights / Log Analytics
PostgreSQL       → Neon Free (application data + LangGraph checkpoints)
Qdrant           → Qdrant Cloud Free
Redis            → Upstash Redis Free (rediss://) — RAG cache + rate limiting
Document files   → local path for now; Azure Blob later
```

Preparation completed in-repo (no cloud accounts created):

- ✅ Env placeholders for Neon / Qdrant API key / Upstash `rediss://` / CORS
- ✅ Split env model: `.env.development` vs `.env.production` (gitignored);
  explicit `uv run --env-file ...` (no silent shared `.env` auto-load)
- ✅ `CHECKPOINT_BACKEND=memory|postgres` (Postgres uses same `DATABASE_URL`)
- ✅ Qdrant client supports optional `QDRANT_API_KEY`
- ✅ Redis client accepts TLS URLs (`rediss://`) via `Redis.from_url`
- ✅ SWA SPA config: `frontend/public/staticwebapp.config.json`
- ✅ Runbook: `docs/phase-8b-runbook.md`

Still planned (manual):

- ⬜ Create Neon / Qdrant Cloud / Upstash free resources
- ⬜ Application hosting (Static Web Apps / Container Apps)
- ⬜ Secret management in Azure
- ⬜ `uv run --env-file .env.production alembic upgrade head` against Neon
- ⬜ Deploy Container Apps (`minReplicas=0`) + Static Web Apps
- ⬜ Wire production `VITE_API_BASE_URL` at frontend build time
- ⬜ Persistent document storage (Azure Blob)
- ⬜ Enable deploy workflow only after credentials exist

**Sprint 8 is not complete** until Phase 8B deployment work is finished.

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
- ✅ Agent evaluation results (`evals/results/agent_evaluation.json`)
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

The diagram below is the long-term target. Sprints 3–7 implement a router-based
LangGraph backend with Langfuse tracing, agent evaluation, and a React chat UI.
Persistent production checkpoints, JWT/RBAC, application-wide OpenTelemetry, and
cloud deployment remain planned.

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
