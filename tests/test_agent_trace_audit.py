from core.agent_trace_audit import (
    audit_agent_trace,
    render_agent_trace_html,
    render_agent_trace_markdown,
)


def test_agent_trace_audit_flags_unobserved_final_token():
    report = audit_agent_trace(
        {
            "task_id": "arc-style-demo-001",
            "observations": [
                "Training example A maps a red block to the top-left corner.",
                "Training example B maps a blue block to the bottom-right corner.",
            ],
            "hypothesis": "Objects move toward the nearest corner matching their color.",
            "actions": ["Apply the rule to the test grid."],
            "final_answer": "Move the green block to the top-left corner.",
        },
        audit_id="agent-trace-test",
        generated_at="2026-05-20T00:00:00+00:00",
    )

    assert report["schema"] == "agent_trace_audit.v1"
    assert report["trace_status"] == "weakly_supported"
    assert report["rule_support"] == "unverifiable"
    assert report["human_gate"] == "reject_until_rechecked"
    assert "green" in report["unsupported_final_tokens"]
    assert report["replay_ledger_hash"].startswith("sha256:")


def test_agent_trace_renderers_include_core_verdict():
    report = audit_agent_trace(
        {
            "task_id": "demo",
            "task": "Audit the trace.",
            "observations": ["Observed red.", "Observed blue."],
            "hypothesis": "Color rule.",
            "actions": ["Apply rule."],
            "final_answer": "Use green.",
        },
        audit_id="agent-trace-render-test",
        generated_at="2026-05-20T00:00:00+00:00",
    )

    markdown = render_agent_trace_markdown(report)
    html = render_agent_trace_html(report)

    assert "AI Judge Agent Trace Audit" in markdown
    assert "reject_until_rechecked" in markdown
    assert "Replay Ledger" in html
    assert "agent-trace-render-test" in html
