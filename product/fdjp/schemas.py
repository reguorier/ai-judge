"""FDJP data schemas – dataclass definitions and serialisation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DimensionFinding:
    finding_id: str
    dimension: str
    claim: str
    claim_type: str = "heuristic"
    basis: list[str] = field(default_factory=list)
    confidence: float = 0.0
    risk_if_wrong: str = ""
    counterargument: str = ""
    action_impact: str = ""
    source_seats: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    # ── LLM/Hybrid fields ──
    status: str = ""                 # pass/warning/blocker/insufficient
    evidence_refs: list[str] = field(default_factory=list)
    reasoning_summary: str = ""
    source: str = "heuristic"        # llm/heuristic/hybrid
    blocker_id: str | None = None
    warning_id: str | None = None
    # ── Structured assertion / constraint fields ──
    assumptions: list[str] = field(default_factory=list)
    verifiable: str = ""
    constraint: str = ""
    source_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "dimension": self.dimension,
            "claim": self.claim,
            "claim_type": self.claim_type,
            "basis": self.basis,
            "confidence": self.confidence,
            "risk_if_wrong": self.risk_if_wrong,
            "counterargument": self.counterargument,
            "action_impact": self.action_impact,
            "source_seats": self.source_seats,
            "evidence_ids": self.evidence_ids,
            "status": self.status,
            "evidence_refs": self.evidence_refs,
            "reasoning_summary": self.reasoning_summary,
            "source": self.source,
            "blocker_id": self.blocker_id,
            "warning_id": self.warning_id,
            "assumptions": self.assumptions,
            "verifiable": self.verifiable,
            "constraint": self.constraint,
            "source_excerpt": self.source_excerpt,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DimensionFinding:
        return cls(
            finding_id=d.get("finding_id", ""),
            dimension=d.get("dimension", ""),
            claim=d.get("claim", ""),
            claim_type=d.get("claim_type", "heuristic"),
            basis=d.get("basis", []),
            confidence=d.get("confidence", 0.0),
            risk_if_wrong=d.get("risk_if_wrong", ""),
            counterargument=d.get("counterargument", ""),
            action_impact=d.get("action_impact", ""),
            source_seats=d.get("source_seats", []),
            evidence_ids=d.get("evidence_ids", []),
            status=d.get("status", ""),
            evidence_refs=d.get("evidence_refs", []),
            reasoning_summary=d.get("reasoning_summary", ""),
            source=d.get("source", "heuristic"),
            blocker_id=d.get("blocker_id"),
            warning_id=d.get("warning_id"),
            assumptions=d.get("assumptions", []),
            verifiable=d.get("verifiable", ""),
            constraint=d.get("constraint", ""),
            source_excerpt=d.get("source_excerpt", ""),
        )


@dataclass
class DimensionReport:
    dimension: str
    label: str = ""
    core_question: str = ""
    summary: str = ""
    findings: list[DimensionFinding] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    score: float = 0.0
    coverage_score: float = 0.0
    evidence_score: float = 0.0
    actionability_score: float = 0.0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "label": self.label,
            "core_question": self.core_question,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "open_questions": self.open_questions,
            "risks": self.risks,
            "score": self.score,
            "coverage_score": self.coverage_score,
            "evidence_score": self.evidence_score,
            "actionability_score": self.actionability_score,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DimensionReport:
        return cls(
            dimension=d.get("dimension", ""),
            label=d.get("label", ""),
            core_question=d.get("core_question", ""),
            summary=d.get("summary", ""),
            findings=[DimensionFinding.from_dict(f) for f in d.get("findings", [])],
            open_questions=d.get("open_questions", []),
            risks=d.get("risks", []),
            score=d.get("score", 0.0),
            coverage_score=d.get("coverage_score", 0.0),
            evidence_score=d.get("evidence_score", 0.0),
            actionability_score=d.get("actionability_score", 0.0),
            status=d.get("status", "pending"),
        )


@dataclass
class DimensionAudit:
    run_id: str
    task_id: str = ""
    task_type: str = "general"
    status: str = "FDJP_RUNTIME_BLOCKED"
    mode: str = "heuristic"
    # ── LLM/Hybrid fields ──
    audit_mode: str = "heuristic_only"       # llm/hybrid/heuristic_only/unavailable
    requested_mode: str = "heuristic_only"
    effective_mode: str = "heuristic_only"
    overall_score: float = 0.0
    dimension_scores: dict[str, float] = field(default_factory=dict)
    dimensions: dict[str, DimensionReport] = field(default_factory=dict)
    findings: list[DimensionFinding] = field(default_factory=list)
    insights: list[dict[str, Any]] = field(default_factory=list)
    cross_dimension_conflicts: list[dict[str, Any]] = field(default_factory=list)
    gates: dict[str, Any] = field(default_factory=dict)
    report_blocks: list[dict[str, Any]] = field(default_factory=list)
    llm_metadata: dict[str, Any] = field(default_factory=dict)
    heuristic_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    version: str = "FDJP-1.0"
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "mode": self.mode,
            "audit_mode": self.audit_mode,
            "requested_mode": self.requested_mode,
            "effective_mode": self.effective_mode,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "dimensions": {
                k: v.to_dict() for k, v in self.dimensions.items()
            },
            "findings": [f.to_dict() for f in self.findings],
            "insights": self.insights,
            "cross_dimension_conflicts": self.cross_dimension_conflicts,
            "gates": self.gates,
            "report_blocks": self.report_blocks,
            "llm_metadata": self.llm_metadata,
            "heuristic_metadata": self.heuristic_metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DimensionAudit:
        dims = {}
        for k, v in d.get("dimensions", {}).items():
            dims[k] = DimensionReport.from_dict(v)
        return cls(
            run_id=d.get("run_id", ""),
            task_id=d.get("task_id", ""),
            task_type=d.get("task_type", "general"),
            status=d.get("status", "FDJP_RUNTIME_BLOCKED"),
            mode=d.get("mode", "heuristic"),
            audit_mode=d.get("audit_mode", d.get("mode", "heuristic_only")),
            requested_mode=d.get("requested_mode", "heuristic_only"),
            effective_mode=d.get("effective_mode", "heuristic_only"),
            overall_score=d.get("overall_score", 0.0),
            dimension_scores=d.get("dimension_scores", {}),
            dimensions=dims,
            findings=[DimensionFinding.from_dict(f) for f in d.get("findings", [])],
            insights=d.get("insights", []),
            cross_dimension_conflicts=d.get("cross_dimension_conflicts", []),
            gates=d.get("gates", {}),
            report_blocks=d.get("report_blocks", []),
            llm_metadata=d.get("llm_metadata", {}),
            heuristic_metadata=d.get("heuristic_metadata", {}),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            version=d.get("version", "FDJP-1.0"),
            schema_version=d.get("schema_version", "1.0"),
        )


def dimension_audit_to_dict(audit: DimensionAudit) -> dict[str, Any]:
    return audit.to_dict()


def dimension_audit_from_dict(d: dict[str, Any]) -> DimensionAudit:
    return DimensionAudit.from_dict(d)


def dimension_audit_to_json(audit: DimensionAudit, indent: int = 2) -> str:
    return json.dumps(audit.to_dict(), ensure_ascii=False, indent=indent) + "\n"


def dimension_audit_from_json(s: str) -> DimensionAudit:
    return DimensionAudit.from_dict(json.loads(s))
