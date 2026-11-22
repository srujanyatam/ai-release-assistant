
from langgraph.types import Command

from app.agent.graph import release_graph


def main():
    config = {
        "configurable": {
            "thread_id": "approval-resume-test-001"
        }
    }

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Approval Resume Test",
        "logs": "ModuleNotFoundError: No module named 'requests'",
        "root_cause": "",
        "confidence": "",
        "recommended_action": "",
        "action_reason": "",
        "approval_status": "pending",
        "action_result": "",
        "error": "",
    }

    print("Starting real LangGraph approval test...")

    paused_result = release_graph.invoke(
        initial_state,
        config=config,
    )

    interrupts = paused_result.get("__interrupt__", [])

    if not interrupts:
        raise RuntimeError(
            "Graph did not pause for human approval. "
            f"Error: {paused_result.get('error')}"
        )

    print("Graph paused successfully for human approval.")

    print("\nResuming graph with human rejection...")

    resumed_result = release_graph.invoke(
        Command(resume={"decision": "reject"}),
        config=config,
    )

    print("\nApproval status:", resumed_result.get("approval_status"))
    print("Action result:", resumed_result.get("action_result"))

    if resumed_result.get("approval_status") != "rejected":
        raise RuntimeError("Graph did not record the rejection.")

    if "No action was executed" not in resumed_result.get("action_result", ""):
        raise RuntimeError("Rejection did not prevent execution.")

    print("\nREAL LANGGRAPH APPROVAL/RESUME TEST: SUCCESS")


if __name__ == "__main__":
    main()
