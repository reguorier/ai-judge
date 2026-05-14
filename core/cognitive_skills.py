#!/usr/bin/env python3
"""Cognitive Skill Engine — Hermes-inspired L3 skill auto-creation from patterns.

When a cognitive pattern appears >=5 times, the system auto-generates
a cognitive skill — a reusable insight about the user's own thinking patterns.

Safety gates: 4 checks before skill creation, inspired by Hermes' 7-gate system.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any


class CognitiveSkillEngine:
    """Auto-creates cognitive skills from detected behavioral patterns."""

    def __init__(self, memory: Any):
        self.memory = memory
        self.skills_dir = Path("~/.ai-judge/skills").expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def create_cognitive_skill(
        self, protocol: str, pattern_key: str, insight: str,
    ) -> dict[str, Any]:
        """Create a cognitive skill from a recurring pattern. 4 safety gates."""

        # Gate 1: Data sufficiency — at least 3 occurrences
        count = self._count_occurrences(protocol, pattern_key)
        if count < 3:
            return {"skill_id": None, "gated": "insufficient_data", "occurrences": count}

        # Gate 2: Skill name safety — alphanumeric + hyphens, < 64 chars
        skill_name = self._safe_skill_name(protocol, pattern_key)
        if not skill_name:
            return {"skill_id": None, "gated": "invalid_name"}

        # Gate 3: No absolute claims — "你应该" forbidden
        if re.search(r"你应该|你必须|你永远", insight):
            return {"skill_id": None, "gated": "absolutist_language"}

        # Gate 4: Not medical/legal — forbidden domains
        forbidden = ["诊断", "治疗", "法律建议", "投资建议", "处方"]
        if any(word in insight for word in forbidden):
            return {"skill_id": None, "gated": "forbidden_domain"}

        # Create skill
        skill = {
            "name": skill_name,
            "description": f"Auto-generated cognitive skill from {protocol} protocol — {pattern_key}",
            "protocol": protocol,
            "pattern": pattern_key,
            "occurrences": count,
            "insight": insight,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "trigger_example": (
                f"Next time you feel {pattern_key}, pause and ask:\n"
                f"> {insight}\n\n"
                f"(This pattern has occurred {count} times. It's a pattern, not an isolated incident.)"
            ),
            "counter_example": (
                f"Note: This pattern may not apply in every situation. "
                f"The skill is a prompt for reflection, not a rule for action."
            ),
        }

        # Save to skills directory
        skill_path = self.skills_dir / f"{skill_name}.json"
        skill_path.write_text(json.dumps(skill, ensure_ascii=False, indent=2), encoding="utf-8")

        # Link to memory
        self.memory.conn.execute(
            "UPDATE patterns SET auto_skill_id=? WHERE pattern_type=? AND trigger_keywords=?",
            (skill_name, protocol, pattern_key),
        )
        self.memory.conn.commit()

        return {"skill_id": skill_name, "occurrences": count, "path": str(skill_path)}

    def list_skills(self) -> list[dict[str, Any]]:
        """List all generated cognitive skills."""
        skills = []
        for f in sorted(self.skills_dir.glob("*.json")):
            try:
                skills.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return skills

    def get_skill(self, skill_name: str) -> dict[str, Any] | None:
        """Get a specific cognitive skill by name."""
        path = self.skills_dir / f"{skill_name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _safe_skill_name(self, protocol: str, pattern_key: str) -> str:
        """Generate a safe skill name from protocol + pattern."""
        raw = f"{protocol.lower()}-{pattern_key}"
        # Replace Chinese with pinyin-like slugs
        safe = re.sub(r"[^\w\-]", "-", raw)
        safe = re.sub(r"-+", "-", safe).strip("-")[:64]
        if not safe or len(safe) < 3:
            return ""
        return safe.lower()

    def _count_occurrences(self, protocol: str, pattern_key: str) -> int:
        row = self.memory.conn.execute(
            "SELECT COUNT(*) FROM events WHERE protocol=? AND (content LIKE ? OR ai_response LIKE ?)",
            (protocol, f"%{pattern_key}%", f"%{pattern_key}%"),
        ).fetchone()
        return row[0] if row else 0
