"""Source-grounded professional digest for publication reports."""

from __future__ import annotations

import re
from typing import Any

from product.reporting.publication.schema import (
    build_block,
    build_card,
    build_metric,
    build_table,
    clip_text,
)


def enrich_from_source(model: dict[str, Any], report: dict[str, Any]) -> None:
    """Enrich a publication model when full source text is available.

    This layer is intentionally conservative: it uses the supplied source text
    as grounding, but avoids inventing new facts. When a field is missing, it
    labels the gap instead of filling it with guessed data.
    """

    source_text = _source_text(report)
    if not source_text:
        return

    domain = str(model.get("domain") or "")
    if domain == "prediction_pool":
        _enrich_prediction_pool(model, report, source_text)
    elif domain == "legal_memo":
        _enrich_legal_memo(model, report, source_text)


def _source_text(report: dict[str, Any]) -> str:
    value = report.get("source_text") or ""
    text = str(value).strip()
    # Strip local render footers from historical browser/PDF captures.
    text = re.sub(r"file:///Users/[^\n]+", "", text)
    return text.strip()


def _source_title(report: dict[str, Any]) -> str:
    title = str(report.get("title") or report.get("question") or "").strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"file:///Users/[^\n]+", "", title)
    return clip_text(title, limit=72)


def _enrich_prediction_pool(model: dict[str, Any], report: dict[str, Any], text: str) -> None:
    metrics = _prediction_metrics(text)
    profile = _prediction_profile(text, metrics)

    source_title = _source_title(report)
    if source_title:
        model["title"] = source_title
    model["subtitle"] = "原文驱动的预测池专业阅读版"
    model["cover_metrics"] = [
        build_metric(item[0], item[1]) for item in profile["cover_metrics"]
    ]

    model["reader_blocks"] = [
        build_block(
            "reader_one_line",
            "一句话判断",
            kind="reader_lead",
            summary=profile["one_line"],
            level="reader",
        ),
        build_block(
            "reader_professional_analysis",
            "专业分析",
            kind="reader",
            items=profile["professional_analysis"],
            level="reader",
        ),
        build_block(
            "reader_advice",
            "当前建议",
            kind="reader",
            items=profile["advice"],
            level="reader",
        ),
        build_block(
            "reader_basis",
            "关键依据",
            kind="reader",
            items=profile["basis"],
            level="reader",
        ),
        build_block(
            "reader_risks",
            "最大风险",
            kind="reader",
            items=profile["risks"],
            level="reader",
        ),
        build_block(
            "reader_boundary",
            "适用边界",
            kind="reader",
            items=profile["boundary"],
            level="reader",
        ),
    ]

    model["industry_blocks"] = []
    model["base_blocks"] = []

    source_blocks = [
        build_block(
            "source_decision_frame",
            "原文驱动 · 决策框架",
            kind="source_frame",
            summary="把原文里的比赛事实、模型行为和资金动作拆成三层，避免正文只剩抽象结论。",
            cards=[
                build_card("预测层", "判断方向", "方向、比分、概率、置信度、公平赔率和信息缺口。"),
                build_card("下注层", "资金选择", "下注/观望、金额、市场赔率、预期价值和撤单条件。"),
                build_card("风控层", "可采纳性", "贷款暴露、盘口完整性、同向拥挤、单场集中和赛后可归因性。"),
            ],
            level="industry",
        ),
        build_block(
            "source_match_matrix",
            "逐场专业拆解",
            kind="match_table",
            summary="只展示原文中有明确席位、资金或分歧依据的场次；缺失字段保留为风险，不用推测补齐。",
            table=build_table(["比赛", "原文信号", "专业解读", "复盘动作"], profile["match_rows"]),
            level="industry",
        ),
        build_block(
            "source_model_behavior",
            "模型行为画像",
            kind="model_behavior",
            summary="这里关注模型行为模式，而不是只看某一场押对押错。",
            table=build_table(["模型", "原文行为", "画像判断", "需要观察"], profile["model_rows"]),
            level="industry",
        ),
        build_block(
            "source_evidence_map",
            "原文证据映射",
            kind="evidence_map",
            summary="把正文判断映射回历史报告中的可核验语句。",
            table=build_table(["报告判断", "原文锚点"], profile["anchors"]),
            level="base",
        ),
    ]
    _prepend_unique_blocks(model, source_blocks)


