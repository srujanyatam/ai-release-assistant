
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEPLOYMENTS_FILE = PROJECT_ROOT / "data" / "deployments.json"
AUDIT_FILE = PROJECT_ROOT / "logs" / "operations_audit.jsonl"

mcp = FastMCP("Operations MCP Server")


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def write_audit_log(tool_name: str, status: str, details: dict) -> None:
    """
    Save an operation's outcome to the audit log.
    Each line represents one JSON event.
    """
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "status": status,
        "details": details
    }

    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")


def load_deployments() -> list:
    """
    Load and validate deployment records from the JSON file.
    """
    with DEPLOYMENTS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Deployment data must be a JSON object.")

    deployments = data.get("deployments")

    if not isinstance(deployments, list):
        raise ValueError("'deployments' must be a list.")

    for deployment in deployments:
        if not isinstance(deployment, dict):
            raise ValueError("Every deployment record must be an object.")

    return data, deployments


def generate_deployment_id(deployments: list) -> str:
    """
    Generate the next available deployment ID.
    """
    existing_numbers = []

    for deployment in deployments:
        deployment_id = deployment.get("deployment_id", "")
        match = re.fullmatch(r"DEP-(\d+)", deployment_id)

        if match:
            existing_numbers.append(int(match.group(1)))

    next_number = max(existing_numbers, default=0) + 1

    return f"DEP-{next_number:03d}"


# --------------------------------------------------
# TOOL 1: GET RECENT DEPLOYMENTS
# --------------------------------------------------

@mcp.tool()
def get_recent_deployments(limit: int = 10) -> dict:
    """
    Retrieve recent deployment records from the deployment data file.
    """
    if not 1 <= limit <= 100:
        result = {
            "error": "limit must be between 1 and 100."
        }
        write_audit_log("get_recent_deployments", "rejected", result)
        return result

    try:
        data, deployments = load_deployments()

        recent = list(reversed(deployments))[:limit]

        result = {
            "source": "local_sample_data",
            "total_deployments": len(deployments),
            "returned_count": len(recent),
            "deployments": recent
        }

        write_audit_log(
            "get_recent_deployments",
            "success",
            {"limit": limit, "returned_count": len(recent)}
        )

        return result

    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as error:
        result = {"error": str(error)}

        write_audit_log(
            "get_recent_deployments",
            "error",
            result
        )

        return result


# --------------------------------------------------
# TOOL 2: SIMULATED ROLLBACK
# --------------------------------------------------

@mcp.tool()
def rollback_to_commit(
    environment: str,
    target_commit_sha: str,
    approved: bool = False
) -> dict:
    """
    Simulate a rollback to a previously deployed commit.

    This operation only modifies local sample deployment data.
    It does not perform a real deployment.
    """
    environment = environment.strip().lower()
    target_commit_sha = target_commit_sha.strip().lower()

    if not environment or not target_commit_sha:
        result = {
            "error": "Environment and target commit SHA are required."
        }
        write_audit_log("rollback_to_commit", "rejected", result)
        return result

    if not re.fullmatch(r"[0-9a-f]{7,40}", target_commit_sha):
        result = {
            "error": "Commit SHA must contain 7 to 40 hexadecimal characters."
        }
        write_audit_log("rollback_to_commit", "rejected", result)
        return result

    if not approved:
        result = {
            "status": "approval_required",
            "message": "No rollback was performed. Approval is required.",
            "environment": environment,
            "target_commit_sha": target_commit_sha
        }

        write_audit_log(
            "rollback_to_commit",
            "approval_required",
            result
        )

        return result

    try:
        data, deployments = load_deployments()

        matching = [
            deployment for deployment in deployments
            if deployment.get("environment", "").lower() == environment
            and deployment.get("commit_sha", "").lower() == target_commit_sha
        ]

        if not matching:
            result = {
                "error": "Target commit not found in this environment's deployment history.",
                "environment": environment,
                "target_commit_sha": target_commit_sha
            }

            write_audit_log("rollback_to_commit", "rejected", result)
            return result

        previous_deployment = matching[-1]

        rollback_record = {
            "deployment_id": generate_deployment_id(deployments),
            "application": previous_deployment.get("application", "demo-app"),
            "environment": environment,
            "version": "simulated-rollback",
            "commit_sha": target_commit_sha,
            "status": "simulated",
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "operation": "simulated_rollback"
        }

        deployments.append(rollback_record)

        with DEPLOYMENTS_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        result = {
            "status": "simulated_rollback_success",
            "message": "A simulated rollback record was added. No real deployment was changed.",
            "rollback": rollback_record
        }

        write_audit_log(
            "rollback_to_commit",
            "success",
            rollback_record
        )

        return result

    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as error:
        result = {"error": str(error)}

        write_audit_log(
            "rollback_to_commit",
            "error",
            result
        )

        return result


# --------------------------------------------------
# START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()
