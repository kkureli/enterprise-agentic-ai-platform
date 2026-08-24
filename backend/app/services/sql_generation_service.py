from pydantic import BaseModel

from app.services.llm_service import get_chat_model


class GeneratedSQL(BaseModel):
    sql: str


SYSTEM_PROMPT = """
You generate PostgreSQL SELECT queries for an enterprise operations system.

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
""".strip()


async def generate_sql(question: str) -> str:
    model = get_chat_model().with_structured_output(GeneratedSQL)

    result = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", question),
        ]
    )

    return result.sql.strip()
