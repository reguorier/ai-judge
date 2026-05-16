from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


def _load_api_server():
    module_path = Path(__file__).resolve().parents[1] / "product" / "api_server.py"
    spec = importlib.util.spec_from_file_location("api_server_product_state_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chief_judge_metadata_attaches_to_local_verdict():
    api_server = _load_api_server()
    verdict = {
        "question": "测试主审",
        "seats": ["chatgpt", "deepseek"],
        "seat_scores": [
            {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.82, "claims_count": 3},
            {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.74, "claims_count": 3},
        ],
        "average_score": 0.78,
        "verdict": "credible",
        "verdict_label": "可采信",
        "one_liner": "本轮判断成立。",
    }

    api_server._attach_product_run_metadata(verdict, chief_judge="deepseek", abstained_seats=["grok"])

    assert verdict["chief_judge"]["id"] == "deepseek"
    assert verdict["seat_roster"]["selected"] == ["chatgpt", "deepseek"]
    assert verdict["seat_roster"]["abstained"] == ["grok"]
    assert verdict["judge_answer"]["label"] == "DeepSeek 轮值主审"
    assert "本轮主审：DeepSeek" in verdict["judge_answer"]["answer"]
    assert verdict["single_judge_baseline"]["label"] == "DeepSeek 单模型对照"
    assert verdict["roster_sensitivity"]


def test_seat_scoreboard_aggregates_runs_and_rounds():
    api_server = _load_api_server()
    verdicts = [
        {
            "run_id": "run-new",
            "question": "新问题",
            "mode": "strategic",
            "created_at": "2026-05-16T12:00:00+00:00",
            "seat_scores": [
                {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.9, "claims_count": 4},
                {"seat": "chatgpt", "seat_name": "ChatGPT", "average_score": 0.7, "claims_count": 4},
            ],
            "web_bridge": {
                "score_rounds": [
                    {"id": "raw_answer", "seat_scores": [{"seat": "deepseek", "average_score": 0.8}]},
                    {"id": "peer_review", "seat_scores": [{"seat": "deepseek", "average_score": 0.88}]},
                ],
                "raw_results": [
                    {"seat": "deepseek", "ok": True},
                    {"seat": "chatgpt", "ok": False, "error": {"code": "response_timeout"}},
                ],
            },
        },
        {
            "run_id": "run-old",
            "question": "旧问题",
            "mode": "standard",
            "created_at": "2026-05-15T12:00:00+00:00",
            "seat_scores": [
                {"seat": "deepseek", "seat_name": "DeepSeek", "average_score": 0.7, "claims_count": 3},
            ],
        },
    ]

    scoreboard = api_server._build_seat_scoreboard(
        verdicts=verdicts,
        bridge={
            "seats": [{"id": "deepseek", "provider": "DeepSeek", "channel": "web", "ready": True}],
            "seat_browser_matrix": [{"seat": "deepseek", "target": "DeepSeek Tab", "ready": True}],
        },
    )

    deepseek = next(row for row in scoreboard["seats"] if row["seat"] == "deepseek")
    chatgpt = next(row for row in scoreboard["seats"] if row["seat"] == "chatgpt")

    assert scoreboard["runs_considered"] == 2
    assert deepseek["run_count"] == 2
    assert deepseek["average_score"] == 0.8
    assert deepseek["latest_run"]["run_id"] == "run-new"
    assert deepseek["k_avg"] == 0.8
    assert deepseek["c_avg"] == 0.88
    assert deepseek["r_stability"] == 1.0
    assert chatgpt["failure_count"] == 1


def test_supplement_merge_replaces_slow_seat_and_marks_recovery():
    api_server = _load_api_server()
    original = [
        {
            "seat": "chatgpt",
            "ok": False,
            "supplementable": True,
            "error": {"code": "slow_response_pending", "message": "still thinking"},
        },
        {"seat": "deepseek", "ok": True, "response": "done"},
    ]
    supplement = [
        {"seat": "chatgpt", "ok": True, "response": "late answer", "error": None},
    ]

    merged = api_server._merge_supplement_raw_results(original, supplement, "supp-1")

    assert merged[0]["ok"]
    assert merged[0]["recovered_by_supplement"]
    assert merged[0]["supplemented_from_run_id"] == "supp-1"
    assert merged[0]["supplement_history"][0]["previous_error"]["code"] == "slow_response_pending"
    assert merged[1]["seat"] == "deepseek"


def test_attach_citation_mvp_adds_replay_ledger_and_gap_suggestions():
    api_server = _load_api_server()
    verdict = {
        "run_id": "run-cite",
        "question": "升级 AI Judge",
        "web_bridge": {
            "raw_results": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": "引用验证 MVP 参考 https://example.com/report 。",
                }
            ],
            "mentor_supplements": [
                {
                    "seat": "chatgpt",
                    "seat_name": "ChatGPT",
                    "ok": True,
                    "response": "导师补充：Replay Ledger 保留原文。",
                }
            ],
            "external_evidence": [
                {"url": "https://example.com/report", "title": "AI Judge 引用验证 MVP report", "snippet": "引用验证 MVP"}
            ],
        },
    }

    report = api_server._attach_citation_mvp(verdict, run_id="run-cite")

    assert report["certification_id"].startswith("CITE-")
    assert verdict["web_bridge"]["certification_id"] == report["certification_id"]
    assert verdict["web_bridge"]["replay_ledger"][0]["raw_answer"].startswith("引用验证 MVP")
    assert verdict["web_bridge"]["evidence_gap_suggestions"]["will_rewrite_body"] is False
    assert verdict["web_bridge"]["evidence_broker"]["counts"]["user_supplied"] == 1
    assert verdict["web_bridge"]["blind_cross_validation"]["status"] == "pending_model_reviews"
    assert report["evidence_gap_queue"]["schema"] == "evidence_gap_queue.v1"
    assert report["eval_case"]["case_id"].startswith("EVAL-")