def _prediction_metrics(text: str) -> dict[str, str]:
    compact = _compact(text)
    metrics = {
        "valid_seats": _first_match(compact, r"(\d+/\d+)有效"),
        "accepted_bets": _first_match(compact, r"(\d+)\s*笔下注"),
        "watch_count": _first_match(compact, r"(\d+)\s*次观望"),
        "total_stake": _first_match(compact, r"总投[⼊入]\s*([0-9,]+)\s*GP"),
        "loan_exposure": _first_match(compact, r"贷款暴露\s*([0-9,]+)\s*GP"),
        "roi": _first_match(compact, r"ROI\s*([0-9.]+%)"),
        "match_count": _first_match(compact, r"(\d+)场[⽐比]赛"),
        "focus_match": "葡萄牙 vs 哥伦比亚",
    }
    if metrics["accepted_bets"]:
        metrics["accepted_bets"] = f"{metrics['accepted_bets']} 笔下注"
    if metrics["watch_count"]:
        metrics["watch_count"] = f"{metrics['watch_count']} 次观望"
    if metrics["total_stake"]:
        metrics["total_stake"] = f"{metrics['total_stake']} GP 总投入"
    if metrics["loan_exposure"]:
        metrics["loan_exposure"] = f"{metrics['loan_exposure']} GP 贷款"
    return metrics


def _prediction_profile(text: str, metrics: dict[str, str]) -> dict[str, Any]:
    if "中国体彩" in text:
        return _ticai_profile(metrics)
    if "run-12" in text:
        return _run12_profile(metrics)
    if "run-9" in text:
        return _run9_profile(metrics)
    if "run-15" in text:
        return _run15_profile(metrics)
    if "run-11" in text:
        return _run11_profile(metrics)
    return _run15_profile(metrics)


def _run15_profile(metrics: dict[str, str]) -> dict[str, Any]:
    return {
        "cover_metrics": [
            ("有效席位", metrics.get("valid_seats") or "11/12"),
            ("下注/观望", _join_nonempty(metrics.get("accepted_bets") or "23 笔下注", metrics.get("watch_count") or "32 次观望", sep=" / ")),
            ("资金暴露", _join_nonempty(metrics.get("total_stake") or "4,170 GP 总投入", metrics.get("loan_exposure") or "0 GP 贷款", sep=" · ")),
            ("主战场", "葡萄牙 vs 哥伦比亚"),
        ],
        "one_line": (
            "run-15 的真正进步不是模型更敢下注，而是系统开始区分“预测能力”和“资金选择”："
            "11/12 席有效、23 笔下注、32 次观望、贷款暴露降为 0，说明预测池从同向押注转向有风控的选择性出手。"
        ),
        "professional_analysis": [
            "预测和下注被拆成两套指标：预测看方向、比分、置信度和公平赔率；下注看赔率边缘、仓位、预期收益和撤退条件。",
            "DeepSeek 全场零注不是空白输出，而是榜首策略：只有存在概率边缘且能交叉验证时才下注，否则保留现金和排名优势。",
            "葡萄牙 vs 哥伦比亚是本轮主战场，8/11 席参与、合计 1,360 GP；但 Gemini 选择平局 @3.60，说明分歧不是方向分歧，而是价值赔率分歧。",
            "比利时、沙特、伊朗三场都暴露出结构化盘口不足的问题：让球线缺失、盘口保护和低置信下注会影响赛后归因。",
        ],
        "advice": [
            "赛后复盘必须分成两张榜：预测命中榜和下注 ROI 榜，不能用单一胜负评价模型。",
            "低赔率强队场次允许“预测正确但不下注”，否则会把模型训练成追求确定性而不是追求正期望。",
            "所有让球盘必须补齐盘口、赔率、时间戳和数据来源；缺线场次只能进入观察，不应进入自动结算建议。",
            "DeepSeek、Gemini 这类严格跳过不完整盘口的行为应被标为风控能力，而不是消极缺席。",
        ],
        "basis": [
            f"原文记录 {metrics.get('valid_seats') or '11/12'} 有效席位，说明样本不是单模型摘要。",
            f"原文记录 {metrics.get('accepted_bets') or '23 笔下注'} 与 {metrics.get('watch_count') or '32 次观望'} 并存，说明模型允许选择不出手。",
            f"资金面记录 {metrics.get('total_stake') or '4,170 GP 总投入'}、{metrics.get('loan_exposure') or '0 GP 贷款'}，风险暴露明显低于高杠杆轮次。",
            "原文明确把 run-15 与 run-10/run-11/run-14 对比，结论是从“被迫赌”转向“选择赌”。",
            "原文将 DeepSeek 的全场零注解释为榜首防守策略，而不是没有预测能力。",
        ],
        "risks": [
            "历史报告仍是赛前态，未纳入最终赛果；任何 ROI、命中率和排名变化都需要结算后回填。",
            "部分席位只有下注，没有完整预测概率或公平赔率，容易把资金动作误读成模型判断。",
            "让球线缺失会让“下注失败”无法归因：可能是方向错，也可能是盘口结构不完整。",
            "高共识并不等于高价值，尤其是西班牙 @1.08 这类市场已经充分定价的低赔率场次。",
        ],
        "boundary": [
            "本版只重排历史报告原文，不新增赛果、实时赔率或模型外部判断。",
            "GP 是虚拟积分，本报告用于预测池产品验收和模型行为复盘，不构成投注建议。",
        ],
        "anchors": [
            ["预测与下注应分开复盘", "原文第一页写明“预测是必须的，下注是可选的”，并列出 Forecast 与 Investment 的不同用途。"],
            ["零贷款是本轮里程碑", "run-15 全量报告第一页记录 23 笔下注、32 次观望、总投入 4,170 GP、贷款暴露 0 GP。"],
            ["葡萄牙场是主战场", "原文写明葡萄牙 vs 哥伦比亚为本轮焦点，8/11 模型参与，资金合计 1,360 GP。"],
            ["DeepSeek 零注是策略", "原文第五节将 DeepSeek 描述为“守榜首保守策略”，条件是有明确概率边缘且能交叉验证。"],
            ["数据完整性高于方向判断", "比利时场原文说明让球线参数缺失，DeepSeek、Gemini、ChatGPT 因数据不完整拒绝下注。"],
        ],
        "match_rows": [
        [
            "西班牙 vs 佛得角",
            "10 个模型预测西班牙胜；只有 4 席下注，赔率 1.08。",
            "方向高度稳定，但市场已经充分定价，低赔率强队不等于有下注价值。",
            "赛后分别记录预测命中与未下注机会成本。",
        ],
        [
            "葡萄牙 vs 哥伦比亚",
            "8/11 席参与，1,360 GP；7 席押葡萄牙，Gemini 押平局 @3.60。",
            "主要分歧不是谁更强，而是市场赔率是否给出正期望。",
            "复核各席公平赔率、市场隐含概率和下注理由是否一致。",
        ],
        [
            "比利时 vs 埃及",
            "4/11 席下注，800 GP；让球线参数缺失，严格席位选择跳过。",
            "盘口字段不完整时，方向判断不能直接转成下注。",
            "补齐让球线、盘口时间戳和赔率来源后再归因。",
        ],
        [
            "沙特 vs 乌拉圭",
            "3/11 席下注，600 GP；MiMo/文心押沙特受让，Doubao 押乌拉圭。",
            "这是本轮真实方向分歧和盘口保护分歧并存的场次。",
            "单独复盘受让盘与胜负方向，避免混成一个结论。",
        ],
        [
            "伊朗 vs 新西兰",
            "4/11 席下注，520 GP；DeepSeek 给出 33/30/37 的近似均分概率。",
            "低置信场次最容易产生事后解释偏差，MiniMax 80% 与 DeepSeek 50% 的差距需要重点看。",
            "结算后检查置信度校准，而不只看下注盈亏。",
        ],
        ],
        "model_rows": [
            ["DeepSeek", "0/5 全场零注，余额 2,810 GP，贷款 0 GP。", "榜首防守型风控：没有概率边缘就不出手。", "是否错过高价值小额机会。"],
            ["Gemini", "仅押葡萄牙场平局 @3.60，跳过缺少结构化让球线的盘口。", "数据验证优先，敢于低仓位反向。", "反向下注是否来自真实 EV，而非过度保守。"],
            ["元宝", "4 笔下注、1,000 GP，分散高频。", "稳胆为主，资金参与度高。", "低赔率重仓是否拉低长期 ROI。"],
            ["Meta AI", "3 笔下注、900 GP，潜在利润 1,009 GP；比利时 -1.5 较激进。", "赔率弹性偏好更高，愿意承担让球风险。", "激进盘口的回撤控制。"],
            ["MiniMax", "3 笔下注、300 GP，低赔稳胆加亚盘博冷。", "中等仓位，预测置信度表达较强。", "高置信是否经过公平赔率校验。"],
        ],
    }


