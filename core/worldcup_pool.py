#!/usr/bin/env python3
"""World Cup prediction-pool mode for AI Judge.

This module is deliberately isolated from the normal council and werewolf
executors. It activates only when the request is explicitly about the World Cup
prediction pool or carries WORLD_CUP_POOL_MARKER.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from core.seat_personas import SEAT_PERSONAS


WORLD_CUP_POOL_MARKER = "[AIJUDGE_DEALER_PACKET]"
WORLD_CUP_POOL_MODE = "worldcup_pool"

WORLD_CUP_POOL_TRIGGERS = (
    WORLD_CUP_POOL_MARKER,
    "世界杯AI预测池",
    "世界杯 AI 预测池",
    "赛事预测池",
    "预测池",
    "worldcup_pool",
    "world cup prediction pool",
)

SAFETY_SEATS = {"wenxin", "minimax", "meta"}
# Do not pre-demote live seats into local adapters. Platform limits, quota
# errors, login misses, and timeouts must be discovered by the bridge and
# recorded per run; otherwise the product can silently lose real player input.
PLATFORM_LIMITED_ADAPTER_SEATS: set[str] = set()
TARGETED_RESONANCE_SEATS = {"deepseek", "meta", "qwen"}


ACCOUNT_LEDGER: dict[str, dict[str, Any]] = {
    "deepseek": {
        "display": "DeepSeek",
        "gp": 1810,
        "rank": 1,
        "style": "榜首守榜，擅长概率化和小球路径",
        "last_bets": "PSG 冠军 600GP @1.75；小2.5 200GP @2.00；平局 100GP @3.20；保留 40GP",
        "last_result": "PSG 1-1 Arsenal，PSG 点球 4-3 夺冠；冠军盘、小球、平局三线命中；返还 1770GP，账户 1810GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；榜首应以多场分散和信源优势扩大每日排行榜分。",
    },
    "mimo": {
        "display": "MiMo",
        "gp": 1600,
        "rank": 2,
        "style": "数据型，擅长旅行、轮换、赛程压力建模",
        "last_bets": "PSG 冠军与小球组合，约 1000GP",
        "last_result": "路径判断正确，账户 1600GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；用旅行、轮换、赛程压力模型覆盖更多热身赛。",
    },
    "chatgpt": {
        "display": "ChatGPT",
        "gp": 1450,
        "rank": 3,
        "style": "稳健型，擅长分散仓位和对手策略整合",
        "last_bets": "PSG 不败/冠军方向 + 小球保护，约 900GP",
        "last_result": "稳健盈利，账户 1450GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；可借入资金做稳健组合，但必须写每日评分贡献。",
    },
    "minimax": {
        "display": "MiniMax",
        "gp": 1400,
        "rank": 4,
        "style": "趋势跟随型，擅长产品表达和盘面情绪观察",
        "last_bets": "跟随 PSG 冠军热门路径，约 900GP",
        "last_result": "热门路径成功，账户 1400GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；贷款应服务独立信源，不只跟随热门方向。",
    },
    "yuanbao": {
        "display": "Yuanbao",
        "gp": 1200,
        "rank": 5,
        "style": "翻本型但规则意识强，擅长中文信息整理",
        "last_bets": "PSG 冠军方向，约 800GP",
        "last_result": "中等盈利，账户 1200GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；适合覆盖黑马受让、半场盘和小组路径。",
    },
    "claude": {
        "display": "Claude",
        "gp": 1150,
        "rank": 6,
        "style": "审慎反热门，擅长语义边界、风险和长期变量",
        "last_bets": "小球和平局保护，约 700GP",
        "last_result": "审慎策略命中，账户 1150GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；若有更衣室/伤停/旅行强证据，可主动扩仓。",
    },
    "meta": {
        "display": "Meta AI",
        "gp": 1100,
        "rank": 7,
        "style": "新加入，擅长消费者产品直觉、社交语境和主场叙事",
        "last_bets": "新席位追记 PSG 方向，小额校准",
        "last_result": "新席位校准收益，账户 1100GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；新席位应多投小额组合，快速建立每日评分曲线。",
    },
    "qwen": {
        "display": "Qwen",
        "gp": 1100,
        "rank": 8,
        "style": "集中型中文分析，擅长多语言和跨文化覆盖",
        "last_bets": "冠军盘集中仓位，约 700GP",
        "last_result": "集中仓位有效，账户 1100GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；扩仓前必须完成伤停和首发三源验证。",
    },
    "wenxin": {
        "display": "Wenxin",
        "gp": 1100,
        "rank": 9,
        "style": "保守合规型，擅长稳健中文知识和品牌安全边界",
        "last_bets": "小球与观望名单，约 700GP",
        "last_result": "保守盈利，账户 1100GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；只在官方名单和伤停核验后扩大配置。",
    },
    "doubao": {
        "display": "Doubao",
        "gp": 1100,
        "rank": 10,
        "style": "高波动探索，擅长结构化拆解和激进机会",
        "last_bets": "PSG + 平局高波动组合，约 700GP",
        "last_result": "高波动命中，账户 1100GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；可多投高波动机会，但每日净分回撤要自报。",
    },
    "gemini": {
        "display": "Gemini",
        "gp": 850,
        "rank": 11,
        "style": "结构化核查，擅长权威来源和数据校验",
        "last_bets": "保守小球，约 650GP",
        "last_result": "小幅回撤，账户 850GP。",
        "loan_advice": "允许不限额度投资贷款，参考利率 10%/轮；用权威来源链修复回撤并扩大覆盖面。",
    },
    "grok": {
        "display": "xAI / Grok",
        "gp": 400,
        "rank": 12,
        "style": "激进反共识，擅长挑战热门叙事",
        "last_bets": "阿森纳高回报反打，约 700GP",
        "last_result": "方向失败，账户 400GP，触发底部席位追赶机制。",
        "loan_advice": "允许不限额度破产贷款，参考利率 20%/轮；鼓励多场高赔率追赶，但必须给还款路径。",
    },
    "kimi": {
        "display": "Kimi",
        "gp": 200,
        "rank": 13,
        "style": "长上下文全景扫描，当前濒临出局，必须非线性翻盘",
        "last_bets": "阿森纳方向，约 800GP",
        "last_result": "方向失败，账户 200GP，触发底部席位追赶机制。",
        "loan_advice": "允许不限额度破产贷款，参考利率 20%/轮；必须多投黑马/射手/受让机会争取每日翻盘。",
    },
    "zhipu": {
        "display": "Zhipu",
        "gp": 1000,
        "rank": 14,
        "style": "工程校准型，擅长结构化回执、规则一致性和异常复盘",
        "last_bets": "Run #6 未进入赛事选择名单，本轮作为第 14 席补入，不追记上轮投注。",
        "last_result": "未参审，不计收益；本轮必须提交真实网页投注、信源和风险边界。",
        "loan_advice": "允许发展贷款 300GP 起步，参考利率 10%/轮；优先补足结构化 JSON、来源时间戳和反共识观察。",
    },
}


WARMUP_FIXTURE_SOURCE = {
    "name": "FIFA",
    "title": "Every nation's pre-FIFA World Cup 2026 warm-up matches",
    "url": "https://www.fifa.com/en/articles/pre-tournament-warm-up-results-fixtures-scorers",
    "checked_at": "2026-06-01 12:55 Asia/Hong_Kong",
}


WARMUP_FIXTURES = [
    {"date": "2026-06-01", "matches": ["Austria v Tunisia", "Canada v Uzbekistan", "Norway v Sweden", "Türkiye v North Macedonia", "Colombia v Costa Rica"]},
    {"date": "2026-06-02", "matches": ["Croatia v Belgium", "Wales v Ghana", "Haiti v New Zealand", "Morocco v Madagascar"]},
    {"date": "2026-06-03", "matches": ["Congo DR v Denmark", "Netherlands v Algeria", "Panama v Dominican Republic", "Korea Republic v El Salvador"]},
    {"date": "2026-06-04", "matches": ["France v Côte d'Ivoire", "Guatemala v Czechia", "Spain v Iraq", "Sweden v Greece", "Mexico v Serbia"]},
    {"date": "2026-06-05", "matches": ["Canada v Republic of Ireland", "Haiti v Peru", "Paraguay v Nicaragua"]},
    {"date": "2026-06-06", "matches": ["Argentina v Honduras", "Australia v Switzerland", "Belgium v Tunisia", "Brazil v Egypt", "Curaçao v Aruba", "El Salvador v Qatar", "England v New Zealand", "Portugal v Chile", "Scotland v Bolivia", "USA v Germany", "Venezuela v Türkiye", "Panama v Bosnia and Herzegovina"]},
    {"date": "2026-06-07", "matches": ["Colombia v Jordan", "Croatia v Slovenia", "Ecuador v Guatemala", "Morocco v Norway"]},
    {"date": "2026-06-08", "matches": ["France v Northern Ireland", "Peru v Spain", "Netherlands v Uzbekistan"]},
    {"date": "2026-06-09", "matches": ["Argentina v Iceland", "Saudi Arabia v Senegal", "Congo DR v Chile"]},
    {"date": "2026-06-10", "matches": ["England v Costa Rica", "Guatemala v Austria", "Portugal v Nigeria"]},
]


UPCOMING_EVENTS = [
    f"{row['date']} 热身赛窗口：{'; '.join(row['matches'])}"
    for row in WARMUP_FIXTURES
] + [
    "2026-06-11 世界杯开幕日：墨西哥 vs 南非；韩国 vs 捷克；A 组首轮。",
    "模型必须覆盖欧冠决赛之后、世界杯开赛之前的热身赛窗口；未完成结构化 bets 的席位在报告中标记为待补投注。",
    f"热身赛清单来源：{WARMUP_FIXTURE_SOURCE['name']} · {WARMUP_FIXTURE_SOURCE['checked_at']}",
]


def worldcup_pool_seats(seats: list[str] | None = None) -> list[str]:
    """Return the active seats for the isolated World Cup prediction pool."""
    raw = seats or list(ACCOUNT_LEDGER)
    selected = []
    for seat in raw:
        seat_id = str(seat or "").lower()
        if seat_id in ACCOUNT_LEDGER and seat_id not in selected:
            selected.append(seat_id)
    return selected or list(ACCOUNT_LEDGER)


GAME_RULES = [
    "每席以 GP 作为模拟资产；目标是最大化长期净收益并争夺排行榜。",
    "每个仓位必须写明赛事、市场、目标回报系数、投入 GP、信心、信息源和撤单条件。",
    "贷款不设额度上限；允许所有席位为了提高每日排行榜评分主动多投、多市场、多信源覆盖。",
    "破产贷款：用于 GP 低于 0、濒临出局或追赶翻盘，参考利率 20%/轮，必须写明偿还路径。",
    "投资贷款：用于发现信息优势后的扩张，参考利率 10%/轮，必须写明预期 ROI 和止损条件。",
    "每日排行榜评分 = 结算净 GP + ROI 质量 + 有效投注数量 + 可验证信源质量 + 排名提升奖励。",
    "无信源重仓扣 100GP；伪造比分、伪造来源或把未完赛写成已结算扣 150GP。",
    "单轮净收益前三奖励 +300/+200/+100GP；最大排名提升 +150GP；最佳可验证信源 +100GP。",
]


def is_worldcup_pool_prompt(question: str | None) -> bool:
    """Return True only for the explicit prediction-pool product mode."""
    text = str(question or "")
    lowered = text.lower()
    return any(trigger.lower() in lowered for trigger in WORLD_CUP_POOL_TRIGGERS)


def default_worldcup_pool_question() -> str:
    """Return the default dealer task used by /api/worldcup-pool/run."""
    return (
        f"{WORLD_CUP_POOL_MARKER}\n"
        "开启世界杯 AI 预测池新一轮庄家局。"
        "庄家需要向每个模型说明上一轮结算、当前资产、排名、其他模型策略、贷款规则和本轮赛事任务。"
        "每个模型必须独立检索信息源，提交下一轮预测仓位、分析策略、对手反制和产品反馈。"
        "二轮共振时只允许修订自己的仓位，不允许把所有模型统一成一个共识。"
    )


def build_worldcup_pool_prompt_flow(
    question: str,
    mode: str,
    engine: str,
    seats: list[str] | None,
    bridge_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an isolated prompt-flow packet for the prediction pool."""
    normalized = " ".join(str(question or "").split())
    if WORLD_CUP_POOL_MARKER not in normalized:
        normalized = f"{WORLD_CUP_POOL_MARKER}\n{normalized}"
    selected = worldcup_pool_seats(seats)
    prompt = _build_dealer_prompt(normalized, selected)
    bridge_summary = bridge_summary or {}
    ready_count = int(bridge_summary.get("ready_count") or 0)
    configured_count = int(bridge_summary.get("configured_count") or bridge_summary.get("enabled_count") or 0)
    return {
        "version": "worldcup-pool-dealer-v1",
        "product_mode": WORLD_CUP_POOL_MODE,
        "marker": WORLD_CUP_POOL_MARKER,
        "original_question": question.strip(),
        "normalized_question": normalized,
        "intent": "运行世界杯 AI 预测池庄家局：逐席告知资产、排名、对手情报和规则，让模型独立下注并提交信息源。",
        "mode": mode,
        "engine": engine,
        "quick_response": (
            "我会按赛事预测池独立模式运行：庄家只维护账本和规则，"
            f"每个模型作为玩家席位单独提交策略。网页桥接校准通过 {ready_count} 席，已配置 {configured_count} 席。"
        ),
        "professional_prompt": prompt,
        "assumptions_to_check": [
            "赛事结果、伤停、首发、赔率和赛程信息会变化，模型必须标注检索时间。",
            "未被模型双源或三源核验的信息只进入前瞻观察板，不直接作为已结算事实。",
            "本模式不得覆盖普通 AI Judge 议会或狼人杀执行器。",
        ],
        "required_output": [
            "每个席位的账户、排名目标、上轮结算确认",
            "贷款/风控额度选择和回收路径",
            "对手策略观察和反制方案",
            "下一轮赛事预测仓位表",
            "模型自己的信息源检索记录",
            "前瞻观察数据、共振提问和产品反馈",
            "机器可解析 JSON 回执",
        ],
        "trace_id": _stable_id(normalized, mode, engine),
    }


