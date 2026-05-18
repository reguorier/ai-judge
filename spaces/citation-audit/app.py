from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

APP_PATH = Path(__file__).resolve()
if len(APP_PATH.parents) > 2:
    ROOT = APP_PATH.parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

LOCAL_PROXY_BYPASS = "localhost,127.0.0.1,::1"
for proxy_key in ("NO_PROXY", "no_proxy"):
    existing = os.environ.get(proxy_key, "")
    entries = [item.strip() for item in existing.split(",") if item.strip()]
    for host in LOCAL_PROXY_BYPASS.split(","):
        if host not in entries:
            entries.append(host)
    os.environ[proxy_key] = ",".join(entries)

from core.citation_audit import render_audit_html, render_audit_markdown, run_citation_audit


DEFAULT_ANSWER = """AI citation errors are basically solved in modern LLM systems.
The 2026 Stanford Trustworthy AI Citation Survey found that hallucinated references dropped below 1%.
Source: https://stanford.example.edu/trustworthy-ai-citation-survey-2026"""

DEFAULT_EVIDENCE = json.dumps(
    [
        {
            "url": "https://hai.stanford.edu/ai-index",
            "title": "Stanford AI Index",
            "snippet": (
                "The AI Index tracks AI trends and risks, but this evidence does not verify "
                "the named 2026 citation survey or below-1-percent claim."
            ),
            "status": "user_supplied",
            "provenance": "user_supplied",
        }
    ],
    indent=2,
)

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Judge Citation Audit</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #17212b;
      --muted: #627083;
      --line: #d9e2ec;
      --accent: #0f766e;
      --accent-ink: #ffffff;
      --soft: #eaf3f2;
      --code: #101923;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      padding: 22px clamp(16px, 4vw, 40px);
      background: #10212c;
      color: white;
      border-bottom: 1px solid #213744;
    }
    header h1 { margin: 0 0 6px; font-size: 28px; line-height: 1.1; }
    header p { margin: 0; color: #c8d6df; max-width: 920px; }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 440px) minmax(0, 1fr);
      gap: 16px;
      max-width: 1320px;
      margin: 0 auto;
      padding: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    h2 { margin: 0 0 12px; font-size: 17px; }
    label { display: block; margin: 12px 0 6px; font-weight: 700; }
    textarea {
      width: 100%;
      min-height: 88px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      color: var(--ink);
      background: white;
      font: 14px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    textarea.answer { min-height: 166px; }
    textarea.evidence { min-height: 190px; }
    .row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 12px 0;
      color: var(--muted);
    }
    .row input { width: 18px; height: 18px; }
    button {
      width: 100%;
      min-height: 44px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: var(--accent-ink);
      font-weight: 800;
      cursor: pointer;
    }
    button:disabled { opacity: .62; cursor: progress; }
    .summary {
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfdff;
      min-width: 0;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 3px; overflow-wrap: anywhere; }
    .tabs {
      display: flex;
      gap: 8px;
      margin: 8px 0 12px;
      border-bottom: 1px solid var(--line);
    }
    .tab {
      width: auto;
      min-height: 36px;
      padding: 0 12px;
      background: transparent;
      color: var(--muted);
      border-radius: 6px 6px 0 0;
    }
    .tab.active { background: var(--soft); color: #0b5f59; }
    .panel { display: none; }
    .panel.active { display: block; }
    pre {
      margin: 0;
      min-height: 360px;
      max-height: 760px;
      overflow: auto;
      white-space: pre-wrap;
      border-radius: 8px;
      padding: 14px;
      background: var(--code);
      color: #edf6fb;
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    #htmlReport {
      width: 100%;
      min-height: 360px;
      height: 760px;
      max-height: 760px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
    }
    .status {
      margin-top: 10px;
      color: var(--muted);
      min-height: 22px;
    }
    @media (max-width: 920px) {
      main { grid-template-columns: 1fr; }
      .summary { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }
  </style>
</head>
<body>
  <header>
    <h1>AI Judge Citation Audit</h1>
    <p>Paste an AI-generated answer and optional external evidence. The audit keeps raw answer text, external evidence, and verification output separate, with reason codes for unverifiable sources and provenance grades for evidence.</p>
  </header>
  <main>
    <section>
      <h2>Input</h2>
      <label for="question">Question</label>
      <textarea id="question">Does this answer provide reliable evidence?</textarea>
      <label for="answer">AI-generated answer</label>
      <textarea id="answer" class="answer">__DEFAULT_ANSWER__</textarea>
      <label for="evidence">External evidence JSON</label>
      <textarea id="evidence" class="evidence">__DEFAULT_EVIDENCE__</textarea>
      <label class="row"><input id="allowNetwork" type="checkbox"> Allow network fetch for cited URLs</label>
      <button id="runButton" type="button">Run Citation Audit</button>
      <div id="status" class="status">Ready. Default case should return unverifiable, not false.</div>
    </section>
    <section>
      <h2>Audit Output</h2>
      <div class="summary">
        <div class="metric"><span>Overall</span><strong id="overall">-</strong></div>
        <div class="metric"><span>Trust Gate</span><strong id="trustGate">-</strong></div>
        <div class="metric"><span>Main Gap</span><strong id="reasonCode">-</strong></div>
        <div class="metric"><span>Evidence</span><strong id="provenance">-</strong></div>
        <div class="metric"><span>Certification ID</span><strong id="certification">-</strong></div>
        <div class="metric"><span>Replay Ledger</span><strong id="ledger">-</strong></div>
      </div>
      <div class="tabs">
        <button class="tab active" data-panel="htmlReport" type="button">Report</button>
        <button class="tab" data-panel="markdownReport" type="button">Markdown</button>
        <button class="tab" data-panel="jsonReport" type="button">JSON</button>
      </div>
      <iframe id="htmlReport" class="panel active" title="HTML report"></iframe>
      <pre id="markdownReport" class="panel"></pre>
      <pre id="jsonReport" class="panel"></pre>
    </section>
  </main>
  <script>
    const runButton = document.getElementById("runButton");
    const statusEl = document.getElementById("status");

    function setPanel(id) {
      document.querySelectorAll(".tab").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.panel === id);
      });
      document.querySelectorAll(".panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === id);
      });
    }

    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => setPanel(tab.dataset.panel));
    });

    function firstNonZero(counts) {
      const entries = Object.entries(counts || {}).filter(([, value]) => Number(value) > 0);
      return entries.length ? `${entries[0][0]}: ${entries[0][1]}` : "none";
    }

    function formatCounts(counts) {
      const entries = Object.entries(counts || {}).filter(([, value]) => Number(value) > 0);
      return entries.length ? entries.map(([key, value]) => `${key}: ${value}`).join(", ") : "-";
    }

    async function runAudit() {
      runButton.disabled = true;
      statusEl.textContent = "Running citation audit...";
      try {
        const response = await fetch("/api/audit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: document.getElementById("question").value,
            answer: document.getElementById("answer").value,
            evidence_json: document.getElementById("evidence").value,
            allow_network: document.getElementById("allowNetwork").checked,
          }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Audit failed");
        document.getElementById("htmlReport").srcdoc = data.html;
        document.getElementById("markdownReport").textContent = data.markdown;
        document.getElementById("jsonReport").textContent = JSON.stringify(data.summary, null, 2);
        document.getElementById("overall").textContent = data.summary.overall_status || "-";
        document.getElementById("trustGate").textContent = data.summary.trust_gate || "-";
        document.getElementById("reasonCode").textContent = firstNonZero(data.summary.unverifiable_reason_counts);
        document.getElementById("provenance").textContent = formatCounts(data.summary.evidence_provenance_counts);
        document.getElementById("certification").textContent = data.summary.certification_id || "-";
        document.getElementById("ledger").textContent = data.summary.replay_ledger_hash || "-";
        statusEl.textContent = "Audit complete.";
      } catch (error) {
        statusEl.textContent = error.message;
      } finally {
        runButton.disabled = false;
      }
    }

    runButton.addEventListener("click", runAudit);
    runAudit();
  </script>
