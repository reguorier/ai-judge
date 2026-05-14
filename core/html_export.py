#!/usr/bin/env python3
"""HTML Report Exporter for AI Judge v3.1 verdicts.

Generates standalone, static HTML reports from V3 verdict data.
No external dependencies, no tracking, local-first.

Usage:
    from core.html_export import generate_verdict_html, save_html_report
    html = generate_verdict_html(verdict_data, profile, hard_truth)
    save_html_report(verdict_data, "verdict_report.html")
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


def generate_verdict_html(
    verdict_data: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
    hard_truth: Optional[dict[str, Any]] = None,
    question: str = "",
    run_id: str = "",
) -> str:
    """Generate a standalone HTML report for AI Judge verdict.

    Args:
        verdict_data: Full verdict output containing claims, scores, consensus
        profile: Neuro-cognitive profile output (optional)
        hard_truth: Hard truth mode output (optional)
        question: Original question being judged
        run_id: Run identifier

    Returns:
        Complete HTML document as string
    """
    profile = profile or {}
    hard_truth = hard_truth or {}

    # Extract data
    smart_sounding = profile.get("smart_sounding_score", 0.5)
    judgment_quality = profile.get("judgment_quality_score", 0.5)
    gap = profile.get("smart_vs_judgment_gap", 0)
    gap_label = profile.get("gap_label", "normal")
    risk_flags = profile.get("cognitive_risk_flags", [])
    signals = profile.get("signals", {})

    mode_level = hard_truth.get("mode_level", 0)
    mode_name = hard_truth.get("mode_name", "普通反馈")

    claims = verdict_data.get("claims", [])
    if isinstance(verdict_data, dict) and "top_claims" in verdict_data:
        claims = verdict_data.get("top_claims", [])
    consensus_map = verdict_data.get("consensus_map", {})
    dissent_flags = verdict_data.get("dissent_flags", [])

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Judge Verdict Report</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #2ea44f;
            --accent-yellow: #d29922;
            --accent-red: #cf222e;
            --accent-purple: #a371f7;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            border-bottom: 1px solid var(--bg-tertiary);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        h1 {{
            color: var(--accent-blue);
            font-size: 1.8em;
            margin-bottom: 10px;
        }}

        .meta {{
            color: var(--text-secondary);
            font-size: 0.9em;
        }}

        .meta code {{
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 4px;
        }}

        /* Dual Score Section */
        .dual-scores {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}

        .score-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            position: relative;
        }}

        .score-card.smart {{
            border-left: 4px solid var(--accent-purple);
        }}

        .score-card.judgment {{
            border-left: 4px solid var(--accent-green);
        }}

        .score-label {{
            font-size: 0.85em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}

        .score-value {{
            font-size: 2.5em;
            font-weight: 700;
        }}

        .score-card.smart .score-value {{ color: var(--accent-purple); }}
        .score-card.judgment .score-value {{ color: var(--accent-green); }}

        .score-bar {{
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            margin-top: 12px;
            overflow: hidden;
        }}

        .score-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        .score-card.smart .score-bar-fill {{ background: var(--accent-purple); }}
        .score-card.judgment .score-bar-fill {{ background: var(--accent-green); }}

        /* Gap Alert */
        .gap-alert {{
            background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}

        .gap-alert.warning {{
            border-left: 4px solid var(--accent-yellow);
        }}

        .gap-alert.danger {{
            border-left: 4px solid var(--accent-red);
        }}

        .gap-title {{
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .gap-alert.warning .gap-title {{ color: var(--accent-yellow); }}
        .gap-alert.danger .gap-title {{ color: var(--accent-red); }}

        /* Hard Truth Mode */
        .hard-truth {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}

        .mode-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 12px;
        }}

        .mode-L0, .mode-L1 {{ background: var(--bg-tertiary); color: var(--text-secondary); }}
        .mode-L2 {{ background: var(--accent-yellow); color: var(--bg-primary); }}
        .mode-L3, .mode-L4 {{ background: var(--accent-red); color: white; }}

        /* Risk Flags */
        .risk-section {{
            margin-bottom: 30px;
        }}

        .risk-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 12px;
        }}

        .risk-item {{
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 12px 16px;
            border-left: 3px solid var(--accent-red);
        }}

        /* Claims Section */
        .claims-section {{
            margin-bottom: 30px;
        }}

        .claim-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }}

        .claim-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .claim-tier {{
            font-size: 0.8em;
            padding: 2px 8px;
            border-radius: 12px;
        }}

        .tier-excellent {{ background: var(--accent-green); color: white; }}
        .tier-good {{ background: var(--accent-blue); color: white; }}
        .tier-acceptable {{ background: var(--accent-yellow); color: var(--bg-primary); }}
        .tier-weak {{ background: var(--bg-tertiary); color: var(--text-secondary); }}
        .tier-rejected {{ background: var(--accent-red); color: white; }}

        .claim-text {{
            color: var(--text-primary);
            font-size: 0.95em;
        }}

        .claim-meta {{
            margin-top: 8px;
            font-size: 0.85em;
            color: var(--text-secondary);
        }}

        /* Human Checklist */
        .checklist {{
            background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
        }}

        .checklist h3 {{
            color: var(--accent-blue);
            margin-bottom: 16px;
        }}

        .checklist-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }}

        .checklist-item:last-child {{
            border-bottom: none;
        }}

        .checkbox {{
            width: 20px;
            height: 20px;
            border: 2px solid var(--accent-blue);
            border-radius: 4px;
            flex-shrink: 0;
            margin-top: 2px;
        }}

        /* Signal Details */
        .signals-section {{
            margin-bottom: 30px;
        }}

        .signal-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}

        .signal-card {{
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 16px;
        }}

        .signal-name {{
            font-size: 0.8em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .signal-label {{
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .signal-score {{
            font-size: 0.9em;
            color: var(--accent-blue);
        }}

        /* Footer */
        footer {{
            border-top: 1px solid var(--bg-tertiary);
            padding-top: 20px;
            margin-top: 40px;
            color: var(--text-secondary);
            font-size: 0.85em;
        }}

        footer a {{
            color: var(--accent-blue);
            text-decoration: none;
        }}

        @media (max-width: 600px) {{
            .dual-scores {{
                grid-template-columns: 1fr;
            }}

            body {{
                padding: 12px;
            }}
        }}

        @media print {{
            body {{
                background: white;
                color: black;
            }}

            .score-card, .hard-truth, .claim-card, .checklist, .gap-alert {{
                background: #f5f5f5;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>🦞 AI Judge Verdict Report</h1>
        <div class="meta">
            Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")} |
            Run ID: <code>{run_id or "unknown"}</code>
        </div>
        {f'<div class="meta" style="margin-top:8px"><strong>Question:</strong> {question[:200]}</div>' if question else ''}
    </header>

    <!-- Dual Scores -->
    <section class="dual-scores">
        <div class="score-card smart">
            <div class="score-label">Smart Sounding</div>
            <div class="score-value">{smart_sounding:.2f}</div>
            <div class="score-bar">
                <div class="score-bar-fill" style="width: {smart_sounding * 100:.1f}%"></div>
            </div>
            <div style="margin-top:8px;font-size:0.85em;color:var(--text-secondary)">
                How confident/fluent/structured it sounds
            </div>
        </div>
        <div class="score-card judgment">
            <div class="score-label">Judgment Quality</div>
            <div class="score-value">{judgment_quality:.2f}</div>
            <div class="score-bar">
                <div class="score-bar-fill" style="width: {judgment_quality * 100:.1f}%"></div>
            </div>
            <div style="margin-top:8px;font-size:0.85em;color:var(--text-secondary)">
                How reliable the actual thinking is
            </div>
        </div>
    </section>

    <!-- Gap Alert -->
    {generate_gap_section(gap, gap_label, risk_flags)}

    <!-- Hard Truth Mode -->
    <section class="hard-truth">
        <div class="mode-badge mode-L{mode_level}">L{mode_level}: {mode_name}</div>
        <div style="font-size:0.95em">{hard_truth.get('trigger_reason', 'Normal feedback mode.') if hard_truth else 'Normal feedback mode.'}</div>
    </section>

    <!-- Risk Flags -->
    {generate_risk_section(risk_flags)}

    <!-- Signal Details -->
    {generate_signals_section(signals)}

    <!-- Claims -->
    {generate_claims_section(claims, consensus_map, dissent_flags)}

    <!-- Human Action Checklist -->
    <section class="checklist">
        <h3>✅ Human Action Checklist</h3>
        {generate_checklist(hard_truth, risk_flags, claims)}
    </section>

    <footer>
        <p>
            AI Judge v3.1 · Local-first · No tracking · No external dependencies<br>
            <a href="https://github.com/reguorider-gif/ai-judge">github.com/reguorider-gif/ai-judge</a>
        </p>
    </footer>
</body>
</html>"""

    return html


