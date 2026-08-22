from typing import Literal

from pydantic import BaseModel

from app.agents.state import AgentState
from app.services.llm_service import get_chat_model


class RouteDecision(BaseModel):
    route: Literal["knowledge", "unsupported"]


SYSTEM_PROMPT = """
You are a router for an enterprise operations AI system.

Classify the user's request into exactly one route:

- knowledge:
  Use when the request asks for information that could be answered
  from enterprise documents, policies, manuals, procedures, error-code
  documentation, or other internal knowledge-base content.

- unsupported:
  Use when the request requires a capability that is not currently
  available, such as querying operational databases, performing actions,
  calling external tools, creating records, or handling unrelated requests.

Do not answer the user's question.
Only classify the request.
""".strip()


async def router_node(state: AgentState) -> dict:
    model = get_chat_model().with_structured_output(RouteDecision)

    result = await model.ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", state["query"]),
        ]
    )

    return {
        "route": result.route,
    }
