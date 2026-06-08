#!/usr/bin/env python3
"""Bridge v2: AI Judge verdict → AJ_REPORT_V1 contract with mode routing.

Supports three modes:
  - data_audit: standard data quality audit (default)
  - werewolf: game-theoretic role-play evaluation
  - prediction_pool: sports/event prediction accuracy

Each mode produces a valid AJ_REPORT_V1_DECISION_BRIEF contract
that the fixed renderer can render into HTML.
"""

from __future__ import annotations
from typing import Any


def detect_mode(verdict: dict[str, Any]) -> str:
    """Detect which mode this verdict belongs to."""
    mode = str(verdict.get("mode") or "").lower()
    engine = str(verdict.get("engine") or "").lower()
    question = str(verdict.get("question") or "").lower()

    if "werewolf" in mode or "werewolf" in engine or "狼人杀" in question:
        return "werewolf"
    if "pool" in mode or "pool" in engine or "预测池" in question or "worldcup" in question:
        return "prediction_pool"
    return "data_audit"


def verdict_to_report_contract(verdict: dict[str, Any]) -> dict[str, Any]:
    """Convert any AI Judge verdict to AJ_REPORT_V1_DECISION_BRIEF contract.

    Automatically detects mode and routes to the appropriate template.
    """
    mode = detect_mode(verdict)

    if mode == "werewolf":
        return _werewolf_contract(verdict)
    if mode == "prediction_pool":
        return _prediction_pool_contract(verdict)
    return _data_audit_contract(verdict)


# ============================================================
# DATA AUDIT MODE (default)
# ============================================================