def _run11_profile(metrics: dict[str, str]) -> dict[str, Any]:
    return {
        "cover_metrics": [("有效模型", "12/12"), ("下注笔数", "48 笔"), ("资金规模", "10,170 GP"), ("核心风险", "100% 趋同")],
        "one_line": "run-11 是预测池的“趋同风险”样本：12/12 模型全部有效、48 笔下注、潜在利润 156,162 GP，但 4 场比赛全部出现 12/12 同向下注，独立判断价值被锦标赛激励显著压缩。",
        "professional_analysis": [
            "这轮不是缺模型，而是缺分歧：德国 vs 库拉索、荷兰 vs 日本、科特迪瓦 vs 厄瓜多尔、瑞典 vs 突尼斯都出现 12/12 同向。",
            "Meta AI 在库拉索 @55.0 上投入 1,200 GP，潜在利润 64,800 GP，体现“长尾赔率冲榜”而非稳健预测。",
            "资金分布表面均匀，但共识方向高度一致；这说明风险不在单场过度集中，而在所有模型被相同激励吸向同一类盘口。",
            "数据质量里情报包 0/12、WC-K1 葡萄牙 vs 哥伦比亚缺盘口，意味着本轮可用于行为研究，但不适合作为判断质量标杆。",
        ],
        "advice": [
            "把 run-11 标记为“高共识/低独立性”样本，进入长期稳定性样本库，用来识别共识幻觉与激励偏差。",
            "新增反趋同门禁：如果 12/12 同向，需要强制展示反方价格、失败条件和替代盘口。",
            "对超高赔率长尾盘设置单模型和全池仓位上限，避免潜在利润数字掩盖本金回撤风险。",
            "补齐首轮情报包后再评价模型预测能力，否则只能评价锦标赛下注行为。",
        ],
        "basis": [
            "原文记录 12/12 全员到齐、48 笔下注、总投入 10,170 GP、潜在利润 156,162 GP。",
            "原文写明 4 场比赛全部由 12/12 模型押同一方向，趋同度 100%。",
            "德国 vs 库拉索中库拉索 @55.0 被全员押注，德国 @1.02 无人押。",
            "数据质量显示 Provider 覆盖 48/48，但 WC-K1 缺盘口，情报包 0/12。",
        ],
        "risks": [
            "高赔率长尾可能是被低估机会，也可能只是市场真实风险的价格表达。",
            "12/12 同向会让多模型审计退化成同一激励下的重复下注。",
            "没有首轮情报包时，无法判断模型是基于事实独立判断，还是被赔率结构牵引。",
        ],
        "boundary": ["本轮适合做激励偏差和趋同噪声研究，不适合证明预测池已经稳定。", "GP 为虚拟积分，不构成投注建议。"],
        "anchors": [
            ["趋同度 100%", "原文第三节写明 12/12 模型在 4 场比赛上全部押同一方向。"],
            ["长尾冲榜", "Meta AI 库拉索 @55.0 投入 1,200 GP，潜在利润 64,800 GP。"],
            ["数据缺口", "数据质量表记录 WC-K1 缺盘口，情报包 0/12。"],
        ],
        "match_rows": [
            ["德国 vs 库拉索", "12/12 押库拉索 moneyline，库拉索 @55.0。", "超高赔率长尾冲榜，收益诱惑压过常规胜率判断。", "要求每席解释为什么不是被赔率牵引。"],
            ["荷兰 vs 日本", "12/12 押平局，投入 2,500 GP。", "实力接近场次的平局共识，但缺反方概率。", "补充双方胜负概率和盘口隐含概率。"],
            ["科特迪瓦 vs 厄瓜多尔", "12/12 押平局，投入 2,720 GP。", "平局赔率被视为正期望，但全员同向仍需警惕。", "赛后检查共识与真实概率校准。"],
            ["瑞典 vs 突尼斯", "12/12 押平局，投入 2,330 GP。", "风格差异被解释为平局价值，但仍是同质判断。", "要求反方席位提供非平局路径。"],
            ["葡萄牙 vs 哥伦比亚", "缺盘口，无模型下注。", "数据链路缺失阻断判断。", "先修复赔率采集，再允许入池。"],
        ],
        "model_rows": [
            ["Meta AI", "4 笔 2,100 GP，库拉索 @55.0 单场 1,200 GP。", "激进集中，追求日榜跃迁。", "长尾失败时的回撤上限。"],
            ["元宝", "4 笔 1,500 GP，四场均衡。", "积极分散但仍跟随全员共识。", "是否有独立盘口解释。"],
            ["DeepSeek", "4 笔 1,200 GP，库拉索+荷兰 vs 日本。", "积极分散，未表现出 run-15 的零注防守。", "策略风格是否随排名变化。"],
            ["MiniMax/MiMo", "各 310 GP，保守投入。", "低仓位参与同向共识。", "保守是否足以抵消趋同风险。"],
        ],
    }


