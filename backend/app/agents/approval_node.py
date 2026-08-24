from langgraph.types import interrupt

from app.agents.state import AgentState


async def approval_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "type": "approval_required",
            "message": "This action requires human approval.",
            "pending_action": state["pending_action"],
        }
    )

    approved = isinstance(decision, dict) and decision.get("approved") is True

    if not approved:
        return {
            "requires_approval": False,
            "approval_granted": False,
            "tool_answer": "The action was rejected by the user.",
        }

    return {
        "requires_approval": False,
        "approval_granted": True,
    }
