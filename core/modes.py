#!/usr/bin/env python3
"""AI Judge Jury Modes — COUNCIL-005 consensus feature.

Defines three jury modes with different depth / speed / seat-count tradeoffs:
  - Flash:    3 seats, 30 seconds, no evidence trace (quick fact-check)
  - Standard: 5 seats, 2 minutes, evidence trace + consensus (most decisions)
  - Strategic: all seats, 5-10 minutes, full dissent + evidence + consensus

Usage:
  from core.modes import JURY_MODES, resolve_mode, mode_info

  config = resolve_mode("flash")
  config = resolve_mode("standard", override_seats=["gemini", "grok"])
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure project root on path for standalone testing
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

JURY_MODES: dict[str, dict[str, Any]] = {
    "flash": {
        "name": "Flash 快速陪审",
        "name_en": "Flash Quick Jury",
        "emoji": "⚡",
        "seats": ["gemini", "grok", "doubao"],
        "seat_rationale": (
            "INTJ (Gemini): 系统性风险识别，事实核查最强。"
            "ENTP (Grok): 挑衅性提问，发现盲点。"
            "ENTJ (Doubao): 决策果断，快速收敛。"
        ),
        "description": (
            "3 席快速裁决，约 30 秒出结果。"
            "适合事实核查、简单判断、快速比对。"
            "跳过证据溯源和共识检验以换取速度。"
        ),
        "timeout_seconds": 30,
        "collect_timeout_per_seat": 8,
        "features": {
            "evidence_trace": False,
            "consensus_check": False,
            "dissent_analysis": False,
            "peach_projection": False,
            "neuro_profile": False,
        },
        "output": "compact",  # 三色标签 + 一句话摘要
    },
    "standard": {
        "name": "Standard 标准陪审",
        "name_en": "Standard Jury",
        "emoji": "⚖",
        "seats": ["gemini", "deepseek", "claude", "kimi", "grok", "doubao"],
        "seat_rationale": (
            "INTJ + INTP + ENFP + ENTP + ENTJ: 覆盖系统性分析、深度推理、"
            "市场叙事、挑衅性检查、决策执行六大维度。6 席平衡裁决。"
        ),
        "description": (
            "6 席平衡裁决，约 2 分钟出结果。"
            "适合大多数商业决策：财报分析、政策评估、技术对比。"
            "含证据溯源和共识检验，不包含完整异议分析。"
        ),
        "timeout_seconds": 120,
        "collect_timeout_per_seat": 20,
        "features": {
            "evidence_trace": True,
            "consensus_check": True,
            "dissent_analysis": False,
            "peach_projection": True,
            "neuro_profile": False,
        },
        "output": "standard",  # 判词摘要 + 评分表 + 证据溯源
    },
    "strategic": {
        "name": "Strategic 深度陪审",
        "name_en": "Strategic Full Jury",
        "emoji": "🏛",
        "seats": None,  # None = all configured seats
        "seat_rationale": (
            "全席参与：覆盖系统、执行、深推、中文生态、产品体验、合规与反共识视角。"
        ),
        "description": (
            "全席开启，约 5-10 分钟出结果。"
            "完整证据溯源 L1/L2/L3、共识检验、异议分析、二桃投影。"
            "适合重大决策：系统性风险评估、投资策略、政策制定。"
        ),
        "timeout_seconds": 600,
        "collect_timeout_per_seat": 60,
        "features": {
            "evidence_trace": True,
            "consensus_check": True,
            "dissent_analysis": True,
            "peach_projection": True,
            "neuro_profile": True,
        },
        "output": "full",  # 完整判词 MD + JSON + 独立 HTML 报告
    },
}


def resolve_mode(
    mode: str = "standard",
    override_seats: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve a mode configuration, with optional seat override.

    Args:
        mode: "flash", "standard", or "strategic"
        override_seats: Optional list of seat names to override default

    Returns:
        Complete mode config dict with resolved seats.

    Raises:
        ValueError: If mode is unknown.
    """
    mode = mode.lower().strip()
    if mode not in JURY_MODES:
        raise ValueError(
            f"Unknown mode '{mode}'. Available: {list(JURY_MODES.keys())}"
        )

    config = dict(JURY_MODES[mode])  # shallow copy

    # Resolve seats
    if override_seats:
        config["seats"] = [s.lower() for s in override_seats]
        config["_seats_override"] = True
    elif config["seats"] is None:
        # All configured seats for strategic
        from core.seat_personas import SEAT_PERSONAS
        config["seats"] = list(SEAT_PERSONAS.keys())
        config["_seats_override"] = False
    else:
        config["_seats_override"] = False

    config["_mode"] = mode
    return config


def mode_info(mode: str) -> dict[str, Any]:
    """Get human-readable mode information for display."""
    config = resolve_mode(mode)
    return {
        "mode": mode,
        "name": config["name"],
        "emoji": config["emoji"],
        "description": config["description"],
        "seat_count": len(config["seats"]),
        "seats": config["seats"],
        "estimated_time": f"{config['timeout_seconds'] // 60} 分钟" if config["timeout_seconds"] >= 60 else f"{config['timeout_seconds']} 秒",
        "features": config["features"],
    }


def list_modes() -> list[dict[str, Any]]:
    """List all available modes with summary info."""
    return [mode_info(m) for m in JURY_MODES.keys()]


# ─── Standalone test ──────────────────────────────────────

if __name__ == "__main__":
    print("AI Judge Jury Modes — Self Test\n")

    for mode_key in JURY_MODES:
        info = mode_info(mode_key)
        print(f"{info['emoji']} {info['name']} ({mode_key})")
        print(f"   Seats: {info['seat_count']} — {', '.join(info['seats'])}")
        print(f"   Time: ~{info['estimated_time']}")
        print(f"   Features: {info['features']}")
        print()

    # Test override
    custom = resolve_mode("flash", override_seats=["gemini", "chatgpt", "deepseek"])
    print(f"Override test: flash with 3 custom seats → {custom['seats']}")
    print(f"  _seats_override: {custom['_seats_override']}")

    # Test all seats for strategic
    strat = resolve_mode("strategic")
    print(f"\nStrategic mode: {len(strat['seats'])} seats → {strat['seats']}")

    print("\nAll tests passed")
