"""
Tests for live demo config — public-demo-live-dry-run-v1
"""
import json
import os
import pytest

DEMO_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo"
)


class TestLiveDemoConfig:
    """Test demo_config.json meets live dry run requirements."""

    def test_config_exists_and_valid_json(self):
        """Config file must exist and be valid JSON."""
        cfg_path = os.path.join(DEMO_DIR, "demo_config.json")
        assert os.path.isfile(cfg_path), f"Config not found at {cfg_path}"
        with open(cfg_path) as f:
            cfg = json.load(f)
        assert cfg["demo_enabled"] is True

    def test_required_fields_present(self):
        """All required fields must be present."""
        cfg_path = os.path.join(DEMO_DIR, "demo_config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)

        required = [
            "demo_enabled", "demo_mode", "max_requests_per_ip_per_hour",
            "max_requests_per_session_per_day", "max_question_chars",
            "allow_file_upload", "allow_sensitive_personal_data",
            "show_disclaimer", "require_privacy_notice_ack",
            "default_reader_type", "fail_closed",
            "rate_limit", "pii_redaction", "abuse_guard", "telemetry",
        ]
        for field in required:
            assert field in cfg, f"Missing required field: {field}"

    def test_fail_closed_and_rate_limits(self):
        """Demo must fail closed and enforce limits."""
        cfg_path = os.path.join(DEMO_DIR, "demo_config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)

        assert cfg["fail_closed"] is True
        assert cfg["rate_limit"]["enabled"] is True
        assert cfg["rate_limit"]["ip_hourly"] == 5
        assert cfg["rate_limit"]["session_daily"] == 10

    def test_security_modules_enabled(self):
        """Rate limit, abuse guard, PII redaction must all be enabled."""
        cfg_path = os.path.join(DEMO_DIR, "demo_config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)

        assert cfg["abuse_guard"]["enabled"] is True
        assert cfg["pii_redaction"]["enabled"] is True
        assert cfg["telemetry"]["enabled"] is True
        assert cfg["telemetry"]["hash_ip_session"] is True
        assert cfg["telemetry"]["save_raw_prompt"] is False

    def test_live_dry_run_config_exists(self):
        """live_dry_run_config.json must exist."""
        cfg_path = os.path.join(DEMO_DIR, "live_dry_run_config.json")
        assert os.path.isfile(cfg_path), f"Live dry run config not found at {cfg_path}"
        with open(cfg_path) as f:
            cfg = json.load(f)
        assert "api_base" in cfg
        assert "dry_run_scope" in cfg