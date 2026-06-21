#!/usr/bin/env python3
"""Three-round AI Judge protocol.

This module is the deterministic orchestration layer that turns scattered
capabilities into one controllable flow:

0. Judge framing before the seats answer.
1. Independent seat answers with information-difference mandates.
2. Judge information board feeds new perspectives back to seats.
3. Final settlement uses claim scoring, diversity checks, and peach weights.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from core.scoring_v2 import score_jury_full_pipeline
from core.seat_personas import SEAT_PERSONAS


SCHEMA_VERSION = "ai_judge.three_round_protocol.v1"
SCORING_SCHEMA_VERSION = "ai_judge.three_round_scoring.v1"


INFORMATION_LANES: dict[str, dict[str, str]] = {
    "real_time_web": {
        "label": "实时联网信息",
        "mandate": "优先补足最新事实、公开来源、时间敏感变量和可引用链接。",
    },
    "chinese_context": {
        "label": "中文语境与本土资料",
        "mandate": "优先补足中文政策、中文产品生态、司法/监管/产业语境。",
    },
    "long_context": {
        "label": "长上下文整合",
        "mandate": "优先整合长材料、附件、历史对话和多段文本里的隐含关系。",
    },
    "deep_reasoning": {
        "label": "底层机制推理",
        "mandate": "优先拆解机制、约束、因果链和可证伪假设。",
    },
    "dissent": {
        "label": "反共识与失败条件",
        "mandate": "优先寻找反例、失败路径、过度自信和共识幻觉。",
    },
    "execution": {
        "label": "执行路径与资源约束",
        "mandate": "优先给出资源、时机、路径、取舍和行动序列。",
    },
    "product_experience": {
        "label": "产品体验与表达",
        "mandate": "优先识别用户感知、交互成本、传播表达和体验风险。",
    },
}


SEAT_INFORMATION_PROFILES: dict[str, list[str]] = {
    "gemini": ["deep_reasoning", "real_time_web"],
    "chatgpt": ["deep_reasoning", "execution"],
    "deepseek": ["deep_reasoning", "dissent"],
    "qwen": ["chinese_context", "long_context"],
    "kimi": ["long_context", "dissent"],
    "grok": ["dissent", "real_time_web"],
    "yuanbao": ["chinese_context", "execution"],
    "mimo": ["long_context", "product_experience"],
    "doubao": ["execution", "chinese_context"],
    "claude": ["long_context", "deep_reasoning"],
    "minimax": ["product_experience", "execution"],
    "zhipu": ["chinese_context", "deep_reasoning"],
    "wenxin": ["chinese_context", "execution"],
    "xunfei": ["chinese_context", "execution", "deep_reasoning"],
}


FRAME_LOCK = {
    "name": "method_seeking_frame",
    "principle": "模型不得把任务理解为找借口或写观点散文，必须统一到找方法、找证据、找约束、找失败条件。",
    "angle": "角度是框架的外显；处理方式是角度的延伸。",
    "required_shift": [
        "从回答问题转为校验问题背后的框架。",
        "从展示知识转为贡献可验证信息差。",
        "从单模型自洽转为接受二轮互评监督。",
        "从平均投票转为按证据、稀缺信息和历史可信度结算权重。",
    ],
}


def build_three_round_plan(
    *,
    question: str,
    mode: str,
    seats: list[str] | None,
    prompt_flow: dict[str, Any] | None = None,
    bridge_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the judge-side protocol plan used before any seat answers."""
    resolved_seats = [str(seat).lower() for seat in (seats or []) if str(seat).lower() in SEAT_PERSONAS]
    bridge_summary = bridge_summary or {}
    bridge_rows = _bridge_rows_by_seat(bridge_summary)
    seat_mandates = [
        _seat_mandate(seat, bridge_rows.get(seat, {}), question)
        for seat in resolved_seats
    ]
    plan = {
        "schema": SCHEMA_VERSION,
        "version": "three-round-protocol-v1",
        "question_hash": _stable_id(question),
        "mode": mode,
        "rounds": [
            {
                "id": "round0_judge_frame",
                "name": "法官确认 / 框架锁定 / 信息差分配",
                "goal": "在提问前锁定观察角度、输出结构和每个席位的信息增量责任。",
            },
            {
                "id": "round1_independent_answer",
                "name": "第一轮独立作答",
                "goal": "席位独立贡献事实、推断、建议、风险和可验证断言。",
            },
            {
                "id": "round2_information_feedback",
                "name": "第二轮信息反哺与共振互评",
                "goal": "法官整合信息差后反哺给席位，让模型修订、坚持或挑战自己的第一轮发言。",
            },
            {
                "id": "round3_judge_settlement",
                "name": "第三轮法官结算",
                "goal": "用五维约束、证据门禁、共识多样性和二桃权重形成最终裁决。",
            },
        ],
        "frame_lock": FRAME_LOCK,
        "required_assertion_schema": {
            "claim": "可判断的断言",
            "evidence": "证据或来源；没有证据必须标注 unknown",
            "assumption": "成立前提",
            "confidence": "0.0-1.0",
            "risk": "失败条件或反例",
            "verifiable": "如何验证",
            "information_delta": "本席位相对其他席位可能新增的信息差",
        },
        "information_lanes": INFORMATION_LANES,
        "seat_mandates": seat_mandates,
        "prompt_trace": {
            "prompt_flow_version": (prompt_flow or {}).get("version"),
            "prompt_trace_id": (prompt_flow or {}).get("trace_id"),
            "intent": (prompt_flow or {}).get("intent"),
        },
    }
    plan["protocol_hash"] = _stable_id(plan)
    return plan


