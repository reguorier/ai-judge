#!/usr/bin/env python3
"""Domain-aware seat routing — assign questions to best-suited models.

Instead of asking all 13 models the same question, route domain-specific
sub-questions to the seats that are strongest in that domain.

Deploy to: /Users/audimacmini/Documents/ai-judge-skill/core/domain_seat_router.py
"""

from __future__ import annotations

import re
from typing import Any


# --- Domain strength mapping (based on empirical TRIAD-MAX-01 results) ---
DOMAIN_SEATS = {
    "finance": {
        "primary": ["chatgpt", "deepseek", "gemini"],
        "secondary": ["qwen", "zhipu"],
        "rationale": "ChatGPT/DeepSeek 擅长数值分析和 SQL，Gemini 风险识别强",
    },
    "legal": {
        "primary": ["qwen", "yuanbao", "zhipu"],
        "secondary": ["chatgpt", "wenxin"],
        "rationale": "Qwen/Yuanbao 中文法律理解好，Zhipu 工程视角独特",
    },
    "medical": {
        "primary": ["gemini", "chatgpt", "qwen"],
        "secondary": ["deepseek", "mimo"],
        "rationale": "Gemini 医学知识全面，ChatGPT 临床数据分析强",
    },
    "data_engineering": {
        "primary": ["deepseek", "chatgpt", "qwen"],
        "secondary": ["zhipu", "gemini"],
        "rationale": "DeepSeek SQL/统计最强，ChatGPT 数据管道经验丰富",
    },
    "cross_domain": {
        "primary": ["yuanbao", "chatgpt", "deepseek"],
        "secondary": ["gemini", "qwen", "zhipu"],
        "rationale": "跨域问题需要综合能力强的模型",
    },
}

# --- Domain detection keywords ---
DOMAIN_KEYWORDS = {
    "finance": [
        "贷款", "信用", "欺诈", "反洗钱", "AML", "FICO", "违约", "利率",
        "交易", "金额", "VaR", "CVaR", "市场风险", "信贷", "审批",
        "finance", "credit", "fraud", "loan", "transaction", "risk",
    ],
    "legal": [
        "法律", "合同", "诉讼", "案件", "律师", "法官", "判决", "和解",
        "privilege", "litigation", "contract", "settlement", "verdict",
        "法规", "合规", "仲裁", "侵权", "知识产权",
    ],
    "medical": [
        "医疗", "患者", "诊断", "药物", "临床", "实验室", "检验",
        "脓毒症", "再入院", "死亡率", "处方", "手术",
        "medical", "patient", "diagnosis", "clinical", "lab", "medication",
        "sepsis", "readmission", "mortality",
    ],
    "data_engineering": [
        "SQL", "数据质量", "ETL", "管道", "数据泄漏", "异常检测",
        "重复", "缺失", "清洗", "特征工程", "建模",
        "data quality", "pipeline", "leakage", "anomaly", "feature",
    ],
}


def detect_domains(question: str) -> list[str]:
    """Detect which domains a question covers.

    Returns list of domain names, sorted by relevance.
    """
    lowered = question.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in lowered)
        if count > 0:
            scores[domain] = count

    if not scores:
        return ["cross_domain"]

    # If multiple domains detected with similar scores, it's cross-domain
    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_domains) >= 3 and sorted_domains[2][1] >= sorted_domains[0][1] * 0.5:
        return ["cross_domain"]

    return [d for d, _ in sorted_domains[:2]]


def route_seats(
    question: str,
    all_seats: list[str],
    mode: str = "strategic",
) -> dict[str, Any]:
    """Route seats for a question based on domain detection.

    Returns:
        {
            "domains": [...],
            "primary_seats": [...],  # Must-answer seats for this domain
            "secondary_seats": [...],  # Nice-to-have seats
            "full_seats": [...],  # All seats to actually run
            "routing_rationale": "...",
        }
    """
    domains = detect_domains(question)

    if mode == "flash":
        # Flash mode: use 3 primary seats from first domain
        primary = DOMAIN_SEATS.get(domains[0], {}).get("primary", all_seats[:3])[:3]
        return {
            "domains": domains,
            "primary_seats": primary,
            "secondary_seats": [],
            "full_seats": primary,
            "routing_rationale": f"快速模式：{domains[0]} 域的 3 个主力席位",
        }

    if mode == "standard":
        # Standard mode: primary + secondary from detected domains
        primary = []
        secondary = []
        for domain in domains:
            config = DOMAIN_SEATS.get(domain, {})
            primary.extend(config.get("primary", []))
            secondary.extend(config.get("secondary", []))

        primary = list(dict.fromkeys(primary))  # deduplicate, preserve order
        secondary = [s for s in dict.fromkeys(secondary) if s not in primary]
        full = primary + secondary[:3]
        # Ensure all seats are in all_seats
        full = [s for s in full if s in all_seats]

        return {
            "domains": domains,
            "primary_seats": primary,
            "secondary_seats": secondary,
            "full_seats": full or all_seats[:5],
            "routing_rationale": f"标准模式：{'+'.join(domains)} 域的 {len(full)} 个席位",
        }

    # Strategic mode: all seats, but mark primary/secondary for priority
    primary = []
    secondary = []
    for domain in domains:
        config = DOMAIN_SEATS.get(domain, {})
        primary.extend(config.get("primary", []))
        secondary.extend(config.get("secondary", []))

    primary = list(dict.fromkeys(primary))
    secondary = [s for s in dict.fromkeys(secondary) if s not in primary]

    return {
        "domains": domains,
        "primary_seats": primary,
        "secondary_seats": secondary,
        "full_seats": all_seats,
        "routing_rationale": f"深度模式：{'+'.join(domains)} 域全席参与，主力席位 {len(primary)} 个",
    }


def get_domain_badge(seat: str, domains: list[str]) -> str | None:
    """Get domain badge for a seat (e.g., '金融主力', '医疗辅助')."""
    for domain in domains:
        config = DOMAIN_SEATS.get(domain, {})
        if seat in config.get("primary", []):
            domain_cn = {
                "finance": "金融", "legal": "法律", "medical": "医疗",
                "data_engineering": "数据", "cross_domain": "跨域",
            }.get(domain, domain)
            return f"{domain_cn}主力"
        if seat in config.get("secondary", []):
            domain_cn = {
                "finance": "金融", "legal": "法律", "medical": "医疗",
                "data_engineering": "数据", "cross_domain": "跨域",
            }.get(domain, domain)
            return f"{domain_cn}辅助"
    return None
