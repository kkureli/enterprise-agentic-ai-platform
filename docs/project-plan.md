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

**Current progress:** Sprints 0–7 COMPLETE · Sprint 8 IN PROGRESS (cloud
playground largely live; backend ACA CD + final polish remaining) ·
Sprints 9–11 PLANNED

**Priority shift:** core platform feature scope is largely sufficient. Focus on
(1) deployment reliability, (2) backend full CD automation, (3) architecture /
docs polish, (4) demo evidence, (5) only then optional new AI use cases.

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

**Status: IN PROGRESS**

**Goal:** low-cost cloud playground with production-oriented packaging, demo
tenants, cost controls, and CI/CD.

## COMPLETE — packaging & runtime

- Backend production Dockerfile (repo-root context, MCP included, CPU-only torch)
- Health/readiness probes; Redis soft dependency for ordinary cache/rate features
- Env split: `.env.development` / `.env.production` + explicit `uv run --env-file`
- `CHECKPOINT_BACKEND=memory|postgres` (Postgres = same `DATABASE_URL` / Neon)
- Qdrant API key + Upstash `rediss://` support
- GHCR image publish workflow (`latest` + immutable SHA tags)
- CI: Ruff lint/format, pytest (~56 tests), Docker build validation
- Azure Static Web Apps deploy workflow for the frontend

## COMPLETE — cloud hosting & data plane (provisioned / in use)

| Layer | Current |
|-------|---------|
| Frontend | Azure Static Web Apps |
| Backend | Azure Container Apps (`minReplicas=0`, `maxReplicas=1`) |
| PostgreSQL | Neon (app data + LangGraph checkpoints) |
| Vectors | Qdrant Cloud |
| Redis | Upstash (RAG cache + rate / demo budget guards) |
| LLM / embeddings | Azure OpenAI / Azure AI Foundry |
| Observability | Langfuse |
| Registry | GitHub Container Registry (GHCR) |

## COMPLETE — playground & demo product surface

- Three demo tenants: Atlas Manufacturing, Borealis Cold Chain, Helios Energy Services
- Seed script `scripts/seed_demo_playground.py` + demo APIs
- E-100 tenant-isolation demo (live retrieval, not frontend hardcoding)
- Playground pages: Playground, Documents, Operations, Compare Runs, Evaluation,
  System Status, Architecture
- Execution Trace / AI Inspector (curated operational metadata only)
- Standard vs Advanced Compare Runs
- Public-demo cost controls (`PUBLIC_DEMO_MODE`, layered Redis limits, daily
  fail-closed budget, prompt length, compare/write limits)

## IN PROGRESS / remaining Sprint 8 work

| Item | Status |
|------|--------|
| Backend full CD: GHCR → Azure OIDC → Container Apps revision | **COMPLETE** (first production run: validate → GHCR → OIDC → ACA → /health → /ready) |
| Commit + SWA deploy of latest local frontend UX polish (cold-start tenant loading states, retrieval-mode education, Architecture RAG Pipeline Explorer) | PENDING (present in local working tree; not claimed live) |
| Final production smoke test after frontend polish lands | PENDING |
| README / architecture / runbook accuracy pass | IN PROGRESS |
| Durable document object storage (Azure Blob) | PLANNED (optional) |
| JWT / RBAC public product layer | OUT OF SCOPE for Sprint 8 (future) |

**Important CI/CD truth**

- Frontend: push/PR workflows can deploy Static Web Apps
- Backend CD workflow (`.github/workflows/backend-cd.yml`):
  validate → GHCR `:sha-<git-sha>` → Azure OIDC → ACA image update → smoke tests
- Backend Full CD is **COMPLETE** after a successful production run
- OIDC federated credential must use GitHub’s **immutable** subject
  (`repo:owner@OWNER_ID/repo@REPO_ID:environment:production`); see
  `scripts/setup-azure-github-oidc.sh` and `docs/phase-8b-runbook.md`
- Ad-hoc GHCR publish: `backend-image.yml` (`workflow_dispatch` only)

## Known Sprint 8 limitations (still true)

- Seeded synthetic enterprise data
- MCP demo/simulated tools
- Local/container filesystem document storage (not Blob)
- ACA cold starts from `minReplicas=0` (accepted cost tradeoff; no keep-alive)
- Playground warm navigation uses client-side request caching; Architecture /
  Evaluation / Status do not wait on tenant APIs
- Cost controls reduce risk; they do not guarantee zero spend

---

# Sprint 9 — Multimodal Manufacturing Use Case

**Status: PLANNED (optional)**

Examples only — do not treat as committed scope:

- Equipment / manual image understanding
- Visual maintenance evidence
- Multimodal retrieval grounded in tenant knowledge

---

# Sprint 10 — Portfolio Polish & Evidence

**Status: PLANNED / partially overlapping Sprint 8 polish**

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
