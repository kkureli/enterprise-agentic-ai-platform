"""Synthesize multi-capability evidence into one grounded answer."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

from app.agents.execution_trace import node_trace
from app.agents.state import AgentState
from app.services.llm_service import get_chat_model

SYNTHESIS_SYSTEM_PROMPT = """
You synthesize grounded evidence from multiple enterprise capabilities into one
final answer for the user.

Rules:
- Answer the original user question directly.
- Use ONLY the provided evidence blocks (Knowledge/RAG, SQL, MCP).
- Do not invent facts that are not supported by the evidence.
- If a capability was selected but its evidence is missing or failed, say so
  briefly without inventing a substitute.
- Prefer concrete operational details from the evidence.
- Do not reveal hidden chain-of-thought or planner internals.
- Keep the answer concise and professional.
""".strip()


class SynthesisOutput(BaseModel):
    answer: str = Field(min_length=1)


def _block(title: str, body: str | None) -> str:
    text = (body or "").strip()
    if not text:
        return f"### {title}\n(unavailable)"
    return f"### {title}\n{text}"


async def synthesis_node(state: AgentState) -> dict:
    started = time.perf_counter()
    planned = list(state.get("planned_routes") or [])

    sections: list[str] = [
        f"Tenant slug: {state.get('tenant_slug') or 'unknown'}",
        f"Selected capabilities: {', '.join(planned) or 'none'}",
        f"User question:\n{state['query']}",
    ]

    if "knowledge" in planned:
        sections.append(_block("Knowledge / RAG evidence", state.get("rag_answer")))
    if "sql" in planned:
        sql_meta = ""
        if state.get("generated_sql"):
            sql_meta = f"\nGenerated SQL:\n{state['generated_sql']}"
        sections.append(
            _block("SQL evidence", f"{state.get('sql_answer') or ''}{sql_meta}".strip())
        )
    if "tool" in planned:
        sections.append(_block("MCP live tool evidence", state.get("tool_answer")))

    model = get_chat_model().with_structured_output(SynthesisOutput)
    result = await model.ainvoke(
        [
            ("system", SYNTHESIS_SYSTEM_PROMPT),
            ("human", "\n\n".join(sections)),
        ]
    )
    answer = result.answer if isinstance(result, SynthesisOutput) else str(result)
    synthesis_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "synthesis_answer": answer,
        **node_trace(
            "synthesis",
            selected_capabilities=[r for r in planned if r != "unsupported"],
            timing={"synthesis_ms": synthesis_ms},
        ),
    }
