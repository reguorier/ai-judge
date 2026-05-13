#!/usr/bin/env python3
"""Achievement v2.0 — Metrics computation, breakthrough detection, visualization data.

AI Judge V2 Direction 4 core module. Implements:
  - 3 core MVP metrics (streak days, overturned count, unique ideas)
  - Radar chart data generation (5 dimensions + 30-day ghost overlay)
  - Breakthrough moment detection (+20% sustained for 2 weeks = golden node)
  - Weekly/Monthly report data structures

Adopted from: 豆包 3指标极简主义 + MiniMax 雷达图残影 + Gemini 防焦虑原则
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Core MVP Metrics ──

@dataclass
class AchievementSnapshot:
    """A point-in-time snapshot of user achievement metrics."""
    user_id: str
    timestamp: float = field(default_factory=time.time)

    # 3 MVP Metrics
    streak_days: int = 0          # Consecutive days with thinking activity
    overturned_count: int = 0     # Times user was right and AI was wrong
    unique_ideas_count: int = 0   # Times flagged as non-consensus but coherent

    # Extended Metrics (collected, not displayed in MVP)
    blind_spot_reduction: float = 0.0   # Rate of blind spot fixes
    cross_domain_links: int = 0         # Cross-domain connections made
    cognitive_depth_level: float = 0.0  # Avg depth score
    anchor_proximity: float = 50.0      # Distance from target anchor (0=perfect)
    calibration_accuracy: float = 0.0   # User self-assessment vs system assessment gap

    def to_dict(self) -> dict[str, Any]:
        return {
            "streak_days": self.streak_days,
            "overturned_count": self.overturned_count,
            "unique_ideas_count": self.unique_ideas_count,
        }


def compute_streak(activity_dates: list[float]) -> int:
    """Compute consecutive days with thinking activity."""
    if not activity_dates:
        return 0

    # Sort dates descending, convert to day-level
    days = sorted(set(
        int(d // 86400) for d in activity_dates
    ), reverse=True)

    today = int(time.time() // 86400)
    if days[0] < today - 1:  # Streak broken (no activity yesterday or today)
        return 0

    streak = 1
    for i in range(1, len(days)):
        if days[i - 1] - days[i] == 1:
            streak += 1
        else:
            break

    return streak


# ── Radar Chart Data ──

RADAR_DIMENSIONS = [
    ("logical_rigor", "逻辑严密性"),
    ("creativity", "创造性"),
    ("depth", "深度"),
    ("breadth", "广度"),
    ("self_awareness", "自省力"),
]


def generate_radar_data(
    current_scores: dict[str, float],
    past_scores: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Generate radar chart data for 5 dimensions.

    Includes ghost overlay from 30 days ago for visual comparison.
    """
    dims = []
    for key, label in RADAR_DIMENSIONS:
        current = current_scores.get(key, 5.0)
        past = past_scores.get(key, current) if past_scores else None

        dims.append({
            "key": key,
            "label": label,
            "current": round(current, 1),
            "past_30d": round(past, 1) if past is not None else None,
            "change": round(current - past, 1) if past is not None else None,
        })

    return {
        "dimensions": dims,
        "has_history": past_scores is not None,
        "generated_at": time.time(),
    }


# ── Breakthrough Detection ──

@dataclass
class BreakthroughMoment:
    """A detected breakthrough moment in a user's thinking journey."""
    timestamp: float
    dimension: str
    description: str
    week_before_avg: float
    week_after_avg: float
    improvement_pct: float


def detect_breakthrough(
    metric_history: list[dict[str, Any]],
    *,
    min_improvement_pct: float = 20.0,
    sustain_weeks: int = 2,
) -> list[BreakthroughMoment]:
    """Detect breakthrough moments in metric history.

    A breakthrough is defined as:
    - A single metric improves >20% in one week
    - The improvement is sustained for at least 2 weeks

    Returns list of breakthrough moments, sorted by recency.
    """
    if len(metric_history) < 3:
        return []

    breakthroughs = []
    weekly_points = _aggregate_weekly(metric_history)

    for i in range(1, len(weekly_points) - sustain_weeks):
        prev = weekly_points[i - 1]
        curr = weekly_points[i]

        for key in prev.get("scores", {}):
            prev_val = prev["scores"].get(key, 0)
            curr_val = curr["scores"].get(key, 0)

            if prev_val == 0:
                continue

            improvement = (curr_val - prev_val) / prev_val * 100

            if improvement >= min_improvement_pct:
                # Check if sustained
                sustained = True
                for j in range(1, sustain_weeks + 1):
                    if i + j >= len(weekly_points):
                        sustained = False
                        break
                    next_val = weekly_points[i + j]["scores"].get(key, 0)
                    if next_val < curr_val * 0.9:  # Dropped more than 10%
                        sustained = False
                        break

                if sustained:
                    breakthroughs.append(BreakthroughMoment(
                        timestamp=curr["timestamp"],
                        dimension=key,
                        description=f"{key} 维度单周提升 {improvement:.0f}%，已维持 {sustain_weeks} 周",
                        week_before_avg=prev_val,
                        week_after_avg=curr_val,
                        improvement_pct=round(improvement, 1),
                    ))

    return sorted(breakthroughs, key=lambda b: b.timestamp, reverse=True)


