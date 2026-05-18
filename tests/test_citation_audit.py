from __future__ import annotations

import json
from pathlib import Path

from core.citation_audit import load_audit_input, render_audit_html, render_audit_markdown, run_citation_audit


def test_citation_audit_verifies_user_supplied_evidence():
    verdict = run_citation_audit(
        title="Verified source demo",
        question="Does the answer cite the AI Judge citation audit report?",
        answer="The launch adds citation audit support. Source: https://example.com/ai-judge-citation-audit",
        external_evidence=[
            {
                "url": "https://example.com/ai-judge-citation-audit",
                "title": "AI Judge citation audit report",
                "snippet": "citation audit support for AI Judge launch",
            }
        ],
        run_id="audit-test-1",
        generated_at="2026-05-16T00:00:00+00:00",
    )

    summary = verdict["summary"]
    assert summary["overall_status"] == "verified"
    assert summary["trust_gate"] == "pass"
    assert summary["certification_id"].startswith("CITE-")
    assert verdict["grand_judge"]["evidence_broker"]["counts"]["user_supplied"] == 1
    assert verdict["grand_judge"]["evidence_broker"]["counts"]["provenance"]["user_supplied"] == 1
    assert summary["evidence_provenance_counts"]["user_supplied"] == 1
    item = verdict["grand_judge"]["replay_ledger"][0]["citation_verification"]["items"][0]
    assert item["matched_evidence"]["provenance"] == "user_supplied"


def test_citation_audit_does_not_self_verify_candidate_source():
    verdict = run_citation_audit(
        question="Does the answer cite a real report?",
        answer="This is proven by https://example.com/missing-report.",
        external_evidence=[],
        run_id="audit-test-2",
        generated_at="2026-05-16T00:00:00+00:00",
    )

    summary = verdict["summary"]
    assert summary["overall_status"] == "unverifiable"
    assert summary["trust_gate"] == "needs_more_evidence"
    assert summary["counts"]["unverifiable"] == 1
    assert summary["unverifiable_reason_counts"]["candidate_not_fetched"] == 1
    assert verdict["grand_judge"]["evidence_broker"]["counts"]["candidate_source"] == 1


def test_claim_support_catches_real_source_overclaimed_causation():
    verdict = run_citation_audit(
        title="Correlation is not causation",
        question="Did the AI review program cause lower churn?",
        answer=(
            "The AI review program caused a 22% reduction in churn. "
            "Source: https://example.com/research/ai-review-churn-2026"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/ai-review-churn-2026",
                "title": "AI review program and 22% churn reduction study",
                "snippet": (
                    "The study reports a 22% churn reduction associated with the AI review program. "
                    "The analysis is observational and does not establish causation."
                ),
            }
        ],
        run_id="audit-test-claim-support-1",
        generated_at="2026-05-18T00:00:00+00:00",
    )

    summary = verdict["summary"]
    citation_item = verdict["grand_judge"]["replay_ledger"][0]["citation_verification"]["items"][0]
    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert citation_item["status"] == "verified"
    assert summary["overall_status"] == "verified"
    assert claim_item["source_relevance"] == "relevant"
    assert claim_item["claim_support"] == "contradicted"
    assert claim_item["support_failure_code"] == "overclaimed_causation"
    assert summary["overall_claim_support"] == "contradicted"
    assert summary["claim_support_counts"]["contradicted"] == 1
    assert summary["claim_support_failure_counts"]["overclaimed_causation"] == 1
    assert "Claim Support" in render_audit_html(verdict)


def test_markdown_loader_and_renderers(tmp_path):
    path = tmp_path / "audit.md"
    path.write_text(
        """# Demo Audit

## Question
Can the answer cite the launch note?

## AI Answer
The feature shipped according to https://example.com/launch.

## External Evidence
```json
[{"url":"https://example.com/launch","title":"Launch note","snippet":"feature shipped"}]
```
""",
        encoding="utf-8",
    )

    data = load_audit_input(path)
    verdict = run_citation_audit(
        question=data["question"],
        answer=data["answer"],
        external_evidence=data["external_evidence"],
        generated_at="2026-05-16T00:00:00+00:00",
    )
    markdown = render_audit_markdown(verdict)
    html = render_audit_html(verdict)

    assert data["title"] == "Demo Audit"
    assert json.loads(json.dumps(verdict, ensure_ascii=False))
    assert "Certification ID" in markdown
    assert "Citation Verification" in html
    assert ".card { color:var(--ink);" in html
    assert "https://example.com/launch" in html


def test_citation_bench_has_100_valid_cases():
    bench = Path(__file__).resolve().parents[1] / "citation-bench" / "citation-bench-100.jsonl"
    rows = [json.loads(line) for line in bench.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(rows) == 100
    assert {row["category"] for row in rows} == {
        "verified",
        "weakly_verified",
        "irrelevant",
        "unverifiable",
        "contradicted",
    }
    assert all(row["expected_status"] for row in rows)
