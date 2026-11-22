
from typing import TypedDict


class ReleaseState(TypedDict):
    """
    Shared state for the AI Release Assistant.

    Every LangGraph node can read from and update this state.
    """

    # GitHub workflow information
    repository: str
    run_id: int | None
    workflow_name: str

    # Failure investigation
    logs: str
    root_cause: str
    confidence: str

    # AI recommendation
    recommended_action: str
    action_reason: str

    # Human approval
    approval_status: str

    # Action execution
    action_result: str

    # Error handling
    error: str
