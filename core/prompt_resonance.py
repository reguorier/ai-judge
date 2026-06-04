#!/usr/bin/env python3
"""Local prompt-alignment pass for AI Judge product runs.

This is intentionally lightweight and deterministic. It gives the product a
fast "resonance" layer before expensive or fragile deep collection starts:
normalize the user's ask, expose assumptions, and produce a stricter prompt
that downstream web/API/desktop seats can answer consistently.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from core.worldcup_pool import build_worldcup_pool_prompt_flow, is_worldcup_pool_prompt


MODE_LABELS = {
    "flash": "快速裁决",
    "standard": "标准议事",
    "strategic": "深度裁决",
}

# P69: Mode-specific system instructions
MODE_SYSTEM_INSTRUCTIONS = {
    "flash": (
        "你正在执行快速裁决模式。请优先给出明确结论，用较少轮次完成判断。"
        "输出应包含：核心结论、3-5条关键理由、主要风险、最小下一步。"
        "避免展开长篇多席位辩论，除非问题本身需要。"
    ),
    "strategic": (
        "你正在执行深度裁决模式。请按议会式流程处理问题：先拆解目标，"
        "再组织多个席位独立发言，进行交叉验证，标注证据、假设、分歧和不确定性，"
        "最后形成可审计裁决报告。输出应包含：问题拆解、席位观点、交叉验证、"
        "共识与分歧、风险、最终裁决、下一步行动。"
    ),
}


def build_prompt_flow(
    question: str,
    mode: str = "flash",
    engine: str = "local",
    seats: list[str] | None = None,
    bridge_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a product-facing alignment packet for a jury run."""
    original = question.strip()
    if is_worldcup_pool_prompt(original):
        return build_worldcup_pool_prompt_flow(
            question=original,
            mode=mode,
            engine=engine,
            seats=seats,
            bridge_summary=bridge_summary,
        )
    normalized = _normalize(original)
    intent = _infer_intent(normalized)
    required_output = _required_output(normalized)
    assumptions = _assumptions(normalized)
    seat_count = len(seats or [])
    bridge_summary = bridge_summary or {}

    professional_prompt = _professional_prompt(
        original=original,
        normalized=normalized,
        intent=intent,
        mode=mode,
        required_output=required_output,
        assumptions=assumptions,
    )

    ready_count = int(bridge_summary.get("ready_count") or 0)
    configured_count = int(bridge_summary.get("configured_count") or bridge_summary.get("enabled_count") or 0)
    quick_response = (
        f"我先把任务对齐为：{intent}。"
        f"本轮采用{MODE_LABELS.get(mode, mode)}，目标席位 {seat_count} 个。"
    )
    if engine == "web":
        quick_response += f" 网页桥接当前校准通过 {ready_count} 席，已配置 {configured_count} 席。"
    else:
        quick_response += " 先走本地稳定路径，深度外部席位可在桥接校准后接管。"

    return {
        "version": "prompt-resonance-v1",
        "original_question": original,
        "normalized_question": normalized,
        "intent": intent,
        "mode": mode,
        "engine": engine,
        "quick_response": quick_response,
        "professional_prompt": professional_prompt,
        "assumptions_to_check": assumptions,
        "required_output": required_output,
        "trace_id": _stable_id(original, mode, engine),
    }


def _normalize(question: str) -> str:
    return " ".join(question.split())


def _infer_intent(question: str) -> str:
    lowered = question.lower()
    has_forecast_term = bool(re.search(r"\bforecast\b", lowered)) and "forecast market" not in lowered
    has_prediction_cn = "预测" in lowered and "预测市场" not in lowered
    if has_prediction_cn or "世界杯" in question or "world cup" in lowered or has_forecast_term:
        return "做一个可审计的预测，并把假设、赛程结构、胜负路径和不确定性拆开"
    if any(token in lowered for token in ("方案", "升级", "落地", "开发")):
        return "把模糊需求收束成可执行产品方案，并识别先后顺序与风险"
    if any(token in lowered for token in ("评估", "是否", "该不该", "值得")):
        return "对一个决策做多席位评估，输出立场、条件和下一步验证"
    return "把问题拆成结论、证据、风险和下一步行动"


def _required_output(question: str) -> list[str]:
    lowered = question.lower()
    if "世界杯" in question or "world cup" in lowered:
        return [
            "逐组给出胜平负路径和小组排名",
            "给出淘汰赛完整晋级链路",
            "标明预测依据、关键变量和置信度",
            "区分事实、假设与主观判断",
        ]
    return [
        "独立结论或方案，标题必须对齐用户任务",
        "列出 3-5 条关键依据，并区分事实、推断和建议",
        "说明页面/流程/证据或实施结构，不要只给评价",
        "给出报告/文稿/交付物的专业格式建议",
        "指出最大风险、反方观点和失败条件",
        "若存在多个可行路径，列出至少 3 个可选方案供用户选择",
        "给出最小可执行下一步和验收标准",
    ]


def _assumptions(question: str) -> list[str]:
    items = []
    if "2026" in question and "世界杯" in question:
        items.extend([
            "需要以已公布赛制、参赛队和分组信息为事实边界",
            "若最终名单、伤病或抽签尚未完全确定，必须标注为预测变量",
        ])
    if "全量" in question or "每个" in question:
        items.append("用户期待覆盖完整范围，不能只给样例或摘要")
    if not items:
        items.append("外部事实若会变化，需要显式标注信息时点")
    return items


def _professional_prompt(
    original: str,
    normalized: str,
    intent: str,
    mode: str,
    required_output: list[str],
    assumptions: list[str],
) -> str:
    output_lines = "\n".join(f"- {item}" for item in required_output)
    assumption_lines = "\n".join(f"- {item}" for item in assumptions)
    mode_instruction = MODE_SYSTEM_INSTRUCTIONS.get(mode, "")
    return (
        "[SYSTEM] 作为 AI Judge 独立专家席位，你重视清晰、证据和可执行性。"
        "请先给出明确立场，再说明依据、风险和下一步；不要回避，不要只写空泛结论。\n\n"
        + (f"[MODE_INSTRUCTION] {mode_instruction}\n\n" if mode_instruction else "") +
        "[QUESTION] [AIJUDGE_PRE_RUN_CONFIRMATION]\n"
        "你将作为 AI Judge 全席位中的独立专家，不要互相迎合，也不要只给一个省略式结论。"
        "目标是输出可审计、可比较、可落地的方案。\n\n"
        "用户原始任务：\n"
        f"{original}\n\n"
        "规范化任务：\n"
        f"{normalized}\n\n"
        "任务意图：\n"
        f"{intent}\n\n"
        "裁决模式：\n"
        f"{MODE_LABELS.get(mode, mode)}\n\n"
        "输出必须包含：\n"
        f"{output_lines}\n\n"
        "专业报告要求：\n"
        "- 标题必须与用户任务对齐，不能把流程状态误写成业务标题\n"
        "- 先给可阅读的结论和方案，再把证据、模型贡献、互评和原始日志放入附录\n"
        "- 若存在多个可行方向，必须分别说明适用场景、优点、缺点、风险和实施成本\n"
        "- 不要省略有效模型给出的具体路径；提炼噪音，但保留可追溯来源\n\n"
        "需要主动核查或声明的假设：\n"
        f"{assumption_lines}\n\n"
        "约束：不要把所有内容塞进一个杂乱页面；不要把不可验证内容说成事实；"
        "事实、推断、建议要分开写，最终输出要能被产品经理直接审阅和选择。"
    )


def _stable_id(*parts: str) -> str:
    raw = "::".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]
