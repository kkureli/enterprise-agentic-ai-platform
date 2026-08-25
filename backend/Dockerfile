# syntax=docker/dockerfile:1

# Production backend image (Phase 8A packaging).
# Build from repository root so MCP is packaged in the same container:
#   docker build -f backend/Dockerfile -t enterprise-agentic-ai-backend .
#
# Do not bake secrets into the image. Pass runtime config via environment variables.

FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# --- Backend application ---
COPY backend/pyproject.toml backend/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/scripts ./scripts

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- MCP stdio server (same container) ---
WORKDIR /app/mcp

ENV UV_PROJECT_ENVIRONMENT=/app/mcp/.venv

COPY mcp/pyproject.toml mcp/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY mcp/server.py ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    APP_ENV=production \
    DEBUG=false \
    MCP_SERVER_DIR=/app/mcp \
    DOCUMENT_STORAGE_PATH=/app/storage/documents

# uv is required at runtime because the MCP client launches: uv run python server.py
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/storage/documents \
    && chown -R app:app /app

COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

# Liveness-compatible process bind. Dependency readiness is /ready.
# PORT is read by the shell / platform, not application Settings.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
