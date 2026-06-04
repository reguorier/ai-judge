"""
Hermes Index & Aggregation Layer (P1)
Builds a global run index from hermes-output.json files across all runs,
including seat-level, weekly, status, and confidence aggregations.
Writes hermes-index.json (machine-readable) and Obsidian vault notes.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def _load_human_gavel_slim(run_dir: Path) -> dict[str, Any]:
    """Load slim human_gavel fields from human-gavel.json, or return empty defaults.

    P4 extension: also returns has_conflict, history_count,
    accepted_count, rejected_count.
    """
    gavel_file = run_dir / "human-gavel.json"
    data = _load_json(gavel_file)
    if not data:
        return {
            "status": "",
            "decision": "",
            "confidence": None,
            "reviewed_at": "",
            "has_conflict": False,
            "history_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        }

    # P4: conflict info
    conflict = data.get("conflict", {})
    has_conflict = conflict.get("has_conflict", False) if isinstance(conflict, dict) else False

    # P4: claim review counts
    claim_review = data.get("claim_review", {})
    accepted_count = len(claim_review.get("accepted", [])) if isinstance(claim_review, dict) else 0
    rejected_count = len(claim_review.get("rejected", [])) if isinstance(claim_review, dict) else 0

    # P4: history count
    hist_path = run_dir / "human-gavel-history.jsonl"
    history_count = 0
    if hist_path.exists():
        try:
            history_count = len(hist_path.read_text(encoding="utf-8").strip().splitlines())
        except Exception:
            history_count = 0

    return {
        "status": data.get("status", ""),
        "decision": data.get("decision", ""),
        "confidence": data.get("confidence"),
        "reviewed_at": data.get("reviewed_at", ""),
        "has_conflict": has_conflict,
        "history_count": history_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
    }


def _load_claim_calibration_slim(run_dir: Path) -> dict[str, Any]:
    """Load slim claim_calibration fields from claim-calibration.json, or return defaults."""
    cal_file = run_dir / "claim-calibration.json"
    data = _load_json(cal_file)
    if not data:
        return {
            "status": "none",
            "accepted_count": 0,
            "rejected_count": 0,
            "unmatched_count": 0,
            "claim_count": 0,
            "updated_at": "",
        }

    n_accepted = len(data.get("accepted", []))
    n_rejected = len(data.get("rejected", []))
    n_unmatched = len(data.get("unmatched", []))
    claim_count = data.get("claim_count", n_accepted + n_rejected + n_unmatched)

    status = "ready"
    if n_unmatched > 0:
        status = "warning"

    return {
        "status": status,
        "accepted_count": n_accepted,
        "rejected_count": n_rejected,
        "unmatched_count": n_unmatched,
        "claim_count": claim_count,
        "updated_at": data.get("generated_at", ""),
    }


def _iso_week(dt_str: str | None) -> str | None:
    """Convert ISO timestamp to YYYY-WW format."""
    if not dt_str:
        return None
    try:
        # Try ISO format with timezone
        ts = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except Exception:
        return None


def build_hermes_index(runs_dir: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    """Scan runs_dir for all */hermes-output.json, build global index."""
    runs: list[dict[str, Any]] = []
    seat_runs: dict[str, list[dict[str, Any]]] = {}
    weekly_runs: dict[str, list[dict[str, Any]]] = {}
    status_counts: dict[str, int] = {}
    confidence_values: list[float] = []
    evidence_gaps: list[dict[str, Any]] = []

    for hermes_file in sorted(runs_dir.glob("*/hermes-output.json")):
        data = _load_json(hermes_file)
        if not data:
            continue

        run_id = data.get("run_id", "") or hermes_file.parent.name
        created_at = data.get("generated_at", None)

        # Try to get created_at from verdict.json as well
        verdict = _load_json(hermes_file.parent / "verdict.json")
        if verdict and verdict.get("created_at"):
            created_at = verdict["created_at"]

        question = data.get("question", None)
        status = data.get("status", "unknown")
        confidence = data.get("confidence", None)
        seat_names = []
        seats_raw = data.get("seats", [])
        if isinstance(seats_raw, list):
            for s in seats_raw:
                if isinstance(s, dict):
                    name = s.get("name", s.get("seat_id", s.get("label", "")))
                elif isinstance(s, str):
                    name = s
                else:
                    name = ""
                if name:
                    seat_names.append(name)

        # Tags: from verdict mode or seat_roster
        tags: list[str] = []
        mode = data.get("mode", "")
        if verdict:
            mode = verdict.get("mode", mode)
        if mode:
            tags.append(mode)

        # Obsidian note path
        obsidian_note: str | None = None
        if vault_dir and created_at:
            try:
                ts = created_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
                note_path = vault_dir / "Runs" / str(dt.year) / f"{dt.month:02d}" / f"Run {run_id}.md"
                if note_path.exists():
                    obsidian_note = str(note_path)
            except Exception:
                pass

        run_entry: dict[str, Any] = {
            "run_id": run_id,
            "created_at": created_at,
            "question": question,
            "status": status,
            "confidence": confidence,
            "seat_count": len(seat_names),
            "seats": seat_names,
            "view_url": f"/api/runs/{run_id}/index.html",
            "hermes_json": f"/api/runs/{run_id}/hermes-output.json",
            "obsidian_note": obsidian_note,
            "tags": tags,
            "human_gavel": _load_human_gavel_slim(hermes_file.parent),
            "claim_calibration": _load_claim_calibration_slim(hermes_file.parent),
        }
        runs.append(run_entry)

        # Status counts
        status_counts[status] = status_counts.get(status, 0) + 1

        # Confidence tracking
        if isinstance(confidence, (int, float)):
            confidence_values.append(float(confidence))

        # Evidence gaps
        gaps = data.get("evidence_gaps", [])
        if gaps:
            for g in gaps:
                if isinstance(g, dict):
                    evidence_gaps.append({
                        "run_id": run_id,
                        "gap": g,
                    })

        # Per-seat aggregation
        for sname in seat_names:
            seat_runs.setdefault(sname, []).append(run_entry)

        # Per-week aggregation
        week = _iso_week(created_at)
        if week:
            weekly_runs.setdefault(week, []).append(run_entry)

    # --- Seat summary ---
    seat_summary: dict[str, dict[str, Any]] = {}
    for seat_id, s_runs in seat_runs.items():
        confs = [r["confidence"] for r in s_runs if isinstance(r["confidence"], (int, float))]
        avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
        high_conf = sum(1 for c in confs if c >= 80)
        low_conf = sum(1 for c in confs if c < 50)
        recent = sorted(s_runs, key=lambda r: r.get("created_at") or "", reverse=True)[:5]
        seat_summary[seat_id] = {
            "total_runs": len(s_runs),
            "avg_confidence": avg_conf,
            "high_confidence_runs": high_conf,
            "low_confidence_runs": low_conf,
            "recent_run_ids": [r["run_id"] for r in recent],
        }

    # --- Weekly summary ---
    weekly_summary: dict[str, dict[str, Any]] = {}
    for week_label, w_runs in weekly_runs.items():
        confs = [r["confidence"] for r in w_runs if isinstance(r["confidence"], (int, float))]
        avg_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
        # Top seats by run count
        seat_counter: dict[str, int] = {}
        for r in w_runs:
            for s in r.get("seats", []):
                seat_counter[s] = seat_counter.get(s, 0) + 1
        top_seats = [s for s, _ in sorted(seat_counter.items(), key=lambda x: -x[1])[:3]]
        # Low confidence runs
        low_conf_runs = [r["run_id"] for r in w_runs if isinstance(r.get("confidence"), (int, float)) and r["confidence"] < 50]
        # Key questions
        key_qs = [r["question"] for r in w_runs if r.get("question")][:5]
        weekly_summary[week_label] = {
            "week_label": week_label,
            "run_count": len(w_runs),
            "avg_confidence": avg_conf,
            "top_seats": top_seats,
            "low_confidence_runs": low_conf_runs,
            "key_questions": key_qs,
        }

    # --- Confidence summary ---
    conf_summary: dict[str, Any] = {
        "avg": 0.0,
        "max": 0.0,
        "min": 0.0,
        "buckets": {"高(≥80)": 0, "中(50-79)": 0, "低(<50)": 0},
    }
    if confidence_values:
        conf_summary["avg"] = round(sum(confidence_values) / len(confidence_values), 2)
        conf_summary["max"] = round(max(confidence_values), 2)
        conf_summary["min"] = round(min(confidence_values), 2)
        conf_summary["buckets"]["高(≥80)"] = sum(1 for c in confidence_values if c >= 80)
        conf_summary["buckets"]["中(50-79)"] = sum(1 for c in confidence_values if 50 <= c < 80)
        conf_summary["buckets"]["低(<50)"] = sum(1 for c in confidence_values if c < 50)

    return {
        "schema_version": "ai-judge-hermes-index-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": len(runs),
        "runs": runs,
        "seat_summary": seat_summary,
        "weekly_summary": weekly_summary,
        "status_summary": status_counts,
        "confidence_summary": conf_summary,
        "evidence_gaps": evidence_gaps,
    }


def write_hermes_index(runs_dir: Path, vault_dir: Path | None = None) -> dict[str, Any]:
    """Build index and write hermes-index.json + Obsidian vault notes."""
    index = build_hermes_index(runs_dir, vault_dir)

    runs_dir = Path(runs_dir)

    # 1. Write hermes-index.json
    index_json_path = runs_dir / "hermes-index.json"
    index_json_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not vault_dir:
        return index

    vault_dir = Path(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)

    # 2. Write hermes-index.md
    indexes_dir = vault_dir / "Indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)

    generated_at = index["generated_at"]
    run_count = index["run_count"]
    status_summary = index["status_summary"]
    conf_summary = index["confidence_summary"]
    seat_summary = index["seat_summary"]
    weekly_summary = index["weekly_summary"]
    runs_list = index["runs"]

    # Build status table
    status_table_lines = []
    for st in ["complete", "pending", "failed"]:
        count = status_summary.get(st, 0)
        status_table_lines.append(f"| {st} | {count} |")
    for st, count in sorted(status_summary.items()):
        if st not in ("complete", "pending", "failed"):
            status_table_lines.append(f"| {st} | {count} |")

    # Build seat table
    seat_table_lines = []
    for sid, sdata in sorted(seat_summary.items()):
        seat_table_lines.append(
            f"| {sid} | {sdata['total_runs']} | {sdata['avg_confidence']} | "
            f"{sdata['high_confidence_runs']} | {sdata['low_confidence_runs']} |"
        )

    # Build recent runs table
    recent_runs = sorted(runs_list, key=lambda r: r.get("created_at") or "", reverse=True)[:20]
    recent_table_lines = []
    for r in recent_runs:
        q = (r.get("question") or "")[:60]
        seats_str = ", ".join(r.get("seats", [])[:3])
        if len(r.get("seats", [])) > 3:
            seats_str += f" +{len(r['seats']) - 3}"
        recent_table_lines.append(
            f"| {r['run_id']} | {q} | {r['status']} | {r['confidence']} | {seats_str} |"
        )

    # Build weekly index links
    weekly_links = []
    for wl in sorted(weekly_summary.keys(), reverse=True):
        ws = weekly_summary[wl]
        weekly_links.append(f"- [[{wl}]]: {ws['run_count']} runs, avg confidence {ws['avg_confidence']}")

    # Build seat index links
    seat_links = [f"- [[{sid}]]" for sid in sorted(seat_summary.keys())]

    hermes_md = f"""---
