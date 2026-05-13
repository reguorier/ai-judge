#!/usr/bin/env python3
"""Cold Start v2.0 — Progressive scaffolding for new users.

AI Judge V2 cold start module. Implements:
  - 3-stage progressive profile (observation → prototype → confirmation)
  - "破壁三问" micro-interactions for bootstrapping
  - Behavior-description-first (no identity labels until confirmed)
  - Fingerprint v0 with explicit confidence = 0.3

Adopted from: 综合各模型共识 — 脚手架≠模板，观察期≠空白期
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ColdStartStage(Enum):
    OBSERVING = "observing"       # Sessions 1-3: record only, no inference
    PROTOTYPING = "prototyping"   # Sessions 4-10: behavior descriptions, user confirms
    CONFIRMING = "confirming"     # Sessions 11+: full fingerprint unlock


@dataclass
class ScaffoldProfile:
    """Progressive user profile that starts as scaffold and becomes real."""
    user_id: str
    stage: ColdStartStage = ColdStartStage.OBSERVING
    session_count: int = 0
    total_chars: int = 0

    # Scaffold data (low confidence, explicitly marked as unverified)
    behavior_observations: list[dict[str, Any]] = field(default_factory=list)
    confirmed_observations: list[str] = field(default_factory=list)
    rejected_observations: list[str] = field(default_factory=list)

    # Bootstrap answers (破壁三问)
    bootstrap_answers: dict[str, str] = field(default_factory=dict)

    # When does the scaffold graduate?
    graduation_session: int = 11
    graduation_chars: int = 5000

    data_confidence: float = 0.0
    fingerprint_version: str = "v0-unverified"

    created_at: float = field(default_factory=time.time)


# ── 破壁三问 (Wall-Breaking Three Questions) ──

BOOTSTRAP_QUESTIONS = [
    {
        "id": "envy",
        "question": "以下两种能力，你更嫉妒哪一种？",
        "options": [
            {"label": "极致理性的数据拆解", "archetype_hint": "system_builder"},
            {"label": "极具画面感的感性叙事", "archetype_hint": "storyteller"},
            {"label": "一眼看穿问题本质的直觉", "archetype_hint": "skeptic"},
            {"label": "把完全无关的东西连在一起的能力", "archetype_hint": "connector"},
        ],
        "rationale": "嫉妒比喜欢更暴露深层需求。",
    },
    {
        "id": "aversion",
        "question": "以下思维习惯，哪一个让你最无法忍受？",
        "options": [
            {"label": "没有数据就下结论", "blind_spot_hint": "over_claims_without_evidence"},
            {"label": "想太多但永远不行动", "blind_spot_hint": "analysis_paralysis"},
            {"label": "总是跑题，抓不住重点", "blind_spot_hint": "tangential"},
            {"label": "重复别人的观点没有自己的", "blind_spot_hint": "echo_chamber"},
        ],
        "rationale": "厌恶锚定底线——你最不想成为的样子。",
    },
    {
        "id": "hypothesis",
        "question": "对于「AI 会取代人类思考吗」这个问题，你的第一反应是什么？（写一句话就好）",
        "open_ended": True,
        "rationale": "你对一个开放问题的第一反应，比任何问卷都更暴露真实思维模式。",
    },
]

# Generic archetypes for prototyping stage
ARCHETYPES = {
    "system_builder": {
        "name": "系统构建者",
        "description": "偏好框架、分类、边界条件，常从定义问题开始",
        "behavioral_markers": ["先列框架", "重视边界", "追求完整性"],
    },
    "skeptic": {
        "name": "质疑者",
        "description": "偏好攻击前提、寻找反例、压力测试现有方案",
        "behavioral_markers": ["先找反例", "质疑假设", "追问证据"],
    },
    "connector": {
        "name": "连接者",
        "description": "偏好跨领域类比、隐喻、将A领域概念迁移到B领域",
        "behavioral_markers": ["跨领域引用", "用类比解释", "擅长隐喻"],
    },
    "storyteller": {
        "name": "叙事者",
        "description": "偏好用故事、场景、用户旅程来承载论证",
        "behavioral_markers": ["场景化思考", "用故事论证", "关注用户体验"],
    },
    "quantifier": {
        "name": "量化者",
        "description": "偏好数据、指标、可测量结果，对模糊表述敏感",
        "behavioral_markers": ["需要数字", "厌恶模糊", "追求量化"],
    },
    "cautious": {
        "name": "审慎者",
        "description": "偏好小步验证、风险控制、先局部试点再推广",
        "behavioral_markers": ["风险意识强", "渐进式推进", "先验证再推广"],
    },
}


def process_bootstrap_answers(answers: dict[str, str]) -> dict[str, Any]:
    """Process bootstrap answers and generate initial archetype hints.

    This does NOT assign the user a label. It generates hints for the
    prototyping stage, all marked as unverified.
    """
    hints = {
        "matched_archetypes": [],
        "alert_blind_spot": None,
        "open_response_saved": False,
    }

    # Q1: Envy → archetype hint
    for q in BOOTSTRAP_QUESTIONS:
        if q["id"] == "envy" and "envy" in answers:
            for opt in q["options"]:
                if opt["label"] == answers["envy"]:
                    hints["matched_archetypes"].append({
                        "archetype": opt["archetype_hint"],
                        "confidence": 0.3,
                        "source": "bootstrap_envy_question",
                    })

    # Q2: Aversion → blind spot hint
    for q in BOOTSTRAP_QUESTIONS:
        if q["id"] == "aversion" and "aversion" in answers:
            for opt in q["options"]:
                if opt["label"] == answers["aversion"]:
                    hints["alert_blind_spot"] = opt["blind_spot_hint"]

    # Q3: Hypothesis → saved for later analysis
    if "hypothesis" in answers:
        hints["open_response_saved"] = True

    return hints


# ── Stage Transition Logic ──

def determine_stage(profile: ScaffoldProfile) -> ColdStartStage:
    """Determine current cold start stage based on session count and data volume."""
    if profile.session_count >= profile.graduation_session:
        return ColdStartStage.CONFIRMING
    elif (
        profile.session_count >= 4
        or profile.total_chars >= 2000
    ):
        return ColdStartStage.PROTOTYPING
    else:
        return ColdStartStage.OBSERVING


def advance_stage(profile: ScaffoldProfile) -> dict[str, Any]:
    """Advance the cold start stage and return what changed."""
    old_stage = profile.stage
    new_stage = determine_stage(profile)
    profile.stage = new_stage

    changes = {
        "previous_stage": old_stage.value,
        "current_stage": new_stage.value,
    }

    if old_stage == ColdStartStage.OBSERVING and new_stage == ColdStartStage.PROTOTYPING:
        changes["message"] = (
            "观察期结束。现在开始，我会基于你的行为给出初步观察，"
            "每条观察都是可验证的行为描述（而非身份标签），你可以确认或否认。"
        )
        changes["unlocked"] = ["behavior_observations", "taste_card_basic"]
        profile.data_confidence = 0.3
        profile.fingerprint_version = "v0-prototype"

    elif old_stage == ColdStartStage.PROTOTYPING and new_stage == ColdStartStage.CONFIRMING:
        changes["message"] = (
            "原型期结束。你已经积累了足够的数据，现在解锁完整的思考画像和成长叙事。"
        )
        changes["unlocked"] = [
            "full_fingerprint",
            "growth_narrative",
            "unique_perspective_detection",
            "radar_chart",
        ]
        profile.data_confidence = 0.7
        profile.fingerprint_version = "v1-confirmed"

    return changes


# ── Observation Generator ──

def generate_behavior_observation(
    profile: ScaffoldProfile,
    recent_sessions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate behavior-description observations for the prototyping stage.

    Returns observations in behavior-description format (NOT identity labels):
      ✅ "你在这3次思考中都先提反方观点再展开论证"
      ❌ "你是批判性思考者"
    """
    if profile.stage == ColdStartStage.OBSERVING or len(recent_sessions) < 3:
        return []

    observations = []

    # Observation 1: Argument structure pattern
    observations.append({
        "id": f"obs_{profile.session_count}_structure",
        "type": "behavior_description",
        "text": "观察生成中...",  # Would be filled by LLM analysis
        "confidence": 0.5,
        "verified": None,  # None = not yet confirmed by user
        "action_required": True,
    })

    return observations


# ── Stage-aware System Response ──

def get_stage_message(profile: ScaffoldProfile) -> str:
    """Get the appropriate system message for the user's current stage."""
    if profile.stage == ColdStartStage.OBSERVING:
        remaining = 3 - profile.session_count
        return (
            f"🔍 观察期（{profile.session_count}/3）\n"
            f"我正在观察你的思考方式。还需要 {remaining} 次对话才能开始理解你。"
        )

    elif profile.stage == ColdStartStage.PROTOTYPING:
        remaining = profile.graduation_session - profile.session_count
        return (
            f"🔍 原型期（{profile.session_count}/{profile.graduation_session}）\n"
            f"我已经开始注意到一些模式，但仍在验证中。"
            f"每条观察都是可验证的行为描述——你可以随时确认或否认。"
        )

    else:
        return (
            "✅ 你的思考指纹已建立。\n"
            "完整画像和成长叙事已解锁。你可以随时重置或手动调整。"
        )
