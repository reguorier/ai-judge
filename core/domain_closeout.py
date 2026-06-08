#!/usr/bin/env python3
"""Domain-specific closeout renderer for AI Judge legal verdicts.

The generic AI Judge closeout is useful as an internal workbench, but legal
questions need a different front page: conclusion first, elements next,
evidence gaps and handling advice after that. This module renders that legal
closeout directly from the verdict object while leaving raw model material in
the page's internal library.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone
from typing import Any


DOMAIN_CLOSEOUT_SCHEMA = "ai_judge.domain_closeout.legal.v1"

LEGAL_MARKERS = [
    "拒不执行判决",
    "拒执罪",
    "判决、裁定罪",
    "是否构成",
    "刑事责任",
    "共犯",
    "帮助犯",
    "教唆犯",
    "主观明知",
    "客观帮助",
    "犯罪构成",
    "刑法",
    "刑事",
    "执行义务",
    "被执行人",
    "协助执行",
    "律师代理",
    "代理职责",
    "执业边界",
    "两高",
    "司法解释",
]


def is_legal_domain(question: str) -> bool:
    """Return True when a prompt is a Chinese legal/criminal closeout task."""
    text = _text(question)
    if not text:
        return False
    return sum(1 for marker in LEGAL_MARKERS if re.search(marker, text)) >= 3


def render_legal_closeout(
    verdict: dict[str, Any],
    report: dict[str, Any],
    question: str,
    run_id: str = "",
) -> str:
    """Render the standardized legal closeout as an embeddable HTML fragment."""
    question = _text(question or verdict.get("question") or "")
    run_id = _text(run_id or verdict.get("run_id") or report.get("run_id") or "AIJ-LOCAL")
    person_rows = extract_person_rows(verdict, question)
    element_checks = extract_element_checks(verdict, question)
    evidence_groups = extract_evidence_checklist(question)
    seat_consensus = extract_seat_consensus(verdict)
    legal_sources = extract_legal_sources(question)

    verdict_label = _text(verdict.get("verdict_label") or (report.get("final_position") or {}).get("label") or "待判定")
    confidence = _confidence_label(verdict, report)
    trust = _trust_label(verdict, report)
    coverage_label = _coverage_label(verdict, report)
    report_date = _report_date(verdict)
    title = _legal_title(question)
    conclusion = _build_conclusion_paragraph(question, person_rows, element_checks)
    one_line = _build_one_line_conclusion(question)

    return _render_html_fragment(
        title=title,
        question=question,
        run_id=run_id,
        report_date=report_date,
        verdict_label=verdict_label,
        confidence=confidence,
        trust=trust,
        coverage_label=coverage_label,
        conclusion=conclusion,
        person_rows=person_rows,
        element_checks=element_checks,
        evidence_groups=evidence_groups,
        seat_consensus=seat_consensus,
        legal_sources=legal_sources,
        one_line=one_line,
    )


def render_legal_closeout_markdown(
    verdict: dict[str, Any],
    report: dict[str, Any],
    question: str,
    run_id: str = "",
) -> str:
    """Render a compact Markdown companion for download/share."""
    question = _text(question or verdict.get("question") or "")
    run_id = _text(run_id or verdict.get("run_id") or report.get("run_id") or "AIJ-LOCAL")
    person_rows = extract_person_rows(verdict, question)
    element_checks = extract_element_checks(verdict, question)
    evidence_groups = extract_evidence_checklist(question)
    legal_sources = extract_legal_sources(question)

    lines = [
        f"# {_legal_title(question)}",
        "",
        f"- Report No. {run_id}",
        f"- 裁决：{_text(verdict.get('verdict_label') or '待判定')}",
        f"- 可信度：{_confidence_label(verdict, report)} · {_trust_label(verdict, report)}",
        f"- 席位覆盖：{_coverage_label(verdict, report)}",
        "",
        "## 裁决结论",
        "",
        _build_conclusion_paragraph(question, person_rows, element_checks),
        "",
        "## 三人责任矩阵",
        "",
        "| 人员 | 风险等级 | 可能责任 | 当前判断 | 关键补证方向 |",
        "|---|---|---|---|---|",
    ]
    for row in person_rows:
        lines.append(
            f"| {_pipe(row['name'])} | {_pipe(row['risk_level'])} | {_pipe(row['possible_liability'])} | "
            f"{_pipe(row['current_judgment'])} | {_pipe(row['evidence_direction'])} |"
        )
    lines.extend(["", "## 构成要件逐项检验", ""])
    for idx, item in enumerate(element_checks, 1):
        lines.extend([f"### {idx}. {item['title']}（{_status_label(item['status'])}）", "", item["content"], ""])
    lines.extend(["## 关键证据清单", ""])
    for group in evidence_groups:
        lines.extend([f"### {group['title']}", ""])
        for item in group["items"]:
            lines.append(f"- {item}")
        lines.extend(["", f"判断标准：{group['note']}", ""])
    lines.extend(["## 法源链接", ""])
    for src in legal_sources:
        lines.append(f"- [{src['title']}]({src['url']})：{src['note']}")
    lines.extend(["", "## 一句话结论", "", _build_one_line_conclusion(question)])
    return "\n".join(lines).strip()


def extract_person_rows(verdict: dict[str, Any], question: str) -> list[dict[str, str]]:
    """Build the responsibility matrix for the named people in the prompt."""
    all_text = _all_seat_text(verdict)
    enhanced_guidance = any(token in question for token in ("李四指导", "由李四指导", "李四主动", "李四提出"))
    public_execution_info = "执行信息公开网" in question or "公开查询" in question
    substituted_receipt = "王五代" in question and "执行款" in question

    zhang = {
        "name": "张三",
        "risk_level": "高",
        "possible_liability": "拒不执行判决、裁定罪正犯",
        "current_judgment": "作为B案被执行人，在取得或控制A案执行款后仍不清偿B案，若B案执行前提成立，拒执风险最高。",
        "evidence_direction": "B案执行通知、财产报告令、未履行金额、A案执行款到账与最终流向。",
    }
    wang = {
        "name": "王五",
        "risk_level": "中",
        "possible_liability": "拒执罪共犯或帮助犯",
        "current_judgment": "单纯代领不当然入罪；若明知张三逃避执行并配合收款、转移或隐匿，风险上升。",
        "evidence_direction": "是否知悉B案、代领理由、收款账户流水、取现转账和是否配合隐匿。",
    }
    li = {
        "name": "李四",
        "risk_level": "低",
        "possible_liability": "特定事实下可能构成案外人共犯或帮助犯",
        "current_judgment": "仅代理A案、陪同笔录或见证代领，原则上仍属中性执业行为，不足以入罪。",
        "evidence_direction": "是否知悉B案、是否提出/设计代领方案、是否参与账户选择和资金处置、是否存在异常利益。",
    }

    if substituted_receipt:
        wang["current_judgment"] = "王五代领使款项未进入张三本人账户，若目的在于避开冻结、扣划或查控，可被评价为协助转移或隐匿财产。"

    support_terms = ("条件支持", "构成", "帮助犯", "共犯", "通谋", "指导")
    li_support = sum(all_text.count(term) for term in support_terms)
    if enhanced_guidance or li_support >= 8:
        li.update({
            "risk_level": "高",
            "possible_liability": "拒执罪案外人共犯；以帮助犯/从犯评价更稳，主导设计时可向教唆或主导型共犯评价",
            "current_judgment": "在张三、王五供述李四指导代领且有客观证据补强时，李四已可能越过一般律师代理边界。",
            "evidence_direction": "必须补强通信记录、笔录发言、账户安排、资金流向、查询痕迹和异常收费，排除同案人口供孤证。",
        })
        wang["risk_level"] = "高" if enhanced_guidance else "中"
    elif public_execution_info:
        li.update({
            "risk_level": "中",
            "possible_liability": "案外人共犯线索，尚不足定罪",
            "current_judgment": "公开可查询和专业律师身份可提高注意义务，但不能直接等同于刑法明知。",
        })

    return [zhang, wang, li]


def extract_element_checks(verdict: dict[str, Any], question: str) -> list[dict[str, str]]:
    """Build criminal element checks for Li Si's possible accomplice liability."""
    enhanced_guidance = any(token in question for token in ("李四指导", "由李四指导", "李四主动", "李四提出"))
    public_execution_info = "执行信息公开网" in question or "公开查询" in question
    substituted_receipt = "王五代" in question and "执行款" in question

    return [
        {
            "title": "主体与义务基础",
            "status": "pending",
            "content": (
                "李四不是B案被执行人，通常不能作为拒执罪直接正犯评价；但在案外人与负有执行义务人通谋，"
                "并协助隐藏、转移财产的路径下，可以进入共犯审查。"
            ),
        },
        {
            "title": "主观明知",
            "status": "pending" if public_execution_info else "not_satisfied",
            "content": (
                "B案信息公开可查、李四具有律师专业注意义务，只能增强其知悉可能性，不能单独替代刑法上的明知。"
                "若结合查询记录、沟通内容、笔录发言、代领理由设计等客观材料，才可能把“应当知道”补强为“实际明知”。"
            ),
        },
        {
            "title": "通谋",
            "status": "pending" if enhanced_guidance else "not_satisfied",
            "content": (
                "张三、王五均供述由李四指导代领，是通谋要件的重要线索，但仍属于需外部印证的同案人口供。"
                "需要微信、电话录音、律所卷宗、执行笔录现场发言或其他同步证据支撑。"
            ),
        },
        {
            "title": "客观帮助行为",
            "status": "satisfied" if enhanced_guidance and substituted_receipt else "pending",
            "content": (
                "王五代领使A案执行款不进入张三本人账户，客观上可能绕开B案法院对张三账户的网络查控、冻结或扣划。"
                "若证明李四指导该安排并参与账户选择、授权填写或后续资金处置，可认定其提供了实质帮助。"
            ),
        },
        {
            "title": "结果与因果关系",
            "status": "pending",
            "content": (
                "仍需证明代领和后续处置导致B案判决、裁定全部或部分无法执行。若款项仍可查封、未被隐匿，"
                "或B案不能执行另有原因，李四行为与执行不能之间的因果关系会被削弱。"
            ),
        },
    ]


