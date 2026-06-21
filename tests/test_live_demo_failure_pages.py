"""
Tests for live demo failure pages — public-demo-live-dry-run-v1
"""
import json
import os
import pytest

DEMO_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo"
)


class TestLiveDemoFailurePages:
    """Test failure messages meet live demo requirements."""

    @pytest.fixture
    def failure_msgs(self):
        path = os.path.join(DEMO_DIR, "demo_failure_messages.json")
        with open(path) as f:
            return json.load(f)

    def test_all_required_failure_types(self, failure_msgs):
        """All 10 failure types must be defined."""
        required = [
            "NO_REASONING_SOURCE",
            "SEARCH_AGENT_TIMEOUT",
            "SEARCH_AGENT_NO_RESULTS",
            "REPORT_RELEVANCE_FAILED",
            "REPORT_VALIDATION_FAILED",
            "ARTIFACT_MISSING",
            "RATE_LIMIT_EXCEEDED",
            "SAFETY_OR_SCOPE_BOUNDARY",
            "DEMO_TASK_NOT_ALLOWED",
            "UNKNOWN",
        ]
        failures = failure_msgs.get("failures", {})
        for r in required:
            assert r in failures, f"Missing failure type: {r}"

    def test_no_traceback_exposure(self, failure_msgs):
        """Failure messages must not expose traceback or secrets in user-facing content."""
        # Only check the failure messages themselves, not the metadata description
        failures = failure_msgs.get("failures", {})
        # Concatenate only user-facing fields: title + plain_message + suggested_action
        user_facing = ""
        for key, entry in failures.items():
            user_facing += entry.get("title", "") + " "
            user_facing += entry.get("plain_message", "") + " "
            user_facing += entry.get("suggested_action", "") + " "
        msgs_str = user_facing.lower()
        forbidden = ["traceback", "api_key", "api key", "secret", "sk-"]
        for term in forbidden:
            assert term not in msgs_str, f"Found forbidden term: {term}"

    def test_all_have_required_fields(self, failure_msgs):
        """All failure types must have title, plain_message, can_retry, suggested_action, show_to_user."""
        for key, entry in failure_msgs["failures"].items():
            assert "title" in entry, f"{key} missing title"
            assert "plain_message" in entry, f"{key} missing plain_message"
            assert "can_retry" in entry, f"{key} missing can_retry"
            assert "suggested_action" in entry, f"{key} missing suggested_action"
            assert entry.get("show_to_user") is True, f"{key} show_to_user must be true"

    def test_demo_task_not_allowed_cannot_retry(self, failure_msgs):
        """DEMO_TASK_NOT_ALLOWED must have can_retry=false."""
        entry = failure_msgs["failures"]["DEMO_TASK_NOT_ALLOWED"]
        assert entry["can_retry"] is False

    def test_rate_limit_exceeded_user_readable(self, failure_msgs):
        """Rate limit message must be user-readable in Chinese."""
        entry = failure_msgs["failures"]["RATE_LIMIT_EXCEEDED"]
        assert len(entry["plain_message"]) > 20
        assert entry["show_to_user"] is True