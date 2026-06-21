"""Legal memo publication adapter."""

from __future__ import annotations

import re
from typing import Any

from product.reporting.publication.schema import as_text_items, build_block, build_table, clip_text


RULE_PATTERN = re.compile(r"《[^》]{2,40}》(?:第[一二三四五六七八九十百千万零〇0-9]+条)?")


def build_legal_memo_blocks(
    report: dict[str, Any],
    *,
    seat_matrix: dict[str, Any] | None = None,
    evidence_packet: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    body = "\n".join(
        str(part)
        for part in (
            report.get("core_conclusion"),
            report.get("body_text"),
            report.get("scope"),
        )
        if part
    )
    rules = _extract_rules(body)
    facts = as_text_items(report.get("verified_facts"), limit=8)
    inferences = as_text_items(report.get("inferences"), limit=8)
    risks = as_text_items(report.get("risks") or report.get("failure_conditions"), limit=8)
    actions = as_text_items(report.get("recommended_actions"), limit=8)

    return [
        build_block(
            "legal_conclusion",
            "法律版 · 结论",
            kind="legal_conclusion",
            summary=report.get("core_conclusion") or "当前材料不足以形成正式法律结论。",
            items=_numbered_conclusions(report.get("core_conclusion") or body),
            level="industry",
        ),
        build_block(
            "legal_basis",
            "法律依据",
            kind="legal_basis",
            summary="先列依据，再进入事实和涵摄，减少模型直接跳结论造成的噪声。",
            items=rules or ["未识别到明确法条；应补充可核验法律依据。"],
            level="industry",
        ),
        build_block(
            "facts_and_subsumption",
            "事实认定与涵摄",
            kind="legal_subsumption",
            summary="把已验证事实和推断分开呈现，避免把推断包装成事实。",
            table=build_table(
                ["层次", "内容"],
                [["已验证事实", "\n".join(facts) or "暂无"], ["涵摄/推断", "\n".join(inferences) or "暂无"]],
            ),
            level="industry",
        ),
        build_block(
            "legal_paths",
            "可行路径",
            kind="legal_paths",
            summary="法律输出必须给可执行路径，而不是只给抽象判断。",
            items=actions or _default_legal_actions(body),
            level="industry",
        ),
        build_block(
            "legal_risks",
            "反方观点、风险与证据缺口",
            kind="legal_risks",
            summary="高风险法律问题必须保留反方观点和复核清单。",
            table=build_table(
                ["风险/反方观点", "复核动作"],
                _risk_rows(risks),
            ),
            level="industry",
        ),
        build_block(
            "lawyer_checklist",
            "律师复核清单",
            kind="checklist",
            summary="该报告是办案研判底稿，不替代执业律师对材料和程序状态的复核。",
            items=[
                "核对主体身份、登记状态、合同/判决/执行文书原件。",
                "核对最新法条、司法解释、地方裁判规则和法院执行口径。",
                "将模型推断逐条对应到证据目录，不能对应的内容标为待补证。",
                "对金额、期限、管辖、时效、优先顺位进行人工复算。",
            ],
            level="industry",
        ),
    ]


def _extract_rules(text: str) -> list[str]:
    seen: set[str] = set()
    rules: list[str] = []
    for match in RULE_PATTERN.findall(text):
        if match not in seen:
            seen.add(match)
            rules.append(match)
        if len(rules) >= 10:
            break
    return rules


def _numbered_conclusions(text: str) -> list[str]:
    if not text:
        return []
    lines = [line.strip(" -\t") for line in re.split(r"[\n。；;]", text) if line.strip()]
    return [clip_text(line, 240) for line in lines[:5]]


def _default_legal_actions(text: str) -> list[str]:
    if "执行" in text:
        return [
            "先确认执行依据和被执行财产范围。",
            "申请法院对可执行财产进行查控、评估、拍卖或变卖。",
            "若涉及股权、登记或第三人权益，补充公司章程、股东名册和工商登记材料。",
        ]
    return [
        "补齐基础事实和证据目录。",
        "按请求权基础拆分主张、抗辩和证明责任。",
        "交由律师复核后再形成正式意见。",
    ]


def _risk_rows(risks: list[str]) -> list[list[str]]:
    if not risks:
        risks = ["事实材料不足或法律依据未核验时，不宜直接出具正式法律意见。"]
    return [[risk, "补证、检索最新规则并由律师复核"] for risk in risks[:8]]