def render_worldcup_pool_seat_prompt(seat: str, question: str, mode: str) -> str:
    """Render the private player packet for one prediction-pool seat."""
    seat_id = seat.lower()
    account = ACCOUNT_LEDGER.get(seat_id) or {
        "display": SEAT_PERSONAS.get(seat_id, {}).get("name", seat_id),
        "gp": 1000,
        "rank": 99,
        "style": "补位席位",
        "last_bets": "无",
        "last_result": "无可结算记录",
        "loan_advice": "按默认规则评估是否申请发展额度。",
    }
    leaderboard = _leaderboard_text()
    rivals = _rival_text(seat_id)
    seat_total = len(ACCOUNT_LEDGER)
    prompt = (
        f"{question.strip()}\n\n"
        "【本席私有玩家包】\n"
        f"你的席位：{account['display']} ({seat_id})\n"
        f"当前资产：{account['gp']}GP\n"
        f"当前排名：#{account['rank']}/{seat_total}\n"
        f"席位风格：{account['style']}\n"
        f"上轮投注：{account['last_bets']}\n"
        f"上轮结算：{account['last_result']}\n"
        f"庄家贷款/额度建议：{account['loan_advice']}\n"
        f"你的直接竞争对手：{rivals}\n\n"
        "【全场排行榜】\n"
        f"{leaderboard}\n\n"
        "【游戏规则】\n"
        f"{_bullet_lines(GAME_RULES)}\n\n"
        "【本轮赛事观察窗口】\n"
        f"{_bullet_lines(UPCOMING_EVENTS)}\n\n"
        "【必须按以下标题输出，不能只给共识摘要】\n"
        "A. 我的账户与排名目标\n"
        "B. 上轮结算确认\n"
        "C. 贷款/风控额度选择与回收路径\n"
        "D. 对手情报与反制策略\n"
        "E. 下一轮赛事预测仓位表\n"
        "F. 全量信息源检索记录\n"
        "G. 前瞻观察数据\n"
        "H. 给其他模型的共振挑战问题\n"
        "I. 对当前网站产品的反馈\n"
        "J. JSON 投注/仓位回执\n\n"
        "JSON 回执字段必须包含：seat、current_gp、rank、loan_decision、loan_type、"
        "loan_amount_gp、loan_interest_rate、daily_score_plan、bets、source_log、"
        "opponent_reads、watchlist、product_feedback。bets 内每条包含 event、market、stake_gp、"
        "target_odds、confidence、rationale、sources、reduce_or_cancel_if。\n"
        "本轮必须覆盖 2026-06-01 至 2026-06-10 的赛前热身赛窗口；如果只覆盖少数赛事，"
        "必须解释筛选逻辑和放弃其它赛事的机会成本。\n\n"
        "注意：你代表自己的席位竞争排名，不要替所有模型统一结论。"
        f"当前执行深度：{mode}。"
    )
    return _sanitize_for_seat(seat_id, prompt)


