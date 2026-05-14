#!/usr/bin/env python3
"""Dissent Agent v3.2 — Devil's Advocate counterargument generation.

Inspired by Tianfu Agent's multi-perspective verification and Gemini's
asymmetric-context anti-collusion scheme.

Integrates with:
  - consensus_v2.diversity_alert_pipeline (detect echo chambers → trigger dissent)
  - determinism.ConfidenceLight (dissent reduces confidence when unresolved)
  - scoring_v2.score_claim_v2 (dissent flag adjusts score)

Key design (Gemini anti-collusion):
  - Fact-finding Agent: temperature=0.0, sees full context
  - Dissent Agent: temperature=0.8, sees ONLY AST/Lint/SAST (no comments, no business logic)
  - Run in sequence, not parallel (CodexPool isolation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CounterArgument:
    """Single counterargument from the Devil's Advocate."""
    claim: str
    reasoning: str
    severity: str  # "fatal" | "strong" | "weak"

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "reasoning": self.reasoning,
            "severity": self.severity,
        }


@dataclass
class DissentResult:
    """Result of dissent challenge against a claim."""

    strength: float              # 0.0 (no dissent) - 1.0 (complete rejection)
    counterarguments: list[CounterArgument] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    should_reduce_confidence: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "strength": round(self.strength, 4),
            "counterarguments": [a.to_dict() for a in self.counterarguments],
            "required_checks": self.required_checks,
            "should_reduce_confidence": self.should_reduce_confidence,
        }


# ── Dissent Engine ──

class DissentAgent:
    """Devil's Advocate — challenges claims based on evidence weaknesses.

    Inspired by Tianfu Agent's Verify phase and Gemini's anti-collusion:
    - Fact Agent (temp=0.0): collects objective evidence
    - Dissent Agent (temp=0.8): restricted view, challenges from blind spots
    """

    # Severity weights for dissent strength calculation
    SEVERITY_WEIGHTS = {"fatal": 1.0, "strong": 0.6, "weak": 0.3}

    def __init__(self, max_counterarguments: int = 3):
        self.max_counterarguments = max_counterarguments

    def challenge(
        self,
        claim: str,
        evidence_items: list[dict[str, Any]],
        restricted_context: Optional[dict[str, Any]] = None,
    ) -> DissentResult:
        """Challenge a claim by examining evidence weaknesses and restricted context.

        Args:
            claim: The claim text to challenge
            evidence_items: List of evidence dicts backing the claim
            restricted_context: Restricted view (AST metrics, lint count, SAST findings)
                               WITHOUT business logic, comments, or test results.
        """
        counterarguments: list[CounterArgument] = []

        # 1. Challenge evidence chain weaknesses
        counterarguments.extend(self._challenge_evidence(evidence_items))

        # 2. Challenge from restricted context (Gemini asymmetric view)
        if restricted_context:
            counterarguments.extend(self._challenge_from_restricted(restricted_context))

        # 3. Challenge common overconfidence patterns
        counterarguments.extend(self._challenge_patterns(claim))

        # Limit arguments
        counterarguments = counterarguments[:self.max_counterarguments]

        # Calculate dissent strength
        strength = self._calculate_strength(counterarguments)

        # Collect required checks
        required_checks = self._collect_checks(counterarguments)

        return DissentResult(
            strength=strength,
            counterarguments=counterarguments,
            required_checks=required_checks,
            should_reduce_confidence=strength > 0.3,
        )

    def _challenge_evidence(self, evidence_items: list[dict[str, Any]]) -> list[CounterArgument]:
        """Find weaknesses in the evidence chain."""
        args = []

        # Check for unverifiable evidence
        unverifiable = [e for e in evidence_items if not e.get("verifiable", True)]
        if unverifiable:
            args.append(CounterArgument(
                claim="部分证据不可客观验证",
                reasoning=f"{len(unverifiable)} 条证据依赖主观判断，无法通过工具或测试自动验证。建议补充可验证证据。",
                severity="strong",
            ))

        # Check for single-source evidence (single point of failure)
        tools = set(e.get("tool_name", "") for e in evidence_items if e.get("tool_name"))
        if len(tools) == 1 and evidence_items:
            args.append(CounterArgument(
                claim="证据来源单一",
                reasoning=f"所有工具证据仅来自 '{list(tools)[0]}'，建议引入更多独立工具交叉验证。",
                severity="weak",
            ))

        # Check for low-confidence evidence
        low_conf = [e for e in evidence_items if e.get("confidence", 0.5) < 0.5]
        if low_conf:
            args.append(CounterArgument(
                claim="部分证据置信度低",
                reasoning=f"{len(low_conf)} 条证据的置信度低于 50%，可能不足以支撑主判断。",
                severity="strong",
            ))

        return args

    def _challenge_from_restricted(self, ctx: dict[str, Any]) -> list[CounterArgument]:
        """Challenge from the restricted view (Gemini asymmetric context).

        The dissent agent ONLY sees: AST complexity, lint count, SAST findings.
        It does NOT see: author comments, business logic, test results.
        """
        args = []

        # AST complexity anomaly
        complexity = ctx.get("ast_complexity")
        if complexity and complexity > 15:
            args.append(CounterArgument(
                claim="高圈复杂度区域可能被遗漏",
                reasoning=f"AST 分析显示圈复杂度达 {complexity}，远超推荐阈值 10。该区域的代码变更可能引入了未被主判断覆盖的逻辑分支。",
                severity="strong",
            ))

        # Lint violation anomaly
        lint_count = ctx.get("lint_violation_count", 0)
        if lint_count > 5:
            args.append(CounterArgument(
                claim="大量 Lint 违规可能掩盖更深层问题",
                reasoning=f"存在 {lint_count} 条 Lint 违规。大量风格问题往往是匆忙提交的信号，可能伴随测试覆盖不足或逻辑错误。",
                severity="weak",
            ))

        # SAST high-severity findings
        sast_count = ctx.get("sast_high_severity_count", 0)
        if sast_count > 0:
            args.append(CounterArgument(
                claim="安全扫描发现高风险项",
                reasoning=f"SAST 扫描发现 {sast_count} 个高风险项。即使主判断未归类为阻断，建议逐项人工确认。",
                severity="fatal",
            ))

        # Large effective change
        effective_lines = ctx.get("effective_lines_changed", 0)
        if effective_lines > 200:
            args.append(CounterArgument(
                claim="变更量过大，审查可能存在疏漏",
                reasoning=f"有效变更 {effective_lines} 行。大规模变更更容易遗漏边界情况和交互效应。",
                severity="strong",
            ))

        return args

    def _challenge_patterns(self, claim: str) -> list[CounterArgument]:
        """Challenge common overconfidence/absolutist patterns."""
        args = []

        claim_lower = claim.lower()

        # Absolute language patterns
        absolute_words = ["always", "never", "must", "绝不", "必须", "一定", "绝对"]
        if any(w in claim_lower for w in absolute_words):
            args.append(CounterArgument(
                claim="绝对化断言需要更强证据支撑",
                reasoning="判断使用了绝对化语言。软件工程中很少有绝对的规则，建议检查是否存在合理的例外场景。",
                severity="weak",
            ))

        # Subjective dimension claims
        subjective_words = ["readability", "maintainability", "可读", "可维护", "优雅", "elegant"]
        if any(w in claim_lower for w in subjective_words):
            args.append(CounterArgument(
                claim="主观维度判断存在合理分歧空间",
                reasoning="可读性和可维护性是主观维度，不同开发者可能有不同理解。建议标注为主观建议而非阻断性判断。",
                severity="strong",
            ))

        # Security claims without test evidence
        security_words = ["security", "vulnerability", "安全", "漏洞", "注入", "injection"]
        test_words = ["test", "测试", "poc", "验证"]
        if any(w in claim_lower for w in security_words) and not any(w in claim_lower for w in test_words):
            args.append(CounterArgument(
                claim="安全判断未提及测试验证",
                reasoning="安全相关的判断应包含对应的测试用例或 PoC。建议补充攻击向量验证。",
                severity="strong",
            ))

        return args

    def _calculate_strength(self, args: list[CounterArgument]) -> float:
        """Calculate overall dissent strength from argument severities."""
        if not args:
            return 0.0
        total = sum(self.SEVERITY_WEIGHTS.get(a.severity, 0.3) for a in args)
        return min(1.0, total / len(args))

    def _collect_checks(self, args: list[CounterArgument]) -> list[str]:
        """Collect required verification checks from dissent arguments."""
        checks = []
        for a in args:
            if a.severity == "fatal":
                checks.append(f"人工确认: {a.claim}")
                checks.append("建议增加对应的自动化测试")
            elif a.severity == "strong":
                checks.append(f"补充验证: {a.claim}")
            else:
                checks.append(f"可选验证: {a.claim}")
        return list(dict.fromkeys(checks))  # deduplicate


