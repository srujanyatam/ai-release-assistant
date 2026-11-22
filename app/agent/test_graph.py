
from langgraph.types import Command
from app.agent.graph import release_graph


def main():
    print("Testing complete LangGraph workflow...")

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

    config = {
        "configurable": {
            "thread_id": "test-graph-thread-001"
        }
    }

    print("\n1. Invoking workflow (will pause for human approval)...")
    paused_result = release_graph.invoke(initial_state, config=config)

    interruptions = paused_result.get("__interrupt__", [])
    
    if interruptions:
        print("\nWorkflow paused successfully at human approval node.")
        approval_request = interruptions[0].value
        print("Approval Request Details:")
        print(f"  - Repository: {approval_request.get('repository')}")
        print(f"  - Run ID: {approval_request.get('run_id')}")
        print(f"  - Recommended Action: {approval_request.get('recommended_action')}")
        print(f"  - Reason: {approval_request.get('reason')}")

        print("\n2. Resuming workflow with 'approve' decision...")
        final_result = release_graph.invoke(
            Command(resume={"decision": "approve"}),
            config=config,
        )
    else:
        final_result = paused_result

    print("\n========== WORKFLOW RESULT ==========")
    print("Root cause:", final_result.get("root_cause"))
    print("Confidence:", final_result.get("confidence"))
    print("Recommended action:", final_result.get("recommended_action"))
    print("Reason:", final_result.get("action_reason"))
    print("Approval Status:", final_result.get("approval_status"))
    print("Action Result:", final_result.get("action_result"))
    print("Error:", final_result.get("error"))

    if final_result.get("error"):
        print("\nLangGraph workflow test: COMPLETED WITH ERRORS")
    else:
        print("\nLangGraph workflow test: SUCCESS")


if __name__ == "__main__":
    main()