def protocol_prompt_addendum(plan: dict[str, Any]) -> str:
    """Render a compact prompt addendum for all first-round seats."""
    mandates = plan.get("seat_mandates") or []
    mandate_lines = []
    for item in mandates:
        lanes = "、".join(item.get("information_lanes") or [])
        mandate_lines.append(
            f"- {item.get('seat_name', item.get('seat'))}: {lanes}；{item.get('mandate', '')}"
        )
    mandate_text = "\n".join(mandate_lines[:16]) or "- 本轮席位必须主动贡献可验证信息差。"
    return (
        "[AIJUDGE_THREE_ROUND_PROTOCOL]\n"
        "本轮不是单模型问答，而是三轮可审计裁决。\n"
        "第0轮：法官已锁定任务框架；第1轮：你独立作答；"
        "第2轮：你会收到其他席位信息差后修订；第3轮：法官用五维、证据、共识多样性和二桃权重结算。\n\n"
        "框架锁定：不要找借口，不要只写泛泛观点；统一到找方法、找证据、找约束、找失败条件。\n"
        "输出必须包含结构化断言：claim / evidence / assumption / confidence / risk / verifiable / information_delta。\n"
        "如果你无法验证，请明确 abstain_reason；不要把未知写成事实。\n\n"
        "信息差分工：\n"
        f"{mandate_text}\n\n"
        "五维底层约束：哲学=问题本质与判断逻辑；历史=周期与先例；经济=利益/成本/稀缺；"
        "政治=权力/规则/话语权；军事=资源有限下的执行、时机、主动权。\n"
        "每个结论至少说明它被哪一维约束支持或挑战。"
    )


def inject_three_round_protocol(base_prompt: str, plan: dict[str, Any]) -> str:
    """Append the protocol addendum once."""
    marker = "[AIJUDGE_THREE_ROUND_PROTOCOL]"
    if marker in base_prompt:
        return base_prompt
    return base_prompt.rstrip() + "\n\n" + protocol_prompt_addendum(plan)