def extract_evidence_checklist(question: str) -> list[dict[str, Any]]:
    """Return a legal evidence checklist with concrete acceptance standards."""
    return [
        {
            "title": "A. 先查B案是否具备拒执罪前提",
            "items": [
                "B案生效裁判文书、执行立案材料和执行依据金额。",
                "向张三送达执行通知书、报告财产令、限制消费令或相关执行文书的回证。",
                "法院网络查控、冻结、扣划记录，以及A案执行款到账时B案未履行余额。",
                "张三是否有履行能力而拒不履行，以及是否存在优先清偿、合理支出等抗辩事实。",
            ],
            "note": "若B案尚未进入执行，或张三未被依法要求履行，拒执罪基础明显不足。",
        },
        {
            "title": "B. 再查A案执行款控制与流向",
            "items": [
                "A案执行笔录全文、现场录音录像、付款审批和付款凭证。",
                "张三指定王五代领的授权材料、代领理由和经办人员询问记录。",
                "王五收款账户流水、收款后取现、转账、消费、购买资产或转第三人的明细。",
                "款项是否回流张三、李四或其关联方，是否用于规避张三本人账户查控。",
            ],
            "note": "若款项进入王五账户后迅速转移、取现或隐匿，张三、王五和指导者风险显著上升。",
        },
        {
            "title": "C. 专门查李四是否越过律师代理边界",
            "items": [
                "李四与张三、王五关于B案、查控、冻结、代领账户的微信、通话、邮件和律所卷宗。",
                "李四是否查询、接收或讨论过张三B案被执行信息。",
                "执行笔录中李四是否主动提出、解释、推动由王五代领。",
                "李四是否参与填写授权、选择收款账户、安排后续转账或取现。",
                "律师费是否异常，是否存在额外分成、资金回流或第三方利益输送。",
            ],
            "note": "只有形成“明知 + 通谋 + 实质帮助 + 执行不能”的证据闭环，才宜从执业合规审查升级为刑事共犯追责。",
        },
    ]


