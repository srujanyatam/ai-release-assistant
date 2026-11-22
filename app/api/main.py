
import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command
from pydantic import BaseModel

from app.agent.graph import release_graph


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")


# --------------------------------------------------
# 2. FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="AI Release Assistant",
    description="AI-powered CI/CD failure investigation and release assistance.",
    version="1.0.0",
)


# --------------------------------------------------
# 3. Approval request model
# --------------------------------------------------

class ApprovalRequest(BaseModel):
    decision: str


# --------------------------------------------------
# 4. GitHub signature verification
# --------------------------------------------------

def verify_github_signature(
    payload: bytes,
    signature: str | None,
) -> bool:

    if not GITHUB_WEBHOOK_SECRET or not signature:
        return False

    expected_signature = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


# --------------------------------------------------
# 5. GitHub MCP log retrieval
# --------------------------------------------------

async def fetch_workflow_logs(run_id: int) -> str:
    """
    Connect to the GitHub MCP server and retrieve workflow logs.
    """

    client = MultiServerMCPClient(
        {
            "github": {
                "transport": "stdio",
                "command": str(
                    PROJECT_ROOT
                    / ".venv"
                    / "Scripts"
                    / "python.exe"
                ),
                "args": [
                    str(
                        PROJECT_ROOT
                        / "app"
                        / "mcp_servers"
                        / "github_server.py"
                    )
                ],
                "env": os.environ.copy(),
            }
        }
    )

    tools = await client.get_tools()

    logs_tool = next(
        (
            tool
            for tool in tools
            if tool.name == "get_run_logs"
        ),
        None,
    )

    if logs_tool is None:
        raise RuntimeError("GitHub MCP get_run_logs tool not found.")

    result = await logs_tool.ainvoke({"run_id": run_id})

    # MCP adapter returns text content blocks.
    if isinstance(result, list):
        text_parts = [
            item.get("text", "")
            for item in result
            if isinstance(item, dict)
        ]
        result_text = "\n".join(text_parts)
    else:
        result_text = str(result)

    try:
        parsed_result = json.loads(result_text)
    except json.JSONDecodeError:
        raise RuntimeError("GitHub MCP returned an invalid response.")

    if parsed_result.get("error"):
        raise RuntimeError(parsed_result["error"])

    logs = parsed_result.get("logs")

    if not isinstance(logs, str) or not logs.strip():
        raise RuntimeError("GitHub MCP returned empty workflow logs.")

    return logs


# --------------------------------------------------
# 6. Helpers for LangGraph interrupts
# --------------------------------------------------

def get_pending_approval(result: dict) -> list:
    """
    Convert LangGraph interrupt objects into API-friendly data.
    """

    pending = []

    for item in result.get("__interrupt__", []):
        value = getattr(item, "value", None)

        if value is not None:
            pending.append(value)

    return pending


# --------------------------------------------------
# 7. Root endpoint
# --------------------------------------------------

@app.get("/")
async def root():
    return {
        "application": "AI Release Assistant",
        "status": "running",
        "message": "API server is ready.",
    }


# --------------------------------------------------
# 8. Health endpoint
# --------------------------------------------------

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Release Assistant API",
        "webhook_secret_configured": bool(GITHUB_WEBHOOK_SECRET),
    }


# --------------------------------------------------
# 9. GitHub webhook endpoint
# --------------------------------------------------

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
):
    """
    Receive a GitHub workflow failure, fetch its logs,
    and start the LangGraph investigation.
    """

    payload = await request.body()

    if not verify_github_signature(payload, x_hub_signature_256):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing GitHub webhook signature.",
        )

    if x_github_event != "workflow_run":
        return {
            "status": "ignored",
            "reason": "Unsupported GitHub event.",
        }

    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        )

    workflow_run = data.get("workflow_run") or {}
    repository = data.get("repository") or {}

    if not workflow_run or not repository:
        raise HTTPException(
            status_code=400,
            detail="Missing workflow or repository information.",
        )

    if (
        data.get("action") != "completed"
        or workflow_run.get("conclusion") != "failure"
    ):
        return {
            "status": "ignored",
            "reason": "Workflow did not complete with failure.",
        }

    run_id = workflow_run.get("id")

    if type(run_id) is not int or run_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid workflow run ID.",
        )

    repository_name = repository.get("full_name", "")

    expected_repository = f"{GITHUB_OWNER}/{GITHUB_REPO}"

    if repository_name.lower() != expected_repository.lower():
        raise HTTPException(
            status_code=403,
            detail="Webhook repository does not match configured repository.",
        )

    # Fetch actual logs using GitHub MCP.
    try:
        logs = await fetch_workflow_logs(run_id)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not retrieve workflow logs: {error}",
        )

    # A stable thread ID allows this investigation to resume later.
    thread_id = x_github_delivery or str(uuid.uuid4())

    initial_state = {
        "repository": repository_name,
        "run_id": run_id,
        "workflow_name": workflow_run.get("name") or "Unknown",
        "logs": logs,
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
            "thread_id": thread_id,
        }
    }

    try:
        result = await release_graph.ainvoke(
            initial_state,
            config=config,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph investigation failed: {error}",
        )

    pending_approval = get_pending_approval(result)

    if pending_approval:
        return {
            "status": "approval_required",
            "thread_id": thread_id,
            "message": "AI analysis completed. Human approval is required.",
            "approval": pending_approval,
            "analysis": {
                "root_cause": result.get("root_cause"),
                "confidence": result.get("confidence"),
                "recommended_action": result.get("recommended_action"),
                "action_reason": result.get("action_reason"),
            },
        }

    return {
        "status": "investigation_stopped",
        "thread_id": thread_id,
        "error": result.get("error"),
        "action_result": result.get("action_result"),
        "message": "The investigation did not reach human approval.",
    }


# --------------------------------------------------
# 10. Human approval endpoint
# --------------------------------------------------

@app.post("/approvals/{thread_id}")
async def submit_approval(
    thread_id: str,
    approval: ApprovalRequest,
):
    """
    Resume a paused LangGraph investigation with
    an explicit human approval or rejection.
    """

    decision = approval.decision.strip().lower()

    if decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approve' or 'reject'.",
        )

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        result = await release_graph.ainvoke(
            Command(
                resume={
                    "decision": decision,
                }
            ),
            config=config,
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not resume approval workflow: {error}",
        )

    return {
        "status": "completed",
        "thread_id": thread_id,
        "approval_status": result.get("approval_status"),
        "action_result": result.get("action_result"),
        "error": result.get("error"),
        "message": (
            "Approval workflow resumed successfully."
        ),
    }
