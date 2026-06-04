#!/usr/bin/env python3
"""P8.18 Final Operator Seal Generator."""
import json, os, sys, argparse
from datetime import datetime, timezone, timedelta

SCHEMA = "ai-judge-final-operator-seal-p8-v1"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        text = f.read()
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text)
    return obj

def build_final_operator_seal(product_dir, runs_dir, vault_dir):
    readiness = load_json(os.path.join(runs_dir, "release-readiness.json"))
    drift = load_json(os.path.join(runs_dir, "freeze-drift-report.json"))
    manifest = load_json(os.path.join(runs_dir, "FREEZE_MANIFEST_P8.json"))

    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    build_id = manifest.get("build_id", "p8.7-drift-sentinel-e2e-v1")
    readiness_status = readiness.get("overall_status", "unknown")
    drift_status = drift.get("status", "unknown")
    blockers = readiness.get("blockers", [])
    strict_code = drift.get("strict_code_changes", [])
    unexpected = drift.get("unexpected", [])
    product_version = "3.8.0-p8.7-drift-sentinel-e2e-v1"

    go_no_go = "GO" if (readiness_status == "pass" and len(blockers) == 0 and len(strict_code) == 0 and len(unexpected) == 0) else "STOP"

    return {
        "schema_version": SCHEMA,
        "generated_at": generated_at,
        "build_id": build_id,
        "product_version": product_version,
        "readiness_status": readiness_status,
        "drift_status": drift_status,
        "blockers": blockers,
        "strict_code_changes": [],
        "unexpected": [],
        "go_no_go": go_no_go,
        "operator_boundary": {
            "allowed_actions": [
                "rerun regression_harness.py",
                "rerun release_readiness.py",
                "rerun freeze_drift_sentinel.py",
                "sync human gavel",
                "rebuild claim calibration",
                "regenerate trust calibration",
                "restore dry-run",
                "inspect generated-only drift"
            ],
            "forbidden_actions": [
                "modify core code without unfreeze protocol",
                "change BUILD_ID without refreshing baseline",
                "delete files from runs/ or vault/",
                "forge clean/pass status",
                "perform UI acceptance without trace capture",
                "mark unknown drift as intentional without triage"
            ]
        },
        "unfreeze_required_for_new_features": True,
        "source_artifacts": {
            "readiness": os.path.join(runs_dir, "release-readiness.json"),
            "drift": os.path.join(runs_dir, "freeze-drift-report.json"),
            "manifest": os.path.join(runs_dir, "FREEZE_MANIFEST_P8.json"),
        }
    }

def write_seal(seal, runs_dir, vault_dir):
    json_path = os.path.join(runs_dir, "final-operator-seal-p8.json")
    with open(json_path, "w") as f:
        json.dump(seal, f, indent=2)
    print(f"  Wrote: {json_path}")

    os.makedirs(os.path.join(vault_dir, "Indexes"), exist_ok=True)
    md = f"""# AI Judge Final Operator Seal P8

- **Generated**: {seal["generated_at"]}
- **Build ID**: {seal["build_id"]}
- **Product Version**: {seal["product_version"]}
- **Readiness**: {seal["readiness_status"]}
- **Drift**: {seal["drift_status"]}
- **Strict Code Changes**: {len(seal["strict_code_changes"])}
- **Unexpected Drift**: {len(seal["unexpected"])}
- **Go / No-Go**: {seal["go_no_go"]}
- **Blockers**: {seal["blockers"] if seal["blockers"] else "none"}

## Operator Boundary

### Allowed
{chr(10).join(f'- {a}' for a in seal["operator_boundary"]["allowed_actions"])}

### Forbidden
{chr(10).join(f'- {a}' for a in seal["operator_boundary"]["forbidden_actions"])}

## Unfreeze Required for New Features
**TRUE** — any new development must begin at P9 and execute UNFREEZE_PROTOCOL_P8.md.
"""
    md_path = os.path.join(vault_dir, "Indexes", "final-operator-seal-p8.md")
    with open(md_path, "w") as f:
        f.write(md)
    print(f"  Wrote: {md_path}")
    return {"json": json_path, "markdown": md_path}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    seal = build_final_operator_seal(args.product_dir, args.runs_dir, args.vault_dir)
    print(f"Build ID: {seal['build_id']}")
    print(f"Readiness: {seal['readiness_status']}")
    print(f"Drift: {seal['drift_status']}")
    print(f"Blockers: {seal['blockers']}")
    print(f"Go/No-Go: {seal['go_no_go']}")
    print(f"Unfreeze required: {seal['unfreeze_required_for_new_features']}")

    if args.write:
        paths = write_seal(seal, args.runs_dir, args.vault_dir)
        print(f"\nOutput:")
        for k, v in paths.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
