from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.approval_node import approval_node
from app.agents.approved_action_node import approved_action_node
from app.agents.mcp_tool_node import mcp_tool_node
from app.agents.rag_node import rag_node
from app.agents.router import router_node
from app.agents.sql_node import sql_node
from app.agents.state import AgentRoute, AgentState


def route_after_router(state: AgentState) -> AgentRoute:
    return state["route"]


def finalize_node(state: AgentState) -> dict:
    route = state["route"]

    if route == "knowledge":
        return {
            "final_answer": state["rag_answer"],
        }

    if route == "sql":
        return {
            "final_answer": state["sql_answer"],
        }

    if route == "tool":
        return {
            "final_answer": state["tool_answer"],
        }

    raise ValueError(f"Unsupported finalize route: {route}")


def fallback_node(state: AgentState) -> dict:
    return {
        "final_answer": "This request is not supported yet.",
    }


def route_after_tool(state: AgentState) -> str:
    if state.get("requires_approval"):
        return "approval"

    return "finalize"


def route_after_approval(state: AgentState) -> str:
    if state.get("approval_granted"):
        return "approved_action"

    return "finalize"


builder = StateGraph(AgentState)

builder.add_node("router", router_node)
builder.add_node("rag", rag_node)
builder.add_node("finalize", finalize_node)
builder.add_node("fallback", fallback_node)
builder.add_node("tool", mcp_tool_node)
builder.add_node("sql", sql_node)
builder.add_node("approval", approval_node)
builder.add_node("approved_action", approved_action_node)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "knowledge": "rag",
        "tool": "tool",
        "sql": "sql",
        "unsupported": "fallback",
    },
)


builder.add_conditional_edges(
    "tool",
    route_after_tool,
    {
        "approval": "approval",
        "finalize": "finalize",
    },
)

builder.add_conditional_edges(
    "approval",
    route_after_approval,
    {
        "approved_action": "approved_action",
        "finalize": "finalize",
    },
)

builder.add_edge(
    "approved_action",
    "finalize",
)

builder.add_edge("rag", "finalize")
builder.add_edge("sql", "finalize")

builder.add_edge("finalize", END)
builder.add_edge("fallback", END)

checkpointer = InMemorySaver()

agent_graph = builder.compile(
    checkpointer=checkpointer,
)
