"""Strategy Intelligence Layer tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.reporting.runtime.strategy_intelligence import (
    build_strategy_intelligence,
    update_strategy_state,
)


def _snapshot(snapshot_id: str, run_id: str, rows: list[dict]) -> dict:
    return {
        "schema": "ai_judge.report_snapshot.v1",
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "created_at": "2026-06-17T00:00:00Z",
        "title": "世界杯赔率套利与下注价值判断",
        "question": "世界杯赔率、盘口和模型信号出现分歧时，是否存在套利或 no bet 策略？",
        "mode": "deep_judge",
        "mode_label": "Deep Judge",
        "status": "completed",
        "judge_ir": {"schema": "ai_judge.judge_ir.v1", "sections": []},
        "noise_audit": {
            "schema": "ai_judge.noise_audit.v1",
            "question_hash": "same-question",
            "seat_noise_rows": rows,
        },
    }


def test_strategy_intelligence_classifies_clusters_entropy_and_drift():
    previous_state = {
        "schema": "ai_judge.strategy_state.v1",
        "profiles": {
            "alpha": {"latest_strategy": "NO_BET_RATIONAL"},
            "beta": {"latest_strategy": "CONSERVATIVE_EDGE"},
        },
    }
    snapshot = _snapshot(
        "snapshot-s2",
        "run-2",
        [
            {
                "seat": "alpha",
                "seat_name": "Alpha",
                "stance": "arbitrage",
                "confidence": 0.81,
                "valid": True,
                "noise_flags": [],
            },
            {
                "seat": "beta",
                "seat_name": "Beta",
                "stance": "no_bet",
                "confidence": 0.42,
                "valid": True,
                "noise_flags": [],
            },
            {
                "seat": "gamma",
                "seat_name": "Gamma",
                "stance": "support",
                "confidence": 0.92,
                "valid": True,
                "noise_flags": [],
            },
            {
                "seat": "delta",
                "seat_name": "Delta",
                "stance": "support",
                "confidence": 0.94,
                "valid": False,
                "noise_flags": ["format_noise"],
            },
        ],
    )

    result = build_strategy_intelligence(snapshot=snapshot, previous_state=previous_state)

    assert result["schema"] == "ai_judge.strategy_intelligence.v1"
    assert result["model_strategies"]["alpha"]["strategy_type"] == "ARBITRAGE_SEEKING"
    assert result["model_strategies"]["beta"]["strategy_type"] == "NO_BET_RATIONAL"
    assert result["model_strategies"]["gamma"]["strategy_type"] == "AGGRESSIVE_VALUE"
    assert result["model_strategies"]["delta"]["strategy_type"] == "NOISE_TRADING"
    assert len(result["cluster_map"]) == 4
    assert result["market_structure"]["stance_entropy"] > 0
    assert result["market_structure"]["disagreement_type"] == "price_driven"
    assert result["strategy_drift"]["model_drifts"]["alpha"]["direction"] == "toward_arbitrage"
    assert result["strategy_drift"]["model_drifts"]["beta"]["direction"] == "toward_no_bet"
    assert result["strategy_drift"]["aggregate_drift_score"] > 0


def test_strategy_state_persists_per_model_per_run(tmp_path):
    first = _snapshot(
        "snapshot-s1",
        "run-1",
        [
            {
                "seat": "alpha",
                "seat_name": "Alpha",
                "stance": "no_bet",
                "confidence": 0.38,
                "valid": True,
                "noise_flags": [],
            }
        ],
    )
    second = _snapshot(
        "snapshot-s2",
        "run-2",
        [
            {
                "seat": "alpha",
                "seat_name": "Alpha",
                "stance": "arbitrage",
                "confidence": 0.82,
                "valid": True,
                "noise_flags": [],
            }
        ],
    )

    update_strategy_state(reports_root=tmp_path, snapshot=first)
    payload = update_strategy_state(reports_root=tmp_path, snapshot=second, previous_snapshot=first)

    state_path = tmp_path / "runtime" / "strategy_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    profile = state["profiles"]["alpha"]

    assert payload["strategy_intelligence"]["model_strategies"]["alpha"]["strategy_type"] == "ARBITRAGE_SEEKING"
    assert state["schema"] == "ai_judge.strategy_state.v1"
    assert state["snapshot_count"] == 2
    assert profile["runs_seen"] == 2
    assert profile["previous_strategy"] == "NO_BET_RATIONAL"
    assert profile["latest_strategy"] == "ARBITRAGE_SEEKING"
    assert profile["latest_drift_direction"] == "toward_arbitrage"
    assert profile["recent_runs"][0]["run_id"] == "run-2"
