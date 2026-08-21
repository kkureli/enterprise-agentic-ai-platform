from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Agentic AI Platform"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_ai"
    redis_url: str = "redis://localhost:6379"
    qdrant_url: str = "http://localhost:6333"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    document_storage_path: str = "storage/documents"
    max_upload_size_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 150

    qdrant_collection_name: str = "document_chunks"

    azure_openai_embedding_deployment: str | None = None
    azure_openai_api_version: str = "2024-02-01"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