def _aggregate_weekly(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate metric history into weekly data points."""
    if not history:
        return []

    weekly = []
    current_week = None
    week_data = []

    for point in sorted(history, key=lambda p: p.get("timestamp", 0)):
        ts = point.get("timestamp", 0)
        week = int(ts // (7 * 86400))

        if current_week is None:
            current_week = week

        if week != current_week:
            # Average the week
            avg_scores = {}
            for wd in week_data:
                for k, v in wd.get("scores", {}).items():
                    avg_scores[k] = avg_scores.get(k, 0) + v

            for k in avg_scores:
                avg_scores[k] /= len(week_data)

            weekly.append({
                "timestamp": current_week * 7 * 86400,
                "scores": avg_scores,
            })

            current_week = week
            week_data = []

        week_data.append(point)

    return weekly


# ── Weekly & Monthly Reports ──

def generate_weekly_report_data(
    snapshot: AchievementSnapshot,
    streak: int,
    breakthroughs: list[BreakthroughMoment],
) -> dict[str, Any]:
    """Generate data for the weekly "3-line" report.

    The weekly report is deliberately minimal — 3 lines, 30 seconds to read.
    """
    new_breakthrough = breakthroughs[0] if breakthroughs else None

    return {
        "type": "weekly",
        "lines": [
            f"本周你思考了 {streak} 天",
            f"你推翻了 {snapshot.overturned_count} 次 AI 的判断",
            f"你有 {snapshot.unique_ideas_count} 个独特想法",
        ] if not new_breakthrough else [
            f"本周你思考了 {streak} 天",
            f"突破时刻：{new_breakthrough.description}",
            f"你推翻了 {snapshot.overturned_count} 次 AI 的判断",
        ],
        "generated_at": time.time(),
    }


def generate_monthly_report_data(
    current_snapshot: AchievementSnapshot,
    past_snapshot: Optional[AchievementSnapshot],
    radar_data: dict[str, Any],
    breakthroughs: list[BreakthroughMoment],
    blind_spot: str,
    suggestion: str,
) -> dict[str, Any]:
    """Generate data for the monthly deep report.

    5 sections: core numbers, capability change, breakthrough story, blind spot, suggestion.
    """
    sections = {
        "core_numbers": {
            "total_sessions": 0,  # Would be populated from real data
            "streak_days": current_snapshot.streak_days,
            "overturned": current_snapshot.overturned_count,
            "unique_ideas": current_snapshot.unique_ideas_count,
        },
        "capability_change": {
            "radar": radar_data,
            "summary": "本月能力画像更新" if past_snapshot else "首次能力画像",
        },
        "breakthrough_story": {
            "has_breakthrough": len(breakthroughs) > 0,
            "moment": breakthroughs[0].description if breakthroughs else "本月无显著突破",
        },
        "blind_spot_reminder": {
            "spot": blind_spot or "暂无明确盲区",
            "suggestion": "留意这个方向，它可能是下一个突破点。",
        },
        "next_month_suggestion": {
            "text": suggestion or "继续在当前方向深耕，也可以尝试一个全新的思考领域。",
        },
    }

    return {
        "type": "monthly",
        "report_date": time.time(),
        "sections": sections,
    }


# ── Anti-Anxiety Design Rules ──

ANTI_ANXIETY_RULES = [
    {
        "rule": "不排名，不比较",
        "implementation": "所有可视化只展示个人基线对比，绝不引入他人数据。",
    },
    {
        "rule": "不展示退步，只展示波动",
        "implementation": "分数下降被重标记为'探索期正常波动'或'新领域学习曲线'。",
    },
    {
        "rule": "所有数据默认私密",
        "implementation": "用户主动分享才生成可转发卡片。一键隐藏所有可视化。",
    },
    {
        "rule": "7天后自动归档",
        "implementation": "历史数据7天后从主视图移入归档，降低'被数据追赶'的焦虑感。",
    },
]
