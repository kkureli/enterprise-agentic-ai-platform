from functools import lru_cache

from langchain_openai import AzureOpenAIEmbeddings

from app.core.config import settings


@lru_cache
def get_embedding_model() -> AzureOpenAIEmbeddings:
    if not settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured.")

    if not settings.azure_openai_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not configured.")

    if not settings.azure_openai_embedding_deployment:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT is not configured.")

    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_embedding_deployment,
        api_version=settings.azure_openai_api_version,
    )


async def embed_documents(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()

    return await model.aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    model = get_embedding_model()

    return await model.aembed_query(text)
