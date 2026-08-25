"""Optional post-synthesis write gate (allowlisted HITL actions only)."""

from __future__ import annotations

import time

from pydantic import BaseModel

from app.agents.execution_trace import node_trace
from app.agents.state import AgentState
from app.services.approved_action_service import APPROVED_WRITE_ACTIONS
from app.services.llm_service import get_chat_model

WRITE_GATE_PROMPT = """
You decide whether an allowlisted maintenance write action should be proposed
AFTER evidence has already been gathered.

Only propose create_maintenance_ticket when:
- the user explicitly asked to create/open a ticket, OR
- the evidence clearly indicates intervention is required AND the user asked
  you to create a ticket if needed.

If proposing a ticket, fill asset_code, issue, and priority from the user
request and evidence. Priority must be one of: low, medium, high.

If no write should occur, set propose_write=false.

Never invent tools other than create_maintenance_ticket.
Do not reveal chain-of-thought.
""".strip()


class WriteProposal(BaseModel):
    propose_write: bool = False
    tool_name: str | None = None
    asset_code: str | None = None
    issue: str | None = None
    priority: str | None = None


async def write_gate_node(state: AgentState) -> dict:
    started = time.perf_counter()

    if not state.get("may_require_write"):
        return {
            **node_trace(
                "write_gate",
                timing={"write_gate_ms": round((time.perf_counter() - started) * 1000, 2)},
            ),
        }

    # Single-route tool path already handled writes inside mcp_tool_node.
    if not state.get("requires_synthesis"):
        return {
            **node_trace(
                "write_gate",
                timing={"write_gate_ms": round((time.perf_counter() - started) * 1000, 2)},
            ),
        }

    evidence = "\n\n".join(
        part
        for part in (
            f"Question: {state['query']}",
            f"Synthesis: {state.get('synthesis_answer') or ''}",
            f"RAG: {state.get('rag_answer') or ''}",
            f"SQL: {state.get('sql_answer') or ''}",
            f"MCP: {state.get('tool_answer') or ''}",
        )
        if part
    )

    model = get_chat_model().with_structured_output(WriteProposal)
    proposal = await model.ainvoke(
        [
            ("system", WRITE_GATE_PROMPT),
            ("human", evidence),
        ]
    )
    if not isinstance(proposal, WriteProposal):
        proposal = WriteProposal.model_validate(proposal)

    write_gate_ms = round((time.perf_counter() - started) * 1000, 2)

    if (
        not proposal.propose_write
        or proposal.tool_name not in APPROVED_WRITE_ACTIONS
        or not proposal.asset_code
        or not proposal.issue
        or proposal.priority not in {"low", "medium", "high"}
    ):
        return {
            **node_trace(
                "write_gate",
                timing={"write_gate_ms": write_gate_ms},
                tools={
                    "mcp_server": "maintenance",
                    "tool_type": "write",
                    "requires_approval": False,
                    "approval_status": "not_proposed",
                },
            ),
        }

    pending_action = {
        "tool_name": proposal.tool_name,
        "arguments": {
            "asset_code": proposal.asset_code,
            "issue": proposal.issue,
            "priority": proposal.priority,
        },
    }

    return {
        "requires_approval": True,
        "pending_action": pending_action,
        "tool_answer": "This action requires human approval before execution.",
        **node_trace(
            "write_gate",
            timing={"write_gate_ms": write_gate_ms},
            tools={
                "mcp_server": "maintenance",
                "tool_name": proposal.tool_name,
                "arguments": pending_action["arguments"],
                "tool_type": "write",
                "requires_approval": True,
                "approval_status": "pending",
            },
            hitl={
                "required": True,
                "approved": None,
                "pending_action": pending_action,
            },
        ),
    }
