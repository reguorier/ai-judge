"""Prediction-pool publication adapter."""

from __future__ import annotations

from typing import Any

from product.reporting.publication.schema import (
    as_text_items,
    build_block,
    build_metric,
    build_table,
    clip_text,
)


def build_prediction_pool_blocks(
    report: dict[str, Any],
    *,
    seat_matrix: dict[str, Any] | None = None,
    evidence_packet: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    pool = _pool_payload(report)
    summary = pool.get("summary") if isinstance(pool.get("summary"), dict) else {}
    betting = pool.get("betting") if isinstance(pool.get("betting"), dict) else {}
    betting_summary = betting.get("summary") if isinstance(betting.get("summary"), dict) else {}
    matches = _match_rows(pool, report)
    model_rows = _model_rows(pool, report)

    accepted_bets = _first(summary, betting_summary, report, keys=("accepted_bets", "bet_count", "下注笔数"))
    no_bets = _first(summary, betting_summary, report, keys=("no_bets", "watch_count", "观望次数"))
    total_stake = _first(summary, betting_summary, report, keys=("total_stake_gp", "total_stake", "总投入"))
    loan_exposure = _first(summary, betting_summary, report, keys=("loan_exposure_gp", "loan_exposure", "贷款暴露"))
    roi = _first(summary, betting_summary, report, keys=("roi", "ROI"))

    metrics = [
        build_metric("有效席位", _first(summary, report, keys=("valid_seats", "有效席位")) or "-"),
        build_metric("下注笔数", accepted_bets or "-"),
        build_metric("观望次数", no_bets or "-"),
        build_metric("总投入", _format_gp(total_stake)),
        build_metric("贷款暴露", _format_gp(loan_exposure), "good" if str(loan_exposure or "0") in {"0", "0 GP"} else "warn"),
        build_metric("ROI", _format_percent(roi)),
    ]

    return [
        build_block(
            "prediction_scoreboard",
            "预测池 · 记分牌",
            kind="scoreboard",
            summary="预测池报告先看资金、下注、观望和风险暴露，再看逐场理由。",
            metrics=metrics,
            level="industry",
        ),
        build_block(
            "forecast_vs_investment",
            "预测 vs 下注",
            kind="concept_table",
            summary="预测是必须判断方向；下注是资金管理选择。不下注不等于没有观点。",
            table=build_table(
                ["维度", "预测 Forecast", "下注 Investment"],
                [
                    ["是否强制", "每个有效席位都应给方向/概率/置信度", "可选择下注或观望"],
                    ["核心内容", "方向、比分、概率、证据缺口", "下注/不下注、金额、赔率、期望值、撤单条件"],
                    ["复盘指标", "命中率、比分接近度、概率校准", "盈亏、ROI、风险暴露、排名变化"],
                    ["噪声信号", "同题复跑方向漂移、置信度离散", "无赔率重仓、贷款冲动、理由与投注不一致"],
                ],
            ),
            level="industry",
        ),
        build_block(
            "match_analysis",
            "逐场分析",
            kind="match_table",
            summary="每场比赛必须同时展示共识、分歧、风险和证据缺口。",
            table=build_table(
                ["比赛", "AI共识/方向", "下注建议", "风险提示"],
                matches,
            ),
            level="industry",
        ),
        build_block(
            "model_behavior",
            "模型行为画像",
            kind="model_behavior",
            summary="区分激进、保守、稳定和高噪声模型，避免只看最终胜负。",
            table=build_table(
                ["模型", "预测/下注行为", "风险标签", "备注"],
                model_rows,
            ),
            level="industry",
        ),
        build_block(
            "pool_risk_controls",
            "风控与结算动作",
            kind="risk_controls",
            summary="预测池输出不能只给推荐，还要给降低噪声和资金风险的动作。",
            items=[
                "判断波动较高的比赛不进入自动结算建议，先人工复核。",
                "无赔率、无信源或投注理由与预测相反时，标记为高风险。",
                "贷款暴露、单场过度集中和同模型前后矛盾进入风险清单。",
                "赛后复盘同时更新预测准确率、下注 ROI 和模型稳定性画像。",
            ],
            level="industry",
        ),
    ]


def _pool_payload(report: dict[str, Any]) -> dict[str, Any]:
    for key in ("prediction_pool", "worldcup_pool", "pool_runtime", "runtime_summary"):
        value = report.get(key)
        if isinstance(value, dict):
            return value
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    for key in ("prediction_pool", "worldcup_pool"):
        value = artifacts.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _match_rows(pool: dict[str, Any], report: dict[str, Any]) -> list[list[str]]:
    matches = pool.get("matches") if isinstance(pool.get("matches"), list) else []
    rows = []
    for item in matches[:12]:
        if not isinstance(item, dict):
            continue
        rows.append([
            item.get("match") or item.get("event") or item.get("name") or "-",
            item.get("consensus") or item.get("forecast") or item.get("direction") or "-",
            item.get("bet") or item.get("investment") or item.get("recommendation") or "观望/待确认",
            item.get("risk") or item.get("risk_note") or item.get("evidence_gap") or "-",
        ])
    if rows:
        return rows

    return [["暂无逐场结构化数据", "需要从预测池 runtime 提取", "不生成下注建议", "数据缺口"]]


def _model_rows(pool: dict[str, Any], report: dict[str, Any]) -> list[list[str]]:
    models = pool.get("models") if isinstance(pool.get("models"), list) else []
    rows = []
    for item in models[:16]:
        if not isinstance(item, dict):
            continue
        rows.append([
            item.get("seat_name") or item.get("seat") or item.get("model") or "-",
            item.get("behavior") or item.get("strategy") or item.get("stance") or "-",
            item.get("risk") or item.get("tag") or "-",
            item.get("note") or item.get("summary") or "-",
        ])
    if rows:
        return rows

    stability = report.get("model_stability") if isinstance(report.get("model_stability"), dict) else {}
    profiles = stability.get("profiles") if isinstance(stability.get("profiles"), list) else []
    for item in profiles[:12]:
        if not isinstance(item, dict):
            continue
        rows.append([
            item.get("seat_name") or item.get("seat") or "-",
            f"稳定性 {item.get('stability_score', '-')}",
            "长期画像",
            f"样本数 {item.get('runs_seen', 0)}",
        ])
    return rows or [["暂无模型行为结构化数据", "待沉淀", "数据缺口", "需要接入预测池回执"]]


def _first(*sources: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            if key in source and source[key] not in (None, ""):
                return source[key]
    return None


def _format_gp(value: Any) -> str:
    if value in (None, ""):
        return "-"
    text = str(value)
    if "GP" in text.upper():
        return text
    return f"{text} GP"


def _format_percent(value: Any) -> str:
    if value in (None, ""):
        return "-"
    text = str(value)
    if "%" in text:
        return text
    try:
        number = float(text)
        if abs(number) <= 1:
            number *= 100
        return f"{number:.1f}%"
    except ValueError:
        return clip_text(text, 40)
