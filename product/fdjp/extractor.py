"""FDJP structured heuristic extractor.

This layer is deliberately not an LLM and not five role-playing agents. It
turns seat answers into traceable assertions, then lets five small dimension
functions evaluate those assertions as constraints.
"""

from __future__ import annotations

import hashlib
from typing import Any

from product.fdjp.assertions import build_assertion_packet
from product.fdjp.constants import (
    CORE_QUESTIONS,
    DIMENSION_LABELS,
    DIMENSIONS,
    HEURISTIC_KEYWORDS,
)
from product.fdjp.schemas import (
    DimensionFinding,
    DimensionReport,
)


DIMENSION_SPECS: dict[str, dict[str, Any]] = {
    "philosophy": {
        "constraint": "元问题约束：定义清楚、本质可解释、判断标准一致，并防止隐喻/角色扮演替代推理。",
        "cues": [
            "约束求解器", "本质", "定义", "判断标准", "逻辑", "一致性", "边界",
            "前提", "假设", "结构化", "可断言", "可测试", "可审计", "推理轨迹",
            "不是视角", "不是角色", "不是prompt", "玄学", "散文", "自由文本",
            "schema", "Schema", "JSON", "校验", "元问题",
        ],
        "risk_if_wrong": "若元问题约束失效，五维会退化成漂亮段落，无法判断答案是否真的解决问题。",
        "counterargument": "过强的结构约束可能压掉探索性观点，所以需要保留 assumptions 和 open_questions。",
        "action_impact": "先把每个维度的输出锁定为可验证断言，再允许进入综合报告。",
        "open_question": "哪些判断属于不可回答、需人类确认或需外部证据补齐？",
    },
    "economy": {
        "constraint": "资源约束：识别利益链、成本结构、稀缺资源、收益方和隐形成本。",
        "cues": [
            "利益", "成本", "收益", "资源", "稀缺", "ROI", "投入", "产出",
            "隐形成本", "利益链", "成本结构", "激励", "预算", "效率", "代价",
            "谁受益", "谁承担", "分配", "交换", "约束条件",
        ],
        "risk_if_wrong": "若资源约束缺失，方案会看起来正确但无法落地，或把成本转嫁给看不见的角色。",
        "counterargument": "早期 MVP 不能过度量化，否则会把真实学习速度误判为短期 ROI。",
        "action_impact": "把每条建议绑定资源、成本、收益方和隐性代价。",
        "open_question": "当前方案最稀缺的资源是工程时间、模型调用、数据质量，还是验证样本？",
    },
    "politics": {
        "constraint": "权力约束：识别话语权、规则制定者、否决点、组织阻力和治理边界。",
        "cues": [
            "权力", "话语权", "规则", "治理", "组织", "阻力", "边缘", "权限",
            "否决", "审批", "责任", "归属", "协调", "联盟", "角色", "边界",
            "制定者", "影响力", "权责", "人工确认", "gate", "Gate",
        ],
        "risk_if_wrong": "若权力约束缺失，系统可能给出无人有权执行、无人愿意维护的答案。",
        "counterargument": "过早引入治理层会拖慢 MVP，所以首版只保留最小否决点和人工 gate。",
        "action_impact": "显式标出谁能改规则、谁能否决、谁负责最终放行。",
        "open_question": "哪些 FDJP 结论必须由 human final gate 覆核后才能发布？",
    },
    "military": {
        "constraint": "执行约束：在资源有限和风险存在时，确定目标、主攻点、优先级、行动顺序和预案。",
        "cues": [
            "策略", "战略", "执行", "行动", "MVP", "优先级", "主攻", "部署",
            "步骤", "路线图", "阶段", "失败预案", "风险", "机动", "时机",
            "快速", "决策", "回滚", "验收", "测试", "最小可行", "P0", "P1", "P2",
        ],
        "risk_if_wrong": "若执行约束缺失，系统会生成正确愿景但没有可落地的下一步和失败预案。",
        "counterargument": "执行层不能抢在哲学层之前定目标，否则会把错误 framing 快速工程化。",
        "action_impact": "把方案拆成 MVP/P1/P2，并为每段绑定验收和回滚条件。",
        "open_question": "首个可发布版本最小需要哪三条断言字段和哪两个门控？",
    },
    "history": {
        "constraint": "时间约束：检索先例、周期、演化路径和类比偏差，防止被当下现象绑架。",
        "cues": [
            "历史", "时间", "先例", "案例", "周期", "类比", "演化", "趋势",
            "过往", "阶段", "路线图", "复盘", "模式", "偏差", "参照", "经验",
            "回归测试", "版本", "MVP", "P1", "P2",
        ],
        "risk_if_wrong": "若时间约束缺失，系统容易把新鲜表象当作新问题，也容易复刻旧失败。",
        "counterargument": "历史类比只能提供候选参照，不能替代当前证据和约束求解。",
        "action_impact": "给每条历史参照标记相似点、差异点、可迁移条件和类比风险。",
        "open_question": "哪些既有 AI Judge 失败 run 可以变成 FDJP 的回归样本？",
    },
}


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8", "ignore")
    return hashlib.sha1(raw).hexdigest()[:10]


