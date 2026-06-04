#!/usr/bin/env python3
"""Watchdog for the dedicated AI Judge Chrome CDP bridge."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridges.chrome_cdp_bridge import ensure_chrome_cdp_awake
from bridges.web_seat_bridge import bridge_status, load_bridge_config


def check_once(open_tabs: bool = True) -> dict:
    config = load_bridge_config()
    wake = ensure_chrome_cdp_awake(config, open_tabs=open_tabs)
    status = bridge_status()
    return {
        "ok": bool(wake.get("ok")) and bool(status.get("ready_count", 0) > 0),
        "wake": wake,
        "ready_count": status.get("ready_count"),
        "configured_count": status.get("configured_count"),
        "enabled_count": status.get("enabled_count"),
        "chrome_cdp": status.get("chrome_cdp"),
        "login_state_path": config.get("login_state_path"),
        "profile_dir": config.get("chrome_cdp_profile_dir"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Judge Chrome bridge watchdog")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument("--interval", type=float, default=45, help="Seconds between checks in loop mode.")
    parser.add_argument("--no-open-tabs", action="store_true", help="Only wake Chrome; do not open missing seat tabs.")
    parser.add_argument("--json", action="store_true", help="Print JSON status.")
    args = parser.parse_args()

    def emit(payload: dict) -> None:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        else:
            print(
                f"ok={payload.get('ok')} ready={payload.get('ready_count')}/"
                f"{payload.get('configured_count')} profile={payload.get('profile_dir')}",
                flush=True,
            )

    if not args.loop:
        payload = check_once(open_tabs=not args.no_open_tabs)
        emit(payload)
        return 0 if payload.get("ok") else 2

    exit_code = 0
    while True:
        try:
            payload = check_once(open_tabs=not args.no_open_tabs)
            emit(payload)
            if not payload.get("ok"):
                exit_code = 2
        except Exception as exc:
            exit_code = 2
            emit({"ok": False, "error": str(exc)})
        time.sleep(max(5, args.interval))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
