#!/usr/bin/env python3
"""Record outreach sends, replies, bounces, and conversion signals."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "growth" / "outreach_batch_001.json"
EVENTS_PATH = ROOT / "growth" / "outreach_events.jsonl"
STATUS_PATH = ROOT / "growth" / "outreach_status.md"

EVENT_TYPES = {
    "prepared",
    "sent",
    "reply",
    "bounce",
    "benchmark_case",
    "pro_signal",
    "paid_signal",
    "closed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_queue() -> dict[str, Any]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def load_events() -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(EVENTS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{EVENTS_PATH}:{line_number}: invalid JSON: {exc}") from exc
    return events


def append_event(event: dict[str, Any]) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def latest_status_by_target(events: list[dict[str, Any]]) -> dict[str, str]:
    status: dict[str, str] = {}
    for event in events:
        target_id = event["target_id"]
        event_type = event["event_type"]
        if event_type in {"prepared", "sent", "reply", "bounce", "benchmark_case", "pro_signal", "paid_signal", "closed"}:
            status[target_id] = event_type
    return status


def render_status(queue: dict[str, Any], events: list[dict[str, Any]]) -> str:
    targets = {target["id"]: target for target in queue["targets"]}
    counts = Counter(event["event_type"] for event in events)
    status_by_target = latest_status_by_target(events)
    events_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_target[event["target_id"]].append(event)

    lines = [
        "# Outreach Status",
        "",
        f"Batch: `{queue['batch_id']}`",
        "Source: `growth/outreach_events.jsonl`",
        "",
        "## Funnel",
        "",
        "| Event | Count |",
        "|---|---:|",
    ]
    for event_type in sorted(EVENT_TYPES):
        lines.append(f"| {event_type} | {counts[event_type]} |")

    lines.extend(
        [
            "",
            "## Target Status",
            "",
            "| ID | Target | To | Latest status | Last event | Next action |",
            "|---|---|---|---|---|---|",
        ]
    )

    for target in queue["targets"]:
        target_events = events_by_target[target["id"]]
        latest = target_events[-1] if target_events else None
        latest_status = status_by_target.get(target["id"], "ready_to_send")
        last_event = latest["timestamp"] if latest else "none"
        next_action = infer_next_action(latest_status)
        lines.append(
            f"| {target['id']} | {target['target']} | `{target['to']}` | {latest_status} | {last_event} | {next_action} |"
        )

    lines.extend(["", "## Event Log", "", "| Timestamp | Target | Event | Channel | Note |", "|---|---|---|---|---|"])
    for event in events:
        target = targets.get(event["target_id"], {})
        note = str(event.get("note", "")).replace("|", "\\|")
        lines.append(
            f"| {event['timestamp']} | {event['target_id']} {target.get('target', '')} | {event['event_type']} | {event.get('channel', '')} | {note} |"
        )

    return "\n".join(lines) + "\n"


def infer_next_action(status: str) -> str:
    if status == "ready_to_send":
        return "Send first-touch email."
    if status == "prepared":
        return "Open compose link or `.eml` draft."
    if status == "sent":
        return "Wait 3-5 days, then follow up once."
    if status == "reply":
        return "Classify reply as benchmark, pro, paid, or closed."
    if status == "bounce":
        return "Find replacement channel."
    if status == "benchmark_case":
        return "Request anonymization permission and add fixture."
    if status == "pro_signal":
        return "Ask which paid workflow matters first."
    if status == "paid_signal":
        return "Offer AI Decision Audit scope and price."
    return "No action."


def write_status(queue: dict[str, Any], events: list[dict[str, Any]]) -> None:
    STATUS_PATH.write_text(render_status(queue, events), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_type", nargs="?", choices=sorted(EVENT_TYPES))
    parser.add_argument("target_id", nargs="?", help="Target ID such as O001")
    parser.add_argument("--channel", default="", help="Channel used, for example qq-mail, email, contact-form")
    parser.add_argument("--note", default="", help="Short outcome note")
    parser.add_argument("--timestamp", default=None, help="Override UTC timestamp, ISO-8601")
    parser.add_argument("--dry-run", action="store_true", help="Print the event without writing files")
    parser.add_argument("--refresh-only", action="store_true", help="Regenerate status page without appending an event")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queue = load_queue()
    if args.refresh_only:
        write_status(queue, load_events())
        print(f"Refreshed {STATUS_PATH.relative_to(ROOT)}")
        return

    if not args.event_type or not args.target_id:
        raise SystemExit("event_type and target_id are required unless --refresh-only is used")

    target_ids = {target["id"] for target in queue["targets"]}
    if args.target_id not in target_ids:
        raise SystemExit(f"Unknown target_id `{args.target_id}`. Known: {', '.join(sorted(target_ids))}")

    event = {
        "timestamp": args.timestamp or utc_now(),
        "target_id": args.target_id,
        "event_type": args.event_type,
        "channel": args.channel,
        "note": args.note,
    }

    if args.dry_run:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
        return

    append_event(event)
    write_status(queue, load_events())
    print(f"Recorded {args.event_type} for {args.target_id} -> {STATUS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