def test_evidence_os_api_endpoints_update_saved_run():
    api_server = _load_api_server()
    old_runs_dir = api_server.RUNS_DIR
    old_tasks = api_server.TASKS
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        api_server.RUNS_DIR = tmp_path
        api_server.TASKS = api_server.TaskManager(db_path=tmp_path / "tasks.sqlite3")
        try:
            verdict = {
                "run_id": "run-api",
                "question": "AI Judge",
                "web_bridge": {
                    "raw_results": [{"seat": "chatgpt", "ok": True, "response": "无引用回答。"}],
                    "mentor_supplements": [],
                    "external_evidence": [],
                },
            }
            api_server._attach_citation_mvp(verdict, run_id="run-api")
            api_server._save_run("run-api", verdict)
            client = api_server.app.test_client()

            gaps = client.get("/api/judge/run-api/evidence-gaps")
            assert gaps.status_code == 200
            task_id = gaps.get_json()["tasks"][0]["task_id"]

            resolved = client.post(
                f"/api/judge/run-api/evidence-gaps/{task_id}/resolve",
                json={"resolution": "补充外部证据", "evidence_id": "EVID-1"},
            )
            assert resolved.status_code == 200
            assert resolved.get_json()["evidence_gap_queue"]["open_count"] == 0

            blind = client.post(
                "/api/judge/run-api/blind-review",
                json={"reviews": [
                    {"reviewer": "gemini", "citation_id": "CITE-000", "decision": "confirm"},
                    {"reviewer": "qwen", "citation_id": "CITE-000", "decision": "confirm"},
                ]},
            )
            assert blind.status_code == 200
            assert blind.get_json()["blind_cross_validation"]["result"]["confirmed_count"] == 1

            signed = client.post(
                "/api/judge/run-api/human-review",
                json={"reviewer": "Auditor", "decision": "conditional", "reason": "我确认该结果仍需补充外部证据再发布，并保留人工复核记录。"},
            )
            assert signed.status_code == 200
            assert signed.get_json()["human_review_status"]["status"] == "signed"
        finally:
            api_server.RUNS_DIR = old_runs_dir
            api_server.TASKS = old_tasks
