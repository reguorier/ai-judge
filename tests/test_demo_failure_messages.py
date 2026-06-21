"""
Test Demo Failure Messages
public-demo-readiness-v1.0.0
"""

import json
import os
import pytest


@pytest.fixture
def failure_messages():
    path = os.path.expanduser(
        "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo/demo_failure_messages.json"
    )
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def failures(failure_messages):
    return failure_messages["failures"]


def test_all_10_types_present(failures):
    required = [
        "NO_REASONING_SOURCE", "SEARCH_AGENT_TIMEOUT", "SEARCH_AGENT_NO_RESULTS",
        "REPORT_RELEVANCE_FAILED", "REPORT_VALIDATION_FAILED", "ARTIFACT_MISSING",
        "RATE_LIMIT_EXCEEDED", "SAFETY_OR_SCOPE_BOUNDARY", "DEMO_TASK_NOT_ALLOWED", "UNKNOWN",
    ]
    for r in required:
        assert r in failures, f"Missing failure type: {r}"
    assert len(failures) == 10


def test_each_failure_required_fields(failures):
    required = {"title", "plain_message", "can_retry", "suggested_action", "show_to_user"}
    for key, msg in failures.items():
        missing = required - set(msg.keys())
        assert not missing, f"Failure {key} missing fields: {missing}"


def test_no_secrets_in_messages(failures):
    forbidden = ["traceback", "api_key", "secret", "password", "sk-"]
    for key, msg in failures.items():
        text = json.dumps(msg).lower()
        for bad in forbidden:
            assert bad not in text, f"{key} exposes '{bad}'"


def test_show_to_user_true_for_all(failures):
    for key, msg in failures.items():
        assert msg["show_to_user"] is True, f"{key} must have show_to_user=true"


def test_can_retry_boolean(failures):
    for key, msg in failures.items():
        assert isinstance(msg["can_retry"], bool), f"{key} can_retry must be boolean"


def test_all_messages_not_empty(failures):
    for key, msg in failures.items():
        assert len(msg["title"]) > 0, f"{key} title is empty"
        assert len(msg["plain_message"]) > 0, f"{key} plain_message is empty"
        assert len(msg["suggested_action"]) > 0, f"{key} suggested_action is empty"