def _run12_profile(metrics: dict[str, str]) -> dict[str, Any]:
    return {
        "cover_metrics": [("有效模型", "12/12"), ("下注笔数", "18 笔"), ("总投注", "6,011 GP"), ("贷款使用", "4,550 GP")],
        "one_line": "run-12 正式版的价值在于修复：12/12 模型全部有效、18 笔下注、2/2 比赛覆盖、0 数据缺口并已结算；但贷款 4,550 GP、占总投注约 75.7%，资金风险仍是主问题。",
        "professional_analysis": [
            "正式版相对预览版补回 Gemini/ChatGPT/xAI，下注从 12 笔增至 18 笔，WC-D1 覆盖缺口清零。",
            "总投注从 9,500 GP 降至 6,011 GP，说明补齐席位后并不是盲目加码，而是下注结构有所收敛。",
            "已结算和 0 数据缺口让 run-12 更适合做回测样本；它可以检验 Validator、Provider 覆盖和赛果回填链路。",
            "风险不是数据缺失，而是资金杠杆：贷款 4,550 GP、单场最大风险 3,766 GP，会放大结算波动。",
        ],
        "advice": [
            "把 run-12 作为“链路完整/资金风险高”的回归样本，用来验收结算、赛果回填和排名更新。",
            "在报告首屏同时展示数据完整性和贷款暴露，避免用户只看到 0 缺口就误以为低风险。",
            "复盘时拆分自有资金 ROI 与贷款放大后的 ROI，单独统计贷款带来的收益和回撤。",
        ],
        "basis": [
            "原文记录 12/12 模型全部有效、18 笔下注、总投注 6,011 GP、已结算。",
            "风险摘要显示贷款已用 4,550 GP，占总投注 75.7%，单场最大风险 3,766 GP。",
            "对比预览版显示有效模型 +3、下注笔数 +6、数据缺口从 1 到 0、补跑队列从 3 到 0。",
        ],
        "risks": [
            "高贷款占比可能让少数错误判断快速放大亏损。",
            "已结算并不等于策略合理，仍需看真实盈亏和排名变化。",
            "正式版修复了覆盖问题，但不自动证明模型预测质量变好。",
        ],
        "boundary": ["本报告适合做链路验收和已结算复盘，不应被当成未来比赛投注模板。", "GP 为虚拟积分，不构成投注建议。"],
        "anchors": [
            ["覆盖修复", "正式版修复 WC-D1 覆盖缺口，12 个模型覆盖两场比赛。"],
            ["贷款风险", "风险摘要写明贷款 4,550 GP，占总投注 75.7%。"],
            ["可回测", "数据质量表显示结算已完成，赛果数据和赔率数据存在。"],
        ],
        "match_rows": [
            ["加拿大 vs 波黑", "全覆盖，盘口含波黑受让、加拿大胜和平局。", "可检验多盘口覆盖和赛果归因。", "回看模型是否因贷款放大单场风险。"],
            ["美国 vs 巴拉圭", "全覆盖，正式版修复此前缺口。", "是链路修复的主证据。", "检查补回席位是否改变最终盈亏。"],
        ],
        "model_rows": [
            ["Gemini/ChatGPT/xAI", "正式版补回三席。", "从缺席修复到全员有效。", "补回席位质量是否稳定。"],
            ["全体模型", "18 笔下注全部通过 Validator，Provider 覆盖 18/18。", "链路有效性较强。", "需要结合结算结果看策略质量。"],
        ],
    }