# ── Integration helpers ──

def challenge_claim_with_dissent(
    claim: str,
    evidence: list[dict[str, Any]],
    consensus_health: Optional[str] = None,
    ast_complexity: Optional[int] = None,
    lint_count: Optional[int] = None,
    sast_count: Optional[int] = None,
    effective_lines: Optional[int] = None,
) -> DissentResult:
    """One-shot dissent challenge against a claim.

    Integrates with:
      - consensus_v2: if health == "critical", force dissent
      - hard_truth: if L2+ mode, require dissent

    Args:
        claim: Claim text
        evidence: Evidence items
        consensus_health: From consensus_v2.diversity_alert_pipeline ["health"]
        ast_complexity: From AST analyzer (restricted view)
        lint_count: From lint analyzer (restricted view)
        sast_count: From SAST analyzer (restricted view)
        effective_lines: Effective lines changed (restricted view)
    """
    # Build restricted context if data available
    restricted = None
    if any(x is not None for x in [ast_complexity, lint_count, sast_count, effective_lines]):
        restricted = {
            "ast_complexity": ast_complexity,
            "lint_violation_count": lint_count,
            "sast_high_severity_count": sast_count,
            "effective_lines_changed": effective_lines,
        }

    agent = DissentAgent(max_counterarguments=3)
    result = agent.challenge(claim, evidence, restricted)

    # If consensus is critical, amplify dissent
    if consensus_health == "critical":
        result.strength = min(1.0, result.strength * 1.5)
        result.should_reduce_confidence = True

    return result
