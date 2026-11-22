
import json
from pathlib import Path
from unittest.mock import patch

from langgraph.types import Command

from app.agent.graph import release_graph


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = PROJECT_ROOT / "logs" / "execution_audit.jsonl"


def main():
    print("Testing rejected action execution safeguard...")

    initial_state = {
        "repository": "srujanyatam/ai-release-assistant",
        "run_id": 12346,
        "workflow_name": "Python CI Tests",
        "logs": "Simulated failure in calculate_total.",
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
            "thread_id": "rejected-execution-test-001"
        }
    }

    mock_analysis = {
        "root_cause": "Incorrect calculation logic.",
        "confidence": "High",
        "recommended_action": "Correct the calculation logic.",
        "action_reason": "The current calculation produces an incorrect result.",
    }

    # Remember the existing audit records.
    existing_records = []

    if AUDIT_FILE.exists():
        existing_records = [
            json.loads(line)
            for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    with patch(
        "app.agent.nodes.generate_response",
        return_value=json.dumps(mock_analysis),
    ):
        paused_result = release_graph.invoke(initial_state, config=config)

        if not paused_result.get("__interrupt__"):
            raise RuntimeError("Workflow did not request approval.")

        print("\nWorkflow paused for human approval.")

        final_result = release_graph.invoke(
            Command(resume={"decision": "reject"}),
            config=config,
        )

    print("\nApproval status:", final_result.get("approval_status"))
    print("Action result:", final_result.get("action_result"))

    if final_result.get("approval_status") != "rejected":
        raise RuntimeError("Rejection was not recorded.")

    if "No action was executed" not in final_result.get("action_result", ""):
        raise RuntimeError("Unexpected rejection result.")

    # Verify that this rejected run did not create an audit record.
    current_records = []

    if AUDIT_FILE.exists():
        current_records = [
            json.loads(line)
            for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    rejected_run_records = [
        record for record in current_records
        if record.get("run_id") == 12346
    ]

    if rejected_run_records:
        raise RuntimeError(
            "FAIL: Rejected action was unexpectedly recorded as executed."
        )

    if len(current_records) != len(existing_records):
        raise RuntimeError(
            "FAIL: The audit file changed during the rejected execution test."
        )

    print("\nRejected execution safeguard: SUCCESS")
    print("No execution audit record was created.")


if __name__ == "__main__":
    main()
