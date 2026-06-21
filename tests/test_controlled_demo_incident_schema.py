"""test_controlled_demo_incident_schema.py — 测试 incident JSONL schema"""

import json
import os
import pytest

INCIDENTS_PATH = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support", "AI Judge",
    "runtime", "product", "demo_launch", "controlled_demo_incidents.jsonl"
)

REQUIRED_FIELDS = [
    "incident_id", "timestamp", "severity", "class", "run_id",
    "user_id", "description", "user_visible", "action_taken",
    "resolved", "owner"
]

VALID_SEVERITIES = ["P0", "P1", "P2"]
VALID_CLASSES = [
    "API_DOWN", "VALIDATION_FAILURE", "PII_LEAK", "SECURITY_BLOCK_FAIL",
    "REPORT_CONFUSING", "USER_CONFUSED", "ARTIFACT_MISSING", "UNKNOWN"
]
VALID_OWNERS = ["engineering", "product", "ops", "safety"]


def _load_incidents():
    if not os.path.exists(INCIDENTS_PATH):
        pytest.skip(f"incidents file not found: {INCIDENTS_PATH}")
    entries = []
    with open(INCIDENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


class TestIncidentSchema:

    def test_all_entries_have_required_fields(self):
        entries = _load_incidents()
        for entry in entries:
            for field in REQUIRED_FIELDS:
                assert field in entry, f"{entry.get('incident_id', '?')} missing field: {field}"

    def test_severity_is_valid(self):
        entries = _load_incidents()
        for entry in entries:
            assert entry["severity"] in VALID_SEVERITIES, \
                f"{entry['incident_id']} invalid severity: {entry['severity']}"

    def test_class_is_valid(self):
        entries = _load_incidents()
        for entry in entries:
            assert entry["class"] in VALID_CLASSES, \
                f"{entry['incident_id']} invalid class: {entry['class']}"

    def test_owner_is_valid(self):
        entries = _load_incidents()
        for entry in entries:
            assert entry["owner"] in VALID_OWNERS, \
                f"{entry['incident_id']} invalid owner: {entry['owner']}"

    def test_no_p0_incidents(self):
        """P0 incidents must be 0 per §11 threshold."""
        entries = _load_incidents()
        p0 = [e for e in entries if e["severity"] == "P0"]
        assert len(p0) == 0, f"found {len(p0)} P0 incidents: {[e['incident_id'] for e in p0]}"

    def test_timestamp_is_iso8601(self):
        entries = _load_incidents()
        for entry in entries:
            ts = entry["timestamp"]
            assert "T" in ts, f"{entry['incident_id']} timestamp not ISO-8601: {ts}"