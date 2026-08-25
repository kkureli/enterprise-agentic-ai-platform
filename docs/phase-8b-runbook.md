# Phase 8B — Low-Cost Cloud Deployment Runbook

**Status:** preparation only. None of the new hosting/data resources below have
been provisioned or deployed yet.

Target fixed monthly infrastructure cost ≈ **$0**.

## Target architecture

| Concern | Target |
|---------|--------|
| React frontend | Azure Static Web Apps Free |
| FastAPI / LangGraph | Azure Container Apps Consumption (`minReplicas=0`) |
| PostgreSQL | Neon Free |
| LangGraph HITL checkpoints | Same Neon DB (`CHECKPOINT_BACKEND=postgres`) |
| Vectors | Qdrant Cloud Free |
| Redis | Upstash Redis Free (`rediss://`) |
| LLM | Existing Azure AI Foundry / Azure OpenAI |
| Observability | Existing Langfuse + App Insights / Log Analytics |

Avoid: AKS, GPU, always-on compute, paid Azure PostgreSQL, Azure Managed Redis,
premium networking, unnecessary gateways.

## Environment file model

Do **not** mix local Docker URLs and cloud URLs in one file.

| File | Purpose | Git |
|------|---------|-----|
| `backend/.env.example` | Placeholders only | tracked |
| `backend/.env.development` | Local Docker Postgres / Redis / Qdrant | gitignored |
| `backend/.env.production` | Local testing against Neon / Qdrant Cloud / Upstash | gitignored |
| `frontend/.env.example` | Placeholders only | tracked |
| `frontend/.env.development` | `npm run dev` | gitignored |
| `frontend/.env.production` | `npm run build` / SWA | gitignored |

Backend settings read **process environment only**. Select explicitly:

```bash
cd backend
uv run --env-file .env.development uvicorn app.main:app --reload
uv run --env-file .env.production uvicorn app.main:app
```

Azure Container Apps injects the same keys as secrets/env vars. Do **not** bake
`.env.production` into the image.

**Qdrant rule:** each file may contain at most one `QDRANT_URL`. Development uses
`http://localhost:6333` with empty `QDRANT_API_KEY`. Production uses HTTPS cloud
URL + API key. Mixing both caused the insecure-connection API key error.

## Backend environment (Container Apps)

Inject as secrets / env vars (never commit real values):

```text
APP_ENV=production
DEBUG=false
PORT=8000
CHECKPOINT_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/neondb?ssl=require
REDIS_URL=rediss://default:TOKEN@HOST:6379
REDIS_ENABLED=true
RAG_CACHE_TTL_SECONDS=300
AGENT_RATE_LIMIT_REQUESTS=30
AGENT_RATE_LIMIT_WINDOW_SECONDS=60
PUBLIC_DEMO_MODE=true
CLIENT_RATE_LIMIT_REQUESTS=10
CLIENT_RATE_LIMIT_WINDOW_SECONDS=60
GLOBAL_AI_RATE_LIMIT_REQUESTS=100
GLOBAL_AI_RATE_LIMIT_WINDOW_SECONDS=3600
DEMO_DAILY_AI_REQUEST_LIMIT=500
MAX_AGENT_QUESTION_CHARS=2000
COMPARE_RATE_LIMIT_REQUESTS=3
COMPARE_RATE_LIMIT_WINDOW_SECONDS=300
DEMO_WRITE_RATE_LIMIT_REQUESTS=5
DEMO_WRITE_RATE_LIMIT_WINDOW_SECONDS=3600
QDRANT_URL=https://YOUR-CLUSTER.cloud.qdrant.io:6333
QDRANT_API_KEY=...
CORS_ORIGINS=["https://YOUR-APP.azurestaticapps.net"]
# When using uv --env-file locally, quote JSON lists so string quotes survive:
# CORS_ORIGINS='["https://YOUR-APP.azurestaticapps.net"]'
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=...
LANGFUSE_TRACING_ENVIRONMENT=production
MCP_SERVER_DIR=/app/mcp
```

