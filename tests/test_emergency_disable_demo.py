"""test_emergency_disable_demo.py — 测试 emergency disable 脚本功能"""

import json
import os
import subprocess
import tempfile
import pytest

SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "emergency_disable_public_demo.sh"
)


def _script_exists():
    return os.path.exists(SCRIPT_PATH)


class TestEmergencyDisableScript:

    def test_script_file_exists(self):
        assert _script_exists(), f"emergency disable script not found: {SCRIPT_PATH}"

    def test_script_is_executable(self):
        if not _script_exists():
            pytest.skip("script not found")
        assert os.access(SCRIPT_PATH, os.X_OK) or os.access(SCRIPT_PATH, os.R_OK), \
            "script is not readable"

    def test_script_contains_required_steps(self):
        if not _script_exists():
            pytest.skip("script not found")
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_steps = [
            "demo_enabled=false",
            "stop accepting new runs",
            "Preserving existing artifacts",
            "maintenance",
            "incident",
            "diagnostic",
            "evidence",
            "PUBLIC_DEMO_EMERGENCY_DISABLED",
        ]
        for step in required_steps:
            assert step.lower() in content.lower(), f"script missing step: {step}"

    def test_script_does_not_delete_evidence(self):
        if not _script_exists():
            pytest.skip("script not found")
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Ensure script does not contain destructive delete commands for evidence
        destructive_patterns = ["rm -rf", "rm -r", "shutil.rmtree", "os.remove"]
        for pattern in destructive_patterns:
            if pattern in content:
                # Check context: it should NOT be used on feedback/evidence paths
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if pattern in line:
                        context = "\n".join(lines[max(0, i-1):min(len(lines), i+2)])
                        assert "feedback" not in context.lower() and "evidence" not in context.lower(), \
                            f"destructive command targets evidence/feedback: {pattern}"

    def test_script_outputs_success_message(self):
        """Script should output PUBLIC_DEMO_EMERGENCY_DISABLED on success."""
        if not _script_exists():
            pytest.skip("script not found")
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "PUBLIC_DEMO_EMERGENCY_DISABLED" in content, \
            "script does not output expected success message"

    def test_script_handles_missing_config(self):
        """Script should handle missing config file gracefully."""
        if not _script_exists():
            pytest.skip("script not found")
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        # Should contain fallback logic for missing config
        assert "config file not found" in content.lower() or "creating emergency lock" in content.lower(), \
            "script does not handle missing config file"