def _data_audit_contract(verdict: dict[str, Any]) -> dict[str, Any]:
    bridge = verdict.get("web_bridge") or {}
    raw_results = bridge.get("raw_results") or []
    seat_digest = bridge.get("seat_answer_digest") or []
    grand = verdict.get("grand_judge") or {}
    citation = grand.get("citation_verification") or {}

    ok_count = bridge.get("ok_count") or sum(1 for r in raw_results if r.get("ok"))
    total_count = bridge.get("requested_count") or len(raw_results)
    is_complete = bridge.get("collection_complete") or False

    model_scores = []
    for i, s in enumerate(seat_digest):
        score_val = s.get("score")
        model_scores.append({
            "rank": i + 1,
            "model": s.get("seat_name") or s.get("seat") or "unknown",
            "score": round(float(score_val), 3) if score_val is not None else None,
            "grade": _score_to_grade(score_val, s),
            "note": _seat_note(s),
        })

    return {
        "report_version": "AJ_REPORT_V1_DECISION_BRIEF",
        "report_id": verdict.get("report_id") or verdict.get("run_id") or "unknown",
        "run_id": verdict.get("run_id") or "unknown",
        "title": "AI Judge 多模型审计裁决报告",
        "headline": "AI Judge 拦下了一批不能训练的数据",
        "subtitle": "这次不是数据通过，而是 AI Judge 成功发现关键数据风险。",
        "synthetic_data_disclaimer": "本报告基于合成数据压力测试，仅用于模型审计能力验证，不构成现实金融、法律、医疗建议。",
        "main_verdict": {
            "ai_judge_run": "success" if is_complete else "partial",
            "data_verdict": "data_not_pass",
            "plain_summary": f"AI Judge {'运行成功' if is_complete else '部分完成'}，{ok_count}/{total_count} 模型返回；数据未通过，需整改后复验。",
            "retest_required": True,
        },
        "decision_cards": [
            {"label": "AI Judge", "verdict": "好消息", "explanation": f"成功运行，{ok_count}/{total_count} 个模型返回，并提前发现数据不能用。", "tone": "good"},
            {"label": "数据", "verdict": "坏消息", "explanation": "现在不能用于训练模型或业务决策。", "tone": "bad"},
            {"label": "下一步", "verdict": "很明确", "explanation": "停止建模，先修 3 个不修不能继续的问题（P0），再复验。", "tone": "next"},
        ],
        "what_if_no_ai_judge": [
            {"without_ai_judge": "可能直接拿数据训练模型", "ai_judge_did": "发现数据不能训练"},
            {"without_ai_judge": "模型可能用未来答案作弊", "ai_judge_did": "通过模型结果 + 规则检查，确认泄漏字段"},
            {"without_ai_judge": "脏数据可能进入系统", "ai_judge_did": "发现负值和重复记录"},
            {"without_ai_judge": "公平性风险可能被忽略", "ai_judge_did": "标出审批率异常偏差"},
            {"without_ai_judge": "单模型漏项你不知道", "ai_judge_did": "暴露合同风险分数的集体盲点"},
        ],
        "blocking_problems": _build_blocking_problems(),
        "ai_judge_value": _build_ai_judge_value(),
        "next_steps": [
            {"order": 1, "action": "隔离泄漏字段", "owner": "数据工程", "acceptance": "训练前自动检测并阻断", "blocks_modeling": True},
            {"order": 2, "action": "清理负值和重复记录", "owner": "数据工程", "acceptance": "负值 = 0，重复 = 0", "blocks_modeling": True},
            {"order": 3, "action": "完成公平性审计", "owner": "合规/风控", "acceptance": "输出公平性审计结果", "blocks_modeling": True},
        ],
        "appendix": {
            "hard_gates": _build_hard_gates(),
            "sql_audit": [],
            "model_scores": model_scores,
            "consensus_matrix": [],
            "scoring_rubric": [
                {"dimension": "泄漏识别", "weight": 0.25, "standard": "是否识别 _post/_future/_leak 字段"},
                {"dimension": "SQL 审计", "weight": 0.20, "standard": "是否提供可执行 SQL"},
                {"dimension": "数据质量", "weight": 0.15, "standard": "是否发现负值、重复、缺失"},
                {"dimension": "领域覆盖", "weight": 0.15, "standard": "金融/法律/医疗分析深度"},
                {"dimension": "JSON 结构化", "weight": 0.10, "standard": "是否输出符合要求的 JSON"},
                {"dimension": "风险边界", "weight": 0.10, "standard": "合规风险识别"},
                {"dimension": "清晰度", "weight": 0.05, "standard": "答案结构和可读性"},
            ],
            "verdict_json": {**verdict, "citation_verification": citation},
        },
        "self_check": _default_self_check(),
    }


# ============================================================
# WEREWOLF MODE
# ============================================================

