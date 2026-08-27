import json
import re
import time

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel, Field

from app.agents.execution_trace import node_trace, safe_result_preview
from app.agents.state import AgentState
from app.services.language_detection import format_response_language_instruction
from app.services.llm_service import get_chat_model
from app.services.mcp_client import (
    call_maintenance_tool,
    list_maintenance_tools,
)

APPROVAL_REQUIRED_TOOLS = {
    "create_maintenance_ticket",
}

MCP_READ_TOOLS = {
    "get_asset_status",
    "get_maintenance_history",
}

MCP_SERVER_NAME = "maintenance"

WRITE_INTENT_RE = re.compile(
    r"\b(create|open|request|file|raise)\b.*\b(ticket|maintenance ticket)\b"
    r"|\b(ticket)\b.*\b(create|open)\b"
    r"|\buse the enterprise system to create\b"
    r"|\b(oluştur|olustur|aç|ac)\b.*\b(bilet|ticket|bakım kaydı|bakim kaydi|"
    r"bakım bileti|bakim bileti)\b"
    r"|\b(bilet|ticket|bakım kaydı|bakim kaydi)\b.*\b(oluştur|olustur|aç|ac)\b"
    r"|\b(bakım kaydı oluştur|bakim kaydi olustur|ticket oluştur|ticket olustur)\b",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """
You are an enterprise operations assistant.

Use the available tools when the user's request requires:
- current operational data, or
- an action in an enterprise system.

The user request may be in English or Turkish. Always call the English tool
names exactly as exposed (get_asset_status, get_maintenance_history,
create_maintenance_ticket). Do not invent localized tool names.

Rules:
- Do not invent operational data.
- Select the tool that best matches the user's request.
- Use tool results as the source of truth.
- After receiving the tool result, answer clearly and concisely.
- If the user asks to create, open, or request a maintenance ticket
  (including Turkish: oluştur / aç / bakım kaydı),
  always select create_maintenance_ticket.
- A ticket creation request must never be answered without selecting
  create_maintenance_ticket.
- If the user asks for the current status of a specific asset
  (including Turkish: güncel durum / durumu nedir),
  select get_asset_status.
- Always include tenant_slug exactly as provided in the system context
  when calling tools (the host also injects it).
- Call at most one tool.
""".strip()

READ_ONLY_SYSTEM_PROMPT = """
You are an enterprise operations assistant gathering LIVE READ evidence only.

Available tools are read-only. You must NOT create tickets or perform writes.
The user request may be in English or Turkish; call English tool names only.

Rules:
- Do not invent operational data.
- Prefer get_asset_status for current operational status of a specific asset.
- Prefer get_maintenance_history only when the question asks for live tool history
  (structured SQL history is handled elsewhere).
- After receiving the tool result, answer clearly and concisely from the tool
  JSON result. Do not emit additional tool calls.
- Always include tenant_slug exactly as provided in the system context.
- Call at most one tool.
""".strip()

WRITE_ONLY_SYSTEM_PROMPT = """
You are preparing an allowlisted maintenance write action.

The user explicitly requested creating/opening a maintenance ticket
(English or Turkish phrasing).
You MUST select create_maintenance_ticket.
Fill asset_code, issue, and priority from the user request.
Priority must be one of: low, medium, high (map Turkish yüksek/orta/düşük
to high/medium/low when needed).
Always include tenant_slug from the system context.
Call exactly one tool: create_maintenance_ticket.
""".strip()


class TicketDraft(BaseModel):
    asset_code: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    priority: str = Field(pattern="^(low|medium|high)$")


def _tenant_slug(state: AgentState) -> str:
    slug = state.get("tenant_slug")
    if not slug:
        raise RuntimeError("tenant_slug is required on AgentState for MCP calls.")
    return slug


def _query_has_write_intent(query: str) -> bool:
    return bool(WRITE_INTENT_RE.search(query or ""))


def _bind_tools(model, tool_schemas: list[dict]):
    """Bind tools and disable parallel tool calls when the SDK supports it."""

    try:
        return model.bind_tools(tool_schemas, parallel_tool_calls=False)
    except TypeError:
        return model.bind_tools(tool_schemas)


def _tool_messages_for_protocol(
    tool_request: AIMessage,
    *,
    primary_id: str,
    primary_content: str,
) -> list[ToolMessage]:
    """Ensure every tool_call_id has a ToolMessage before the next LLM turn."""

    messages: list[ToolMessage] = []
    for tool_call in tool_request.tool_calls or []:
        call_id = tool_call["id"]
        if call_id == primary_id:
            messages.append(ToolMessage(content=primary_content, tool_call_id=call_id))
        else:
            messages.append(
                ToolMessage(
                    content=json.dumps(
                        {
                            "skipped": True,
                            "reason": "Only one MCP tool call is executed per request.",
                        }
                    ),
                    tool_call_id=call_id,
                )
            )
    return messages


def _pending_write_payload(
    *,
    tool_name: str,
    arguments: dict,
    tenant_slug: str,
) -> dict:
    safe_args = {key: value for key, value in arguments.items() if key != "tenant_slug"}
    return {
        "requires_approval": True,
        "pending_action": {
            "tool_name": tool_name,
            "arguments": safe_args,
        },
        "tool_answer": "This action requires human approval before execution.",
        **node_trace(
            "tool",
            tools={
                "mcp_server": MCP_SERVER_NAME,
                "tool_name": tool_name,
                "arguments": safe_args,
                "tool_type": "write",
                "requires_approval": True,
                "approval_status": "pending",
                "tenant_slug": tenant_slug,
            },
            hitl={
                "required": True,
                "approved": None,
                "pending_action": {
                    "tool_name": tool_name,
                    "arguments": safe_args,
                },
            },
        ),
    }


async def _draft_ticket_from_query(query: str) -> TicketDraft:
    model = get_chat_model().with_structured_output(TicketDraft)
    result = await model.ainvoke(
        [
            (
                "system",
                (
                    "Extract create_maintenance_ticket fields from the user request. "
                    "priority must be low, medium, or high. Prefer high when urgency "
                    "is implied. Do not invent unrelated assets."
                ),
            ),
            ("human", query),
        ]
    )
    return result if isinstance(result, TicketDraft) else TicketDraft.model_validate(result)


async def mcp_tool_node(state: AgentState) -> dict:
    read_only = bool(state.get("tool_read_only"))
    tenant_slug = _tenant_slug(state)
    query = state["query"]
    may_require_write = bool(state.get("may_require_write")) or (
        not read_only and _query_has_write_intent(query)
    )

    mcp_tools = await list_maintenance_tools()
    available = {tool.name for tool in mcp_tools.tools}

    if read_only:
        allowed = available & MCP_READ_TOOLS
        system = READ_ONLY_SYSTEM_PROMPT
    elif may_require_write:
        # Explicit write intent: only expose allowlisted write tools so HITL fires.
        allowed = available & APPROVAL_REQUIRED_TOOLS
        system = WRITE_ONLY_SYSTEM_PROMPT
    else:
        allowed = {
            name for name in available if name in MCP_READ_TOOLS or name in APPROVAL_REQUIRED_TOOLS
        }
        system = SYSTEM_PROMPT

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
        if tool.name in allowed
    ]

    if not tool_schemas and may_require_write and not read_only:
        draft = await _draft_ticket_from_query(query)
        return _pending_write_payload(
            tool_name="create_maintenance_ticket",
            arguments={
                "asset_code": draft.asset_code,
                "issue": draft.issue,
                "priority": draft.priority,
                "tenant_slug": tenant_slug,
            },
            tenant_slug=tenant_slug,
        )

    model = _bind_tools(get_chat_model(), tool_schemas)
    system = (
        f"{system}\n\nTenant slug for all tool calls: {tenant_slug}\n"
        "Pass tenant_slug in every tool call argument object."
    )

    messages = [
        ("system", system),
        ("human", query),
    ]

    tool_request = await model.ainvoke(messages)

    if not tool_request.tool_calls:
        if may_require_write and not read_only:
            draft = await _draft_ticket_from_query(query)
            return _pending_write_payload(
                tool_name="create_maintenance_ticket",
                arguments={
                    "asset_code": draft.asset_code,
                    "issue": draft.issue,
                    "priority": draft.priority,
                    "tenant_slug": tenant_slug,
                },
                tenant_slug=tenant_slug,
            )
        return {
            "tool_answer": (
                "The request requires an operational tool, but no appropriate tool was selected."
            ),
            **node_trace(
                "tool",
                tools={
                    "mcp_server": MCP_SERVER_NAME,
                    "tool_name": None,
                    "tool_type": "read",
                    "result_preview": "No tool selected.",
                    "tenant_slug": tenant_slug,
                },
            ),
        }

    # Execute only the first tool call; still satisfy protocol for any extras.
    tool_call = tool_request.tool_calls[0]
    if tool_call["name"] not in allowed:
        if may_require_write and not read_only:
            draft = await _draft_ticket_from_query(query)
            return _pending_write_payload(
                tool_name="create_maintenance_ticket",
                arguments={
                    "asset_code": draft.asset_code,
                    "issue": draft.issue,
                    "priority": draft.priority,
                    "tenant_slug": tenant_slug,
                },
                tenant_slug=tenant_slug,
            )
        raise RuntimeError(f"Unknown or disallowed MCP tool requested: {tool_call['name']}")

    safe_args = tool_call["args"] if isinstance(tool_call["args"], dict) else {}
    safe_args = {**safe_args, "tenant_slug": tenant_slug}

    if tool_call["name"] in APPROVAL_REQUIRED_TOOLS:
        if read_only:
            raise RuntimeError("Write tools are not allowed during composite read fan-out.")
        return _pending_write_payload(
            tool_name=tool_call["name"],
            arguments=safe_args,
            tenant_slug=tenant_slug,
        )

    if may_require_write and not read_only:
        # Model picked a read tool despite write intent — still require HITL write.
        draft = await _draft_ticket_from_query(query)
        return _pending_write_payload(
            tool_name="create_maintenance_ticket",
            arguments={
                "asset_code": draft.asset_code,
                "issue": draft.issue,
                "priority": draft.priority,
                "tenant_slug": tenant_slug,
            },
            tenant_slug=tenant_slug,
        )

    tool_started = time.perf_counter()
    result = await call_maintenance_tool(
        tool_call["name"],
        safe_args,
        tenant_slug=tenant_slug,
    )
    tool_ms = round((time.perf_counter() - tool_started) * 1000, 2)
    tool_result = result.structured_content

    protocol_messages = _tool_messages_for_protocol(
        tool_request,
        primary_id=tool_call["id"],
        primary_content=json.dumps(tool_result),
    )

    # Final answer from tool JSON only — no further tool calling.
    answer_model = get_chat_model()
    final_response = await answer_model.ainvoke(
        [
            (
                "system",
                (
                    "Summarize the MCP tool result for the user clearly and concisely. "
                    "Do not call tools. Do not invent data beyond the JSON result. "
                    "Write the entire answer in the requested response language."
                ),
            ),
            (
                "human",
                (
                    f"{format_response_language_instruction(state.get('response_language'))}\n\n"
                    f"User question:\n{query}\n\n"
                    f"Tool result JSON:\n{json.dumps(tool_result)}"
                ),
            ),
        ]
    )

    # Keep protocol helper available for tests / future multi-call paths.
    _ = protocol_messages

    return {
        "tool_answer": str(final_response.content),
        **node_trace(
            "tool",
            tools={
                "mcp_server": MCP_SERVER_NAME,
                "tool_name": tool_call["name"],
                "arguments": {
                    key: value for key, value in safe_args.items() if key != "tenant_slug"
                },
                "result_preview": safe_result_preview(tool_result),
                "tool_type": "read",
                "execution_duration_ms": tool_ms,
                "requires_approval": False,
                "tenant_slug": tenant_slug,
            },
            timing={"tool_execution_ms": tool_ms},
        ),
    }