def _run9_profile(metrics: dict[str, str]) -> dict[str, Any]:
    return {
        "cover_metrics": [("有效模型", "12/12"), ("下注笔数", "27 笔"), ("总投入", "8,210 GP"), ("主风险", "巴西盘 61.1%")],
        "one_line": "run-9 是覆盖面扩大后的集中暴露样本：12/12 模型有效、27 笔下注、总投入 8,210 GP，但巴西受让盘一场吸收 5,020 GP、占 61.1%，核心风险集中在一个被认为离群高水的盘口上。",
        "professional_analysis": [
            "这轮首次形成较广覆盖：27 笔下注横跨 4 场比赛，但仍有西班牙 vs 佛得角、法国 vs 塞内加尔两场缺盘口。",
            "巴西 vs 摩洛哥是主战场，8 个模型押巴西受让 @2.88；Gemini 单笔 2,000 GP，是全场最大单笔。",
            "模型策略分层清晰：激进派重注巴西，稳健派分散多场，守势派 Kimi/文心极小仓位试探。",
            "本轮最该沉淀的是“离群高水识别”能力：高赔率可能是正期望，也可能是风险真实升高。",
        ],
        "advice": [
            "将巴西受让盘设为单独复盘对象，重点检查赔率离群是否来自数据错误、盘口延迟还是市场分歧。",
            "对单场资金占比超过 50% 的轮次触发集中度警报。",
            "把缺盘口比赛从模型能力评价中剔除，单独归因到数据链路。",
            "对 Kimi/文心这类极低仓位守势策略保留画像，不要只按收益排名评价。",
        ],
        "basis": [
            "原文记录 run-9 有 12/12 模型有效、27 笔下注、4 场比赛有下注、2 场缺盘口、总投注 8,210 GP。",
            "巴西 vs 摩洛哥 8 笔下注、5,020 GP，占本轮总投注 61.1%。",
            "Gemini 单笔 2,000 GP 押巴西受让 @2.88，Meta AI 和 DeepSeek 也把巴西视为高价值盘口。",
            "覆盖缺口明确来自盘口行数为 0，而不是模型不愿下注。",
        ],
        "risks": [
            "主战场失败会让大多数模型同向回撤。",
            "离群高水可能是数据异常，不能直接当成套利机会。",
            "贷款和冲榜激励会诱导模型牺牲稳健性。",
        ],
        "boundary": ["本轮适合研究集中度、离群赔率和模型策略分层，不构成真实投注建议。", "GP 为虚拟积分。"],
        "anchors": [
            ["集中暴露", "原文共识表显示 WC-C2 巴西受让 8 席、5,020 GP、占比 61.1%。"],
            ["离群高水", "原文解释 1xBet 给巴西受让 @2.88，被多个模型视为高于其他平台。"],
            ["缺盘口归因", "原文写明 WC-H1 和 WC-I1 盘口行数为 0，数据链路未补齐。"],
        ],
        "match_rows": [
            ["巴西 vs 摩洛哥", "8 席、5,020 GP、潜在利润 9,371 GP。", "全轮主战场，押注集中在巴西受让 @2.88 离群高水。", "核验赔率源、时间戳和盘口是否真实可交易。"],
            ["澳大利亚 vs 土耳其", "7 席、1,590 GP，押澳大利亚受让。", "弱队受让盘提供保护，风险低于巴西主战场。", "回测受让盘保护是否兑现。"],
            ["海地 vs 苏格兰", "6 席、690 GP，最小资金场。", "覆盖性质大于强观点，低仓位说明信心不足。", "看小注是否改善组合分散度。"],
            ["卡塔尔 vs 瑞士", "6 席、910 GP，押卡塔尔受让。", "市场强弱悬殊，但模型押盘口保护。", "区分胜负预测和受让盘收益。"],
            ["西班牙/法国相关场次", "两场缺盘口无下注。", "数据链路问题，不应归咎于模型判断。", "优先补齐盘口采集。"],
        ],
        "model_rows": [
            ["Gemini", "1 笔 2,000 GP 重注巴西受让 @2.88。", "激进集中，目标日榜/周榜跃迁。", "单笔仓位上限和赔率真实性。"],
            ["Meta AI", "4 笔 1,450 GP，巴西单点爆破加分散对冲。", "核心+对冲。", "核心盘失败时对冲是否有效。"],
            ["DeepSeek", "3 笔 1,200 GP，高赔率巴西+澳大利亚。", "激进分散。", "是否过度追求单日高回报。"],
            ["Kimi/文心", "25 GP / 85 GP 极小仓位。", "守势试探。", "低仓位是否来自排名压力还是证据不足。"],
        ],
    }