def generate_gap_section(gap: float, gap_label: str, risk_flags: list) -> str:
    """Generate the gap alert section."""
    if abs(gap) < 0.15:
        return ""

    alert_class = "danger" if gap > 0.30 else "warning"

    return f"""<section class="gap-alert {alert_class}">
        <div class="gap-title">⚠️ Gap Alert: {gap_label}</div>
        <div style="font-size:0.9em">
            Gap: <strong>{gap:.1%}</strong> — This output "sounds smarter than it is".
            The polished language exceeds the underlying judgment quality.
        </div>
    </section>"""


def generate_risk_section(risk_flags: list) -> str:
    """Generate the risk flags section."""
    if not risk_flags:
        return ""

    items = "\n".join(f'<div class="risk-item">{flag}</div>' for flag in risk_flags)

    return f"""<section class="risk-section">
        <h3 style="margin-bottom:12px;color:var(--accent-red)">🚩 Cognitive Risk Flags</h3>
        <div class="risk-grid">{items}</div>
    </section>"""


def generate_signals_section(signals: dict) -> str:
    """Generate the cognitive signals section."""
    if not signals:
        return ""

    signal_names = {
        "self_closure": "自我视角闭环",
        "ambiguity_flexibility": "模糊性处理",
        "recovery_after_negative": "反馈恢复模式",
        "experience_grounding": "经验锚定度",
    }

    cards = []
    for key, data in signals.items():
        if not data:
            continue
        name = signal_names.get(key, key)
        label = data.get("label", "N/A")
        score = data.get(f"{key.replace('_', '_')}score", data.get("score", "N/A"))

        # Handle different score key names
        score_key = f"{key}_score"
        if key == "self_closure":
            score_key = "self_closure_score"
        elif key == "ambiguity_flexibility":
            score_key = "ambiguity_flexibility_score"
        elif key == "experience_grounding":
            score_key = "experience_grounding_score"
        elif key == "recovery_after_negative":
            score_key = "recovery_score"

        score_val = data.get(score_key, data.get("score", 0.5))

        cards.append(f"""<div class="signal-card">
            <div class="signal-name">{name}</div>
            <div class="signal-label">{label}</div>
            <div class="signal-score">{score_val:.2f}</div>
        </div>""")

    if not cards:
        return ""

    return f"""<section class="signals-section">
        <h3 style="margin-bottom:12px">🧠 Cognitive Proxy Signals</h3>
        <div class="signal-grid">{"".join(cards)}</div>
    </section>"""


