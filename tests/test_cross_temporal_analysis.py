from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from core.auto_jury import format_verdict_markdown
from core.cross_temporal_analysis import build_cross_temporal_analysis


def _sample_verdict() -> dict:
    return {
        "run_id": "run-xray",
        "question": "用横纵分析法改造 AI Judge",
        "mode": "strategic",
        "status": "complete",
        "verdict": "conditional",
        "verdict_label": "条件支持",
        "confidence": 78,
        "average_score": 0.71,
        "reasons": ["网页席位未全量回收，不能包装成全模型共识。"],
        "next_steps": ["先补齐旧页面答案，再进入发布门禁。"],
        "seat_count": 3,
        "seat_scores": [
            {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.82, "claims_count": 4},
            {"seat": "qwen", "seat_name": "Qwen", "average_score": 0.60, "claims_count": 3},
        ],
        "web_bridge": {
            "requested_count": 3,
            "ok_count": 2,
            "failed_count": 1,
            "collection_complete": False,
            "raw_results": [
                {"seat": "chatgpt", "seat_name": "ChatGPT", "ok": True, "response": "支持，但需要验证。"},
                {"seat": "qwen", "seat_name": "Qwen", "ok": True, "response": "谨慎支持。"},
                {
                    "seat": "minimax",
                    "seat_name": "MiniMax",
                    "ok": False,
                    "supplementable": True,
                    "error": {"code": "slow_response_pending", "message": "页面已有答案但未回收。"},
                },
            ],
            "score_rounds": [
                {"id": "raw_answer", "label": "原始答案", "average_score": 0.74, "claim_count": 4},
                {"id": "peer_review", "label": "互评", "average_score": 0.68, "claim_count": 3},
            ],
        },
        "execution_trace": {
            "events": [
                {"index": 1, "phase": "collect", "action": "wait", "detail": "等待 MiniMax"},
                {"index": 2, "phase": "retry", "action": "existing_answer_recovery", "detail": "旧页面回收"},
                {"index": 3, "phase": "report", "action": "run_saved", "detail": "报告已写入"},
            ]
        },
    }


def test_cross_temporal_analysis_marks_partial_bridge_and_actions():
    analysis = build_cross_temporal_analysis(_sample_verdict())

    assert analysis["schema"] == "cross_temporal_analysis.v2"
    assert analysis["horizontal_comparison"]["ok_count"] == 2
    assert analysis["horizontal_comparison"]["pending_count"] == 1
    assert analysis["horizontal_comparison"]["consensus_label"] == "席位不完整"
    assert analysis["vertical_trace"]["retry_event_count"] == 1
    assert "2/3" in analysis["closeout_report"]["executive_summary"]
    assert any("旧页面只读回收" in item for item in analysis["recommended_actions"])
    assert analysis["trust_tier"]["tier"] == "D"

    coverage = next(item for item in analysis["math_audit"]["signals"] if item["id"] == "coverage_gate")
    assert coverage["severity"] == "block"
    signal_ids = {item["id"] for item in analysis["math_audit"]["signals"]}
    assert {
        "svd_noise_filter",
        "simpson_aggregate_trap",
        "bertrand_standard_sensitivity",
        "birthday_claim_collision",
        "cauchy_schwarz_redundancy",
        "axiomatic_self_consistency",
    } <= signal_ids
    assert len(analysis["math_audit"]["roi_decisions"]) == 6


def test_markdown_includes_cross_temporal_closeout():
    verdict = _sample_verdict()
    verdict["cross_temporal_analysis"] = build_cross_temporal_analysis(verdict)

    rendered = format_verdict_markdown(verdict)

    assert "## Cross-Temporal Closeout" in rendered
    assert "Trust tier" in rendered
    assert "容斥式席位覆盖" in rendered
    assert "SVD 评分噪声过滤" in rendered
    assert "只读回收" in rendered


def test_local_engine_uses_seat_scores_as_complete_coverage():
    verdict = _sample_verdict()
    verdict.pop("web_bridge")
    verdict["seat_count"] = 2
    verdict["seat_scores"] = verdict["seat_scores"][:2]

    analysis = build_cross_temporal_analysis(verdict)

    assert analysis["vertical_trace"]["bridge_health"] == "本地引擎"
    assert analysis["horizontal_comparison"]["ok_count"] == 2
    assert analysis["horizontal_comparison"]["requested_count"] == 2
    coverage = next(item for item in analysis["math_audit"]["signals"] if item["id"] == "coverage_gate")
    assert coverage["severity"] == "ok"


def test_api_save_run_attaches_cross_temporal_analysis(tmp_path, monkeypatch):
    module_path = Path(__file__).resolve().parents[1] / "product" / "api_server.py"
    spec = importlib.util.spec_from_file_location("api_server_xray_test", module_path)
    assert spec and spec.loader
    api_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_server)
    monkeypatch.setattr(api_server, "RUNS_DIR", tmp_path)

    verdict = _sample_verdict()
    api_server._save_run("run-xray", verdict)

    saved = json.loads((tmp_path / "run-xray" / "verdict.json").read_text(encoding="utf-8"))
    assert saved["cross_temporal_analysis"]["schema"] == "cross_temporal_analysis.v2"
    assert "Cross-Temporal Closeout" in (tmp_path / "run-xray" / "verdict.md").read_text(encoding="utf-8")


def test_required_policy_treats_grok_as_optional_for_trust_tier():
    verdict = _sample_verdict()
    verdict["confidence"] = 88
    verdict["web_bridge"] = {
        "requested_count": 3,
        "ok_count": 2,
        "failed_count": 1,
        "collection_complete": True,
        "execution_policy": {
            "required_count": 2,
            "required_valid_count": 2,
            "required_failed_count": 0,
            "required_supplementable_seats": [],
            "optional_seats": ["grok"],
            "collection_complete": True,
        },
        "raw_results": [
            {"seat": "chatgpt", "seat_name": "ChatGPT", "ok": True, "response": "支持，证据充足。"},
            {"seat": "qwen", "seat_name": "Qwen", "ok": True, "response": "支持，路径清晰。"},
            {"seat": "grok", "seat_name": "Grok", "ok": False, "error": {"code": "provider_quota_limited"}},
        ],
    }

    analysis = build_cross_temporal_analysis(verdict)

    assert analysis["horizontal_comparison"]["required_ok_count"] == 2
    assert analysis["horizontal_comparison"]["required_count"] == 2
    coverage = next(item for item in analysis["math_audit"]["signals"] if item["id"] == "coverage_gate")
    assert coverage["severity"] == "ok"
    assert analysis["trust_tier"]["tier"] in {"A", "B"}
