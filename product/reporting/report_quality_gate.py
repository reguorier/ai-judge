"""Quality gate for final reports: ensures reports are grounded in user issues, not meta analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityResult:
    ok: bool
    failures: list[str] = field(default_factory=list)


# ─── Meta report detection ───────────────────────────────────────────

META_REPORT_BANNED_TERMS: list[str] = [
    "AI Judge 产品价值",
    "AI Judge产品价值",
    "多模型审计产品",
    "报告视觉格式",
    "B2B SaaS",
    "投资人",
    "产品页面",
    "薄客户端",
    "dashboard/workbench",
    "应以最终报告作为主交付物",
    "界面只保留提交",
    "报告是主交付物",
    "客户端只需要必要状态",
    "把日常入口固定为 AI Judge Client",
    "不扩展 dashboard",
    "优先改进最终报告质量",
    "真实 Web seat 接入前",
]


def looks_like_ai_judge_meta_report(text: str) -> bool:
    """Return True if the report body is dominated by AI Judge product meta-language."""
    hit_count = 0
    for term in META_REPORT_BANNED_TERMS:
        if term in text:
            hit_count += 1
    # 命中 4 个以上 meta 禁词 → 判为 meta 报告
    return hit_count >= 4


# ─── User intent detection ───────────────────────────────────────────

PRODUCT_EVAL_KEYWORDS: list[str] = [
    "AI Judge",
    "产品评测",
    "产品评估",
    "product evaluation",
    "dashboard 评测",
    "界面评测",
    "系统评测",
]


def user_asked_product_eval(question: str) -> bool:
    """Return True if the user's question is about evaluating the AI Judge product itself."""
    q_lower = question.lower()
    return any(kw.lower() in q_lower for kw in PRODUCT_EVAL_KEYWORDS)


# ─── Keyword overlap ─────────────────────────────────────────────────

def keyword_overlap(question: str, report_text: str) -> float:
    """Compute a simple token overlap ratio between question and report body.

    Returns a float in [0.0, 1.0].
    """
    if not question or not report_text:
        return 0.0
    # Extract CJK bigrams and alphabetic words
    q_tokens = set(_tokenize(question))
    r_tokens = set(_tokenize(report_text))
    if not q_tokens:
        return 1.0
    return len(q_tokens & r_tokens) / len(q_tokens)


def _tokenize(text: str) -> list[str]:
    """Extract meaningful tokens: CJK bigrams and alphabetic words."""
    tokens: list[str] = []
    # Alphabetic words (2+ chars)
    tokens.extend(re.findall(r"[a-zA-Z]{2,}", text))
    # CJK bigrams
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    for i in range(len(cjk_chars) - 1):
        tokens.append(cjk_chars[i] + cjk_chars[i + 1])
    return tokens


# ─── Source pack usage check ─────────────────────────────────────────

def uses_source_pack(report_text: str, source_pack: dict[str, Any]) -> bool:
    """Heuristic: check if key phrases from source_pack appear in the report."""
    phrases: list[str] = []
    # Extract key phrases from source_pack
    legal = source_pack.get("legal_analysis", {}) or {}
    if isinstance(legal, dict):
        for val in legal.values():
            if isinstance(val, str) and len(val) > 10:
                phrases.append(val[:80])
    search = source_pack.get("search_agent_output", {}) or {}
    if isinstance(search, dict):
        # Collect both summary and result as candidate phrases
        for key in ("summary", "result"):
            val = search.get(key, "")
            if isinstance(val, str) and len(val) > 15:
                phrases.append(val[:80])

    if not phrases:
        return True  # no source pack → nothing to check

    hit_count = 0
    for phrase in phrases:
        # Check if at least 15 chars from the phrase appear in the report
        snippet = phrase[:15]
        if snippet in report_text:
            hit_count += 1
    return hit_count >= max(1, len(phrases) // 2)


# ─── Duplicate detection ─────────────────────────────────────────────

def duplicate_similarity_against_recent_reports(report_text: str) -> float:
    """Stub: would compare against recently generated reports. Returns 0.0 for now."""
    return 0.0


# ─── Main gate ───────────────────────────────────────────────────────

def validate_final_report_relevance(
    question: str,
    report_text: str,
    source_pack: dict[str, Any] | None = None,
) -> QualityResult:
    """Validate that a final report is grounded in the user's issue.

    Args:
        question: The user's original question.
        report_text: The body text of the final report.
        source_pack: The collected analysis sources (search, LLM, seat outputs).

    Returns:
        QualityResult with ok=True if all checks pass.
    """
    sp = source_pack or {}
    failures: list[str] = []

    # 1. Minimum length (token/char minimum for substantive content)
    if len(report_text.strip()) < 100:
        failures.append("report_too_short")

    # 2. Meta report leak
    if looks_like_ai_judge_meta_report(report_text) and not user_asked_product_eval(question):
        failures.append("meta_report_leaked")

    # 3. Keyword overlap
    overlap = keyword_overlap(question, report_text)
    if overlap < 0.18:
        failures.append(f"low_question_report_overlap ({overlap:.2f})")

    # 4. Source pack usage
    has_content = sp.get("has_substantive_content", bool(sp))
    if has_content and not uses_source_pack(report_text, sp):
        failures.append("source_pack_not_used")

    # 5. Near-duplicate
    dup_sim = duplicate_similarity_against_recent_reports(report_text)
    if dup_sim > 0.90:
        failures.append("near_duplicate_report")

    return QualityResult(ok=not failures, failures=failures)