
import json
from unittest.mock import patch

from langgraph.types import Command

from app.agent.graph import release_graph


def main():
    thread_id = "approved-execution-test-001"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    fake_analysis = {
        "root_cause": "A required Python dependency is missing.",
        "confidence": "High",
        "recommended_action": "Install the missing dependency.",
        "action_reason": "The workflow logs show ModuleNotFoundError.",
    }

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Approved Execution Test",
        "logs": "ModuleNotFoundError: No module named 'requests'",
        "root_cause": "",
        "confidence": "",
        "recommended_action": "",
        "action_reason": "",
        "approval_status": "pending",
        "action_result": "",
        "error": "",
    }

    print("Testing approved execution path...")

    with patch(
        "app.agent.nodes.generate_response",
        return_value=json.dumps(fake_analysis),
    ):
        paused = release_graph.invoke(
            initial_state,
            config=config,
        )

    if not paused.get("__interrupt__"):
        raise RuntimeError("Graph did not pause for approval.")

    print("Graph paused successfully.")

    result = release_graph.invoke(
        Command(resume={"decision": "approve"}),
        config=config,
    )

    print("Approval status:", result.get("approval_status"))
    print("Action result:", result.get("action_result"))

    if result.get("approval_status") != "approved":
        raise RuntimeError("Approval was not recorded.")

    if "simulated action executed successfully" not in (
        result.get("action_result", "").lower()
    ):
        raise RuntimeError("Simulated execution did not complete.")

    print("\nAPPROVED EXECUTION TEST: SUCCESS")


if __name__ == "__main__":
    main()
