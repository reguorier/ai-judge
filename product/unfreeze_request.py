#!/usr/bin/env python3
"""P9.0 Unfreeze Request Generator."""
import json, os, argparse
from datetime import datetime, timezone, timedelta

def load_json(path):
    with open(path) as f:
        raw = f.read()
    # Try full parse first; if it fails, trim trailing non-JSON content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Trim trailing garbage: find the last valid JSON structural character
    for end_char in ("}\n", "]\n", "}", "]"):
        idx = raw.rfind(end_char)
        if idx != -1:
            candidate = raw[:idx + len(end_char)]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Unable to parse JSON from {path}")

def evaluate_entry_gate(readiness, drift, seal, manifest_exists):
    readiness_ok = readiness.get("overall_status") == "pass"
    blockers_empty = len(readiness.get("blockers", [])) == 0
    drift_ok = drift.get("status") in ("clean", "generated_only")
    strict_empty = len(drift.get("strict_code_changes", [])) == 0
    unexpected_empty = len(drift.get("unexpected", [])) == 0
    entry_blockers = []
    if not readiness_ok:
        entry_blockers.append("readiness not pass")
    if not blockers_empty:
        entry_blockers.append(f"blockers present: {readiness.get('blockers')}")
    if not drift_ok:
        entry_blockers.append(f"drift not clean/generated_only: {drift.get('status')}")
    if not strict_empty:
        entry_blockers.append(f"strict_code_changes present: {len(drift.get('strict_code_changes', []))}")
    if not unexpected_empty:
        entry_blockers.append(f"unexpected present: {len(drift.get('unexpected', []))}")
    if not manifest_exists:
        entry_blockers.append("freeze manifest missing")
    if not seal:
        entry_blockers.append("operator seal missing")
    approved = len(entry_blockers) == 0
    return approved, entry_blockers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--vault-dir", required=True)
    parser.add_argument("--build-id", default="p8.7-drift-sentinel-e2e-v1")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    readiness = load_json(os.path.join(args.runs_dir, "release-readiness.json"))
    drift = load_json(os.path.join(args.runs_dir, "freeze-drift-report.json"))
    seal_path = os.path.join(args.runs_dir, "final-operator-seal-p8.json")
    manifest_path = os.path.join(args.runs_dir, "FREEZE_MANIFEST_P8.json")
    seal = load_json(seal_path) if os.path.exists(seal_path) else {}
    manifest_exists = os.path.exists(manifest_path)

    approved, entry_blockers = evaluate_entry_gate(readiness, drift, seal, manifest_exists)

    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    assessment = {
        "schema_version": "ai-judge-p9-change-impact-assessment-v1",
        "generated_at": generated_at,
        "baseline_build_id": args.build_id,
        "readiness_status": readiness.get("overall_status"),
        "drift_status": drift.get("status"),
        "proposed_scope": [],
        "affected_files": [],
        "affected_apis": [],
        "risk_level": "low",
        "entry_blockers": entry_blockers,
        "entry_decision": "approved" if approved else "blocked",
        "required_regression": [
            "release_readiness",
            "regression_harness",
            "freeze_drift_sentinel",
            "operator_handoff"
        ]
    }

    request = {
        "schema_version": "ai-judge-p9-unfreeze-request-v1",
        "generated_at": generated_at,
        "baseline_build_id": args.build_id,
        "baseline_product_version": seal.get("product_version", "3.8.0-p8.7-drift-sentinel-e2e-v1"),
        "readiness_status": readiness.get("overall_status"),
        "drift_status": drift.get("status"),
        "blockers": readiness.get("blockers", []),
        "strict_code_changes": [],
        "unexpected": [],
        "go_no_go": seal.get("go_no_go", "GO"),
        "entry_decision": "approved" if approved else "blocked",
        "entry_blockers": entry_blockers,
        "reason": "No concrete feature request yet. This P9.0 only opens the governance gate and does not authorize coding.",
        "proposed_theme": "Operational Intelligence / Maintenance UX / Controlled Extensions",
        "allowed_changes": [
            "add P9 documentation and scripts",
            "add new P9 feature modules (no P0-P8 modification)",
            "extend dashboard with P9-only UI components",
            "add new API routes under /p9/ prefix"
        ],
        "forbidden_without_new_approval": [
            "modify P0-P8 core modules",
            "change BUILD_ID or refresh freeze manifest",
            "delete or alter runs/ or vault/ data",
            "modify existing API schema or routes",
            "bypass trace-based UI acceptance",
            "mark unknown drift as intentional without triage"
        ]
    }

    print(f"Readiness: {readiness.get('overall_status')}")
    print(f"Drift: {drift.get('status')}")
    print(f"Blockers: {readiness.get('blockers', [])}")
    print(f"Strict code changes: {len(drift.get('strict_code_changes', []))}")
    print(f"Unexpected: {len(drift.get('unexpected', []))}")
    print(f"Entry decision: {'approved' if approved else 'blocked'}")
    if entry_blockers:
        for b in entry_blockers:
            print(f"  - {b}")

    if args.write:
        os.makedirs(args.runs_dir, exist_ok=True)
        req_path = os.path.join(args.runs_dir, "unfreeze-request-p9.json")
        with open(req_path, "w") as f:
            json.dump(request, f, indent=2)
        print(f"Wrote: {req_path}")

        imp_path = os.path.join(args.runs_dir, "p9-change-impact-assessment.json")
        with open(imp_path, "w") as f:
            json.dump(assessment, f, indent=2)
        print(f"Wrote: {imp_path}")

        os.makedirs(os.path.join(args.vault_dir, "Indexes"), exist_ok=True)
        vault_md = f"""# AI Judge P9 Unfreeze Request

- **Generated**: {generated_at}
- **Build ID**: {args.build_id}
- **Readiness**: {readiness.get('overall_status')}
- **Drift**: {drift.get('status')}
- **Entry Decision**: {'APPROVED' if approved else 'BLOCKED'}
- **Entry Blockers**: {entry_blockers if entry_blockers else 'none'}

## Reason
No concrete feature request yet. Governance gate only.

## Allowed
- P9 documentation and scripts
- New P9 feature modules (no P0-P8 modification)
- Dashboard P9-only UI components
- New API routes under /p9/ prefix

## Forbidden
- Modify P0-P8 core modules
- Change BUILD_ID or refresh manifest
- Delete runs/vault data
- Modify existing API schema/routes
"""
        vault_path = os.path.join(args.vault_dir, "Indexes", "unfreeze-request-p9.md")
        with open(vault_path, "w") as f:
            f.write(vault_md)
        print(f"Wrote: {vault_path}")

if __name__ == "__main__":
    main()
# (content generated by AI, for reference only)
