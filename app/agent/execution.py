
import json
from datetime import datetime, timezone
from pathlib import Path

from app.agent.state import ReleaseState


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = PROJECT_ROOT / "logs" / "execution_audit.jsonl"


def execute_approved_action(state: ReleaseState) -> dict:
    """
    Execute a safe simulated action only after human approval.
    Record the execution attempt in an audit log.
    """

    if state.get("approval_status") != "approved":
        return {
            "action_result": (
                "Execution blocked: explicit human approval is missing."
            )
        }

    if state.get("error"):
        return {
            "action_result": (
                "Execution blocked: failure analysis contains an error."
            )
        }

    recommended_action = state.get("recommended_action", "").strip()

    if not recommended_action:
        return {
            "action_result": (
                "Execution blocked: no valid recommended action exists."
            )
        }

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": state.get("repository", ""),
        "run_id": state.get("run_id"),
        "approval_status": "approved",
        "recommended_action": recommended_action,
        "execution_type": "simulated",
        "status": "completed",
    }

    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with AUDIT_FILE.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record) + "\n")

    except OSError as error:
        return {
            "action_result": (
                f"Simulated execution could not be audited: {error}"
            )
        }

    return {
        "action_result": (
            "Simulated action executed successfully. "
            "No real GitHub or deployment changes were made."
        )
    }
