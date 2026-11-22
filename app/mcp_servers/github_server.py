
import os
import io
import zipfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# 1. Load configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")


# --------------------------------------------------
# 2. Validate configuration
# --------------------------------------------------

if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
    raise ValueError(
        "Missing GitHub configuration. Check your .env file."
    )


# --------------------------------------------------
# 3. Configure GitHub API
# --------------------------------------------------

BASE_URL = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "AI-Release-Assistant",
}

MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_EXTRACTED_BYTES = 50 * 1024 * 1024
MAX_LOG_CHARACTERS = 20000


# --------------------------------------------------
# 4. Create MCP server
# --------------------------------------------------

mcp = FastMCP("GitHub MCP Server")


# --------------------------------------------------
# 5. GitHub workflow runs
# --------------------------------------------------

@mcp.tool()
def get_workflow_runs(per_page: int = 10) -> dict:
    """
    Retrieve recent GitHub Actions workflow runs
    from the configured repository.
    """

    if not 1 <= per_page <= 100:
        return {
            "error": "per_page must be between 1 and 100."
        }

    endpoint = (
        f"{BASE_URL}/repos/{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/actions/runs"
    )

    params = {
        "per_page": per_page,
        "page": 1,
    }

    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=20.0,
        ) as client:

            response = client.get(
                endpoint,
                params=params,
            )

            response.raise_for_status()
            data = response.json()

            runs = []

            for run in data.get("workflow_runs", []):
                runs.append({
                    "id": run["id"],
                    "name": run["name"],
                    "run_number": run["run_number"],
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                    "branch": run["head_branch"],
                    "event": run["event"],
                    "created_at": run["created_at"],
                    "html_url": run["html_url"],
                    "head_sha": run["head_sha"],
                })

            return {
                "repository": (
                    f"{GITHUB_OWNER}/{GITHUB_REPO}"
                ),
                "total_count": data.get("total_count", 0),
                "returned_count": len(runs),
                "workflow_runs": runs,
            }

    except httpx.HTTPStatusError as error:
        return {
            "error": "GitHub API request failed.",
            "status_code": error.response.status_code,
        }

    except httpx.RequestError:
        return {
            "error": "Could not connect to GitHub API."
        }


# --------------------------------------------------
# 6. GitHub workflow logs (ZIP extraction)
# --------------------------------------------------

@mcp.tool()
def get_run_logs(run_id: int) -> dict:
    """
    Download and extract readable logs from a
    GitHub Actions workflow run ZIP archive.
    """

    if run_id <= 0:
        return {
            "error": "run_id must be a positive integer."
        }

    endpoint = (
        f"{BASE_URL}/repos/{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/actions/runs/{run_id}/logs"
    )

    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=60.0,
            follow_redirects=True,
        ) as client:

            response = client.get(endpoint)

            if response.status_code == 404:
                return {
                    "error": "Workflow run not found.",
                    "run_id": run_id,
                }

            response.raise_for_status()

            archive_bytes = response.content

            if not archive_bytes:
                return {
                    "error": "GitHub returned an empty log archive.",
                    "run_id": run_id,
                }

            if len(archive_bytes) > MAX_ARCHIVE_BYTES:
                return {
                    "error": "Log archive exceeds the 25 MB limit.",
                    "run_id": run_id,
                }

            # ZIP files normally start with PK.
            if not archive_bytes.startswith(b"PK"):
                return {
                    "error": "GitHub response is not a valid ZIP archive.",
                    "run_id": run_id,
                }

            extracted_logs = []
            total_extracted_bytes = 0

            with zipfile.ZipFile(
                io.BytesIO(archive_bytes)
            ) as archive:

                for file_info in archive.infolist():

                    if file_info.is_dir():
                        continue

                    # Ignore unusually large files.
                    total_extracted_bytes += file_info.file_size

                    if total_extracted_bytes > MAX_EXTRACTED_BYTES:
                        return {
                            "error": (
                                "Extracted logs exceed the "
                                "50 MB safety limit."
                            ),
                            "run_id": run_id,
                        }

                    # GitHub workflow log files are text files.
                    if not file_info.filename.lower().endswith(
                        (".txt", ".log")
                    ):
                        continue

                    with archive.open(file_info) as log_file:
                        content = log_file.read(
                            MAX_EXTRACTED_BYTES + 1
                        )

                    if len(content) > MAX_EXTRACTED_BYTES:
                        return {
                            "error": "Individual log file is too large.",
                            "run_id": run_id,
                        }

                    decoded_content = content.decode(
                        "utf-8",
                        errors="replace",
                    )

                    extracted_logs.append(
                        f"\n===== {file_info.filename} =====\n"
                        f"{decoded_content}"
                    )

            if not extracted_logs:
                return {
                    "error": "No readable text logs found in the archive.",
                    "run_id": run_id,
                }

            combined_logs = "\n".join(extracted_logs)

            truncated = (
                len(combined_logs) > MAX_LOG_CHARACTERS
            )

            combined_logs = combined_logs[
                :MAX_LOG_CHARACTERS
            ]

            return {
                "run_id": run_id,
                "status": "success",
                "files_extracted": len(extracted_logs),
                "truncated": truncated,
                "logs": combined_logs,
            }

    except zipfile.BadZipFile:
        return {
            "error": "GitHub returned an invalid ZIP archive.",
            "run_id": run_id,
        }

    except httpx.HTTPStatusError as error:
        return {
            "error": "GitHub API request failed.",
            "status_code": error.response.status_code,
            "run_id": run_id,
        }

    except httpx.RequestError:
        return {
            "error": "Could not connect to GitHub API.",
            "run_id": run_id,
        }

    except (OSError, EOFError, RuntimeError, zipfile.LargeZipFile):
        return {
            "error": "Could not safely extract workflow logs.",
            "run_id": run_id,
        }


