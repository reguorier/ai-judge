#!/usr/bin/env python3
"""Evidence Object v3.2 — Structured evidence with source tracing.

Inspired by Tianfu Agent's knowledge-tracing (each conclusion cites its source).
AI Judge advantage: harness Ground Truth replaces Tianfu's ancient-text verification.

Integrates with:
  - formula_engine.evaluate_bluff_ev (bluff detection gate)
  - scoring_v2.score_claim_v2 (evidence feeds into scoring)
  - hard_truth (Ground Truth conflict detection)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Evidence:
    """Single piece of evidence backing a claim.

    Every claim must have at least one Evidence. Claims without evidence
    are automatically downgraded to 'suggestion' tier.
    """
    kind: str  # "tool_result" | "rule_match" | "harness_result" | "precedent"
    description: str
    source_path: Optional[str] = None       # File path for IDE jump
    source_line: Optional[int] = None       # Line number in source file
    rule_id: Optional[str] = None           # e.g. "OWASP A03:2021"
    tool_name: Optional[str] = None         # e.g. "sast", "lint", "test_runner"
    confidence: float = 0.5                 # Tool/rule intrinsic confidence
    verifiable: bool = True                 # Can be objectively verified?

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "source_path": self.source_path,
            "source_line": self.source_line,
            "rule_id": self.rule_id,
            "tool_name": self.tool_name,
            "confidence": self.confidence,
            "verifiable": self.verifiable,
        }

    @classmethod
    def from_tool(cls, tool_name: str, finding_id: str, description: str,
                  file_path: str = "", line: int = 0,
                  tool_confidence: float = 0.9, verifiable: bool = True) -> "Evidence":
        return cls(
            kind="tool_result",
            description=f"[{tool_name}] {description}",
            source_path=file_path,
            source_line=line,
            tool_name=tool_name,
            confidence=tool_confidence,
            verifiable=verifiable,
        )

    @classmethod
    def from_rule(cls, rule_id: str, source: str, description: str,
                  match_confidence: float = 0.9) -> "Evidence":
        return cls(
            kind="rule_match",
            description=description,
            rule_id=rule_id,
            confidence=match_confidence,
            verifiable=True,
        )

    @classmethod
    def from_harness(cls, test_suite: str, passed: bool,
                     description: str = "", coverage_delta: float = 0.0) -> "Evidence":
        return cls(
            kind="harness_result",
            description=description or f"Harness [{test_suite}]: {'PASS' if passed else 'FAIL'}",
            tool_name=test_suite,
            confidence=1.0 if passed else 0.0,
            verifiable=True,
        )

    @classmethod
    def from_precedent(cls, case_id: str, similarity: float, outcome: str) -> "Evidence":
        return cls(
            kind="precedent",
            description=f"Precedent [{case_id}]: {outcome} (similarity={similarity:.0%})",
            confidence=similarity,
            verifiable=False,
        )


@dataclass
class EvidenceBundle:
    """Collection of evidence items with aggregate metrics."""

    items: list[Evidence] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def verifiable_count(self) -> int:
        return sum(1 for e in self.items if e.verifiable)

    @property
    def verifiable_ratio(self) -> float:
        if not self.items:
            return 0.0
        return self.verifiable_count / len(self.items)

    @property
    def avg_confidence(self) -> float:
        if not self.items:
            return 0.0
        return sum(e.confidence for e in self.items) / len(self.items)

    @property
    def has_harness_conflict(self) -> bool:
        """Check if harness results conflict (some pass, some fail)."""
        harness_results = [e for e in self.items if e.kind == "harness_result"]
        passes = sum(1 for e in harness_results if e.confidence > 0.5)
        fails = len(harness_results) - passes
        return fails > 0

    def add(self, evidence: Evidence) -> None:
        self.items.append(evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_evidence": self.count,
            "verifiable_count": self.verifiable_count,
            "verifiable_ratio": round(self.verifiable_ratio, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "has_harness_conflict": self.has_harness_conflict,
            "items": [e.to_dict() for e in self.items],
        }

    # ── Evidence strength calculation (feeds into allocation_score) ──

    def compute_evidence_strength(self) -> float:
        """Compute overall evidence strength for allocation_score.

        Tianfu-inspired: weight = verifiability × tool_confidence × source_diversity.
        """
        if not self.items:
            return 0.0

        # Verifiability bonus
        ver_bonus = self.verifiable_ratio

        # Tool diversity bonus (multiple independent tools > single tool)
        tools = set(e.tool_name for e in self.items if e.tool_name)
        diversity_bonus = min(1.0, len(tools) / 3.0)  # max at 3+ tools

        # Average confidence
        avg_conf = self.avg_confidence

        return min(1.0, 0.4 * ver_bonus + 0.3 * diversity_bonus + 0.3 * avg_conf)

    def compute_evidence_quality(self) -> float:
        """Compute evidence quality (feeds into evaluate_bluff_ev)."""
        if not self.items:
            return 0.0
        # Quality = verifiability × avg_confidence
        return self.verifiable_ratio * self.avg_confidence
