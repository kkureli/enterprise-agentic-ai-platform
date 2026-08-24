from app.agents.state import AgentState
from app.services.sql_agent_service import answer_with_sql


async def sql_node(state: AgentState) -> dict:
    result = await answer_with_sql(
        tenant_id=state["tenant_id"],
        question=state["query"],
    )

    return {
        "sql_answer": result.answer,
        "generated_sql": result.sql,
    }