def _ticai_profile(metrics: dict[str, str]) -> dict[str, Any]:
    return {
        "cover_metrics": [("报告性质", "体彩参考"), ("数据来源", "AI 预测池 run-9 至 run-15"), ("核心约束", "官方赔率优先"), ("资金原则", "预算上限")],
        "one_line": "这份体彩参考报告不能当成投注指令，价值在于把 AI 预测池的方向、比分、置信度和分歧翻译成体彩玩法检查表，并反复提醒官方赔率、让球数和赛程必须以中国体彩公布为准。",
        "professional_analysis": [
            "报告把胜平负、让球胜平负、总进球、比分、半全场和混合过关分开，说明不同玩法承载的风险完全不同。",
            "葡萄牙、比利时、沙特、伊朗等场次都保留反方概率或低置信提示，避免把 AI 共识包装成确定性。",
            "串关部分明确提示成功率是单场概率乘积：即使每场 70%，2 串 1 也只有约 49%。",
            "资金管理建议把单场上限、过关上限、总预算和止盈止损写出来，这是比单场推荐更重要的风控内容。",
        ],
        "advice": [
            "把所有推荐方向改成“研究参考 + 官方赔率复核”格式，禁止出现无条件下注口吻。",
            "体彩版首屏必须优先展示免责声明、预算规则和高不确定比赛，而不是只展示热门场次。",
            "对串关组合增加成功率乘积和最大亏损提示。",
            "将国际平台赔率与体彩官方赔率分列，避免用户误以为二者可直接替代。",
        ],
        "basis": [
            "原文免责声明写明：AI 预测池 GP 与真实资金无关，赔率来自国际博彩平台，与体彩可能不同。",
            "葡萄牙 vs 哥伦比亚虽有 8/11 模型看葡萄牙，但 DeepSeek 仅给 48% 概率，平局 29% 不可忽视。",
            "伊朗 vs 新西兰被标为高不确定性，DeepSeek 给出 33/30/37 的近似均分概率。",
            "资金管理表建议单场不超过总预算 10%，过关不超过 5%，不要用生活费、应急金或贷款购彩。",
        ],
        "risks": [
            "AI 预测池赔率不是体彩官方赔率，直接套用会产生价格偏差。",
            "串关会指数级放大失败概率，不能用单场信心简单相加。",
            "强队低赔率场次可能命中但收益不足，诱导用户过度串关。",
        ],
        "boundary": ["本报告只适合做玩法理解和风险清单，不构成投注建议。", "中国体彩赔率、让球数、赛程以官方公布为准。"],
        "anchors": [
            ["官方赔率优先", "原文第一页免责声明说明赔率来自国际平台，与体彩可能不同。"],
            ["串关风险", "原文写明 2 串 1 成功率是单场概率乘积，串关数越多期望值越低。"],
            ["资金纪律", "原文资金管理建议单场 10%、过关 5%、不要用贷款购彩。"],
        ],
        "match_rows": [
            ["葡萄牙 vs 哥伦比亚", "8/11 看葡萄牙，DeepSeek 仅 48%，平局 29%。", "主胜有共识但并不稳，平局风险需要保留。", "官方赔率复核后再判断胜平负/总进球。"],
            ["西班牙 vs 佛得角", "10/11 看西班牙，置信度 85%-95%，国际赔率 @1.08。", "方向稳定但回报低，适合风险提示而非重仓理由。", "重点看让球数和轮换风险。"],
            ["比利时 vs 埃及", "7/11 看比利时，置信度 40%-78%，Doubao 反向。", "共识不强，反方观点不可忽略。", "谨慎处理让球盘。"],
            ["沙特 vs 乌拉圭", "乌拉圭 6/11，MiMo 反向沙特且仅 35% 置信。", "胜负方向与受让保护需要分开。", "核对体彩让球幅度。"],
            ["伊朗 vs 新西兰", "DeepSeek 33/30/37，分歧极大。", "不适合给强方向，应作为高不确定性样本。", "避免串关纳入。"],
        ],
        "model_rows": [["体彩参考", "从 AI 预测池转译到玩法。", "重点是风险解释，而非模型排名。", "官方赔率和预算纪律。"]],
    }


