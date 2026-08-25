# Enterprise Agentic AI Platform — Project Plan

Internal engineering roadmap and sprint status for the **Enterprise Agentic AI
Platform**. Portfolio-facing narrative lives in [`README.md`](../README.md).
Deep technical notes live in [`architecture.md`](architecture.md) and the
deployment runbook [`phase-8b-runbook.md`](phase-8b-runbook.md).

**Status legend**

| Mark | Meaning |
|------|---------|
| COMPLETE | Implemented and verified |
| IN PROGRESS | Partially done / remaining work listed |
| PLANNED | Not started or not yet productionized |

**Current progress:** Sprints 0–8 COMPLETE · Sprints 9–11 PLANNED

**Next focus (post–Sprint 8):** (1) demo video / screenshots / portfolio polish,
(2) Sprint 9 multimodal later, (3) Sprint 10 portfolio/evidence polish as
appropriate, (4) Sprint 11 repository/code-review intelligence agent.

---

# Sprint 0 — Repository & Architecture Foundation

**Status: COMPLETE**

- Monorepo with Python 3.12 + `uv`, FastAPI, Pydantic Settings
- Docker Compose: PostgreSQL, Redis, Qdrant
- Async SQLAlchemy 2 + Alembic + tenant/user models and APIs
- `/health`, `/ready`, Ruff, pytest, GitHub Actions CI
- Initial architecture documentation

---

# Sprint 1 — Enterprise Knowledge Ingestion & RAG v1

**Status: COMPLETE**

- Tenant-scoped documents (PostgreSQL metadata + local file storage)
- Parse (TXT/PDF) → chunk → Azure OpenAI dense embeddings → Qdrant
- Dense retrieval with `tenant_id` payload filtering
- Document status lifecycle and retrieval/RAG APIs

---

# Sprint 2 — Advanced RAG & Retrieval Evaluation

**Status: COMPLETE**

- Sparse BM25 vectors + dense/sparse hybrid weighted RRF
- Cross-encoder reranking + hybrid/reranker fusion
- Multi-query / query-rewrite Advanced retrieval mode
- Retrieval golden set + Recall@K / MRR / nDCG@K results under `evals/`

**Note:** both Standard and Advanced use hybrid retrieval + reranking; Advanced
adds multi-query expansion/fusion.

---

# Sprint 3 — LangGraph Agent Orchestration

**Status: COMPLETE**

- Router graph: `knowledge` / `sql` / `tool` / `unsupported`
- RAG node, finalize, fallback
- Agent API with thread-aware execution

---

# Sprint 4 — MCP & Enterprise Tool Integration

**Status: COMPLETE**

- MCP stdio server under `/mcp` packaged into backend image
- Tools: `get_asset_status`, `get_maintenance_history`, `create_maintenance_ticket`
- Read tools execute via MCP; write tools prepared for host interception / HITL

Demo/simulated tool data — not a live CMMS/ERP.

---

# Sprint 5 — SQL Agent + Security + HITL

**Status: COMPLETE**

- NL → SQL with SQLGlot validation, SELECT-only, allowed tables, tenant bind param
- Read-only SQL execution path
- HITL interrupt/resume for write tools; approved ticket persistence in PostgreSQL
- Operational models: assets, maintenance records, maintenance tickets

---

# Sprint 6 — Evaluation, Langfuse & Production Observability

**Status: COMPLETE**

- Langfuse tracing for LangGraph / nested LLM calls
- 24-case agent golden dataset + evaluation runners
- Persisted agent and retrieval evaluation results

---

# Sprint 7 — React UI & Production UX

**Status: COMPLETE**

- React + TypeScript + Vite chat UI
- Retrieval mode selector, HITL approval card, route badges
- Frontend lint/build tooling

Later Sprint 8 work expanded this into the full **Enterprise Agentic AI
Playground** (Documents, Operations, Compare Runs, Evaluation, System Status,
Architecture).

---

# Sprint 8 — Azure Deployment, Public Playground & Production Hardening

**Status: COMPLETE**

**Goal achieved:** low-cost public cloud playground with production-oriented
packaging, demo tenants, cost controls, and full backend CI/CD.

## Final accomplishments

- Azure Container Apps (backend; `minReplicas=0`, `maxReplicas=1`)
- Azure Static Web Apps (frontend)
- Neon PostgreSQL (app data)
- Qdrant Cloud (vectors)
- Upstash Redis (RAG cache + rate / demo budget guards)
- Persistent LangGraph PostgreSQL checkpoints (`CHECKPOINT_BACKEND=postgres`,
  same Neon `DATABASE_URL`)
