#!/usr/bin/env python3
"""Domain packs for AI Judge intake, seat routing, and public report shape."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DOMAIN_PACK_SCHEMA = "ai_judge.domain_pack.v1"


@dataclass(frozen=True)
class DomainPack:
    domain_id: str
    label: str
    risk_level: str
    report_kind: str
    output_sections: list[str]
    evidence_requirements: list[str]
    recommended_round2_policy: str
    recommended_seat_tags: list[str]
    judge_prompt_addendum: str
    disclaimer: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = DOMAIN_PACK_SCHEMA
        return data


FINANCE_MARKET_PACK = DomainPack(
    domain_id="finance_market_timing",
    label="金融市场/指数择时与杠杆风险",
    risk_level="high",
    report_kind="financial_risk_opinion",
    output_sections=[
        "cover",
        "one_line_verdict",
        "market_snapshot",
        "judge_reframed_question",
        "scenario_matrix",
        "leverage_risk",
        "catalyst_calendar",
        "decision_framework",
        "risk_matrix",
        "evidence_checklist",
        "next_actions",
        "limited_audit_appendix",
    ],
    evidence_requirements=[
        "当前纳斯达克综合指数或相关 ETF 的价格、估值、趋势与波动率信息。",
        "未来 30 天关键事件：FOMC、CPI/PCE、就业、财报、地缘政治和流动性变量。",
        "贷款成本、期限、强平/追加保证金机制、最大可承受回撤。",
        "至少给出牛市、震荡、回撤三种情景，不得把方向性预测写成确定事实。",
    ],
    recommended_round2_policy="all_valid_first_round",
    recommended_seat_tags=["real_time_web", "deep_reasoning", "dissent", "execution"],
    judge_prompt_addendum=(
        "这是高风险金融议题。必须区分事实、市场数据、假设、情景推演和行动建议。"
        "不得输出确定收益承诺，不得把贷款抄底包装成无风险策略。"
        "必须讨论借款成本、回撤承受、时间窗口、止损、仓位和替代方案。"
    ),
    disclaimer="非个性化投资建议；任何杠杆/贷款投资均需结合个人财务状况并独立决策。",
)


LEGAL_PACK = DomainPack(
    domain_id="legal",
    label="法律争议/诉讼方案",
    risk_level="high",
    report_kind="legal_opinion",
    output_sections=["facts", "issues", "law", "claims", "evidence", "strategy", "risks", "next_actions"],
    evidence_requirements=["具体事实证据", "法条/司法解释", "案例或裁判倾向", "诉讼请求与管辖信息"],
    recommended_round2_policy="all_valid_first_round",
    recommended_seat_tags=["long_context", "chinese_context", "deep_reasoning", "dissent"],
    judge_prompt_addendum="法律议题必须区分事实、法律依据、裁判倾向、诉讼策略和待验证假设。",
    disclaimer="仅供法律研究与方案评估，正式使用前应由执业律师复核。",
)


MEDICAL_PACK = DomainPack(
    domain_id="medical",
    label="医疗健康/风险分级",
    risk_level="critical",
    report_kind="medical_risk_triage",
    output_sections=["symptoms", "red_flags", "evidence", "differential", "questions", "next_actions"],
    evidence_requirements=["症状时间线", "既往病史/用药", "检查结果", "红旗症状"],
    recommended_round2_policy="all_valid_first_round",
    recommended_seat_tags=["deep_reasoning", "dissent", "real_time_web"],
    judge_prompt_addendum="医疗议题必须给出风险分级和就医边界，不得替代医生诊断。",
    disclaimer="非医疗诊断；出现红旗症状应及时就医。",
)


PRODUCT_TECH_PACK = DomainPack(
    domain_id="product_tech",
    label="产品/技术/工程方案",
    risk_level="medium",
    report_kind="implementation_plan",
    output_sections=["goal", "architecture", "workflow", "risks", "tests", "next_actions"],
    evidence_requirements=["现有代码/流程", "用户路径", "约束条件", "验收标准"],
    recommended_round2_policy="priority_blocking_with_late_evidence_queue",
    recommended_seat_tags=["execution", "product_experience", "deep_reasoning", "long_context"],
    judge_prompt_addendum="产品技术议题必须给出架构、数据流、验收标准和风险回滚。",
)


GENERAL_PACK = DomainPack(
    domain_id="general",
    label="综合裁决",
    risk_level="medium",
    report_kind="general_verdict",
    output_sections=["key_conclusions", "options", "risks", "next_actions"],
    evidence_requirements=["事实边界", "关键假设", "可验证依据"],
    recommended_round2_policy="priority_blocking_with_late_evidence_queue",
    recommended_seat_tags=["deep_reasoning", "dissent", "execution"],
    judge_prompt_addendum="综合议题必须区分事实、推断、建议和假设。",
)


def infer_domain_pack(question: str) -> DomainPack:
    text = str(question or "").lower()
    if any(token in text for token in ("纳斯达克", "nasdaq", "指数", "贷款", "抄底", "股票", "etf", "qqq", "tqqq", "投资", "赚钱")):
        return FINANCE_MARKET_PACK
    if any(token in text for token in ("法院", "诉讼", "案由", "法条", "合同", "债权", "破产", "律师", "法律")):
        return LEGAL_PACK
    if any(token in text for token in ("症状", "用药", "检查", "诊断", "医院", "医生", "治疗", "medical", "clinical")):
        return MEDICAL_PACK
    if any(token in text for token in ("代码", "客户端", "架构", "产品", "接口", "api", "系统", "流程", "开发")):
        return PRODUCT_TECH_PACK
    return GENERAL_PACK


def build_intake_plan(
    *,
    question: str,
    seats: list[str] | None = None,
    bridge_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = infer_domain_pack(question)
    seats = [str(seat).lower() for seat in (seats or []) if str(seat or "").strip()]
    return {
        "schema": "ai_judge.judge_intake_plan.v1",
        "domain_pack": pack.to_dict(),
        "reframed_question": _reframe_question(question, pack),
        "judge_checks": _judge_checks(pack),
        "expansion_questions": _expansion_questions(pack),
        "recommended_round2_policy": pack.recommended_round2_policy,
        "recommended_seat_tags": pack.recommended_seat_tags,
        "requested_seats": seats,
        "ready_count": int((bridge_summary or {}).get("ready_count") or 0),
        "disclaimer": pack.disclaimer,
    }


def _reframe_question(question: str, pack: DomainPack) -> str:
    if pack.domain_id == "finance_market_timing":
        return (
            "在不承诺收益的前提下，基于当前市场数据、未来 30 天宏观/财报/流动性事件、"
            "贷款成本与最大回撤承受，评估是否应借款买入纳斯达克综合指数或相关 ETF，"
            "并给出情景矩阵、仓位/止损/替代方案和禁止动作。原始问题："
            f"{question}"
        )
    return f"请围绕「{question}」输出可验证事实、关键假设、风险边界和可执行方案。"


def _judge_checks(pack: DomainPack) -> list[str]:
    checks = [
        "事实与假设必须分层。",
        "缺失证据必须进入证据清单，不得补写成事实。",
        "最终建议必须给出触发条件和反例。",
    ]
    if pack.domain_id == "finance_market_timing":
        checks.extend([
            "任何方向性走势都是概率情景，不得写成确定收益。",
            "贷款抄底必须显式计算借款成本、最大回撤、强平和现金流压力。",
            "必须给出不做/少做/替代方案。",
        ])
    return checks


def _expansion_questions(pack: DomainPack) -> list[str]:
    if pack.domain_id == "finance_market_timing":
        return [
            "未来 30 天最可能改变纳指方向的 3-5 个催化因素是什么？",
            "如果指数先跌 5%-10%，贷款人是否还有现金流与心理承受能力？",
            "买指数、分批买、买短债/货币基金、等待事件落地，哪种风险收益更好？",
            "哪些条件出现时必须放弃抄底假设？",
        ]
    return [
        "这个问题背后真正要裁决的对象是什么？",
        "哪些事实需要先验证？",
        "哪些假设一旦变化会推翻结论？",
    ]
