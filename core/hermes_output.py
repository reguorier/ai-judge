#!/usr/bin/env python3
"""Build the sanitized AI Judge envelope for Hermes display.

Hermes is a delivery surface, not the final judge. This module reads local
AI Judge run artifacts and emits a compact hermes-output.json envelope.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ai-judge-hermes-output-v1"
OUTPUT_FILE = "hermes-output.json"


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def build_hermes_envelope(run_dir: Path) -> dict[str, Any]:
    """Build a Hermes-compatible output envelope from a run directory.

    The envelope contains: verdict summary, seat consensus map, top claims,
    human recommendation placeholder, and metadata.
    """
    task = _load_json(run_dir / "task-status.json", {})
    claims = _load_json(run_dir / "claim-ledger.json", [])
    verdict_text = ""
    verdict_path = run_dir / "verdict.md"
    if verdict_path.exists():
        verdict_text = verdict_path.read_text(encoding="utf-8")[:3000]

    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(task.get("run_id", run_dir.name)),
        "question": str(task.get("question", "")),
        "timestamp": str(task.get("timestamp", "")),
        "seats_engaged": len(task.get("seats", [])),
        "claims_total": len(claims) if isinstance(claims, list) else 0,
        "consensus_map": _build_consensus_map(claims),
        "top_claims": _extract_top_claims(claims, limit=5),
        "dissent_flags": _extract_dissent(claims),
        "verdict_preview": verdict_text[:800],
        "human_recommendation_placeholder": (
            "State what the user should do next and why."
        ),
    }
    return envelope


def _build_consensus_map(claims: Any) -> dict[str, int]:
    if not isinstance(claims, list):
        return {"consensus": 0, "split": 0, "dissent": 0}
    result = {"consensus": 0, "split": 0, "dissent": 0}
    for c in claims:
        if not isinstance(c, dict):
            continue
        agree = c.get("agree_count", 0)
        total = c.get("total_seats", 9)
        if total == 0:
            continue
        ratio = agree / total
        if ratio >= 0.7:
            result["consensus"] += 1
        elif ratio >= 0.4:
            result["split"] += 1
        else:
            result["dissent"] += 1
    return result


def _extract_top_claims(claims: Any, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(claims, list):
        return []
    scored = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        score = sum([
            c.get("source_authority", 0),
            c.get("evidence_strength", 0),
            c.get("freshness", 0),
            c.get("reproducibility", 0),
            c.get("historical_reliability", 0),
        ])
        scored.append({
            "claim": str(c.get("content", ""))[:200],
            "score": score,
            "agree_count": c.get("agree_count", 0),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def _extract_dissent(claims: Any) -> list[dict[str, Any]]:
    if not isinstance(claims, list):
        return []
    dissents = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        agree = c.get("agree_count", 0)
        total = c.get("total_seats", 9)
        if total > 0 and agree / total < 0.4:
            dissents.append({
                "claim": str(c.get("content", ""))[:200],
                "agree_count": agree,
                "total_seats": total,
                "confidence": c.get("confidence", 0),
            })
    return dissents


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Hermes-compatible output envelope from AI Judge run."
    )
    parser.add_argument("run_dir", help="Path to the run directory")
    parser.add_argument("--write", action="store_true", help="Write hermes-output.json")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"Error: {args.run_dir} is not a directory", flush=True)
        raise SystemExit(1)

    envelope = build_hermes_envelope(run_dir)

    if args.write:
        out_path = run_dir / OUTPUT_FILE
        out_path.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote {out_path}", flush=True)
    else:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