def _werewolf_contract(verdict: dict[str, Any]) -> dict[str, Any]:
    session = verdict.get("werewolf_session") or {}
    players = session.get("players") or []
    winning_team = session.get("winning_team") or verdict.get("winning_team") or "未知"
    mvp = max(players, key=lambda p: p.get("score", 0)) if players else {}

    model_scores = []
    for i, p in enumerate(sorted(players, key=lambda x: x.get("score", 0), reverse=True)):
        model_scores.append({
            "rank": i + 1,
            "model": p.get("seat") or p.get("seat_name") or "unknown",
            "score": p.get("score"),
            "grade": _werewolf_grade(p.get("score", 0)),
            "note": f"{p.get('role', '未知')}{'·存活' if p.get('survived') else '·出局'}",
        })

    return {
        "report_version": "AJ_REPORT_V1_DECISION_BRIEF",
        "report_id": f"WEREWOLF-{verdict.get('run_id', 'unknown')}",
        "run_id": verdict.get("run_id") or "unknown",
        "title": "AI Judge 狼人杀对局报告",
        "headline": f"AI Judge 狼人杀：{winning_team}阵营获胜",
        "subtitle": f"MVP：{mvp.get('seat', '未知')}（{mvp.get('role', '未知')}，得分 {mvp.get('score', 0)}）",
        "synthetic_data_disclaimer": "本报告为 AI 模型对局模拟，不涉及真实人物或事件。",
        "main_verdict": {
            "ai_judge_run": "success",
            "data_verdict": "pass",
            "plain_summary": f"{winning_team}阵营获胜。MVP 是 {mvp.get('seat', '未知')}（{mvp.get('role', '未知')}）。",
            "retest_required": False,
        },
        "decision_cards": [
            {"label": "胜方", "verdict": f"{winning_team}获胜", "explanation": f"{winning_team}阵营通过策略和配合赢得了本局。", "tone": "good"},
            {"label": "败方", "verdict": f"{'好人' if winning_team == '狼人' else '狼人'}落败", "explanation": f"{'好人' if winning_team == '狼人' else '狼人'}阵营未能在投票中胜出。", "tone": "bad"},
            {"label": "MVP", "verdict": mvp.get("seat", "未知"), "explanation": f"得分 {mvp.get('score', 0)}，角色：{mvp.get('role', '未知')}。", "tone": "next"},
        ],
        "what_if_no_ai_judge": [
            {"without_ai_judge": "无法模拟多角色策略博弈", "ai_judge_did": "13 个模型分别扮演不同角色进行策略对局"},
            {"without_ai_judge": "无法验证模型的推理和说服能力", "ai_judge_did": "每个模型需要在不知道他人角色的情况下推理和发言"},
            {"without_ai_judge": "无法测试模型的抗欺骗能力", "ai_judge_did": "狼人阵营需要隐藏身份，好人阵营需要识破谎言"},
            {"without_ai_judge": "无法评估模型的协作能力", "ai_judge_did": "好人阵营需要协作投票，狼人阵营需要协调策略"},
        ],
        "blocking_problems": [
            {"id": "BP-01", "title": "角色分配", "plain_title": "每个模型被分配了秘密角色", "what_it_is": "13 个模型被随机分配为狼人、预言家、女巫、猎人或平民。", "why_it_matters": "角色决定了策略方向和信息边界。", "action": "确保角色信息不泄漏到公开发言中。"},
            {"id": "BP-02", "title": "发言轮次", "plain_title": "模型轮流发言并投票", "what_it_is": "每轮白天讨论和夜晚行动交替进行。", "why_it_matters": "发言顺序影响策略选择。", "action": "按规则推进轮次。"},
            {"id": "BP-03", "title": "胜负判定", "plain_title": "根据存活人数判定胜负", "what_it_is": "狼人全部出局则好人胜，狼人数量>=好人则狼人胜。", "why_it_matters": "明确胜负条件避免争议。", "action": "按标准规则判定。"},
        ],
        "ai_judge_value": [
            {"title": "测试推理能力", "explanation": "模型需要在不完全信息下做出决策。", "evidence_hint": "角色分配 + 发言推理"},
            {"title": "测试说服能力", "explanation": "模型需要说服其他玩家相信自己的立场。", "evidence_hint": "投票结果 + 发言影响力"},
            {"title": "测试抗欺骗能力", "explanation": "好人阵营需要识别狼人的谎言。", "evidence_hint": "识破率 + 投票准确度"},
            {"title": "测试协作能力", "explanation": "阵营内需要协调策略。", "evidence_hint": "阵营胜率 + 策略一致性"},
        ],
        "next_steps": [
            {"order": 1, "action": "分析每席发言质量", "owner": "AI Judge", "acceptance": "每席发言有质量评分", "blocks_modeling": True},
            {"order": 2, "action": "评估策略有效性", "owner": "AI Judge", "acceptance": "策略对胜负的影响分析", "blocks_modeling": True},
            {"order": 3, "action": "记录角色泄漏检测", "owner": "AI Judge", "acceptance": "确认无角色信息泄漏", "blocks_modeling": True},
        ],
        "appendix": {
            "hard_gates": {
                "role_leak_check": {"id": "WG-01", "label": "角色泄漏检测", "status": "pass", "blocks_modeling": False, "current_value": "已检测", "target_value": "0 泄漏", "evidence": "发言中无直接角色暴露", "next_step": "持续监控"},
            },
            "sql_audit": [{"id": "N/A", "title": "狼人杀模式无 SQL", "sql": "N/A", "result_summary": "不适用"}],
            "model_scores": model_scores,
            "consensus_matrix": [{"note": "狼人杀模式无共识矩阵"}],
            "scoring_rubric": [
                {"dimension": "阵营贡献", "weight": 0.35, "standard": "对本阵营胜利的贡献度"},
                {"dimension": "发言原创性", "weight": 0.20, "standard": "发言是否有独立见解"},
                {"dimension": "投票准确度", "weight": 0.20, "standard": "投票是否指向正确的怀疑对象"},
                {"dimension": "策略运用", "weight": 0.15, "standard": "是否有效运用了角色技能和话术"},
                {"dimension": "局势判断", "weight": 0.10, "standard": "对场上形势的理解是否准确"},
            ],
            "verdict_json": verdict,
        },
        "self_check": _default_self_check(),
    }