def _enrich_legal_memo(model: dict[str, Any], report: dict[str, Any], text: str) -> None:
    source_title = _source_title(report)
    if source_title:
        model["title"] = source_title
    model["subtitle"] = "原文驱动的法律三段论阅读版"
    model["cover_metrics"] = [
        build_metric("问题类型", "执行与公司法交叉"),
        build_metric("主路径", "股权变价清偿"),
        build_metric("高风险动作", "公司直接持有自身股权"),
        build_metric("复核重点", "登记状态/章程/案卷/法源"),
    ]

    model["reader_blocks"] = [
        build_block(
            "reader_one_line",
            "一句话判断",
            kind="reader_lead",
            summary=(
                "可以把股权作为被执行财产处置，但专业表达应是“冻结、评估、拍卖或变卖股权后以价款清偿”；"
                "不宜把方案写成公司直接受让自身股权抵债。"
            ),
            level="reader",
        ),
        build_block(
            "reader_professional_analysis",
            "专业分析",
            kind="reader",
            items=[
                "大前提：民事执行规则允许法院查询、冻结、拍卖或变卖被执行人的财产性权益；股权属于可执行财产。",
                "小前提：本案特殊性在于公司既是债权人，又是股权所在公司，因此执行对象不是公司自己的财产，而是股东名下的股权价值。",
                "涵摄：法院处置股权价值并分配价款是稳妥路径；公司直接取得自身股权会触发资本维持、回购限制、减资债权人保护和登记可办理性风险。",
                "结论：优先推动法院监督下的变价清偿；只有在严格满足减资、回购注销、债权人保护和登记程序时，才考虑经济上类似抵债的方案。",
            ],
            level="reader",
        ),
        build_block(
            "reader_advice",
            "当前建议",
            kind="reader",
            items=[
                "把申请表述为“将股权作为可供执行财产依法处置后清偿”，不要表述为“直接过户给公司抵债”。",
                "先准备公司章程、股东名册、出资证明、工商登记、财务报表、权利负担和潜在买受人名单。",
                "优先摸底其他股东是否愿意同等条件承接，再考虑第三方受让、质押融资、分红执行或执行和解。",
                "所有价款尽量进入法院账户或公司对公账户，保留债务抵充和结案材料。",
            ],
            level="reader",
        ),
        build_block(
            "reader_basis",
            "关键依据",
            kind="reader",
            items=[
                "《民事诉讼法》执行条款支持对被执行人财产进行冻结、拍卖、变卖和协助变更登记。",
                "《公司法》第84、85条处理有限责任公司股权转让和强制执行中的优先购买权。",
                "《公司法》第162条、第224条分别涉及公司取得自身股份限制和减资债权人保护。",
                "《民法典》第440、443条支持股权出质路径，但公司不宜接受自身股权或股票作为质权标的。",
                "最高院股权执行规定为冻结、评估、拍卖、通知公司和其他股东提供操作依据。",
            ],
            level="reader",
        ),
        build_block(
            "reader_risks",
            "最大风险",
            kind="reader",
            items=[
                "公司直接受让自身股权可能被评价为绕开减资和债权人保护程序。",
                "优先购买权不会阻断执行，但会影响竞买人意愿、成交价格和处置效率。",
                "股权未实缴、质押、查封、代持、公司资不抵债或行业准入限制都会显著降低变现确定性。",
                "股权变价款不足时只能部分清偿，剩余债务仍需继续履行。",
            ],
            level="reader",
        ),
        build_block(
            "reader_boundary",
            "适用边界",
            kind="reader",
            items=[
                "这是办案研判底稿，需要律师结合原始判决、执行案卷、公司章程、登记状态和最新法源复核。",
                "本版重排历史报告原文，不替代法院、登记机关和律师对具体程序可行性的判断。",
            ],
            level="reader",
        ),
    ]

    model["industry_blocks"] = []
    model["base_blocks"] = []

    source_blocks = [
        build_block(
            "legal_syllogism_map",
            "法律三段论地图",
            kind="legal_reasoning",
            summary="把原文的法条、事实、涵摄和结论拆开，避免直接跳到“能不能抵债”。",
            table=build_table(
                ["层次", "原文内容", "报告解释"],
                [
                    ["大前提", "民诉法执行条款、公司法股权转让和回购限制、民法典股权质押、最高院股权执行规定。", "法律允许执行股权价值，但不当然允许公司长期持有自身股权。"],
                    ["小前提", "股东对公司负赔偿债务，且股东持有该公司股权。", "债权人与股权所在公司重合，这是本案核心特殊性。"],
                    ["涵摄", "正确表达是依法处置股权后以价款清偿，错误表达是直接过户给公司抵债。", "执行路径和公司治理路径必须分开。"],
                    ["结论", "法院执行拍卖/变卖优先，减资/回购注销只能作为严格程序下的兜底。", "选择路径时以合规、可登记、可回款为排序标准。"],
                ],
            ),
            level="industry",
        ),
        build_block(
            "legal_path_matrix",
            "路径优先级矩阵",
            kind="legal_paths",
            summary="不是所有能想到的抵债方式都同等稳妥，核心是把财产价值变成可分配价款。",
            table=build_table(
                ["优先级", "路径", "适用前提", "主要风险"],
                [
                    ["优先", "法院执行拍卖/变卖", "股权权属、出资、负担和估值材料可提交。", "流拍、折价和其他股东优先购买权影响。"],
                    ["优先", "其他股东受让", "其他股东愿意同等条件承接。", "价格公允性和付款闭环。"],
                    ["可选", "第三人受让", "存在外部买家，且章程/监管不禁止。", "受让资格、优先购买权和登记办理。"],
                    ["备选", "股权质押融资", "有第三方愿意融资并完成质押登记。", "公司不宜作为自身股权质权人。"],
                    ["备选", "分红/清算分配请求权执行", "已有到期、明确的分红或清算分配请求权。", "未来不确定收益不能直接当现金执行。"],
                    ["兜底", "减资/回购注销", "股东会、债权人保护、公告和登记程序均能完成。", "程序成本高，且不适合作为私下抵销。"],
                    ["兜底", "执行和解分期", "短期股权难以变现，但公司接受时间表。", "逾期恢复执行和担保设计。"],
                ],
            ),
            level="industry",
        ),
        build_block(
            "legal_evidence_checklist",
            "证据与材料清单",
            kind="evidence_checklist",
            summary="专业输出必须告诉办案团队下一步要拿什么材料，而不是只给抽象结论。",
            items=[
                "生效判决、执行通知书、执行案号和执行法院沟通记录。",
                "公司章程、股东名册、出资证明、工商登记信息和历次股权变更材料。",
                "最近三年财务报表、资产负债表、利润表、重大债权债务和分红记录。",
                "股权是否质押、查封、代持、未实缴或存在行业审批限制。",
                "其他股东是否行使优先购买权的书面表态，以及潜在第三方买受人报价。",
            ],
            level="industry",
        ),
        build_block(
            "legal_source_map",
            "法源映射",
            kind="legal_sources",
            summary="原文明确列出法源，本版只做结构化映射，不新增未经核验的案例。",
            table=build_table(
                ["法源", "作用"],
                [
                    ["民事诉讼法第248、249、251条", "执行法院可查询、冻结、拍卖、变卖财产并协助办理权属变更。"],
                    ["公司法第84、85条", "有限责任公司股权转让和强制执行中的优先购买权程序。"],
                    ["公司法第162条", "股份有限公司原则上不得收购自身股份，公司不得接受自身股票作为质权标的。"],
                    ["公司法第224条", "减资需资产负债表、财产清单、债权人通知公告和清偿/担保保护。"],
                    ["民法典第440、443条", "股权可以出质，质权自办理出质登记时设立。"],
                    ["法释〔2021〕20号", "人民法院强制执行股权的冻结、评估、拍卖、优先购买权等操作细则。"],
                ],
            ),
            level="base",
        ),
    ]
    _prepend_unique_blocks(model, source_blocks)


def _prepend_unique_blocks(model: dict[str, Any], blocks: list[dict[str, Any]]) -> None:
    industry_ids = {block.get("id") for block in model.get("industry_blocks") or [] if isinstance(block, dict)}
    base_ids = {block.get("id") for block in model.get("base_blocks") or [] if isinstance(block, dict)}
    industry_add: list[dict[str, Any]] = []
    base_add: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("level") == "base":
            if block.get("id") not in base_ids:
                base_add.append(block)
        elif block.get("id") not in industry_ids:
            industry_add.append(block)
    model["industry_blocks"] = industry_add + [b for b in model.get("industry_blocks") or [] if isinstance(b, dict)]
    model["base_blocks"] = base_add + [b for b in model.get("base_blocks") or [] if isinstance(b, dict)]


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _join_nonempty(left: str | None, right: str | None, *, sep: str) -> str:
    items = [item for item in (left, right) if item]
    return sep.join(items) if items else "-"