title: Hermes Index
generated_at: {generated_at}
run_count: {run_count}
tags: [ai-judge, hermes, index]
---

# AI Judge Hermes Index

## 概览
- 总 run 数: {run_count}
- 生成时间: {generated_at}

## 状态分布
| 状态 | 数量 |
|------|------|
{chr(10).join(status_table_lines)}

## 置信度分布
- 平均: {conf_summary['avg']}
- 高(≥80): {conf_summary['buckets']['高(≥80)']} / 中(50-79): {conf_summary['buckets']['中(50-79)']} / 低(<50): {conf_summary['buckets']['低(<50)']}

## 席位参与统计
| 席位 | 参与次数 | 平均置信度 | 高置信度 | 低置信度 |
|------|---------|-----------|---------|---------|
{chr(10).join(seat_table_lines)}

## 最近 Run（最多 20 个）
| Run ID | 问题 | 状态 | 置信度 | 席位 |
|--------|------|------|--------|------|
{chr(10).join(recent_table_lines)}

## 周度索引
{chr(10).join(weekly_links)}

## 席位索引
{chr(10).join(seat_links)}

## 关联
[[AI Judge]]
[[Hermes]]
"""

    (indexes_dir / "hermes-index.md").write_text(hermes_md, encoding="utf-8")

    # 3. Write per-seat notes
    seats_dir = vault_dir / "Seats"
    seats_dir.mkdir(parents=True, exist_ok=True)

    for sid, sdata in sorted(seat_summary.items()):
        # Collect recent runs for this seat with verdict details
        seat_runs = [r for r in runs_list if sid in r.get("seats", [])]
        seat_runs_sorted = sorted(seat_runs, key=lambda r: r.get("created_at") or "", reverse=True)

        seat_run_table_lines = []
        for r in seat_runs_sorted[:10]:
            # Try to get verdict snippet from hermes-output
            hermes = _load_json(runs_dir / r["run_id"] / "hermes-output.json")
            snippet = ""
            if hermes:
                snippet = (hermes.get("verdict_summary") or "")[:50]
            seat_run_table_lines.append(
                f"| {r['run_id']} | {(r.get('question') or '')[:40]} | {r['confidence']} | {snippet} |"
            )

        seat_md = f"""---
