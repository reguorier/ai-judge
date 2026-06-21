"""
Tests for live demo telemetry — public-demo-live-dry-run-v1
"""
import json
import os
import sys
import tempfile
import pytest

OBS_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/observability"
)
sys.path.insert(0, OBS_DIR)

from demo_telemetry import DemoTelemetry, get_demo_telemetry


class TestLiveDemoTelemetry:
    """Test telemetry meets live demo requirements."""

    def test_record_all_event_types(self):
        """All 5 event types must be recordable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telem = DemoTelemetry(log_dir=tmpdir, enabled=True)
            telem.record_submitted("TASK-001", "ordinary_user", "s1", "1.2.3.4")
            telem.record_completed("TASK-001", "ordinary_user", 1500, "s1", "1.2.3.4")
            telem.record_failed("TASK-002", "professional_user", "TIMEOUT", "s2", "5.6.7.8")
            telem.record_rate_limited("s3", "9.9.9.9")
            telem.record_safety_blocked("TASK-003", "prompt_injection", "s4", "8.8.8.8")

            log_file = os.path.join(tmpdir, "demo_telemetry.jsonl")
            assert os.path.isfile(log_file)

            events = []
            with open(log_file) as f:
                for line in f:
                    events.append(json.loads(line.strip()))

            event_types = [e["event"] for e in events]
            assert "demo_run_submitted" in event_types
            assert "demo_run_completed" in event_types
            assert "demo_run_failed" in event_types
            assert "rate_limited" in event_types
            assert "safety_blocked" in event_types

    def test_ip_and_session_hashed(self):
        """IP and session must be stored as hash, not raw."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telem = DemoTelemetry(log_dir=tmpdir, enabled=True)
            raw_ip = "192.168.1.100"
            raw_session = "user-session-abc123"
            telem.record_submitted("T-1", "ordinary_user", raw_session, raw_ip)

            log_file = os.path.join(tmpdir, "demo_telemetry.jsonl")
            with open(log_file) as f:
                event = json.loads(f.readline().strip())

            # Hash must not equal raw value
            assert event["ip_hash"] != raw_ip
            assert event["session_id_hash"] != raw_session
            # Hash must be truncated (12 chars)
            assert len(event["ip_hash"]) <= 12

    def test_telemetry_can_be_disabled(self):
        """Telemetry must respect enabled=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telem = DemoTelemetry(log_dir=tmpdir, enabled=False)
            telem.record_submitted("T-1", "ordinary_user", "s1", "1.1.1.1")
            telem.record_completed("T-1", "ordinary_user", 100, "s1", "1.1.1.1")

            log_file = os.path.join(tmpdir, "demo_telemetry.jsonl")
            assert not os.path.isfile(log_file), "No log file should be created when disabled"

    def test_no_raw_prompt_in_event(self):
        """Events must not contain raw_prompt field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telem = DemoTelemetry(log_dir=tmpdir, enabled=True)
            telem.record_submitted("T-1", "ordinary_user", "s1", "1.1.1.1")

            log_file = os.path.join(tmpdir, "demo_telemetry.jsonl")
            with open(log_file) as f:
                event = json.loads(f.readline().strip())

            assert "raw_prompt" not in event
            assert "prompt" not in event
            assert "user_input" not in event

    def test_singleton_returns_same_instance(self):
        """get_demo_telemetry must return singleton."""
        with tempfile.TemporaryDirectory() as tmpdir:
            t1 = get_demo_telemetry(log_dir=tmpdir, enabled=True)
            t2 = get_demo_telemetry(log_dir=tmpdir, enabled=True)
            assert t1 is t2

    def test_get_stats_returns_counts(self):
        """get_stats must return event counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            telem = DemoTelemetry(log_dir=tmpdir, enabled=True)
            telem.record_submitted("T-1", "ordinary_user", "s1", "1.1.1.1")
            telem.record_completed("T-1", "ordinary_user", 100, "s1", "1.1.1.1")
            telem.record_rate_limited("s2", "2.2.2.2")

            stats = telem.get_stats(hours=24)
            assert stats["total_events"] == 3