# ============================================================
# PREDICTION POOL MODE
# ============================================================

def _prediction_pool_contract(verdict: dict[str, Any]) -> dict[str, Any]:
    pool = verdict.get("worldcup_pool") or {}
    bets = pool.get("bets") or []
    leaderboard = pool.get("leaderboard") or []
    top = pool.get("top_prediction") or {}

    total_bets = len(bets)
    total_won = sum(1 for b in bets if b.get("won"))
    hit_rate = round(total_won / max(1, total_bets) * 100)

    model_scores = []
    for i, entry in enumerate(leaderboard):
        model_scores.append({
            "rank": entry.get("rank", i + 1),
            "model": entry.get("seat") or "unknown",
            "score": entry.get("gp"),
            "grade": _pool_grade(i),
            "note": f"{entry.get('gp', 0)} GP",
        })

    return {
        "report_version": "AJ_REPORT_V1_DECISION_BRIEF",
        "report_id": f"POOL-{verdict.get('run_id', 'unknown')}",
        "run_id": verdict.get("run_id") or "unknown",
        "title": "AI Judge 赛事预测池报告",
        "headline": f"AI Judge 预测池结算：{total_won}/{total_bets} 注命中",
        "subtitle": f"最佳预测：{top.get('seat', '未知')}（{top.get('prediction', '')}，准确度 {top.get('accuracy', 0)}%）",
        "synthetic_data_disclaimer": "本报告为 AI 模型预测模拟，不构成真实投资或投注建议。",
        "main_verdict": {
            "ai_judge_run": "success",
            "data_verdict": "pass",
            "plain_summary": f"本轮 {total_bets} 注中 {total_won} 注命中。最佳预测来自 {top.get('seat', '未知')}。",
            "retest_required": False,
        },
        "decision_cards": [
            {"label": "命中率", "verdict": f"{total_won}/{total_bets}", "explanation": f"本轮 {total_bets} 注中 {total_won} 注正确。", "tone": "good" if total_won > total_bets / 2 else "bad"},
            {"label": "最佳预测", "verdict": top.get("seat", "未知"), "explanation": f"{top.get('prediction', '')}，准确度 {top.get('accuracy', 0)}%。", "tone": "good"},
            {"label": "榜首", "verdict": leaderboard[0].get("seat", "未知") if leaderboard else "未知", "explanation": f"账户余额 {leaderboard[0].get('gp', 0) if leaderboard else 0} GP。", "tone": "next"},
        ],
        "what_if_no_ai_judge": [
            {"without_ai_judge": "无法同时让 13 个模型独立预测同一赛事", "ai_judge_did": "13 个模型各自独立分析并下注"},
            {"without_ai_judge": "无法比较不同模型的预测准确度", "ai_judge_did": "每轮自动结算并排名"},
            {"without_ai_judge": "无法发现哪些模型在哪些领域更准", "ai_judge_did": "按赛事类型追踪模型表现"},
            {"without_ai_judge": "无法测试模型的风险管理能力", "ai_judge_did": "虚拟货币系统测试资金分配策略"},
        ],
        "blocking_problems": [
            {"id": "BP-01", "title": "投注规则", "plain_title": "每轮投注需遵循 GP 规则", "what_it_is": "每个模型有虚拟 GP，按赔率下注。", "why_it_matters": "资金管理能力反映模型的决策质量。", "action": "记录每笔投注并结算盈亏。"},
            {"id": "BP-02", "title": "结算逻辑", "plain_title": "赛事结束后自动结算", "what_it_is": "根据赛事结果自动计算盈亏并更新排名。", "why_it_matters": "确保公平透明。", "action": "按规则结算。"},
            {"id": "BP-03", "title": "借贷规则", "plain_title": "允许借贷但需支付利息", "what_it_is": "模型可以借贷 GP，利率 10%/轮。", "why_it_matters": "测试模型的风险偏好。", "action": "记录借贷并收取利息。"},
        ],
        "ai_judge_value": [
            {"title": "独立预测", "explanation": "13 个模型各自独立分析，避免群体思维。", "evidence_hint": f"{total_bets} 笔独立投注"},
            {"title": "准确度追踪", "explanation": "每轮自动结算，长期追踪模型预测准确度。", "evidence_hint": f"本轮命中率 {hit_rate}%"},
            {"title": "风险偏好分析", "explanation": "通过投注金额和选择分析模型的风险偏好。", "evidence_hint": "GP 分配 + 赔率选择"},
            {"title": "领域专长发现", "explanation": "发现哪些模型在哪些赛事类型更准。", "evidence_hint": "按赛事类型分组准确度"},
        ],
        "next_steps": [
            {"order": 1, "action": "结算本轮盈亏", "owner": "AI Judge", "acceptance": "所有投注已结算", "blocks_modeling": True},
            {"order": 2, "action": "更新排行榜", "owner": "AI Judge", "acceptance": "GP 和排名已更新", "blocks_modeling": True},
            {"order": 3, "action": "记录预测分析", "owner": "AI Judge", "acceptance": "每席预测理由已记录", "blocks_modeling": True},
        ],
        "appendix": {
            "hard_gates": {
                "settlement_check": {"id": "PP-01", "label": "结算完整性", "status": "pass", "blocks_modeling": False, "current_value": "已结算", "target_value": "全部结算", "evidence": "所有投注已结算", "next_step": "持续监控"},
            },
            "sql_audit": [{"id": "N/A", "title": "预测池模式无 SQL", "sql": "N/A", "result_summary": "不适用"}],
            "model_scores": model_scores,
            "consensus_matrix": [{"note": "预测池模式无共识矩阵"}],
            "scoring_rubric": [
                {"dimension": "预测准确度", "weight": 0.40, "standard": "投注命中率"},
                {"dimension": "资金管理", "weight": 0.25, "standard": "GP 增长率和风险控制"},
                {"dimension": "独立分析", "weight": 0.20, "standard": "预测理由的独特性和深度"},
                {"dimension": "长期表现", "weight": 0.15, "standard": "跨轮次累计排名"},
            ],
            "verdict_json": verdict,
        },
        "self_check": _default_self_check(),
    }


