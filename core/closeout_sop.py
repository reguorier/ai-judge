#!/usr/bin/env python3
"""Standard closeout SOP for AI Judge final reports.

This module keeps the human-facing closeout contract separate from rendering.
Every client can rely on the same sequence: final judgment, one-sentence plan,
phased execution, Codex execution template, output requirements, and evidence
boundary.
"""

from __future__ import annotations

from typing import Any


CLOSEOUT_SOP_SCHEMA = "ai_judge.closeout_sop.v1"


def build_closeout_sop(
    verdict: dict[str, Any],
    *,
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage_label: str,
    recommendation: str,
    risk_line: str,
    next_action: str,
    findings: list[str],
    plan: list[str],
    risks: list[str],
) -> dict[str, Any]:
    """Build the product-wide SOP closeout block."""
    question = _text(verdict.get("question") or "")
    product_workflow = _is_ai_judge_workflow(question)
    topic = _topic(question)
    final_judgment = _final_judgment(
        topic=topic,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage_label=coverage_label,
        product_workflow=product_workflow,
    )
    one_sentence_plan = _one_sentence_plan(
        recommendation=recommendation,
        product_workflow=product_workflow,
        topic=topic,
    )
    phases = _phases(
        product_workflow=product_workflow,
        recommendation=recommendation,
        next_action=next_action,
        risk_line=risk_line,
        findings=findings,
        plan=plan,
        risks=risks,
    )
    codex_template = _codex_template(
        topic=topic,
        product_workflow=product_workflow,
        recommendation=recommendation,
        next_action=next_action,
        risk_line=risk_line,
        plan=plan,
    )
    return {
        "schema": CLOSEOUT_SOP_SCHEMA,
        "title": "标准化收口 SOP",
        "style": "codex_human_closeout",
        "final_judgment": final_judgment,
        "one_sentence_plan": one_sentence_plan,
        "phases": phases,
        "codex_template": codex_template,
        "evidence_boundary": [
            "保留原始模型回答，不用法官总结覆盖模型原文。",
            "单独保存外部证据与引用验证，不把 source exists 等同于 claim is proven。",
            "审计结论必须同时给出 citation status、claim support status、Replay Ledger 和人工确认状态。",
        ],
        "final_essence": _final_essence(
            topic=topic,
            verdict_label=verdict_label,
            confidence=confidence,
            recommendation=recommendation,
            product_workflow=product_workflow,
        ),
    }


def _final_judgment(
    *,
    topic: str,
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage_label: str,
    product_workflow: bool,
) -> str:
    if product_workflow:
        return (
            f"最终判断：{verdict_label}，置信度 {confidence}，席位覆盖 {coverage_label}。"
            "不要再把页面做成模型材料堆叠；先把 AI Judge 标准化成可信、可追溯、可执行的审计收口协议。"
        )
    trust_text = f"，可信等级 {trust}" if trust else ""
    return f"最终判断：{verdict_label}，置信度 {confidence}{trust_text}，席位覆盖 {coverage_label}。围绕“{topic}”进入分阶段执行。"


def _one_sentence_plan(*, recommendation: str, product_workflow: bool, topic: str) -> str:
    if product_workflow:
        return "一句话方案：先给人话结论，再给 Phase 执行路线和 Codex 执行模板，最后把证据链、模型原文和评分依据放进附录。"
    return f"一句话方案：{recommendation or f'把“{topic}”拆成结论、依据、风险、下一步和验收指标。'}"


