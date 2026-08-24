import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.services.llm_service import get_chat_model
from app.services.sql_generation_service import generate_sql
from app.services.sql_query_service import execute_readonly_sql


class SQLAgentResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    answer: str


SYSTEM_PROMPT = """
You answer questions about enterprise operational data.

You are given:
- the user's original question
- the SQL query that was executed
- the rows returned by PostgreSQL

Rules:
- Answer using only the provided SQL result.
- Do not invent data.
- If no rows were returned, clearly say that no matching data was found.
- Be concise and clear.
- Do not expose the SQL query unless the user explicitly asks for it.
""".strip()


async def answer_with_sql(
    tenant_id: UUID,
    question: str,
) -> SQLAgentResult:
    sql = await generate_sql(question)

    rows = await execute_readonly_sql(
        tenant_id=tenant_id,
        sql=sql,
    )

    rows_json = json.dumps(
        rows,
        default=str,
        ensure_ascii=False,
    )

    model = get_chat_model()

    response = await model.ainvoke(
        [
            (
                "system",
                SYSTEM_PROMPT,
            ),
            (
                "human",
                f"""
User question:
{question}

Executed SQL:
{sql}

SQL result:
{rows_json}
""".strip(),
            ),
        ]
    )

    return SQLAgentResult(
        sql=sql,
        rows=rows,
        answer=str(response.content),
    )