</body>
</html>
"""


def parse_evidence(evidence_json: str) -> list[dict[str, Any]]:
    if not evidence_json.strip():
        return []
    loaded = json.loads(evidence_json)
    if not isinstance(loaded, list):
        raise ValueError("External evidence JSON must be a list.")
    return loaded


def audit_payload(question: str, answer: str, evidence_json: str, allow_network: bool) -> dict[str, Any]:
    evidence = parse_evidence(evidence_json)
    verdict = run_citation_audit(
        title="AI Judge Citation Audit",
        question=question,
        answer=answer,
        external_evidence=evidence,
        allow_network=allow_network,
    )
    html = render_audit_html(verdict).replace(
        ".card { background:var(--panel);",
        ".card { color:var(--ink); background:var(--panel);",
    )
    return {
        "markdown": render_audit_markdown(verdict),
        "html": html,
        "summary": verdict["summary"],
    }


app = FastAPI(title="AI Judge Citation Audit")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE.replace("__DEFAULT_ANSWER__", DEFAULT_ANSWER).replace("__DEFAULT_EVIDENCE__", DEFAULT_EVIDENCE)


@app.get("/config")
def config() -> dict[str, Any]:
    return {
        "name": "AI Judge Citation Audit",
        "status_labels": ["verified", "weakly_verified", "irrelevant", "unverifiable", "contradicted"],
        "unverifiable_reason_codes": ["no_citation", "missing_external_evidence", "candidate_not_fetched", "fetch_error", "retrieval_blocked", "weak_match"],
        "evidence_provenance": ["model_candidate", "user_supplied", "fetched", "independently_attested", "notarized"],
        "source_isolation": ["raw_answer", "external_evidence", "verification_output"],
    }


@app.post("/api/audit")
async def api_audit(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        result = audit_payload(
            question=str(payload.get("question", "")),
            answer=str(payload.get("answer", "")),
            evidence_json=str(payload.get("evidence_json", "")),
            allow_network=bool(payload.get("allow_network", False)),
        )
        return JSONResponse(result)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/run/audit")
async def gradio_compatible_audit(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        data = payload.get("data", [])
        question, answer, evidence_json, allow_network = (data + ["", "", "", False])[:4]
        result = audit_payload(str(question), str(answer), str(evidence_json), bool(allow_network))
        return JSONResponse(
            {
                "data": [result["markdown"], result["html"], json.dumps(result["summary"], ensure_ascii=False, indent=2)],
                "is_generating": False,
            }
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
