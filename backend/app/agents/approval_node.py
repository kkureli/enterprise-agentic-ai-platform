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
    tool_name = (state.get("pending_action") or {}).get("tool_name")
    mcp_server = "github" if tool_name == "create_github_issue" else "maintenance"

    if not approved:
        reject_message = (
            "GitHub Issue açma isteği reddedildi; dış yazma yapılmadı."
            if state.get("response_language") == "tr"
            and tool_name == "create_github_issue"
            else (
                "GitHub Issue creation was rejected; no external write was performed."
                if tool_name == "create_github_issue"
                else "The action was rejected by the user."
            )
        )
        return {
            "requires_approval": False,
            "approval_granted": False,
            "tool_answer": reject_message,
            **node_trace(
                "approval",
                route="tool" if tool_name != "create_github_issue" else "external_risk_assessment",
                hitl={
                    "required": True,
                    "approved": False,
                    "pending_action": state.get("pending_action"),
                },
                tools={
                    "approval_status": "rejected",
                    "requires_approval": True,
                    "tool_name": tool_name,
                    "arguments": (state.get("pending_action") or {}).get("arguments"),
                    "tool_type": "write",
                    "mcp_server": mcp_server,
                },
            ),
        }

    return {
        "requires_approval": False,
        "approval_granted": True,
        **node_trace(
            "approval",
            route="tool" if tool_name != "create_github_issue" else "external_risk_assessment",
            hitl={
                "required": True,
                "approved": True,
                "pending_action": state.get("pending_action"),
            },
            tools={
                "approval_status": "approved",
                "requires_approval": True,
                "tool_name": tool_name,
                "arguments": (state.get("pending_action") or {}).get("arguments"),
                "tool_type": "write",
                "mcp_server": mcp_server,
            },
        ),
    }
