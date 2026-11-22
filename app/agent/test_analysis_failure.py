
from unittest.mock import patch

from app.agent.graph import release_graph


def main():
    print("Testing analysis failure safeguard...")

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Python CI Tests",
        "logs": """
Run pytest

FAILED tests/test_calculator.py::test_calculate_total
AssertionError: assert 250 == 300
""",
        "root_cause": "",
        "confidence": "",
        "recommended_action": "",
        "action_reason": "",
        "approval_status": "pending",
        "action_result": "",
        "error": "",
    }

    config = {
        "configurable": {
            "thread_id": "analysis-failure-test-001"
        }
    }

    # Simulate an unavailable LLM without calling an actual provider.
    with patch(
        "app.agent.nodes.generate_response",
        side_effect=RuntimeError("Simulated LLM provider failure."),
    ):
        result = release_graph.invoke(
            initial_state,
            config=config,
        )

    print("\n========== TEST RESULT ==========")
    print("Error:", result.get("error"))
    print("Approval status:", result.get("approval_status"))
    print("Recommended action:", result.get("recommended_action"))

    # The analysis must report an error.
    if not result.get("error"):
        raise RuntimeError("Expected analysis error was not reported.")

    # The workflow must not request human approval.
    if result.get("__interrupt__"):
        raise RuntimeError(
            "FAIL: Workflow requested approval despite analysis failure."
        )

    # No recommendation should be available.
    if result.get("recommended_action", "").strip():
        raise RuntimeError(
            "FAIL: Recommendation exists despite analysis failure."
        )

    print("\nAnalysis failure safeguard: SUCCESS")
    print("Workflow stopped without requesting human approval.")


if __name__ == "__main__":
    main()
