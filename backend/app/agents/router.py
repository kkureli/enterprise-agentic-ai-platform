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
Use for questions that require querying historical or structured
operational data stored in PostgreSQL.

Examples:
- counts and aggregates
- lists of assets
- filtering assets by status
- maintenance history
- existing maintenance tickets
- historical maintenance records

Prefer sql when the user asks about multiple records, lists,
aggregations, filtering, or historical structured data.

tool:
Use only for currently available operational capabilities:

1. Getting the current live operational status of a specific asset.
2. Creating a maintenance ticket.

Examples:
- "What is the current status of MACHINE-42?" -> tool
- "Check MACHINE-17 right now." -> tool
- "Create a maintenance ticket for MACHINE-42." -> tool

Do not route arbitrary enterprise actions to tool.
If no available tool supports the requested action, use unsupported.

unsupported:
Use when the request requires a capability that is not available.

Examples:
- sending email
- booking flights
- ordering external parts
- weather
- financial market prices
- external news

Important distinctions:

"What does error AX-4317 mean?"
-> knowledge

"Which assets are currently in warning state?"
-> sql

"How many maintenance records does MACHINE-42 have?"
-> sql

"Show the maintenance history for MACHINE-42."
-> sql

"What is the current operational status of MACHINE-42?"
-> tool

"Create a maintenance ticket for MACHINE-42."
-> tool

"Send an email to the maintenance manager."
-> unsupported

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
