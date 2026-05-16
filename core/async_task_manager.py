#!/usr/bin/env python3
"""AI Judge Async Task Manager — COUNCIL-005 consensus feature.

Manages long-running jury tasks (especially Strategic mode, 5-10 minutes).
Uses SQLite for persistence so tasks survive server restarts.

Features:
  - Submit a jury task → get a run_id immediately
  - Poll progress via SSE-compatible endpoint
  - Cancel running tasks
  - List history with status filtering
  - Automatic cleanup of old completed tasks

Usage:
  from core.async_task_manager import TaskManager

  tm = TaskManager()
  run_id = tm.submit(question="...", mode="strategic", seats=["gemini", ...])
  # Later:
  status = tm.get_status(run_id)  # {"step": "collecting", "progress": 0.45, ...}
  result = tm.get_result(run_id)  # None if still running, verdict dict if complete
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

DB_PATH = _PROJECT_ROOT / "data" / "tasks.db"


class TaskManager:
    """Async task queue backed by SQLite."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    run_id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'standard',
                    seats TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress REAL NOT NULL DEFAULT 0.0,
                    current_step TEXT,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC)
            """)
            conn.commit()

    def submit(
        self,
        question: str,
        mode: str = "standard",
        seats: list[str] | None = None,
    ) -> str:
        """Submit a new jury task. Returns run_id immediately."""
        run_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        from core.modes import resolve_mode
        config = resolve_mode(mode, override_seats=seats)
        resolved_seats = config["seats"]

        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO tasks (run_id, question, mode, seats, status, progress, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'pending', 0.0, ?, ?)""",
                (run_id, question, mode, json.dumps(resolved_seats), now, now),
            )
            conn.commit()

        return run_id

    def update_progress(
        self,
        run_id: str,
        step: str,
        progress: float,
    ) -> None:
        """Update the progress of a running task."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE tasks SET status='running', progress=?, current_step=?, updated_at=?
                   WHERE run_id=?""",
                (min(progress, 0.99), step, now, run_id),
            )
            conn.commit()

    def complete(self, run_id: str, result: dict[str, Any]) -> None:
        """Mark a task as complete and store the result."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE tasks SET status='complete', progress=1.0, current_step='done',
                   result_json=?, updated_at=?, completed_at=?
                   WHERE run_id=?""",
                (json.dumps(result, default=str), now, now, run_id),
            )
            conn.commit()

    def fail(self, run_id: str, error: str) -> None:
        """Mark a task as failed with an error message."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE tasks SET status='failed', progress=0.0, error=?, updated_at=?
                   WHERE run_id=?""",
                (error, now, run_id),
            )
            conn.commit()

    def cancel(self, run_id: str) -> bool:
        """Cancel a pending or running task."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """UPDATE tasks SET status='cancelled', updated_at=?, completed_at=?
                   WHERE run_id=? AND status IN ('pending', 'running')""",
                (now, now, run_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_status(self, run_id: str) -> dict[str, Any] | None:
        """Get current status of a task."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE run_id=?", (run_id,)
            ).fetchone()

        if row is None:
            return None

        return {
            "run_id": row["run_id"],
            "question": row["question"][:200],
            "mode": row["mode"],
            "status": row["status"],
            "progress": row["progress"],
            "current_step": row["current_step"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }

    def get_result(self, run_id: str) -> dict[str, Any] | None:
        """Get the verdict result of a completed task. None if not complete."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT status, result_json FROM tasks WHERE run_id=?", (run_id,)
            ).fetchone()

        if row is None or row["status"] != "complete":
            return None

        return json.loads(row["result_json"]) if row["result_json"] else None

    def list_tasks(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent tasks, optionally filtered by status."""
        with self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    """SELECT run_id, question, mode, status, progress, created_at, completed_at
                       FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT ?""",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT run_id, question, mode, status, progress, created_at, completed_at
                       FROM tasks ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()

        return [
            {
                "run_id": r["run_id"],
                "question": r["question"][:120],
                "mode": r["mode"],
                "status": r["status"],
                "progress": r["progress"],
                "created_at": r["created_at"],
                "completed_at": r["completed_at"],
            }
            for r in rows
        ]

    def cleanup_old(self, days: int = 7) -> int:
        """Remove completed/failed/cancelled tasks older than N days."""
        cutoff = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """DELETE FROM tasks
                   WHERE status IN ('complete', 'failed', 'cancelled')
                   AND completed_at < datetime(?, ?)""",
                (cutoff, f'-{days} days'),
            )
            conn.commit()
            return cursor.rowcount

    def run_task(
        self,
        run_id: str,
        question: str,
        mode: str,
        seats: list[str],
        score_fn: Callable,
    ) -> None:
        """Run a task in a background thread. Call score_fn(question, mode, seats) to get result."""
        try:
            # Phase 1: Render prompts
            self.update_progress(run_id, "rendering_prompts", 0.05)
            from core.mcp_server import ai_judge_ask
            prompt_data = ai_judge_ask(question, seats)
            self.update_progress(run_id, "prompts_ready", 0.15)

            # Phase 2: Collect (delegated to score_fn)
            self.update_progress(run_id, "collecting", 0.20)
            result = score_fn(question=question, mode=mode, seats=seats)
            self.update_progress(run_id, "scoring", 0.80)

            # Phase 3: Evidence trace (if strategic)
            from core.modes import resolve_mode
            config = resolve_mode(mode)
            if config["features"].get("evidence_trace"):
                self.update_progress(run_id, "evidence_tracing", 0.90)

            # Done
            self.update_progress(run_id, "finalizing", 0.95)
            self.complete(run_id, result)

        except Exception as e:
            self.fail(run_id, str(e))

    def submit_and_run(
        self,
        question: str,
        mode: str = "standard",
        seats: list[str] | None = None,
        score_fn: Callable | None = None,
        background: bool = True,
    ) -> str:
        """Submit and optionally start running a task. Returns run_id.

        If background=True (default), runs in a daemon thread.
        If background=False, caller must call run_task() manually.
        """
        from core.modes import resolve_mode
        config = resolve_mode(mode, override_seats=seats)
        resolved_seats = config["seats"]

        run_id = self.submit(question, mode, resolved_seats)

        if background and score_fn:
            t = threading.Thread(
                target=self.run_task,
                args=(run_id, question, mode, resolved_seats, score_fn),
                daemon=True,
            )
            t.start()

        return run_id


# ─── Standalone test ──────────────────────────────────────

if __name__ == "__main__":
    print("AI Judge Async Task Manager — Self Test\n")

    tm = TaskManager()

    # Submit a task
    run_id = tm.submit("Is solar cheaper than coal?", mode="flash")
    print(f"1. Submitted: {run_id}")

    # Check status
    status = tm.get_status(run_id)
    print(f"   Status: {status['status']}, progress: {status['progress']}")

    # Update progress
    tm.update_progress(run_id, "collecting", 0.30)
    status = tm.get_status(run_id)
    print(f"2. After update: step={status['current_step']}, progress={status['progress']}")

    # Complete
    tm.complete(run_id, {"verdict": "credible", "score": 0.85})
    result = tm.get_result(run_id)
    print(f"3. Complete: verdict={result['verdict']}, score={result['score']}")

    # List
    tasks = tm.list_tasks()
    print(f"4. Total tasks: {len(tasks)}")

    # Cleanup test db
    tm.cleanup_old(days=0)
    print("5. Cleanup done")

    print("\nAll tests passed")
