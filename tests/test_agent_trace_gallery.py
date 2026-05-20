import json
from pathlib import Path

from core.agent_trace_audit import audit_agent_trace


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def test_supported_agent_trace_fixture_allows_review():
    report = audit_agent_trace(
        _load("agent-trace-supported.json"),
        audit_id="agent-trace-supported-test",
        generated_at="2026-05-20T00:00:00+00:00",
    )

    assert report["trace_status"] == "supported"
    assert report["exploration_coverage"] == "strong"
    assert report["rule_support"] == "supported"
    assert report["human_gate"] == "allow_with_review"


def test_partial_agent_trace_fixture_requires_human_review():
    report = audit_agent_trace(
        _load("agent-trace-partial.json"),
        audit_id="agent-trace-partial-test",
        generated_at="2026-05-20T00:00:00+00:00",
    )

    assert report["trace_status"] == "partially_supported"
    assert report["exploration_coverage"] == "partial"
    assert report["rule_support"] == "supported"
    assert report["human_gate"] == "needs_human_review"
    assert "size-dependent transformation" in report["missed_alternatives"]
