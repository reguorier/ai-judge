#!/usr/bin/env python3
"""Track the three free AI Decision Audit slots."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SLOTS_PATH = ROOT / "growth" / "free_audit_slots.json"
STATUS_PATH = ROOT / "growth" / "free_audit_status.md"

STATUSES = {
    "open",
    "reserved",
    "input_received",
    "audit_complete",
    "permission_requested",
    "testimonial_granted",
    "closed",
}

PERMISSION_STATUSES = {"not_requested", "pending", "granted", "declined"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_slots() -> dict[str, Any]:
    return json.loads(SLOTS_PATH.read_text(encoding="utf-8"))


def write_slots(slots: dict[str, Any]) -> None:
    SLOTS_PATH.write_text(json.dumps(slots, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def find_slot(slots: dict[str, Any], slot_id: str) -> dict[str, Any]:
    for slot in slots["slots"]:
        if slot["slot_id"] == slot_id:
            return slot
    known = ", ".join(slot["slot_id"] for slot in slots["slots"])
    raise SystemExit(f"Unknown slot_id `{slot_id}`. Known: {known}")


def render_status(slots: dict[str, Any]) -> str:
    open_count = sum(1 for slot in slots["slots"] if slot["status"] == "open")
    reserved_count = sum(1 for slot in slots["slots"] if slot["status"] in {"reserved", "input_received"})
    completed_count = sum(1 for slot in slots["slots"] if slot["status"] in {"audit_complete", "permission_requested", "testimonial_granted", "closed"})
    testimonial_count = sum(1 for slot in slots["slots"] if slot["permission_status"] == "granted")

    lines = [
        "# Free AI Decision Audit Slot Status",
        "",
        f"Offer: `{slots['offer_id']}`",
        "Source: `growth/free_audit_slots.json`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Open slots | {open_count} |",
        f"| Reserved/in progress | {reserved_count} |",
        f"| Completed/closed | {completed_count} |",
        f"| Testimonial permissions granted | {testimonial_count} |",
        "",
        "## Slots",
        "",
        "| Slot | Status | Contact ref | Case type | Permission | Report | Note |",
        "|---|---|---|---|---|---|---|",
    ]

    for slot in slots["slots"]:
        note = str(slot.get("note", "")).replace("|", "\\|")
        lines.append(
            f"| {slot['slot_id']} | {slot['status']} | {slot.get('contact_ref', '')} | {slot.get('case_type', '')} | "
            f"{slot.get('permission_status', '')} | {slot.get('report_path', '')} | {note} |"
        )

    return "\n".join(lines) + "\n"


def write_status(slots: dict[str, Any]) -> None:
    STATUS_PATH.write_text(render_status(slots), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slot_id", nargs="?", help="Slot ID, for example F001")
    parser.add_argument("--status", choices=sorted(STATUSES), help="New slot status")
    parser.add_argument("--contact", default=None, help="Contact reference, for example O001 or email/domain")
    parser.add_argument("--case-type", default=None, help="memo, report, README, investment memo, product plan, etc.")
    parser.add_argument("--permission", choices=sorted(PERMISSION_STATUSES), default=None)
    parser.add_argument("--report", default=None, help="Report path after completion")
    parser.add_argument("--note", default=None, help="Short public-safe note")
    parser.add_argument("--refresh-only", action="store_true", help="Regenerate status page without changing slot data")
    parser.add_argument("--dry-run", action="store_true", help="Print updated JSON without writing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    slots = load_slots()

    if args.refresh_only:
        write_status(slots)
        print(f"Refreshed {STATUS_PATH.relative_to(ROOT)}")
        return

    if not args.slot_id or not args.status:
        raise SystemExit("slot_id and --status are required unless --refresh-only is used")

    slot = find_slot(slots, args.slot_id)
    slot["status"] = args.status
    if args.contact is not None:
        slot["contact_ref"] = args.contact
    if args.case_type is not None:
        slot["case_type"] = args.case_type
    if args.permission is not None:
        slot["permission_status"] = args.permission
    if args.report is not None:
        slot["report_path"] = args.report
    if args.note is not None:
        slot["note"] = args.note
    slot["updated_at"] = utc_now()

    if args.dry_run:
        print(json.dumps(slots, ensure_ascii=False, indent=2))
        return

    write_slots(slots)
    write_status(slots)
    print(f"Updated {args.slot_id} -> {STATUS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