def _clean_text(text: Any) -> str:
    return " ".join(str(text or "").split()).strip()


def _truncate(text: str, limit: int = 240) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _matching_cues(text: str, dim: str) -> list[str]:
    spec_cues = DIMENSION_SPECS[dim]["cues"]
    cues = list(dict.fromkeys([*HEURISTIC_KEYWORDS.get(dim, []), *spec_cues]))
    lowered = text.lower()
    return [cue for cue in cues if cue.lower() in lowered]


def _record_score(record: dict[str, Any], dim: str) -> tuple[float, list[str]]:
    text = record["text"]
    matches = _matching_cues(text, dim)
    score = len(matches) * 1.0
    label_signals = {
        "philosophy": ("哲学", "元问题", "底层架构"),
        "economy": ("经济", "资源约束", "利益成本"),
        "politics": ("政治", "权力坐标", "治理"),
        "military": ("军事", "战略执行", "执行层"),
        "history": ("历史", "时间参照", "周期"),
    }
    if any(signal in text for signal in label_signals[dim]):
        score += 2.0
    if dim == "philosophy" and ("每个维度" in text or "五维" in text) and (
        "约束" in text or "结构化" in text or "可测试" in text or "审计" in text
    ):
        score += 2.0
        if "五维元约束" not in matches:
            matches.append("五维元约束")
    if dim == "military" and ("MVP" in text or "P1" in text or "P2" in text):
        score += 2.0
    return score, matches


def _classify_claim_type(text: str) -> str:
    if any(cue in text for cue in ("必须", "应当", "需要", "建议", "不应", "不能", "先")):
        return "recommendation"
    if any(cue in text for cue in ("若", "否则", "风险", "失败", "容易", "威胁")):
        return "risk"
    if any(cue in text for cue in ("推断", "认为", "可显著", "可能", "前提")):
        return "inference"
    if any(cue in text for cue in ("事实", "当前", "已经", "现有")):
        return "fact"
    return "claim"


def _assumptions_for(dim: str, text: str) -> list[str]:
    common = "席位回答中的该断言足以代表至少一个可审计观点。"
    by_dim = {
        "philosophy": "问题可以被表达为清晰判断标准，而不是只靠自由文本解释。",
        "economy": "资源、成本和收益方可以从任务上下文中被明确标注。",
        "politics": "执行链条中存在规则制定者、否决点或责任归属。",
        "military": "方案能被拆成有顺序、有验收、有回滚的行动。",
        "history": "存在可比较的先例、周期或版本演化样本。",
    }
    assumptions = [common, by_dim[dim]]
    if "条件支持" in text:
        assumptions.append("支持结论依赖其后列出的约束条件被满足。")
    if "MVP" in text:
        assumptions.append("首版只实现最小可验证闭环，不一次性实现完整理想系统。")
    return assumptions


def _verifiability_for(dim: str) -> str:
    checks = {
        "philosophy": "检查输出是否包含问题定义、判断标准、假设、不可回答边界和证据引用。",
        "economy": "检查每条建议是否标注收益方、成本承担方、稀缺资源和隐形成本。",
        "politics": "检查是否标注规则制定者、否决点、执行责任人与 human gate。",
        "military": "检查是否存在 MVP/P1/P2、行动顺序、验收标准和失败预案。",
        "history": "检查是否给出先例、相似点、差异点、迁移条件和类比风险。",
    }
    return checks[dim]


