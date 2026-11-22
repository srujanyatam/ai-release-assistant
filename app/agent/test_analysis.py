
from app.agent.nodes import analyze_failure


def main():
    test_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Python CI Tests",
        "logs": """
        Run pytest

        ==================================== FAILURES ====================================
        __________________________ test_calculate_total __________________________

        def test_calculate_total():
            result = calculate_total([100, 200])
            assert result == 300

        AssertionError: assert 250 == 300

        =========================== short test summary info ===========================
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

    print("Testing AI failure analysis...\n")

    result = analyze_failure(test_state)

    print("Root cause:")
    print(result.get("root_cause", "Not available"))

    print("\nConfidence:")
    print(result.get("confidence", "Not available"))

    print("\nRecommended action:")
    print(result.get("recommended_action", "Not available"))

    print("\nReason:")
    print(result.get("action_reason", "Not available"))

    print("\nError:")
    print(result.get("error", "None"))


if __name__ == "__main__":
    main()
