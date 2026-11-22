
import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api import main


TEST_SECRET = "local-webhook-test-secret"

TEST_PAYLOAD = {
    "action": "completed",
    "repository": {
        "full_name": "srujanyatam/ai-release-assistant"
    },
    "workflow_run": {
        "id": 12345,
        "name": "CI Tests",
        "status": "completed",
        "conclusion": "failure",
        "head_branch": "main",
        "head_sha": "abc1234567890",
        "html_url": "https://github.com/example/actions/runs/12345"
    }
}


def create_signature(payload: bytes) -> str:
    """Generate a GitHub-compatible test signature."""

    digest = hmac.new(
        TEST_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


class WebhookTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)
        self.patches = [
            patch.object(main, "GITHUB_WEBHOOK_SECRET", TEST_SECRET),
            patch.object(main, "GITHUB_OWNER", "srujanyatam"),
            patch.object(main, "GITHUB_REPO", "ai-release-assistant"),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_valid_failure_webhook(self):
        payload = json.dumps(
            TEST_PAYLOAD,
            separators=(",", ":"),
        ).encode("utf-8")

        signature = create_signature(payload)

        fake_interrupt = SimpleNamespace(
            value={
                "type": "human_approval",
                "question": "Do you approve the recommended action?",
                "options": ["approve", "reject"],
            }
        )

        fake_graph_result = {
            "__interrupt__": [fake_interrupt],
            "root_cause": "A test dependency failed.",
            "confidence": "High",
            "recommended_action": "Install the missing dependency.",
            "action_reason": "The dependency is required by the test.",
        }

        with (
            patch(
                "app.api.main.fetch_workflow_logs",
                new_callable=AsyncMock,
                return_value="Sample workflow failure logs",
            ) as mock_logs,
            patch.object(
                main.release_graph,
                "ainvoke",
                new_callable=AsyncMock,
                return_value=fake_graph_result,
            ) as mock_graph,
        ):
            response = self.client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "workflow_run",
                    "X-GitHub-Delivery": "test-delivery-001",
                },
            )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertEqual(
            result["status"],
            "approval_required",
        )

        self.assertEqual(
            result["thread_id"],
            "test-delivery-001",
        )

        self.assertEqual(
            result["analysis"]["root_cause"],
            "A test dependency failed.",
        )

        mock_logs.assert_awaited_once_with(12345)
        mock_graph.assert_awaited_once()

        print("Valid failure webhook and LangGraph approval: SUCCESS")

    def test_invalid_signature(self):
        payload = json.dumps(TEST_PAYLOAD).encode("utf-8")

        response = self.client.post(
            "/webhook/github",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid",
                "X-GitHub-Event": "workflow_run",
            },
        )

        self.assertEqual(response.status_code, 401)

        print("Invalid signature rejection: SUCCESS")

    def test_unsupported_event(self):
        payload = json.dumps(
            TEST_PAYLOAD,
            separators=(",", ":"),
        ).encode("utf-8")

        signature = create_signature(payload)

        response = self.client.post(
            "/webhook/github",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "push",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ignored")

        print("Unsupported event handling: SUCCESS")

    def test_human_approval(self):
        fake_result = {
            "approval_status": "approved",
            "action_result": "Simulated action executed successfully.",
            "error": "",
        }
        with patch.object(
            main.release_graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=fake_result,
        ) as mock_graph:
            response = self.client.post(
                "/approvals/test-delivery-001",
                json={"decision": "approve"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["approval_status"],
            "approved",
        )
        resume_command = mock_graph.await_args.args[0]
        self.assertEqual(
            resume_command.resume,
            {"decision": "approve"},
        )
        print("Human approval handling: SUCCESS")

    def test_human_rejection(self):
        fake_result = {
            "approval_status": "rejected",
            "action_result": "Human rejected the action. No action was executed.",
            "error": "",
        }
        with patch.object(
            main.release_graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=fake_result,
        ) as mock_graph:
            response = self.client.post(
                "/approvals/test-delivery-002",
                json={"decision": "reject"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["approval_status"],
            "rejected",
        )
        resume_command = mock_graph.await_args.args[0]
        self.assertEqual(
            resume_command.resume,
            {"decision": "reject"},
        )
        print("Human rejection handling: SUCCESS")

    def test_invalid_approval_decision(self):
        response = self.client.post(
            "/approvals/test-delivery-003",
            json={"decision": "maybe"},
        )
        self.assertEqual(response.status_code, 400)
        print("Invalid approval rejection: SUCCESS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