def generate_claims_section(claims: list, consensus_map: dict, dissent_flags: list) -> str:
    """Generate the claims section."""
    if not claims:
        return ""

    cards = []
    for claim in claims[:10]:  # Limit to 10 claims
        if isinstance(claim, dict):
            text = claim.get("claim", claim.get("content", ""))[:150]
            score = claim.get("score", claim.get("allocation_score", 0))
            tier = claim.get("tier", "acceptable")
            agree_count = claim.get("agree_count", 0)
        else:
            text = str(claim)[:150]
            score = 0.5
            tier = "acceptable"
            agree_count = 0

        tier_class = f"tier-{tier}"

        cards.append(f"""<div class="claim-card">
            <div class="claim-header">
                <span class="claim-tier {tier_class}">{tier}</span>
                <span style="font-size:0.85em;color:var(--text-secondary)">Score: {score:.2f}</span>
            </div>
            <div class="claim-text">{text}</div>
            {f'<div class="claim-meta">Agreed by {agree_count} seats</div>' if agree_count else ''}
        </div>""")

    if not cards:
        return ""

    return f"""<section class="claims-section">
        <h3 style="margin-bottom:12px">📋 Claims ({len(claims)} total)</h3>
        {"".join(cards)}
    </section>"""


def generate_checklist(hard_truth: dict, risk_flags: list, claims: list) -> str:
    """Generate human action checklist based on verdict data."""
    items = []

    # Always add verification items
    items.append("Verify at least one high-confidence claim before acting")

    # Add items based on risks
    if risk_flags:
        items.append("Review cognitive risk flags before accepting conclusions")

    mode_level = hard_truth.get("mode_level", 0) if hard_truth else 0
    if mode_level >= 2:
        items.append("Answer the three hard truth questions before proceeding")

    if mode_level >= 3:
        items.append("Stop expanding — only accept verifiable evidence now")

    # Add items based on claims
    rejected_claims = [c for c in claims if isinstance(c, dict) and c.get("tier") == "rejected"]
    if rejected_claims:
        items.append(f"Review {len(rejected_claims)} rejected claim(s) — understand why they were blocked")

    # Default items if none added
    if not items:
        items = [
            "Review the verdict summary above",
            "Verify key claims before acting",
            "Decide: accept, reject, or request more evidence"
        ]

    checklist_items = "\n".join(f"""<div class="checklist-item">
            <div class="checkbox"></div>
            <div>{item}</div>
        </div>""" for item in items)

    return checklist_items


