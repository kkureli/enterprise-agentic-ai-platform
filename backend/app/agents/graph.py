from langgraph.graph import END, START, StateGraph

from app.agents.mcp_tool_node import mcp_tool_node
from app.agents.rag_node import rag_node
from app.agents.router import router_node
from app.agents.state import AgentRoute, AgentState


def route_after_router(state: AgentState) -> AgentRoute:
    return state["route"]


def finalize_node(state: AgentState) -> dict:
    if state["route"] == "knowledge":
        answer = state["rag_answer"]
    elif state["route"] == "tool":
        answer = state["tool_answer"]
    else:
        raise ValueError(f"Unsupported finalize route: {state['route']}")

    return {
        "final_answer": answer,
    }


def fallback_node(state: AgentState) -> dict:
    return {
        "final_answer": "This request is not supported yet.",
    }


builder = StateGraph(AgentState)

builder.add_node("router", router_node)
builder.add_node("rag", rag_node)
builder.add_node("finalize", finalize_node)
builder.add_node("fallback", fallback_node)
builder.add_node("tool", mcp_tool_node)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "knowledge": "rag",
        "tool": "tool",
        "unsupported": "fallback",
    },
)

builder.add_edge("rag", "finalize")
builder.add_edge("tool", "finalize")
builder.add_edge("finalize", END)

builder.add_edge("fallback", END)

agent_graph = builder.compile()
