from app.agents.execution_trace import node_trace, safe_result_preview
from app.agents.state import AgentState
from app.services.approved_action_service import execute_approved_action


async def approved_action_node(state: AgentState) -> dict:
    result = await execute_approved_action(
        tenant_id=state["tenant_id"],
        pending_action=state["pending_action"],
    )

    safe_result = {
        "ticket_id": result.get("ticket_id"),
        "priority": result.get("priority"),
        "status": result.get("status"),
        "asset_code": result.get("asset_code"),
    }

    return {
        "requires_approval": False,
        "action_result": result,
        "tool_answer": (
            f"Maintenance ticket {result['ticket_id']} was created "
            f"successfully with priority {result['priority']}."
        ),
        **node_trace(
            "approved_action",
            route="tool",
            hitl={
                "required": True,
                "approved": True,
                "pending_action": state.get("pending_action"),
                "action_result": safe_result,
            },
            tools={
                "mcp_server": "maintenance",
                "tool_name": (state.get("pending_action") or {}).get("tool_name"),
                "arguments": (state.get("pending_action") or {}).get("arguments"),
                "tool_type": "write",
                "requires_approval": True,
                "approval_status": "executed",
                "action_result": safe_result,
                "result_preview": safe_result_preview(safe_result),
            },
        ),
    }
