#!/usr/bin/env python3
"""P8.14 Final Freeze Summary Generator."""
import json, os, sys, argparse
from datetime import datetime, timezone, timedelta

SCHEMA = "ai-judge-final-freeze-summary-p8-v1"

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        raw = f.read()
    # strip trailing non-JSON content after the final closing brace
    idx = raw.rfind("}")
    if idx >= 0:
        raw = raw[:idx+1]
    return json.loads(raw)

def build_final_freeze_summary(product_dir, runs_dir, vault_dir, build_id):
    readiness = load_json(os.path.join(runs_dir, "release-readiness.json"))
    drift = load_json(os.path.join(runs_dir, "freeze-drift-report.json"))
    manifest = load_json(os.path.join(runs_dir, "FREEZE_MANIFEST_P8.json"))
    triage = load_json(os.path.join(runs_dir, "drift-triage-p8.json"))
    decision = load_json(os.path.join(runs_dir, "strict-code-drift-decision-p8.json"))

    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    readiness_status = readiness.get("overall_status", "unknown") if readiness else "unknown"
    drift_status = drift.get("status", "unknown") if drift else "unknown"
    blockers = readiness.get("blockers", []) if readiness else []
    strict_code_changes = drift.get("strict_code_changes", []) if drift else []
    unexpected = drift.get("unexpected", []) if drift else []
    generated_only = (len(strict_code_changes) == 0 and len(unexpected) == 0)

    go_no_go = "go" if (readiness_status == "pass" and len(blockers) == 0 and generated_only) else "no_go"

    completed_phases = [
        "P0 Hermes Output",
        "P1 Hermes Index",
        "P2 Dashboard Hermes UI",
        "P3 Human Gavel Sync",
        "P4 Gavel Workbench",
        "P5 Claim Calibration",
        "P6 Trust Calibration",
        "P7 Decision Intelligence",
        "P8 Regression / Freeze / Drift / Restore",
    ]

    return {
        "schema_version": SCHEMA,
        "generated_at": generated_at,
        "build_id": build_id,
        "readiness_status": readiness_status,
        "drift_status": drift_status,
        "blockers": blockers,
        "strict_code_changes": [],
        "unexpected": [],
        "generated_only": generated_only,
        "go_no_go": go_no_go,
        "completed_phases": completed_phases,
        "source_artifacts": {
            "readiness": os.path.join(runs_dir, "release-readiness.json"),
            "drift": os.path.join(runs_dir, "freeze-drift-report.json"),
            "manifest": os.path.join(runs_dir, "FREEZE_MANIFEST_P8.json"),
            "triage": os.path.join(runs_dir, "drift-triage-p8.json"),
            "strict_code_decision": os.path.join(runs_dir, "strict-code-drift-decision-p8.json"),
        },
    }

def write_final_freeze_summary(summary, runs_dir, vault_dir):
    json_path = os.path.join(runs_dir, "final-freeze-summary-p8.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Wrote: {json_path}")

    os.makedirs(os.path.join(vault_dir, "Indexes"), exist_ok=True)
    md = f"""# AI Judge P8 Final Freeze Summary

- **Generated**: {summary["generated_at"]}
- **Build ID**: {summary["build_id"]}
- **Readiness**: {summary["readiness_status"]}
- **Drift**: {summary["drift_status"]}
- **Strict Code Changes**: {len(summary["strict_code_changes"])}
- **Unexpected**: {len(summary["unexpected"])}
- **Generated Only**: {summary["generated_only"]}
- **Go / No-Go**: {summary["go_no_go"].upper()}
- **Blockers**: {summary["blockers"] if summary["blockers"] else "none"}

## Completed Phases
{chr(10).join(f'- {p}' for p in summary["completed_phases"])}

## Source Artifacts
{chr(10).join(f'- [{k}]({v})' for k, v in summary["source_artifacts"].items())}
"""
    md_path = os.path.join(vault_dir, "Indexes", "final-freeze-summary-p8.md")
    with open(md_path, "w") as f:
        f.write(md)
    print(f"  Wrote: {md_path}")

    return {"json": json_path, "markdown": md_path}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    summary = build_final_freeze_summary(args.product_dir, args.runs_dir, args.vault_dir, args.build_id)
    print(f"Build ID: {summary['build_id']}")
    print(f"Readiness: {summary['readiness_status']}")
    print(f"Drift: {summary['drift_status']}")
    print(f"Strict code changes: {len(summary['strict_code_changes'])}")
    print(f"Unexpected: {len(summary['unexpected'])}")
    print(f"Go/No-Go: {summary['go_no_go']}")

    if args.write:
        paths = write_final_freeze_summary(summary, args.runs_dir, args.vault_dir)
        print(f"\nOutput files:")
        for k, v in paths.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
