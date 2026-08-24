from app.agents.state import AgentState
from app.services.approved_action_service import execute_approved_action


async def approved_action_node(state: AgentState) -> dict:
    result = await execute_approved_action(
        tenant_id=state["tenant_id"],
        pending_action=state["pending_action"],
    )

    return {
        "requires_approval": False,
        "action_result": result,
        "tool_answer": (
            f"Maintenance ticket {result['ticket_id']} was created "
            f"successfully with priority {result['priority']}."
        ),
    }
