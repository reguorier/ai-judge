#!/usr/bin/env python3
"""Anchor Engine v2.0 — Goal anchoring with taste cards, distance calculation, drift detection.

AI Judge V2 Phase 2 core module. Implements:
  - Anchor data structure (5-field + dimensions + examples + hard constraints)
  - Taste Card generation from 3+2 examples
  - Distance calculation with zone-based scoring
  - Drift detection via Pearson correlation
  - Exploration budget toggle

Adopted from: MiniMax schema + 豆包 MVP + Meta 产品设计者 品味卡 + Gemini 纠偏环
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Data Structures ──

@dataclass
class AnchorDimension:
    """A single evaluation dimension with weight and target levels."""
    dim_name: str  # e.g., "准确性", "创造性", "品牌调性"
    weight: float  # 0-1, all weights must sum to 1.0
    evaluation_func: str = "eval_default"
    confidence_threshold: float = 0.7
    target_min: float = 6.0
    target_target: float = 8.0
    target_exemplary: float = 9.5


@dataclass
class GoalAnchor:
    """Complete goal anchor for a user."""
    anchor_id: str
    owner_id: str
    name: str  # e.g., "产品文案-品牌调性优先"
    dimensions: list[AnchorDimension]
    positive_examples: list[str]  # 2-10 ideal output examples
    negative_examples: list[str]  # 1-5 unacceptable output examples
    hard_constraints: list[str] = field(default_factory=list)
    exploration_budget: float = 0.15  # 15% exploration by default
    created_at: float = field(default_factory=time.time)
    last_calibrated: float = field(default_factory=time.time)
    drift_status: str = "normal"  # "normal" | "warning" | "drifted"
    drift_score: float = 0.0
    data_confidence: float = 0.0  # 0.0-1.0, how much real data backs this anchor

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "owner_id": self.owner_id,
            "name": self.name,
            "dimensions": [
                {
                    "dim_name": d.dim_name,
                    "weight": d.weight,
                    "evaluation_func": d.evaluation_func,
                    "confidence_threshold": d.confidence_threshold,
                    "target_level": {
                        "min": d.target_min,
                        "target": d.target_target,
                        "exemplary": d.target_exemplary,
                    },
                }
                for d in self.dimensions
            ],
            "positive_examples": self.positive_examples[:3],  # Only store top 3
            "negative_examples": self.negative_examples[:2],
            "hard_constraints": self.hard_constraints,
            "exploration_budget": self.exploration_budget,
            "created_at": self.created_at,
            "last_calibrated": self.last_calibrated,
            "drift_status": self.drift_status,
            "drift_score": self.drift_score,
            "data_confidence": self.data_confidence,
        }


# ── Anchor Creation ──

def create_anchor_from_examples(
    owner_id: str,
    name: str,
    positive_examples: list[str],
    negative_examples: list[str],
    *,
    min_positive: int = 2,
    min_negative: int = 1,
) -> tuple[Optional[GoalAnchor], str]:
    """Create a goal anchor from user-provided examples.

    Minimum: 2 positive + 1 negative example. Below this, refuse creation.

    Returns (anchor, message). anchor is None if creation refused.
    """
    if len(positive_examples) < min_positive:
        return None, f"需要至少 {min_positive} 个理想输出范例（当前 {len(positive_examples)} 个）"
    if len(negative_examples) < min_negative:
        return None, f"需要至少 {min_negative} 个不可接受范例（当前 {len(negative_examples)} 个）"

    anchor_id = _generate_anchor_id(owner_id, name)

    # Default dimensions with equal weights (will be calibrated later)
    dimensions = [
        AnchorDimension(dim_name="准确性", weight=0.30),
        AnchorDimension(dim_name="深度", weight=0.20),
        AnchorDimension(dim_name="创造性", weight=0.15),
        AnchorDimension(dim_name="流畅性", weight=0.15),
        AnchorDimension(dim_name="实用性", weight=0.20),
    ]

    anchor = GoalAnchor(
        anchor_id=anchor_id,
        owner_id=owner_id,
        name=name,
        dimensions=dimensions,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        data_confidence=0.2,  # Low confidence — just created from examples
    )

    return anchor, f"品味卡「{name}」已创建（基于 {len(positive_examples)} 正例 + {len(negative_examples)} 负例）。权重初始化为均分，将随使用自动校准。"


def _generate_anchor_id(owner_id: str, name: str) -> str:
    raw = f"{owner_id}:{name}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ── Taste Card Generation ──

@dataclass
class TasteCard:
    """User-friendly taste card — what the user sees."""
    style_summary: str  # One sentence: "你想要的风格"
    avoid_traps: str    # One sentence: "要避开的坑"
    current_distance: int  # 0-100, distance from target. 100 = perfect match
    dimension_weights: dict[str, float]


def generate_taste_card(anchor: GoalAnchor) -> TasteCard:
    """Generate a simple, user-readable taste card from an anchor.

    The taste card is deliberately minimal — 3 things the user can
    understand in 10 seconds.
    """
    # Style summary from dimension weights
    top_dims = sorted(anchor.dimensions, key=lambda d: d.weight, reverse=True)
    top_names = [d.dim_name for d in top_dims[:2]]
    style = f"你优先追求 {' 和 '.join(top_names)}"

    # Avoid traps from negative examples
    if anchor.negative_examples:
        avoid = f"避免类似「{anchor.negative_examples[0][:50]}...」的输出"
    else:
        avoid = "暂无负面案例"

    # Weights dict
    weights = {d.dim_name: d.weight for d in anchor.dimensions}

    return TasteCard(
        style_summary=style,
        avoid_traps=avoid,
        current_distance=50,  # Start at midpoint
        dimension_weights=weights,
    )


# ── Distance Calculation ──

def calculate_anchor_distance(
    anchor: GoalAnchor,
    dimension_scores: dict[str, float],
) -> dict[str, Any]:
    """Calculate weighted distance from current scores to anchor targets.

    Uses zone-based scoring:
      - Above target: gap = 0 (don't penalize exceeding)
      - In acceptable zone: gap = |target - score| × 0.5
      - Below acceptable: gap = |target - score| × 1.5

    Hard constraint violation: penalty = 50 per violation.
    """
    total_distance = 0.0
    dimension_details = {}
    hard_constraint_violations = 0

    for dim in anchor.dimensions:
        score = dimension_scores.get(dim.dim_name, dim.target_target)
        target = dim.target_target
        gap = abs(target - score)

        # Zone-based weighting
        if score >= target:
            zone_weight = 0.0  # Exceeding target isn't penalized
            zone = "exceed"
        elif score >= dim.target_min:
            zone_weight = 0.5
            zone = "acceptable"
        else:
            zone_weight = 1.5
            zone = "below"

        weighted_gap = dim.weight * gap * zone_weight
        total_distance += weighted_gap

        dimension_details[dim.dim_name] = {
            "score": score,
            "target": target,
            "gap": round(gap, 2),
            "zone": zone,
            "weighted_gap": round(weighted_gap, 4),
        }

    # Hard constraint penalty
    for constraint in anchor.hard_constraints:
        # In practice, this would check if the output violates the constraint
        # For now, hard_constraints are stored as descriptions for LLM evaluation
        pass

    # Normalize to 0-100 scale
    max_distance = sum(d.weight * 10 * 1.5 for d in anchor.dimensions)
    normalized = min(100, (total_distance / max_distance) * 100) if max_distance > 0 else 50

    return {
        "distance": round(total_distance, 4),
        "normalized_distance": round(normalized, 2),
        "dimension_details": dimension_details,
        "hard_constraint_violations": hard_constraint_violations,
        "verdict": _distance_verdict(normalized),
    }


def _distance_verdict(normalized_distance: float) -> str:
    if normalized_distance < 20:
        return "非常接近目标"
    elif normalized_distance < 40:
        return "接近目标"
    elif normalized_distance < 60:
        return "中等偏离"
    elif normalized_distance < 80:
        return "显著偏离"
    else:
        return "严重偏离"


# ── Drift Detection ──

def detect_anchor_drift(
    anchor: GoalAnchor,
    recent_behavior_scores: list[dict[str, float]],
    *,
    drift_threshold: float = 0.15,
) -> dict[str, Any]:
    """Detect if user's actual behavior is drifting from their declared anchor.

    Uses a simplified Pearson-like approach: compare the correlation between
    user's recent accepted outputs and the anchor's expected dimensional profile.

    Args:
        anchor: Current goal anchor
        recent_behavior_scores: List of dimension score dicts from recent accepted outputs
        drift_threshold: Threshold above which to trigger warning

    Returns:
        Drift detection result with status and message
    """
    if len(recent_behavior_scores) < 3:
        return {
            "drift_status": "normal",
            "drift_score": 0.0,
            "message": "数据不足，需要至少 3 次评审后进行漂移检测。",
        }

    # Compute average behavior profile
    dim_names = [d.dim_name for d in anchor.dimensions]
    behavior_profile = {}
    for dim in dim_names:
        scores = [s.get(dim, 0) for s in recent_behavior_scores if dim in s]
        behavior_profile[dim] = sum(scores) / len(scores) if scores else 0

    # Compute expected profile from anchor weights
    expected_profile = {d.dim_name: d.target_target * d.weight for d in anchor.dimensions}

    # Compute correlation between behavior and expected
    # A low correlation means user's behavior doesn't match their declared preferences
    behavior_vals = [behavior_profile.get(d, 0) for d in dim_names]
    expected_vals = [expected_profile.get(d, 0) for d in dim_names]

    correlation = _pearson_correlation(behavior_vals, expected_vals)
    drift_score = 1.0 - max(0, correlation)

    status = "normal"
    message = ""

    if drift_score > drift_threshold:
        status = "drifted"
        message = (
            f"你的最近 {len(recent_behavior_scores)} 次选择与品味卡「{anchor.name}」"
            f"存在 {drift_score:.0%} 的偏离。"
            f"要更新品味卡吗？"
        )
    elif drift_score > drift_threshold * 0.7:
        status = "warning"
        message = (
            f"你的选择开始与品味卡出现轻微偏离（{drift_score:.0%}）。"
            "目前仍在正常范围，但值得留意。"
        )

    # Update anchor state
    anchor.drift_score = drift_score
    anchor.drift_status = status

    return {
        "drift_status": status,
        "drift_score": round(drift_score, 4),
        "correlation": round(correlation, 4),
        "message": message,
        "behavior_profile": behavior_profile,
        "expected_profile": expected_profile,
    }


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    den_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

    if den_x == 0 or den_y == 0:
        return 0.0

    return num / (den_x * den_y)


# ── Exploration Budget ──

def should_explore(anchor: GoalAnchor, consecutive_strict_runs: int) -> tuple[bool, str]:
    """Determine if the current run should use exploration mode.

    Every 5th strict run, force 1 exploration. Plus the exploration_budget
    percentage of runs are randomly selected for exploration.

    Returns (should_explore, mode_description).
    """
    # Force exploration every 5 runs
    if consecutive_strict_runs >= 5:
        return True, "强制探索（每 5 次严格评审后 1 次自由探索）"

    # Random exploration based on budget
    import random
    if random.random() < anchor.exploration_budget:
        return True, f"随机探索（{anchor.exploration_budget:.0%} 预算触发）"

    return False, "严格模式（按目标锚点评分）"


# ── Dimension Weight Calibration (Correction Loop) ──

def calibrate_weights_from_diff(
    anchor: GoalAnchor,
    user_edited_output: str,
    ai_original_output: str,
) -> dict[str, Any]:
    """Update anchor weights based on user's edit behavior.

    This implements Gemini's "纠偏环" — when the user edits AI output,
    we extract implicit preferences from the diff and adjust weights.

    Note: This function computes the signals. Actual LLM-based diff analysis
    would be done by the calling code. Here we provide the structure.

    Returns adjustment suggestions. The caller decides whether to apply them.
    """
    # Placeholder for LLM-driven diff analysis
    # In production, this would:
    # 1. Compare original vs edited text
    # 2. Identify which dimensions changed
    # 3. Infer user's implicit preference direction
    # 4. Return weight adjustment suggestions

    suggestions = {
        "anchor_id": anchor.anchor_id,
        "action": "suggest_adjustment",
        "message": "基于你刚才的修改，检测到以下偏好信号：",
        "adjustments": [],  # Would be populated by LLM analysis
        "apply_automatically": False,  # User must confirm
    }

    # Mark that calibration happened
    anchor.last_calibrated = time.time()

    return suggestions
