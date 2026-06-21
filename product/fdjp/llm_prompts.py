"""FDJP LLM prompt templates for five-dimension semantic audit."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """你是 AI Judge 的 FDJP 五维语义审计器。
你不是重新回答用户问题，而是审查已有 verdict/raw_results 是否完成五类思考。

五类维度：
- philosophy：问题本质、概念边界、判断标准、错误 framing
- economy：利益方、成本、收益、稀缺资源、隐形成本
- politics：权力结构、规则制定者、否决者、话语权、合法性
- military：目标、主攻点、行动顺序、资源配置、风险预案
- history：时间线、先例、周期、历史转向、类比风险

输出必须是 JSON，不要 Markdown。
每个 dimension 必须包含：
- status: pass/warning/blocker/insufficient
- claim
- confidence: 0-1
- evidence_refs
- reasoning_summary
- risk_if_wrong
- action_impact
- blocker_id 或 warning_id，可为空

如果材料不足，写 insufficient，不要编造。"""


def build_audit_prompt(
    question: str,
    verdict_summary: str,
    seat_outputs: list[dict[str, Any]],
    task_type: str = "general",
) -> str:
    """Build the full FDJP audit prompt for the LLM.

    Args:
        question: The original user question.
        verdict_summary: Summary text from the verdict/conclusion.
        seat_outputs: List of seat output dicts with seat_id / output fields.
        task_type: Task category for context.

    Returns:
        Full prompt string to send to the LLM.
    """
    parts: list[str] = [SYSTEM_PROMPT, ""]

    parts.append("## 任务类型")
    parts.append(f"{task_type}")
    parts.append("")

    parts.append("## 用户问题")
    parts.append(question.strip() or "(no question)")
    parts.append("")

    parts.append("## 裁决摘要")
    parts.append(verdict_summary.strip() or "(no summary)")
    parts.append("")

    if seat_outputs:
        parts.append("## 席位观点")
        for i, seat in enumerate(seat_outputs[:10], 1):
            seat_id = seat.get("seat_id", seat.get("seat", f"seat_{i}"))
            output = seat.get("output", seat.get("text", ""))
            if output:
                output_short = output[:2000]  # truncate very long outputs
                parts.append(f"### {seat_id}")
                parts.append(output_short)
                parts.append("")

    parts.append("## 审计要求")
    parts.append(
        "请审查上述裁决是否完成了五维语义审计。"
        "对每个 dimension 输出 status（pass/warning/blocker/insufficient）、"
        "claim、confidence、evidence_refs、reasoning_summary、"
        "risk_if_wrong、action_impact。"
        "如果某维度信息不足，status 填 insufficient，不要编造。"
    )
    parts.append("")
    parts.append("只输出 JSON，不要包含 Markdown 代码块标记。")

    return "\n".join(parts)