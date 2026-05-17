#!/usr/bin/env python3
"""Record sponsor requests and manual sponsorship signals."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "growth" / "sponsor_events.jsonl"
STATUS_PATH = ROOT / "growth" / "sponsor_status.md"

EVENT_TYPES = {
    "sponsor_copy_ready",
    "sponsor_request",
    "tier_selected",
    "payment_intent",
    "paid",
    "declined",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def render_status(events: list[dict[str, Any]]) -> str:
    counts = Counter(event["event_type"] for event in events)
    tier_counts = Counter(event.get("tier", "") or "unspecified" for event in events if event["event_type"] in {"sponsor_request", "tier_selected", "payment_intent", "paid"})
    paid_total = sum(float(event.get("amount", 0) or 0) for event in events if event["event_type"] == "paid")

    lines = [
        "# Sponsor Status",
        "",
        "Source: `growth/sponsor_events.jsonl`",
        "",
        "## Funnel",
        "",
        "| Event | Count |",
        "|---|---:|",
    ]
    for event_type in sorted(EVENT_TYPES):
        lines.append(f"| {event_type} | {counts[event_type]} |")
    lines.append(f"| paid_total_usd | {paid_total:.2f} |")

    lines.extend(["", "## Tier Demand", "", "| Tier | Count |", "|---|---:|"])
    for tier, count in sorted(tier_counts.items()):
        lines.append(f"| {tier} | {count} |")

    lines.extend(["", "## Event Log", "", "| Timestamp | Event | Tier | Channel | Amount | Note |", "|---|---|---|---|---:|---|"])
    for event in events:
        note = str(event.get("note", "")).replace("|", "\\|")
        lines.append(
            f"| {event['timestamp']} | {event['event_type']} | {event.get('tier', '')} | "
            f"{event.get('channel', '')} | {float(event.get('amount', 0) or 0):.2f} | {note} |"
        )
    return "\n".join(lines) + "\n"


def write_status(events: list[dict[str, Any]]) -> None:
    STATUS_PATH.write_text(render_status(events), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_type", nargs="?", choices=sorted(EVENT_TYPES))
    parser.add_argument("--tier", default="", help="benchmark-supporter, pro-backer, decision-audit-sponsor, one-time")
    parser.add_argument("--channel", default="", help="email, github, manual, etc.")
    parser.add_argument("--amount", type=float, default=0.0, help="Paid amount in USD for paid events")
    parser.add_argument("--note", default="", help="Short public-safe note")
    parser.add_argument("--timestamp", default=None, help="Override UTC timestamp, ISO-8601")
    parser.add_argument("--dry-run", action="store_true", help="Print the event without writing files")
    parser.add_argument("--refresh-only", action="store_true", help="Regenerate status page without appending an event")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh_only:
        write_status(load_events())
        print(f"Refreshed {STATUS_PATH.relative_to(ROOT)}")
        return

    if not args.event_type:
        raise SystemExit("event_type is required unless --refresh-only is used")

    if args.event_type == "paid" and args.amount <= 0:
        raise SystemExit("--amount must be greater than 0 for paid events")

    event = {
        "timestamp": args.timestamp or utc_now(),
        "event_type": args.event_type,
        "tier": args.tier,
        "channel": args.channel,
        "amount": args.amount,
        "note": args.note,
    }
    if args.dry_run:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
        return

    append_event(event)
    write_status(load_events())
    print(f"Recorded {args.event_type} -> {STATUS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