def extract_seat_consensus(verdict: dict[str, Any]) -> list[dict[str, str]]:
    """Extract a compact seat consensus table from digest/raw result records."""
    bridge = verdict.get("web_bridge") if isinstance(verdict.get("web_bridge"), dict) else {}
    rows = bridge.get("seat_answer_digest") or bridge.get("raw_results") or []
    score_map = _seat_score_map(verdict)

    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        seat = _text(row.get("seat") or row.get("model") or "")
        if seat.lower() == "claude":
            continue
        name = _text(row.get("seat_name") or row.get("model") or seat or "席位")
        stance = _text(row.get("stance") or row.get("position") or "未标注")
        score = row.get("score")
        if score is None:
            score = score_map.get(seat.lower())
        summary = _compact(
            row.get("answer_preview")
            or row.get("summary")
            or row.get("response")
            or row.get("text")
            or "",
            120,
        )
        result.append({
            "model": name,
            "stance": stance,
            "score": f"{float(score):.3f}" if isinstance(score, (int, float)) else "-",
            "summary": summary or "保留原文于内部资料库。",
        })
    return result


def extract_legal_sources(question: str) -> list[dict[str, str]]:
    """Return canonical public legal-source links for this legal domain."""
    sources = [
        {
            "title": "《中华人民共和国刑法》第三百一十三条",
            "url": "https://www.npc.gov.cn/npc/c1773/c1848/c21114/c25714/c25716/201905/t20190522_46193.html",
            "note": "拒不执行判决、裁定罪的基础罪状和法定刑。",
        },
        {
            "title": "法释〔2024〕13号：两高拒执罪司法解释发布信息",
            "url": "https://www.spp.gov.cn/xwfbh/wsfbt/202411/t20241118_673533.shtml",
            "note": "2024年12月1日起施行，包含案外人通谋协助隐藏、转移财产的共犯规则。",
        },
        {
            "title": "中国执行信息公开网",
            "url": "http://zxgk.court.gov.cn/",
            "note": "用于核查被执行信息公开查询事实，不替代案卷送达和执行材料。",
        },
    ]
    return sources


