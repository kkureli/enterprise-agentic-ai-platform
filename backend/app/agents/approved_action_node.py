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
        "external_url": result.get("external_url"),
        "external_id": result.get("external_id"),
        "deduplicated": result.get("deduplicated"),
        "provider": result.get("provider"),
        "risk_escalation_id": result.get("risk_escalation_id"),
    }

    tool_name = (state.get("pending_action") or {}).get("tool_name")
    if tool_name == "create_github_issue" and result.get("external_url"):
        if result.get("deduplicated"):
            tool_answer = (
                f"GitHub issue already exists for this evaluation "
                f"({result['external_url']}); skipped duplicate create."
            )
        else:
            escalation_note = ""
            if result.get("risk_escalation_id"):
                escalation_note = (
                    f" Internal escalation {result['risk_escalation_id']} recorded."
                )
            tool_answer = (
                f"GitHub issue created successfully: {result['external_url']}."
                f"{escalation_note}"
            )
    else:
        tool_answer = (
            f"Maintenance ticket {result['ticket_id']} was created "
            f"successfully with priority {result['priority']}."
        )

    return {
        "requires_approval": False,
        "action_result": result,
        "tool_answer": tool_answer,
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
                "mcp_server": (
                    "github" if tool_name == "create_github_issue" else "maintenance"
                ),
                "tool_name": tool_name,
                "arguments": (state.get("pending_action") or {}).get("arguments"),
                "tool_type": "write",
                "requires_approval": True,
                "approval_status": "executed",
                "action_result": safe_result,
                "result_preview": safe_result_preview(safe_result),
            },
        ),
    }