- Public multi-tenant playground (Atlas / Borealis / Helios demo tenants)
- Execution Trace / AI Inspector
- Compare Runs (Standard vs Advanced)
- Evaluation (persisted regression metrics)
- System Status (safe readiness view)
- Architecture / RAG Pipeline Explorer
- Public-demo cost controls (`PUBLIC_DEMO_MODE`, layered Redis limits, daily
  fail-closed budget, prompt length, compare/write limits)
- Frontend/backend performance optimization (client request cache, lazy routes,
  backend cold-start / readiness parallelism)
- GHCR immutable images (`:sha-<full-git-sha>` + `latest`)
- GitHub Actions full backend CD (`.github/workflows/backend-cd.yml`)
- Azure OIDC with no long-lived deployment secret (GitHub Environment
  `production`; immutable subject form)

## First production Backend CD run (verified end-to-end)

```text
validate
  → immutable GHCR SHA image
  → GitHub OIDC
  → Azure Container Apps revision
  → /health
  → /ready
```

OIDC federated credential uses GitHub’s **immutable** subject
(`repo:owner@OWNER_ID/repo@REPO_ID:environment:production`); see
`scripts/setup-azure-github-oidc.sh` and `docs/phase-8b-runbook.md`.

## Packaging & runtime (also delivered)

- Backend production Dockerfile (repo-root context, MCP included, CPU-only torch)
- Health/readiness probes; Redis soft dependency for ordinary cache/rate features
- Env split: `.env.development` / `.env.production` + explicit `uv run --env-file`
- Qdrant API key + Upstash `rediss://` support
- CI: Ruff lint/format, pytest, Docker build validation
- Ad-hoc GHCR publish: `backend-image.yml` (`workflow_dispatch` only)

## Cloud hosting & data plane

| Layer | Current |
|-------|---------|
| Frontend | Azure Static Web Apps |
| Backend | Azure Container Apps |
| PostgreSQL | Neon (app data + LangGraph checkpoints) |
| Vectors | Qdrant Cloud |
| Redis | Upstash |
| LLM / embeddings | Azure OpenAI / Azure AI Foundry |
| Observability | Langfuse |
| Registry | GitHub Container Registry (GHCR) |

## Known limitations (accepted; not Sprint 8 blockers)

- Seeded synthetic enterprise data; MCP demo/simulated tools
- Local/container filesystem document storage (Azure Blob optional later)
- ACA cold starts from `minReplicas=0` (accepted cost tradeoff)
- Cost controls reduce risk; they do not guarantee zero spend
- JWT / RBAC public product layer remains out of scope (future)

---

# Sprint 9 — Multimodal Manufacturing Use Case

**Status: PLANNED (later; do not start until portfolio polish priority allows)**

Examples only — do not treat as committed scope:

- Equipment / manual image understanding
- Visual maintenance evidence
- Multimodal retrieval grounded in tenant knowledge

---

# Sprint 10 — Portfolio Polish & Evidence

**Status: PLANNED (near-term after Sprint 8 close — demo video / screenshots first)**

- Screenshots and short demo video
- Architecture diagrams / RAG explorer evidence
- Benchmark evidence presentation
- CV / interview project bullets
- Documentation polish

---

# Sprint 11 — AI Code Review / Repository Intelligence Agent

**Status: PLANNED (optional future project)**

Examples only:

- Repository indexing and diff-aware analysis
- GitHub/GitLab review integrations
- Structured review comments and evaluation

---

# Overall Target Topology (current)

```text
Browser
  → Azure Static Web Apps (React/Vite)
  → Azure Container Apps (FastAPI + LangGraph + MCP)
       ├── Neon PostgreSQL (data + checkpoints)
       ├── Qdrant Cloud (vectors)
       ├── Upstash Redis (cache + limits)
       ├── Azure OpenAI / Foundry
       └── Langfuse

GitHub Actions → GHCR (immutable SHA image)
  → Azure OIDC (Environment: production) → ACA revision → smoke tests
GitHub Actions → Static Web Apps (frontend)
```

---

# Engineering Principles

- Do not mark planned functionality as implemented or deployed.
- Preserve tenant isolation at every data boundary.
- Prefer clear service boundaries over large route handlers.
- Measure retrieval and generation quality; keep eval datasets honest about size.
- Use human approval for sensitive tool actions.
- PostgreSQL is the relational source of truth; Qdrant is a retrieval index.
- Redis is short-lived cache/limits only — never primary state or checkpoints.
- Keep secrets out of Git; keep CI green before advancing.
