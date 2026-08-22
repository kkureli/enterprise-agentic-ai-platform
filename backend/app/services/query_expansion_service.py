from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_service import get_chat_model


class QueryExpansion(BaseModel):
    queries: list[str] = Field(
        min_length=1,
        max_length=settings.query_expansion_max_count,
    )


SYSTEM_PROMPT = """
You generate alternative search queries for an enterprise retrieval system.

Generate up to 3 concise alternative queries that preserve the user's original intent.

Rules:
- Preserve important identifiers, product codes, error codes, names, and numbers.
- Do not invent facts.
- Use wording that may improve document retrieval.
- Include semantic paraphrases and useful domain terminology.
- Do not answer the question.
""".strip()


async def expand_query(
    query: str,
) -> list[str]:
    model = get_chat_model().with_structured_output(QueryExpansion)

    result = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", query),
        ]
    )

    queries = [query]

    for expanded_query in result.queries:
        cleaned_query = expanded_query.strip()

        if cleaned_query and cleaned_query.lower() not in {item.lower() for item in queries}:
            queries.append(cleaned_query)

    return queries