def save_html_report(
    output_path: str | Path,
    verdict_data: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
    hard_truth: Optional[dict[str, Any]] = None,
    question: str = "",
    run_id: str = "",
) -> int:
    """Generate and save HTML report to file.

    Returns:
        0 on success, 1 on error
    """
    try:
        html = generate_verdict_html(
            verdict_data=verdict_data,
            profile=profile,
            hard_truth=hard_truth,
            question=question,
            run_id=run_id,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

        print(f"✅ HTML report saved: {path}")
        return 0

    except Exception as e:
        print(f"❌ Failed to generate HTML report: {e}", flush=True)
        return 1


# Demo data for testing
DEMO_VERDICT = {
    "claims": [
        {"claim": "Market timing is favorable due to Q3 demand signals", "score": 0.82, "tier": "excellent", "agree_count": 8},
        {"claim": "Pricing should be aggressive to capture market share", "score": 0.45, "tier": "acceptable", "agree_count": 5},
        {"claim": "Trust me, this will 10x in 6 months", "score": 0.12, "tier": "rejected", "agree_count": 1},
    ],
    "consensus_map": {"consensus": 5, "split": 3, "dissent": 1},
    "dissent_flags": [],
}

DEMO_PROFILE = {
    "smart_sounding_score": 0.78,
    "judgment_quality_score": 0.52,
    "smart_vs_judgment_gap": 0.26,
    "gap_label": "sounds_smarter_than_is",
    "cognitive_risk_flags": ["self_reference_closure", "low_ambiguity_tolerance"],
    "signals": {
        "self_closure": {"label": "high_self_closure", "self_closure_score": 0.72},
        "ambiguity_flexibility": {"label": "low_flexibility_choose_side", "ambiguity_flexibility_score": 0.28},
        "experience_grounding": {"label": "concept_driven", "experience_grounding_score": 0.22},
    },
}

DEMO_HARD_TRUTH = {
    "mode_level": 2,
    "mode_name": "判断优先",
    "trigger_reason": "smart_sounding高但judgment_quality低，切换判断优先模式。",
}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate AI Judge HTML verdict report")
    parser.add_argument("--demo", action="store_true", help="Generate demo report")
    parser.add_argument("--output", default="verdict_report.html", help="Output file path")
    parser.add_argument("--verdict-file", help="Path to verdict JSON file")
    parser.add_argument("--profile-file", help="Path to neuro profile JSON file")
    args = parser.parse_args()

    if args.demo:
        html = generate_verdict_html(
            verdict_data=DEMO_VERDICT,
            profile=DEMO_PROFILE,
            hard_truth=DEMO_HARD_TRUTH,
            question="Is this pricing strategy competitive for Q3 launch?",
            run_id="demo-run-001",
        )

        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Demo report saved to {args.output}")

    elif args.verdict_file:
        verdict_data = json.loads(Path(args.verdict_file).read_text())

        profile = None
        if args.profile_file:
            profile = json.loads(Path(args.profile_file).read_text())

        html = generate_verdict_html(verdict_data=verdict_data, profile=profile)
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Report saved to {args.output}")

    else:
        print("Use --demo or --verdict-file <path>")
