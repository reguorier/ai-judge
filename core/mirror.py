#!/usr/bin/env python3
"""Mirror v2.0 — Thinking fingerprint, growth narrative, unique perspective.

AI Judge V2 Direction 3 core module. Implements:
  - Thinking fingerprint extraction (3-layer: structural, semantic, temporal)
  - Growth narrative generation ("two letters + one story" framework)
  - Unique perspective detection (non-consensus but internally coherent)
  - Dual-channel architecture (cold evaluation + warm mirror, separated)

Adopted from: DeepSeek 思考指纹 + Meta Seat H + Gemini 客体评判/主体共情分离
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Thinking Fingerprint ──

@dataclass
class ThinkingFingerprint:
    """A user's thinking fingerprint — behavior patterns, not identity labels."""
    user_id: str
    version: str  # "v0-prototype" or "v1-confirmed"
    data_points: int  # Number of sessions used

    # Layer 1: Structural (rule-driven)
    argument_style: str = "unknown"  # "deductive" | "inductive" | "analogical" | "mixed"
    info_density: float = 0.0       # Words per unique concept
    citation_frequency: float = 0.0 # Citations per 1000 chars
    meta_marker_ratio: float = 0.0  # Uncertainty markers per 1000 chars

    # Layer 2: Semantic (LLM-driven, populated by analysis)
    reasoning_preference: str = "unknown"  # "first_principles" | "analogy" | "case_based" | "framework"
    blind_spot_type: str = ""              # "over_index_novelty" | "confirmation_bias" | "scope_creep"
    unique_perspective_score: float = 0.0  # How much user diverges from consensus

    # Layer 3: Temporal (cross-session)
    style_stability: float = 0.0     # How consistent across sessions
    growth_vector: list[float] = field(default_factory=list)  # Direction of change
    exploration_diversity: float = 0.0  # Topic breadth

    # Metadata
    confidence: float = 0.3  # How confident the system is in this fingerprint

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "version": self.version,
            "data_points": self.data_points,
            "argument_style": self.argument_style,
            "info_density": round(self.info_density, 4),
            "citation_frequency": round(self.citation_frequency, 4),
            "meta_marker_ratio": round(self.meta_marker_ratio, 4),
            "reasoning_preference": self.reasoning_preference,
            "blind_spot_type": self.blind_spot_type,
            "unique_perspective_score": round(self.unique_perspective_score, 4),
            "style_stability": round(self.style_stability, 4),
            "exploration_diversity": round(self.exploration_diversity, 4),
            "confidence": round(self.confidence, 2),
        }


def extract_fingerprint_v0(
    user_id: str,
    sessions: list[dict[str, Any]],
) -> ThinkingFingerprint:
    """Extract initial thinking fingerprint from session data.

    v0 prototype — low confidence, explicitly marked as unverified.
    Uses structural features only (Layer 1). Semantic features require
    more data (>= 10 sessions) and are set to "unknown".
    """
    if not sessions:
        return ThinkingFingerprint(
            user_id=user_id,
            version="v0-prototype",
            data_points=0,
            confidence=0.1,
        )

    all_text = " ".join(
        s.get("output", s.get("content", ""))
        for s in sessions
        if isinstance(s, dict)
    )

    words = all_text.split()
    word_count = len(words)
    char_count = len(all_text)

    # Basic structural features
    info_density = word_count / max(char_count, 1) if char_count > 0 else 0
    meta_count = sum(
        1 for m in ["可能", "也许", "不确定", "或许", "maybe", "perhaps"]
        if m in all_text
    )
    meta_marker_ratio = meta_count / max(word_count, 1) * 1000

    return ThinkingFingerprint(
        user_id=user_id,
        version="v0-prototype",
        data_points=len(sessions),
        info_density=info_density,
        meta_marker_ratio=meta_marker_ratio,
        confidence=0.3,
    )


# ── Growth Narrative ("Two Letters + One Story") ──

@dataclass
class GrowthNarrative:
    """A growth narrative in the "two letters + one story" format."""
    title: str
    letter_past: str    # Letter 1: 30 days ago
    letter_present: str  # Letter 2: Now
    story_arc: str      # The narrative: who you're becoming
    evidence_snippets: list[str]  # Quotes from user's own work
    generated_at: str = ""


