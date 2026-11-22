
import json
from pathlib import Path
from unittest.mock import patch

from langgraph.types import Command

from app.agent.graph import release_graph


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = PROJECT_ROOT / "logs" / "execution_audit.jsonl"


def main():
    print("Testing approved action execution...")

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12345,
        "workflow_name": "Python CI Tests",
        "logs": "Simulated failure: test_calculate_total expected 300 but received 250.",
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
            "thread_id": "execution-approval-test-001"
        }
    }

    # Start the workflow and wait for human approval.
    with patch(
        "app.agent.nodes.generate_response",
        return_value=json.dumps({
            "root_cause": "The calculate_total function returns an incorrect sum.",
            "confidence": "High",
            "recommended_action": "Correct the calculation logic in calculate_total.",
            "action_reason": "The function should return 300 for the input [100, 200]."
        }),
    ):
        paused_result = release_graph.invoke(
            initial_state,
            config=config,
        )

    interruptions = paused_result.get("__interrupt__", [])

    if not interruptions:
        raise RuntimeError("Workflow did not request human approval.")

    print("\nWorkflow paused for approval.")

    # Simulate explicit human approval.
    final_result = release_graph.invoke(
        Command(resume={"decision": "approve"}),
        config=config,
    )

    print("\n========== FINAL RESULT ==========")
    print("Approval status:", final_result.get("approval_status"))
    print("Action result:", final_result.get("action_result"))

    if final_result.get("approval_status") != "approved":
        raise RuntimeError("Approval was not recorded.")

    expected_message = (
        "Simulated action executed successfully. "
        "No real GitHub or deployment changes were made."
    )

    if final_result.get("action_result") != expected_message:
        raise RuntimeError("Simulated execution did not complete.")

    if not AUDIT_FILE.exists():
        raise RuntimeError("Execution audit file was not created.")

    records = [
        json.loads(line)
        for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    matching_records = [
        record
        for record in records
        if record.get("run_id") == 12345
        and record.get("repository") == "srujanyatam/ai-release-assistant"
    ]

    if not matching_records:
        raise RuntimeError("Execution audit record was not found.")

    latest_record = matching_records[-1]

    if latest_record.get("status") != "completed":
        raise RuntimeError("Audit record does not show completed execution.")

    if latest_record.get("execution_type") != "simulated":
        raise RuntimeError("Unexpected execution type in audit record.")

    print("\nAudit record verified:")
    print(json.dumps(latest_record, indent=2))

    print("\nApproved execution test: SUCCESS")


if __name__ == "__main__":
    main()