def _finding_from_record(
    dim: str,
    record: dict[str, Any],
    matches: list[str],
    rank: int,
) -> DimensionFinding:
    spec = DIMENSION_SPECS[dim]
    text = record["text"]
    source_seats = [record["seat_id"]] if record.get("seat_id") else []
    evidence_ids = [record["evidence_id"]]
    match_count = len(set(matches))
    confidence = min(0.42 + match_count * 0.045 + record["confidence"] * 0.22, 0.78)
    claim_type = f"seat_assertion_{_classify_claim_type(text)}"
    if record.get("source_type") == "evidence":
        claim_type = f"evidence_assertion_{_classify_claim_type(text)}"
    return DimensionFinding(
        finding_id=f"fdjp-{dim}-{_stable_id(dim, record['evidence_id'], text)}",
        dimension=dim,
        claim=_truncate(text, 260),
        claim_type=claim_type,
        basis=list(dict.fromkeys([spec["constraint"], *matches[:8]])),
        confidence=round(confidence, 4),
        risk_if_wrong=spec["risk_if_wrong"],
        counterargument=spec["counterargument"],
        action_impact=spec["action_impact"],
        source_seats=source_seats,
        evidence_ids=evidence_ids,
        status="pass" if confidence >= 0.62 else "warning",
        evidence_refs=evidence_ids,
        reasoning_summary=(
            f"第 {rank} 条候选断言命中 {DIMENSION_LABELS.get(dim, dim)} "
            f"约束线索：{', '.join(matches[:5]) or 'semantic'}。"
        ),
        source="heuristic_structured",
        assumptions=_assumptions_for(dim, text),
        verifiable=_verifiability_for(dim),
        constraint=spec["constraint"],
        source_excerpt=_truncate(text, 360),
    )


def _dimension_report(dim: str, records: list[dict[str, Any]]) -> DimensionReport:
    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    seen_texts: set[str] = set()
    for record in records:
        score, matches = _record_score(record, dim)
        if score <= 0:
            continue
        normalized_text = _truncate(record["text"], 180)
        if normalized_text in seen_texts:
            continue
        seen_texts.add(normalized_text)
        scored.append((score, record, matches))

    scored.sort(key=lambda item: (item[0], item[1]["confidence"], len(item[2])), reverse=True)
    findings = [
        _finding_from_record(dim, record, matches, rank)
        for rank, (_score, record, matches) in enumerate(scored[:5], start=1)
    ]

    source_seats = sorted({
        seat
        for finding in findings
        for seat in finding.source_seats
        if seat
    })
    evidence_count = sum(len(f.evidence_ids) for f in findings)

    if findings:
        coverage_score = min(0.30 + len(findings) * 0.08 + len(source_seats) * 0.04, 0.78)
        evidence_score = min(0.25 + evidence_count * 0.06 + len(source_seats) * 0.05, 0.76)
        actionability_score = min(
            0.28
            + sum(1 for f in findings if f.verifiable) * 0.06
            + sum(1 for f in findings if f.assumptions) * 0.03,
            0.74,
        )
        score = min(
            coverage_score * 0.38 + evidence_score * 0.32 + actionability_score * 0.30,
            0.75,
        )
        status = "audited" if len(source_seats) >= 2 or len(findings) >= 2 else "partial"
        leading = findings[0].claim
        summary = (
            f"从 {len(source_seats) or 1} 个来源提取 {len(findings)} 条结构化断言；"
            f"主约束：{DIMENSION_SPECS[dim]['constraint']} 代表断言：{leading}"
        )
        risks = [DIMENSION_SPECS[dim]["risk_if_wrong"]]
    else:
        coverage_score = 0.12
        evidence_score = 0.08
        actionability_score = 0.10
        score = 0.18
        status = "insufficient"
        summary = (
            f"未从席位回答中提取到可追溯的 {DIMENSION_LABELS.get(dim, dim)} "
            "结构化断言；不能用题面关键词替代审计发现。"
        )
        risks = [f"{DIMENSION_LABELS.get(dim, dim)} 维度缺少可验证断言。"]

    return DimensionReport(
        dimension=dim,
        label=DIMENSION_LABELS.get(dim, dim),
        core_question=CORE_QUESTIONS.get(dim, ""),
        summary=summary,
        findings=findings,
        open_questions=[DIMENSION_SPECS[dim]["open_question"]],
        risks=risks,
        score=score,
        coverage_score=coverage_score,
        evidence_score=evidence_score,
        actionability_score=actionability_score,
        status=status,
    )


def analyze_philosophy(records: list[dict[str, Any]]) -> DimensionReport:
    return _dimension_report("philosophy", records)


def analyze_economy(records: list[dict[str, Any]]) -> DimensionReport:
    return _dimension_report("economy", records)


def analyze_politics(records: list[dict[str, Any]]) -> DimensionReport:
    return _dimension_report("politics", records)


def analyze_military(records: list[dict[str, Any]]) -> DimensionReport:
    return _dimension_report("military", records)


def analyze_history(records: list[dict[str, Any]]) -> DimensionReport:
    return _dimension_report("history", records)


DIMENSION_ANALYZERS = {
    "philosophy": analyze_philosophy,
    "economy": analyze_economy,
    "politics": analyze_politics,
    "military": analyze_military,
    "history": analyze_history,
}


def _first_evidence_ids(report: DimensionReport, limit: int = 2) -> list[str]:
    ids: list[str] = []
    for finding in report.findings:
        for ev_id in finding.evidence_ids:
            if ev_id not in ids:
                ids.append(ev_id)
            if len(ids) >= limit:
                return ids
    return ids


