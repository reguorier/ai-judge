import json
from pathlib import Path

from core.model_stability import (
    load_model_stability_profiles,
    model_stability_summary,
    update_model_stability_profiles,
)


def test_model_stability_profiles_track_quality_mode_and_rates(tmp_path):
    path = tmp_path / "profiles.json"
    audit = {
        "schema": "ai_judge.noise_audit.v1",
        "run_id": "run-xunfei-1",
        "noise_score": 72,
        "seat_noise_rows": [
            {
                "seat": "xunfei",
                "seat_name": "讯飞星火",
                "valid": False,
                "confidence": None,
                "error_code": "xunfei_quality_mode_not_verified",
                "noise_flags": ["invalid_output", "refusal_or_auth_block"],
            },
            {
                "seat": "deepseek",
                "seat_name": "DeepSeek",
                "valid": True,
                "confidence": 0.74,
                "error_code": "",
                "noise_flags": [],
            },
        ],
    }

    store = update_model_stability_profiles(
        run_id="run-xunfei-1",
        question="product ai judge 讯飞推理模式烟测",
        mode="deep_judge",
        noise_audit=audit,
        path=path,
        generated_at="2026-06-17T00:00:00+00:00",
    )
    persisted = load_model_stability_profiles(path)
    summary = model_stability_summary(store, seats=["xunfei"])
    xunfei = summary["profiles"][0]

    assert persisted["profiles"]["xunfei"]["runs_seen"] == 1
    assert xunfei["seat"] == "xunfei"
    assert xunfei["rates"]["quality_mode_failure_rate"] == 1.0
    assert xunfei["rates"]["refusal_or_auth_rate"] == 1.0
    assert xunfei["average_noise_score"] == 72.0
    assert xunfei["domain_fit"]["product"]["runs"] == 1


def test_model_stability_update_is_idempotent_per_run(tmp_path):
    path = tmp_path / "profiles.json"
    audit = {
        "noise_score": 10,
        "seat_noise_rows": [
            {"seat": "xunfei", "seat_name": "讯飞星火", "valid": True, "confidence": 0.8, "error_code": "", "noise_flags": []},
        ],
    }

    update_model_stability_profiles(run_id="same-run", question="product", mode="standard", noise_audit=audit, path=path)
    update_model_stability_profiles(run_id="same-run", question="product", mode="standard", noise_audit=audit, path=path)
    store = json.loads(Path(path).read_text(encoding="utf-8"))

    assert store["run_count"] == 1
    assert store["profiles"]["xunfei"]["runs_seen"] == 1
