#!/usr/bin/env python3
"""Thinking Log v2.0 — Fragment collection, question distillation, parliament.

AI Judge V2 Direction 5 core module. Implements:
  - 3 low-friction input channels (global hotkey, browser right-click, @log in chat)
  - Weekly question distillation (DBSCAN clustering + LLM synthesis)
  - 6-role parliament (Judger, Challenger, Extender, Synthesizer, Archaeologist, Resonator)
  - Over-reflection prevention (production density check, 1-yuan barrier)

Adopted from: Kimi 5-step distillation + Meta 产品设计者 "一个框" + Gemini 考古学家 + DeepSeek 共鸣者
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Thinking Fragment ──

@dataclass
class ThinkingFragment:
    """A single raw thinking fragment — deliberately minimal structure."""
    fragment_id: str
    user_id: str
    content: str  # Raw text, no formatting required
    source: str   # "hotkey" | "browser_clip" | "chat_log" | "voice"
    timestamp: float = field(default_factory=time.time)
    word_count: int = 0
    tags: list[str] = field(default_factory=list)  # Auto-tagged, not user-tagged
    is_private: bool = False  # B-track (private) or A-track (public)
    embedding: Optional[list[float]] = None  # Populated during distillation

    def __post_init__(self):
        self.word_count = len(self.content.split())
        if not self.fragment_id:
            raw = f"{self.user_id}:{self.content}:{self.timestamp}"
            self.fragment_id = hashlib.sha256(raw.encode()).hexdigest()[:12]


# ── Fragment Store ──

class FragmentStore:
    """In-memory fragment store. In production, backed by SQLite."""
    def __init__(self):
        self._fragments: dict[str, list[ThinkingFragment]] = {}

    def add(self, fragment: ThinkingFragment) -> None:
        uid = fragment.user_id
        if uid not in self._fragments:
            self._fragments[uid] = []
        self._fragments[uid].append(fragment)

    def get_recent(self, user_id: str, days: int = 7) -> list[ThinkingFragment]:
        cutoff = time.time() - days * 86400
        frags = self._fragments.get(user_id, [])
        return [f for f in frags if f.timestamp >= cutoff]

    def get_count_today(self, user_id: str) -> int:
        cutoff = time.time() - 86400
        frags = self._fragments.get(user_id, [])
        return sum(1 for f in frags if f.timestamp >= cutoff)

    def get_all(self, user_id: str) -> list[ThinkingFragment]:
        return self._fragments.get(user_id, [])


# ── Daily Limit Check ──

def check_daily_limit(
    fragment_count_today: int,
    *,
    free_limit: int = 5,
    charge_per_extra: float = 1.0,
) -> dict[str, Any]:
    """Check if user has exceeded free daily fragment limit.

    Implements Meta 产品设计者's "1-yuan barrier" — 6th fragment costs 1 yuan.
    This is NOT a revenue mechanism; it's an over-reflection prevention.
    """
    if fragment_count_today <= free_limit:
        return {
            "allowed": True,
            "free_remaining": free_limit - fragment_count_today,
            "cost": 0,
            "message": f"今日还可记录 {free_limit - fragment_count_today} 条免费碎片。",
        }

    extra = fragment_count_today - free_limit
    return {
        "allowed": True,  # Still allowed, just costs
        "free_remaining": 0,
        "cost": extra * charge_per_extra,
        "message": (
            f"今日已超过 {free_limit} 条免费限额。第 {fragment_count_today} 条需 ¥{charge_per_extra}。"
            "这是为了防止过度反思——记录的目的是思考，不是记录本身。"
        ),
    }


# ── Question Distillation ──

@dataclass
class DistilledQuestion:
    """A question that has emerged from fragmented thinking."""
    core_tension: str  # One sentence summary
    evidence_fragment_ids: list[str]
    confidence: float  # How confident the system is this is a real tension
    suggested_inquiry: str  # "要发起议会讨论这个问题吗？"


def distill_questions(
    fragments: list[ThinkingFragment],
    *,
    max_questions: int = 3,
    min_fragments: int = 5,
) -> list[DistilledQuestion]:
    """Distill core questions from accumulated thinking fragments.

    Production flow:
    1. Embed all fragments → DBSCAN clustering
    2. Find high-density clusters
    3. For each cluster, detect internal contradictions
    4. Send to LLM: "These fragments seem to point to one core tension. What is it?"
    5. Return top 3 distilled questions

    This simplified version provides the structural scaffold.
    """
    if len(fragments) < min_fragments:
        return []

    # Group fragments by topic similarity (simplified: by word overlap)
    clusters = _simple_cluster(fragments)

    questions = []
    for cluster in clusters[:max_questions]:
        if len(cluster) < 3:
            continue

        # Extract core tension
        all_text = " ".join(f.content for f in cluster)
        tension = _extract_tension(all_text)

        questions.append(DistilledQuestion(
            core_tension=tension,
            evidence_fragment_ids=[f.fragment_id for f in cluster],
            confidence=min(0.3 + 0.1 * len(cluster), 0.9),
            suggested_inquiry=f"是否要发起一次议会来彻底讨论「{tension}」？",
        ))

    return questions


def _simple_cluster(fragments: list[ThinkingFragment]) -> list[list[ThinkingFragment]]:
    """Simplified clustering by word overlap. Replace with DBSCAN in production."""
    # For now, group by shared significant words
    clusters: list[list[ThinkingFragment]] = []
    assigned: set[str] = set()

    for f in fragments:
        if f.fragment_id in assigned:
            continue
        cluster = [f]
        assigned.add(f.fragment_id)

        f_words = set(f.content.split()) if f.content else set()
        for other in fragments:
            if other.fragment_id in assigned:
                continue
            other_words = set(other.content.split()) if other.content else set()
            overlap = len(f_words & other_words) / max(len(f_words | other_words), 1)
            if overlap > 0.15:
                cluster.append(other)
                assigned.add(other.fragment_id)

        clusters.append(cluster)

    return sorted(clusters, key=len, reverse=True)


def _extract_tension(text: str) -> str:
    """Extract core tension from text. Simplified — LLM does this in production."""
    # Detect contrasting words
    contrasts = []
    if "但是" in text or "然而" in text or "不过" in text:
        contrasts.append("内部矛盾")
    if "?" in text or "不知道" in text or "不确定" in text:
        contrasts.append("未解决的问题")

    if contrasts:
        return f"你似乎在{'和'.join(contrasts)}之间反复"

    words = text.split()
    if len(words) > 50:
        top_word = max(set(words), key=words.count) if words else "思考"
        return f"围绕「{top_word}」的持续思考"

    return "本周的多条碎片似乎指向一个共同的关注点"


# ── Parliament Roles ──

PARLIAMENT_ROLES = {
    "judger": {
        "name": "评审者",
        "responsibility": "按目标锚点严格评分，只给事实，不含感情",
        "system_prompt_draft": (
            "你是一个严格的评审者。你的唯一任务是基于目标锚点对内容进行评分。"
            "输出格式：每个维度一个分数 + 一句话证据引用。不要给建议，不要给鼓励，只给事实。"
        ),
    },
    "challenger": {
        "name": "挑战者",
        "responsibility": "找出三个最可能推翻当前结论的假设或逻辑漏洞",
        "system_prompt_draft": (
            "你是一个挑剔的挑战者。你的任务是攻击当前论证中最薄弱的三个环节。"
            "每个攻击点必须附带具体证据或反例。即使论证整体正确，你也要找到可质疑的部分。"
            "你的价值不在于「正确」，而在于「让思考经得起攻击」。"
        ),
    },
    "extender": {
        "name": "延伸者",
        "responsibility": "提出两个跨领域类比或延伸方向",
        "system_prompt_draft": (
            "你是一个跨领域连接者。你的任务是从当前论证出发，提出两个来自完全不同领域"
            "的类比或延伸方向。这些连接应该让人有'我怎么没想到'的感觉。"
            "不要评价当前论证的好坏，只做连接。"
        ),
    },
    "synthesizer": {
        "name": "综合者",
        "responsibility": "整合所有角色意见，生成最终议会报告",
        "system_prompt_draft": (
            "你是一个综合者。你的任务是将评审者、挑战者、延伸者、溯源者、共鸣者的所有意见"
            "整合为一份决策建议。你需要：1）标注哪些点达成了共识；2）标注哪些点存在分歧；"
            "3）给出一个综合判断和置信度。你不是在给出自己的观点，而是在整合所有人的观点。"
        ),
    },
    "archaeologist": {
        "name": "溯源者",
        "responsibility": "指出用户「没说出口的」——被忽视的利益相关方、隐性假设、缺失的对立面",
        "system_prompt_draft": (
            "你是一个溯源的考古学家。你的任务不是评估用户的现有逻辑，而是寻找缺失的拼图。"
            "分析用户的论述，找出他们视为理所当然的隐性假设（Implicit Assumptions），"
            "或者他们完全忽略的利益相关方和对立面。"
            "你的第一句话总是：'在这个问题中，你没有提到的是……'"
        ),
    },
    "resonator": {
        "name": "共鸣者",
        "responsibility": "不评判、不挑战，只帮用户把散落的想法整理成他「真正想说的是什么」",
        "system_prompt_draft": (
            "你是一个共鸣者。你不评判对错，不挑战漏洞，不延伸方向。"
            "你的唯一任务是：把用户散落的、不成熟的、碎片化的想法，整理成一段连贯的表达——"
            "不是你要说的话，而是你认为用户'真正想说的是什么'。"
            "你的输出应该让用户感觉：'对，这就是我想说的，只是我没表达得这么清楚。'"
            "如果用户的思考中有矛盾和张力，不要尝试解决——矛盾本身就是最有价值的信号。"
        ),
    },
}


def get_parliament_prompt(role: str, content: str, anchor_name: str = "") -> str:
    """Generate the full prompt for a parliament role."""
    role_config = PARLIAMENT_ROLES.get(role)
    if not role_config:
        return f"Unknown role: {role}"

    system = role_config["system_prompt_draft"]
    anchor_context = f"\n\n当前评审锚点：{anchor_name}" if anchor_name else ""

    return f"""{system}{anchor_context}

