#!/usr/bin/env python3
"""Process-local guard for the fixed Chrome bridge.

The fixed Chrome profile is a shared, stateful resource. Only one long-running
workflow may control the model tabs at a time; otherwise prompts and captures
cross-contaminate each other.

P1.9: Added FIFO queue for bridge-constrained judge runs. When the bridge is
busy, new submissions can join a queue and be auto-started when the bridge
becomes free.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {}
_QUEUE: deque[dict[str, Any]] = deque()
_MAX_QUEUE_SIZE = 10


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
    queued = list(_QUEUE)
    if not state:
        return {
            "busy": False,
            "queued_count": len(queued),
            "can_start_new_run": True,
        }
    elapsed = 0.0
    try:
        elapsed = max(0.0, time.monotonic() - float(state.get("started_monotonic") or 0.0))
    except Exception:
        elapsed = 0.0
    return {
        "busy": True,
        "kind": state.get("kind"),
        "run_id": state.get("run_id"),
        "active_run_id": state.get("run_id"),
        "label": state.get("label"),
        "since": state.get("started_at"),
        "started_at": state.get("started_at"),
        "elapsed_seconds": round(elapsed, 1),
        "queued_count": len(queued),
        "can_start_new_run": False,
        "recoverable": elapsed > 60.0,  # P2.7: stuck if running > 60s
        "current_phase": state.get("phase", "running"),
        "last_cdp_phase": state.get("last_cdp_phase", "idle"),  # P2.9
        "current_seat": state.get("current_seat"),  # P2.7: propagated from set_bridge_phase()
    }


# ── P2.7: Bridge Stuck Recovery ────────────────────────────────────────


def set_bridge_phase(phase: str, current_seat: str | None = None) -> None:
    """P2.7: Update bridge phase and current seat in the lock state.

    Callable from worker thread while bridge lock is held. Updates
    _STATE['phase'] and optionally _STATE['current_seat']. Used by
    bridge_run_snapshot() to expose progress to /api/bridge/status.
    """
    import json, traceback
    try:
        _STATE["phase"] = phase
        if current_seat:
            _STATE["current_seat"] = current_seat
        # P2.9: track last CDP subphase for recovery diagnostics
        if any(phase.startswith(p) for p in ("cdp_", "seat_submit_", "seat_answered", "seat_answer_")):
            _STATE["last_cdp_phase"] = phase
    except Exception:
        pass  # non-critical; only affects monitoring


def force_release_bridge_run(reason: str = "manual_recovery", cancelled_run_id: str | None = None) -> dict[str, Any]:
    """Force-release the bridge lock for a stuck run and return the cancelled info.

    This is a recovery function — it unconditionally clears the lock state
    regardless of the caller's token. Intended for admin/operator use only.
    """
    state = dict(_STATE)
    was_busy = bool(state)
    released_run_id = state.get("run_id") or cancelled_run_id
    released_label = state.get("label") or ""
    released_since = state.get("started_at", datetime.now(timezone.utc).isoformat())
    released_elapsed = 0.0
    try:
        released_elapsed = max(0.0, time.monotonic() - float(state.get("started_monotonic") or 0.0))
    except Exception:
        released_elapsed = 0.0

    _STATE.clear()
    try:
        if _LOCK.locked():
            _LOCK.release()
    except RuntimeError:
        # Lock was not held — already released or never acquired
        pass

    return {
        "released": was_busy,
        "run_id": released_run_id,
        "label": released_label,
        "since": released_since,
        "elapsed_seconds": round(released_elapsed, 1),
        "reason": reason,
    }


# ── P1.9: Bridge Queue ─────────────────────────────────────────────────

def enqueue_judge(run_id: str, question: str, mode: str, seats: list[str]) -> dict[str, Any] | None:
    """Add a judge run to the bridge queue. Returns position info or None if queue is full."""
    if len(_QUEUE) >= _MAX_QUEUE_SIZE:
        return None
    entry = {
        "run_id": run_id,
        "question": question[:100],
        "mode": mode,
        "seats": seats,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    _QUEUE.append(entry)
    return {
        "run_id": run_id,
        "position": len(_QUEUE),
        "queued": True,
    }


def dequeue_next() -> dict[str, Any] | None:
    """Pop the next pending judge from the queue. Returns None if queue is empty."""
    if not _QUEUE:
        return None
    return _QUEUE.popleft()


def queue_snapshot() -> list[dict[str, Any]]:
    """Return a copy of the current queue."""
    return [dict(e) for e in _QUEUE]


def bridge_can_queue() -> bool:
    """Check whether the bridge supports queuing (always True for P1.9+)."""
    return True