# --------------------------------------------------
# 7. GitHub Pull Request diff
# --------------------------------------------------

@mcp.tool()
def get_pr_diff(pull_number: int) -> dict:
    """
    Retrieve the code changes (diff) for a GitHub Pull Request.
    """

    if pull_number <= 0:
        return {
            "error": "pull_number must be a positive integer."
        }

    endpoint = (
        f"{BASE_URL}/repos/{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/pulls/{pull_number}"
    )

    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=20.0,
        ) as client:

            response = client.get(
                endpoint,
                headers={
                    "Accept": "application/vnd.github.diff"
                },
            )

            if response.status_code == 404:
                return {
                    "error": "Pull Request not found.",
                    "pull_number": pull_number,
                }

            response.raise_for_status()

            return {
                "repository": (
                    f"{GITHUB_OWNER}/{GITHUB_REPO}"
                ),
                "pull_number": pull_number,
                "status": "success",
                "diff": response.text[:20000],
            }

    except httpx.HTTPStatusError as error:
        return {
            "error": "GitHub API request failed.",
            "status_code": error.response.status_code,
        }

    except httpx.RequestError:
        return {
            "error": "Could not connect to GitHub API."
        }


# --------------------------------------------------
# 8. Rerun GitHub workflow
# --------------------------------------------------

@mcp.tool()
def rerun_workflow(
    run_id: int,
    approved: bool = False,
) -> dict:
    """
    Rerun a GitHub Actions workflow.
    Requires an approval flag before sending the request.
    """

    if run_id <= 0:
        return {
            "error": "run_id must be a positive integer."
        }

    if not approved:
        return {
            "status": "approval_required",
            "message": (
                "Workflow was NOT rerun. "
                "Explicit approval is required."
            ),
            "run_id": run_id,
        }

    endpoint = (
        f"{BASE_URL}/repos/{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/actions/runs/{run_id}/rerun"
    )

    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=20.0,
        ) as client:

            response = client.post(endpoint)
            response.raise_for_status()

            return {
                "status": "rerun_requested",
                "run_id": run_id,
                "http_status": response.status_code,
                "message": (
                    "GitHub accepted the workflow rerun request."
                ),
            }

    except httpx.HTTPStatusError as error:
        return {
            "error": "GitHub API request failed.",
            "status_code": error.response.status_code,
            "run_id": run_id,
        }

    except httpx.RequestError:
        return {
            "error": "Could not connect to GitHub API.",
            "run_id": run_id,
        }


# --------------------------------------------------
# 9. Start MCP server
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()
