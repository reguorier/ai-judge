"""
Test Demo Config Schema
public-demo-readiness-v1.0.0

Validates demo_config.json structure and values.
"""

import json
import os
import pytest


@pytest.fixture
def config_path():
    return os.path.expanduser(
        "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo/demo_config.json"
    )


@pytest.fixture
def config(config_path):
    with open(config_path) as f:
        return json.load(f)


def test_demo_enabled(config):
    assert config["demo_enabled"] is True


def test_fail_closed_must_be_true(config):
    assert config["fail_closed"] is True, "fail_closed must be true for public demo safety"


def test_required_boolean_keys(config):
    for key in ["show_disclaimer", "require_privacy_notice_ack"]:
        assert config.get(key) is True, f"{key} must be True"


def test_rate_limit_values(config):
    assert config["max_requests_per_ip_per_hour"] == 5
    assert config["max_requests_per_session_per_day"] == 10


def test_demo_mode_and_modes(config):
    assert config["demo_mode"] == "public_preview"
    assert "deep_judge" in config["allowed_modes"]


def test_default_reader_type(config):
    assert config["default_reader_type"] == "ordinary_user"
    assert config["fallback_reader_type"] == "ordinary_user"


def test_file_upload_disabled(config):
    assert config["allow_file_upload"] is False
    assert config["allow_sensitive_personal_data"] is False


def test_max_question_chars(config):
    assert config["max_question_chars"] == 1200


def test_no_unknown_required_keys(config):
    required = {
        "demo_enabled", "demo_mode", "allowed_modes",
        "max_requests_per_ip_per_hour", "max_requests_per_session_per_day",
        "max_question_chars", "allow_file_upload", "allow_sensitive_personal_data",
        "show_disclaimer", "require_privacy_notice_ack",
        "default_reader_type", "fallback_reader_type", "fail_closed",
    }
    assert required.issubset(set(config.keys())), f"Missing keys: {required - set(config.keys())}"