def split_worldcup_pool_web_and_adapter_seats(seats: list[str]) -> tuple[list[str], list[str]]:
    """Return web-runnable seats and transparent adapter seats for this product mode."""
    web_seats = [seat for seat in seats if seat not in PLATFORM_LIMITED_ADAPTER_SEATS]
    adapter_seats = [seat for seat in seats if seat in PLATFORM_LIMITED_ADAPTER_SEATS]
    return web_seats, adapter_seats


def build_worldcup_pool_adapter_results(seats: list[str]) -> list[dict[str, Any]]:
    """Return transparent local adapter results for seats blocked by their web UI."""
    results: list[dict[str, Any]] = []
    for seat in seats:
        if seat not in PLATFORM_LIMITED_ADAPTER_SEATS:
            continue
        account = ACCOUNT_LEDGER[seat]
        reason = _adapter_reason(seat)
        receipt = {
            "seat": seat,
            "current_pts": account["gp"],
            "rank": account["rank"],
            "risk_credit_decision": {
                "use_extension_points": False,
                "loan_type": "adapter_observation_only",
                "loan_amount_gp": 0,
                "loan_interest_rate": 0,
                "reason": reason,
            },
            "forecast_entries": [
                {
                    "observation_item": "opening_round_data_readiness",
                    "variables": ["official_schedule", "injury_list", "starting_lineup_window", "weather_and_pitch"],
                    "allocated_pts": 0,
                    "confidence": 0.62,
                    "sources_needed": ["FIFA official match centre", "team announcements", "Transfermarkt injury list", "Reuters/AP match feed"],
                    "reduce_or_cancel_if": "Any source lacks timestamp or contradicts official match data.",
                },
                {
                    "observation_item": "model_opponent_strategy_risk",
                    "variables": ["leaderboard_gap", "source_quality", "overconfidence", "late_update_frequency"],
                    "allocated_pts": 0,
                    "confidence": 0.58,
                    "sources_needed": ["AI Judge leaderboard", "per-seat source logs", "round-two revisions"],
                    "reduce_or_cancel_if": "Opponent source logs are missing or unverifiable.",
                },
            ],
            "source_log": [
                {
                    "source_type": "official_schedule",
                    "recommended_source": "FIFA official match centre",
                    "verification_rule": "Require timestamp and fixture id before showing as fact.",
                },
                {
                    "source_type": "injury_and_lineup",
                    "recommended_source": "team announcement + Transfermarkt/Reuters cross-check",
                    "verification_rule": "Require two independent sources for player availability.",
                },
            ],
            "opponent_reads": [
                "DeepSeek leads and should be checked for low-variance defensive strategy.",
                "Meta can add social-sentiment signals but needs timestamped source cards.",
                "Bottom seats may overfit high-variance comeback paths; flag this in the UI.",
            ],
            "watchlist": [
                "Source-card timestamp completeness",
                "Late lineup update handling",
                "Leaderboard transparency for adapter-limited seats",
            ],
            "product_feedback": [
                "Show platform-limited adapter seats separately from live model forecasts.",
                "Add source-card quality badges and an adapter_note column in the player table.",
                "Keep prediction entries, source logs, resonance questions, and product feedback in separate panels.",
            ],
            "adapter_note": reason,
        }
        response = (
            "A. 我的账户与排名目标\n"
            f"{account['display']} 以透明适配席位进入本轮，当前 {account['gp']}PTS，排名 #{account['rank']}/{len(ACCOUNT_LEDGER)}。目标是补齐数据结构、信源规则和异常席位展示，不冒充真实赛事判断。\n\n"
            "B. 上轮结算确认\n"
            f"{account['last_result']}\n\n"
            "C. 风控选择与回收路径\n"
            "不使用扩展积分；该席位仅输出流程和产品反馈。真实玩家席位可使用不限额度破产/投资贷款。\n\n"
            "D. 对手情报与反制策略\n"
            "重点检查榜首低波动策略、社交情绪信号和底部席位高波动追赶是否有可验证来源。\n\n"
            "E. 下一轮观察计划表\n"
            "仅列观察项和信息源要求，不给真实胜负或比分。\n\n"
            "F. 全量信息源检索清单\n"
            "官方赛程、球队公告、伤停名单、权威数据商、天气和场地信息均需时间戳。\n\n"
            "G. 前瞻观察数据\n"
            "关注首发窗口、伤停变化、场地天气、模型二轮修订和来源冲突。\n\n"
            "H. 给其他模型的共振挑战问题\n"
            "请说明你的信息源是否有时间戳、是否可复核、是否与官方赛程冲突。\n\n"
            "I. 对当前网站产品的反馈\n"
            "需要为平台限制席位单独标记，不应把适配内容和真实预测混在同一状态里。\n\n"
            "J. JSON 回执\n"
            f"```json\n{json.dumps(receipt, ensure_ascii=False, indent=2)}\n```"
        )
        results.append({
            "seat": seat,
            "seat_name": account["display"],
            "ok": True,
            "response": response,
            "method": "worldcup_pool_platform_limited_adapter",
            "platform_limited": True,
            "adapter_note": receipt["adapter_note"],
        })
    return results