def build_information_board(
    *,
    question: str,
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the judge information board used for round-2 feedback."""
    deliberation = deliberation or {}
    rows = []
    all_terms: dict[str, int] = {}
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if not item.get("ok") or seat not in SEAT_PERSONAS:
            continue
        response = str(item.get("response") or "")
        terms = _terms(response)
        for term in terms:
            all_terms[term] = all_terms.get(term, 0) + 1
        rows.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or SEAT_PERSONAS[seat]["name"],
            "stance": _stance_label(response),
            "evidence_count": _evidence_count(response),
            "information_delta": _information_delta(response, question),
            "frame_markers": _frame_markers(response),
            "summary": _compact(response, 260),
            "terms": terms[:12],
        })

    rare_terms = [
        term for term, count in sorted(all_terms.items(), key=lambda pair: (pair[1], pair[0]))
        if count == 1
    ][:18]
    disagreements = deliberation.get("disagreements") or _stance_disagreements(rows)
    board = {
        "schema": "ai_judge.information_board.v1",
        "question_hash": _stable_id(question),
        "seat_count": len(rows),
        "rare_terms": rare_terms,
        "seat_information": [
            {k: v for k, v in row.items() if k != "terms"}
            for row in rows
        ],
        "disagreements": disagreements,
        "judge_feedback": _judge_feedback(rows, rare_terms, plan),
    }
    board["board_hash"] = _stable_id(board)
    return board


def build_round2_revision_prompts(
    *,
    question: str,
    mode: str,
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build per-seat second-round prompts with judge information feedback."""
    board = build_information_board(question=question, raw_results=raw_results, deliberation=deliberation, plan=plan)
    public_rows = board.get("seat_information") or []
    prompts = []
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if not item.get("ok") or seat not in SEAT_PERSONAS:
            continue
        own_preview = _compact(item.get("response"), 420)
        others = [row for row in public_rows if row.get("seat") != seat]
        prompt = (
            "[AIJUDGE_RESONANCE_FOLLOWUP]\n"
            "[AIJUDGE_ROUND2_INFORMATION_FEEDBACK]\n"
            f"模式：{mode}\n"
            f"原始问题：{question}\n\n"
            "你已经完成第一轮独立作答。现在法官把其他席位的信息差、框架差异和潜在缺口反哺给你。\n"
            "请带入用户角色，判断哪些信息会改变用户的真实决策、验收标准和下一步动作。\n"
            "请不要重复第一轮原文。你必须说明：哪些观点需要修订，哪些观点仍坚持，新增了什么证据或失败条件。\n\n"
            f"你的第一轮摘要：{own_preview}\n\n"
            f"全局稀缺信息词：{', '.join(board.get('rare_terms') or []) or '暂无'}\n"
            f"主要分歧：{'; '.join(board.get('disagreements') or []) or '暂无'}\n\n"
            "其他席位信息差：\n"
            + "\n".join(
                f"- {row.get('seat_name')}: 立场={row.get('stance')}；证据数={row.get('evidence_count')}；"
                f"信息差={'; '.join(row.get('information_delta') or []) or row.get('summary')}"
                for row in others[:10]
            )
            + "\n\n"
            "请输出以下结构：\n"
            "1. revised_claims：修订后的关键断言，每条含 evidence/assumption/confidence/risk/verifiable。\n"
            "2. learned_from_others：你吸收了哪些席位的信息差。\n"
            "3. still_disagree：你仍不同意什么，为什么。\n"
            "4. final_delta：第二轮相比第一轮真正新增的判断。"
        )
        prompts.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or SEAT_PERSONAS[seat]["name"],
            "questions": [
                "哪些第一轮判断需要根据新信息修订？",
                "你吸收了其他席位的哪些信息差？",
                "你仍坚持或反对什么，证据是什么？",
            ],
            "source_answer_preview": own_preview,
            "information_board": {
                "board_hash": board.get("board_hash"),
                "rare_terms": board.get("rare_terms"),
                "judge_feedback": board.get("judge_feedback"),
            },
            "prompt": prompt,
        })
    return prompts


