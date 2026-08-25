from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Agentic AI Platform"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_ai"
    redis_url: str = "redis://localhost:6379"
    redis_enabled: bool = True
    rag_cache_ttl_seconds: int = 300
    agent_rate_limit_requests: int = 30
    agent_rate_limit_window_seconds: int = 60
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # memory (default local) | postgres (Neon / production — same DATABASE_URL)
    checkpoint_backend: Literal["memory", "postgres"] = "memory"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None

    # Load from process environment only (explicit selection via
    # `uv run --env-file .env.development|production ...` or Container Apps).
    # Do not auto-load a shared .env file.
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    document_storage_path: str = "storage/documents"
    max_upload_size_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 150
    dense_retrieval_weight: float = 0.7
    sparse_retrieval_weight: float = 0.3
    dense_identifier_weight: float = 0.5
    sparse_identifier_weight: float = 0.5
    rrf_k: int = 60
    hybrid_rank_weight: float = 0.7
    reranker_rank_weight: float = 0.3
    final_rrf_k: int = 60
    multi_query_rrf_k: int = 60
    original_query_weight: float = 1.0
    expanded_query_weight: float = 0.7
    query_expansion_max_count: int = 3
    retrieval_candidate_multiplier: int = 2
    retrieval_candidate_min: int = 10

    qdrant_collection_name: str = "document_chunks_v2"

    azure_openai_embedding_deployment: str | None = None
    azure_openai_api_version: str = "2024-02-01"

    # Optional override for container deployments. Defaults to monorepo ../mcp
    # or /app/mcp when packaged in the production image.
    mcp_server_dir: str | None = None

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
