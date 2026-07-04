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
            "The AI review program caused a 22% reduction in churn, "
            "so the company should attribute retention gains to the program. "
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
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_verdict"] == "unsupported_by_cited_source"
    assert claim_item["support_failure_code"] == "overclaimed_causation"
    assert claim_item["retrieved2response"] == "non_entailment"
    assert claim_item["retrieved2response_entailment"] is False
    assert summary["overall_claim_support"] == "unsupported"
    assert summary["overall_support_verdict"] == "unsupported_by_cited_source"
    assert summary["support_verdict_counts"]["unsupported_by_cited_source"] == 1
    assert summary["claim_support_pass_rate"] == 0.0
    assert summary["claim_support_counts"]["unsupported"] == 1
    assert summary["claim_support_failure_counts"]["overclaimed_causation"] == 1
    assert summary["retrieved2response_counts"]["non_entailment"] == 1
    assert verdict["human_review_status"]["status"] == "required"
    assert "Claim Support" in render_audit_html(verdict)


def test_claim_support_catches_absolute_claim_from_limited_source():
    verdict = run_citation_audit(
        title="Absolute claim is not supported by limited source",
        question="Does the source prove all hallucinated citations are caught?",
        answer=(
            "The audit catches all hallucinated citations with no false negatives. "
            "Source: https://example.com/research/citation-audit-pilot"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/citation-audit-pilot",
                "title": "Citation audit pilot",
                "snippet": (
                    "The pilot detected 71% of seeded hallucinated citations in a small sample. "
                    "The study was limited and reported false negatives, so the result is not exhaustive."
                ),
            }
        ],
        run_id="audit-test-claim-support-absolute",
        generated_at="2026-05-19T00:00:00+00:00",
    )

    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert verdict["summary"]["overall_status"] == "verified"
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_failure_code"] == "overclaimed_absolute"
    assert verdict["summary"]["overall_claim_support"] == "unsupported"


def test_claim_support_catches_quantified_effect_overclaim():
    verdict = run_citation_audit(
        title="Quantified effect is overclaimed",
        question="Does the source support a 95% hallucination reduction?",
        answer=(
            "The release reduced hallucinated citations by 95%. "
            "Source: https://example.com/research/citation-audit-release"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/citation-audit-release",
                "title": "Citation audit release evaluation",
                "snippet": "The evaluation observed a 12% reduction in hallucinated citations on the sampled documents.",
            }
        ],
        run_id="audit-test-claim-support-quantified",
        generated_at="2026-05-19T00:00:00+00:00",
    )

    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert verdict["summary"]["overall_status"] == "verified"
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_failure_code"] == "overclaimed_quantified_effect"
    assert verdict["summary"]["claim_support_failure_counts"]["overclaimed_quantified_effect"] == 1


def test_claim_source_support_catches_scoped_population_overclaim():
    verdict = run_citation_audit(
        title="Scoped adult source is overgeneralized",
        question="Does the source support applying the result to all patients?",
        answer=(
            "The intervention improves outcomes for all patients. "
            "Source: https://example.com/research/adult-outcomes"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/adult-outcomes",
                "title": "Adult outcomes trial",
                "snippet": "The trial enrolled adult patients and reported improved outcomes in that adult cohort.",
            }
        ],
        run_id="audit-test-claim-support-scope",
        generated_at="2026-07-04T00:00:00+00:00",
    )

    citation_item = verdict["grand_judge"]["replay_ledger"][0]["citation_verification"]["items"][0]
    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert citation_item["status"] == "verified"
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_verdict"] == "unsupported_by_cited_source"
    assert claim_item["support_failure_code"] == "overclaimed_scope"
    assert verdict["summary"]["support_verdict_counts"]["unsupported_by_cited_source"] == 1


def test_claim_source_support_catches_range_endpoint_as_precise_value():
    verdict = run_citation_audit(
        title="Range endpoint is reported as precise",
        question="Does the source support the precise reported value?",
        answer=(
            "The program reduced readmissions by 30%. "
            "Source: https://example.com/research/readmission-range"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/readmission-range",
                "title": "Readmission program evaluation",
                "snippet": "Across sites, the program was associated with a 10-30% reduction in readmissions.",
            }
        ],
        run_id="audit-test-claim-support-range-endpoint",
        generated_at="2026-07-04T00:00:00+00:00",
    )

    citation_item = verdict["grand_judge"]["replay_ledger"][0]["citation_verification"]["items"][0]
    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert citation_item["status"] == "verified"
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_verdict"] == "unsupported_by_cited_source"
    assert claim_item["support_failure_code"] == "overclaimed_range_endpoint"


def test_claim_source_support_catches_hedge_removed_from_effect():
    verdict = run_citation_audit(
        title="Hedged source is made certain",
        question="Does the source support a definite reduction claim?",
        answer=(
            "The intervention reduces infection risk. "
            "Source: https://example.com/research/infection-risk"
        ),
        external_evidence=[
            {
                "url": "https://example.com/research/infection-risk",
                "title": "Infection risk pilot",
                "snippet": "The pilot suggests the intervention may reduce infection risk, but the result is uncertain.",
            }
        ],
        run_id="audit-test-claim-support-hedge",
        generated_at="2026-07-04T00:00:00+00:00",
    )

    citation_item = verdict["grand_judge"]["replay_ledger"][0]["citation_verification"]["items"][0]
    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert citation_item["status"] == "verified"
    assert claim_item["claim_support"] == "unsupported"
    assert claim_item["support_verdict"] == "unsupported_by_cited_source"
    assert claim_item["support_failure_code"] == "overclaimed_hedge"


def test_claim_support_keeps_explicit_external_refutation_contradicted():
    verdict = run_citation_audit(
        title="Explicit refutation stays contradicted",
        question="Does the release note prove hallucinated references dropped below 1%?",
        answer=(
            "The model reduced hallucinated references below 1% in the release evaluation. "
            "Source: https://example.com/release/model-citation-quality"
        ),
        external_evidence=[
            {
                "url": "https://example.com/release/model-citation-quality",
                "title": "Model citation quality release note",
                "snippet": "The release note reports hallucinated references remained at 7.8% in the evaluation set.",
                "contradicts": True,
            }
        ],
        run_id="audit-test-claim-support-contradicted",
        generated_at="2026-07-03T00:00:00+00:00",
    )

    claim_item = verdict["grand_judge"]["claim_support_audit"]["items"][0]

    assert verdict["summary"]["overall_status"] == "contradicted"
    assert claim_item["claim_support"] == "contradicted"
    assert claim_item["support_verdict"] == "contradicted"
    assert claim_item["support_failure_code"] == "source_contradicts_claim"
    assert claim_item["retrieved2response"] == "non_entailment"
    assert verdict["summary"]["overall_claim_support"] == "contradicted"
    assert verdict["summary"]["overall_support_verdict"] == "contradicted"


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
