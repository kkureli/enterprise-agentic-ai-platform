from app.agents.state import AgentState
from app.services.rag_service import answer_question


async def rag_node(state: AgentState) -> dict:
    result = await answer_question(
        tenant_id=state["tenant_id"],
        question=state["query"],
        retrieval_mode=state.get("retrieval_mode", "standard"),
    )

    return {
        "rag_answer": result.answer,
    }
