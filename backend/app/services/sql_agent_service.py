import json
import logging
import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlglot import exp, parse

from app.services.language_detection import (
    detect_response_language,
    format_response_language_instruction,
)
from app.services.llm_service import get_chat_model
from app.services.sql_generation_service import generate_sql, repair_sql
from app.services.sql_query_service import (
    UnsafeSQLQueryError,
    execute_readonly_sql,
    validate_readonly_sql,
)

logger = logging.getLogger(__name__)


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
    repaired: bool = False


SYSTEM_PROMPT = """
You answer questions about enterprise operational and commercial account data.

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
- Write the entire answer in the requested response language.
  SQL identifiers and raw row values may stay as returned; translate the
  user-facing explanation as needed without changing facts.
- For company questions, keep entity identity exact (company_name, domain,
  internal_customer_id). Never blend facts across different companies.
""".strip()


def _extract_tables(sql: str) -> list[str]:
    try:
        statements = parse(sql, read="postgres")
    except Exception:
        return []

    if not statements:
        return []

    return sorted({table.name for table in statements[0].find_all(exp.Table)})


async def _generate_and_validate_sql(question: str) -> tuple[str, bool, float]:
    """Generate SQL, validate, and apply at most one safety repair if needed."""

    generation_started = time.perf_counter()
    sql = await generate_sql(question)
    repaired = False

    try:
        validate_readonly_sql(sql)
    except UnsafeSQLQueryError as first_error:
        logger.info(
            "SQL validation failed; attempting one bounded repair. error=%s sql=%s",
            first_error,
            sql,
        )
        rejected = sql
        sql = await repair_sql(question, rejected, str(first_error))
        repaired = True
        try:
            # Second validation must pass; never execute rejected SQL.
            validate_readonly_sql(sql)
        except UnsafeSQLQueryError as second_error:
            generation_duration_ms = round((time.perf_counter() - generation_started) * 1000, 2)
            raise UnsafeSQLQueryError(
                f"SQL remained unsafe after one repair attempt: {second_error}"
            ) from second_error

    generation_duration_ms = round((time.perf_counter() - generation_started) * 1000, 2)
    return sql, repaired, generation_duration_ms


async def answer_with_sql(
    tenant_id: UUID,
    question: str,
    response_language: str | None = None,
) -> SQLAgentResult:
    language = response_language or detect_response_language(question)
    try:
        sql, repaired, generation_duration_ms = await _generate_and_validate_sql(question)
    except UnsafeSQLQueryError as exc:
        logger.warning("SQL capability soft-failed after validation/repair: %s", exc)
        soft_answer = (
            "Yapılandırılmış SQL sorgusu güvenlik kuralları nedeniyle çalıştırılamadı; "
            "diğer kanıt kaynaklarıyla devam ediliyor."
            if language == "tr"
            else (
                "Structured SQL could not be executed under safety rules; "
                "continuing with other evidence sources."
            )
        )
        return SQLAgentResult(
            sql="",
            rows=[],
            answer=soft_answer,
            validation_status="failed",
            tables_used=[],
            tenant_scope_verified=False,
            read_only_verified=False,
            row_count=0,
            generation_duration_ms=None,
            execution_duration_ms=None,
            llm_generation_ms=None,
            repaired=False,
        )

    validation_status = "passed"
    tenant_scope_verified = True
    read_only_verified = True
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
{format_response_language_instruction(language)}

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
        repaired=repaired,
    )
