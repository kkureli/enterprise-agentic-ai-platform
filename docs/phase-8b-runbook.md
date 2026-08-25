# Phase 8B — Low-Cost Cloud Deployment Runbook

**Status:** primary hosting, data plane, and **Backend Full CD** are in use for
the public playground (Azure Container Apps, Static Web Apps, Neon, Qdrant Cloud,
Upstash). First successful production Backend CD run completed:

`validate → GHCR → Azure OIDC → ACA revision → /health → /ready`.

This runbook remains the operational reference for env vars, cost controls,
migrations, OIDC subject format, and rollback.

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

### Firebase Analytics (optional)

Purpose: basic anonymous portfolio traffic measurement (visits, daily/monthly
traffic, approximate geo, standard GA4 active-user metrics).

The playground intentionally does **not** track AI prompts, responses, SQL,
documents, execution traces, tenant IDs, or other application content. Only
standard Firebase / GA4 website telemetry is enabled, and only in production
builds (`import.meta.env.PROD`) when all `VITE_FIREBASE_*` values are present.

Set these GitHub Actions repository/environment **variables** (same style as
`VITE_API_BASE_URL`) so the SWA workflow can embed them at build time:

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MEASUREMENT_ID`

Missing values skip Analytics initialization; the UI still loads normally.

Do **not** assume Azure / Neon / Qdrant / Upstash credentials are absent — the
public playground stack is already wired. Frontend deploys via Static Web Apps.
Backend production CD is live via `.github/workflows/backend-cd.yml`
(validate → GHCR → OIDC → ACA → smoke tests).

## Backend CD (GitHub Actions → GHCR → Azure OIDC → ACA)

### Pipeline

```text
push master (backend/** | mcp/** | workflow)
  → validate (ruff + pytest)
  → build/push immutable GHCR image :sha-<full-git-sha>
  → Azure login via OIDC (GitHub Environment: production)
  → az containerapp update --image <sha tag>  (existing app only)
  → smoke GET /health then GET /ready (bounded cold-start wait)
```

Concurrency group `backend-production` with `cancel-in-progress: false` prevents
overlapping ACA updates.

`backend-image.yml` is **workflow_dispatch only** (ad-hoc GHCR publish). It no
longer pushes on `master`, so it cannot race Backend CD.

### GitHub Environment `production` variables

Non-secret identifiers only (no Azure client secret):

| Variable | Example / notes |
|----------|-----------------|
| `AZURE_CLIENT_ID` | Entra app (federated) application (client) ID |
| `AZURE_TENANT_ID` | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID |
| `AZURE_RESOURCE_GROUP` | `rg-enterprise-agentic-ai` |
| `AZURE_CONTAINER_APP` | `enterprise-agentic-ai-backend` |
| `AZURE_CONTAINER_APP_URL` | `https://enterprise-agentic-ai-backend.jollyplant-fb706637.swedencentral.azurecontainerapps.io` |

Create/update via `scripts/setup-azure-github-oidc.sh` or:

```bash
gh variable set AZURE_CLIENT_ID --env production --body "<appId>"
# …same for the other variables above
```

### One-time Azure federated identity

GitHub Actions presents an **immutable** OIDC `sub` that includes numeric owner
and repository IDs (not the legacy name-only form).

Observed production subject shape:

```text
repo:<owner>@<OWNER_ID>/<repo>@<REPO_ID>:environment:production
```

Example pattern (IDs resolved dynamically — do not hardcode):

```text
repo:kkureli@<OWNER_ID>/enterprise-agentic-ai-platform@<REPO_ID>:environment:production
```

Resolve IDs with:

```bash
gh api repos/kkureli/enterprise-agentic-ai-platform --jq '{owner_id: .owner.id, repo_id: .id}'
```

Issuer / audience (unchanged):

```text
issuer:   https://token.actions.githubusercontent.com
audience: api://AzureADTokenExchange
```

Legacy name-only subjects such as:

```text
repo:kkureli/enterprise-agentic-ai-platform:environment:production
```

do **not** match GitHub’s token and fail Entra token exchange with **AADSTS700213**.

`scripts/setup-azure-github-oidc.sh` builds the immutable subject from `gh api`,
creates or **updates** the federated credential when the subject differs, and
does not create duplicates on re-run.

Least-privilege role:

- **Role:** `Container Apps Contributor`
- **Scope:** the existing Container App resource only
  `/subscriptions/<sub>/resourceGroups/rg-enterprise-agentic-ai/providers/Microsoft.App/containerApps/enterprise-agentic-ai-backend`

Do **not** grant Owner or subscription-wide Contributor.

Inspect then run (local Azure CLI + `gh`):

```bash
./scripts/setup-azure-github-oidc.sh
```

CD updates **only** the image reference. It does not recreate the app,
environment, ingress, scaling, or application secrets. Existing GHCR pull
configuration on the Container App is left untouched.

### Smoke tests

After `az containerapp update`:

1. `GET /health` — HTTP 200, retries ~every 5s up to ~120s (cold start)
2. `GET /ready` — HTTP 200 (Postgres + Qdrant hard deps)

On failure the workflow fails and prints non-secret revision diagnostics.

### Manual rollback

Redeploy a previous immutable tag (do not invent tags):

```bash
az containerapp update \
  --name enterprise-agentic-ai-backend \
  --resource-group rg-enterprise-agentic-ai \
  --image ghcr.io/kkureli/enterprise-agentic-ai-platform-backend:sha-<PREVIOUS_FULL_GIT_SHA>
```

## Document storage

Container-local `DOCUMENT_STORAGE_PATH` is not durable. Prefer Azure Blob in a
later hardening step; not required to start the first free-tier demo deploy.
