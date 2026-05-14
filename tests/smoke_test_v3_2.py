#!/usr/bin/env python3
"""AI Judge v3.2 smoke test.

Checks the Tianfu migration layer:
  1. EvidenceBundle metrics
  2. RiskRouter depth classification
  3. Dissent trigger for sensitive work
  4. Reasoning tree JSON shape
  5. Full v3.2 scoring pipeline integration
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from core.evidence import Evidence, EvidenceBundle
from core.reasoning_trace import build_reasoning_tree_from_pipeline
from core.risk_router import compute_review_depth
from core.scoring_v2 import score_jury_full_pipeline_v3_2


def build_demo_bundle() -> EvidenceBundle:
    bundle = EvidenceBundle()
    bundle.add(Evidence.from_tool(
        "sast",
        "sast_001",
        "No high-severity injection finding in checkout sanitizer",
        file_path="payment/checkout.ts",
        line=89,
        tool_confidence=0.94,
    ))
    bundle.add(Evidence.from_harness(
        "pytest-checkout",
        passed=True,
        description="Regression tests cover script tags and SQL metacharacters",
    ))
    bundle.add(Evidence.from_rule(
        "OWASP-A03",
        "OWASP Top 10",
        "Injection-sensitive changes require tool and test evidence.",
        match_confidence=0.88,
    ))
    return bundle


def main() -> None:
    task_info = {
        "task_id": "smoke-v3.2-checkout",
        "files_changed": 2,
        "lines_added": 147,
        "lines_deleted": 38,
        "all_tests_pass": True,
        "risk_surface": ["security", "payment"],
        "test_status": "passed",
        "touched_modules": ["checkout", "sanitizer"],
        "sast_high_severity_count": 0,
        "lint_violation_count": 1,
        "ast_complexity": 18,
    }

    bundle = build_demo_bundle()
    metrics = bundle.to_dict()
    assert metrics["total_evidence"] == 3
    assert metrics["verifiable_count"] == 3
    assert bundle.compute_evidence_strength() > 0.7

    risk = compute_review_depth(task_info)
    assert risk["review_depth"] == "full_jury"
    assert risk["needs_dissent"] is True

    tree = build_reasoning_tree_from_pipeline(
        verdict_summary="Manual review required",
        task_info=task_info,
        evidence_items=metrics["items"],
        dissent_result={
            "strength": 0.4,
            "should_reduce_confidence": True,
            "counterarguments": [{"claim": "Complexity risk", "reasoning": "AST complexity is above threshold."}],
            "required_checks": ["Confirm sanitizer branch coverage."],
        },
        confidence_light={"confidence": 0.66, "level": "yellow"},
    )
    assert tree["kind"] == "conclusion"
    assert any(child["kind"] == "evidence" for child in tree["children"])
    assert any(child["kind"] == "dissent" for child in tree["children"])

    claim = {
        "claim_id": "c1",
        "claim": "Checkout sanitizer is safe enough for release.",
        "source_authority": 0.78,
        "evidence_strength": bundle.compute_evidence_strength(),
        "evidence_count": bundle.count,
        "evidence_quality": bundle.compute_evidence_quality(),
        "freshness": 0.92,
        "reproducibility": 0.88,
        "historical_reliability": 0.80,
        "confidence": 0.84,
        "risk_penalty": 0.02,
    }
    result = score_jury_full_pipeline_v3_2(
        claims=[claim],
        task_info=task_info,
        evidence_bundles={"c1": bundle},
    )
    assert result["scoring_version"] == "3.2.0-tianfu"
    assert result["summary"]["review_depth"] == "full_jury"
    assert result["summary"]["dissent_triggered"] is True
    assert result["summary"]["evidence_total"] == 3
    assert result["v3_2_dissent_results"]["c1"]["strength"] > 0
    assert result["v3_2_reasoning_tree"]["kind"] == "conclusion"

    print("AI Judge v3.2 smoke test passed")


if __name__ == "__main__":
    main()