def build_scoring_context(
    *,
    question: str,
    mode: str,
    raw_results: list[dict[str, Any]],
    deliberation: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build vectors/performance data so consensus and peach projection can run."""
    deliberation = deliberation or {}
    summaries = {str(row.get("seat")): row for row in deliberation.get("answer_summaries") or []}
    board = build_information_board(question=question, raw_results=raw_results, deliberation=deliberation, plan=plan)
    rare_terms = set(board.get("rare_terms") or [])
    seat_vectors: dict[str, list[float]] = {}
    seat_performance: dict[str, dict[str, float]] = {}
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        if seat not in SEAT_PERSONAS:
            continue
        response = str(item.get("response") or "")
        ok = bool(item.get("ok"))
        summary = summaries.get(seat, {})
        terms = set(_terms(response))
        quality = float(summary.get("quality") or _quality_proxy(response, ok))
        evidence = min(1.0, float(summary.get("evidence_count") or _evidence_count(response)) / 6.0)
        peer = float(summary.get("avg_peer_score") or quality)
        rarity = min(1.0, len(terms.intersection(rare_terms)) / 5.0)
        risk = min(1.0, float(summary.get("risk_count") or _risk_count(response)) / 5.0)
        stance = _stance_numeric(str(summary.get("stance") or _stance_label(response)))
        seat_vectors[seat] = [
            round(quality, 4),
            round(evidence, 4),
            round(peer, 4),
            round(rarity, 4),
            round(risk, 4),
            round(stance, 4),
        ]
        seat_performance[seat] = {
            "correctness": round(max(0.05, min(0.98, 0.34 + quality * 0.34 + evidence * 0.18 + peer * 0.14)), 4),
            "rarity_score": round(rarity, 4),
            "replay_count": 1.0 if ok else 0.0,
            "demand_score": round(0.55 + (0.10 if mode in ("strategic", "deep_judge") else 0.0), 4),
            "calibration_consistency": round(max(0.05, min(0.98, 0.40 + peer * 0.40 + evidence * 0.10)), 4),
        }
    return {
        "schema": "ai_judge.three_round_scoring_context.v1",
        "question_hash": _stable_id(question),
        "mode": mode,
        "seat_vectors": seat_vectors,
        "seat_performance": seat_performance,
        "information_board": board,
    }


def run_three_round_scoring(
    *,
    claims: list[dict[str, Any]],
    scoring_context: dict[str, Any],
) -> dict[str, Any]:
    """Run the full scoring stack and normalize the result for verdicts."""
    seat_vectors = scoring_context.get("seat_vectors") or {}
    seat_performance = scoring_context.get("seat_performance") or {}
    pipeline = score_jury_full_pipeline(
        claims,
        seat_vectors=seat_vectors,
        seat_performance=seat_performance,
    )
    result = {
        "schema": SCORING_SCHEMA_VERSION,
        "pipeline": pipeline,
        "phase1_scoring": pipeline.get("phase1_scoring"),
        "phase2_diversity": pipeline.get("phase2_diversity"),
        "phase3_peach_projection": pipeline.get("phase3_peach_projection"),
        "summary": pipeline.get("summary") or {},
        "information_board": scoring_context.get("information_board") or {},
    }
    result["effective_score_source"] = "phase1_weighted_by_peach" if result.get("phase3_peach_projection") else "phase1_scoring"
    return result


def _seat_mandate(seat: str, bridge_row: dict[str, Any], question: str) -> dict[str, Any]:
    persona = SEAT_PERSONAS.get(seat, {})
    lanes = list(SEAT_INFORMATION_PROFILES.get(seat) or ["deep_reasoning"])
    if bridge_row.get("channel") == "api" and "real_time_web" not in lanes:
        lanes.append("real_time_web")
    lane_labels = [INFORMATION_LANES[lane]["label"] for lane in lanes if lane in INFORMATION_LANES]
    mandates = [INFORMATION_LANES[lane]["mandate"] for lane in lanes if lane in INFORMATION_LANES]
    return {
        "seat": seat,
        "seat_name": persona.get("name", seat),
        "mbti": persona.get("mbti", ""),
        "information_lanes": lane_labels,
        "mandate": " ".join(mandates),
        "frame_correction": persona.get("jury_prompt_injection", ""),
        "bridge_ready": bool(bridge_row.get("ready")),
        "question_focus": _question_focus(question),
    }


def _bridge_rows_by_seat(bridge_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for key in ("seats", "seat_browser_matrix"):
        for row in bridge_summary.get(key) or []:
            if isinstance(row, dict):
                seat = str(row.get("id") or row.get("seat") or "").lower()
                if seat:
                    rows[seat] = row
    return rows


def _question_focus(question: str) -> str:
    if any(token in question for token in ("方案", "落地", "实现", "代码", "流程")):
        return "implementation"
    if any(token in question for token in ("是否", "该不该", "能否", "风险")):
        return "decision"
    if any(token in question for token in ("为什么", "本质", "逻辑", "框架")):
        return "frame"
    return "general"


def _terms(text: Any) -> list[str]:
    raw = str(text or "").lower()
    tokens = re.findall(r"[一-鿿]{2,}|[a-z][a-z0-9_+-]{2,}", raw)
    stop = {"以及", "但是", "如果", "因为", "所以", "这个", "一个", "the", "and", "for", "with", "that", "this"}
    deduped = []
    for token in tokens:
        if token in stop or token in deduped:
            continue
        deduped.append(token)
    return deduped[:80]


def _information_delta(response: str, question: str) -> list[str]:
    text = str(response or "")
    deltas = []
    patterns = [
        (r"(?:https?://\S+)", "包含外部链接或来源"),
        (r"(?:20\d{2}|19\d{2}|今天|昨日|最新|recent|latest)", "包含时间敏感信息"),
        (r"(?:成本|收益|利益|价格|预算|ROI|稀缺)", "补充经济/资源信息"),
        (r"(?:权力|规则|审批|监管|话语权|组织)", "补充权力/规则信息"),
        (r"(?:风险|失败|反例|不确定|边界)", "补充失败条件"),
        (r"(?:历史|案例|先例|周期|演进)", "补充历史参照"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            deltas.append(label)
    question_terms = set(_terms(question))
    novel_terms = [term for term in _terms(text) if term not in question_terms][:5]
    if novel_terms:
        deltas.append("新增关键词：" + "、".join(novel_terms))
    return deltas[:6]


def _frame_markers(response: str) -> list[str]:
    text = str(response or "")
    markers = []
    for label, pattern in (
        ("找方法", r"方法|路径|步骤|执行|落地"),
        ("找证据", r"证据|来源|引用|验证|数据"),
        ("找约束", r"约束|边界|前提|条件|假设"),
        ("找失败条件", r"失败|风险|反例|不可行|不确定"),
    ):
        if re.search(pattern, text, re.IGNORECASE):
            markers.append(label)
    return markers


def _judge_feedback(rows: list[dict[str, Any]], rare_terms: list[str], plan: dict[str, Any] | None) -> list[str]:
    feedback = []
    if rare_terms:
        feedback.append("第二轮必须优先处理稀缺信息，而不是重复多数席位已经说过的共识。")
    low_evidence = [row.get("seat_name") for row in rows if int(row.get("evidence_count") or 0) <= 1]
    if low_evidence:
        feedback.append("低证据席位需要在第二轮补证据或主动降置信度：" + "、".join(map(str, low_evidence[:6])))
    if plan:
        feedback.append("第二轮修订必须回到框架锁定：找方法、找证据、找约束、找失败条件。")
    return feedback


def _quality_proxy(response: str, ok: bool) -> float:
    if not ok:
        return 0.15
    length_score = min(len(response), 1800) / 1800
    evidence = min(_evidence_count(response), 6) / 6
    structure = 1.0 if re.search(r"[\n。；;].*(风险|结论|步骤|证据)", response) else 0.35
    return round(max(0.05, min(0.95, 0.20 + length_score * 0.28 + evidence * 0.30 + structure * 0.17)), 4)


def _evidence_count(text: Any) -> int:
    raw = str(text or "")
    count = 0
    count += len(re.findall(r"https?://", raw))
    count += len(re.findall(r"(?:根据|来源|引用|数据显示|报告|法条|案例|研究)", raw))
    count += len(re.findall(r"(?:20\d{2}|19\d{2})", raw))
    return min(12, count)


def _risk_count(text: Any) -> int:
    return min(10, len(re.findall(r"(?:风险|失败|不确定|反例|代价|限制|边界)", str(text or ""))))


def _stance_label(text: str) -> str:
    raw = str(text or "")
    if re.search(r"不建议|不可行|反对|否定|不能", raw):
        return "反对/否定"
    if re.search(r"建议|可行|应该|支持|可以", raw):
        return "支持/可行"
    if re.search(r"取决于|条件|如果|需要", raw):
        return "条件性"
    return "观察性"


def _stance_numeric(label: str) -> float:
    if "反对" in label or "否定" in label:
        return 0.15
    if "支持" in label or "可行" in label:
        return 0.85
    if "条件" in label:
        return 0.55
    return 0.40


def _stance_disagreements(rows: list[dict[str, Any]]) -> list[str]:
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(str(row.get("stance") or "unknown"), []).append(str(row.get("seat_name") or row.get("seat")))
    if len(groups) <= 1:
        return []
    return [f"{stance}: {', '.join(names)}" for stance, names in groups.items()]


def _compact(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _stable_id(*parts: Any) -> str:
    raw = "::".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]
