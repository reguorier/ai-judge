"""Structured intermediate representation for AI Judge report rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JUDGE_IR_SCHEMA = "ai_judge.judge_ir.v1"
SECTION_ORDER = ("summary", "metrics", "analysis", "comparison", "risk", "appendix")
COMPONENT_TYPES = (
    "MetricGrid",
    "ModelComparisonTable",
    "RiskMatrix",
    "EvidenceBlock",
    "RailSummary",
    "AppendixPanel",
)


@dataclass(frozen=True)
class IRComponent:
    """A registry-rendered UI component with structured props only."""

    type: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IRSection:
    """A fixed-layout section in the compiled report."""

    slot: str
    title: str
    components: tuple[IRComponent, ...] = ()


@dataclass(frozen=True)
class JudgeIR:
    """Publication-grade report IR consumed by deterministic renderers."""

    title: str
    subtitle: str
    run_id: str
    domain_label: str
    generated_at: str
    sections: tuple[IRSection, ...]
    rail: IRComponent
    quality: dict[str, Any] = field(default_factory=dict)
    schema: str = JUDGE_IR_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "title": self.title,
            "subtitle": self.subtitle,
            "run_id": self.run_id,
            "domain_label": self.domain_label,
            "generated_at": self.generated_at,
            "quality": self.quality,
            "sections": [
                {
                    "slot": section.slot,
                    "title": section.title,
                    "components": [
                        {"type": component.type, "props": component.props}
                        for component in section.components
                    ],
                }
                for section in self.sections
            ],
            "rail": {"type": self.rail.type, "props": self.rail.props},
        }
