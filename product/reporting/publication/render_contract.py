"""Render contract enforcement for JudgeIR."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.judge_ir import (
    COMPONENT_TYPES,
    JUDGE_IR_SCHEMA,
    SECTION_ORDER,
    IRComponent,
    IRSection,
    JudgeIR,
)


class RenderContractError(ValueError):
    """Raised when a renderer receives unstructured or unsafe input."""


def validate_judge_ir(ir: Any) -> JudgeIR:
    """Validate and return a JudgeIR object before rendering."""

    if not isinstance(ir, JudgeIR):
        raise RenderContractError("render_input_must_be_judge_ir")
    if ir.schema != JUDGE_IR_SCHEMA:
        raise RenderContractError("unsupported_judge_ir_schema")
    if not ir.title.strip():
        raise RenderContractError("missing_ir_title")
    if not ir.run_id.strip():
        raise RenderContractError("missing_ir_run_id")

    slots = tuple(section.slot for section in ir.sections)
    if slots != SECTION_ORDER:
        raise RenderContractError("invalid_section_order")

    for section in ir.sections:
        _validate_section(section)
    _validate_component(ir.rail)
    return ir


def _validate_section(section: IRSection) -> None:
    if not section.title.strip():
        raise RenderContractError(f"missing_section_title:{section.slot}")
    if section.slot not in SECTION_ORDER:
        raise RenderContractError(f"unknown_section_slot:{section.slot}")
    for component in section.components:
        _validate_component(component)


def _validate_component(component: IRComponent) -> None:
    if component.type not in COMPONENT_TYPES:
        raise RenderContractError(f"unknown_component:{component.type}")
    if not isinstance(component.props, dict):
        raise RenderContractError(f"component_props_must_be_object:{component.type}")
    _reject_raw_html(component.props, path=component.type)


def _reject_raw_html(value: Any, *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in {"html", "raw_html", "innerhtml", "dangerouslysetinnerhtml"}:
                raise RenderContractError(f"raw_html_prop_rejected:{path}.{key}")
            _reject_raw_html(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_raw_html(child, path=f"{path}[{index}]")
    elif isinstance(value, tuple):
        for index, child in enumerate(value):
            _reject_raw_html(child, path=f"{path}[{index}]")