def generate_growth_narrative_prompt(
    user_id: str,
    fingerprint_now: ThinkingFingerprint,
    fingerprint_past: Optional[ThinkingFingerprint],
    recent_sessions: list[dict[str, Any]],
) -> str:
    """Generate the LLM prompt for growth narrative creation.

    This produces the prompt template that gets sent to the LLM.
    The actual generation is done by the LLM, but the prompt structure
    enforces the design constraints.

    Design constraints:
      - Max 800 chars
      - 2nd person ("你")
      - Must include >= 3 direct quotes from user's own text
      - Must identify at least one change the user hasn't noticed
      - Must NOT evaluate personality (no "你是一个深刻的人")
      - Only describe behavior (no "这个论证的结构很严密")
    """
    changes_detected = ""
    if fingerprint_past:
        changes = []
        if fingerprint_past.info_density != fingerprint_now.info_density:
            change = "up" if fingerprint_now.info_density > fingerprint_past.info_density else "down"
            changes.append(f"信息密度 {change}")
        if fingerprint_past.meta_marker_ratio != fingerprint_now.meta_marker_ratio:
            change = "more" if fingerprint_now.meta_marker_ratio > fingerprint_past.meta_marker_ratio else "less"
            changes.append(f"不确定表达 {change}")
        changes_detected = ", ".join(changes) if changes else "无明显变化"

    snippets = []
    for s in recent_sessions[-5:]:
        text = s.get("output", s.get("content", ""))
        if len(text) > 30:
            snippets.append(text[:200])

    prompt = f"""你是一个思考观察者，不是评判者。请基于以下数据生成一份"成长叙事"。

## 用户当前思考特征
- 信息密度: {fingerprint_now.info_density:.4f}
- 不确定标记频率: {fingerprint_now.meta_marker_ratio:.2f}/千字
- 数据点数: {fingerprint_now.data_points} 次会话

## 30天前的特征
{changes_detected if changes_detected else "数据不足，无30天前对比"}

## 用户近期原文摘录
{chr(10).join(f'- "{s}"' for s in snippets)}

## 生成要求
请按"两信一叙"格式生成：
1. 第一封信（30天前的你）：描述当时的思考模式，引用至少1处原文
2. 第二封信（现在的你）：描述现在注意到的变化，指出至少1个用户自己可能没发现的变化
3. 一段叙事（你正在成为谁）：将两封信串联成一个成长故事

## 硬约束
- 总字数不超过800字
- 使用第二人称"你"
- 至少引用3处用户原文
- 只描述行为（✅"你的论证密度从X变为Y"），不评价人格（❌"你是一个思想深刻的人"）
- 如果数据不足以支撑某个判断，诚实地说"我还不确定"

请直接用中文输出。"""

    return prompt


# ── Unique Perspective Detection ──

def detect_unique_perspective(
    user_claim: str,
    jury_consensus: str,
    *,
    divergence_threshold: float = 0.7,
    coherence_threshold: float = 0.8,
) -> dict[str, Any]:
    """Detect if user's perspective is non-consensus but internally coherent.

    In production, this uses embedding comparison + LLM coherence assessment.
    Here we provide the structural framework.

    Returns None if perspective is not uniquely notable.
    """
    # Placeholder for embedding-based divergence calculation
    # In production: compute cosine distance between user_claim and jury_consensus embeddings
    divergence = 0.5  # Placeholder
    coherence = 0.85   # Placeholder (would be LLM-assessed)

    if divergence > divergence_threshold and coherence > coherence_threshold:
        return {
            "flagged": True,
            "divergence_score": divergence,
            "coherence_score": coherence,
            "message": (
                "你在这个议题上提出了一个与众不同的观点。"
                "主流判断的方向与你不同，但你的论证在内部逻辑上是自洽的。"
                "这不是对错问题——而是说明你看到了其他人没看到的东西。"
            ),
            "action": "highlight_not_evaluate",
        }

    return {"flagged": False}


# ── Dual-Channel Feedback ──

@dataclass
class DualChannelFeedback:
    """Separate evaluation (cold) and mirror (warm) feedback channels."""
    # Cold channel: objective scoring
    scores: dict[str, float]  # Dimension -> score
    confidence_light: dict[str, Any]  # From determinism module

    # Warm channel: behavior observations only
    observations: list[str]        # "你这次先列了3个维度再做判断"
    growth_opportunities: list[str] # "可以尝试的探索方向"
    user_effort_acknowledgment: str # "我必须承认，你把X概念引入Y领域的尝试很勇敢"

    # Never in either channel: personality labels, identity statements
    # ✅ "这个论证的结构很严密"
    # ❌ "你是一个思路清晰的人"


def generate_mirror_feedback(
    scores: dict[str, float],
    fingerprint: ThinkingFingerprint,
    recent_sessions: list[dict[str, Any]],
) -> DualChannelFeedback:
    """Generate dual-channel feedback from current evaluation data.

    Cold channel: scores + confidence. Warm channel: behavior observations only.
    """
    # Cold channel
    cold = {
        "scores": scores,
        "confidence_light": {"level": "steady"},  # Would come from determinism module
    }

    # Warm channel — behavior descriptions only
    observations = []
    growth_opps = []

    if fingerprint.meta_marker_ratio > 5:
        observations.append("你在这次思考中频繁使用不确定标记，显示你在主动暴露认知边界")
    if fingerprint.info_density > 0.6:
        observations.append("你的信息密度较高，偏好紧凑的表达方式")

    # Find user effort to acknowledge
    acknowledgment = ""
    if recent_sessions:
        last = recent_sessions[-1]
        text = last.get("output", last.get("content", ""))
        if len(text) > 200:
            acknowledgment = "你这次思考的篇幅和结构投入是明显的，我能看到你在认真对待这个问题。"

    return DualChannelFeedback(
        scores=scores,
        confidence_light=cold["confidence_light"],
        observations=observations,
        growth_opportunities=growth_opps,
        user_effort_acknowledgment=acknowledgment,
    )
