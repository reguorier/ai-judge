#!/usr/bin/env python3
"""P59: Unified Run Control Registry for AI Judge.

Provides a single source of truth for all active/stopped/resumed runs across
meeting (jury), werewolf, and worldcup flows.

Each run is tracked with:
  - run_id, mode, phase, active_seat, progress, started_at, updated_at
  - cancel_requested flag (external stop signal)
  - events[] (append-only log)
  - bridge_claim (lock token for shared bridge release)
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_RUNS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()

VALID_MODES = {"meeting", "werewolf", "worldcup"}
VALID_PHASES = {
    "meeting": ["queued", "running", "stopping", "stopped", "failed", "completed"],
    "werewolf": ["queued", "running", "stopping", "stopped", "failed", "completed"],
    "worldcup": ["queued", "running", "stopping", "stopped", "failed", "completed"],
}


def start_run(
    mode: str,
    label: str | None = None,
    bridge_claim: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Register a new run in the control layer. Returns the run dict."""
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {VALID_MODES}")

    rid = run_id or uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    run = {
        "run_id": rid,
        "mode": mode,
        "phase": "queued",
        "label": label or f"{mode}:{rid}",
        "active_seat": None,
        "progress": 0.0,
        "progress_label": "排队中",
        "started_at": now,
        "updated_at": now,
        "cancel_requested": False,
        "paused": False,
        "bridge_claim": bridge_claim,
        "events": [],
        "artifacts": [],
        "metadata": metadata or {},
    }
    with _LOCK:
        _RUNS[rid] = run
    _log_event(rid, {"type": "run_started", "mode": mode, "label": run["label"]})
    return dict(run)


def get_run(run_id: str) -> dict[str, Any] | None:
    """Return a snapshot of the run, or None."""
    with _LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        return None
    return dict(run)


def update_run(run_id: str, **kwargs: Any) -> dict[str, Any] | None:
    """Update run fields (phase, progress, active_seat, etc). Thread-safe."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        for k, v in kwargs.items():
            if k in run:
                run[k] = v
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    return result


def request_stop(run_id: str) -> dict[str, Any] | None:
    """Set cancel_requested = True. Does NOT immediately kill—let the worker check the flag."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["cancel_requested"] = True
        run["paused"] = False
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "stop_requested"})
    return result


def request_pause(run_id: str) -> dict[str, Any] | None:
    """Set paused=True, cancel_requested=False. Worker/dispatcher should poll is_paused()."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["paused"] = True
        run["cancel_requested"] = False
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "pause_requested"})
    return result


def request_resume(run_id: str) -> dict[str, Any] | None:
    """Clear paused flag and set phase back to running."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["paused"] = False
        run["phase"] = "running"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "resume_requested"})
    return result


def is_paused(run_id: str) -> bool:
    """Check if the run is currently paused (for worker/dispatcher polling)."""
    with _LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        return False
    return bool(run.get("paused"))


def mark_stopped(run_id: str) -> dict[str, Any] | None:
    """Mark a run as stopped after graceful shutdown."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["phase"] = "stopped"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "run_stopped"})
    return result


def mark_completed(run_id: str) -> dict[str, Any] | None:
    """Mark a run as completed."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["phase"] = "completed"
        run["progress"] = 1.0
        run["progress_label"] = "完成"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "run_completed"})
    return result


def mark_failed(run_id: str, error: str = "") -> dict[str, Any] | None:
    """Mark a run as failed."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["phase"] = "failed"
        run["error"] = error
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    _log_event(run_id, {"type": "run_failed", "error": error})
    return result


def release_bridge_for_run(run_id: str) -> bool:
    """Release the bridge lock if this run owns it."""
    from core.bridge_run_lock import release_bridge_run

    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return False
        claim = run.get("bridge_claim")
    if claim:
        release_bridge_run(claim)
        with _LOCK:
            run["bridge_claim"] = None
        _log_event(run_id, {"type": "bridge_released"})
        return True
    return False


def is_cancel_requested(run_id: str) -> bool:
    """Check if stop was requested for this run (for worker polling)."""
    with _LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        return False
    return bool(run.get("cancel_requested"))


def save_control_state(run_id: str) -> str | None:
    """Persist control state to runtime/runs/<run_id>/control.json. Returns path or None."""
    import json as _json
    from pathlib import Path as _Path

    run = get_run(run_id)
    if run is None:
        return None

    state = "running"
    if run.get("cancel_requested"):
        state = "cancelled"
    elif run.get("paused"):
        state = "paused"
    elif run.get("phase") in ("completed",):
        state = "completed"
    elif run.get("phase") in ("failed",):
        state = "failed"
    elif run.get("phase") in ("stopped",):
        state = "stopped"

    control = {
        "run_id": run["run_id"],
        "state": state,
        "paused": run.get("paused", False),
        "stop_requested": run.get("cancel_requested", False),
        "phase": run.get("phase"),
        "updated_at": run.get("updated_at"),
    }

    try:
        run_dir = _Path(__file__).resolve().parent.parent / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        ctrl_path = run_dir / "control.json"
        with open(ctrl_path, "w", encoding="utf-8") as f:
            _json.dump(control, f, ensure_ascii=False, indent=2)
        return str(ctrl_path)
    except Exception:
        return None


def load_control_state(run_id: str) -> dict[str, Any] | None:
    """Load control state from runtime/runs/<run_id>/control.json. Returns dict or None."""
    import json as _json
    from pathlib import Path as _Path

    try:
        ctrl_path = _Path(__file__).resolve().parent.parent / "runs" / run_id / "control.json"
        if not ctrl_path.exists():
            return None
        with open(ctrl_path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return None


def set_phase(run_id: str, phase: str, progress: float = 0.0, label: str = "") -> dict[str, Any] | None:
    """Convenience: set phase + progress + label."""
    if label and phase not in ("running",):
        pass
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return None
        run["phase"] = phase
        if progress:
            run["progress"] = progress
        if label:
            run["progress_label"] = label
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = dict(run)
    return result


def list_runs(mode: str | None = None) -> list[dict[str, Any]]:
    """List all tracked runs, optionally filtered by mode."""
    with _LOCK:
        runs = list(_RUNS.values())
    result = []
    for r in runs:
        if mode and r.get("mode") != mode:
            continue
        result.append(dict(r))
    result.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return result


def _log_event(run_id: str, event: dict[str, Any]) -> None:
    """Append a timestamped event to the run's event log."""
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return
        run["events"].append(event)
        run["updated_at"] = event["ts"]


def add_event(run_id: str, event: dict[str, Any]) -> None:
    """Public API: add an event to a run's event log."""
    _log_event(run_id, event)


def add_artifact(run_id: str, artifact: dict[str, Any]) -> None:
    """Add an artifact (file/product) reference to a run."""
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return
        artifact["ts"] = datetime.now(timezone.utc).isoformat()
        run["artifacts"].append(artifact)
        run["updated_at"] = artifact["ts"]


def clean_old_runs(max_age_hours: float = 24.0) -> int:
    """Remove runs older than max_age_hours. Returns count removed."""
    cutoff = time.monotonic() - (max_age_hours * 3600)
    with _LOCK:
        to_remove = []
        for rid, run in list(_RUNS.items()):
            try:
                started = datetime.fromisoformat(run["started_at"])
                age = time.monotonic() - started.timestamp()
                if age > max_age_hours * 3600:
                    to_remove.append(rid)
            except Exception:
                to_remove.append(rid)
        for rid in to_remove:
            del _RUNS[rid]
    return len(to_remove)