def _phases(
    *,
    product_workflow: bool,
    recommendation: str,
    next_action: str,
    risk_line: str,
    findings: list[str],
    plan: list[str],
    risks: list[str],
) -> list[dict[str, Any]]:
    if product_workflow:
        return [
            {
                "title": "Phase 1: 收口体验基线",
                "items": [
                    "当前页只展示最终判断、一句话方案、风险和下一步。",
                    "专业报告通过固定锚点展开，不把模型原文塞进首屏。",
                    "客户端和网站报告共用同一份 final_report.sop_closeout 结构。",
                ],
            },
            {
                "title": "Phase 2: 可信度与证据链",
                "items": [
                    "保留 raw model answers、导师补充、外部证据和审计结论的隔离关系。",
                    "明确区分 source exists 和 claim is proven。",
                    "输出 Certification ID、Replay Ledger、citation status、claim support status。",
                ],
            },
            {
                "title": "Phase 3: 桌面端可用性审核",
                "items": [
                    "所有入口必须能回到最终报告、席位原文、证据审查和发布确认。",
                    "按钮状态必须说明为什么可点或不可点。",
                    "失败席位只读回收、刷新、遮挡清理和慢生成状态必须有明确恢复路径。",
                ],
            },
            {
                "title": "Phase 4: 发布门禁与复盘",
                "items": [
                    "发布前必须有人类确认当前判断可以作为决策依据。",
                    "未完成席位、引用不可验证或高风险分歧会自动降级为阶段性报告。",
                    "每轮执行后回填测试结果、改动文件、遗留风险和下一轮任务。",
                ],
            },
        ]
    return [
        {
            "title": "Phase 1: 决策基线",
            "items": _fallback_items([recommendation, findings[0] if findings else "", next_action], "先把结论、依据和下一步写成一页可读收口。"),
        },
        {
            "title": "Phase 2: 证据与风险",
            "items": _fallback_items([risk_line, *(risks[:2])], "补齐证据链，标注不可验证内容和最大反方观点。"),
        },
        {
            "title": "Phase 3: 执行与验证",
            "items": _fallback_items(plan[:3], "按最小可执行动作推进，并记录验证结果。"),
        },
        {
            "title": "Phase 4: 发布与复盘",
            "items": [
                "人工确认后再对外发布或作为决策依据。",
                "新增反例、席位失败或证据不足时降级报告并重跑。",
                "把结论、证据、风险和测试结果回填到下一轮输入。",
            ],
        },
    ]


def _codex_template(
    *,
    topic: str,
    product_workflow: bool,
    recommendation: str,
    next_action: str,
    risk_line: str,
    plan: list[str],
) -> dict[str, Any]:
    if product_workflow:
        goal = "把 AI Judge 全流程收口标准化，让每次运行都能输出人能一眼读懂、又可审计复盘的最终方案。"
        positioning = (
            "AI Judge 是 source-isolated citation and claim-support audit 工具。"
            "它不是重写 AI 答案，而是保存原始回答、导师补充、外部证据和审计结论，并输出可信决策报告。"
        )
    else:
        goal = f"围绕“{topic}”输出可执行、可验证、可复盘的最终方案。"
        positioning = "AI Judge 负责把多席位判断转成决策收口；原始模型回答和证据链必须可追溯。"
    priorities = _fallback_items([recommendation, next_action, *(plan[:4])], "先处理最高影响、最低可逆成本的动作。")
    return {
        "label": "Codex 执行模板",
        "goal": goal,
        "positioning": positioning,
        "current_priorities": priorities,
        "execution_rules": [
            "不做虚假宣传，不把 unverifiable 说成 verified。",
            "不混合模型原文、补充意见和外部证据。",
            "不自动发布、提交论文或对外承诺，除非用户明确确认。",
            "每次外部动作后更新 ledger/status 文件。",
            "每次代码变更后运行测试并报告结果。",
        ],
        "output_requirements": [
            "本轮做了什么。",
            "当前卡点是什么。",
            "新增了什么公开资产或内部资产。",
            "是否出现用户回复、关注、商业或验证信号。",
            "下一步最该做什么。",
            "涉及的文件、测试结果和剩余风险。",
        ],
        "risk_to_watch": risk_line,
    }


def _final_essence(
    *,
    topic: str,
    verdict_label: str,
    confidence: str,
    recommendation: str,
    product_workflow: bool,
) -> str:
    if product_workflow:
        return (
            f"最终你拿到的方案本质上是：不是继续美化报告页，而是把 AI Judge 做成一套标准化审计协议。"
            f"当前判断为“{verdict_label}”，置信度 {confidence}；每一步输出都必须能被阅读、验证和复盘。"
        )
    return (
        f"最终你拿到的方案本质上是：围绕“{topic}”的可执行判断。"
        f"当前判断为“{verdict_label}”，建议从“{recommendation}”开始。"
    )


def _fallback_items(values: list[Any], fallback: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _compact(value, 120)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if len(items) >= 4:
            break
    return items or [fallback]


def _is_ai_judge_workflow(question: str) -> bool:
    markers = ("AI Judge", "ai judge", "报告", "摘要", "排版", "论文", "PDF", "总结", "人话", "SOP", "sop", "客户端", "桌面端")
    return any(marker in question for marker in markers)


def _topic(question: str) -> str:
    return _compact(question or "当前议题", 90)


def _compact(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _text(value: Any) -> str:
    return str(value or "").strip()
