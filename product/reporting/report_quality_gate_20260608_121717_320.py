"""P0-3: Final report relevance quality gate.

Ensures generated reports actually address the user's legal issue, not product meta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityGateResult:
    ok: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_final_report_relevance(
    *,
    question: str,
    report_text: str,
    source_pack: dict[str, Any] | None = None,
) -> QualityGateResult:
    """Check that the final report is actually about the user's question.

    Rules:
    1. If source_pack has substantive content, report must reflect it
    2. Report body must not be pure product meta template
    3. Report must contain at least one keyword from the question domain
    """
    failures: list[str] = []
    warnings: list[str] = []

    source_pack = source_pack or {}

    # Rule 1: If sources exist, report must be non-trivial
    if source_pack.get("has_substantive_content"):
        if len(report_text) < 500:
            failures.append("Report too short despite having substantive sources")
        # Check report is not the product meta template
        meta_indicators = [
            "应以最终报告作为主交付物",
            "薄客户端足够承载提交",
            "dashboard/workbench 只能作为内部 debug/operator aid",
        ]
        meta_count = sum(1 for m in meta_indicators if m in report_text)
        if meta_count >= 2:
            failures.append(f"Report appears to be product meta template ({meta_count} meta indicators)")

    # Rule 2: domain keyword check
    domain_keywords = _extract_domain_keywords(question)
    if domain_keywords:
        matched = [kw for kw in domain_keywords if kw in report_text]
        if not matched:
            failures.append(
                f"Report contains no domain keywords from question. "
                f"Expected at least one of: {domain_keywords[:5]}"
            )
        elif len(matched) < max(1, len(domain_keywords) // 3):
            warnings.append(
                f"Low keyword match: {len(matched)}/{len(domain_keywords)}. "
                f"Matched: {matched}"
            )

    return QualityGateResult(ok=len(failures) == 0, failures=failures, warnings=warnings)


def _extract_domain_keywords(question: str) -> list[str]:
    """Extract signature domain keywords from question text."""
    # Legal domain keywords
    legal_kw_map = {
        "破产": ["破产", "债权", "申报", "清偿", "劣后"],
        "迟延履行": ["迟延履行", "利息", "加倍", "执行", "判决"],
        "宅基地": ["宅基地", "拆迁", "补偿", "村民", "登记", "转售", "合同无效", "不当得利"],
        "请求权": ["请求权", "案由", "被告", "诉讼请求", "民法典"],
        "法院": ["法院", "判例", "裁判", "最高人民法院", "北京", "上海", "广东", "江苏", "浙江"],
    }
    keywords = []
    for domain, kws in legal_kw_map.items():
        if any(kw in question for kw in kws[:3]):
            keywords.extend(kws)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result