from functools import lru_cache

from langchain_openai import AzureChatOpenAI

from app.core.config import settings


@lru_cache
def get_chat_model() -> AzureChatOpenAI:
    if not settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured.")

    if not settings.azure_openai_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not configured.")

    if not settings.azure_openai_deployment:
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is not configured.")

    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version,
        temperature=0,
    )


async def generate_text(
    system_prompt: str,
    user_prompt: str,
) -> str:
    model = get_chat_model()

    response = await model.ainvoke(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )

    return str(response.content)