seat_id: {sid}
total_runs: {sdata['total_runs']}
avg_confidence: {sdata['avg_confidence']}
high_confidence_runs: {sdata['high_confidence_runs']}
low_confidence_runs: {sdata['low_confidence_runs']}
tags: [ai-judge, hermes, seat]
---

# Seat: {sid}

## 统计
- 参与 run 数: {sdata['total_runs']}
- 平均置信度: {sdata['avg_confidence']}
- 高置信度(≥80): {sdata['high_confidence_runs']}
- 低置信度(<50): {sdata['low_confidence_runs']}

## 最近参与 Run
| Run ID | 问题 | 置信度 | 判词 |
|--------|------|--------|------|
{chr(10).join(seat_run_table_lines) if seat_run_table_lines else '| (无) | | | |'}

## 关联
[[AI Judge]]
[[Hermes Index]]
"""
        (seats_dir / f"{sid}.md").write_text(seat_md, encoding="utf-8")

    # 4. Write per-week notes
    for wl, ws in sorted(weekly_summary.items()):
        w_runs = sorted(
            [r for r in runs_list if _iso_week(r.get("created_at")) == wl],
            key=lambda r: r.get("created_at") or "",
            reverse=True,
        )

        top_seat_table = []
        seat_counter: dict[str, int] = {}
        for r in w_runs:
            for s in r.get("seats", []):
                seat_counter[s] = seat_counter.get(s, 0) + 1
        for s, c in sorted(seat_counter.items(), key=lambda x: -x[1])[:5]:
            top_seat_table.append(f"| {s} | {c} |")

        low_conf_table = []
        for r in w_runs:
            if isinstance(r.get("confidence"), (int, float)) and r["confidence"] < 50:
                low_conf_table.append(f"| {r['run_id']} | {(r.get('question') or '')[:50]} | {r['confidence']} |")

        key_qs_table = []
        for r in w_runs:
            if r.get("question"):
                key_qs_table.append(f"| {r['run_id']} | {(r['question'])[:60]} |")
                if len(key_qs_table) >= 10:
                    break

        weekly_md = f"""---
week: {wl}
run_count: {ws['run_count']}
avg_confidence: {ws['avg_confidence']}
top_seats: {json.dumps(ws['top_seats'])}
tags: [ai-judge, hermes, weekly]
---

# Week {wl}

## 概览
- Run 数: {ws['run_count']}
- 平均置信度: {ws['avg_confidence']}

## Top 席位
| 席位 | 参与次数 |
|------|---------|
{chr(10).join(top_seat_table) if top_seat_table else '| (无) | 0 |'}

## 低置信度 Run
| Run ID | 问题 | 置信度 |
|--------|------|--------|
{chr(10).join(low_conf_table) if low_conf_table else '| (无) | | |'}

## 关键议题
| Run ID | 问题 |
|--------|------|
{chr(10).join(key_qs_table) if key_qs_table else '| (无) | |'}

## 关联
[[AI Judge]]
[[Hermes Index]]
"""
        (indexes_dir / f"{wl}.md").write_text(weekly_md, encoding="utf-8")

    return index