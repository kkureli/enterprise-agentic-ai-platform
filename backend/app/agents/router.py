from pydantic import BaseModel

from app.agents.state import AgentRoute, AgentState
from app.services.llm_service import get_chat_model


class RouteDecision(BaseModel):
    route: AgentRoute


ROUTER_SYSTEM_PROMPT = """
You are a routing component for an enterprise AI operations platform.

Choose exactly one route:

knowledge:
Use for questions that require enterprise knowledge documents,
policies, manuals, procedures, troubleshooting guides, or internal
knowledge base content.

sql:
Use for questions that require querying structured operational data
stored in the database, such as:
- asset lists or statuses
- maintenance history
- counts and aggregates
- maintenance tickets already stored in the system
- filtering operational records
- questions about historical structured data

tool:
Use when the user wants to perform an action or use a live enterprise
capability, such as:
- creating a maintenance ticket
- invoking an operational tool
- performing an enterprise system action

unsupported:
Use when the request cannot be answered or performed using the
available enterprise capabilities.

Important distinctions:

"What does error AX-4317 mean?"
→ knowledge

"How many maintenance records does MACHINE-42 have?"
→ sql

"Show the maintenance history for MACHINE-42."
→ sql

"Create a maintenance ticket for MACHINE-42."
→ tool

Return only the structured routing decision.
""".strip()


async def router_node(state: AgentState) -> dict:
    model = get_chat_model().with_structured_output(RouteDecision)

    result = await model.ainvoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", state["query"]),
        ]
    )

    return {
        "route": result.route,
    }
