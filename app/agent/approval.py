
from langgraph.types import interrupt

from app.agent.state import ReleaseState


def request_human_approval(state: ReleaseState) -> dict:
    """
    Pause the workflow and ask a human to approve or reject
    the AI-recommended action.
    """

    decision = interrupt({
        "type": "human_approval",
        "question": "Do you approve the recommended action?",
        "repository": state["repository"],
        "run_id": state["run_id"],
        "recommended_action": state["recommended_action"],
        "reason": state["action_reason"],
        "options": ["approve", "reject"],
    })

    if isinstance(decision, dict):
        decision = decision.get("decision", "")

    decision = str(decision).strip().lower()

    if decision in ("approve", "approved", "yes"):
        return {
            "approval_status": "approved",
            "action_result": "Human approved the action. It is ready for execution.",
        }

    if decision in ("reject", "rejected", "no"):
        return {
            "approval_status": "rejected",
            "action_result": "Human rejected the action. No action was executed.",
        }

    raise ValueError(
        "Invalid approval decision. Use 'approve' or 'reject'."
    )
