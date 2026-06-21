"""FDJP – Five-Dimensional Judgment Protocol constants."""

DIMENSIONS = ["philosophy", "economy", "politics", "military", "history"]

DIMENSION_LABELS = {
    "philosophy": "哲学层｜本质校验",
    "economy": "经济层｜利益结构",
    "politics": "政治层｜权力坐标",
    "military": "军事层｜战略执行",
    "history": "历史层｜时间参照",
}

DEFAULT_DIMENSION_WEIGHTS = {
    "philosophy": 0.24,
    "military": 0.22,
    "economy": 0.20,
    "politics": 0.18,
    "history": 0.16,
}

TASK_TYPE_WEIGHTS = {
    "legal": {
        "philosophy": 0.25,
        "history": 0.22,
        "politics": 0.20,
        "economy": 0.16,
        "military": 0.17,
    },
    "business": {
        "economy": 0.28,
        "military": 0.24,
        "philosophy": 0.20,
        "politics": 0.16,
        "history": 0.12,
    },
    "product": {
        "philosophy": 0.24,
        "economy": 0.24,
        "military": 0.24,
        "politics": 0.14,
        "history": 0.14,
    },
    "research": {
        "philosophy": 0.26,
        "history": 0.22,
        "economy": 0.16,
        "politics": 0.16,
        "military": 0.20,
    },
    "general": {
        "philosophy": 0.24,
        "military": 0.22,
        "economy": 0.20,
        "politics": 0.18,
        "history": 0.16,
    },
}

FDJP_VERSION = "FDJP-1.0"
FDJP_SCHEMA_VERSION = "1.0"

FDJP_P0_BLOCKERS = {
    "PHILOSOPHY_ESSENCE_MISSING": "未识别问题本质，只复述题面",
    "MILITARY_ACTION_MISSING": "没有可执行行动",
    "ECONOMY_STAKEHOLDER_MISSING": "没有识别关键利益方",
    "POLITICS_AUTHORITY_MISSING": "应识别权力结构但缺失",
    "HISTORY_PRECEDENT_REQUIRED_MISSING": "应有历史/先例/时间线但缺失",
    "FDJP_SCHEMA_INVALID": "五维审计 JSON schema 不合法",
    "FDJP_LLM_EVIDENCE_UNSUPPORTED": "LLM 证据引用不可追溯占比过高（>=50%）",
}

FDJP_P1_WARNINGS = {
    "HIDDEN_COST_WEAK": "隐形成本分析不足",
    "POWER_MAP_SHALLOW": "权力结构分析浅",
    "BAD_ANALOGY_RISK": "历史类比可能误导",
    "NO_FALLBACK_PLAN": "缺少失败预案",
    "FDJP_LLM_UNAVAILABLE_HEURISTIC_ONLY": "仅启用启发式审计，不能标 FULL_PASS",
    "FDJP_LLM_EVIDENCE_WEAK": "LLM 证据引用不可追溯占比较高（>=25%）",
}

FDJP_STATUS = {
    "FDJP_FULL_PASS": "五维审计完整通过",
    "FDJP_PASS_WITH_WARNINGS": "通过但存在警告",
    "FDJP_PARTIAL": "部分通过，存在显著信息缺口",
    "FDJP_CONTENT_BLOCKED": "内容层阻塞（P0 blocker 触发或整体认知分过低）",
    "FDJP_AUDIT_BLOCKED": "审计层阻塞（schema/system 级故障）",
    "FDJP_RUNTIME_BLOCKED": "运行层阻塞",
    "FDJP_SCHEMA_BLOCKED": "结构层阻塞",
    "FDJP_AUDIT_UNAVAILABLE": "审计不可用（异常/未初始化）",
}

VALID_FDJP_STATUSES = list(FDJP_STATUS.keys())

# ── Gate Semantics: Fixed score thresholds ──
FDJP_SCORE_THRESHOLD_FULL_PASS = 0.80
FDJP_SCORE_THRESHOLD_WARNINGS = 0.60
FDJP_SCORE_THRESHOLD_PARTIAL = 0.35
# < 0.35 → CONTENT_BLOCKED

# ── LLM/Hybrid audit mode constants ──
VALID_AUDIT_MODES = {"llm", "hybrid", "heuristic_only", "unavailable"}
DEFAULT_AUDIT_MODE = "heuristic_only"

FDJP_LLM_ERRORS = {
    "FDJP_LLM_UNAVAILABLE": "LLM provider 不可用",
    "FDJP_LLM_PARSE_FAILED": "LLM 返回无法解析",
    "FDJP_LLM_EMPTY_RESPONSE": "LLM 返回为空",
    "FDJP_LLM_JSON_EXTRACT_FAILED": "LLM JSON 提取失败",
    "FDJP_LLM_TIMEOUT": "LLM 调用超时",
    "FDJP_LLM_RATE_LIMITED": "LLM 频率限制",
}

HYBRID_LLM_WEIGHT = 0.70
HYBRID_HEURISTIC_WEIGHT = 0.30
LLM_INSUFFICIENT_DIM_CAP = 0.59

HEURISTIC_KEYWORDS = {
    "philosophy": [
        "本质", "定义", "判断标准", "概念", "边界", "性质",
        "核心问题", "根本", "原问题", "定性", "性质认定",
    ],
    "economy": [
        "成本", "收益", "利益", "资源", "清偿", "补偿",
        "执行风险", "隐形成本", "损失", "金额", "债权",
        "债务", "清偿顺序", "优先权", "财产",
    ],
    "politics": [
        "权力", "规则", "法院", "管理人", "登记权利人",
        "话语权", "主体", "被告", "管辖", "裁定",
        "司法解释", "行政", "部门", "审批",
    ],
    "military": [
        "策略", "立即", "保全", "主张", "行动", "下一步",
        "风险规避", "方案", "措施", "诉讼策略", "执行",
        "证据保全", "财产保全", "申请",
    ],
    "history": [
        "时间", "历史", "先例", "案例", "转变", "地区差异",
        "演化", "趋势", "过往", "历年", "司法实践",
        "类案", "参考", "指导案例",
    ],
}

CORE_QUESTIONS = {
    "philosophy": "问题的本质是什么？判断标准是什么？存在哪些错误 framing？",
    "economy": "关键利益方是谁？谁受益、谁付成本？隐藏成本在哪里？",
    "politics": "权力和规则掌握在谁手中？谁是规则制定者和否决者？",
    "military": "最终目标是什么？主攻点在哪里？行动顺序和风险预案？",
    "history": "时间线和先例是什么？处于什么周期阶段？类比风险？",
}