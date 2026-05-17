from __future__ import annotations

import json
import sys
from pathlib import Path

import gradio as gr

APP_PATH = Path(__file__).resolve()
if len(APP_PATH.parents) > 2:
    ROOT = APP_PATH.parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from core.citation_audit import render_audit_html, render_audit_markdown, run_citation_audit


DEFAULT_ANSWER = """AI citation errors are basically solved in modern LLM systems.
The 2026 Stanford Trustworthy AI Citation Survey found that hallucinated references dropped below 1%.
Source: https://stanford.example.edu/trustworthy-ai-citation-survey-2026"""

DEFAULT_EVIDENCE = json.dumps([
    {
        "url": "https://hai.stanford.edu/ai-index",
        "title": "Stanford AI Index",
        "snippet": "The AI Index tracks AI trends and risks, but this evidence does not verify the named 2026 citation survey or below-1-percent claim.",
        "status": "user_supplied",
    }
], indent=2)


def audit(question: str, answer: str, evidence_json: str, allow_network: bool) -> tuple[str, str, str]:
    try:
        evidence = json.loads(evidence_json) if evidence_json.strip() else []
    except json.JSONDecodeError as exc:
        return f"Evidence JSON error: {exc}", "", ""
    verdict = run_citation_audit(
        title="AI Judge Citation Audit",
        question=question,
        answer=answer,
        external_evidence=evidence,
        allow_network=allow_network,
    )
    markdown = render_audit_markdown(verdict)
    html = render_audit_html(verdict)
    raw = json.dumps(verdict["summary"], ensure_ascii=False, indent=2)
    return markdown, html, raw


with gr.Blocks(title="AI Judge Citation Audit") as demo:
    gr.Markdown(
        """
        # AI Judge Citation Audit

        Paste an AI-generated answer and optional external evidence. The audit separates model text from external evidence and labels citations as `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, or `contradicted`.
        """
    )
    with gr.Row():
        with gr.Column():
            question = gr.Textbox(label="Question", value="Does this answer provide reliable evidence?", lines=2)
            answer = gr.Textbox(label="AI-generated answer", value=DEFAULT_ANSWER, lines=8)
            evidence = gr.Code(label="External evidence JSON", value=DEFAULT_EVIDENCE, language="json", lines=10)
            allow_network = gr.Checkbox(label="Allow network fetch for cited URLs", value=False)
            run = gr.Button("Run Citation Audit", variant="primary")
        with gr.Column():
            markdown = gr.Markdown(label="Audit summary")
            html_report = gr.HTML(label="HTML report")
            summary_json = gr.Code(label="Machine-readable summary", language="json")
    run.click(
        audit,
        inputs=[question, answer, evidence, allow_network],
        outputs=[markdown, html_report, summary_json],
        queue=False,
    )


if __name__ == "__main__":
    demo.launch(show_error=True)
