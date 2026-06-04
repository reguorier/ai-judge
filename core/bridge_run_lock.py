#!/usr/bin/env python3
"""Process-local guard for the fixed Chrome bridge.

The fixed Chrome profile is a shared, stateful resource. Only one long-running
workflow may control the model tabs at a time; otherwise prompts and captures
cross-contaminate each other.
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {}


def try_acquire_bridge_run(kind: str, run_id: str, label: str | None = None) -> dict[str, Any] | None:
    """Try to reserve the fixed Chrome bridge for one workflow."""
    token = uuid.uuid4().hex
    acquired = _LOCK.acquire(blocking=False)
    if not acquired:
        return None
    _STATE.clear()
    _STATE.update({
        "token": token,
        "kind": kind,
        "run_id": run_id,
        "label": label or f"{kind}:{run_id}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_monotonic": time.monotonic(),
    })
    return {"token": token, "kind": kind, "run_id": run_id}


def release_bridge_run(claim: dict[str, Any] | None) -> None:
    """Release the fixed Chrome bridge if this caller owns the current claim."""
    if not claim:
        return
    token = str(claim.get("token") or "")
    if _STATE.get("token") == token:
        _STATE.clear()
        _LOCK.release()


def bridge_run_snapshot() -> dict[str, Any]:
    """Return a user-facing snapshot of the current bridge owner."""
    state = dict(_STATE)
    if not state:
        return {"busy": False}
    elapsed = 0.0
    try:
        elapsed = max(0.0, time.monotonic() - float(state.get("started_monotonic") or 0.0))
    except Exception:
        elapsed = 0.0
    return {
        "busy": True,
        "kind": state.get("kind"),
        "run_id": state.get("run_id"),
        "label": state.get("label"),
        "started_at": state.get("started_at"),
        "elapsed_seconds": round(elapsed, 1),
    }
