"""Lightweight search agent for legal-domain web search via Bing.

Provides substantive search results to feed into deep_judge_runner
without requiring LLM API keys or heavy model dependencies.
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

# ── legal keyword set for snippet relevance filtering ──
_LEGAL_KEYWORDS = {
    "法", "补", "偿", "征", "收", "拆", "迁", "宅", "基", "地",
    "农", "村", "集", "体", "安", "置", "院", "判", "例", "条",
    "款", "规", "定", "破", "产", "债", "权", "清", "偿", "律",
    "师", "诉", "讼", "裁", "决", "执", "行", "合同", "责任",
    "权", "利", "义", "务", "民", "法", "刑", "政", "行",
}

# ── topic-specific query templates ──
_TOPIC_TEMPLATES: dict[str, list[str]] = {
    "bankruptcy": [
        "破产债权 法律规定 中国",
        "企业破产法 清偿顺序 债权人保护",
    ],
    "demolition": [
        "征收补偿 地上附着物 青苗费 安置补助费",
        "土地管理法 宅基地 征收 补偿标准",
        "农村房屋拆迁 补偿 法律 规定",
    ],
}

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "bankruptcy": ["破产", "债权", "清偿", "企业破产", "债务", "重整", "清算"],
    "demolition": ["宅基地", "拆迁", "征收", "补偿", "安置", "房屋征收", "土地征收", "地上附着物", "青苗", "安置补助"],
}

_REQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_BING_URL = "https://www.bing.com/search"


def _detect_topics(question: str) -> list[str]:
    """Detect which legal topics the question relates to."""
    topics: list[str] = []
    q = question
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            topics.append(topic)
    if not topics:
        topics.append("general")
    return topics


def _search_bing(query: str, timeout: int = 12) -> list[str]:
    """Search Bing and return filtered legal snippets."""
    try:
        r = requests.get(
            _BING_URL,
            params={"q": query, "setlang": "zh-Hans"},
            headers=_REQ_HEADERS,
            timeout=timeout,
        )
    except Exception:
        return []

    if r.status_code != 200:
        return []

    snippets_raw = re.findall(
        r'class="b_caption"[^>]*>.*?<p[^>]*>(.*?)</p>',
        r.text,
        re.DOTALL,
    )

    legal: list[str] = []
    for s in snippets_raw:
        clean = re.sub(r"<[^>]+>", "", s).strip()
        clean = re.sub(r"&[a-z]+;", "", clean)
        clean = re.sub(r"&#\d+;", "", clean)
        cn_chars = re.findall(r"[\u4e00-\u9fff]", clean)
        if len(cn_chars) < 20:
            continue
        kw_hits = sum(1 for kw in _LEGAL_KEYWORDS if kw in clean)
        if kw_hits >= 2:
            legal.append(clean)
    return legal


def search_legal(question: str) -> dict[str, Any]:
    """Search for legal information related to the question.

    Returns a dict suitable as search_agent_output for deep_judge_runner.
    """
    topics = _detect_topics(question)
    all_snippets: list[str] = []

    for topic in topics:
        templates = _TOPIC_TEMPLATES.get(topic, [question])
        for tmpl in templates:
            snippets = _search_bing(tmpl)
            all_snippets.extend(snippets)
            time.sleep(0.3)

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for s in all_snippets:
        key = s[:80]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    if not unique:
        # Fallback: search with raw question
        fallback = _search_bing(question)
        if fallback:
            unique = fallback[:15]

    return {
        "result": "\n\n".join(unique[:10]),
        "sources": [],
        "query": question,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "snippet_count": len(unique),
    }