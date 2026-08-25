from langgraph.types import interrupt

from app.agents.execution_trace import node_trace
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
            **node_trace(
                "approval",
                route="tool",
                hitl={
                    "required": True,
                    "approved": False,
                    "pending_action": state.get("pending_action"),
                },
                tools={
                    "approval_status": "rejected",
                    "requires_approval": True,
                    "tool_name": (state.get("pending_action") or {}).get("tool_name"),
                    "arguments": (state.get("pending_action") or {}).get("arguments"),
                    "tool_type": "write",
                    "mcp_server": "maintenance",
                },
            ),
        }

    return {
        "requires_approval": False,
        "approval_granted": True,
        **node_trace(
            "approval",
            route="tool",
            hitl={
                "required": True,
                "approved": True,
                "pending_action": state.get("pending_action"),
            },
            tools={
                "approval_status": "approved",
                "requires_approval": True,
                "tool_name": (state.get("pending_action") or {}).get("tool_name"),
                "arguments": (state.get("pending_action") or {}).get("arguments"),
                "tool_type": "write",
                "mcp_server": "maintenance",
            },
        ),
    }
