from pydantic import BaseModel
from sqlglot import exp, parse

from app.services.llm_service import get_chat_model


class GeneratedSQL(BaseModel):
    sql: str


SYSTEM_PROMPT = """
You generate PostgreSQL SELECT queries for an enterprise operations system.

The user question may be in English or Turkish. Map intent to the English
schema below. Never invent Turkish table or column names; always use the
exact English identifiers listed here.

Available tables:

assets:
- id
- tenant_id
- asset_code
- name
- location
- status
- active_error_code
- created_at
- updated_at

maintenance_records:
- id
- tenant_id
- asset_id
- maintenance_date
- maintenance_type
- description
- technician
- created_at

maintenance_tickets:
- id
- tenant_id
- asset_id
- issue
- priority
- status
- created_at
- updated_at

Rules:
- Generate exactly one SELECT query.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or TRUNCATE.
- Only use the tables listed above.
- Every query must be tenant scoped.
- Always use :tenant_id as the tenant bind parameter.
- Never invent or hardcode a tenant UUID.
- Use PostgreSQL syntax.
- Do not answer the user's question.
- Return only the SQL through the structured output.
- Every table referenced in FROM or JOIN must be explicitly tenant scoped.
- For joined tables, every table alias must have its own
  alias.tenant_id = :tenant_id condition in the WHERE clause.
- Tenant predicates must use the declared alias (mr.tenant_id), never the
  bare table name (maintenance_records.tenant_id) when an alias exists.
- Tenant predicates must appear in WHERE, not only in JOIN ON.
- Never assume that tenant scope propagates through a JOIN.
- Never use OR in the WHERE clause. Prefer AND and IN (...) instead.
- Prefer simple alias names such as a, mr, mt.
- Turkish examples of intent mapping (still use English identifiers in SQL):
  "uyarı" / "warning" → status or issue filters as appropriate
  "bakım kaydı" / "geçmiş" → maintenance_records
  "bilet" / "ticket" → maintenance_tickets
  "varlık" / "makine" → assets / asset_code

Compliant join example:

SELECT mr.maintenance_date, mr.description, mr.maintenance_type
FROM maintenance_records AS mr
JOIN assets AS a ON a.id = mr.asset_id
WHERE a.tenant_id = :tenant_id
  AND mr.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'

Compliant multi-table example:

SELECT a.asset_code, mt.issue, mt.priority, mt.status
FROM maintenance_tickets AS mt
JOIN assets AS a ON a.id = mt.asset_id
WHERE a.tenant_id = :tenant_id
  AND mt.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'
""".strip()


REPAIR_SYSTEM_PROMPT = """
You repair a rejected PostgreSQL SELECT query so it passes enterprise SQL safety
validation.

You will receive:
- the original user question (English or Turkish)
- the rejected SQL
- the exact validation error
- a checklist of required alias.tenant_id predicates derived from the rejected SQL

Fix the SQL while preserving the user's intent.
Always keep English table/column identifiers from the enterprise schema.

Hard requirements:
- Exactly one SELECT statement
- Only tables: assets, maintenance_records, maintenance_tickets
- Every FROM/JOIN table alias must have alias.tenant_id = :tenant_id in WHERE
- Use the alias form exactly (example: mr.tenant_id = :tenant_id).
  Do NOT use the bare table name when the table is aliased
  (maintenance_records.tenant_id is INVALID if the alias is mr).
- Put every tenant predicate in the WHERE clause. JOIN ON alone is not enough.
- Never use OR; rewrite with AND / IN (...)
- Keep :tenant_id as the only tenant bind parameter
- Do not invent tables or columns
- Return only repaired SQL through structured output

Compliant join pattern:

SELECT ...
FROM maintenance_records AS mr
JOIN assets AS a ON a.id = mr.asset_id
WHERE a.tenant_id = :tenant_id
  AND mr.tenant_id = :tenant_id
  AND a.asset_code = 'MACHINE-42'
""".strip()


def extract_table_alias_pairs(sql: str) -> list[tuple[str, str]]:
    """Return (table_name, alias_or_name) pairs for FROM/JOIN tables."""

    statements = parse(sql, read="postgres")
    if len(statements) != 1:
        return []

    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for table in statements[0].find_all(exp.Table):
        table_name = table.name
        alias = table.alias_or_name
        key = alias.lower()
        if key in seen:
            continue
        seen.add(key)
        pairs.append((table_name, alias))
    return pairs


def required_tenant_predicates(sql: str) -> list[str]:
    """Build alias.tenant_id = :tenant_id predicates for every FROM/JOIN alias."""

    return [f"{alias}.tenant_id = :tenant_id" for _, alias in extract_table_alias_pairs(sql)]


def build_repair_human_message(
    question: str,
    rejected_sql: str,
    validation_error: str,
) -> str:
    """Structured repair context with dynamically derived alias requirements."""

    pairs = extract_table_alias_pairs(rejected_sql)
    predicates = required_tenant_predicates(rejected_sql)

    if pairs:
        alias_lines = "\n".join(
            f"- {table_name} AS {alias} → required WHERE predicate: {alias}.tenant_id = :tenant_id"
            for table_name, alias in pairs
        )
        predicate_block = "\n".join(f"- {predicate}" for predicate in predicates)
        alias_section = (
            "Table aliases found in the rejected SQL (derived dynamically):\n"
            f"{alias_lines}\n\n"
            "ALL of the following predicates MUST appear in the WHERE clause "
            "(not only in JOIN ON). Use these exact alias forms:\n"
            f"{predicate_block}\n"
        )
    else:
        alias_section = (
            "Could not parse table aliases from rejected SQL. Still ensure every "
            "FROM/JOIN alias has alias.tenant_id = :tenant_id in WHERE.\n"
        )

    return (
        f"User question:\n{question}\n\n"
        f"Rejected SQL:\n{rejected_sql}\n\n"
        f"Validation error:\n{validation_error}\n\n"
        f"{alias_section}\n"
        "Return a compliant SELECT query that includes every required alias "
        "tenant predicate in WHERE."
    )


async def generate_sql(question: str) -> str:
    model = get_chat_model().with_structured_output(GeneratedSQL)

    result = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", question),
        ]
    )

    return result.sql.strip()


async def repair_sql(question: str, rejected_sql: str, validation_error: str) -> str:
    """One bounded repair attempt after validation failure (query not executed)."""

    model = get_chat_model().with_structured_output(GeneratedSQL)
    result = await model.ainvoke(
        [
            ("system", REPAIR_SYSTEM_PROMPT),
            (
                "human",
                build_repair_human_message(question, rejected_sql, validation_error),
            ),
        ]
    )
    return result.sql.strip()