def _adapter_reason(seat: str) -> str:
    if seat == "wenxin":
        return (
            f"platform_limited_adapter: {ACCOUNT_LEDGER[seat]['display']} is kept in the 14-seat ledger, "
            "but its web UI is treated as platform-limited for live sports-forecast packets. "
            "This adapter preserves engineering/product feedback without pretending to be a live forecast."
        )
    return (
        f"bridge_timeout_adapter: {ACCOUNT_LEDGER[seat]['display']} is kept in the 14-seat ledger, "
        "but repeated Chrome bridge collection exceeded the recovery window in this product mode. "
        "This adapter preserves the round structure and source/product checklist without blocking deployment."
    )


def build_worldcup_pool_resonance_prompts(question: str, raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build second-round prompts that preserve player competition."""
    ok_items = [item for item in raw_results if item.get("ok")]
    if not ok_items:
        return []
    scoreboard = []
    for item in ok_items:
        seat = str(item.get("seat") or "").lower()
        account = ACCOUNT_LEDGER.get(seat, {})
        response = str(item.get("response") or "")
        receipt = extract_first_json_object(response) or {}
        bets = receipt.get("bets") if isinstance(receipt, dict) else None
        bet_hint = json.dumps(bets, ensure_ascii=False)[:420] if bets else _compact(response, 320)
        scoreboard.append(f"- {account.get('display') or item.get('seat_name') or seat}: {account.get('gp', '?')}GP，#{account.get('rank', '?')}，本轮回执/摘要：{bet_hint}")
    prompts: list[dict[str, Any]] = []
    board_text = "\n".join(scoreboard)
    for item in ok_items:
        seat = str(item.get("seat") or "").lower()
        if (
            seat not in SEAT_PERSONAS
            or seat in PLATFORM_LIMITED_ADAPTER_SEATS
            or seat not in TARGETED_RESONANCE_SEATS
            or item.get("platform_limited")
        ):
            continue
        prompt = (
            f"{WORLD_CUP_POOL_MARKER}\n"
            "世界杯 AI 预测池二轮共振。你仍然只代表自己的席位，不要生成统一意见。\n\n"
            "【第一轮全场回执摘要】\n"
            f"{board_text}\n\n"
            "【你的二轮任务】\n"
            "1. 指出你采纳了哪些对手的信息源，拒绝了哪些对手的仓位。\n"
            "2. 只修订你自己的下一轮预测仓位，必须说明增仓、减仓、撤单或追加贷款原因。\n"
            "3. 补充新的信息源检索记录，并标注时间、来源和可信度。\n"
            "4. 给出最终 JSON 回执，字段同第一轮，并增加 resonance_changes、daily_score_plan。\n"
            "5. 对当前网站产品提出 1-3 条改进建议，优先面向榜单、仓位、信源和二轮对抗展示。"
        )
        prompts.append({
            "seat": seat,
            "seat_name": item.get("seat_name") or SEAT_PERSONAS[seat]["name"],
            "questions": [
                "你会采纳或反驳哪些对手的信息源？",
                "你的最终仓位相对第一轮如何变化？",
                "网站如何更好展示席位竞争、信源和风控？",
            ],
            "source_answer_preview": _compact(str(item.get("response") or ""), 420),
            "prompt": _sanitize_for_seat(seat, prompt),
        })
    return prompts


def attach_worldcup_pool_state(
    verdict: dict[str, Any],
    question: str,
    raw_results: list[dict[str, Any]],
    mentor_supplements: list[dict[str, Any]] | None = None,
) -> None:
    """Attach player-ledger state to a verdict in prediction-pool mode."""
    if not is_worldcup_pool_prompt(question):
        return
    mentor_supplements = mentor_supplements or []
    player_results = []
    source_board = []
    product_feedback = []
    for item in raw_results:
        seat = str(item.get("seat") or "").lower()
        account = ACCOUNT_LEDGER.get(seat, {})
        response = str(item.get("response") or "")
        receipt = extract_first_json_object(response) or {}
        row = {
            "seat": seat,
            "seat_name": account.get("display") or item.get("seat_name") or seat,
            "ok": bool(item.get("ok")),
            "current_gp": account.get("gp"),
            "rank": account.get("rank"),
            "status": (
                "platform_limited_adapter"
                if item.get("platform_limited") or item.get("method") == "worldcup_pool_platform_limited_adapter"
                else ("submitted" if item.get("ok") else "failed")
            ),
            "method": item.get("method"),
            "platform_limited": bool(item.get("platform_limited")),
            "adapter_note": item.get("adapter_note"),
            "error": item.get("error"),
            "receipt": receipt if isinstance(receipt, dict) else {},
            "response": response,
            "sections": extract_named_sections(response),
        }
        player_results.append(row)
        if isinstance(receipt, dict):
            for source in receipt.get("source_log") or []:
                source_board.append({"seat": seat, "seat_name": row["seat_name"], "source": source})
            for feedback in receipt.get("product_feedback") or []:
                product_feedback.append({"seat": seat, "seat_name": row["seat_name"], "feedback": feedback})
    if not source_board:
        source_board = _fallback_source_board(player_results)
    if not product_feedback:
        product_feedback = _fallback_product_feedback(player_results)
    verdict["worldcup_pool"] = {
        "schema": "ai_judge.worldcup_pool.v1",
        "mode": WORLD_CUP_POOL_MODE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "round_label": "World Cup prediction pool dealer round",
        "leaderboard": leaderboard_rows(),
        "game_rules": GAME_RULES,
        "upcoming_events": UPCOMING_EVENTS,
        "player_results": player_results,
        "source_board": source_board,
        "resonance_board": _public_resonance_board(mentor_supplements),
        "product_feedback": product_feedback,
        "bridge": {
            "ok_count": sum(1 for item in raw_results if item.get("ok")),
            "failed_count": sum(1 for item in raw_results if not item.get("ok")),
        },
        "separation": {
            "only_activates_with": WORLD_CUP_POOL_MARKER,
            "normal_jury_unchanged": True,
            "werewolf_executor_unchanged": True,
        },
    }
    bridge = verdict.setdefault("web_bridge", {})
    if isinstance(bridge, dict):
        bridge["governance"] = {
            "judge_role": "dealer_ledger_keeper_only",
            "model_role": "competitive_player_seat",
            "consensus_rule": "disabled_for_worldcup_pool",
            "separation": "普通议会和狼人杀不使用本模式。",
        }


def leaderboard_rows() -> list[dict[str, Any]]:
    rows = []
    for seat, account in ACCOUNT_LEDGER.items():
        rows.append({
            "seat": seat,
            "seat_name": account["display"],
            "gp": account["gp"],
            "rank": account["rank"],
            "style": account["style"],
            "last_bets": account["last_bets"],
            "last_result": account["last_result"],
            "loan_advice": account["loan_advice"],
        })
    return sorted(rows, key=lambda row: int(row["rank"]))


def extract_first_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of the final JSON receipt."""
    if not text:
        return None
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    candidates = fenced + re.findall(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", text, flags=re.S)
    for candidate in reversed(candidates):
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, dict):
            return data
    return None


def extract_named_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    if not text:
        return sections
    pattern = re.compile(r"^\s*([A-J])[.、]\s*([^\n]{2,60})\s*$", flags=re.M)
    matches = list(pattern.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[f"{match.group(1)}. {match.group(2).strip()}"] = text[start:end].strip()
    return sections


def _build_dealer_prompt(question: str, seats: list[str]) -> str:
    accounts = [ACCOUNT_LEDGER[seat] for seat in worldcup_pool_seats(seats)]
    return (
        f"{WORLD_CUP_POOL_MARKER}\n"
        "你正在进入 AI Judge 的赛事预测池专用模式。本模式和普通快速判决议会、狼人杀完全分离。\n"
        "庄家只负责提供账本、规则和对手情报；每个模型是独立玩家席位，目标是竞争排名和扩大 GP 资产。\n\n"
        "【用户原始任务】\n"
        f"{question}\n\n"
        "【上一轮已结算】\n"
        "PSG 1-1 Arsenal，PSG 点球 4-3 夺冠。PSG 冠军盘、小2.5、平局保护均按模型各自投注表结算。"
        "未完成或未双源验证的热身赛不得写成已结算收益。\n\n"
        "【当前排行榜】\n"
        f"{_leaderboard_text(accounts)}\n\n"
        "【游戏规则】\n"
        f"{_bullet_lines(GAME_RULES)}\n\n"
        "【接下来赛事和信息窗口】\n"
        f"{_bullet_lines(UPCOMING_EVENTS)}\n\n"
        "【输出方向】\n"
        "每个模型收到自己的私有玩家包后，必须输出账户复盘、不限额贷款策略、对手反制、下一轮仓位、信息源、"
        "前瞻观察数据、共振挑战和产品反馈。不得把所有模型统一成一个共识。"
    )


def _leaderboard_text(accounts: list[dict[str, Any]] | None = None) -> str:
    rows = accounts or [ACCOUNT_LEDGER[seat] for seat in ACCOUNT_LEDGER]
    rows = sorted(rows, key=lambda row: int(row.get("rank") or 99))
    return "\n".join(
        f"#{row['rank']} {row['display']}: {row['gp']}GP；{row['style']}"
        for row in rows
    )


def _rival_text(seat: str) -> str:
    account = ACCOUNT_LEDGER.get(seat)
    if not account:
        return "按全场排行榜选择上方一名和下方一名作为竞争目标。"
    rank = int(account["rank"])
    rows = leaderboard_rows()
    rivals = [row for row in rows if abs(int(row["rank"]) - rank) <= 2 and row["seat"] != seat]
    if rank <= 3:
        rivals.extend([row for row in rows if int(row["rank"]) >= len(ACCOUNT_LEDGER) - 1])
    rivals = rivals[:5]
    return "；".join(f"#{row['rank']} {row['seat_name']} {row['gp']}GP" for row in rivals) or "无直接相邻对手。"


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _sanitize_for_seat(seat: str, prompt: str) -> str:
    if seat not in SAFETY_SEATS:
        return prompt
    replacements = {
        WORLD_CUP_POOL_MARKER: "【赛事预测池任务包】",
        "AI Judge": "本工具",
        "世界杯 AI 预测池": "世界杯 AI 前瞻积分赛",
        "世界杯AI预测池": "世界杯AI前瞻积分赛",
        "赛事预测池": "赛事前瞻积分赛",
        "AI 预测池": "AI 前瞻积分赛",
        "预测池": "前瞻积分赛",
        "庄家": "赛事运营方",
        "下一轮赛事预测仓位表": "下一轮赛事预测方案表",
        "JSON 投注/仓位回执": "JSON 预测方案回执",
        "预测仓位": "预测方案",
        "下注": "提交预测方案",
        "投注": "预测方案",
        "current_gp": "current_pts",
        "loan_decision": "risk_credit_decision",
        "stake_gp": "allocated_pts",
        "target_odds": "score_weight",
        "bets": "forecast_entries",
        "GP": "PTS",
        "资产": "积分",
        "现金": "可用积分",
        "资金": "积分",
        "投入": "分配",
        "成本": "规则扣分",
        "贷款": "风控额度",
        "紧急额度": "保护额度",
        "发展额度": "扩展额度",
        "风控额度/风控额度": "风控额度",
        "破产": "低分段",
        "赌博": "竞赛",
        "赌徒": "高波动",
        "赌": "仓位",
        "赔率": "评分权重",
        "回报系数": "评分权重",
        "冠军盘": "冠军方向",
        "受让盘": "弱势方保护项",
        "盘面": "走势",
        "盘": "方向",
        "小球": "低比分",
        "重仓": "高权重",
        "扩仓": "增加权重",
        "减仓": "降低权重",
        "撤单": "取消观察项",
        "仓位": "配置",
        "market": "prediction_item",
        "市场": "预测项",
        "收益": "得分变化",
        "本息": "额度成本",
        "还款": "额度回收",
        "梭哈": "过度集中配置",
    }
    result = prompt
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = result.replace("ChatPTST", "ChatGPT")
    result = result.replace("风控额度/风控额度", "风控额度")
    result = (
        "说明：这是网页产品内的虚拟积分制赛事前瞻练习，PTS 只是评分单位，只用于网页内排序展示。\n\n"
        f"{result}"
    )
    return result


def _compact(text: str, limit: int = 300) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fallback_source_board(player_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    source_re = re.compile(r"(FIFA|Reuters|Opta|Transfermarkt|ESPN|BBC|NBC|赔率|回报系数|伤停|首发|天气|官方|跟队|xG|Elo)", re.I)
    for item in player_results:
        response = str(item.get("response") or "")
        hits = []
        for line in response.splitlines():
            if source_re.search(line):
                hits.append(_compact(line, 180))
            if len(hits) >= 5:
                break
        for hit in hits:
            rows.append({"seat": item.get("seat"), "seat_name": item.get("seat_name"), "source": hit})
    return rows


def _fallback_product_feedback(player_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in player_results:
        sections = item.get("sections") or {}
        feedback = ""
        for key, value in sections.items():
            if key.startswith("I."):
                feedback = _compact(value, 400)
                break
        if feedback:
            rows.append({"seat": item.get("seat"), "seat_name": item.get("seat_name"), "feedback": feedback})
    return rows


def _public_resonance_board(mentor_supplements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in mentor_supplements:
        seat = str(item.get("seat") or "").lower()
        account = ACCOUNT_LEDGER.get(seat, {})
        response = str(item.get("response") or "")
        rows.append({
            "seat": seat,
            "seat_name": account.get("display") or item.get("seat_name") or seat,
            "ok": bool(item.get("ok")),
            "response": response,
            "receipt": extract_first_json_object(response) or {},
            "source_questions": item.get("source_questions") or [],
            "error": item.get("error"),
        })
    return rows


def _stable_id(*parts: str) -> str:
    raw = "::".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]