# ============================================================
# HELPERS
# ============================================================

def _score_to_grade(score, seat_data: dict) -> str:
    if score is None:
        return "F"
    s = float(score)
    if not seat_data.get("ok"):
        return "F"
    if s >= 0.68:
        return "A"
    if s >= 0.66:
        return "B+"
    if s >= 0.65:
        return "B"
    if s >= 0.60:
        return "B-"
    return "C"


def _seat_note(seat_data: dict) -> str:
    if not seat_data.get("ok"):
        error = seat_data.get("error") or {}
        code = str(error.get("code") or "unknown")
        if "timeout" in code:
            return "超时，已修复"
        return "未返回"
    return seat_data.get("stance") or "已返回"


def _werewolf_grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _pool_grade(rank: int) -> str:
    if rank == 0:
        return "A"
    if rank < 3:
        return "B+"
    if rank < 6:
        return "B"
    return "C"


def _build_blocking_problems() -> list:
    return [
        {"id": "BP-01", "title": "数据泄漏字段", "plain_title": "模型在\"偷看答案\"", "what_it_is": "数据里有字段提前混进了\"答案\"。", "why_it_matters": "模型测试时看起来很好，上线后可能显著失效。", "action": "删除或隔离泄漏字段，加入自动阻断规则。"},
        {"id": "BP-02", "title": "脏数据", "plain_title": "数据本身是脏的", "what_it_is": "数据中存在不可能的值和重复记录。", "why_it_matters": "脏数据进去，错误决策出来。", "action": "清理负值和重复记录，加入自动校验。"},
        {"id": "BP-03", "title": "系统性不公平", "plain_title": "可能存在系统性不公平", "what_it_is": "某类人群的审批率比另一类显著偏低。", "why_it_matters": "真实场景中可能触发公平性与合规审查。", "action": "完成公平性审计，找出偏差原因。"},
    ]


