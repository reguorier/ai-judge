#!/usr/bin/env python3
"""AI Judge — Unified CLI entry point.

Usage:
    ai-judge license status
    ai-judge jury --question "Is this pricing competitive?"
    ai-judge collect --run latest
    ai-judge verdict --run latest
    ai-judge reflect --date 2026-05-09
    ai-judge list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("AI_JUDGE_ROOT", Path.home() / ".ai-judge"))


def _check_license_or_exit() -> None:
    """Gate: refuse any production command without a valid license."""
    from core.license_validator import validate_license

    status = validate_license()
    if not status.valid:
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(1)


def _run_paid_core(command: str, args: argparse.Namespace) -> int:
    """Delegate production behavior to the paid core package."""
    try:
        from ai_judge_core import commands  # type: ignore[import-untyped]
    except ImportError:
        print(json.dumps({
            "ok": False,
            "error": "paid_core_missing",
            "message": (
                "Production commands require the paid ai-judge-core package. "
                "Install it to run jury, collect, verdict, and reflect commands."
            ),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    runner = getattr(commands, command, None)
    if runner is None:
        print(json.dumps({
            "ok": False,
            "error": "command_missing",
            "message": f"Paid core does not expose command '{command}'.",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return int(runner(args))


def cmd_license(args: argparse.Namespace) -> int:
    """License management."""
    from core.license_validator import activate_license, validate_license

    action = getattr(args, "license_action", "status")
    if action == "activate":
        key = args.key or os.environ.get("LICENSE_KEY", "")
        if not key:
            print("Error: --key required, or set LICENSE_KEY", file=sys.stderr)
            return 2
        status = activate_license(key)
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 0 if status.valid else 1
    else:
        status = validate_license()
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 0 if status.valid else 1


def cmd_jury(args: argparse.Namespace) -> int:
    """Create a jury session."""
    _check_license_or_exit()
    return _run_paid_core("jury", args)


def cmd_collect(args: argparse.Namespace) -> int:
    """Collect answers from AI seats."""
    _check_license_or_exit()
    return _run_paid_core("collect", args)


def cmd_verdict(args: argparse.Namespace) -> int:
    """Generate auditable verdict."""
    _check_license_or_exit()
    return _run_paid_core("verdict", args)


def cmd_reflect(args: argparse.Namespace) -> int:
    """Generate daily reflection log."""
    _check_license_or_exit()
    return _run_paid_core("reflect", args)


def cmd_list(args: argparse.Namespace) -> int:
    """List recent jury runs."""
    _check_license_or_exit()
    return _run_paid_core("list_runs", args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-judge",
        description="Multi-model AI jury system — 9 models deliberate, you hold the gavel.",
    )
    sub = parser.add_subparsers(dest="command")

    # license
    lic = sub.add_parser("license", help="License management")
    lic_sub = lic.add_subparsers(dest="license_action")
    act = lic_sub.add_parser("activate", help="Activate a license key")
    act.add_argument("--key", help="License key (or set LICENSE_KEY env var)")
    act.set_defaults(func=cmd_license)
    st = lic_sub.add_parser("status", help="Check license status")
    st.set_defaults(func=cmd_license)

    # jury
    j = sub.add_parser("jury", help="Create a jury session")
    j.add_argument("--question", required=True, help="The question for the jury")
    j.set_defaults(func=cmd_jury)

    # collect
    c = sub.add_parser("collect", help="Collect answers from AI seats")
    c.add_argument("--run", help="Run ID (default: latest)")
    c.set_defaults(func=cmd_collect)

    # verdict
    v = sub.add_parser("verdict", help="Generate auditable verdict")
    v.add_argument("--run", help="Run ID (default: latest)")
    v.set_defaults(func=cmd_verdict)

    # reflect
    r = sub.add_parser("reflect", help="Generate daily reflection log")
    r.add_argument("--date", help="Date in YYYY-MM-DD (default: today)")
    r.set_defaults(func=cmd_reflect)

    # list
    lc = sub.add_parser("list", help="List recent jury runs")
    lc.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
