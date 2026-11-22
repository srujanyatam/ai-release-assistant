import json
from typing import Any
from app.agent.llm import generate_response
from app.agent.state import ReleaseState


def analyze_failure(state: ReleaseState) -> dict[str, Any]:
    """
    Analyse GitHub Actions failure logs using Gemini.

    Reads:
        repository
        run_id
        workflow_name
        logs

    Updates:
        root_cause
        confidence
        recommended_action
        action_reason
        error
    """

    logs = state.get("logs", "")

    if not logs or not logs.strip():
        return {
            "error": "Cannot analyse failure: workflow logs are empty."
        }

    prompt = f"""
You are an experienced CI/CD and software reliability engineer.

Analyse the following GitHub Actions workflow failure.

Repository: {state.get("repository", "Unknown")}
Workflow: {state.get("workflow_name", "Unknown")}
Run ID: {state.get("run_id", "Unknown")}

WORKFLOW LOGS:
{logs[:15000]}

Identify the most likely failure cause and recommend a practical fix.

Return ONLY a valid JSON object with these exact fields:

{{
    "root_cause": "Explanation of the likely failure",
    "confidence": "High, Medium, or Low",
    "recommended_action": "Specific recommended fix",
    "action_reason": "Why this fix should resolve the failure"
}}

Do not invent information that is not supported by the logs.
If the evidence is insufficient, clearly say so.
"""

    try:
        response = generate_response(prompt)

        # Remove optional Markdown code fences.
        cleaned = response.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()

        analysis = json.loads(cleaned)

        required_fields = [
            "root_cause",
            "confidence",
            "recommended_action",
            "action_reason",
        ]

        if not all(
            isinstance(analysis.get(field), str)
            and analysis[field].strip()
            for field in required_fields
        ):
            raise ValueError("Gemini response is missing required fields.")

        return {
            "root_cause": analysis["root_cause"],
            "confidence": analysis["confidence"],
            "recommended_action": analysis["recommended_action"],
            "action_reason": analysis["action_reason"],
            "error": "",
        }

    except Exception as error:
        return {
            "error": f"Failure analysis failed: {type(error).__name__}: {error}"
        }


def route_after_analysis(state: ReleaseState) -> str:
    """
    Continue to human approval only when analysis is valid.
    Otherwise, stop the workflow safely.
    """

    required_fields = [
        "root_cause",
        "confidence",
        "recommended_action",
        "action_reason",
    ]

    # Stop if the analysis node reported an error.
    if state.get("error"):
        return "stop"

    # Stop if any required analysis field is missing or empty.
    for field in required_fields:
        value = state.get(field, "")
        if not isinstance(value, str) or not value.strip():
            return "stop"

    return "request_approval"
