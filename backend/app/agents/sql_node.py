from app.agents.execution_trace import node_trace
from app.agents.state import AgentState
from app.services.sql_agent_service import answer_with_sql


async def sql_node(state: AgentState) -> dict:
    result = await answer_with_sql(
        tenant_id=state["tenant_id"],
        question=state["query"],
        response_language=state.get("response_language"),
    )

    timing = {}
    if result.generation_duration_ms is not None:
        timing["sql_generation_ms"] = result.generation_duration_ms
    if result.execution_duration_ms is not None:
        timing["sql_execution_ms"] = result.execution_duration_ms
    if result.llm_generation_ms is not None:
        timing["llm_generation_ms"] = result.llm_generation_ms

    return {
        "sql_answer": result.answer,
        "generated_sql": result.sql,
        **node_trace(
            "sql",
            route="sql",
            sql={
                "generated_sql": result.sql,
                "validation_status": result.validation_status,
                "tables_used": result.tables_used,
                "tenant_scope_verified": result.tenant_scope_verified,
                "read_only_verified": result.read_only_verified,
                "row_count": result.row_count,
                "execution_duration_ms": result.execution_duration_ms,
                "generation_duration_ms": result.generation_duration_ms,
            },
            timing=timing or None,
        ),
    }
