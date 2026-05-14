#!/usr/bin/env python3
"""AI Judge Personal Cognitive Engine — FUSE, DECIDE, DARE protocols.

Three protocols for personal cognitive auditing:
  FUSE   (Fuse-Understand-Separate-Evaluate) — Emotional trigger audit
  DECIDE (Decision Evidence Chain)            — Major decision calibration
  DARE   (Detect-Admit-Reverse-Execute)       — Fear/withdrawal pattern tracking

Built on Hermes-inspired L2 persistent memory + L3 skill auto-creation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.hermes_memory import PersistentMemory, SessionMemory
from core.cognitive_skills import CognitiveSkillEngine


class PersonalCognitiveEngine:
    """Top-level engine for the three personal cognitive protocols."""

    def __init__(self, memory: PersistentMemory | None = None, session: SessionMemory | None = None):
        self.memory = memory or PersistentMemory()
        self.session = session or SessionMemory()
        self.skills = CognitiveSkillEngine(self.memory)

    # ── FUSE Protocol ──

    def fuse_trigger(self, trigger_description: str) -> dict[str, Any]:
        """Record an emotional trigger. 24h later, fuse_reflect() should be called."""
        self.session.record("fuse_trigger", {"description": trigger_description})
        event_id = self.memory.store_event("FUSE", "trigger", trigger_description)
        return {
            "protocol": "FUSE",
            "stage": "trigger",
            "message": (
                "已记录触发点。系统将在 24 小时后提醒你复盘。\n"
                "如果你现在冷静了，也可以立即运行 fuse_reflect。"
            ),
            "event_id": event_id,
            "reminder": "fuse_reflect will be available after 24h",
        }

    def fuse_reflect(self, event_id: int | None = None) -> dict[str, Any]:
        """24h later: 3-seat cross-examination of the emotional event."""
        recent = self.session.query("fuse_trigger", limit=1)
        if not recent:
            return {"error": "No recent trigger found. Use fuse_trigger first."}

        trigger = recent[0]["data"].get("description", "unknown trigger")

        # Three cognitive seats examine the event
        seats = {
            "旁观者席位": "如果是一个完全无关的旁观者看到这一幕，他会怎么评价你的反应？",
            "辩护者席位": "为你的反应辩护——在当时的情境下，你的反应可能有哪些合理之处？",
            "概率者席位": "回顾你历史上类似的情绪事件，这种情绪在统计上是'合理信号'还是'过度反应'？比例大概是多少？",
        }

        self.session.record("fuse_reflect", {"trigger": trigger, "seats": list(seats.keys())})
        self.memory.store_event("FUSE", "reflect", trigger, ai_response=json.dumps(seats, ensure_ascii=False))

        return {
            "protocol": "FUSE",
            "stage": "reflect",
            "trigger": trigger,
            "seats": seats,
            "instruction": "请逐一回答三个席位的问题。最后，你裁决：这次是'合理信号'还是'过度反应'？",
            "final_verdict_prompt": "Your verdict: 合理信号 / 过度反应 (explain why)",
        }

    def fuse_verdict(self, verdict: str, reasoning: str) -> dict[str, Any]:
        """User's final judgment on the emotional event."""
        event_id = self.memory.store_event("FUSE", "verdict", f"Verdict: {verdict}\nReasoning: {reasoning}")
        self.session.record("fuse_verdict", {"verdict": verdict, "reasoning": reasoning})

        # Pattern detection
        pattern = self.memory.detect_pattern("FUSE", [verdict])
        skill_msg = None
        if pattern and pattern["threshold_met"]:
            skill = self.skills.create_cognitive_skill(
                "FUSE", verdict,
                f"你已 {pattern['count']} 次将类似情绪判定为'{verdict}'。",
            )
            skill_msg = f"⚠️ 模式检测：这是你第 {pattern['count']} 次做出此判定。系统已生成认知技能：{skill['skill_id']}"

        return {
            "protocol": "FUSE",
            "stage": "complete",
            "event_id": event_id,
            "pattern_alert": skill_msg,
            "summary": f"判决：{verdict}。理由：{reasoning[:100]}...",
        }

    # ── DECIDE Protocol ──

    def decide_record(
        self, decision: str, benefits: list[str], concerns: list[str], confidence: float,
    ) -> dict[str, Any]:
        """Record a major decision with benefits, concerns, and confidence."""
        benefits_str = "\n".join(f"- {b}" for b in benefits)
        concerns_str = "\n".join(f"- {c}" for c in concerns)

        decision_id = self.memory.store_decision(decision, benefits_str, concerns_str, confidence)
        self.session.record("decide_record", {
            "decision": decision, "confidence": confidence, "decision_id": decision_id,
        })

        return {
            "protocol": "DECIDE",
            "stage": "recorded",
            "decision_id": decision_id,
            "confidence": confidence,
            "review_date": "3 months from now",
            "message": (
                f"你对此决策的 confidence 是 {confidence}。\n"
                "系统将在 3 个月后提醒你回顾。届时对比实际结果，校准你的判断。"
            ),
        }

    def decide_review(self) -> dict[str, Any]:
        """Check for decisions due for 3-month review."""
        due = self.memory.get_due_reviews()
        if not due:
            return {"protocol": "DECIDE", "stage": "review", "due_count": 0, "message": "没有到期的决策回顾。"}

        results = []
        for d in due:
            results.append({
                "decision_id": d["id"],
                "decision": d["decision_text"],
                "original_confidence": d["confidence"],
                "benefits": d["benefits"],
                "concerns": d["concerns"],
                "created_3mo_ago": time.strftime("%Y-%m-%d", time.localtime(d["created_at"])),
                "prompt": (
                    f"3 个月前你对此决策的 confidence 是 {d['confidence']}。\n"
                    f"当时你担心的：{d['concerns'][:200]}\n\n"
                    "现在回顾：\n"
                    "1. 你当时最担心的那件事——实际发生了吗？\n"
                    "2. 你当时没考虑到的最大变量是什么？\n"
                    "3. 如果重来一次，你的 confidence 应该是多少？"
                ),
            })

        return {"protocol": "DECIDE", "stage": "review", "due_count": len(due), "decisions": results}

    def decide_calibrate(self, decision_id: int, actual_outcome: str, new_confidence: float) -> dict[str, Any]:
        """User reviews a past decision. Compute log_score calibration."""
        rows = self.memory.conn.execute(
            "SELECT confidence FROM decisions WHERE id=?", (decision_id,)
        ).fetchone()
        if not rows:
            return {"error": f"Decision {decision_id} not found."}

        original_conf = rows[0]
        # log_score: higher penalty for confident wrong
        # outcome is "good" if the user says so (subjective calibration)
        import math
        is_good = "good" in actual_outcome.lower() or "准确" in actual_outcome
        prob = original_conf if is_good else 1.0 - original_conf
        log_score_val = round(-math.log(max(prob, 1e-9)), 4)

        self.memory.record_review(decision_id, actual_outcome, log_score_val)

        # Calibration message
        if log_score_val < 0.5:
            calib_msg = "🟢 你的判断很准。"
        elif log_score_val < 1.5:
            calib_msg = "🟡 你的判断基本合理，但有一些偏差。"
        else:
            calib_msg = f"🔴 你的判断偏差较大。原 confidence={original_conf}，log_score={log_score_val}。建议降低未来类似决策的 confidence。"

        stats = self.memory.get_calibration_stats()

        return {
            "protocol": "DECIDE",
            "stage": "calibrated",
            "decision_id": decision_id,
            "original_confidence": original_conf,
            "new_confidence": new_confidence,
            "log_score": log_score_val,
            "calibration_message": calib_msg,
            "overall_stats": stats,
        }

    # ── DARE Protocol ──

    def dare_trigger(self, opportunity_description: str) -> dict[str, Any]:
        """Record a moment of fear/withdrawal. 24h later, dare_reflect()."""
        self.session.record("dare_trigger", {"description": opportunity_description})
        self.memory.store_event("DARE", "trigger", opportunity_description)
        return {
            "protocol": "DARE",
            "stage": "trigger",
            "message": "已记录。24 小时后系统将推送反思问题。",
        }

    def dare_reflect(self) -> dict[str, Any]:
        """24h later: structured fear analysis."""
        recent = self.session.query("dare_trigger", limit=1)
        if not recent:
            return {"error": "No recent DARE trigger found."}

        opportunity = recent[0]["data"].get("description", "unknown")

        fear_options = [
            "怕别人嘲笑我",
            "怕麻烦/怕累",
            "怕失败后丢面子",
            "怕成功了之后压力更大",
            "怕自己能力不够",
            "其他",
        ]

        self.memory.store_event("DARE", "reflect", opportunity, ai_response=json.dumps(fear_options, ensure_ascii=False))

        return {
            "protocol": "DARE",
            "stage": "reflect",
            "opportunity": opportunity,
            "fear_options": fear_options,
            "instruction": "勾选你真正的恐惧来源（可多选）。如果选'其他'，请具体描述。",
            "counterfactual": "如果这个机会出现在一年后的你面前，你的答案会不同吗？",
        }

    def dare_verdict(self, fears: list[str], counterfactual_answer: str = "") -> dict[str, Any]:
        """User identifies their fear pattern."""
        fears_str = ", ".join(fears)
        event_id = self.memory.store_event(
            "DARE", "verdict",
            f"Fears: {fears_str}\nCounterfactual: {counterfactual_answer}",
        )

        # Pattern detection per fear keyword
        patterns = []
        for fear in fears:
            p = self.memory.detect_pattern("DARE", [fear])
            if p and p["threshold_met"]:
                skill = self.skills.create_cognitive_skill(
                    "DARE", fear,
                    f"你已 {p['count']} 次因'{fear}'而退缩。\n"
                    f"回顾历史上因此拒绝的机会——有没有你后悔的？",
                )
                patterns.append({"fear": fear, "count": p["count"], "skill": skill["skill_id"]})

        pattern_msgs = None
        if patterns:
            pattern_msgs = [f"⚠️ '{p['fear']}'模式已出现 {p['count']} 次 —— 认知技能已生成" for p in patterns]

        return {
            "protocol": "DARE",
            "stage": "complete",
            "event_id": event_id,
            "patterns_detected": pattern_msgs,
            "summary": f"恐惧来源：{fears_str}",
        }

    # ── Periodic Self-Nudge (Hermes-inspired) ──

    def periodic_nudge(self) -> dict[str, Any]:
        """Daily check: any patterns, due reviews, or protocol triggers to surface?"""
        nudges = []

        # Check due DECIDE reviews
        due = self.memory.get_due_reviews()
        if due:
            nudges.append({
                "type": "DECIDE",
                "message": f"你有 {len(due)} 个决策到了 3 个月回顾期",
            })

        # Check session for pending FUSE/DARE triggers
        fuse_triggers = self.session.query("fuse_trigger", limit=5)
        dare_triggers = self.session.query("dare_trigger", limit=5)

        for t in fuse_triggers:
            elapsed = time.time() - t["timestamp"]
            if elapsed > 24 * 3600:  # More than 24h
                nudges.append({
                    "type": "FUSE",
                    "message": f"24 小时前你记录了一次情绪触发点。现在冷静了，要不要复盘？",
                })

        for t in dare_triggers:
            elapsed = time.time() - t["timestamp"]
            if elapsed > 24 * 3600:
                nudges.append({
                    "type": "DARE",
                    "message": f"24 小时前你记录了一次退缩。现在平静了，想分析一下吗？",
                })

        stats = self.memory.get_calibration_stats()

        return {
            "nudge_count": len(nudges),
            "nudges": nudges,
            "calibration_stats": stats,
            "message": "No pending actions." if not nudges else f"{len(nudges)} items need attention.",
        }

    def dashboard(self) -> dict[str, Any]:
        """Personal cognitive dashboard summary."""
        stats = self.memory.get_calibration_stats()
        session_snapshot = self.session.snapshot()

        # Count by protocol
        fuse_count = self.memory.conn.execute("SELECT COUNT(*) FROM events WHERE protocol='FUSE'").fetchone()[0]
        decide_count = self.memory.conn.execute("SELECT COUNT(*) FROM events WHERE protocol='DECIDE' AND stage='recorded'").fetchone()[0]
        dare_count = self.memory.conn.execute("SELECT COUNT(*) FROM events WHERE protocol='DARE'").fetchone()[0]
        pattern_count = self.memory.conn.execute("SELECT COUNT(*) FROM patterns WHERE occurrence_count >= 5").fetchone()[0]

        return {
            "version": "1.0.0",
            "session": session_snapshot,
            "totals": {
                "fuse_events": fuse_count,
                "decide_decisions": decide_count,
                "dare_events": dare_count,
                "cognitive_patterns_detected": pattern_count,
            },
            "calibration": stats,
            "decisions_due_review": len(self.memory.get_due_reviews()),
        }