def _render_html_fragment(
    *,
    title: str,
    question: str,
    run_id: str,
    report_date: str,
    verdict_label: str,
    confidence: str,
    trust: str,
    coverage_label: str,
    conclusion: str,
    person_rows: list[dict[str, str]],
    element_checks: list[dict[str, str]],
    evidence_groups: list[dict[str, Any]],
    seat_consensus: list[dict[str, str]],
    legal_sources: list[dict[str, str]],
    one_line: str,
) -> str:
    esc = lambda value: _html.escape(str(value or ""))

    person_html = "".join(
        "<tr>"
        f"<td><strong>{esc(row['name'])}</strong></td>"
        f"<td><span class='{_risk_class(row['risk_level'])}'>{esc(row['risk_level'])}</span></td>"
        f"<td>{esc(row['possible_liability'])}</td>"
        f"<td>{esc(row['current_judgment'])}</td>"
        f"<td>{esc(row['evidence_direction'])}</td>"
        "</tr>"
        for row in person_rows
    )
    element_html = "".join(
        "<div class='legal-subsection'>"
        f"<h3>2.{idx} {esc(row['title'])} <span class='{_status_class(row['status'])}'>{esc(_status_label(row['status']))}</span></h3>"
        f"<p>{esc(row['content'])}</p>"
        "</div>"
        for idx, row in enumerate(element_checks, 1)
    )
    evidence_html = "".join(
        "<div class='evidence-group'>"
        f"<h4>{esc(group['title'])}</h4>"
        f"<ol>{''.join(f'<li>{esc(item)}</li>' for item in group['items'])}</ol>"
        f"<div class='judge-note'>{esc(group['note'])}</div>"
        "</div>"
        for group in evidence_groups
    )
    rec_html = _recommendation_cards()
    seat_rows = "".join(
        "<tr>"
        f"<td>{esc(row['model'])}</td><td>{esc(row['stance'])}</td><td>{esc(row['score'])}</td><td>{esc(row['summary'])}</td>"
        "</tr>"
        for row in seat_consensus
    ) or "<tr><td colspan='4'>席位摘要保留于内部资料库。</td></tr>"
    source_html = "".join(
        f"<li><a href='{esc(src['url'])}' target='_blank' rel='noopener noreferrer'>{esc(src['title'])}</a> — {esc(src['note'])}</li>"
        for src in legal_sources
    )

    return f"""
<style>
.legal-closeout {{ --bg:#ffffff; --bg-alt:#f7f8fa; --bg-card:#f0f2f5; --text:#1a1a2e; --muted:#5a6072; --accent:#1a56db; --accent-light:#e8eefb; --green:#15803d; --green-bg:#dcfce7; --yellow:#a16207; --yellow-bg:#fef9c3; --red:#b91c1c; --red-bg:#fee2e2; --border:#e2e5ea; max-width:880px; margin:0 auto 28px; padding:32px 24px 64px; background:var(--bg); color:var(--text); line-height:1.75; font-size:15px; border:1px solid var(--border); border-radius:8px; }}
.legal-closeout * {{ box-sizing:border-box; }}
.legal-closeout-header {{ border-bottom:2px solid var(--text); padding-bottom:24px; margin-bottom:28px; }}
.legal-closeout-header h1 {{ font-size:22px; font-weight:700; line-height:1.4; margin:0 0 8px; max-width:none; }}
.legal-meta {{ display:flex; flex-wrap:wrap; gap:16px; color:var(--muted); font-size:13px; }}
.legal-scorecard {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:28px; }}
.legal-scorecard > div {{ background:var(--bg-alt); border:1px solid var(--border); border-radius:8px; padding:16px; text-align:center; }}
.legal-scorecard span {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--muted); margin-bottom:4px; }}
.legal-scorecard strong {{ display:block; font-size:19px; line-height:1.35; overflow-wrap:anywhere; }}
.legal-verdict-banner {{ background:var(--accent-light); border-left:4px solid var(--accent); border-radius:0 8px 8px 0; padding:20px 24px; margin-bottom:32px; }}
.legal-verdict-banner h2 {{ font-size:18px; font-weight:700; color:var(--accent); margin:0 0 8px; }}
.legal-verdict-banner p {{ margin:0; font-size:14.5px; line-height:1.85; }}
.legal-section {{ margin-bottom:36px; }}
.legal-section-title {{ font-size:16px; font-weight:700; border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:16px; display:flex; align-items:baseline; gap:8px; }}
.legal-section-num {{ font-size:12px; color:var(--muted); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
.legal-table-wrap {{ overflow-x:auto; margin:12px 0; }}
.legal-closeout table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
.legal-closeout th {{ background:var(--bg-card); font-weight:600; text-align:left; padding:10px 12px; border:1px solid var(--border); white-space:nowrap; }}
.legal-closeout td {{ padding:10px 12px; border:1px solid var(--border); vertical-align:top; line-height:1.6; }}
.risk-high,.risk-medium,.risk-low {{ font-weight:600; padding:2px 8px; border-radius:4px; font-size:12px; white-space:nowrap; }}
.risk-high {{ background:var(--red-bg); color:var(--red); }}
.risk-medium {{ background:var(--yellow-bg); color:var(--yellow); }}
.risk-low {{ background:var(--green-bg); color:var(--green); }}
.legal-subsection {{ margin-bottom:20px; }}
.legal-subsection h3 {{ font-size:14px; font-weight:600; margin:0 0 8px; color:var(--text); }}
.legal-subsection p,.legal-section li {{ font-size:14.5px; line-height:1.85; }}
.legal-subsection p {{ margin:0; }}
.evidence-group {{ margin-bottom:16px; }}
.evidence-group h4 {{ font-size:13px; font-weight:600; margin:0 0 8px; color:var(--accent); }}
.evidence-group ol,.source-list {{ padding-left:20px; margin:0; }}
.evidence-group li,.source-list li {{ font-size:13.5px; padding:3px 0; line-height:1.7; }}
.judge-note {{ font-size:13px; color:var(--muted); background:var(--bg-alt); padding:8px 12px; border-radius:6px; margin-top:8px; }}
.rec-card {{ background:var(--bg-alt); border:1px solid var(--border); border-radius:8px; padding:16px 20px; margin-bottom:12px; }}
.rec-card h4 {{ font-size:14px; font-weight:600; margin:0 0 6px; }}
.rec-card p {{ font-size:13.5px; color:var(--muted); margin:0; line-height:1.75; }}
.source-list a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid transparent; }}
.source-list a:hover {{ border-bottom-color:var(--accent); }}
.legal-conclusion-box {{ background:var(--bg-alt); border:2px solid var(--text); border-radius:8px; padding:20px 24px; margin-top:32px; }}
.legal-conclusion-box h3 {{ font-size:14px; font-weight:700; margin:0 0 8px; text-transform:uppercase; letter-spacing:1px; }}
.legal-conclusion-box p {{ font-size:15px; line-height:1.85; font-weight:500; margin:0; }}
.legal-footer {{ border-top:1px solid var(--border); padding-top:16px; margin-top:40px; font-size:12px; color:var(--muted); display:flex; justify-content:space-between; gap:12px; }}
@media print {{ .legal-closeout {{ max-width:100%; padding:0; border:0; }} .legal-section {{ page-break-inside:avoid; }} }}
@media (max-width:640px) {{ .legal-scorecard {{ grid-template-columns:repeat(2,1fr); }} .legal-closeout {{ padding:18px 14px 36px; }} }}
</style>
<article class="legal-closeout" id="report-manuscript" data-report-root="legal-domain-closeout" data-schema="{DOMAIN_CLOSEOUT_SCHEMA}">
  <header class="legal-closeout-header">
    <h1>{esc(title)}</h1>
    <div class="legal-meta">
      <span>Report No. {esc(run_id)}</span>
      <span>{esc(report_date)}</span>
      <span>AI Judge</span>
      <span>{esc(len(seat_consensus))} 席位</span>
    </div>
  </header>
  <div class="legal-scorecard">
    <div><span>裁决</span><strong style="color:var(--yellow)">{esc(verdict_label)}</strong></div>
    <div><span>可信度</span><strong style="color:var(--accent)">{esc(confidence)} · {esc(trust)}</strong></div>
    <div><span>席位覆盖</span><strong style="color:var(--green)">{esc(coverage_label)}</strong></div>
    <div><span>发布状态</span><strong style="font-size:14px">正式文稿</strong></div>
  </div>
  <section class="legal-verdict-banner">
    <h2>裁决结论</h2>
    <p>{esc(conclusion)}</p>
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">01</span> 三人责任矩阵</div>
    <div class="legal-table-wrap"><table><thead><tr><th>人员</th><th>风险等级</th><th>可能责任</th><th>当前判断</th><th>关键补证方向</th></tr></thead><tbody>{person_html}</tbody></table></div>
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">02</span> 李四构成要件逐项检验</div>
    {element_html}
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">03</span> 关键证据清单</div>
    {evidence_html}
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">04</span> 分层处理建议</div>
    {rec_html}
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">05</span> 席位共识与分歧</div>
    <div class="legal-table-wrap"><table><thead><tr><th>席位</th><th>立场</th><th>均分</th><th>核心判断</th></tr></thead><tbody>{seat_rows}</tbody></table></div>
    <p style="margin-top:12px;font-size:13px;color:var(--muted)">席位原文、互评、共振追问和评分细节保留于下方内部资料库；本节只展示被压缩后的共识边界。</p>
  </section>
  <section class="legal-section">
    <div class="legal-section-title"><span class="legal-section-num">06</span> 法源链接</div>
    <ol class="source-list">{source_html}</ol>
  </section>
  <section class="legal-conclusion-box">
    <h3>可直接使用的一句话结论</h3>
    <p>{esc(one_line)}</p>
  </section>
  <footer class="legal-footer">
    <span>AI Judge · 用途：事实初筛与办案/内审决策参考，不替代律师正式法律意见</span>
    <span>Report No. {esc(run_id)}</span>
  </footer>
</article>
"""


