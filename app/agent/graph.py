
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import ReleaseState
from app.agent.nodes import analyze_failure
from app.agent.approval import request_human_approval
from app.agent.execution import execute_approved_action


def route_after_analysis(state: ReleaseState) -> str:
    """Continue only when failure analysis is valid."""

    required_fields = [
        "root_cause",
        "confidence",
        "recommended_action",
        "action_reason",
    ]

    if state.get("error"):
        return "stop"

    for field in required_fields:
        value = state.get(field, "")

        if not isinstance(value, str) or not value.strip():
            return "stop"

    return "request_approval"


def route_after_approval(state: ReleaseState) -> str:
    """Execute only after explicit human approval."""

    if state.get("approval_status") == "approved":
        return "execute"

    return "stop"


def build_graph():
    workflow = StateGraph(ReleaseState)

    workflow.add_node("analyze_failure", analyze_failure)
    workflow.add_node("human_approval", request_human_approval)
    workflow.add_node("execute_action", execute_approved_action)

    workflow.add_edge(START, "analyze_failure")

    workflow.add_conditional_edges(
        "analyze_failure",
        route_after_analysis,
        {
            "request_approval": "human_approval",
            "stop": END,
        },
    )

    workflow.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "execute": "execute_action",
            "stop": END,
        },
    )

    workflow.add_edge("execute_action", END)

    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


release_graph = build_graph()
