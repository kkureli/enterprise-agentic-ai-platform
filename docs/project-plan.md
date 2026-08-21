# Enterprise Agentic AI Platform — Project Plan

This document tracks the implementation roadmap for the **Enterprise Agentic AI Platform**.

The project is intentionally built in incremental sprints. A capability is only marked as complete after it is implemented and verified locally.

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

- 🟡 Azure OpenAI chat model deployment
- ⬜ RAG service
- ⬜ Retrieve relevant chunks
- ⬜ Construct grounded context
- ⬜ System prompt
- ⬜ Generate answer from retrieved context
- ⬜ Refuse / qualify when context is insufficient

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

- ⬜ Return source metadata with each answer
- ⬜ `document_id`
- ⬜ `filename`
- ⬜ `chunk_index`
- ⬜ Retrieval score where useful

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

- ⬜ Tenant A must never retrieve Tenant B chunks
- ⬜ Invalid documents must fail safely
- ⬜ Retrieval must return relevant results
- ⬜ RAG response must include sources
- ⬜ CI must remain green

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

**Goal:** Upgrade basic dense RAG into a measurable production retrieval system.

## Retrieval

- ⬜ Sparse / lexical retrieval
- ⬜ Dense + sparse hybrid retrieval
- ⬜ Reciprocal Rank Fusion (RRF)
- ⬜ Cross-encoder reranking
- ⬜ Retrieval configuration tuning
- ⬜ Metadata filtering improvements

Target architecture:

```text
                   Query
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
     Dense Retrieval     Sparse Retrieval
           │                   │
           └─────────┬─────────┘
                     ▼
                    RRF
                     ↓
                  Reranker
                     ↓
                   Top-K
```

## Evaluation

- ⬜ Golden retrieval dataset
- ⬜ Recall@K
- ⬜ MRR
- ⬜ nDCG
- ⬜ Compare dense vs hybrid
- ⬜ Compare hybrid vs hybrid + reranker
- ⬜ Retrieval regression checks

---

# Sprint 3 — LangGraph Agent Orchestration

**Goal:** Move from single RAG calls to stateful agent workflows.

- ⬜ LangGraph integration
- ⬜ Agent state definition
- ⬜ Planning / routing
- ⬜ Tool selection
- ⬜ Retrieval node
- ⬜ Decision nodes
- ⬜ Error handling
- ⬜ Retry paths
- ⬜ Multi-step workflows
- ⬜ Agent state persistence foundation

Target:

```text
User Request
    ↓
LangGraph
    ↓
Intent / Decision
    ├── RAG
    ├── SQL
    ├── Tool
    └── Human Approval
```

---

# Sprint 4 — MCP & Enterprise Tool Integration

**Goal:** Allow agents to interact with external enterprise systems through controlled tools.

- ⬜ MCP server foundation
- ⬜ Tool discovery
- ⬜ Tool schemas
- ⬜ Enterprise API tools
- ⬜ CRM/ticket-style demo tools
- ⬜ Tool input validation
- ⬜ Tool output normalization
- ⬜ Tenant-aware tool access

---

# Sprint 5 — SQL Agent, Security & Human-in-the-Loop

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

## Human-in-the-Loop

- ⬜ Pause before sensitive actions
- ⬜ Human approval
- ⬜ Resume workflow
- ⬜ Redis-backed transient workflow state

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

- ⬜ Architecture diagrams
- ⬜ Updated README
- ⬜ Demo screenshots
- ⬜ Demo video
- ⬜ Performance evidence
- ⬜ Retrieval evaluation results
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
