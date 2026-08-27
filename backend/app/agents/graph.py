from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.a2a_risk_node import a2a_risk_node
from app.agents.approval_node import approval_node
from app.agents.approved_action_node import approved_action_node
from app.agents.mcp_tool_node import mcp_tool_node
from app.agents.rag_node import rag_node
from app.agents.router import planner_node
from app.agents.sql_node import sql_node
from app.agents.state import AgentRoute, AgentState
from app.agents.synthesis_node import synthesis_node
from app.agents.write_gate_node import write_gate_node


def _planned_routes(state: AgentState) -> list[AgentRoute]:
    routes = list(state.get("planned_routes") or [])
    if routes:
        return routes
    route = state.get("route")
    return [route] if route else ["unsupported"]


def route_after_planner(state: AgentState) -> str | list[Send]:
    """Single-route fast path or LangGraph fan-out via Send."""

    routes = _planned_routes(state)
    mapping = {
        "knowledge": "rag",
        "sql": "sql",
        "tool": "tool",
        "external_risk_assessment": "a2a_risk",
    }

    if not routes or routes == ["unsupported"] or routes[0] == "unsupported":
        return "fallback"

    executable = [route for route in routes if route in mapping]
    if not executable:
        return "fallback"

    if len(executable) == 1:
        return mapping[executable[0]]

    return [Send(mapping[route], state) for route in executable]


def after_capability(state: AgentState) -> str:
    if state.get("requires_synthesis"):
        return "synthesize"
    return "finalize"


def route_after_a2a(state: AgentState) -> str:
    """A2A may request HITL for high-risk GitHub escalation."""

    # Composite paths synthesize first; HITL runs after (see after_synthesize).
    if state.get("requires_synthesis"):
        return "synthesize"
    if state.get("requires_approval"):
        return "approval"
    return "finalize"


def route_after_tool(state: AgentState) -> str:
    if state.get("requires_approval"):
        return "approval"
    if state.get("requires_synthesis"):
        return "synthesize"
    return "finalize"


def route_after_approval(state: AgentState) -> str:
    if state.get("approval_granted"):
        return "approved_action"
    return "finalize"


def after_synthesize(state: AgentState) -> str:
    # High-risk A2A may set requires_approval while also synthesizing.
    if state.get("requires_approval"):
        return "approval"
    if state.get("may_require_write"):
        return "write_gate"
    return "finalize"


def after_write_gate(state: AgentState) -> str:
    if state.get("requires_approval"):
        return "approval"
    return "finalize"


def finalize_node(state: AgentState) -> dict:
    from app.agents.execution_trace import node_trace

    a2a_answer = (state.get("a2a_answer") or "").strip()

    # Explicit reject/approve outcomes from HITL take precedence over synthesis.
    if state.get("approval_granted") is False and state.get("tool_answer"):
        reject_note = state["tool_answer"]
        if a2a_answer:
            return {
                "final_answer": f"{a2a_answer}\n\n{reject_note}",
                **node_trace("finalize"),
            }
        return {
            "final_answer": reject_note,
            **node_trace("finalize"),
        }

    if state.get("action_result") and state.get("tool_answer"):
        action_note = state["tool_answer"]
        if a2a_answer:
            return {
                "final_answer": f"{a2a_answer}\n\n{action_note}",
                **node_trace("finalize"),
            }
        return {
            "final_answer": action_note,
            **node_trace("finalize"),
        }

    if state.get("synthesis_answer"):
        return {
            "final_answer": state["synthesis_answer"],
            **node_trace("finalize"),
        }

    route = state.get("route") or (_planned_routes(state) or ["unsupported"])[0]

    if route == "knowledge":
        return {
            "final_answer": state["rag_answer"],
            **node_trace("finalize"),
        }

    if route == "sql":
        return {
            "final_answer": state["sql_answer"],
            **node_trace("finalize"),
        }

    if route == "tool":
        return {
            "final_answer": state["tool_answer"],
            **node_trace("finalize"),
        }

    if route == "external_risk_assessment":
        # Waiting for HITL: surface assessment + approval message.
        if state.get("requires_approval") and state.get("tool_answer") and a2a_answer:
            return {
                "final_answer": f"{a2a_answer}\n\n{state['tool_answer']}",
                **node_trace("finalize"),
            }
        return {
            "final_answer": state["a2a_answer"],
            **node_trace("finalize"),
        }

    raise ValueError(f"Unsupported finalize route: {route}")


def fallback_node(state: AgentState) -> dict:
    from app.agents.execution_trace import node_trace

    return {
        "final_answer": "This request is not supported yet.",
        **node_trace(
            "fallback",
            route="unsupported",
        ),
    }


def build_agent_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("planner", planner_node)
    graph_builder.add_node("rag", rag_node)
    graph_builder.add_node("sql", sql_node)
    graph_builder.add_node("tool", mcp_tool_node)
    graph_builder.add_node("a2a_risk", a2a_risk_node)
    graph_builder.add_node("synthesize", synthesis_node)
    graph_builder.add_node("write_gate", write_gate_node)
    graph_builder.add_node("finalize", finalize_node)
    graph_builder.add_node("fallback", fallback_node)
    graph_builder.add_node("approval", approval_node)
    graph_builder.add_node("approved_action", approved_action_node)

    graph_builder.add_edge(START, "planner")

    graph_builder.add_conditional_edges(
        "planner",
        route_after_planner,
        ["rag", "sql", "tool", "a2a_risk", "fallback"],
    )

    graph_builder.add_conditional_edges(
        "rag",
        after_capability,
        {
            "synthesize": "synthesize",
            "finalize": "finalize",
        },
    )
    graph_builder.add_conditional_edges(
        "sql",
        after_capability,
        {
            "synthesize": "synthesize",
            "finalize": "finalize",
        },
    )
    graph_builder.add_conditional_edges(
        "tool",
        route_after_tool,
        {
            "approval": "approval",
            "synthesize": "synthesize",
            "finalize": "finalize",
        },
    )
    graph_builder.add_conditional_edges(
        "a2a_risk",
        route_after_a2a,
        {
            "approval": "approval",
            "synthesize": "synthesize",
            "finalize": "finalize",
        },
    )

    graph_builder.add_conditional_edges(
        "synthesize",
        after_synthesize,
        {
            "write_gate": "write_gate",
            "finalize": "finalize",
        },
    )
    graph_builder.add_conditional_edges(
        "write_gate",
        after_write_gate,
        {
            "approval": "approval",
            "finalize": "finalize",
        },
    )

    graph_builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "approved_action": "approved_action",
            "finalize": "finalize",
        },
    )
    graph_builder.add_edge("approved_action", "finalize")
    graph_builder.add_edge("finalize", END)
    graph_builder.add_edge("fallback", END)

    return graph_builder


builder = build_agent_graph()

# Default for local development and tests. Production may replace this during
# application lifespan when CHECKPOINT_BACKEND=postgres.
checkpointer = InMemorySaver()

agent_graph = builder.compile(
    checkpointer=checkpointer,
)


def compile_agent_graph(active_checkpointer):
    """Compile the agent graph with the provided checkpointer."""

    return builder.compile(
        checkpointer=active_checkpointer,
    )
