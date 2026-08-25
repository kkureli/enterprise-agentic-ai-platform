import json
import time

from langchain_core.messages import ToolMessage

from app.agents.execution_trace import node_trace, safe_result_preview
from app.agents.state import AgentState
from app.services.llm_service import get_chat_model
from app.services.mcp_client import (
    call_maintenance_tool,
    list_maintenance_tools,
)

APPROVAL_REQUIRED_TOOLS = {
    "create_maintenance_ticket",
}

MCP_SERVER_NAME = "maintenance"

SYSTEM_PROMPT = """
You are an enterprise operations assistant.

Use the available tools when the user's request requires:
- current operational data, or
- an action in an enterprise system.

Rules:
- Do not invent operational data.
- Select the tool that best matches the user's request.
- Use tool results as the source of truth.
- After receiving the tool result, answer clearly and concisely.
- If the user asks to create, open, or request a maintenance ticket,
  always select create_maintenance_ticket.
- A ticket creation request must never be answered without selecting
  create_maintenance_ticket.
- If the user asks for the current status of a specific asset,
  select get_asset_status.
""".strip()


async def mcp_tool_node(state: AgentState) -> dict:
    mcp_tools = await list_maintenance_tools()

    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in mcp_tools.tools
    ]

    model = get_chat_model().bind_tools(tool_schemas)

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", state["query"]),
    ]

    tool_request = await model.ainvoke(messages)

    if not tool_request.tool_calls:
        return {
            "tool_answer": (
                "The request requires an operational tool, but no appropriate tool was selected."
            ),
            **node_trace(
                "tool",
                route="tool",
                tools={
                    "mcp_server": MCP_SERVER_NAME,
                    "tool_name": None,
                    "tool_type": "read",
                    "result_preview": "No tool selected.",
                },
            ),
        }

    tool_call = tool_request.tool_calls[0]

    allowed_tools = {tool.name for tool in mcp_tools.tools}

    if tool_call["name"] not in allowed_tools:
        raise RuntimeError(f"Unknown MCP tool requested: {tool_call['name']}")

    safe_args = tool_call["args"] if isinstance(tool_call["args"], dict) else {}

    if tool_call["name"] in APPROVAL_REQUIRED_TOOLS:
        return {
            "requires_approval": True,
            "pending_action": {
                "tool_name": tool_call["name"],
                "arguments": safe_args,
            },
            "tool_answer": ("This action requires human approval before execution."),
            **node_trace(
                "tool",
                route="tool",
                tools={
                    "mcp_server": MCP_SERVER_NAME,
                    "tool_name": tool_call["name"],
                    "arguments": safe_args,
                    "tool_type": "write",
                    "requires_approval": True,
                    "approval_status": "pending",
                },
                hitl={
                    "required": True,
                    "approved": None,
                    "pending_action": {
                        "tool_name": tool_call["name"],
                        "arguments": safe_args,
                    },
                },
            ),
        }

    tool_started = time.perf_counter()
    result = await call_maintenance_tool(
        tool_call["name"],
        safe_args,
    )
    tool_ms = round((time.perf_counter() - tool_started) * 1000, 2)

    tool_result = result.structured_content

    tool_message = ToolMessage(
        content=json.dumps(tool_result),
        tool_call_id=tool_call["id"],
    )

    final_response = await model.ainvoke(
        [
            *messages,
            tool_request,
            tool_message,
        ]
    )

    return {
        "tool_answer": str(final_response.content),
        **node_trace(
            "tool",
            route="tool",
            tools={
                "mcp_server": MCP_SERVER_NAME,
                "tool_name": tool_call["name"],
                "arguments": safe_args,
                "result_preview": safe_result_preview(tool_result),
                "tool_type": "read",
                "execution_duration_ms": tool_ms,
                "requires_approval": False,
            },
            timing={"tool_execution_ms": tool_ms},
        ),
    }
