#!/usr/bin/env python3
"""
Summarize Demo Readiness
public-demo-readiness-v1.0.0

Reads all demo readiness artifacts and produces a summary report.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def check_file(path: Path, label: str) -> dict:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    return {"label": label, "path": str(path), "exists": exists, "size_bytes": size}


def main():
    product_root = Path(os.path.expanduser("/Users/audimacmini/Library/Application Support/AI Judge"))
    project_root = find_project_root()
    product = product_root / "runtime" / "product"
    demo = product / "demo"
    security = product / "security"
    obs = product / "observability"

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "public-demo-readiness-v1.0.0",
    }

    # --- Files checklist ---
    files = [
        # §4-§5 demo config & whitelist
        check_file(demo / "demo_config.json", "demo_config.json"),
        check_file(demo / "demo_task_whitelist.json", "demo_task_whitelist.json"),
        # §8 error & compliance
        check_file(demo / "demo_failure_messages.json", "demo_failure_messages.json"),
        check_file(demo / "demo_privacy_notice.md", "demo_privacy_notice.md"),
        check_file(demo / "demo_disclaimer.md", "demo_disclaimer.md"),
        check_file(demo / "demo_operator_checklist.md", "demo_operator_checklist.md"),
        # §6 security
        check_file(security / "__init__.py", "security/__init__.py"),
        check_file(security / "rate_limiter.py", "security/rate_limiter.py"),
        check_file(security / "abuse_guard.py", "security/abuse_guard.py"),
        check_file(security / "pii_redactor.py", "security/pii_redactor.py"),
        # §9 replay
        check_file(demo / "demo_replay_manifest.json", "demo_replay_manifest.json"),
        # §11 observability
        check_file(obs / "demo_healthcheck.py", "observability/demo_healthcheck.py"),
        check_file(obs / "demo_telemetry.py", "observability/demo_telemetry.py"),
        # §10 scripts
        check_file(project_root / "scripts" / "run_public_demo_smoke.sh", "scripts/run_public_demo_smoke.sh"),
        check_file(project_root / "scripts" / "build_demo_replay_pack.sh", "scripts/build_demo_replay_pack.sh"),
        check_file(project_root / "scripts" / "verify_demo_safety.sh", "scripts/verify_demo_safety.sh"),
        check_file(project_root / "scripts" / "summarize_demo_readiness.py", "scripts/summarize_demo_readiness.py"),
        # §13 tests
        check_file(project_root / "tests" / "test_demo_config_schema.py", "tests/test_demo_config_schema.py"),
        check_file(project_root / "tests" / "test_demo_task_whitelist.py", "tests/test_demo_task_whitelist.py"),
        check_file(project_root / "tests" / "test_rate_limiter.py", "tests/test_rate_limiter.py"),
        check_file(project_root / "tests" / "test_abuse_guard.py", "tests/test_abuse_guard.py"),
        check_file(project_root / "tests" / "test_pii_redactor.py", "tests/test_pii_redactor.py"),
        check_file(project_root / "tests" / "test_demo_failure_messages.py", "tests/test_demo_failure_messages.py"),
        check_file(project_root / "tests" / "test_demo_replay_pack.py", "tests/test_demo_replay_pack.py"),
        check_file(project_root / "tests" / "test_public_demo_smoke.py", "tests/test_public_demo_smoke.py"),
        # §15 release seal
        check_file(project_root / "RELEASE_SEAL_PUBLIC_DEMO_READINESS_V1.md", "RELEASE_SEAL_PUBLIC_DEMO_READINESS_V1.md"),
    ]

    # Replay sub-files
    replay_base = demo / "replay"
    for replay_name in ["bankruptcy_demo", "homestead_demo", "civil_code_demo"]:
        rdir = replay_base / replay_name
        for fname in [
            "input.json", "final_report.html", "final_report_contract.json",
            "evidence_pack.json", "run_metadata.json", "validation_result.json", "README.md",
        ]:
            files.append(check_file(rdir / fname, f"replay/{replay_name}/{fname}"))

    results["files"] = [f for f in files]

    # Stats
    total = len(files)
    present = sum(1 for f in files if f["exists"])
    missing = total - present
    total_size = sum(f["size_bytes"] for f in files)

    results["summary"] = {
        "total_files_expected": total,
        "files_present": present,
        "files_missing": missing,
        "total_size_bytes": total_size,
        "total_size_human": f"{total_size / 1024:.1f} KB",
        "all_present": missing == 0,
    }

    # --- Demo config validation ---
    config_path = demo / "demo_config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        checks = {
            "demo_enabled": config.get("demo_enabled") is True,
            "fail_closed": config.get("fail_closed") is True,
            "show_disclaimer": config.get("show_disclaimer") is True,
            "require_privacy_notice_ack": config.get("require_privacy_notice_ack") is True,
            "rate_limit_ip_hourly": config.get("max_requests_per_ip_per_hour") == 5,
            "rate_limit_session_daily": config.get("max_requests_per_session_per_day") == 10,
            "max_question_chars": config.get("max_question_chars") == 1200,
            "allow_file_upload_false": config.get("allow_file_upload") is False,
            "allow_sensitive_personal_data_false": config.get("allow_sensitive_personal_data") is False,
            "default_reader_type": config.get("default_reader_type") == "ordinary_user",
        }
        results["config_checks"] = checks
        results["summary"]["config_all_checks_pass"] = all(checks.values())
    else:
        results["config_checks"] = {"error": "demo_config.json not found"}
        results["summary"]["config_all_checks_pass"] = False

    # --- Whitelist validation ---
    whitelist_path = demo / "demo_task_whitelist.json"
    if whitelist_path.exists():
        with open(whitelist_path) as f:
            whitelist = json.load(f)
        tasks = whitelist.get("tasks", [])
        cats = {}
        for t in tasks:
            parts = t.get("id", "").split("-")
            cat = parts[1] if len(parts) >= 2 else "UNKNOWN"
            cats[cat] = cats.get(cat, 0) + 1
        results["whitelist"] = {
            "total_tasks": len(tasks),
            "categories": cats,
            "has_6_tasks": len(tasks) >= 6,
            "has_legal_3": cats.get("LEGAL", 0) >= 3,
            "has_product_1": cats.get("PRODUCT", 0) >= 1,
            "has_audit_1": cats.get("AUDIT", 0) >= 1,
            "has_decision_1": cats.get("DECISION", 0) >= 1,
        }
    else:
        results["whitelist"] = {"error": "whitelist not found"}

    # --- Failure messages count ---
    failure_path = demo / "demo_failure_messages.json"
    if failure_path.exists():
        with open(failure_path) as f:
            fm = json.load(f)
        failures = fm.get("failures", {})
        results["failure_messages"] = {
            "count": len(failures),
            "has_all_10": len(failures) == 10,
            "types": list(failures.keys()),
        }

    # --- Replay pack summary ---
    manifest_path = demo / "demo_replay_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        results["replay_pack"] = {
            "total_replays": len(manifest.get("replays", [])),
            "ids": [r["id"] for r in manifest.get("replays", [])],
        }

    # --- Final verdict ---
    all_good = (
        results["summary"]["all_present"]
        and results["summary"].get("config_all_checks_pass", False)
        and results.get("whitelist", {}).get("has_6_tasks", False)
    )
    results["verdict"] = "PUBLIC_DEMO_READINESS_V1_PASS" if all_good else "PUBLIC_DEMO_READINESS_V1_INCOMPLETE"

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print()
    print(f"Files: {present}/{total} present, {missing} missing, {total_size/1024:.1f} KB total")
    print(f"Config checks: {'ALL PASS' if results['summary'].get('config_all_checks_pass') else 'SOME FAIL'}")
    print(f"Verdict: {results['verdict']}")

    if missing > 0:
        print("\nMissing files:")
        for f in files:
            if not f["exists"]:
                print(f"  - {f['label']}")

    sys.exit(0 if all_good else 1)


if __name__ == "__main__":
    main()