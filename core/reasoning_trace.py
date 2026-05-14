#!/usr/bin/env python3
"""Reasoning Trace v3.2 — Tree-structured judgment reasoning chain.

Inspired by Tianfu Agent's visualized reasoning chain:
  From input → fact collection → evidence → rule matching → dissent → conclusion.

Integrates with:
  - scoring_v2.score_claim_v2 → claim-level trace
  - determinism.ConfidenceLight → confidence node
  - dissent.DissentResult → dissent node
  - evidence.EvidenceBundle → evidence nodes

Output: ReasoningNode tree ready for UI rendering (ReasoningTree.tsx).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ReasoningNode:
    """Single node in the reasoning tree.

    Mirrors the TypeScript ReasoningNodeData interface for seamless JSON serialization
    to the Tauri frontend.
    """
    id: str
    kind: str                  # "fact" | "evidence" | "rule" | "dissent" | "conclusion"
    label: str                 # Short display text
    detail: str = ""           # Expanded detail text
    confidence: Optional[float] = None
    source: Optional[dict[str, Any]] = None  # { filePath, line, ruleId, toolName }
    children: list["ReasoningNode"] = field(default_factory=list)
    disputed: bool = False
    collapsed_by_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "detail": self.detail,
            "confidence": self.confidence,
            "source": self.source,
            "children": [c.to_dict() for c in self.children],
            "disputed": self.disputed,
            "collapsedByDefault": self.collapsed_by_default,
        }


class ReasoningTracer:
    """Build a tree-structured reasoning chain from the scoring pipeline.

    Maps to Tianfu Agent's reasoning visualization data structure.
    Integrates with existing scoring_v2, determinism, dissent, and evidence modules.
    """

    def build_tree(
        self,
        verdict_summary: str,
        task_info: dict[str, Any],
        evidence_items: list[dict[str, Any]] = None,
        rule_matches: list[dict[str, Any]] = None,
        dissent_result: Optional[dict[str, Any]] = None,
        confidence_light: Optional[dict[str, Any]] = None,
    ) -> ReasoningNode:
        """Build the complete reasoning tree.

        Args:
            verdict_summary: Final verdict summary string
            task_info: Task metadata (files_changed, lines_added, modules, etc.)
            evidence_items: List of evidence dicts from Evidence.to_dict()
            rule_matches: List of rule match dicts
            dissent_result: DissentResult.to_dict()
            confidence_light: ConfidenceLight dict from determinism
        """
        evidence_items = evidence_items or []
        rule_matches = rule_matches or []

        # Root: Conclusion
        root = ReasoningNode(
            id="root",
            kind="conclusion",
            label=verdict_summary,
            detail=self._build_verdict_detail(task_info, len(evidence_items),
                                               len(rule_matches), dissent_result),
            confidence=confidence_light.get("confidence") if confidence_light else None,
            disputed=dissent_result is not None and dissent_result.get("should_reduce_confidence", False),
        )

        # 1. Facts section
        root.children.append(self._build_fact_section(task_info))

        # 2. Evidence section
        if evidence_items:
            root.children.append(self._build_evidence_section(evidence_items))

        # 3. Rules section
        if rule_matches:
            root.children.append(self._build_rule_section(rule_matches))

        # 4. Dissent section
        if dissent_result:
            root.children.append(self._build_dissent_section(dissent_result))

        return root

    def _build_verdict_detail(self, task_info: dict, ev_count: int,
                               rule_count: int, dissent: Optional[dict]) -> str:
        lines = [
            f"任务: {task_info.get('task_id', 'unknown')}",
            f"证据: {ev_count} 条 | 规则: {rule_count} 条",
        ]
        if dissent:
            args = dissent.get("counterarguments", [])
            strength = dissent.get("strength", 0)
            lines.append(f"异议: {len(args)} 条反方论点 | 强度: {strength:.0%}")
        return "\n".join(lines)

    def _build_fact_section(self, task_info: dict) -> ReasoningNode:
        """Build fact collection node (Tianfu: 事实认定)."""
        modules = ", ".join(task_info.get("touched_modules", [])) or "无"
        risk = ", ".join(task_info.get("risk_surface", [])) or "无"
        test_status = task_info.get("test_status", "无测试")

        node = ReasoningNode(
            id="facts",
            kind="fact",
            label=f"变更 {task_info.get('files_changed', 0)} 个文件, "
                  f"+{task_info.get('lines_added', 0)}/-{task_info.get('lines_deleted', 0)} 行",
            detail=f"涉及模块: {modules}\n风险领域: {risk}\n测试状态: {test_status}",
        )

        # File-level sub-nodes
        for f in task_info.get("files", []):
            node.children.append(ReasoningNode(
                id=f"fact_file_{f.get('path', '').replace('/', '_')}",
                kind="fact",
                label=f"{f.get('path', '')} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})",
                detail=f"{f.get('hunks', 0)} 个变更块",
                source={
                    "filePath": f.get("path", ""),
                    "line": f.get("first_line"),
                } if f.get("path") else None,
                collapsed_by_default=True,
            ))

        return node

    def _build_evidence_section(self, evidence_items: list[dict]) -> ReasoningNode:
        """Build evidence section (Tianfu: 工具验证)."""
        verifiable = sum(1 for e in evidence_items if e.get("verifiable", True))
        total = len(evidence_items)

        node = ReasoningNode(
            id="evidence_section",
            kind="evidence",
            label=f"证据 ({total} 条)",
            detail=f"可验证: {verifiable} 条 | 不可验证: {total - verifiable} 条",
        )

        for i, e in enumerate(evidence_items):
            source = None
            if e.get("source_path") or e.get("source_line"):
                source = {
                    "filePath": e.get("source_path", ""),
                    "line": e.get("source_line"),
                    "ruleId": e.get("rule_id"),
                    "toolName": e.get("tool_name"),
                }

            node.children.append(ReasoningNode(
                id=f"evidence_{i}",
                kind="evidence",
                label=e.get("description", "")[:120],
                detail=f"类型: {e.get('kind', 'unknown')}\n"
                       f"置信度: {e.get('confidence', 0.5):.0%}\n"
                       f"可验证: {e.get('verifiable', True)}",
                confidence=e.get("confidence"),
                source=source,
            ))

        return node

    def _build_rule_section(self, rule_matches: list[dict]) -> ReasoningNode:
        """Build rule matching section (Tianfu: 规则匹配)."""
        node = ReasoningNode(
            id="rule_section",
            kind="rule",
            label=f"规则匹配 ({len(rule_matches)} 条)",
            detail="以下规则被触发:",
        )

        for r in rule_matches:
            node.children.append(ReasoningNode(
                id=f"rule_{r.get('rule_id', '')}",
                kind="rule",
                label=f"{r.get('source', '')} — {r.get('blocking_level', 'warning')}",
                detail=f"适用: {r.get('applies_to', '')}\n"
                       f"匹配精度: {r.get('match_confidence', 0.5):.0%}",
                confidence=r.get("match_confidence"),
                source={
                    "ruleId": r.get("rule_id"),
                } if r.get("rule_id") else None,
            ))

        return node

    def _build_dissent_section(self, dissent: dict) -> ReasoningNode:
        """Build dissent section (Tianfu: 异议/争议)."""
        args = dissent.get("counterarguments", [])
        args_text = "\n".join(
            f"• {a.get('claim', '')}: {a.get('reasoning', '')}"
            for a in args
        )

        checks = dissent.get("required_checks", [])
        checks_text = "\n".join(f"• {c}" for c in checks)

        node = ReasoningNode(
            id="dissent",
            kind="dissent",
            label=f"异议 ✦ (强度: {dissent.get('strength', 0):.0%})",
            detail=f"反方论点:\n{args_text}\n\n需要补充验证:\n{checks_text}",
            confidence=1.0 - dissent.get("strength", 0),
            disputed=True,
        )

        for i, a in enumerate(args):
            node.children.append(ReasoningNode(
                id=f"dissent_arg_{i}",
                kind="dissent",
                label=a.get("claim", "")[:100],
                detail=a.get("reasoning", ""),
                disputed=True,
                collapsed_by_default=True,
            ))

        return node


# ── Quick integration function ──

def build_reasoning_tree_from_pipeline(
    verdict_summary: str,
    task_info: dict[str, Any],
    evidence_items: Optional[list[dict[str, Any]]] = None,
    rule_matches: Optional[list[dict[str, Any]]] = None,
    dissent_result: Optional[dict[str, Any]] = None,
    confidence_light: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """One-shot: build the reasoning tree from pipeline outputs.

    Designed as the final step in score_jury_full_pipeline_v3().
    Returns a dict ready for JSON serialization to the Tauri frontend.
    """
    tracer = ReasoningTracer()
    tree = tracer.build_tree(
        verdict_summary=verdict_summary,
        task_info=task_info,
        evidence_items=evidence_items,
        rule_matches=rule_matches,
        dissent_result=dissent_result,
        confidence_light=confidence_light,
    )
    return tree.to_dict()