## 待评审内容
{content}

请以上述角色身份，用中文输出你的分析。"""


# ── Over-Reflection Prevention ──

def check_over_reflection(
    *,
    reflection_time_minutes: float,
    productive_time_minutes: float,
    daily_fragment_count: int,
) -> dict[str, Any]:
    """Check if user is over-reflecting (spending more time on reflection than production).

    Rules:
      - Ratio > 3: Warning
      - Ratio > 5: 24-hour lock
      - Daily fragments > 5: Charge 1 yuan per extra
    """
    ratio = reflection_time_minutes / max(productive_time_minutes, 1)

    result = {
        "ratio": round(ratio, 2),
        "status": "normal",
        "action": "none",
        "message": "",
    }

    if ratio > 5:
        result["status"] = "locked"
        result["action"] = "lock_24h"
        result["message"] = (
            f"反思时间超过生产时间的 {ratio:.0f} 倍。"
            "反思功能已锁定 24 小时。建议：先做一个决定，再看反馈。"
        )
    elif ratio > 3:
        result["status"] = "warning"
        result["action"] = "warn"
        result["message"] = (
            f"反思时间超过生产时间的 {ratio:.0f} 倍。"
            "反思有帮助，但过度反思可能替代真正的行动。"
        )

    if daily_fragment_count > 5:
        result["over_fragment"] = True
        cost = daily_fragment_count - 5
        result["fragment_cost"] = cost

    return result
