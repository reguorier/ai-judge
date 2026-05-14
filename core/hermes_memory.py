#!/usr/bin/env python3
"""Hermes-inspired 3-tier memory system for AI Judge personal cognitive engine.

L1 — Session Memory (RAM ring buffer)
L2 — Persistent Memory (SQLite FTS5 + LLM summaries)
L3 — Skill Memory (SKILL.md patterns, auto-distilled from L2)
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections import deque
from pathlib import Path
from typing import Any


# ── L1: Session Ring Buffer ──

class SessionMemory:
    """In-memory ring buffer for current session context."""

    def __init__(self, max_events: int = 100):
        self.events: deque[dict[str, Any]] = deque(maxlen=max_events)

    def record(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append({
            "timestamp": time.time(),
            "type": event_type,
            "data": data,
        })

    def query(self, event_type: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        results = list(self.events)
        if event_type:
            results = [e for e in results if e["type"] == event_type]
        return results[-limit:]

    def snapshot(self) -> dict[str, Any]:
        return {"count": len(self.events), "latest_types": [e["type"] for e in list(self.events)[-5:]]}


# ── L2: Persistent Memory (SQLite FTS5) ──

class PersistentMemory:
    """SQLite FTS5-backed persistent memory for cross-session knowledge."""

    def __init__(self, db_path: str = "~/.ai-judge/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT NOT NULL,        -- FUSE, DECIDE, DARE
                stage TEXT NOT NULL,            -- trigger, capture, reflect, verdict
                content TEXT NOT NULL,          -- user input
                ai_response TEXT,               -- system response
                confidence REAL,                -- user's confidence at time
                actual_outcome TEXT,            -- for DECIDE calibration
                created_at REAL NOT NULL,
                reviewed_at REAL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                protocol, stage, content, ai_response, tokenize='porter unicode61'
            );
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,     -- fear, overreaction, blindspot
                trigger_keywords TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                auto_skill_id TEXT              -- linked cognitive skill
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_text TEXT NOT NULL,
                benefits TEXT NOT NULL,
                concerns TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at REAL NOT NULL,
                review_at REAL NOT NULL,        -- 3-month callback
                reviewed BOOLEAN DEFAULT 0,
                actual_outcome TEXT,
                log_score REAL
            );
        """)
        self.conn.commit()

    def store_event(
        self, protocol: str, stage: str, content: str,
        ai_response: str = "", confidence: float | None = None,
    ) -> int:
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO events(protocol, stage, content, ai_response, confidence, created_at) VALUES(?,?,?,?,?,?)",
            (protocol, stage, content, ai_response, confidence, now),
        )
        self.conn.execute(
            "INSERT INTO events_fts(rowid, protocol, stage, content, ai_response) VALUES(?,?,?,?,?)",
            (cur.lastrowid, protocol, stage, content, ai_response),
        )
        self.conn.commit()
        return cur.lastrowid

    def store_decision(
        self, decision: str, benefits: str, concerns: str, confidence: float,
    ) -> int:
        now = time.time()
        review_at = now + 90 * 24 * 3600  # 3 months
        cur = self.conn.execute(
            "INSERT INTO decisions(decision_text, benefits, concerns, confidence, created_at, review_at) VALUES(?,?,?,?,?,?)",
            (decision, benefits, concerns, confidence, now, review_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_due_reviews(self) -> list[dict[str, Any]]:
        now = time.time()
        rows = self.conn.execute(
            "SELECT * FROM decisions WHERE review_at <= ? AND reviewed = 0 ORDER BY review_at",
            (now,),
        ).fetchall()
        return [dict(zip([d[0] for d in self.conn.execute("PRAGMA table_info(decisions)")], r)) for r in rows]

    def record_review(self, decision_id: int, actual_outcome: str, log_score_val: float) -> None:
        self.conn.execute(
            "UPDATE decisions SET reviewed=1, actual_outcome=?, log_score=? WHERE id=?",
            (actual_outcome, log_score_val, decision_id),
        )
        self.conn.commit()

    def detect_pattern(self, protocol: str, keywords: list[str]) -> dict[str, Any] | None:
        """Check if a pattern has appeared >=5 times."""
        keyword_str = " ".join(keywords)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE protocol=? AND (content LIKE ? OR ai_response LIKE ?)",
            (protocol, f"%{keyword_str}%", f"%{keyword_str}%"),
        ).fetchone()[0]

        if count >= 3:
            now = time.time()
            existing = self.conn.execute(
                "SELECT * FROM patterns WHERE pattern_type=? AND trigger_keywords=?",
                (protocol, keyword_str),
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE patterns SET occurrence_count=occurrence_count+1, last_seen=? WHERE id=?",
                    (now, existing[0]),
                )
            else:
                self.conn.execute(
                    "INSERT INTO patterns(pattern_type, trigger_keywords, occurrence_count, first_seen, last_seen) VALUES(?,?,1,?,?)",
                    (protocol, keyword_str, now, now),
                )
            self.conn.commit()
            return {"pattern_type": protocol, "keywords": keyword_str, "count": count, "threshold_met": count >= 5}
        return None

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT e.* FROM events e JOIN events_fts ef ON e.id = ef.rowid "
            "WHERE events_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [dict(zip([d[0] for d in self.conn.execute("PRAGMA table_info(events)")], r)) for r in rows]

    def get_calibration_stats(self) -> dict[str, Any]:
        """Compute overall decision calibration."""
        rows = self.conn.execute(
            "SELECT confidence, log_score FROM decisions WHERE reviewed=1 AND log_score IS NOT NULL"
        ).fetchall()
        if not rows:
            return {"total_decisions": 0, "avg_log_score": None, "message": "No reviewed decisions yet."}
        avg_log = sum(r[1] for r in rows) / len(rows)
        return {"total_decisions": len(rows), "avg_log_score": round(avg_log, 4)}