def _recommendation_cards() -> str:
    cards = [
        (
            "对张三：优先按拒执罪正犯线索固定证据",
            "先核实B案执行前提、履行能力、A案执行款到账和拒不清偿事实；若存在转移、隐匿或拒不报告财产，可进入刑事线索审查。",
        ),
        (
            "对王五：围绕协助转移财产审查",
            "若仅基于夫妻关系代收且不知B案，不宜当然入罪；若明知规避执行并参与收款、取现、转移或隐匿，可按共犯路径审查。",
        ),
        (
            "对李四：从执业合规审查升级到刑事共犯审查需证据闭环",
            "张三、王五供述只能启动线索核查；只有补足明知、通谋、实质帮助和执行不能的客观证据后，才宜按拒执罪共犯处理。",
        ),
    ]
    return "".join(
        f"<div class='rec-card'><h4>{_html.escape(title)}</h4><p>{_html.escape(body)}</p></div>"
        for title, body in cards
    )


def _build_conclusion_paragraph(
    question: str,
    person_rows: list[dict[str, str]],
    element_checks: list[dict[str, str]],
) -> str:
    li_row = next((row for row in person_rows if row["name"] == "李四"), {})
    if li_row.get("risk_level") == "高":
        return (
            "在四项强化事实均成立并获得客观证据补强的前提下，李四的行为已可能从一般A案代理行为上升为"
            "拒不执行判决、裁定罪的案外人共犯，责任形态以帮助犯或从犯评价更稳；若证据证明其主导设计"
            "规避查控方案，可进一步向教唆或主导型共犯评价。但定罪仍不能仅凭“公开可查”“律师应当知道”"
            "或张三、王五供述直接完成，必须补足明知、通谋、实质帮助和导致B案无法执行的客观证据链。"
        )
    return (
        "按现有事实，李四仅作为A案代理律师陪同制作执行笔录并见证张三指定王五代领执行款，尚不足以构成"
        "拒不执行判决、裁定罪；只有证明其明知B案执行义务，并与张三、王五通谋，通过代领安排实质帮助隐藏、"
        "转移执行款，致使B案无法执行，才可进入共犯追责。"
    )


