#!/usr/bin/env python3
"""Risk Router v3.2 — Task risk classification and review depth routing.

Inspired by Tianfu Agent's tiered scheduling:
  - critical tasks → FullJury (fact + rule + dissent + confidence)
  - normalized tasks → Standard (fact + rule + confidence)
  - trivial tasks → FastCheck (tool results only)

Integrates with:
  - hard_truth.determine_mode (L0-L4 escalation already handles feedback mode)
  - consensus_v2.diversity_alert_pipeline (echo chamber → trigger dissent)
  - scoring_v2.score_claim_v2 (bluff gate + bid gate + score gate)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReviewDepth(str, Enum):
    """Review depth level — maps to Tianfu's tiered scheduling."""
    FULL_JURY = "full_jury"           # Fact + Rule + Dissent + Confidence + Precedent
    STANDARD_WITH_DISSENT = "standard_dissent"  # Standard + Dissent
    STANDARD = "standard"             # Fact + Rule + Confidence
    FAST_CHECK = "fast_check"         # Tool results + Rule only


@dataclass
class RiskClassification:
    """Classification result for a judge task."""
    depth: ReviewDepth
    needs_dissent: bool
    needs_precedent: bool
    reason: str
    tool_strategy: dict[str, Any]
    model_strategy: dict[str, Any]