Probes:

- Liveness: `GET /health`
- Readiness: `GET /ready` — PostgreSQL and Qdrant are hard dependencies; Redis
  is reported as a soft/degraded dependency for ordinary cache/rate features.
  When `PUBLIC_DEMO_MODE=true`, the hard daily AI budget **fails closed** if
  Redis cannot verify the counter.

Redis / Upstash is used for:

- Short-lived tenant-aware RAG response caching
- Per-tenant agent rate limiting
- Per-client (hashed IP) rate limiting
- Global hourly AI ceiling
- Hard daily demo AI request budget
- Compare Runs stricter limit
- Approved write-action rate limiting

Redis is **not** used for primary application data, LangGraph checkpoints,
maintenance tickets, or vector storage.

### Public demo cost-defense layers

Application-level controls reduce abuse and Azure OpenAI spend risk but are
**not** a substitute for Azure subscription budgets/alerts. Do not assume Azure
budget alerts hard-stop spend unless those alerts are actually configured.

1. RAG cache (repeated identical tenant-aware knowledge questions)
2. Per-client rate limit (`CLIENT_RATE_LIMIT_*`)
3. Per-tenant rate limit (`AGENT_RATE_LIMIT_*`)
4. Global hourly AI limit (`GLOBAL_AI_RATE_LIMIT_*`)
5. Hard daily request ceiling (`DEMO_DAILY_AI_REQUEST_LIMIT`, fail-closed in public demo)
6. Maximum prompt length (`MAX_AGENT_QUESTION_CHARS`)
7. Compare Runs stricter limit (`COMPARE_RATE_LIMIT_*`; each compare = 2 AI units)
8. Write-action rate limit on approved HITL writes (`DEMO_WRITE_RATE_LIMIT_*`)
9. Azure Container Apps `maxReplicas=1` (infra concurrency)
10. Azure Container Apps `minReplicas=0` (scale to zero)

A fragile Redis distributed semaphore was intentionally **not** added; rely on
global rate limits + single-replica Container Apps instead.

Container listens on **8000**.

## Neon migrations & seed (from local machine)

```bash
cd backend
uv run --env-file .env.production alembic upgrade head
PYTHONPATH=. uv run --env-file .env.production python scripts/seed_operational_data.py
```

Local Docker database:

```bash
cd backend
uv run --env-file .env.development alembic upgrade head
PYTHONPATH=. uv run --env-file .env.development python scripts/seed_operational_data.py
```

LangGraph checkpoint tables are created automatically on application startup
when `CHECKPOINT_BACKEND=postgres` via `AsyncPostgresSaver.setup()`.

## Frontend (Static Web Apps)

Vite mode files:

- `npm run dev` → `.env.development` (`VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`)
- `npm run build` → `.env.production` (set public ACA `/api/v1` URL before building)

```bash
cd frontend
# after setting VITE_API_BASE_URL in .env.production:
npm run build
```

`frontend/public/staticwebapp.config.json` provides SPA navigation fallback.

## Future Azure CLI sketch (do not run until accounts exist)

These commands are illustrative placeholders only:

```bash
# Build/push image to a registry you control, then:
az containerapp up \
  --name <app-name> \
  --resource-group <rg> \
  --environment <cae> \
  --image <registry>/enterprise-agentic-ai-backend:<tag> \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --cpu 1.0 \
  --memory 2.0Gi

# Static Web Apps (after GitHub connection / token exists):
# az staticwebapp create ...
```

Do **not** enable a deploy GitHub Action until Azure / Neon / Qdrant / Upstash
credentials exist; current CI remains lint/test + Docker build-only.

## Document storage

Container-local `DOCUMENT_STORAGE_PATH` is not durable. Prefer Azure Blob in a
later hardening step; not required to start the first free-tier demo deploy.