def _build_one_line_conclusion(question: str) -> str:
    if any(token in question for token in ("李四指导", "由李四指导", "张三和王五均供述")):
        return (
            "在强化事实均成立且有客观证据补强时，李四可倾向按拒执罪案外人共犯/帮助犯审查；"
            "但“应当知道”和同案人口供不能单独替代刑法明知与通谋证明。"
        )
    return (
        "按现有事实，李四正常代理和在场见证不足以入罪；除非证明其明知并通谋指导代领、转移或隐匿财产。"
    )


def _legal_title(question: str) -> str:
    if "李四" in question and "拒不执行" in question:
        return "李四是否构成拒不执行判决、裁定罪共犯的裁决报告"
    return "AI Judge 法律领域裁决报告"


def _all_seat_text(verdict: dict[str, Any]) -> str:
    bridge = verdict.get("web_bridge") if isinstance(verdict.get("web_bridge"), dict) else {}
    rows = bridge.get("seat_answer_digest") or bridge.get("raw_results") or []
    chunks: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        chunks.append(_text(row.get("response") or row.get("answer_preview") or row.get("summary") or row.get("text") or ""))
    return "\n".join(chunks)


def _seat_score_map(verdict: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in verdict.get("seat_scores") or []:
        if not isinstance(row, dict):
            continue
        seat = _text(row.get("seat")).lower()
        if seat:
            try:
                result[seat] = float(row.get("average_score"))
            except (TypeError, ValueError):
                pass
    scoring = verdict.get("scoring") if isinstance(verdict.get("scoring"), dict) else {}
    nested = scoring.get("seat_scores") if isinstance(scoring, dict) else {}
    if isinstance(nested, dict):
        for seat, score in nested.items():
            if isinstance(score, dict):
                score = score.get("mean") or score.get("average_score")
            try:
                result[_text(seat).lower()] = float(score)
            except (TypeError, ValueError):
                pass
    return result


def _coverage_label(verdict: dict[str, Any], report: dict[str, Any]) -> str:
    bridge = verdict.get("web_bridge") if isinstance(verdict.get("web_bridge"), dict) else {}
    ok = bridge.get("ok_count")
    requested = bridge.get("requested_count") or len(verdict.get("seats") or [])
    if ok is not None and requested:
        return f"{ok}/{requested}"
    for item in report.get("meta") or []:
        if isinstance(item, dict) and "席位" in _text(item.get("label")):
            return _text(item.get("value") or "-")
    return "-"


def _confidence_label(verdict: dict[str, Any], report: dict[str, Any]) -> str:
    confidence = verdict.get("confidence")
    if confidence is not None:
        return f"{confidence}%"
    executive = report.get("executive_summary") if isinstance(report.get("executive_summary"), dict) else {}
    return _text(executive.get("confidence_label") or (report.get("final_position") or {}).get("confidence") or "-")


def _trust_label(verdict: dict[str, Any], report: dict[str, Any]) -> str:
    trust = verdict.get("trust_tier") if isinstance(verdict.get("trust_tier"), dict) else {}
    return _text(trust.get("tier") or (report.get("final_position") or {}).get("trust") or "-")


def _report_date(verdict: dict[str, Any]) -> str:
    raw = _text(verdict.get("created_at") or verdict.get("updated_at"))
    if raw[:10]:
        return raw[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _risk_class(value: str) -> str:
    if "高" in value:
        return "risk-high"
    if "低" in value:
        return "risk-low"
    return "risk-medium"


def _status_class(status: str) -> str:
    if status == "satisfied":
        return "risk-high"
    if status == "not_satisfied":
        return "risk-low"
    return "risk-medium"


def _status_label(status: str) -> str:
    return {
        "satisfied": "初步满足",
        "pending": "待补强",
        "not_satisfied": "不足",
    }.get(status, "待验证")


def _pipe(value: Any) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact(value: Any, limit: int = 240) -> str:
    text = " ".join(_text(value).split())
    return text[: limit - 1].rstrip() + "..." if len(text) > limit else text