class RiskRouter:
    """Classify tasks by risk level and determine review depth.

    High-sensitivity domains (payment, auth, security, etc.) → FullJury
    Compliance/policy tasks → StandardWithDissent
    Small diffs with passing tests → FastCheck
    Everything else → Standard
    """

    HIGH_SENSITIVITY = [
        "payment", "auth", "privacy", "security", "data",
        "encryption", "credentials", "token", "session",
        "permission", "access_control", "pii", "gdpr",
    ]

    COMPLIANCE_KEYWORDS = [
        "compliance", "policy", "regulation", "gdpr", "hipaa",
        "soc2", "pci", "audit", "governance",
    ]

    FAST_CHECK_MAX_LINES = 30

    def __init__(self, force_full_jury_on_security: bool = True,
                 fast_check_max_lines: int = 30):
        self.force_full_jury = force_full_jury_on_security
        self.fast_check_max = fast_check_max_lines

    def classify(self, task_info: dict[str, Any]) -> RiskClassification:
        """Classify a task and determine review depth.

        Args:
            task_info: Task metadata dict with keys:
                - risk_surface (list[str]): risk domains touched
                - files_changed (int)
                - lines_added (int), lines_deleted (int)
                - all_tests_pass (bool)
                - contains_compliance (bool, optional)

        Returns:
            RiskClassification with depth, tool strategy, model strategy.
        """
        risk_surface = task_info.get("risk_surface", [])
        diff_size = task_info.get("lines_added", 0) + task_info.get("lines_deleted", 0)
        tests_pass = task_info.get("all_tests_pass", False)
        is_compliance = task_info.get("contains_compliance", False)

        risk_lower = [r.lower() for r in risk_surface]

        # 1. Security/sensitive → FullJury
        if self.force_full_jury and self._touches_high_sensitivity(risk_lower):
            return RiskClassification(
                depth=ReviewDepth.FULL_JURY,
                needs_dissent=True,
                needs_precedent=True,
                reason="触及安全/敏感领域，启动全合议审查",
                tool_strategy=self._tool_strategy(ReviewDepth.FULL_JURY),
                model_strategy=self._model_strategy(ReviewDepth.FULL_JURY),
            )

        # 2. Compliance → Standard + Dissent
        if is_compliance or self._has_compliance_keywords(risk_lower):
            return RiskClassification(
                depth=ReviewDepth.STANDARD_WITH_DISSENT,
                needs_dissent=True,
                needs_precedent=True,
                reason="合规/策略相关，启动异议审查",
                tool_strategy=self._tool_strategy(ReviewDepth.STANDARD_WITH_DISSENT),
                model_strategy=self._model_strategy(ReviewDepth.STANDARD_WITH_DISSENT),
            )

        # 3. Small diff + tests passing + not sensitive → FastCheck
        if (diff_size <= self.fast_check_max
                and tests_pass
                and not self._touches_high_sensitivity(risk_lower)):
            return RiskClassification(
                depth=ReviewDepth.FAST_CHECK,
                needs_dissent=False,
                needs_precedent=False,
                reason=f"变更量小 (≤{self.fast_check_max}行) + 测试全过，快速审查",
                tool_strategy=self._tool_strategy(ReviewDepth.FAST_CHECK),
                model_strategy=self._model_strategy(ReviewDepth.FAST_CHECK),
            )

        # 4. Default → Standard
        return RiskClassification(
            depth=ReviewDepth.STANDARD,
            needs_dissent=False,
            needs_precedent=False,
            reason="标准审查流程",
            tool_strategy=self._tool_strategy(ReviewDepth.STANDARD),
            model_strategy=self._model_strategy(ReviewDepth.STANDARD),
        )

    def _touches_high_sensitivity(self, risk_lower: list[str]) -> bool:
        return any(
            any(sens in r for sens in self.HIGH_SENSITIVITY)
            for r in risk_lower
        )

    def _has_compliance_keywords(self, risk_lower: list[str]) -> bool:
        return any(
            any(kw in r for kw in self.COMPLIANCE_KEYWORDS)
            for r in risk_lower
        )

    def _tool_strategy(self, depth: ReviewDepth) -> dict[str, Any]:
        """Get tool execution strategy for a review depth."""
        strategies = {
            ReviewDepth.FULL_JURY: {
                "run_all": True,
                "mandatory": ["sast", "lint", "test", "ast"],
                "optional": ["dependency", "performance", "coverage"],
            },
            ReviewDepth.STANDARD_WITH_DISSENT: {
                "run_all": False,
                "mandatory": ["sast", "lint"],
                "optional": ["ast", "test"],
            },
            ReviewDepth.STANDARD: {
                "run_all": False,
                "mandatory": ["sast", "lint"],
                "optional": ["ast"],
            },
            ReviewDepth.FAST_CHECK: {
                "run_all": False,
                "mandatory": ["lint"],
                "optional": [],
            },
        }
        return strategies.get(depth, strategies[ReviewDepth.STANDARD])

    def _model_strategy(self, depth: ReviewDepth) -> dict[str, Any]:
        """Get model selection strategy for a review depth."""
        strategies = {
            ReviewDepth.FULL_JURY: {
                "use_local": True,
                "allow_remote": True,
                "min_context_window": 8192,
            },
            ReviewDepth.STANDARD_WITH_DISSENT: {
                "use_local": True,
                "allow_remote": False,
                "min_context_window": 4096,
            },
            ReviewDepth.STANDARD: {
                "use_local": True,
                "allow_remote": False,
                "min_context_window": 4096,
            },
            ReviewDepth.FAST_CHECK: {
                "use_local": True,
                "allow_remote": False,
                "min_context_window": 2048,
            },
        }
        return strategies.get(depth, strategies[ReviewDepth.STANDARD])


# ── Integration: merge with existing hard_truth mode ──

def compute_review_depth(
    task_info: dict[str, Any],
    neuro_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compute review depth, merging RiskRouter with hard_truth mode.

    The hard_truth L0-L4 mode handles feedback style (how to present).
    The RiskRouter handles resource allocation (how deep to investigate).
    Both are independent dimensions that combine.

    Returns a merged dict ready for the orchestrator.
    """
    router = RiskRouter()
    classification = router.classify(task_info)

    result = {
        "review_depth": classification.depth.value,
        "needs_dissent": classification.needs_dissent,
        "needs_precedent": classification.needs_precedent,
        "reason": classification.reason,
        "tool_strategy": classification.tool_strategy,
        "model_strategy": classification.model_strategy,
    }

    # If hard_truth mode is L2+, force dissent regardless
    if neuro_profile:
        from core.hard_truth import determine_mode
        mode = determine_mode(neuro_profile)
        if mode.get("mode_level", 0) >= 2:
            result["needs_dissent"] = True
            result["hard_truth_forced_dissent"] = True

    return result