def _build_cross_dimension_conflicts(
    dimensions: dict[str, DimensionReport],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    if dimensions["philosophy"].findings and any(
        dimensions[dim].findings for dim in ("economy", "politics", "military", "history")
    ):
        conflicts.append({
            "conflict_id": "fdjp-cross-meta-constraint",
            "severity": "warning",
            "dimensions": ["philosophy", "economy", "politics", "military", "history"],
            "description": "哲学层要求结构化、可验证、可审计；其他维度的建议必须降级为断言和约束，不能直接变成散文结论。",
            "evidence_ids": _first_evidence_ids(dimensions["philosophy"], 2),
            "resolution": "综合报告只采用带 source_seats、evidence_ids、assumptions、verifiable 的断言。",
        })
    if dimensions["economy"].findings and dimensions["military"].findings:
        conflicts.append({
            "conflict_id": "fdjp-cross-resource-execution",
            "severity": "info",
            "dimensions": ["economy", "military"],
            "description": "经济层的资源/成本约束需要反向限制军事层的 MVP、优先级和行动顺序。",
            "evidence_ids": [
                *_first_evidence_ids(dimensions["economy"], 1),
                *_first_evidence_ids(dimensions["military"], 1),
            ],
            "resolution": "先落最小结构化断言闭环，再扩展图求解和 LLM 语义抽取。",
        })
    if dimensions["politics"].findings and dimensions["military"].findings:
        conflicts.append({
            "conflict_id": "fdjp-cross-governance-speed",
            "severity": "info",
            "dimensions": ["politics", "military"],
            "description": "政治层的规则/否决点可能约束执行层速度，必须保留 human gate 和发布门禁。",
            "evidence_ids": [
                *_first_evidence_ids(dimensions["politics"], 1),
                *_first_evidence_ids(dimensions["military"], 1),
            ],
            "resolution": "自动审计可给建议，但 FULL_PASS 或高风险发布必须经过明确门控。",
        })
    if dimensions["history"].findings and dimensions["philosophy"].findings:
        conflicts.append({
            "conflict_id": "fdjp-cross-analogy-validation",
            "severity": "info",
            "dimensions": ["history", "philosophy"],
            "description": "历史层提供先例和周期，但所有类比都需要哲学层检查相似点、差异点和适用边界。",
            "evidence_ids": [
                *_first_evidence_ids(dimensions["history"], 1),
                *_first_evidence_ids(dimensions["philosophy"], 1),
            ],
            "resolution": "历史参照必须附带差异点和类比风险，不能作为直接证明。",
        })
    return conflicts[:6]


def run_heuristic_dimension_audit(
    task: dict[str, Any],
    seats: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    task_type: str = "general",
) -> dict[str, Any]:
    """Run structured five-dimension audit without an LLM.

    The heuristic mode remains capped below FULL_PASS, but it now reads seat
    answers as assertions instead of emitting keyword-only findings.
    """
    assertion_packet = build_assertion_packet(seats, evidence)
    records = assertion_packet["assertions"]

    dimensions: dict[str, DimensionReport] = {}
    dim_scores: dict[str, float] = {}
    for dim in DIMENSIONS:
        report = DIMENSION_ANALYZERS[dim](records)
        dimensions[dim] = report
        dim_scores[dim] = report.score

    overall = sum(dim_scores.values()) / max(len(dim_scores), 1)
    overall = min(overall, 0.75)
    all_findings = [
        finding.to_dict()
        for dim in DIMENSIONS
        for finding in dimensions[dim].findings
    ]

    audit = {
        "run_id": task.get("run_id", ""),
        "task_id": task.get("task_id", ""),
        "task_type": task_type,
        "status": "FDJP_PASS_WITH_WARNINGS",
        "mode": "heuristic",
        "overall_score": round(overall, 4),
        "dimension_scores": {k: round(v, 4) for k, v in dim_scores.items()},
        "dimensions": {k: v.to_dict() for k, v in dimensions.items()},
        "findings": all_findings,
        "insights": [],
        "cross_dimension_conflicts": _build_cross_dimension_conflicts(dimensions),
        "gates": {},
        "report_blocks": [],
        "heuristic_metadata": {
            "extractor": "seat_assertion_constraint_v2",
            "assertion_schema": assertion_packet["schema"],
            "seat_source_count": assertion_packet["seat_source_count"],
            "evidence_source_count": assertion_packet["evidence_source_count"],
            "assertion_count": len(records),
            "finding_count": len(all_findings),
            "full_pass_cap": 0.75,
        },
        "created_at": "",
        "updated_at": "",
        "version": "FDJP-1.0",
        "schema_version": "1.1",
    }
    return audit