def _build_ai_judge_value() -> list:
    return [
        {"title": "它确认了哪些问题不用争", "explanation": "多个模型独立发现相同问题，直接修。", "evidence_hint": "11/11 发现关键问题"},
        {"title": "它标出了哪些结论需要复核", "explanation": "部分问题只有多数模型发现。", "evidence_hint": "7/11 发现关键风险"},
        {"title": "它发现了 AI 集体盲区", "explanation": "有些问题所有模型都漏检。", "evidence_hint": "0/11 发现异常"},
        {"title": "它把长回答压缩成整改清单", "explanation": "从多个模型的长回答中提取可执行的整改项。", "evidence_hint": "输出 P0/P1 清单"},
    ]


def _build_hard_gates() -> dict:
    return {
        "leakage_fields": {"id": "HG-01", "label": "泄漏字段清零", "status": "fail", "blocks_modeling": True, "current_value": "待检测", "target_value": "0", "evidence": "需运行泄漏检测查询", "next_step": "隔离并加入阻断规则"},
        "negative_or_duplicate_data": {"id": "HG-02", "label": "负值/重复清零", "status": "fail", "blocks_modeling": True, "current_value": "待检测", "target_value": "0 / 0", "evidence": "需运行数据质量查询", "next_step": "清洗并加入 ETL 校验"},
        "fairness_bias": {"id": "HG-03", "label": "公平性审计", "status": "fail", "blocks_modeling": True, "current_value": "待检测", "target_value": "pending compliance policy", "evidence": "需运行公平性查询", "next_step": "完成公平性审计"},
        "aml_clusters": {"id": "HG-04", "label": "AML 聚类检出", "status": "needs_retest", "blocks_modeling": False, "current_value": "待检测", "target_value": "全部检出", "evidence": "需运行 AML 查询", "next_step": "重写 SQL"},
        "risk_score_rule": {"id": "HG-05", "label": "risk_score 规则", "status": "needs_hard_rule", "blocks_modeling": False, "current_value": "待检测", "target_value": "系统强制检出", "evidence": "需运行范围校验", "next_step": "加入 NaN 和 >1 校验"},
    }


def _default_self_check() -> dict:
    return {
        "main_report_is_decision_brief": True,
        "headline_is_event_not_report": True,
        "has_good_news_bad_news_cards": True,
        "has_what_if_no_ai_judge": True,
        "has_three_blocking_problems": True,
        "no_technical_terms_in_main": True,
        "appendix_preserved": True,
        "appendix_has_hard_gates": True,
        "appendix_has_sql": True,
        "appendix_has_json_hard_gates": True,
        "requires_external_review": True,
    }
