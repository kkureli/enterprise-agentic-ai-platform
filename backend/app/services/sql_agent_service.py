import json
import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlglot import exp, parse

from app.services.llm_service import get_chat_model
from app.services.sql_generation_service import generate_sql
from app.services.sql_query_service import (
    UnsafeSQLQueryError,
    execute_readonly_sql,
    validate_readonly_sql,
)


class SQLAgentResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    answer: str
    validation_status: str = "passed"
    tables_used: list[str] = []
    tenant_scope_verified: bool = True
    read_only_verified: bool = True
    row_count: int = 0
    generation_duration_ms: float | None = None
    execution_duration_ms: float | None = None
    llm_generation_ms: float | None = None


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


def _extract_tables(sql: str) -> list[str]:
    try:
        statements = parse(sql, read="postgres")
    except Exception:
        return []

    if not statements:
        return []

    return sorted({table.name for table in statements[0].find_all(exp.Table)})


async def answer_with_sql(
    tenant_id: UUID,
    question: str,
) -> SQLAgentResult:
    generation_started = time.perf_counter()
    sql = await generate_sql(question)
    generation_duration_ms = round((time.perf_counter() - generation_started) * 1000, 2)

    try:
        validate_readonly_sql(sql)
        validation_status = "passed"
        tenant_scope_verified = True
        read_only_verified = True
    except UnsafeSQLQueryError:
        raise

    tables_used = _extract_tables(sql)

    execution_started = time.perf_counter()
    rows = await execute_readonly_sql(
        tenant_id=tenant_id,
        sql=sql,
    )
    execution_duration_ms = round((time.perf_counter() - execution_started) * 1000, 2)

    rows_json = json.dumps(
        rows,
        default=str,
        ensure_ascii=False,
    )

    model = get_chat_model()

    llm_started = time.perf_counter()
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
    llm_generation_ms = round((time.perf_counter() - llm_started) * 1000, 2)

    return SQLAgentResult(
        sql=sql,
        rows=rows,
        answer=str(response.content),
        validation_status=validation_status,
        tables_used=tables_used,
        tenant_scope_verified=tenant_scope_verified,
        read_only_verified=read_only_verified,
        row_count=len(rows),
        generation_duration_ms=generation_duration_ms,
        execution_duration_ms=execution_duration_ms,
        llm_generation_ms=llm_generation_ms,
    )
