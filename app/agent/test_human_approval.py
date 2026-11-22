
from langgraph.types import Command

from app.agent.graph import release_graph


def main():
    print("Testing human approval workflow...")

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Python CI Tests",
        "logs": """
Run pytest

test_calculate_total:
    result = calculate_total([100, 200])
    assert result == 300

AssertionError: assert 250 == 300

FAILED tests/test_calculator.py::test_calculate_total
1 failed, 4 passed
Error: Process completed with exit code 1.
""",
        "root_cause": "",
        "confidence": "",
        "recommended_action": "",
        "action_reason": "",
        "approval_status": "pending",
        "action_result": "",
        "error": "",
    }

    # A thread ID lets LangGraph identify this paused workflow.
    config = {
        "configurable": {
            "thread_id": "approval-test-001"
        }
    }

    # Start the workflow. It should pause at human approval.
    paused_result = release_graph.invoke(initial_state, config=config)

    interruptions = paused_result.get("__interrupt__", [])

    if not interruptions:
        raise RuntimeError(
            "Workflow did not pause for human approval."
        )

    print("\nWorkflow paused successfully.")
    print("Approval request:")
    print(interruptions[0].value)

    # Simulate a human approving the recommendation.
    print("\nSubmitting human approval...")

    final_result = release_graph.invoke(
        Command(resume={"decision": "reject"}),
        config=config,
    )

    print("\n========== FINAL RESULT ==========")
    print("Approval status:", final_result["approval_status"])
    print("Action result:", final_result["action_result"])

    if final_result["approval_status"] != "rejected":
        raise RuntimeError("Rejection test failed.")

    print("\nRejection test: SUCCESS")


if __name__ == "__main__":
    main()
