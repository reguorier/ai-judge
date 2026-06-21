"""Test expansion incident policy — §9 requirements."""

import json
import pytest
from pathlib import Path


INCIDENTS_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_incidents.jsonl")


@pytest.fixture
def incidents():
    with open(INCIDENTS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


class TestExpansionIncidentP0Blocking:
    """P0 incidents must not exist — if they do, expansion is BLOCKED"""

    def test_no_p0_incidents(self, incidents):
        p0 = [i for i in incidents if i["severity"] == "P0"]
        assert len(p0) == 0, f"P0 incidents found: {len(p0)} — expansion must be BLOCKED"

    def test_no_pii_leak_incidents(self, incidents):
        pii = [i for i in incidents if i.get("class") == "PII_LEAK"]
        assert len(pii) == 0, f"PII leak incidents: {len(pii)}"

    def test_no_secret_exposure_incidents(self, incidents):
        secrets = [i for i in incidents if i.get("class") in ("SECURITY_BLOCK_FAIL", "TRACEBACK_EXPOSURE")]
        assert len(secrets) == 0, f"Secret/traceback exposure: {len(secrets)}"


class TestExpansionIncidentSeverityClassification:
    """Severity must be valid and correctly classified"""

    def test_valid_severity(self, incidents):
        valid = {"P0", "P1", "P2"}
        for i in incidents:
            assert i["severity"] in valid, f"Invalid severity: {i['severity']}"

    def test_valid_class(self, incidents):
        valid = {"API_DOWN", "VALIDATION_FAILURE", "PII_LEAK", "SECURITY_BLOCK_FAIL",
                 "REPORT_CONFUSING", "USER_CONFUSED", "ARTIFACT_MISSING", "UNKNOWN"}
        for i in incidents:
            assert i.get("class", "UNKNOWN") in valid, f"Invalid class: {i.get('class')}"

    def test_non_safety_incidents_are_p2(self, incidents):
        """Non-safety incidents (confusion, UI) should be P2"""
        non_safety = [i for i in incidents if i.get("class") in ("REPORT_CONFUSING", "USER_CONFUSED")]
        for i in non_safety:
            assert i["severity"] == "P2", f"Non-safety incident {i['incident_id']} severity {i['severity']} should be P2"

    def test_p2_incidents_are_non_blocking(self, incidents):
        """P2 incidents should not block the release"""
        p2 = [i for i in incidents if i["severity"] == "P2"]
        for i in p2:
            assert i.get("resolved") is True or i.get("user_visible") is not None, \
                f"P2 incident {i['incident_id']} should be tracked"


class TestExpansionIncidentResolved:
    """All incidents should have resolved flag"""

    def test_all_have_resolved(self, incidents):
        for i in incidents:
            assert "resolved" in i, f"Incident {i['incident_id']} missing 'resolved' field"

    def test_all_have_action_taken(self, incidents):
        for i in incidents:
            assert "action_taken" in i and i["action_taken"], \
                f"Incident {i['incident_id']} missing action_taken"

    def test_all_have_owner(self, incidents):
        valid_owners = {"engineering", "product", "ops", "safety"}
        for i in incidents:
            assert i.get("owner") in valid_owners, \
                f"Incident {i['incident_id']} invalid owner: {i.get('owner')}"