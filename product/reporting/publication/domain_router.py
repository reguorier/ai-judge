"""Route AI Judge questions to publication report domains."""

from __future__ import annotations

from typing import Any


SUPPORTED_DOMAINS = {
    "auto",
    "general_decision",
    "legal_memo",
    "prediction_pool",
    "business_strategy",
    "finance_risk",
    "ops_check",
}

DOMAIN_LABELS = {
    "general_decision": "通用决策",
    "legal_memo": "法律分析",
    "prediction_pool": "预测池",
    "business_strategy": "商业/产品策略",
    "finance_risk": "金融/资金风险",
    "ops_check": "工程/运维验收",
}


def detect_domain(
    question: str,
    report: dict[str, Any] | None = None,
    *,
    domain_hint: str | None = "auto",
) -> str:
    hint = (domain_hint or "auto").strip()
    if hint in SUPPORTED_DOMAINS and hint != "auto":
        return hint

    report = report if isinstance(report, dict) else {}
    mode = str(report.get("mode") or "").lower()
    title = str(report.get("title") or "")
    body = str(report.get("body_text") or report.get("core_conclusion") or "")
    text = f"{question}\n{title}\n{body}".lower()

    if mode == "prediction_pool":
        return "prediction_pool"

    legal_tokens = (
        "法律",
        "法院",
        "诉讼",
        "执行",
        "股权",
        "债务",
        "赔偿",
        "合同",
        "法条",
        "司法解释",
        "律师",
        "债权",
    )
    if any(token.lower() in text for token in legal_tokens):
        return "legal_memo"

    prediction_tokens = (
        "世界杯",
        "预测池",
        "下注",
        "投注",
        "赔率",
        "盘口",
        "gp",
        "roi",
        "观望",
        "贷款",
        "forecast",
        "investment",
        "odds",
    )
    if any(token in text for token in prediction_tokens):
        return "prediction_pool"

    ops_tokens = (
        "验收",
        "烟测",
        "链路",
        "部署",
        "接口",
        "客户端",
        "api",
        "测试",
        "bug",
        "回归",
        "诊断",
    )
    if any(token in text for token in ops_tokens):
        return "ops_check"

    finance_tokens = (
        "投资",
        "市场",
        "股票",
        "基金",
        "融资",
        "贷款",
        "杠杆",
        "利率",
        "现金流",
        "回撤",
    )
    if any(token in text for token in finance_tokens):
        return "finance_risk"

    business_tokens = (
        "商业",
        "产品",
        "运营",
        "增长",
        "用户",
        "定价",
        "获客",
        "销售",
        "策略",
        "路线图",
    )
    if any(token in text for token in business_tokens):
        return "business_strategy"

    return "general_decision"
