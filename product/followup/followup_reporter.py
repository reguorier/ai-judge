"""Write follow-up notes without overwriting the final report."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from product.followup.followup_context import load_followup_context
from product.reporting.report_schema import utc_now_iso


def _classify(prompt: str) -> str:
    lower = prompt.lower()
    if "反方" in prompt or "oppos" in lower:
        return "反方怎么说"
    if "下一步" in prompt or "action" in lower:
        return "下一步怎么做"
    if "摘要" in prompt or "summary" in lower:
        return "压缩摘要"
    if "补跑" in prompt or "rerun" in lower:
        return "补跑失败席位"
    return "解释这个结论"


def write_followup_note(run_dir: Path, prompt: str) -> dict[str, Any]:
    context = load_followup_context(run_dir)
    summary = context["summary"]
    followup_id = f"followup-{utc_now_iso().replace(':', '').replace('+', 'Z')}-{uuid.uuid4().hex[:6]}"
    followup_dir = run_dir / "followups"
    followup_dir.mkdir(parents=True, exist_ok=True)
    path = followup_dir / f"{followup_id}.md"
    kind = _classify(prompt)
    report_excerpt = re.sub(r"\s+", " ", context["final_report"]).strip()[:900]
    content = (
        f"# AI Judge Follow-up\n\n"
        f"- run_id: {summary.get('run_id')}\n"
        f"- type: {kind}\n"
        f"- created_at: {utc_now_iso()}\n"
        f"- based_on: final_report.md, summary.json, evidence_packet.json, seat_matrix.json\n\n"
        f"## 用户追问\n\n{prompt}\n\n"
        f"## 基于当前报告的回应\n\n"
        f"此回应只基于当前 run artifacts，不重新编造上下文。核心参考摘要：{report_excerpt}\n\n"
        f"## 建议\n\n- 若问题要求新证据，请启动新 run 或补跑失败席位。\n- 若只是解释报告，请继续引用 final_report.md 中的事实/推断/风险分区。\n"
    )
    path.write_text(content, encoding="utf-8")
    return {"followup_id": followup_id, "followup_path": str(path), "type": kind}
