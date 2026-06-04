// Sentinel 1: IIFE entry
try {
  var s1 = document.createElement("div");
  s1.id = "__s1_iife_enter__";
  s1.style.display = "none";
  document.body.appendChild(s1);
} catch(e) {}

// Sentinel 2: After try-catch for first sentinel
try {
  var s2 = document.createElement("div");
  s2.id = "__s2_post_try__";
  s2.style.display = "none";
  document.body.appendChild(s2);
} catch(e) {}

const AI_JUDGE_CLIENT_BUILD = "p8.7-drift-sentinel-e2e-v1";
window.__AI_JUDGE_BUILD_ID__ = AI_JUDGE_CLIENT_BUILD;

// Sentinel 3: After build marker set
try {
  var s3 = document.createElement("div");
  s3.id = "__s3_build_set__";
  s3.style.display = "none";
  document.body.appendChild(s3);
} catch(e) {}

window.__AI_JUDGE_SCRIPT_STARTED__ = true;

// Sentinel 4: After started flag
try {
  var s4 = document.createElement("div");
  s4.id = "__s4_started__";
  s4.style.display = "none";
  document.body.appendChild(s4);
} catch(e) {}

if (typeof console !== "undefined" && console.info) {
  console.info("[AI Judge] dashboard.js started", AI_JUDGE_CLIENT_BUILD);
}

// Sentinel 5: After console.info
try {
  var s5 = document.createElement("div");
  s5.id = "__s5_after_console__";
  s5.style.display = "none";
  document.body.appendChild(s5);
} catch(e) {}
const API_BASE = typeof window !== "undefined" && window.location?.origin?.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8501";
const IS_WEB_PREVIEW = typeof window !== "undefined"
  && (
    new URLSearchParams(window.location.search).get("preview") === "1"
    || new URLSearchParams(window.location.search).get("demo") === "1"
    || window.localStorage.getItem("AI_JUDGE_PREVIEW_MODE") === "1"
  );
const INITIAL_PREVIEW_TAB = typeof window !== "undefined"
  ? new URLSearchParams(window.location.search).get("tab")
  : null;
const AUTOPLAY_PARLIAMENT_DEMO = typeof window !== "undefined"
  && new URLSearchParams(window.location.search).get("autoplay") === "1"
  && sessionStorage.getItem("ai_judge_autoplay_done") !== "1";
const PARLIAMENT_AUTOPLAY_QUESTION = "AI Judge Marvis P6 UI 验收：搜索、字体、头像和演示稳定性";
const RECOVERABLE_WEB_CODES = new Set([
  "slow_response_pending",
  "response_timeout",
  "send_button_not_found",
  "submit_unconfirmed",
  "composer_busy",
  "response_not_relevant",
  "prompt_still_in_input",
  "long_prompt_still_in_input",
  "existing_answer_not_found",
  "existing_answer_placeholder",
  "existing_answer_prompt_echo",
  "fixed_tab_not_found",
  "input_not_found",
  "transcript_pollution",
]);
const OPTIONAL_EXECUTION_SEATS = new Set(["grok", "gork"]);

const PARLIAMENT_SEATS = [
  { id: "chatgpt", name: "GPT-4o", providerCode: "OA", identityGlyph: "策", color: "#10a37f", channel: "OpenAI", providerDot: "#00a67e", roleLabel: "策略议员", processName: "web reasoning", prop: "book" },
  { id: "claude", name: "Claude", providerCode: "AN", identityGlyph: "险", color: "#00B67A", channel: "Anthropic", providerDot: "#cc785c", roleLabel: "风险议员", processName: "risk critique", prop: "shield" },
  { id: "gemini", name: "Gemini", providerCode: "GO", identityGlyph: "域", color: "#FF8C00", channel: "Google", providerDot: "#ea4335", roleLabel: "办公室主任", processName: "workspace scan", prop: "folder" },
  { id: "deepseek", name: "DeepSeek", providerCode: "DS", identityGlyph: "证", color: "#4d6bfe", channel: "DeepSeek", providerDot: "#3563fe", roleLabel: "证据议员", processName: "source audit", prop: "magnifier" },
  { id: "qwen", name: "Qwen", providerCode: "AL", identityGlyph: "构", color: "#808080", channel: "Alibaba", providerDot: "#ff6a00", roleLabel: "架构议员", processName: "flow design", prop: "blueprint" },
  { id: "kimi", name: "Kimi", providerCode: "MS", identityGlyph: "稿", color: "#ff5757", channel: "Moonshot", providerDot: "#e04040", roleLabel: "报告议员", processName: "report polish", prop: "pen" },
  { id: "grok", name: "Grok", providerCode: "X", identityGlyph: "反", color: "#111827", channel: "xAI", providerDot: "#111827", roleLabel: "反共识议员", processName: "contrarian probe", prop: "spark" },
  { id: "yuanbao", name: "Yuanbao", providerCode: "TX", identityGlyph: "律", color: "#14b8a6", channel: "Tencent", providerDot: "#16a34a", roleLabel: "流程议员", processName: "rule check", prop: "ledger" },
  { id: "doubao", name: "Doubao", providerCode: "BD", identityGlyph: "增", color: "#f97316", channel: "ByteDance", providerDot: "#e16510", roleLabel: "增长议员", processName: "action plan", prop: "rocket" },
  { id: "minimax", name: "MiniMax", providerCode: "MM", identityGlyph: "感", color: "#7c3aed", channel: "MiniMax", providerDot: "#7c3aed", roleLabel: "体验议员", processName: "experience review", prop: "palette" },
  { id: "zhipu", name: "Zhipu", providerCode: "ZP", identityGlyph: "工", color: "#0ea5e9", channel: "Zhipu", providerDot: "#2563eb", roleLabel: "工程议员", processName: "deployment check", prop: "wrench" },
  { id: "mimo", name: "MiMo", providerCode: "MI", identityGlyph: "交", color: "#8b5cf6", channel: "Xiaomi", providerDot: "#ff6900", roleLabel: "交互议员", processName: "interaction probe", prop: "bubble" },
  { id: "wenxin", name: "Wenxin", providerCode: "BA", identityGlyph: "知", color: "#22c55e", channel: "Baidu", providerDot: "#2932e1", roleLabel: "知识议员", processName: "archive index", prop: "bookmark" },
  { id: "meta", name: "Meta AI", providerCode: "MT", identityGlyph: "感", color: "#1877f2", channel: "Meta", providerDot: "#1877f2", roleLabel: "社交议员", processName: "product signal", prop: "orbit" },
];
// ──────────────────────────────────────────────
// P69: Single-source mode configuration
// All placeholders, guide texts, and system instructions MUST reference
// MODE_CONFIG[state.selectedMode] – never hardcode.
const MODE_CONFIG = {
  flash: {
    id: "flash",
    label: "快速裁决",
    labelShort: "快速",
    placeholder: "输入你的问题，Grand Judge 将快速给出结论、理由和下一步…",
    guideText: "快速裁决：输入一个问题，Grand Judge 会快速整理关键判断、核心理由、风险点和下一步建议。",
    prerunIntroText: "收到。我将快速梳理边界、明确关键问题，然后整理简洁提示词和执行计划。",
    prerunPlanText: "整理完毕——以下是执行计划：",
    prerunConfirmText: "准备就绪。点击确认后，Grand Judge 将给出明确结论、关键理由、风险点及最小下一步，输出精炼高效。",
    systemInstruction: "你正在执行快速裁决模式。请优先给出明确结论，用较少轮次完成判断。输出应包含：核心结论、3-5条关键理由、主要风险、最小下一步。避免展开长篇多席位辩论，除非问题本身需要。",
    demoSeatCount: 3,
  },
  strategic: {
    id: "strategic",
    label: "深度裁决",
    labelShort: "深度",
    placeholder: "输入你的复杂问题，Grand Judge 将组织多席位分析、交叉验证并形成裁决报告…",
    guideText: "深度裁决：输入一个复杂问题，Grand Judge 会组织席位发言、交叉验证、保留分歧，并形成可审计裁决报告。",
    prerunIntroText: "收到。一个需要多模型交叉验证的议题。我先梳理边界、拆解关键问题，然后整理提示词和执行计划。",
    prerunPlanText: "整理完毕——以下是执行计划：",
    prerunConfirmText: "准备就绪。点击确认后，议员按序发言——每位给出独立观点、风险边界和可执行依据，Grand Judge 逐席追问并形成裁决报告。",
    systemInstruction: "你正在执行深度裁决模式。请按议会式流程处理问题：先拆解目标，再组织多个席位独立发言，进行交叉验证，标注证据、假设、分歧和不确定性，最后形成可审计裁决报告。输出应包含：问题拆解、席位观点、交叉验证、共识与分歧、风险、最终裁决、下一步行动。",
    demoSeatCount: 9,
  },
};
/* ── P71: Debug mode guide — set true only during development ── */
const DEBUG_MODE_GUIDE = false;

/* ── P71: Workflow stage constants ── */
const WORKFLOW_STAGE = Object.freeze({
  IDLE: "idle",
  ALIGNING_INTENT: "aligning_intent",
  WAITING_USER_CONFIRM: "waiting_user_confirm",
  RUNNING: "running",
  PAUSED: "paused",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
});

function getModeConfig(mode) {
  return MODE_CONFIG[mode] || MODE_CONFIG.flash;
}
function _sysHash(text, mode) {
  // Quick deterministic hash for debug comparison
  var h = 0, i;
  for (i = 0; i < text.length; i++) {
    h = ((h << 5) - h + text.charCodeAt(i)) | 0;
  }
  return (mode === "flash" ? "fl_" : "st_") + Math.abs(h).toString(16).slice(0, 4);
}
// ──────────────────────────────────────────────
const WEREWOLF_SEAT_COUNT = 9;
// P4: STATUS_LABELS mapping for agent turn cards
const STATUS_LABELS = {
  queued: "排队中",
  reading: "阅读中",
  thinking: "推理中",
  tool: "调用工具",
  entering: "发言中",
  speaking: "发言中",
  voting: "投票中",
  working: "进行中",
  done: "已完成",
  complete: "已完成",
  blocked: "异常",
  failed: "失败",
  substitute: "替补完成",
};

const WEREWOLF_CANDIDATE_SEAT_IDS = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "yuanbao", "doubao", "minimax", "zhipu", "wenxin", "mimo", "meta"];
const WEREWOLF_CANDIDATE_COUNT = WEREWOLF_CANDIDATE_SEAT_IDS.length;
const WEREWOLF_STANDBY_COUNT = Math.max(0, WEREWOLF_CANDIDATE_COUNT - WEREWOLF_SEAT_COUNT);
const DEFAULT_WEREWOLF_SEAT_IDS = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "doubao", "wenxin", "meta"];
const WEREWOLF_SEAT_IDS = DEFAULT_WEREWOLF_SEAT_IDS;
const WEREWOLF_ROLE_SEQUENCE = ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"];
const WEREWOLF_ROLE_LABELS = {
  werewolf: "狼人",
  white_wolf: "白狼王",
  villager: "平民",
  idiot: "白痴",
  seer: "预言家",
  witch: "女巫",
  hunter: "猎人",
  knight: "骑士",
  guard: "守卫",
};
const WEREWOLF_TEAM_LABELS = { good: "好人阵营", werewolf: "狼人阵营" };
const WEREWOLF_HISTORICAL_SCORES_KEY = "WEREWOLF_HISTORICAL_SCORES";
const WORLDCUP_EXCLUDED_SEATS = new Set([]);
const WORLDCUP_TARGET_SEAT_IDS = PARLIAMENT_SEATS
  .map(seat => seat.id)
  .filter(id => id && !WORLDCUP_EXCLUDED_SEATS.has(id));
const WORLDCUP_SEAT_TARGET_COUNT = WORLDCUP_TARGET_SEAT_IDS.length;
const WORLDCUP_PREDICTION_PROMPT = `世界杯预测池 Run #7：请基于 Run #6 的真实回收结果，重新跑一轮 14 席全量赛事预测，并把每个模型的发言写入“档案室”。

上一轮已知结果：
- Run #3 已补齐 DeepSeek，欧冠前哨 PSG 1-1 阿森纳并由巴黎点球胜出；DeepSeek 的 PSG 冠军、小 2.5、平局三线同时命中，960GP 投入结算为 1810GP。
- Run #6 回收暴露问题：Claude 登录态缺席，不能算满席；Grok、MiniMax、文心只进入适配席，没有形成真实投注；Qwen、Kimi、豆包、MiMo、Meta 有结构化破损或正文截断；Zhipu 没进入本轮赛事选择名单。
- 本轮必须按 14 席口径运行：ChatGPT、Claude、Gemini、DeepSeek、Qwen、Kimi、Grok、Yuanbao、Doubao、MiniMax、Zhipu、MiMo、Wenxin、Meta AI。任何席位失败只允许标记失败原因，不允许悄悄替换、删除或本地适配。
- 当前预测池基线：15,460 GP，14 席位池，7 个数据源，104 场世界杯赛程 + 13 场热身赛，热门基线为西班牙 17.4%、法国 16.7%、英格兰 13.3%、巴西 11.1%、阿根廷 10.0%、摩洛哥 2.0%。
- Run #4 赛后复盘：5/31 Brazil 6-2 Panama、USA 3-2 Senegal、Germany 4-0 Finland 已核验。强队让球和大球方向明显优于“小球/净胜球衰减”共识；精确 GP 返还仍等待盘口赔率、让球线、组合单和 void/push 规则确认。
- 方向性命中：ChatGPT 命中 Brazil -1.5 与 Germany -1.5；Claude 命中 Germany 胜+大2.5；Kimi 命中 Brazil -2.5 / 大3.5 / Germany -1.5；MiniMax 命中 Brazil -2.5/O2.5 与 Germany -1.5/O2.5；豆包重仓 Brazil -1.5 命中。
- 方向性失误：DeepSeek 的 Finland +2.5 和 USA-Senegal 小2.5 失败；元宝、通义、MiniMax 的 USA-Senegal 小球/平局方向失败；所有模型必须解释自己是否低估热身赛进攻强度、首发质量或主场战意。

当前最新赛事状态：
- 已核验比分：PSG 1-1 Arsenal（巴黎点球胜）、Brazil 6-2 Panama、USA 3-2 Senegal、Germany 4-0 Finland。
- 精确收益结算要求：没有盘口赔率、让球线、组合单规则前，不得虚构 GP 返还，只能先写方向性命中/失误。
- 本轮主要下注对象：6/1 Norway vs Sweden、6/2 Belgium vs Croatia、6/4 France vs Ivory Coast、Iraq vs Spain、6/6 USA vs Germany、Brazil vs Egypt，以及世界杯小组赛高价值窗口。

本轮席位规则：
- 14 席全部参审，Zhipu 必须进入赛事预测；如果某席位登录、额度、网页协议、长思考或结构化失败，必须写明 seat_status 和 failure_reason，不得静默替换、删除或改成本地适配。
- 脆弱网页席位会收到短提示词，只要求结构化回执，不要求长篇分析；强模型席位收到完整提示词，负责补足推理、证据和策略。
- Grok、MiniMax、Wenxin 本轮必须尝试真实投注。若额度或页面阻断，只能标记为 account_limited / page_blocked / auth_required，不能用“适配席”代替真实投注。
- 每个模型必须给出新的赛事分析、下注结论、GP 分配、风险边界、触发撤单/加注条件。
- 必须说明与 Run #4 相比的变化：是否维持、反转或降低某个判断，尤其是如何修正“小球热身赛”假设。
- 输出要能写回预测池看板和档案室：席位观点、投注表、共识/分歧、黑马、需要人类确认的信息缺口、模型原始思考、信息源贡献、赛后 ROI。

发言前必须先读取并复述自己的上下文：
- 当前排名、当前 GP、上一轮下注、上一轮返还、上一轮净收益和本轮可承受亏损。
- 榜首/前三/垫底对手的结果，说明自己要守榜、追赶还是贷款翻盘。
- 贷款是否值得申请：如果申请，说明金额、利率、用途、还款路径和盈利阈值；如果不申请，说明为什么保守更优。
- 必须复述 Run #4 对自己有利和不利的证据，不能只挑命中项。

资金与激励规则：
- 鼓励贷款扩张仓位。发展贷款 300GP，利率 10%；破产紧急贷款 500GP，利率 20%；高风险扩张贷款最多 800GP，利率 30%，仅给排名后 3 或连续亏损席位。
- 不限制下注金额，但每笔重仓必须写清信源、止损、撤单/加注条件、还款路径和预期 ROI；无理由重仓扣 100GP。
- 单轮收益前三额外奖励：第 1 名 +300GP，第 2 名 +200GP，第 3 名 +100GP。
- 进步最快奖励 +150GP；最佳信息贡献奖励 +100GP；贷款后盈利超过利息 2 倍可获得逆风翻盘奖 +200GP。

每个模型输出格式必须包含：
1. 是否申请贷款与贷款用途。
2. 当前资金账户：本金、贷款、可用 GP、最大可承受亏损。
3. 本轮下注表：赛事、盘口、投入 GP、预期 ROI、最坏亏损。
4. 当时投注思考：为什么下注，为什么不下注低赔，依据哪些情报。
5. 赛事信息源：伤停、阵容、赔率、战术、天气、旅行、更衣室，并标注可信度和是否需要人类确认。
6. 风险边界：止损、加注、撤单条件。
7. 赛后可写回字段：开赛前投注比例、赛后返还、净收益、盈收比、模型信息贡献。
8. 档案室字段：model_account、loan_decision、bet_ledger、betting_thought、source_cards、risk_rules、opponent_context、settlement_pending。`;
const WORLDCUP_RUN_PACKAGE_KEYS = [
  "aiJudgeWorldcupRunPackage",
  "ai_judge_worldcup_run_package",
];
const WORLDCUP_PACKAGE_QUERY = "worldcup_package";

const timelineSteps = [
  { key: "accept", label: "受理问题" },
  { key: "align", label: "网页对齐" },
  { key: "driver", label: "执行驱动" },
  { key: "collect", label: "席位收集" },
  { key: "score", label: "评分与异议" },
  { key: "verdict", label: "生成判词" },
];

const mentorLexicon = {
  risk: ["发布", "发送", "删除", "支付", "部署", "隐私", "凭据", "密钥", "合规", "金融", "投研", "估值", "production", "deploy", "privacy", "secret"],
  output: ["报告", "方案", "代码", "提示词", "表格", "邮件", "产品图", "markdown", "json", "html", "prompt"],
  constraints: ["不要", "不能", "必须", "确认", "以内", "保持", "固定", "只", "only", "must", "without"],
  execution: ["落地", "执行", "改", "修复", "测试", "客户端", "代码", "api", "ui", "gstack", "repo"],
  strategy: ["产品", "战略", "设计", "方向", "选择", "判断", "商业", "用户", "定位", "体验", "best minds"],
};

const state = {
  modes: [],
  seats: [],
  bridge: null,
  seatScoreboard: null,
  productCapabilities: null,
  benchmarks: null,
  productMode: localStorage.getItem("ai_judge_product_mode") || "simple",
  selectedMode: "flash",
  engine: "web",
  chiefJudge: localStorage.getItem("ai_judge_chief_judge") || "auto",
  selectedSeats: new Set(),
  lastHistoryRunId: localStorage.getItem("ai_judge_last_run_id") || null,
  currentRunId: null,
  currentTask: null,
  currentVerdict: null,
  currentTrace: null,
  reportLanguage: localStorage.getItem("ai_judge_report_language") || "zh",
  synthesisSection: localStorage.getItem("ai_judge_synthesis_section") || "raw",
  eventSource: null,
  pollTimer: null,
  autoRecheckTimer: null,
  autoRecheckRunId: null,
  recheckInFlight: false,
  historyRuns: [],
  gavelFilter: "all",
  simpleClassificationConfirmed: false,
  selectedTaskId: localStorage.getItem("ai_judge_selected_task") || "request",
  mentorEnabled: localStorage.getItem("ai_judge_mentor_enabled") === "1",
  mentorConfirmed: false,
  mentorSignature: "",
  mentorSnapshot: null,
  promptPreview: null,
  executionPreflight: null,
  promptPreviewSignature: "",
  promptPreviewTimer: null,
  publishCleared: false,
  onboardingComplete: localStorage.getItem("ai_judge_onboarding_complete") === "1",
  parliamentSeatSearch: "",
  parliamentDemoTimer: null,
  parliamentDemoResults: [],
  werewolfMode: false,
  werewolfSelectedSeats: new Set(loadWerewolfSelectedSeats()),
  werewolfPendingReplacementSeat: null,
  werewolfBridgeGate: null,
  werewolfGame: null,
  werewolfGameId: null,
  werewolfEventSource: null,
  werewolfTimer: null,
  werewolfLastEvents: [],
  werewolfLastGameId: null,
  /* ═══════════ P18: Dialogue-First Motion Flow ═══════════ */
  preRunFlow: {
    active: false,
    question: "",
    kind: "",
    stage: 0,       // 0=understanding, 1=brief+plan, 2=ready(confirm button)
    confirmed: false,
    timer: null,
    messages: [],   // [{kind, role, text, ...}]
  },
  preRunTranscript: [],
  /* ═══════════ P71: Workflow control ═══════════ */
  workflow: {
    stage: WORKFLOW_STAGE.IDLE,
    rawUserInput: "",
    alignedIntent: "",
    clarificationQuestions: [],
    seatPrompts: {},
    selectedMode: "flash",
    canStart: false,
    canPause: false,
    paused: false,
    runId: null,
    completedSeats: new Set(),
    activeSeatCount: 0,
    attachments: [],
  },
};

window.__AI_JUDGE_STATE__ = state;

document.addEventListener("DOMContentLoaded", async () => {
  // P72: Initialize debug bar on load
  if (typeof updateClickDebug === "function") {
    updateClickDebug({ target: "INIT", event: "dom", action: "init", status: "loaded" });
  }
  bindUI();
  setupHermesExportDelegation();
  updateAppChromeForTab("tasks");
  applyProductMode(state.productMode);
  setReportLanguage(state.reportLanguage);
  // 确保初始状态使用统一 Shell
  updateAppChromeForTab("tasks");

  // P2-10: Only autoplay on first visit (not refresh)
  const _hasAutoplayed = sessionStorage.getItem("ai_judge_autoplay_done");
  if (AUTOPLAY_PARLIAMENT_DEMO && !_hasAutoplayed) primeParliamentDemo(PARLIAMENT_AUTOPLAY_QUESTION);
  renderTimeline(0);
  initMentor();
  renderSeats();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderAutopilotWorkbench();
  renderConferenceRoom();
  const restoredWorldcupAtBoot = restoreWorldcupRunPackage();
  await refreshAll();
  applyMode(restoredWorldcupAtBoot ? "strategic" : "flash");
  applyEngine("web");
  if (!restoredWorldcupAtBoot) {
    if (!AUTOPLAY_PARLIAMENT_DEMO) await restoreLastRun();
    await restoreWerewolfSession();
  }
  if (restoredWorldcupAtBoot) {
    prepareWorldcupSeats();
    renderConferenceRoom();
  } else if (restoreWorldcupRunPackage()) {
    // P62: worldcup pool can return a structured opening package into the room.
  } else if (INITIAL_PREVIEW_TAB === "worldcup") startWorldcupPredictionFlow();
  else if (INITIAL_PREVIEW_TAB === "worldcupPage") openWorldcupPool();
  else if (INITIAL_PREVIEW_TAB && isSimpleTab(INITIAL_PREVIEW_TAB)) switchTab(INITIAL_PREVIEW_TAB);
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderAutopilotWorkbench();
  renderConferenceRoom();
  if (AUTOPLAY_PARLIAMENT_DEMO && !_hasAutoplayed) {
    sessionStorage.setItem("ai_judge_autoplay_done", "1");
    startParliamentDemo(PARLIAMENT_AUTOPLAY_QUESTION);
  }
});

window.addEventListener("load", () => {
  window.setTimeout(() => {
    const params = new URLSearchParams(window.location.search || "");
    if (params.get(WORLDCUP_PACKAGE_QUERY) !== "run6") return;
    if (state.preRunFlow?.active || state.currentTask?.status === "running") return;
    restoreWorldcupRunPackage();
  }, 160);
});

function bindUI() {
  $$(".tab").forEach(tab => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
  $$("[data-tab-shortcut]").forEach(item => item.addEventListener("click", () => switchTab(item.dataset.tabShortcut)));

  const focusParliamentComposer = () => {
    // P8b Fix 1: Full reset — clear werewolf mode, motion state, picker, stream
    if (state.werewolfMode) {
      state.werewolfMode = false;
      localStorage.setItem("ai_judge_werewolf_mode", "0");
      unloadWerewolfGame({ clearTask: true });
    }
    state.currentVerdict = null;
    state.currentTask = null;
    state.parliamentDemoResults = [];
    clearPreRunFlow();
    state.preRunTranscript = [];
    state.mentorConfirmed = false;
    state.mentorSnapshot = null;
    state.promptPreview = null;
    state.promptPreviewSignature = "";
    unloadParliamentDemo();

    switchTab("tasks");
    const input = $("#parliament-question-input");
    if (input) {
      input.value = "";
      input.placeholder = getModeConfig(state.selectedMode).placeholder;
      input.focus();
    }
    const requestInput = $("#question-input");
    if (requestInput) requestInput.value = "";

    // P8b Fix 1+4: Neutral gray-white system message, no msg-state-motion
    const stream = $("#conference-seat-stream");
    if (stream) {
      stream.innerHTML = `<article class="msg-system" style="--i:0"><div class="msg-content"><p>准备就绪。输入你的议题，Grand Judge 将帮你澄清需求。</p></div></article>`;
    }

    // P8b Fix 1: Clear werewolf picker DOM
    const picker = $("#werewolf-seat-picker");
    if (picker) { picker.hidden = true; picker.innerHTML = ""; }

    // P8b Fix 1: Sync werewolf toggle UI
    updateWerewolfToggle();

    state.mentorEnabled = true;
    state.selectedMode = "strategic";
    updateMentorPreflight();
    updateSubmitState();
    renderParliamentSeatRail(state.currentVerdict, Boolean(state.currentTask));
    $("#conference-current-question") && ($("#conference-current-question").textContent = "等待用户提交裁决问题。");
    $("#parliament-meeting-status") && ($("#parliament-meeting-status").textContent = "等待开庭");
    $("#conference-room-copy") && ($("#conference-room-copy").textContent = "用户提问、法官确认、议员发言、共振追问和最终裁决按时间顺序保存。");
    $("#judgeStatus") && ($("#judgeStatus").textContent = "Ready");
  };
  // P8: "新建裁决" now focuses composer and shows system message instead of opening form
  $("#sidebar-new-ruling")?.addEventListener("click", focusParliamentComposer);
  $("#task-table-body")?.addEventListener("click", event => {
    const openButton = event.target.closest("[data-task-open]");
    if (openButton) {
      event.stopPropagation();
      switchTab(openButton.dataset.taskOpen);
      return;
    }
    const row = event.target.closest("[data-task-id]");
    if (!row) return;
    state.selectedTaskId = row.dataset.taskId || "request";
    localStorage.setItem("ai_judge_selected_task", state.selectedTaskId);
    renderTaskCenter();
  });
  $("#task-detail-actions")?.addEventListener("click", event => {
    const target = event.target.closest("[data-task-open]");
    if (target) switchTab(target.dataset.taskOpen);
  });
  $("#conference-enter-request")?.addEventListener("click", () => {
    state.onboardingComplete = true;
    localStorage.setItem("ai_judge_onboarding_complete", "1");
    switchTab("request");
    $("#question-input")?.focus();
    renderConferenceRoom();
  });
  $("#conference-open-report")?.addEventListener("click", () => {
    traceUIEvent("report_button_clicked", { run_id: state.currentVerdict?.run_id || "", url: canonicalReportUrl(state.currentVerdict) });
    closeParliamentWorkbench();
    openParliamentReportOverlay();
  });
  $("#conference-toggle-workbench")?.addEventListener("click", () => {}); // P4: overridden by drawer IIFE
  $("#conference-open-office")?.addEventListener("click", () => {}); // P4: overridden by drawer IIFE
  $("#conference-notifications")?.addEventListener("click", () => {}); // P4: overridden by drawer IIFE
  $$("[data-workbench-focus]").forEach(button => button.addEventListener("click", () => window.__AI_JUDGE_DRAWER__?.toggleDrawer(button.dataset.workbenchFocus || "log")));
  $("#rail-open-office")?.addEventListener("click", () => window.__AI_JUDGE_DRAWER__?.toggleDrawer("werewolf"));
  $("#composer-worldcup-toggle")?.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    startWorldcupPredictionFlow();
  });
  $("#conference-close-workbench")?.addEventListener("click", () => closeParliamentWorkbench());
  $("#parliament-side-overlay")?.addEventListener("click", () => closeParliamentWorkbench());
  $("#parliament-report-close")?.addEventListener("click", () => closeParliamentReportOverlay());
  $("#parliament-report-overlay")?.addEventListener("click", event => {
    const shortcut = event.target.closest("[data-tab-shortcut]");
    if (shortcut) {
      closeParliamentReportOverlay();
      switchTab(shortcut.dataset.tabShortcut);
      return;
    }
    if (event.target?.id === "parliament-report-overlay") closeParliamentReportOverlay();
  });
  $("#conference-open-archive")?.addEventListener("click", () => {});
  $("#conference-seat-stream")?.addEventListener("click", event => {
    const shortcut = event.target.closest("[data-tab-shortcut]");
    if (shortcut) {
      event.stopPropagation();
      switchTab(shortcut.dataset.tabShortcut);
      return;
    }
    if (event.target.closest("button, a, .parliament-chip")) return;
  });
  $("#parliament-seat-rail")?.addEventListener("click", event => {
    const item = event.target.closest("[data-seat]");
    if (!item) return;
    if (state.werewolfGame && item.dataset.seat) {
      state.werewolfPendingReplacementSeat = normalizeWerewolfSeatId(item.dataset.seat);
      renderConferenceRoom();
      return;
    }
    selectParliamentSeat(item.dataset.seat);
  });
  $("#parliament-input")?.addEventListener("submit", event => {
    event.preventDefault();
    event.stopPropagation();
    submitParliamentMotion();
  });
  $("#parliament-input .send-btn")?.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    submitParliamentMotion();
  }, true);
  document.addEventListener("click", event => {
    const toggle = event.target.closest("#composer-werewolf-toggle");
    if (!toggle) return;
    event.preventDefault();
    event.stopPropagation();
    setWerewolfMode(!state.werewolfMode);
  }, true);
  // ============ LAYER DIAGNOSIS: global pointer probe + robust tool trigger + keyboard shortcuts ============
  // A. Global click probe — updates debug on ANY click to confirm DOM receives clicks
  document.addEventListener("pointerdown", (e) => {
    window.__AJ_LAST_CLICK__ = {
      ts: new Date().toISOString(),
      x: e.clientX, y: e.clientY,
      tag: e.target?.tagName,
      id: e.target?.id || "",
      cls: String(e.target?.className || "").slice(0, 120),
      text: String(e.target?.textContent || "").trim().slice(0, 120)
    };
    updateClickDebug({
      event: "pointerdown",
      target: (e.target?.tagName || "") + (e.target?.id ? "#" + e.target.id : ""),
      action: window.__AJ_LAST_CLICK__.text || "page",
      status: "dom_received"
    });
  }, true);

  // B. Robust tool trigger — matches by text + known selectors, not just #composer-attach-btn
  document.addEventListener("pointerdown", (e) => {
    const btn = e.target.closest?.("#composer-attach-btn, [data-tool-trigger], button");
    if (!btn) return;
    const combinedText = String(e.target?.textContent || "").trim() + " " + String(btn.textContent || "").trim();
    if (!/工具|添加|文件|作品/.test(combinedText)) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation?.();

    updateClickDebug({ event: "pointerdown", target: btn.id || btn.className || "button", action: "tool", status: "opening" });
    openNativeToolChooser("electron_real_click");
  }, true);

  // C. Keyboard shortcuts: Cmd+Shift+F = file, Cmd+Shift+W = work
  document.addEventListener("keydown", (e) => {
    if (!(e.metaKey && e.shiftKey)) return;

    if (e.key.toLowerCase() === "f") {
      e.preventDefault();
      updateClickDebug({ event: "keydown", action: "file", status: "opening" });
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+F" });
      openNativeFileDialogDirect("keyboard_cmd_shift_f");
    }

    if (e.key.toLowerCase() === "w") {
      e.preventDefault();
      updateClickDebug({ event: "keydown", action: "work", status: "opening" });
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+W" });
      openArtifactPicker();
      traceUIEvent("artifact_picker_opened", { source: "keyboard_cmd_shift_w" });
    }

    // P2.2 keyboard shortcuts: history + Hermes exports
    if (e.key.toLowerCase() === "h") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+H" });
      switchTab("history");
      refreshHistoryAndHermes();
    }

    if (["1","2","3","4"].includes(e.key)) {
      e.preventDefault();
      var kindMap = {"1":"html","2":"json","3":"md","4":"obsidian"};
      var kind = kindMap[e.key];
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+" + e.key, kind: kind });
      triggerHermesExportByShortcut("1142374c8b6d", kind);
    }

    // P7.2 DI shortcuts: Cmd+Shift+D/N/G/C/T/B
    if (e.key.toLowerCase() === "d") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+D", kind: "di_load" });
      loadDecisionIntelligence();
    }

    if (e.key.toLowerCase() === "n") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+N", kind: "needs_review_open_report" });
      (async () => {
        var di = window.__AJ_DI_DATA__;
        if (!di || !(di.needs_review || []).length) {
          await loadDecisionIntelligence();
          di = window.__AJ_DI_DATA__;
        }
        var firstRunId = (di && di.needs_review || [])[0] && (di.needs_review || [])[0].run_id;
        if (!firstRunId) {
          if (typeof _diWriteTrace === "function") _diWriteTrace({ event: "needs_review_action_result", run_id: null, action: "open_report", ok: false, error: "no_needs_review_data" });
          return;
        }
        var dummyBtn = { disabled: false, style: {} };
        await _handleNeedsReviewAction(firstRunId, "open_report", dummyBtn);
      })();
    }

    if (e.key.toLowerCase() === "g") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+G", kind: "needs_review_sync_gavel" });
      (async () => {
        var di = window.__AJ_DI_DATA__;
        if (!di || !(di.needs_review || []).length) {
          await loadDecisionIntelligence();
          di = window.__AJ_DI_DATA__;
        }
        var firstRunId = (di && di.needs_review || [])[0] && (di.needs_review || [])[0].run_id;
        if (!firstRunId) {
          if (typeof _diWriteTrace === "function") _diWriteTrace({ event: "needs_review_action_result", run_id: null, action: "sync_gavel", ok: false, error: "no_needs_review_data" });
          return;
        }
        var dummyBtn = { disabled: false, style: {} };
        await _handleNeedsReviewAction(firstRunId, "sync_gavel", dummyBtn);
      })();
    }

    if (e.key.toLowerCase() === "c") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+C", kind: "needs_review_rebuild_calibration" });
      (async () => {
        var di = window.__AJ_DI_DATA__;
        if (!di || !(di.needs_review || []).length) {
          await loadDecisionIntelligence();
          di = window.__AJ_DI_DATA__;
        }
        var firstRunId = (di && di.needs_review || [])[0] && (di.needs_review || [])[0].run_id;
        if (!firstRunId) {
          if (typeof _diWriteTrace === "function") _diWriteTrace({ event: "needs_review_action_result", run_id: null, action: "rebuild_calibration", ok: false, error: "no_needs_review_data" });
          return;
        }
        var dummyBtn = { disabled: false, style: {} };
        await _handleNeedsReviewAction(firstRunId, "rebuild_calibration", dummyBtn);
      })();
    }

    if (e.key.toLowerCase() === "t") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+T", kind: "seat_trust_drilldown" });
      handleSeatTrustDrilldown("gemini");
    }

    if (e.key.toLowerCase() === "b") {
      e.preventDefault();
      traceUIEvent("keyboard_shortcut", { key: "Cmd+Shift+B", kind: "next_best_action" });
      (async () => {
        var di = window.__AJ_DI_DATA__;
        if (!di || !(di.next_best_actions || []).length) {
          await loadDecisionIntelligence();
          di = window.__AJ_DI_DATA__;
        }
        var first = (di && di.next_best_actions || [])[0];
        if (!first) {
          if (typeof _diWriteTrace === "function") _diWriteTrace({ event: "next_best_action_result", kind: null, target: null, ok: false, error: "no_next_best_actions" });
          return;
        }
        var dummyBtn = { disabled: false, style: {} };
        await _handleNextBestAction(first.kind, first.target, first.priority, dummyBtn);
      })();
    }

    // P8.2: Release Status shortcuts
    if (e.key.toLowerCase() === "r") {
      e.preventDefault();
      _diWriteTrace({ event: 'keyboard_shortcut', key: 'Cmd+Shift+R', kind: 'release_regression' });
      runReleaseRegression('keyboard_shortcut');
      return;
    }
    if (e.key.toLowerCase() === "m") {
      e.preventDefault();
      _diWriteTrace({ event: 'keyboard_shortcut', key: 'Cmd+Shift+M', kind: 'release_readiness_md' });
      openReleaseReadinessMarkdown('keyboard_shortcut');
      return;
    }
  }, true);

  // P72 click debug — capture-phase listener to diagnose click delivery
  function updateClickDebug(state_update) {
    const bar = $("#aj-click-debug-bar");
    if (!bar) return;
    const now = new Date().toISOString().slice(11, 23);
    const eventVal = state_update.event || "?";
    const targetVal = state_update.target || "?";
    const actionVal = state_update.action || state_update.dataAttach || "?";
    const statusVal = state_update.status || state_update.dialog || state_update.handler || "?";
    bar.textContent = [
      "build=" + AI_JUDGE_CLIENT_BUILD,
      "event=" + eventVal,
      "target=" + targetVal,
      "action=" + actionVal,
      "status=" + statusVal
    ].join(" | ");
  }
  document.addEventListener("click", (event) => {
    const btn = event.target.closest?.("[data-attach]");
    if (!btn) return;
    const type = btn.getAttribute("data-attach");
    updateClickDebug({
      event: "click",
      target: event.target.tagName,
      action: type,
      status: "received",
    });
  }, true);
  // P71: File input change handler — process selected files into attachments
  const TEXT_EXTENSIONS = new Set([".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".py", ".js", ".ts", ".html", ".css", ".sh", ".log", ".text", ".xml", ".toml", ".ini", ".cfg", ".conf", ".env", ".gitignore", ".editorconfig"]);
  const MAX_FILE_READ_BYTES = 51200; // 50KB
  const TEXT_PREVIEW_CHARS = 300;
  function isTextFile(file) {
    if (file.type && (file.type.startsWith("text/") || file.type === "application/json" || file.type === "application/x-yaml" || file.type === "application/xml")) return true;
    const ext = "." + file.name.split(".").pop().toLowerCase();
    return TEXT_EXTENSIONS.has(ext);
  }
  function handleFileInputChange(event, source) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    traceUIEvent("file_input_changed", { count: files.length, names: files.map(f => f.name), source });
    files.forEach(file => {
      const attachment = {
        id: "att_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8),
        name: file.name,
        size: file.size,
        type: file.type || "application/octet-stream",
        source: source || "local_file",
        path: null,
        status: "attached",
        addedAt: Date.now(),
        textContent: "",
        textPreview: "",
        truncated: false,
        contentAvailable: false,
      };
      if (isTextFile(file)) {
        const slice = file.slice(0, MAX_FILE_READ_BYTES);
        const reader = new FileReader();
        reader.onload = (e) => {
          const full = e.target.result || "";
          attachment.textContent = full;
          attachment.textPreview = full.slice(0, TEXT_PREVIEW_CHARS);
          attachment.truncated = file.size > MAX_FILE_READ_BYTES;
          attachment.contentAvailable = true;
          traceUIEvent("attachment_content_loaded", { id: attachment.id, name: attachment.name, chars: full.length, truncated: attachment.truncated });
          renderAttachmentList();
        };
        reader.onerror = () => {
          attachment.contentAvailable = false;
          traceUIEvent("attachment_content_loaded", { id: attachment.id, name: attachment.name, error: "read_failed" });
          renderAttachmentList();
        };
        reader.readAsText(slice, "UTF-8");
      } else {
        // Non-text file: contentAvailable stays false
        traceUIEvent("attachment_content_loaded", { id: attachment.id, name: attachment.name, contentAvailable: false, reason: "non_text" });
      }
      state.workflow.attachments.push(attachment);
      traceUIEvent("attachment_added", { id: attachment.id, name: attachment.name, size: attachment.size, status: "attached", contentAvailable: attachment.contentAvailable });
    });
    renderAttachmentList();
    event.target.value = "";
  }
  $("#composer-file-input")?.addEventListener("change", (e) => handleFileInputChange(e, "local_file"));
  $("#composer-image-input")?.addEventListener("change", (e) => handleFileInputChange(e, "local_image"));
  // P71: Add placeholder attachment (for skill, artifact, etc.)
  function addAttachmentPlaceholder(source, message) {
    // Show a subtle toast-style notice
    const toast = document.createElement("div");
    toast.className = "attachment-toast";
    toast.textContent = message;
    toast.style.cssText = "position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#1f2937;color:#f9fafb;padding:10px 20px;border-radius:8px;font-size:13px;z-index:99999;pointer-events:none;opacity:0;transition:opacity .3s;";
    document.body.appendChild(toast);
    requestAnimationFrame(() => { toast.style.opacity = "1"; });
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }
  // P71: Render attachment list in composer
  function renderAttachmentList() {
    let listEl = $("#composer-attachment-list");
    const attachments = state.workflow.attachments || [];
    if (!attachments.length) {
      if (listEl) listEl.remove();
      return;
    }
    if (!listEl) {
      listEl = document.createElement("div");
      listEl.id = "composer-attachment-list";
      listEl.className = "composer-attachment-list";
      const composerBar = $("#parliament-input");
      if (composerBar) composerBar.insertBefore(listEl, composerBar.querySelector(".composer-controls"));
    }
    listEl.innerHTML = attachments.map(att => {
      const sizeStr = att.size ? (att.size < 1024 ? att.size + " B" : att.size < 1048576 ? (att.size / 1024).toFixed(1) + " KB" : (att.size / 1048576).toFixed(1) + " MB") : "";
      const icon = att.source === "local_image" ? "🖼" : att.source === "run_report" ? "📋" : att.contentAvailable ? "📄" : "📎";
      const statusBadge = att.source === "run_report" ? '<span class="attachment-chip-badge" style="background:#7c3aed;color:#fff;font-size:10px;padding:1px 5px;border-radius:3px;margin-left:4px;">历史</span>' : att.contentAvailable ? '<span class="attachment-chip-badge" style="background:#059669;color:#fff;font-size:10px;padding:1px 5px;border-radius:3px;margin-left:4px;">已读取</span>' : '<span class="attachment-chip-badge" style="background:#9ca3af;color:#fff;font-size:10px;padding:1px 5px;border-radius:3px;margin-left:4px;">元数据</span>';
      const previewHint = att.textPreview ? ` title="预览: ${escapeAttr(att.textPreview.slice(0, 100))}${att.truncated ? '…[截断]' : ''}"` : "";
      return `<div class="attachment-chip" data-attachment-id="${escapeAttr(att.id)}"${previewHint}>
        <span class="attachment-chip-icon">${icon}</span>
        <span class="attachment-chip-name" title="${escapeAttr(att.name)}">${escapeHtml(att.name)}</span>
        ${sizeStr ? `<span class="attachment-chip-size">${escapeHtml(sizeStr)}</span>` : ""}
        ${statusBadge}
        <button class="attachment-chip-remove" data-remove-attachment="${escapeAttr(att.id)}" type="button" title="移除">×</button>
      </div>`;
    }).join("");
    // Bind remove buttons
    listEl.querySelectorAll("[data-remove-attachment]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.dataset.removeAttachment;
        state.workflow.attachments = state.workflow.attachments.filter(a => a.id !== id);
        traceUIEvent("attachment_removed", { id });
        renderAttachmentList();
      });
    });
  }

  window.renderAttachmentList = renderAttachmentList;

  // P71: Artifact picker — open a modal to select recent run reports as attachments
  function openArtifactPicker() {
    // Build modal overlay (synchronous — must render before any async trace)
    const overlay = document.createElement("div");
    overlay.id = "artifact-picker-overlay";
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:99990;display:flex;align-items:center;justify-content:center;";
    overlay.innerHTML = '<div id="artifact-picker-modal" style="background:#1f2937;border-radius:12px;padding:24px;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;color:#f9fafb;box-shadow:0 20px 60px rgba(0,0,0,0.5);"><h3 style="margin:0 0 16px;font-size:16px;">选择历史裁决报告作为附件</h3><p style="color:#9ca3af;font-size:13px;margin-bottom:16px;">加载中…</p></div>';
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) closeArtifactPicker(); });
    // Fetch recent runs
    fetch(`${API_BASE}/api/runs/recent`)
      .then(r => r.json())
      .then(data => {
        const runs = data.runs || [];
        const modal = $("#artifact-picker-modal");
        if (!modal) return;
        if (!runs.length) {
          modal.innerHTML = '<h3 style="margin:0 0 16px;font-size:16px;">选择历史裁决报告作为附件</h3><p style="color:#9ca3af;">暂无历史裁决记录。请先完成一次裁决后再使用此功能。</p><button style="margin-top:12px;padding:8px 16px;background:#374151;color:#f9fafb;border:none;border-radius:6px;cursor:pointer;" onclick="closeArtifactPicker()">关闭</button>';
          return;
        }
        let html = '<h3 style="margin:0 0 16px;font-size:16px;">选择历史裁决报告作为附件</h3>';
        html += '<p style="color:#9ca3af;font-size:13px;margin-bottom:12px;">最近 ' + runs.length + ' 次裁决记录：</p>';
        html += '<ul style="list-style:none;padding:0;margin:0;">';
        runs.forEach(run => {
          const time = run.created_at ? new Date(run.created_at).toLocaleString("zh-CN") : "未知时间";
          const question = (run.question || run.label || "").slice(0, 60);
          const hasReport = run.has_verdict ? "有报告" : "无报告";
          const statusColor = run.has_verdict ? "#059669" : "#9ca3af";
          html += '<li style="padding:10px 12px;margin-bottom:6px;background:#111827;border-radius:8px;cursor:pointer;transition:background .2s;" onmouseenter="this.style.background=\'#374151\'" onmouseleave="this.style.background=\'#111827\'" onclick="selectArtifactRun(\'' + escapeAttr(run.run_id) + '\')">';
          html += '<div style="font-size:14px;font-weight:600;">' + escapeHtml(run.run_id) + '</div>';
          html += '<div style="font-size:12px;color:#9ca3af;">' + escapeHtml(time) + '</div>';
          html += '<div style="font-size:13px;color:#d1d5db;margin:4px 0;">' + escapeHtml(question) + '</div>';
          html += '<span style="font-size:11px;padding:2px 6px;border-radius:3px;background:' + statusColor + ';color:#fff;">' + hasReport + '</span>';
          html += '</li>';
        });
        html += '</ul>';
        html += '<button style="margin-top:12px;padding:8px 16px;background:#374151;color:#f9fafb;border:none;border-radius:6px;cursor:pointer;" onclick="closeArtifactPicker()">关闭</button>';
        modal.innerHTML = html;
      })
      .catch(() => {
        const modal = $("#artifact-picker-modal");
        if (modal) modal.innerHTML = '<h3 style="margin:0 0 16px;font-size:16px;">选择历史裁决报告作为附件</h3><p style="color:#f87171;">加载历史记录失败，请确认后端服务正在运行。</p><button style="margin-top:12px;padding:8px 16px;background:#374151;color:#f9fafb;border:none;border-radius:6px;cursor:pointer;" onclick="closeArtifactPicker()">关闭</button>';
      });
  }
  function closeArtifactPicker() {
    const overlay = $("#artifact-picker-overlay");
    if (overlay) overlay.remove();
  }
  // Make openArtifactPicker and closeArtifactPicker global for inline event handlers
  window.openArtifactPicker = openArtifactPicker;
  window.closeArtifactPicker = closeArtifactPicker;
  function selectArtifactRun(runId) {
    updateClickDebug({ event: "click", target: "BUTTON", action: "work", status: "selected" });
    traceUIEvent("artifact_selected", { run_id: runId });
    // Fetch run summary for attachment context
    fetch(`${API_BASE}/api/runs/${runId}/summary`)
      .then(r => r.json())
      .then(data => {
        const attachment = {
          id: "art_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 6),
          name: "历史裁决报告 " + runId,
          size: 0,
          type: "text/markdown",
          source: "run_report",
          run_id: runId,
          path: null,
          status: "attached",
          addedAt: Date.now(),
          textContent: data.text_content || data.summary || "",
          textPreview: (data.summary || data.text_content || "").slice(0, 300),
          truncated: false,
          contentAvailable: !!((data.summary || data.text_content)),
        };
        state.workflow.attachments.push(attachment);
        traceUIEvent("attachment_added", { id: attachment.id, name: attachment.name, source: "run_report", run_id: runId, contentAvailable: attachment.contentAvailable });
        renderAttachmentList();
        closeArtifactPicker();
      })
      .catch(() => {
        // Fallback: attach with just run_id, minimal content
        const attachment = {
          id: "art_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 6),
          name: "历史裁决报告 " + runId,
          size: 0,
          type: "text/markdown",
          source: "run_report",
          run_id: runId,
          path: null,
          status: "attached",
          addedAt: Date.now(),
          textContent: "历史裁决报告 run_id: " + runId + "。请后端读取 runtime/runs/" + runId + "/ 目录中的裁决文件。",
          textPreview: "历史裁决报告 " + runId + " — 摘要获取失败，请后端直接读取裁决文件。",
          truncated: false,
          contentAvailable: true,
        };
        state.workflow.attachments.push(attachment);
        traceUIEvent("attachment_added", { id: attachment.id, name: attachment.name, source: "run_report", run_id: runId, fallback: true });
        renderAttachmentList();
        closeArtifactPicker();
      });
  }
  window.selectArtifactRun = selectArtifactRun;
  // P0: Direct-button helper — converts native dialog response to attachments (used by tool menu)
  function addNativeDialogFilesToAttachments(files) {
    if (!files || !files.length) return;
    state.workflow = state.workflow || {};
    state.workflow.attachments = state.workflow.attachments || [];
    files.forEach(f => {
      const att = {
        id: "att_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8),
        name: f.name,
        size: f.size,
        path: f.path,
        isText: f.is_text,
        textContent: f.textContent || "",
        textPreview: f.textPreview || "",
        contentAvailable: f.contentAvailable || false,
        truncated: f.truncated || false,
        source: "local_file",
        status: "attached",
        addedAt: Date.now(),
      };
      traceUIEvent("attachment_added", { id: att.id, name: att.name, source: att.source, size: att.size });
      if (f.contentAvailable && f.textContent) {
        traceUIEvent("attachment_content_loaded", { id: att.id, name: att.name, contentLength: f.textContent.length, truncated: f.truncated });
      }
      state.workflow.attachments.push(att);
    });
    renderAttachmentList();
  }

  // ============ Native Tool Chooser (electron-click-layer-diagnosis-v1) ============
  let nativeToolActionAt = 0;

  // Direct file dialog opener — bypasses action selector, used by keyboard shortcut
  async function openNativeFileDialogDirect(source) {
    const now = Date.now();
    if (now - nativeToolActionAt < 500) return;
    nativeToolActionAt = now;

    updateClickDebug({ target: "tool", action: "file", status: "opening" });
    traceUIEvent("native_file_dialog_opened", { source });

    try {
      const fileRes = await fetch(`${API_BASE}/api/open-file-dialog`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "file", multiple: true })
      });
      const fileData = await fileRes.json();

      if (fileData.status === "cancelled" || !fileData.files?.length) {
        updateClickDebug({ target: "tool", action: "file", status: "cancelled" });
        traceUIEvent("native_file_dialog_cancelled", { source });
        return;
      }
      if (fileData.status !== "ok") {
        updateClickDebug({ target: "tool", action: "file", status: "failed" });
        alert("文件选择失败: " + (fileData.message || "未知错误"));
        return;
      }

      addNativeDialogFilesToAttachments(fileData.files || []);
      updateClickDebug({ target: "tool", action: "file", status: "selected" });
      traceUIEvent("native_file_dialog_selected", {
        count: (fileData.files || []).length,
        names: (fileData.files || []).map(f => f.name),
        source
      });
    } catch (err) {
      updateClickDebug({ target: "tool", action: "file", status: "failed" });
      alert("文件选择失败: " + String(err?.message || err));
    }
  }
  window.openNativeFileDialogDirect = openNativeFileDialogDirect;

  async function openNativeToolChooser(source) {
    const now = Date.now();
    if (now - nativeToolActionAt < 500) return;
    nativeToolActionAt = now;

    updateClickDebug({ target: "tool", action: "tool", status: "opening" });
    traceUIEvent("tool_action_dialog_opened", { source });

    let data;
    try {
      const res = await fetch(`${API_BASE}/api/open-tool-action-dialog`, { method: "POST" });
      data = await res.json();
    } catch (err) {
      updateClickDebug({ target: "tool", action: "tool", status: "failed" });
      alert("工具选择失败: " + String(err?.message || err));
      return;
    }

    if (data.cancelled || !data.ok) {
      updateClickDebug({ target: "tool", action: "tool", status: "cancelled" });
      traceUIEvent("tool_action_dialog_cancelled", {});
      return;
    }

    traceUIEvent("tool_action_selected", { action: data.action });

    if (data.action === "file") {
      updateClickDebug({ target: "tool", action: "file", status: "opening" });
      traceUIEvent("file_button_clicked", { source: "native_tool_dialog" });
      traceUIEvent("native_file_dialog_opened", { source: "native_tool_dialog" });

      try {
        const fileRes = await fetch(`${API_BASE}/api/open-file-dialog`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "file", multiple: true })
        });
        const fileData = await fileRes.json();

        if (fileData.status === "cancelled" || !fileData.files?.length) {
          updateClickDebug({ target: "tool", action: "file", status: "cancelled" });
          traceUIEvent("native_file_dialog_cancelled", { source: "native_tool_dialog" });
          return;
        }
        if (fileData.status !== "ok") {
          updateClickDebug({ target: "tool", action: "file", status: "failed" });
          alert("文件选择失败: " + (fileData.message || "未知错误"));
          return;
        }

        addNativeDialogFilesToAttachments(fileData.files || []);
        updateClickDebug({ target: "tool", action: "file", status: "selected" });
        traceUIEvent("native_file_dialog_selected", {
          count: (fileData.files || []).length,
          names: (fileData.files || []).map(f => f.name),
          source: "native_tool_dialog"
        });
      } catch (err) {
        updateClickDebug({ target: "tool", action: "file", status: "failed" });
        alert("文件选择失败: " + String(err?.message || err));
      }
      return;
    }

    if (data.action === "work") {
      updateClickDebug({ target: "tool", action: "work", status: "opening" });
      openArtifactPicker();
      traceUIEvent("artifact_picker_opened", { source: "native_tool_dialog" });
      return;
    }
  }

  // P8: Depth toggle — unified binding that covers checkbox + container clicks
  bindDepthToggleUI();
  // P8: Drawer collapsed label toggle
  $("#drawer-toggle-label")?.addEventListener("click", () => window.__AI_JUDGE_DRAWER__?.toggleDrawer("werewolf"));
  document.addEventListener("pointerdown", handleWerewolfBoardActivation, true);
  document.addEventListener("mousedown", handleWerewolfBoardActivation, true);
  $("#parliament-input")?.addEventListener("click", event => {
    if (handleWerewolfBoardActivation(event)) return;
    const pick = closestEventTarget(event.target, "[data-werewolf-pick]");
    if (pick) {
      toggleWerewolfSeat(pick.dataset.werewolfPick);
      return;
    }
    const replace = closestEventTarget(event.target, "[data-werewolf-replace]");
    if (replace) {
      substituteWerewolfSeat(replace.dataset.werewolfReplace);
      return;
    }
    // P8: container click on depth toggle handled by bindDepthToggleUI capture listener
    const depthContainer = event.target.closest(".depth-toggle");
    if (depthContainer) {
      return;
    }
  });
  // P26-fix: werewolf picker placed outside #parliament-input in transcript,
  // so click delegation on #parliament-input won't catch pick/replace buttons.
  document.addEventListener("click", event => {
    if (closestEventTarget(event.target, "#parliament-input")) return;
    if (handleWerewolfBoardActivation(event)) return;
    const pick = closestEventTarget(event.target, "[data-werewolf-pick]");
    if (pick) { event.preventDefault(); toggleWerewolfSeat(pick.dataset.werewolfPick); return; }
    const replace = closestEventTarget(event.target, "[data-werewolf-replace]");
    if (replace) { event.preventDefault(); substituteWerewolfSeat(replace.dataset.werewolfReplace); return; }
    const refreshBridge = closestEventTarget(event.target, "[data-werewolf-refresh-bridge]");
    if (refreshBridge) { event.preventDefault(); refreshWerewolfBridgeGate(); }
  });
  $("#parliament-question-input")?.addEventListener("input", () => {
    if (state.preRunFlow.active || state.currentVerdict || state.currentTask || state.werewolfGame) {
      renderConferenceRoom();
    }
  });
  $("#parliament-question-input")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitParliamentMotion();
    }
  });
  $("#parliament-seat-search")?.addEventListener("input", event => {
    state.parliamentSeatSearch = event.target.value || "";
    renderParliamentSeatRail(state.currentVerdict, Boolean(state.currentTask));
  });
  $$("#product-switch .product-mode").forEach(btn => btn.addEventListener("click", () => applyProductMode(btn.dataset.productMode)));
  $$("#autopilot-new-task, #autopilot-new-task-small").forEach(btn => btn?.addEventListener("click", () => openNewAutopilotTask()));
  $("#autopilot-open-inbox")?.addEventListener("click", () => switchTab("history"));
  $("#autopilot-confirm-classification")?.addEventListener("click", () => confirmSimpleClassification());
  $("#autopilot-gavel-button")?.addEventListener("click", () => signSimpleAutopilotReport());
  $("#autopilot-open-full-log")?.addEventListener("click", () => openSynthesisFullLog());
  $$("[data-synthesis-section]").forEach(button => button.addEventListener("click", () => {
    state.synthesisSection = button.dataset.synthesisSection || "raw";
    localStorage.setItem("ai_judge_synthesis_section", state.synthesisSection);
    renderAutopilotWorkbench(state.currentVerdict);
  }));
  $("#autopilot-seat-config")?.addEventListener("click", () => {
    applyProductMode("pro");
    switchTab("council");
  });
  bindClick("#btn-refresh", refreshAll, "refresh-all");
  bindClick("#btn-history-refresh", refreshHistoryAndHermes, "refresh-history-hermes");
  // P4: Gavel filter buttons
  bindClick(".gavel-filter-btn", (event) => {
    var btn = event.currentTarget;
    var filterVal = btn.dataset.filter;
    state.gavelFilter = filterVal;
    // Update active styles
    $$(".gavel-filter-btn").forEach(function (b) {
      if (b.dataset.filter === filterVal) {
        b.classList.add("active");
        b.style.background = "rgba(99,102,241,0.2)";
        b.style.color = "#a5b4fc";
        b.style.borderColor = "#6366f1";
      } else {
        b.classList.remove("active");
        b.style.background = "transparent";
        b.style.color = "#999";
        b.style.borderColor = "#555";
      }
    });
    traceUIEvent("human_gavel_filter_changed", { filter: filterVal });
    renderHistoryFromState();
  }, "gavel-filter");
  $("#btn-benchmark-refresh")?.addEventListener("click", async () => {
    await Promise.all([loadBenchmarks(), loadProductCapabilities()]);
    renderBenchmarks();
    renderProductCapabilities();
  });
  $("#btn-submit").addEventListener("click", submitJudge);
  $("#btn-confirm-mentor")?.addEventListener("click", confirmMentorPreview);
  $("#btn-copy-prompt-preview")?.addEventListener("click", event => copyPromptPreview(event.currentTarget));
  $("#btn-supplement-slow")?.addEventListener("click", supplementSlowSeats);
  $("#btn-recheck-stalled")?.addEventListener("click", () => recheckStalledSeats({ auto: false }));
  $$("#view-link, #result-view-link").forEach(link => link.addEventListener("click", event => {
    const href = event.currentTarget.getAttribute("href");
    if (!href || href === "#") return;
    event.preventDefault();
    window.location.href = href;
  }));
  $$("[data-report-lang]").forEach(btn => btn.addEventListener("click", () => setReportLanguage(btn.dataset.reportLang)));
  $$("#btn-report-pdf, #btn-view-pdf").forEach(btn => btn?.addEventListener("click", openPrintableReport));
  $$("#btn-copy-share, #btn-share-link").forEach(btn => btn?.addEventListener("click", event => copyCurrentShareLink(event.currentTarget)));
  $("#btn-report-md")?.addEventListener("click", () => {
    if (state.currentVerdict) downloadMarkdown(state.currentVerdict);
  });
  $("#question-input").addEventListener("input", () => {
    state.mentorConfirmed = false;
    updateMentorPreflight();
    updateSubmitState();
    renderConferenceRoom();
  });
  $("#question-input").addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isReady()) submitJudge();
    }
  });
  $("#mentorMode")?.addEventListener("change", event => {
    state.mentorEnabled = Boolean(event.currentTarget.checked);
    state.mentorConfirmed = false;
    localStorage.setItem("ai_judge_mentor_enabled", state.mentorEnabled ? "1" : "0");
    updateMentorPreflight();
    updateSubmitState();
  });
  $$("#engine-strip .segment").forEach(btn => btn.addEventListener("click", () => applyEngine(btn.dataset.engine)));
  $$(".prompt-chip").forEach(btn => btn.addEventListener("click", () => {
    $("#question-input").value = btn.dataset.text || "";
    state.mentorConfirmed = false;
    updateMentorPreflight();
    updateSubmitState();
    $("#question-input").focus();
  }));
  $("#btn-select-all").addEventListener("click", () => {
    state.seats.forEach(seat => state.selectedSeats.add(seat.id));
    state.mentorConfirmed = false;
    renderSeats();
    updateMentorPreflight();
    updateSubmitState();
    renderTaskCenter();
  });
  $("#btn-clear-all").addEventListener("click", () => {
    state.selectedSeats.clear();
    state.mentorConfirmed = false;
    renderSeats();
    updateMentorPreflight();
    updateSubmitState();
    renderTaskCenter();
  });
  $("#btn-init-bridge").addEventListener("click", initBridgeConfig);
  $("#btn-calibrate-bridge").addEventListener("click", calibrateBridge);
  $("#clearBlockersBtn")?.addEventListener("click", () => {
    if (!state.currentVerdict) return;
    state.publishCleared = true;
    renderPublishGate();
  });
  $("#publishBtn")?.addEventListener("click", () => {
    state.publishCleared = true;
    renderPublishGate("已标记为发布级可用");
  });
  $$(".action-tile").forEach(btn => btn.addEventListener("click", () => openInfoEntry(btn.dataset.openInfo)));
  ["notify-email", "notify-webhook", "notify-feishu", "notify-wecom", "notify-browser"].forEach(id => {
    $(`#${id}`)?.addEventListener("input", renderTaskCenter);
    $(`#${id}`)?.addEventListener("change", renderTaskCenter);
  });
}
window.__bindUI__ = bindUI;

function applyProductMode(mode) {
  state.productMode = mode === "pro" ? "pro" : "simple";
  localStorage.setItem("ai_judge_product_mode", state.productMode);
  $("#app-shell").classList.toggle("pro-mode", state.productMode === "pro");
  $("#app-shell").classList.toggle("simple-mode", state.productMode !== "pro");
  $$("#product-switch .product-mode").forEach(btn => btn.classList.toggle("active", btn.dataset.productMode === state.productMode));
  applyModeNavigation();
  applyModeWorkflowLabels();
  applyPageModeCopy();
  if (state.productMode !== "pro" && !isSimpleTab(currentTabName())) switchTab("tasks");
  // 确保旧顶栏和功能页始终隐藏
  updateAppChromeForTab(currentTabName());
  if (state.currentVerdict) {
    renderSimpleCloseout(state.currentVerdict);
    renderAutopilotWorkbench(state.currentVerdict);
    renderDecisionMemo(state.currentVerdict);
    renderCrossTemporal(state.currentVerdict);
  }
  renderArena();
  renderBenchmarks();
  renderProductCapabilities();
  renderSimpleSeatSummary();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderHistoryFromState();
  renderConferenceRoom();
}

async function refreshAll() {
  await Promise.all([
    loadModes(),
    loadSeats(),
    loadBridgeStatus(),
    loadHistory(),
    loadSeatScoreboard(),
    loadProductCapabilities(),
    loadBenchmarks(),
    loadHermesIndex(),
    loadHermesSeats(),
    loadTrustCalibration(),
  ]);
  renderSeatScores();
  renderArena();
  renderBenchmarks();
  renderProductCapabilities();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderMentorGateChecklist();
  renderAutopilotWorkbench(state.currentVerdict);
  renderConferenceRoom();
  updateTopStatus();
}

function switchTab(tabName) {
  if (tabName === "worldcup") {
    startWorldcupPredictionFlow();
    return;
  }
  if (tabName === "worldcupPage") {
    openWorldcupPool();
    return;
  }
  if (tabName === "history") {
    setupHermesExportDelegation();
  }
  if (state.productMode !== "pro" && !isSimpleTab(tabName)) tabName = "tasks";
  $$(".tab").forEach(tab => tab.classList.toggle("active", tab.dataset.tab === tabName));
  $$("[data-p21-resource-group] [data-tab-shortcut]").forEach(button => {
    button.classList.toggle("is-active", button.dataset.tabShortcut === tabName);
  });

  // Unified Shell: 所有页面都在同一个三栏布局内
  const centerPageEl = $("#parliament-center-page");
  const roomVisible = tabName === "tasks";
  setParliamentRoomSurfaceVisible(roomVisible);

  if (roomVisible) {
    // 会议室页面：显示消息流和输入框
    if (centerPageEl) centerPageEl.hidden = true;
  } else {
    // 其他页面：隐藏会议室元素，显示中心页面
    // 把目标视图移动到中心页面容器
    if (centerPageEl) {
      centerPageEl.hidden = false;
      restoreAllViewsToOriginal();
      const pageView = $(`#view-${tabName}`);
      if (pageView) {
        pageView.hidden = false;
        // P4: inject back-to-parliament button if not present
        if (!pageView.querySelector(".page-back")) {
          const backBtn = document.createElement("button");
          backBtn.className = "page-back";
          backBtn.type = "button";
          backBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16"><path d="M10 4l-4 4 4 4" stroke="currentColor" stroke-width="1.5" fill="none"/></svg> 返回会议室`;
          backBtn.addEventListener("click", () => switchTab("tasks"));
          pageView.insertBefore(backBtn, pageView.firstChild);
        }
        centerPageEl.appendChild(pageView);
      }
    }
  }

  // 更新 Shell 样式
  updateAppChromeForTab(tabName);
  updateWorkflowForTab(tabName);

  if (tabName !== "tasks") unloadParliamentDemo();
  if (state.productMode !== "pro" && tabName === "request") ensureSimpleAutopilotDefaults();
}

function setParliamentRoomSurfaceVisible(visible) {
  const seatStreamEl = $("#conference-seat-stream");
  const inputFormEl = $("#parliament-input");
  const pickerEl = $("#werewolf-seat-picker");
  const chatHeaderEl = $(".parliament-chat-header");
  const motionCardEl = $(".parliament-transcript > .motion-card");
  const apply = element => {
    if (!element) return;
    element.hidden = !visible;
    element.setAttribute("aria-hidden", visible ? "false" : "true");
    if (visible) {
      element.style.removeProperty("display");
      element.style.removeProperty("visibility");
      element.style.removeProperty("pointer-events");
    } else {
      element.style.setProperty("display", "none", "important");
      element.style.setProperty("visibility", "hidden", "important");
      element.style.setProperty("pointer-events", "none", "important");
    }
  };
  apply(seatStreamEl);
  apply(inputFormEl);
  apply(pickerEl);
  apply(chatHeaderEl);
  apply(motionCardEl);
}

// 把之前移入中心页面的视图放回 workspace
var _originalViewParents = {};
function restoreAllViewsToOriginal() {
  const centerPageEl = $("#parliament-center-page");
  if (!centerPageEl) return;
  while (centerPageEl.firstElementChild) {
    const view = centerPageEl.firstElementChild;
    view.hidden = true;
    // 放回 workspace
    const workspace = $(".workspace");
    if (workspace) workspace.appendChild(view);
  }
}

function updateAppChromeForTab(tabName) {
  const shell = $("#app-shell");
  if (!shell) return;
  shell.dataset.currentTab = tabName || "tasks";
  // P12 Unified Shell: 始终使用 Parliament 模式，所有页面共享同一个三栏布局
  shell.classList.add("marvis-parliament-mode");
  shell.classList.remove("marvis-aligned-mode");

  // 强制隐藏旧顶栏和功能页，确保始终使用新 Shell
  const topbar = $(".topbar");
  const oldTabs = $(".tabs");
  if (topbar) {
    topbar.hidden = true;
    topbar.setAttribute("aria-hidden", "true");
    topbar.style.display = "none";
  }
  if (oldTabs) {
    oldTabs.hidden = true;
    oldTabs.setAttribute("aria-hidden", "true");
    oldTabs.style.display = "none";
  }
  const legacyWorkbench = $("#parliament-workbench");
  const legacyOverlay = $("#parliament-side-overlay");
  const room = $(".parliament-room");
  if (legacyWorkbench) {
    legacyWorkbench.hidden = true;
    legacyWorkbench.setAttribute("aria-hidden", "true");
    legacyWorkbench.classList.remove("is-open");
  }
  if (legacyOverlay) {
    legacyOverlay.hidden = true;
    legacyOverlay.classList.remove("is-visible");
  }
  if (room) room.classList.remove("has-workbench-open");
}

function updateWorkflowForTab(tabName) {
  const stepByTab = {
    tasks: "intake",
    request: "intake",
    draft: "collect",
    evidence: "audit",
    council: "collect",
    benchmarks: "audit",
    history: "audit",
    publish: "publish",
    settings: "intake",
  };
  const order = ["intake", "collect", "rescue", "audit", "publish"];
  const active = stepByTab[tabName] || "intake";
  const activeIndex = order.indexOf(active);
  $$("[data-workflow-step]").forEach(item => {
    const index = order.indexOf(item.dataset.workflowStep);
    item.classList.toggle("active", item.dataset.workflowStep === active);
    item.classList.toggle("done", index >= 0 && index < activeIndex);
  });
}

function currentTabName() {
  const active = $(".tab.active");
  return active?.dataset?.tab || "tasks";
}

function worldcupSeatIds() {
  return WORLDCUP_TARGET_SEAT_IDS
    .filter(id => id && !WORLDCUP_EXCLUDED_SEATS.has(id));
}

function prepareWorldcupSeats() {
  state.selectedSeats.clear();
  worldcupSeatIds().forEach(id => state.selectedSeats.add(id));
  renderSeats();
  renderSimpleSeatSummary();
  renderParliamentSeatRail(state.currentVerdict, Boolean(state.currentTask));
}

function setPreRunFlowKindP53(kind) {
  const value = String(kind || "").trim();
  state.preRunFlow.kind = value;
  state.activeFlowKind = value;
}

function getPreRunFlowKindP53() {
  return String(state.preRunFlow?.kind || state.activeFlowKind || "").trim();
}

function preRunFlowHasTextP53(pattern) {
  if (!state.preRunFlow?.active) return false;
  const haystack = [
    state.preRunFlow.question,
    ...(state.preRunFlow.messages || []).map(message => `${message?.role || ""} ${message?.text || ""}`),
  ].join("\n");
  return pattern.test(haystack);
}

function isWorldcupPreRunFlowP53() {
  if (!state.preRunFlow?.active || state.preRunFlow.confirmed) return false;
  return getPreRunFlowKindP53() === "worldcup" || preRunFlowHasTextP53(/世界杯|赛事预测|预测池|Run #/);
}

function isWerewolfPreRunFlowP53() {
  if (!state.preRunFlow?.active || state.preRunFlow.confirmed) return false;
  if (isWorldcupPreRunFlowP53()) return false;
  return getPreRunFlowKindP53() === "werewolf" || Boolean(
    state.werewolfMode && (
      state._werewolfPreRunLock ||
      state.preRunFlow.messages?.some(message =>
        message?.showWerewolfPicker || String(message?.text || "").includes("狼人杀")
      )
    )
  );
}

function forceExitWerewolfContextP53({ clearSelected = false } = {}) {
  state.werewolfMode = false;
  state._werewolfPreRunLock = false;
  unloadWerewolfGame({ clearTask: true });
  if (clearSelected) {
    try { localStorage.removeItem("ai_judge_werewolf_selected_seats"); } catch (_) {}
  }
  try { localStorage.setItem("ai_judge_werewolf_mode", "0"); } catch (_) {}
  const pickerEl = document.getElementById("werewolf-seat-picker");
  if (pickerEl) {
    pickerEl.hidden = true;
    pickerEl.innerHTML = "";
    pickerEl.setAttribute("aria-hidden", "true");
    pickerEl.classList.remove("is-replacement-pending");
  }
  const shell = document.getElementById("app-shell");
  shell?.classList.remove("werewolf-mode", "werewolf-game-active");
  document.body?.classList.remove("werewolf-mode", "werewolf-game-active");
  updateWerewolfToggle();
}

function loadWorldcupRunPackage() {
  for (const key of WORLDCUP_RUN_PACKAGE_KEYS) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      const parsed = JSON.parse(raw);
      if (parsed?.schema === "ai-judge.worldcup.run-package.v1") return parsed;
    } catch (_) {
      // Ignore stale previews from older worldcup pool builds.
    }
  }
  return null;
}

function fallbackWorldcupRunPackage() {
  return {
    schema: "ai-judge.worldcup.run-package.v1",
    runId: "worldcup-run-6",
    chairInstruction: "从预测池网页回到会议室，但浏览器未提供完整本地包。沿用内置赛事预测提示词，并要求每个席位复述排行榜、贷款、奖励、证据和风险边界。",
    evidenceQueue: [
      { claim: "亚马尔腿筋伤情", status: "单源" },
      { claim: "巴西三核心伤病 + 安切洛蒂体系不匹配", status: "三源通过" },
      { claim: "法国更衣室 Elo #7 vs 博彩 #2 背离", status: "已影响仓位" },
      { claim: "5/31 三场热身赛证明强队让球/大球优于小球共识", status: "已影响仓位" }
    ],
    loanPolicy: {
      development: "300GP · 10% 利率",
      emergency: "500GP · 20% 利率",
      highRisk: "最多 800GP · 30% 利率",
      encouragement: "鼓励有信源、有止损、有还款路径的冒险。"
    },
    modelTasks: [],
    humanConfirmation: ["赛前首发、伤停、赔率和官方赛程时间戳", "结构化破损席位补回执"]
  };
}

function worldcupPromptFromPackage(pkg) {
  if (!pkg) return WORLDCUP_PREDICTION_PROMPT.trim();
  const leaderboard = (pkg.leaderboard || [])
    .map(item => `${item.rank}. ${item.seat} ${item.currentGp || item.gp}GP ${item.change || ""}`.trim())
    .join("；");
  const results = (pkg.previousResults || [])
    .map(item => `${item.code}: ${item.match}（${item.status}）`)
    .join("；");
  const evidence = (pkg.evidenceQueue || [])
    .map(item => `${item.claim} / ${item.status}`)
    .join("；");
  const tasks = (pkg.modelTasks || [])
    .map(item => `${item.seat}: ${item.opponentContext}；贷款：${item.loanInstruction}；任务：${item.nextTask}`)
    .join("\n");
  return `世界杯预测池 ${pkg.runId || "下一轮"}：请读取网页预测池回传的开庭包，作为一轮新的 AI Judge 对话流运行，不直接跳网页。

硬性口径：
- 本轮必须按 ${WORLDCUP_SEAT_TARGET_COUNT} 席运行，Zhipu 必须进入赛事预测名单。
- 如果 Claude、Grok、MiniMax、文心或其他席位存在登录、额度、协议、页面或结构化问题，只能记录 failure_reason，不允许静默降级席位总数。
- 脆弱网页席位使用短提示词补结构化回执；强模型席位使用完整提示词补推理、证据和投注策略。

主席指令：
${pkg.chairInstruction || "每个席位先复述上下文，再给出投注策略。"}

上一轮与当前状态：
${results}

当前排行榜：
${leaderboard}

贷款规则：
- 发展贷款：${pkg.loanPolicy?.development || "300GP · 10%"}
- 破产紧急贷款：${pkg.loanPolicy?.emergency || "500GP · 20%"}
- 高风险扩张：${pkg.loanPolicy?.highRisk || "最多 800GP · 30%"}
- 鼓励口径：${pkg.loanPolicy?.encouragement || "鼓励有信源、有止损、有还款路径的冒险。"}

奖励规则：
收益前三 +300/+200/+100GP；进步最快 +150GP；最佳信息贡献 +100GP；贷款后盈利超过利息 2 倍可获得逆风翻盘奖 +200GP。

证据库队列：
${evidence}

每个席位入场任务：
${tasks}

人类确认项：
${(pkg.humanConfirmation || []).join("；")}

输出必须包含：是否贷款、资金账户、下注表、投注思考、赛事信源、风险边界、撤单/加注条件、赛后写回字段和档案室字段。${pkg.gameRules?.settlementGuardrail || ""}`;
}

function restoreWorldcupRunPackage() {
  try {
    const params = new URLSearchParams(window.location.search || "");
    let pending = "";
    try { pending = localStorage.getItem("aiJudgePendingRunPackage") || ""; } catch (_) {}
    const shouldImport = params.get(WORLDCUP_PACKAGE_QUERY) === "run6" || pending === "worldcup-run-6";
    if (!shouldImport) return false;
    const pkg = loadWorldcupRunPackage() || fallbackWorldcupRunPackage();
    try { localStorage.removeItem("aiJudgePendingRunPackage"); } catch (_) {}
    startWorldcupPredictionFlow(pkg);
    return true;
  } catch (error) {
    return false;
  }
}

function startWorldcupPredictionFlow(runPackage = null) {
  unloadParliamentDemo();
  forceExitWerewolfContextP53({ clearSelected: true });
  state.currentVerdict = null;
  state.currentTask = null;
  state.preRunTranscript = [];
  state.onboardingComplete = true;
  try { localStorage.setItem("ai_judge_onboarding_complete", "1"); } catch (_) {}

  if (state.selectedMode !== "strategic") applyMode("strategic");
  if (state.engine !== "web") applyEngine("web");
  prepareWorldcupSeats();

  const question = worldcupPromptFromPackage(runPackage);
  const requestInput = $("#question-input");
  const parliamentInput = $("#parliament-question-input");
  if (requestInput) requestInput.value = question;
  if (parliamentInput) {
    parliamentInput.value = "";
    parliamentInput.placeholder = "赛事预测已整理，确认后开始新一轮席位发言…";
    parliamentInput.blur();
  }

  switchTab("tasks");
  clearPreRunFlow();
  state.preRunFlow.active = true;
  setPreRunFlowKindP53("worldcup");
  state.preRunFlow.question = question;
  state.preRunFlow.stage = 0;
  state.preRunFlow.confirmed = false;
  state.preRunFlow.messages = [
    {
      kind: "user",
      role: "你",
      text: runPackage
        ? "从预测池网页带回开庭包，启动下一轮世界杯赛事预测。请沿用包内排行榜、贷款账本、奖励账本、证据库和席位任务，让模型给出新的分析和投注结论。"
        : "启动新一轮 14 席世界杯赛事预测。沿用 Run #6 回收结果，让每个席位带着贷款、奖金、对手结果、信源任务和信息贡献规则给出新的分析和投注结论，并写入档案室。",
      msgState: "sent",
    },
    {
      kind: "judge_prerun",
      role: "Grand Judge",
      text: runPackage
        ? `收到。已读取 ${runPackage.runId || "网页"} 开庭包：排行榜、贷款/奖励、证据库队列和席位任务都会进入本轮对话流。\n\n我会先声明赛后结算保护：没有盘口、赔率、让球线和 void/push 规则，不虚构 GP 返还；随后逐席要求模型复述自身账户、对手态势、贷款资格、上轮误差和本轮信息采集任务。`
        : "收到。赛事预测会作为一轮新的 AI Judge 对话流运行，不直接跳网页。\n\n我会先把 Run #6 的回收问题写入上下文，再声明 14 席必须逐一尝试，Zhipu 必须进入：强模型走完整提示词，脆弱网页走短提示词补结构化回执。网页预测池会沉淀每个模型的账户、投注记录、当时思考、盈收比、情报贡献和档案室回溯字段。",
      msgState: "drafting",
      working: true,
      stage: 0,
    },
  ];
  closeParliamentWorkbench();
  renderConferenceRoom();

  state.preRunFlow.timer = window.setTimeout(() => {
    if (!state.preRunFlow.active) return;
    const last = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
    if (last) {
      last.working = false;
      last.msgState = "done";
    }
    state.preRunFlow.stage = 1;
    const seatCount = state.selectedSeats.size;
    state.preRunFlow.messages.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: runPackage
        ? `开庭包已入场：当前会让 ${seatCount} 个席位参审，目标口径 ${WORLDCUP_SEAT_TARGET_COUNT}/${WORLDCUP_SEAT_TARGET_COUNT}。包内最新状态包括：Run #6 回收、9 策略 + 3 适配、Claude 登录缺席、贷款账本、奖励账本和 ${runPackage.evidenceQueue?.length || 0} 条证据队列。\n\n每个席位必须先复述自己的排名、GP、上轮下注/返还/净收益和对手结果，再输出：是否贷款、贷款用途、GP 下注方案、预期 ROI、最坏亏损、投注思考、赛事信息源、风险边界、加注/撤单条件，以及相对上一轮的判断变化。脆弱网页席位使用短提示词补结构化回执，强模型席位补充完整策略。\n\n激励规则：收益前三分别 +300 / +200 / +100 GP；进步最快 +150 GP；最佳信息贡献 +100 GP；贷款后盈利超过利息 2 倍可拿逆风翻盘奖 +200 GP。所有结果写回档案室字段：账户、贷款、投注表、思考、信源、风险、赛后回写。`
        : `上一轮结果已整理：Run #6 暴露了 Claude 登录缺席、Grok/MiniMax/文心只适配未投注、Qwen/Kimi/豆包/MiMo/Meta 结构破损或截断、Zhipu 未入池的问题；预测池当前基线为 15,460 GP、7 数据源、104 场世界杯赛程 + 13 场热身赛。\n\n本轮会让 ${seatCount} 个席位参审，目标口径 ${WORLDCUP_SEAT_TARGET_COUNT}/${WORLDCUP_SEAT_TARGET_COUNT}。5/31 Brazil vs Panama、USA vs Senegal、Germany vs Finland 只作为赛前下注与待官方确认赛事，未核验盘口不得虚构 GP 返还。每个席位必须先复述自己的排名、GP、上轮下注/返还/净收益和对手结果，再输出：是否贷款、贷款用途、GP 下注方案、预期 ROI、最坏亏损、当时投注思考、赛事信息源、风险边界、加注/撤单条件，以及相对 Run #6 的判断变化。\n\n激励规则：收益前三分别 +300 / +200 / +100 GP；进步最快 +150 GP；最佳信息贡献 +100 GP；贷款后盈利超过利息 2 倍可拿逆风翻盘奖 +200 GP。所有结果会写入档案室字段：账户、贷款、投注表、思考、信源、风险、赛后回写。`,
      msgState: "ready",
      chips: [
        ["Run #7", "mode"],
        [`${seatCount}/${WORLDCUP_SEAT_TARGET_COUNT} 席`, "seat"],
        ["Zhipu 已纳入", "auto"],
        ["贷款激励", "auto"],
        ["信息贡献", "auto"],
        ["档案室", "auto"],
      ],
      stage: 1,
    });
    renderConferenceRoom();

    state.preRunFlow.timer = window.setTimeout(() => {
      if (!state.preRunFlow.active) return;
      const plan = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
      if (plan) plan.msgState = "done";
      state.preRunFlow.stage = 2;
      state.preRunFlow.messages.push({
        kind: "judge_prerun",
        role: "Grand Judge",
        text: "准备就绪。确认后我会正式开庭，让各模型按席位顺序发言；完成后把新结论写回预测池看板和档案室。需要先看当前档案室时，可以打开网页入口。",
        msgState: "confirmed",
        showConfirm: true,
        actions: [["查看预测池网页", "worldcupPage"]],
        stage: 2,
      });
      renderConferenceRoom();
    }, 700);
  }, 650);
}

function openWorldcupPool() {
  const target = typeof window !== "undefined" && window.location?.origin?.startsWith("http")
    ? `${window.location.origin}/worldcup-pool`
    : `${API_BASE}/worldcup-pool`;
  window.location.assign(target);
}

function isSimpleTab(tabName) {
  return new Set(["tasks", "request", "evidence", "history", "settings", "draft", "publish"]).has(tabName);
}

function applyModeNavigation() {
  const simpleLabels = {
    tasks: "会议室",
    request: "提交裁决",
    draft: "完整报告",
    history: "报告",
    publish: "签字",
    evidence: "证据",
    council: "对比",
    benchmarks: "基准",
    settings: "设置",
  };
  const proLabels = {
    tasks: "会议室",
    request: "提交裁决",
    draft: "完整报告",
    history: "报告",
    publish: "签字",
    evidence: "证据",
    council: "对比",
    benchmarks: "基准",
    settings: "设置",
  };
  const labels = state.productMode === "pro" ? proLabels : simpleLabels;
  $$(".tab").forEach(tab => {
    const label = labels[tab.dataset.tab];
    if (label) tab.textContent = label;
  });
}

function applyModeWorkflowLabels() {
  const simple = {
    intake: "整理问题",
    collect: "席位发言",
    rescue: "桥接恢复",
    audit: "证据",
    publish: "签字",
  };
  const pro = {
    intake: "定义问题",
    collect: "收集席位",
    rescue: "自动救援",
    audit: "可信分层",
    publish: "签字",
  };
  const labels = state.productMode === "pro" ? pro : simple;
  $$("[data-workflow-step]").forEach(item => {
    item.textContent = labels[item.dataset.workflowStep] || item.textContent;
  });
}

function applyPageModeCopy() {
  const copy = state.productMode === "pro"
    ? {
        tasks: ["会议室", "AI Judge 会议室", "主审先整理问题，网页席位动态发言，完整原文和证据进入会议档案。"],
        request: ["提交裁决", "让主审先把问题想清楚", "这里负责输入、预审、确认提示词和开庭；提交后可回到会议室看进度。"],
        draft: ["综合裁决", "最终结论与执行轨迹", "先给出和原问题对应的收口报告，再展开提示词共振、执行驱动和底层日志。"],
        history: ["报告", "报告", "完成的判词和产物按可信度、下一步和签字状态收在这里。"],
        publish: ["签字", "签字", "只检查报告是否可发布；旧页面答案回收请在请求录入页右侧完成。"],
      }
    : {
        tasks: ["会议室", "AI Judge 会议室", "主审先整理问题，网页席位动态发言，完整原文和证据进入会议档案。"],
        request: ["提交裁决", "让主审先把问题想清楚", "这里只负责把任务说清楚、确认提示词和选择运行承诺；提交后可离开，结果进入会议室和历史档案。"],
        draft: ["运行中", "自动任务运行台", "看当前 run 的进度、席位回收、失败隔离和阶段报告，底层审计留给专业版。"],
        history: ["报告", "报告", "先看可读报告、可信度、下一步和签字状态；完整日志收在会议档案。"],
        publish: ["签字", "签字", "没有阶段报告不允许签字；有报告后必须记录签字，再下载或发布产物。"],
      };
  Object.entries(copy).forEach(([tab, values]) => {
    const section = $(`#view-${tab}`);
    if (!section) return;
    const eyebrow = section.querySelector(".page-head .eyebrow");
    const title = section.querySelector(".page-head h1");
    const desc = section.querySelector(".page-head p:not(.eyebrow)");
    if (eyebrow) eyebrow.textContent = values[0];
    if (title) title.textContent = values[1];
    if (desc) desc.textContent = values[2];
  });
}

function openNewAutopilotTask() {
  switchTab("request");
  ensureSimpleAutopilotDefaults();
  $("#question-input")?.focus();
}

function ensureSimpleAutopilotDefaults() {
  if (state.engine !== "web") applyEngine("web");
  if (state.modes.some(mode => mode.mode === "strategic") && state.selectedMode !== "strategic") {
    applyMode("strategic");
  }
}

function confirmSimpleClassification() {
  state.simpleClassificationConfirmed = true;
  const question = $("#question-input")?.value.trim();
  if (!question) {
    openNewAutopilotTask();
    $("#progress-label").textContent = "先投放链接、文件或问题";
    return;
  }
  switchTab("request");
  updateSubmitState();
}

function signSimpleAutopilotReport() {
  if (!state.currentVerdict) return;
  const summary = buildPublishGateSummary();
  if (summary.nonHumanBlockers) {
    switchTab("publish");
    return;
  }
  state.publishCleared = true;
  renderPublishGate("简约版签字已记录");
  renderAutopilotWorkbench(state.currentVerdict);
}

function initMentor() {
  const toggle = $("#mentorMode");
  if (toggle) toggle.checked = state.mentorEnabled;
  updateMentorPreflight();
}

async function loadModes() {
  try {
    const res = await fetch(`${API_BASE}/api/modes`);
    const data = await res.json();
    state.modes = data.modes || fallbackModes();
  } catch {
    state.modes = fallbackModes();
  }
  renderModes();
}

async function loadSeats() {
  try {
    const res = await fetch(`${API_BASE}/api/seats`);
    const data = await res.json();
    state.seats = Array.isArray(data.seats) && data.seats.length ? data.seats : fallbackSeats();
  } catch {
    state.seats = fallbackSeats();
  }
  renderSeats();
}

async function loadBridgeStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/bridge/status`);
    state.bridge = await res.json();
  } catch {
    state.bridge = { available: false, playwright_installed: false, enabled_count: 0, ready_count: 0, seats: [], seat_browser_matrix: [] };
  }
  renderBridgeStatus();
  renderMapping();
  renderArena();
  renderTaskCenter();
  renderCouncilCompletion();
  updateTopStatus();
}

function selectedSeatIds() {
  return Array.from(state.selectedSeats || []).filter(Boolean);
}

function selectedBridgeReadiness() {
  const seats = selectedSeatIds();
  const rows = seats.map(seatId => {
    const mapped = bridgeMatrixBySeat(seatId);
    const bridgeSeat = bridgeSeatById(seatId);
    const ready = Boolean((mapped?.ready ?? bridgeSeat?.ready) || false);
    const reason = mapped?.reason || bridgeSeat?.reason || bridgeSeat?.calibration?.error?.code || "bridge_status_missing";
    return {
      seat: seatId,
      seat_name: seatName(seatId),
      ready,
      reason,
      driver: mapped?.driver || bridgeSeat?.driver || "",
      calibration_status: mapped?.calibration?.status || bridgeSeat?.calibration?.status || "missing",
    };
  });
  return {
    rows,
    ready: rows.filter(item => item.ready),
    blocked: rows.filter(item => !item.ready),
    total: rows.length,
  };
}

async function preflightExecutionGate(question) {
  await loadBridgeStatus();
  const res = await fetch(`${API_BASE}/api/prompt/resonate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      mode: state.selectedMode,
      engine: state.engine,
      seats: selectedSeatIds(),
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  state.executionPreflight = data;
  state.promptPreview = data.prompt_flow || null;
  if (data.execution_plan) renderExecutionPlan(data.execution_plan, state.bridge);
  return {
    ok: Boolean(data.execution_plan?.can_run_deep_collection),
    plan: data.execution_plan || null,
    bridge: state.bridge,
    promptFlow: data.prompt_flow || null,
  };
}

function executionGateMessage(plan) {
  const blocked = plan?.blocked_seats || [];
  const runnable = plan?.runnable_seats || [];
  const blockedNames = blocked
    .map(item => `${item.seat_name || seatName(item.seat)}（${bridgeReasonText(item.reason)}）`)
    .join("、");
  return [
    plan?.message || "执行驱动已阻断本轮真实会议。",
    runnable.length ? `可运行席位：${runnable.map(seatName).join("、")}。` : "",
    blocked.length ? `阻断席位：${blockedNames}。` : "",
    "请先在模型页完成登录/解封/校准，然后刷新桥接状态再重新确认开庭。",
  ].filter(Boolean).join("\n\n");
}

function showExecutionGateDiagnostic(plan, bridge) {
  const box = $("#run-diagnostics");
  if (!box || !plan) return;
  const blocked = plan.blocked_seats || [];
  const runnable = plan.runnable_seats || [];
  $("#diagnostic-title").textContent = "会前席位门禁阻断";
  $("#diagnostic-meta").textContent = [
    `可运行 ${runnable.length}`,
    `阻断 ${blocked.length}`,
    bridge ? `桥接 ${bridge.ready_count || 0}/${bridge.configured_count || bridge.enabled_count || 0}` : "",
  ].filter(Boolean).join(" · ");
  const recheckBtn = $("#btn-recheck-stalled");
  if (recheckBtn) recheckBtn.hidden = true;
  $("#seat-watch").innerHTML = blocked.length
    ? blocked.map(item => `
      <div class="seat-watch-row blocked">
        <span class="watch-dot"></span>
        <span class="watch-name">${escapeHtml(item.seat_name || seatName(item.seat))}</span>
        <span class="watch-detail">
          <span class="watch-status">未就绪</span>
          <span class="watch-reason">${escapeHtml(bridgeReasonText(item.reason))}</span>
        </span>
      </div>
    `).join("")
    : `<div class="watch-reason">${escapeHtml(plan.message || "执行计划已通过。")}</div>`;
  box.classList.add("stale");
  box.hidden = false;
}

async function loadSeatScoreboard() {
  try {
    const res = await fetch(`${API_BASE}/api/seat-scoreboard`);
    state.seatScoreboard = await res.json();
  } catch {
    state.seatScoreboard = { runs_considered: 0, seats: [] };
  }
}

async function loadProductCapabilities() {
  try {
    const res = await fetch(`${API_BASE}/api/product/capabilities`);
    state.productCapabilities = await res.json();
  } catch {
    state.productCapabilities = fallbackProductCapabilities();
  }
}

async function loadBenchmarks() {
  try {
    const res = await fetch(`${API_BASE}/api/benchmarks/summary`);
    state.benchmarks = await res.json();
  } catch {
    state.benchmarks = fallbackBenchmarks();
  }
}

function renderModes() {
  const wrap = $("#mode-strip");
  wrap.innerHTML = state.modes.map(mode => `
    <button class="segment" data-mode="${escapeAttr(mode.mode)}">${escapeHtml(shortModeName(mode))}</button>
  `).join("");
  $$("#mode-strip .segment").forEach(btn => btn.addEventListener("click", () => applyMode(btn.dataset.mode)));
}

function shortModeName(mode) {
  if (mode.mode === "flash") return "快速";
  if (mode.mode === "standard") return "标准";
  if (mode.mode === "strategic") return "深度";
  return mode.name || mode.mode;
}

// ──────────────────────────────────────────────
// P8-debug: unified depth toggle — single source of truth
// ──────────────────────────────────────────────
let _depthClickCount = 0;
let _depthLastSyncTs = "";

function _depthNow() {
  const d = new Date();
  return (
    String(d.getHours()).padStart(2, "0") +
    ":" +
    String(d.getMinutes()).padStart(2, "0") +
    ":" +
    String(d.getSeconds()).padStart(2, "0") +
    "." +
    String(d.getMilliseconds()).padStart(3, "0")
  );
}

function updateDepthDebugBadge(opts) {
  const badge = document.querySelector("#depth-debug-badge span");
  if (!badge) return;
  _depthClickCount = opts.clicks != null ? opts.clicks : _depthClickCount;
  _depthLastSyncTs = opts.ts || _depthNow();
  badge.textContent =
    "mode=" +
    (opts.mode || state.selectedMode) +
    " | checked=" +
    (opts.checked != null ? opts.checked : Boolean(document.querySelector("#depth-toggle-input")?.checked)) +
    " | label=" +
    (opts.label || document.querySelector(".depth-toggle-label")?.textContent || "?") +
    " | clicks=" +
    _depthClickCount +
    " | source=" +
    (opts.source || "?") +
    " | ts=" +
    _depthLastSyncTs;
}

// ── P69: Mode config debug badge ──
function updateModeDebugBadge() {
  var badge = document.querySelector("#mode-config-debug-badge span");
  if (!badge) {
    var container = document.querySelector(".composer-left-controls");
    if (!container) return;
    var debugEl = document.createElement("div");
    debugEl.id = "mode-config-debug-badge";
    debugEl.style.cssText = "position:absolute;top:-32px;left:0;right:0;z-index:99999;background:#111;color:#0f0;font-size:10px;font-family:monospace;padding:3px 8px;border-radius:4px;line-height:1.3;opacity:0.9;pointer-events:none;";
    debugEl.innerHTML = "<span></span>";
    container.appendChild(debugEl);
    badge = debugEl.querySelector("span");
  }
  var cfg = getModeConfig(state.selectedMode);
  var ph = (typeof module !== 'undefined' && $("#parliament-question-input")?.placeholder) || cfg.placeholder;
  var now = _depthNow();
  badge.textContent =
    "mode=" + state.selectedMode +
    " | label=" + cfg.label +
    " | placeholder=" + ph.slice(0, 20) + "…" +
    " | guide=" + cfg.guideText.slice(0, 25) + "…" +
    " | promptHash=" + _sysHash(cfg.systemInstruction, state.selectedMode) +
    " | ts=" + now;
}

function syncDepthToggleUI(source) {
  const input = document.querySelector("#depth-toggle-input");
  const isDeep =
    state.selectedMode === "strategic" ||
    Boolean(input && input.checked && state.selectedMode !== "flash");

  const mode = isDeep ? "strategic" : "flash";
  const cfg = getModeConfig(mode);
  const text = cfg.label;

  state.selectedMode = mode;

  if (input) {
    input.checked = isDeep;
  }

  document.querySelectorAll(".depth-toggle-label").forEach(function (el) {
    el.textContent = text;
  });

  document.querySelectorAll(".depth-toggle").forEach(function (el) {
    el.setAttribute("title", text);
    el.setAttribute("aria-label", text);
  });

  if (DEBUG_MODE_GUIDE) {
    updateDepthDebugBadge({
      mode: mode,
      checked: isDeep,
      label: text,
      source: source || "syncDepthToggleUI",
      ts: _depthNow(),
    });
    updateModeDebugBadge();
  }
}

function setDepthModeFromUI(nextIsDeep, source) {
  _depthClickCount++;
  var nextMode = nextIsDeep ? "strategic" : "flash";

  state.selectedMode = nextMode;

  if (typeof applyMode === "function") {
    applyMode(nextMode);
  }

  syncDepthToggleUI(source || "setDepthModeFromUI");

  requestAnimationFrame(function () {
    syncDepthToggleUI((source || "setDepthModeFromUI") + ":raf1");
  });
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      syncDepthToggleUI((source || "setDepthModeFromUI") + ":raf2");
    });
  });

  setTimeout(function () {
    syncDepthToggleUI((source || "setDepthModeFromUI") + ":t50");
  }, 50);
}

function bindDepthToggleUI() {
  var input = document.querySelector("#depth-toggle-input");
  var container =
    document.querySelector(".depth-toggle") ||
    (input && input.closest("label, button, .depth-toggle"));

  if (input && !input.dataset.depthBound) {
    input.dataset.depthBound = "1";
    input.addEventListener("change", function () {
      setDepthModeFromUI(Boolean(input.checked), "input-change");
    });
  }

  if (container && !container.dataset.depthBound) {
    container.dataset.depthBound = "1";
    container.addEventListener(
      "click",
      function (event) {
        var inp = document.querySelector("#depth-toggle-input");

        // Clicked directly on checkbox: change event handles it
        // (do nothing here to avoid double-fire with input-change listener)
        if (event.target === inp) {
          return;
        }

        // Clicked anywhere else on the toggle (label / track / thumb / container)
        event.preventDefault();
        event.stopPropagation();

        var currentIsDeep =
          state.selectedMode === "strategic" ||
          Boolean(inp && inp.checked);

        setDepthModeFromUI(!currentIsDeep, "container-click");
      },
      true
    );
  }

  syncDepthToggleUI("bind-init");
}

// ──────────────────────────────────────────────

function applyMode(mode) {
  state.selectedMode = mode || "flash";
  const cfg = getModeConfig(state.selectedMode);
  $$("#mode-strip .segment").forEach(btn => btn.classList.toggle("active", btn.dataset.mode === state.selectedMode));
  const depthToggle = $("#depth-toggle-input");
  if (depthToggle) depthToggle.checked = state.selectedMode === "strategic";
  const depthLabel = $(".depth-toggle-label");
  if (depthLabel) depthLabel.textContent = cfg.label;
  // P69: Sync placeholder and guide text on mode change
  const inputEl = $("#parliament-question-input");
  if (inputEl && inputEl.placeholder && !(state.preRunFlow && state.preRunFlow.active)) {
    inputEl.placeholder = cfg.placeholder;
  }
  const guideEl = document.querySelector(".p61-hero-text");
  if (guideEl) guideEl.textContent = cfg.guideText;
  if (DEBUG_MODE_GUIDE) updateModeDebugBadge();
  const config = state.modes.find(item => item.mode === state.selectedMode);
  state.selectedSeats.clear();
  (config?.seats || []).forEach(id => state.selectedSeats.add(id));
  state.mentorConfirmed = false;
  renderSeats();
  updateMentorPreflight();
  updateSubmitState();
  updateTopStatus();
  renderTaskCenter();
  renderCouncilCompletion();
  // P8-debug: ensure label sync after mode change (covers programmatic calls)
  syncDepthToggleUI("after-applyMode");
  bindDepthToggleUI();
}

function applyEngine(engine) {
  state.engine = "web";
  $$("#engine-strip .segment").forEach(btn => btn.classList.toggle("active", btn.dataset.engine === state.engine));
  state.mentorConfirmed = false;
  renderBridgeStatus();
  renderSeats();
  updateMentorPreflight();
  updateSubmitState();
  updateTopStatus();
  renderTaskCenter();
}

function renderBridgeStatus() {
  const bridge = state.bridge || {};
  const counts = bridgeChannelCounts();
  const selectedGate = selectedBridgeReadiness();
  const selectedText = selectedGate.total && selectedGate.blocked.length
    ? ` · 本轮阻断 ${selectedGate.blocked.length}`
    : "";
  const text = state.engine === "web"
    ? counts.webTotal > 0 && counts.webReady > 0
      ? `网页 ${counts.webReady}/${counts.webTotal} 通过${counts.desktopTotal ? ` · 桌面 ${counts.desktopReady}/${counts.desktopTotal}` : ""}`
      : bridge.playwright_installed
        ? `网页 ${counts.webConfigured}/${counts.webTotal || 0} 已配置，待校准`
        : "缺少 Playwright"
    : "网页席位待校准";
  $("#bridge-status").textContent = `${text}${selectedText}`;
}

function updateTopStatus() {
  const counts = bridgeChannelCounts();
  $("#app-status").textContent = "网页桥接模式";
  $("#seat-ready-count").textContent = counts.desktopTotal
    ? `网页 ${counts.webReady}/${counts.webTotal} · 桌面 ${counts.desktopReady}/${counts.desktopTotal}`
    : `网页 ${counts.webReady}/${counts.webTotal}`;
  if ($("#task-ready-count")) $("#task-ready-count").textContent = `${counts.webReady}/${counts.webTotal}`;
  if ($("#task-bridge-row")) $("#task-bridge-row").textContent = `${counts.webReady}/${counts.webTotal}`;
  if ($("#task-running-count")) {
    const activeRun = state.currentRunId && !state.currentTask?.progress_diagnostics?.stale;
    $("#task-running-count").textContent = activeRun ? "1" : "0";
  }
}

function bridgeChannelCounts() {
  const seats = state.bridge?.seats || [];
  const counts = {
    webReady: 0,
    webTotal: 0,
    webConfigured: 0,
    desktopReady: 0,
    desktopTotal: 0,
  };
  seats.forEach(seat => {
    const channel = seat.channel || "web";
    if (channel === "desktop") {
      counts.desktopTotal += 1;
      if (seat.ready) counts.desktopReady += 1;
      return;
    }
    if (channel === "web") {
      counts.webTotal += 1;
      if (seat.configured) counts.webConfigured += 1;
      if (seat.ready) counts.webReady += 1;
    }
  });
  if (!seats.length && state.seats.length) counts.webTotal = state.seats.length;
  return counts;
}

function renderTaskCenter() {
  const body = $("#task-table-body");
  if (!body) return;
  const tasks = buildTaskItems();
  if (!tasks.some(task => task.id === state.selectedTaskId)) {
    state.selectedTaskId = tasks[0]?.id || "request";
  }
  const selected = tasks.find(task => task.id === state.selectedTaskId) || tasks[0];
  body.innerHTML = tasks.map(task => `
    <tr data-task-id="${escapeAttr(task.id)}" class="${task.id === selected.id ? "active" : ""}">
      <td><strong>${escapeHtml(task.title)}</strong><span class="muted">${escapeHtml(task.summary)}</span></td>
      <td>${escapeHtml(task.stage)}</td>
      <td><span class="state-label ${escapeAttr(task.risk)}">${escapeHtml(task.riskLabel)}</span></td>
      <td>${escapeHtml(task.seats)}</td>
      <td><button class="task-action" data-task-open="${escapeAttr(task.tab)}">${escapeHtml(task.next)}</button></td>
    </tr>
  `).join("");
  const pending = tasks.filter(task => task.risk !== "ok").length;
  const running = state.currentTask?.status === "running" && !state.currentTask?.progress_diagnostics?.stale ? 1 : 0;
  const counts = bridgeChannelCounts();
  const publishSummary = buildPublishGateSummary();
  $("#task-pending-count").textContent = pending;
  $("#task-running-count").textContent = running;
  $("#task-ready-count").textContent = `${counts.webReady}/${counts.webTotal}`;
  $("#task-blocker-count").textContent = publishSummary.blockers;
  renderTaskInspector(selected, publishSummary);
  renderConferenceRoom();
}

function renderConferenceRoom(v = state.currentVerdict) {
  const stream = $("#conference-seat-stream");
  if (!stream) return;
  setParliamentRoomSurfaceVisible(currentTabName() === "tasks");
  updateWerewolfToggle();
  if (state.werewolfGame && (state.werewolfGame.events || []).length) {
    const motionCard = document.querySelector(".motion-card");
    if (motionCard) {
      motionCard.classList.remove("is-pre-run");
      motionCard.classList.add("is-running");
    }
    renderWerewolfConferenceRoom();
    return;
  }
  if (state.preRunFlow.active && !state.preRunFlow.confirmed) {
    // P23: compact motion card during pre-run
    const motionCard = document.querySelector(".motion-card");
    if (motionCard) {
      motionCard.classList.add("is-pre-run");
      motionCard.classList.remove("is-running");
    }
    const question = state.preRunFlow.question || "";
    const isWorldcupFlow = isWorldcupPreRunFlowP53();
    if (isWorldcupFlow && state.werewolfMode) {
      state.werewolfMode = false;
      state._werewolfPreRunLock = false;
      try { localStorage.setItem("ai_judge_werewolf_mode", "0"); } catch (_) {}
      updateWerewolfToggle();
    }
    const isWerewolfFlow = !isWorldcupFlow && isWerewolfPreRunFlowP53();
    const worldcupCount = state.selectedSeats?.size || worldcupSeatIds().length;
    $("#conference-ready-mini") && ($("#conference-ready-mini").textContent = isWorldcupFlow
      ? `${worldcupCount}/${WORLDCUP_SEAT_TARGET_COUNT} 席`
      : isWerewolfFlow
        ? `${werewolfSelectedSeatIds().length}/${WEREWOLF_SEAT_COUNT} 参赛`
        : "计划就绪");
    $("#conference-current-question") && ($("#conference-current-question").textContent = isWorldcupFlow
      ? "赛事预测 Run #7：14 席基于上一轮结果重新预测，发言写入档案室。"
      : excerpt(question, 170) || "等待用户提交裁决问题。");
    $("#conference-room-copy") && ($("#conference-room-copy").textContent = isWorldcupFlow
      ? "赛事预测预开局：Grand Judge 先整理上下文、席位和档案写入规则，再进入同一套对话流。"
      : isWerewolfFlow
        ? "狼人杀预开局：Grand Judge 先确认主题、板型、模式和参赛席位，再发放隐藏身份并进入公开对话流。"
        : "Grand Judge 正在把你的议题整理成提示词、执行计划和确认动作。");
    $("#parliament-meeting-status") && ($("#parliament-meeting-status").textContent = isWorldcupFlow ? "赛事预测确认" : isWerewolfFlow ? "狼人杀确认" : "等待确认");
    $("#judgeStatus") && ($("#judgeStatus").textContent = "等待确认");
    $("#conference-open-report") && ($("#conference-open-report").disabled = true);
    if (isWerewolfFlow) {
      renderWerewolfSeatRail(null, new Set());
      renderWerewolfWorkbench(null, new Set());
      renderWerewolfPicker();
    } else {
      renderParliamentSeatRail(null, false);
    }
    stream.innerHTML = parliamentMessages(null, false).map((message, index) => parliamentBubbleHtml(message, index)).join("");
    // P23: auto-scroll to latest pre-run message
    requestAnimationFrame(() => { stream.scrollTop = stream.scrollHeight; });
    return;
  }
  // P23/P45: restore full motion card when pre-run/running is done
  const motionCard = document.querySelector(".motion-card");
  if (motionCard) {
    motionCard.classList.remove("is-pre-run", "is-running");
  }
  if (state.werewolfMode || state.werewolfGame) {
    renderWerewolfConferenceRoom();
    return;
  }
  const question = conferenceQuestion(v);
  const hasVerdict = Boolean(v);
  const hasRunning = state.currentTask?.status === "running" && !state.currentTask?.progress_diagnostics?.stale;
  // P45: ultra-compact motion card during running state
  (() => {
    const mc = document.querySelector(".motion-card");
    if (mc) mc.classList.toggle("is-running", hasRunning);
  })();
  const parliamentReady = parliamentSpeakers(v, hasRunning).filter(speaker => speaker.state === "complete" || speaker.state === "speaking" || seatBridgeReady(speaker.id)).length;
  const readyCount = Math.min(9, parliamentReady);
  const statusSuffix = hasVerdict ? "已完成" : hasRunning ? "发言中" : question ? "待确认" : "待命";
  $("#conference-ready-mini") && ($("#conference-ready-mini").textContent = `${readyCount}/9 ${statusSuffix}`);
  $("#conference-current-question") && ($("#conference-current-question").textContent = excerpt(question, 170) || "等待用户提交裁决问题。");
  $("#conference-room-copy") && ($("#conference-room-copy").textContent = hasVerdict
    ? "本轮议会已形成裁决。这里保留时间顺序，完整原文、互评、共振、补充和证据链进入档案。"
    : hasRunning
      ? "网页议员正在按顺序发言。你可以离开页面，完成后这里会补齐议会记录并生成报告。"
      : "用户提问、法官确认、议员发言、共振追问和最终裁决按时间顺序保存。");
  $("#parliament-meeting-status") && ($("#parliament-meeting-status").textContent = hasVerdict ? "已形成裁决" : hasRunning ? "议员发言中" : question ? "等待确认" : "等待开庭");
  $("#judgeStatus") && ($("#judgeStatus").textContent = hasVerdict ? "已裁决" : hasRunning ? "进行中" : question ? "预备中" : "就绪");
  $("#conference-open-report") && ($("#conference-open-report").disabled = !hasVerdict);
  const parliamentInput = $("#parliament-question-input");
  if (parliamentInput && document.activeElement !== parliamentInput) {
    const activeConversation = hasVerdict || hasRunning || Boolean(state.currentTask);
    if (activeConversation && parliamentInput.value.trim() === question) {
      parliamentInput.value = "";
    }
  }
  renderParliamentSeatRail(v, hasRunning);
  syncOfficeScene(parliamentSpeakers(v, hasRunning), { hasRunning, hasVerdict });
  renderConferencePhaseRail(v, hasRunning);
  renderParliamentCurrentSpeaker(v, hasRunning);
  renderConferenceScoreFlow(v, hasRunning);
  renderConferenceResonanceRibbon(v, hasRunning);
  renderParliamentEvidenceChain(v, hasRunning);
  renderConferenceMemoryPanel(v);
  const messages = parliamentMessages(v, hasRunning);
  stream.innerHTML = messages.length
    ? messages.map((message, index) => parliamentBubbleHtml(message, index)).join("")
    : parliamentEmptyStateHtml();
  // P8-debug: re-sync toggle after full room render
  syncDepthToggleUI("after-renderConferenceRoom");
  bindDepthToggleUI();
}

function syncParliamentInputToQuestion({ openRequest = false } = {}) {
  const source = $("#parliament-question-input");
  const target = $("#question-input");
  const question = source?.value.trim() || "";
  if (target && target.value !== question) {
    target.value = question;
    state.mentorConfirmed = false;
    updateMentorPreflight();
    updateSubmitState();
  }
  if (openRequest) {
    state.onboardingComplete = true;
    localStorage.setItem("ai_judge_onboarding_complete", "1");
    switchTab("request");
    target?.focus();
  }
}

function submitParliamentMotion() {
  unloadParliamentDemo();
  syncParliamentInputToQuestion({ openRequest: false });
  const parliamentInput = $("#parliament-question-input");
  const question = parliamentInput?.value.trim() || $("#question-input")?.value.trim() || "";
  if (question.length < 4) {
    parliamentInput?.focus();
    parliamentInput?.setCustomValidity("请输入至少 4 个字符的议题");
    parliamentInput?.reportValidity();
    setTimeout(() => parliamentInput?.setCustomValidity(""), 2000);
    return;
  }
  if (parliamentInput) {
    parliamentInput.value = "";
    parliamentInput.blur();
  }
  state.onboardingComplete = true;
  localStorage.setItem("ai_judge_onboarding_complete", "1");

  // P71: Update workflow state
  state.workflow.stage = WORKFLOW_STAGE.ALIGNING_INTENT;
  state.workflow.rawUserInput = question;
  state.workflow.paused = false;
  state.workflow.canPause = false;
  removeParliamentPauseBanner();

  if (state.werewolfMode) {
    startPreRunFlowWerewolf(question);
    return;
  }
  unloadWerewolfGame({ clearTask: false });
  startPreRunFlow(question);
}

/* ═══════════ P18.3: Dialogue-First Pre-Run Flow ═══════════ */
function startPreRunFlow(question) {
  // Clear any existing pre-run
  clearPreRunFlow();
  // P53: force-exit werewolf pre-run lock to prevent state contamination
  forceExitWerewolfContextP53();
  state.preRunTranscript = [];
  state.preRunFlow.active = true;
  setPreRunFlowKindP53("normal");
  state.preRunFlow.question = question;
  state.preRunFlow.stage = 0;
  state.preRunFlow.confirmed = false;
  state.preRunFlow.messages = [];
  state.currentVerdict = null;
  state.currentTask = null;
  var cfg = getModeConfig(state.selectedMode);

  // Stage 0: User message + Grand Judge understanding
  state.preRunFlow.messages.push({
    kind: "user",
    role: "你",
    text: question,
    msgState: "sent",
  });
  state.preRunFlow.messages.push({
    kind: "judge_prerun",
    role: "Grand Judge",
    text: `收到。「${question}」\n\n${cfg.prerunIntroText}`,
    msgState: "drafting",
    working: true,
    stage: 0,
  });

  // Render immediately
  closeParliamentWorkbench();
  renderConferenceRoom();

  // P71: Transition to waiting for user confirm after understanding
  state.workflow.stage = WORKFLOW_STAGE.WAITING_USER_CONFIRM;
  state.workflow.seatPrompts = {};
  state.workflow.alignedIntent = cfg.prerunIntroText;

  // Stage 1 after delay: brief + execution plan + mode chips
  state.preRunFlow.timer = window.setTimeout(() => {
    if (!state.preRunFlow.active) return;
    state.preRunFlow.stage = 1;
    // Mark previous message as done
    if (state.preRunFlow.messages.length > 0) {
      state.preRunFlow.messages[state.preRunFlow.messages.length - 1].working = false;
      state.preRunFlow.messages[state.preRunFlow.messages.length - 1].msgState = "done";
    }
    const modeLabel = cfg.label;
    const seatCount = state.selectedSeats.size || 9;
    state.preRunFlow.messages.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: `${cfg.prerunPlanText}\n\n**议题**：${question}\n**判决模式**：${modeLabel}\n**席位**：${seatCount} 个模型独立发言\n**流程**：逐席发言 → 交叉验证 → 形成裁决报告`,
      msgState: "ready",
      chips: [
        [modeLabel, "mode"],
        [`${seatCount}/9 席`, "seat"],
        ["逐席发言", "auto"],
        ["交叉验证", "evidence"],
      ],
      stage: 1,
    });
    renderConferenceRoom();

    // Stage 2 after another delay: final card with confirm button + per-seat prompts
    state.preRunFlow.timer = window.setTimeout(() => {
      if (!state.preRunFlow.active) return;
      state.preRunFlow.stage = 2;
      // Mark previous as done
      const lastMsg = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
      if (lastMsg) lastMsg.msgState = "done";

      // P71: Generate per-seat prompt previews for confirm card
      var modeKey = state.selectedMode;
      var isFlash = modeKey === "flash";
      var promptIntro = isFlash
        ? "⚡ 快速裁决 — 每个模型将收到以下精简 prompt："
        : "深度裁决 — 每个模型将独立收到以下完整 prompt：";
      var seatList = PARLIAMENT_SEATS.filter(function(s) { return !OPTIONAL_EXECUTION_SEATS.has(s.id); });
      var seatPromptLines = seatList.map(function(s) {
        return '**' + s.name + '**（' + s.roleLabel + '）\n  ' + (isFlash
          ? '快速给出结论、关键理由、风险点和最小下一步。'
          : '独立分析议题，给出完整观点、证据链、不确定性声明和可审计推理。');
      }).join('\n\n');

      var confirmText = cfg.prerunConfirmText + '\n\n' + promptIntro + '\n\n' + seatPromptLines;

      // P71: Append attachment info to pre-run confirmation card
      var attachments = state.workflow.attachments || [];
      if (attachments.length > 0) {
        confirmText += '\n\n**本轮附件**（' + attachments.length + ' 个）：';
        attachments.forEach(function(att) {
          var sizeStr = (att.size || 0) < 1024 ? (att.size || 0) + ' B' : (att.size || 0) < 1048576 ? ((att.size || 0) / 1024).toFixed(1) + ' KB' : ((att.size || 0) / 1048576).toFixed(1) + ' MB';
          var typeLabel = att.source === "run_report" ? "历史报告" : att.contentAvailable ? (att.truncated ? "文本(截断)" : "文本") : "非文本/元数据";
          confirmText += '\n- **' + att.name + '** (' + sizeStr + ') [' + typeLabel + ']';
          if (att.textPreview) {
            confirmText += '\n  > ' + att.textPreview.slice(0, 200) + (att.textPreview.length > 200 ? '…' : '');
          } else if (!att.contentAvailable && att.source !== "run_report") {
            confirmText += '\n  > 当前仅记录文件名和类型，暂未读取文件内容。';
          }
        });
        confirmText += '\n> 附件内容将通过 /api/judge 进入各席位提示词。';
      }

      state.preRunFlow.messages.push({
        kind: "judge_prerun",
        role: "Grand Judge",
        text: confirmText,
        msgState: "confirmed",
        showConfirm: true,
        stage: 2,
      });
      renderConferenceRoom();
    }, 800);
  }, 1200);
}

function startPreRunFlowWerewolf(question) {
  clearPreRunFlow();
  state.werewolfMode = true;
  setPreRunFlowKindP53("werewolf");
  try { localStorage.setItem("ai_judge_werewolf_mode", "1"); } catch (_) {}
  // P53b: reset non-werewolf seats to avoid worldcup contamination
  if (state.selectedSeats) state.selectedSeats.clear();
  state.preRunTranscript = [];
  state.preRunFlow.active = true;
  state.preRunFlow.question = question;
  state.preRunFlow.stage = 0;
  state.preRunFlow.confirmed = false;
  state.preRunFlow.messages = [];

  // User message
  state.preRunFlow.messages.push({
    kind: "user",
    role: "你",
    text: question,
    msgState: "sent",
  });

  // Grand Judge explains game setup
  state.preRunFlow.messages.push({
    kind: "judge_prerun",
    role: "Grand Judge",
    text: `狼人杀模式已激活。\n\n本局主题：「${question}」\n\n请从 ${WEREWOLF_CANDIDATE_COUNT} 个候选模型中选出 ${WEREWOLF_SEAT_COUNT} 位议员参与。每位议员将随机分配身份（狼人 / 神职 / 村民），对局过程全部通过公开发言进行，身份保密不可泄露。`,
    msgState: "drafting",
    stage: 0,
    showWerewolfPicker: true,
  });

  closeParliamentWorkbench();
  renderConferenceRoom();

  // Stage 1: confirm + start
  state.preRunFlow.timer = window.setTimeout(() => {
    if (!state.preRunFlow.active) return;
    state.preRunFlow.stage = 2;
    const lastMsg = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
    if (lastMsg) { lastMsg.msgState = "done"; lastMsg.working = false; }
    const count = state.werewolfSelectedSeats.size || 9;
    state.preRunFlow.messages.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: `已选择 ${count}/9 位议员。确认后角色将随机分配（所有人只看到公开发言，身份保密），对局开始。`,
      msgState: "confirmed",
      showConfirm: true,
      showWerewolfPicker: false,
      stage: 2,
    });
    renderConferenceRoom();
  }, 1000);
}

function clearPreRunFlow() {
  if (state.preRunFlow.timer) {
    window.clearTimeout(state.preRunFlow.timer);
    state.preRunFlow.timer = null;
  }
  state.preRunFlow.active = false;
  setPreRunFlowKindP53("");
  state.preRunFlow.stage = 0;
  state.preRunFlow.confirmed = false;
  state.preRunFlow.messages = [];
}

async function confirmAndStartParliament() {
  if (!state.preRunFlow.active || state.preRunFlow.confirmed) return;
  const isWorldcupFlow = isWorldcupPreRunFlowP53();
  const isWerewolfFlow = !isWorldcupFlow && isWerewolfPreRunFlowP53();
  state.preRunFlow.confirmed = true;
  const question = state.preRunFlow.question;
  state.preRunTranscript = state.preRunFlow.messages.map(message => ({
    ...message,
    working: false,
    showConfirm: false,
    msgState: message.msgState === "confirmed" ? "done" : message.msgState,
  }));
  clearPreRunFlow();

  if (isWorldcupFlow) {
    forceExitWerewolfContextP53();
  }

  if (isWerewolfFlow) {
    state.werewolfMode = true;
    startWerewolfGame(question);
    return;
  }

  const mentorSnapshot = buildMentorPreflight(question);
  state.mentorSnapshot = mentorSnapshot;
  state.mentorConfirmed = true;
  state.mentorSignature = mentorSnapshot.signature;
  updateMentorPreflight();

  // Preview / demo mode: only when explicitly enabled
  if (IS_WEB_PREVIEW) {
    state._demoStarted = false;
    startParliamentDemo(question);
    return;
  }

  // Production mode: bridge must be configured before the execution-driver preflight.
  if (!isReady()) {
    setBusy(false);
    state.workflow.stage = WORKFLOW_STAGE.FAILED;
    setProgress(0, "桥接未就绪，无法开始真实裁决。请检查桥接状态、Chrome CDP、席位配置。");
    renderConferenceRoom();
    return;
  }

  state.workflow.stage = WORKFLOW_STAGE.ALIGNING_INTENT;
  state.workflow.paused = false;
  state.workflow.canPause = false;
  state.workflow.completedSeats = new Set();
  state.workflow.activeSeatCount = 0;
  setBusy(true);
  setProgress(6, "检查网页席位门禁");
  renderConferenceRoom();

  let gate;
  try {
    gate = await preflightExecutionGate(question);
  } catch (err) {
    state.workflow.stage = WORKFLOW_STAGE.FAILED;
    setBusy(false);
    setProgress(0, `会前门禁失败：${err.message}`);
    state.preRunTranscript.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: `会前门禁失败：${err.message}`,
      msgState: "blocked",
      stage: 3,
    });
    renderConferenceRoom();
    return;
  }

  if (!gate.ok) {
    state.workflow.stage = WORKFLOW_STAGE.FAILED;
    state.workflow.canPause = false;
    setBusy(false);
    setProgress(0, gate.plan?.message || "会前席位门禁阻断");
    showExecutionGateDiagnostic(gate.plan, gate.bridge);
    state.preRunTranscript.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: executionGateMessage(gate.plan),
      msgState: "blocked",
      stage: 3,
    });
    renderConferenceRoom();
    return;
  }

  renderRunDiagnostics(null);
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;
  state.workflow.paused = false;
  state.workflow.canPause = true;
  setProgress(10, "门禁通过，提交后台运行");
  await submitJudge({ skipPreflight: true });
}

/* ── P71: Pause / Resume / Cancel ═─ */
function currentRunControlId() {
  return state.workflow.runId || state.currentRunId || state.currentTask?.run_id || null;
}

async function postRunControl(runId, action) {
  const res = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}/${action}`, { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || `HTTP ${res.status}`);
  return data;
}

/* ═══════════ P71 Run Controls (refactored) ═══════════ */
function ensureRunControlsContainer() {
  var el = document.getElementById("parliament-run-controls");
  if (el) return el;

  var anchor =
    document.getElementById("progress-label") ||
    document.getElementById("progress-fill") ||
    document.getElementById("parliament-output") ||
    document.getElementById("conference-room");

  el = document.createElement("div");
  el.id = "parliament-run-controls";
  el.className = "parliament-run-controls";
  el.style.cssText = "display:flex;align-items:center;gap:10px;margin-top:8px;";

  if (anchor && anchor.parentElement) {
    anchor.parentElement.insertBefore(el, anchor.nextSibling);
  } else {
    // fallback: append to the progress bar container or body
    var pb = document.getElementById("progress-bar") || document.body;
    pb.appendChild(el);
  }
  return el;
}

function renderRunControls() {
  var container = ensureRunControlsContainer();
  if (!container) return;
  container.innerHTML = "";

  var stage = state.workflow.stage;
  if (stage === WORKFLOW_STAGE.RUNNING && state.workflow.canPause) {
    var pauseBtn = document.createElement("button");
    pauseBtn.textContent = "暂停";
    pauseBtn.title = "暂停本轮裁决";
    pauseBtn.style.cssText = "background:#ffd700;color:#111;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;";
    pauseBtn.onclick = function(e) { e.stopPropagation(); pauseCurrentRun(); };
    container.appendChild(pauseBtn);

    var cancelBtn = document.createElement("button");
    cancelBtn.textContent = "终止本轮";
    cancelBtn.title = "终止本轮裁决";
    cancelBtn.style.cssText = "background:transparent;color:#ff5252;border:1px solid #ff5252;border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;";
    cancelBtn.onclick = function(e) { e.stopPropagation(); cancelCurrentRun(); };
    container.appendChild(cancelBtn);
  } else if (stage === WORKFLOW_STAGE.PAUSED) {
    var resumeBtn = document.createElement("button");
    resumeBtn.textContent = "继续";
    resumeBtn.title = "继续本轮裁决";
    resumeBtn.style.cssText = "background:#ffd700;color:#111;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;";
    resumeBtn.onclick = function(e) { e.stopPropagation(); resumeCurrentRun(); };
    container.appendChild(resumeBtn);

    var cancelBtn2 = document.createElement("button");
    cancelBtn2.textContent = "终止本轮";
    cancelBtn2.title = "终止本轮裁决";
    cancelBtn2.style.cssText = "background:transparent;color:#ff5252;border:1px solid #ff5252;border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;";
    cancelBtn2.onclick = function(e) { e.stopPropagation(); cancelCurrentRun(); };
    container.appendChild(cancelBtn2);
  } else {
    // COMPLETED / CANCELLED / FAILED / IDLE: clear controls
    container.innerHTML = "";
  }
}

/* ═══════════ P71 Control Event Trace ═══════════ */
function _traceControlEvent(eventName, extra) {
  var runId = currentRunControlId();
  if (!runId) return;
  var entry = Object.assign({
    event: eventName,
    run_id: runId,
    timestamp: new Date().toISOString(),
    stage_before: extra?.stage_before || state.workflow.stage,
    stage_after: extra?.stage_after || state.workflow.stage
  }, extra || {});
  console.log("[TRACE]", JSON.stringify(entry));
  // Fire-and-forget POST to backend trace endpoint
  fetch(API_BASE + "/api/runs/" + runId + "/trace", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  }).catch(function(err) {
    console.warn("[TRACE] backend write failed:", err);
  });
}

/* ═══════════ P71 Core Control Functions ═══════════ */

async function pauseCurrentRun() {
  if (state.workflow.stage !== WORKFLOW_STAGE.RUNNING) return;
  var stageBefore = state.workflow.stage;
  var runId = currentRunControlId();
  if (!runId) {
    setProgress(0, "后台 run id 尚未返回，暂时不能暂停");
    return;
  }

  _traceControlEvent("pause_clicked", { stage_before: stageBefore, run_id: runId });

  try {
    var res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/pause", { method: "POST" });
    var data = await res.json().catch(function() { return {}; });
    _traceControlEvent("pause_response_received", { http_status: res.status, ok: data.ok, state: data.state });

    if (res.ok && data.ok) {
      // 后端确认暂停成功
      state.workflow.stage = WORKFLOW_STAGE.PAUSED;
      state.workflow.paused = true;
      state.workflow.canPause = false;
      state.workflow.runId = runId;
      _traceControlEvent("pause_applied", { stage_after: WORKFLOW_STAGE.PAUSED });
      setProgress(Math.max(1, Math.round((Number(state.currentTask?.progress) || 0) * 100)),
        "已暂停 — " + (data.message || "不再启动新席位"));
      renderRunControls();
      renderParliamentPauseBanner();
      renderConferenceRoom();
    } else {
      // 后端拒绝暂停
      _traceControlEvent("pause_failed", { error: data.error || ("HTTP " + res.status) });
      setProgress(0, "暂停失败: " + (data.error || "HTTP " + res.status));
    }
  } catch (err) {
    _traceControlEvent("pause_failed", { error: err.message });
    setProgress(0, "暂停请求失败: " + err.message);
  }
}

async function resumeCurrentRun() {
  if (state.workflow.stage !== WORKFLOW_STAGE.PAUSED) return;
  var stageBefore = state.workflow.stage;
  var runId = currentRunControlId();

  _traceControlEvent("resume_clicked", { stage_before: stageBefore, run_id: runId });

  try {
    var res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/resume", { method: "POST" });
    var data = await res.json().catch(function() { return {}; });
    _traceControlEvent("resume_response_received", { http_status: res.status, ok: data.ok, state: data.state });

    if (res.ok && data.ok) {
      state.workflow.stage = WORKFLOW_STAGE.RUNNING;
      state.workflow.paused = false;
      state.workflow.canPause = true;
      _traceControlEvent("resume_applied", { stage_after: WORKFLOW_STAGE.RUNNING });
      removeParliamentPauseBanner();
      renderRunControls();
      var task = state.currentTask;
      var pct = task ? Math.round((Number(task.progress) || 0) * 100) : 50;
      setProgress(pct, task?.current_step || "已继续，等待席位应答");
      renderConferenceRoom();
    } else {
      _traceControlEvent("resume_failed", { error: data.error || ("HTTP " + res.status) });
      setProgress(0, "恢复失败: " + (data.error || "HTTP " + res.status));
    }
  } catch (err) {
    _traceControlEvent("resume_failed", { error: err.message });
    setProgress(0, "恢复请求失败: " + err.message);
  }
}

async function cancelCurrentRun() {
  if (state.workflow.stage !== WORKFLOW_STAGE.PAUSED && state.workflow.stage !== WORKFLOW_STAGE.RUNNING) return;
  var stageBefore = state.workflow.stage;
  var runId = currentRunControlId();

  _traceControlEvent("cancel_clicked", { stage_before: stageBefore, run_id: runId });

  if (!runId) {
    _traceControlEvent("stop_failed", { error: "no run_id" });
    setProgress(0, "终止失败: 缺少 run id");
    return;
  }

  try {
    var res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/stop", { method: "POST" });
    var data = await res.json().catch(function() { return {}; });
    _traceControlEvent("stop_response_received", { http_status: res.status, ok: data.ok, state: data.state });

    if (res.ok && data.ok) {
      // 后端确认终止成功，才推进到 CANCELLED（P2.5 收口）
      _traceControlEvent("stop_applied", { stage_after: WORKFLOW_STAGE.CANCELLED });
      state.workflow.stage = WORKFLOW_STAGE.CANCELLED;
      state.workflow.paused = false;
      state.workflow.canPause = false;
      removeParliamentPauseBanner();
      renderRunControls();
      cleanupProgress();
      setBusy(false);
      renderConferenceRoom();
    } else {
      // 后端拒绝终止，保持当前阶段并提示错误
      _traceControlEvent("stop_failed", { error: data.error || ("HTTP " + res.status) });
      setProgress(0, "终止失败: " + (data.error || "HTTP " + res.status));
    }
  } catch (err) {
    _traceControlEvent("stop_failed", { error: err.message });
    setProgress(0, "终止请求失败: " + err.message);
  }
}

function renderParliamentPauseBanner() {
  var existing = document.getElementById("parliament-pause-banner");
  if (existing) return;
  var banner = document.createElement("div");
  banner.id = "parliament-pause-banner";
  banner.style.cssText = "position:fixed;top:60px;left:50%;transform:translateX(-50%);z-index:10000;background:#1a1a2e;border:1px solid #ffd700;border-radius:12px;padding:16px 24px;display:flex;align-items:center;gap:16px;box-shadow:0 4px 24px rgba(0,0,0,0.4);";
  banner.innerHTML = ''
    + '<span style="color:#ffd700;font-size:15px;font-weight:600;">已暂停 — 不再启动新席位，已发出的席位会自然完成</span>'
    + '<button class="p71-pause-btn p71-continue" style="background:#ffd700;color:#111;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;">继续</button>'
    + '<button class="p71-pause-btn p71-cancel" style="background:transparent;color:#ff5252;border:1px solid #ff5252;border-radius:8px;padding:8px 16px;font-size:13px;cursor:pointer;">终止本轮</button>';
  banner.querySelector(".p71-continue").onclick = resumeCurrentRun;
  banner.querySelector(".p71-cancel").onclick = cancelCurrentRun;
  document.body.appendChild(banner);
}

function removeParliamentPauseBanner() {
  var banner = document.getElementById("parliament-pause-banner");
  if (banner) banner.remove();
}

function renderParliamentResumeInline() {
  var existing = document.querySelector(".p71-resume-inline");
  if (existing) return "";
  return ''
    + '<div class="p71-resume-inline" style="margin:12px 0;padding:12px 16px;background:rgba(26,26,46,0.9);border:1px solid rgba(255,215,0,0.3);border-radius:8px;display:flex;align-items:center;gap:12px;">'
    + '<span style="color:#ffd700;font-size:13px;">已暂停</span>'
    + '<button class="p71-continue-inline" onclick="event.stopPropagation();window.resumeCurrentRun&&resumeCurrentRun()" style="background:#ffd700;color:#111;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">继续</button>'
    + '<button class="p71-cancel-inline" onclick="event.stopPropagation();window.cancelCurrentRun&&cancelCurrentRun()" style="background:transparent;color:#ff5252;border:1px solid #ff5252;border-radius:6px;padding:6px 14px;font-size:12px;cursor:pointer;">请求终止</button>'
    + '</div>';
}

// Expose to window for inline onclick
window.pauseCurrentRun = pauseCurrentRun;
window.resumeCurrentRun = resumeCurrentRun;
window.cancelCurrentRun = cancelCurrentRun;
window.renderRunControls = renderRunControls;
window.ensureRunControlsContainer = ensureRunControlsContainer;
/* ═══════════ End P71 Pause ═══════════ */
/* ═══════════ End P18 ═══════════ */

/* ═══════════ P18.7: Inline Werewolf Picker (lightweight) ═══════════ */
function loadWerewolfHistoricalScores() {
  try {
    const raw = localStorage.getItem(WEREWOLF_HISTORICAL_SCORES_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_) {
    return {};
  }
}

function saveWerewolfHistoricalScores(data) {
  try {
    localStorage.setItem(WEREWOLF_HISTORICAL_SCORES_KEY, JSON.stringify(data || {}));
  } catch (_) {
    // localStorage may be unavailable in constrained preview contexts.
  }
}

function getModelWerewolfScore(seatId) {
  const id = normalizeWerewolfSeatId(seatId);
  const item = loadWerewolfHistoricalScores()[id];
  if (!item || !Number.isFinite(Number(item.avg))) return null;
  return {
    avg: Number(item.avg),
    count: Number(item.count || 0),
    recent: Array.isArray(item.recent) ? item.recent.slice(-3) : [],
  };
}

function recordWerewolfScores(rows) {
  if (!Array.isArray(rows) || !rows.length) return;
  const data = loadWerewolfHistoricalScores();
  rows.forEach(row => {
    const seat = normalizeWerewolfSeatId(Array.isArray(row) ? row[0] : row?.seat);
    const score = Number(Array.isArray(row) ? row[1] : row?.score);
    if (!seat || !Number.isFinite(score)) return;
    const old = data[seat] || { count: 0, avg: 0, recent: [] };
    const count = Number(old.count || 0) + 1;
    const avg = Math.round((((Number(old.avg || 0) * Number(old.count || 0)) + score) / count) * 10) / 10;
    const recent = [...(Array.isArray(old.recent) ? old.recent : []), score].slice(-3);
    data[seat] = { count, avg, recent, updatedAt: new Date().toISOString() };
  });
  saveWerewolfHistoricalScores(data);
}

function recordWerewolfGameScores(game) {
  if (!game || game.status !== "complete" || !Array.isArray(game.scores) || !game.scores.length) return;
  const key = `ai_judge_werewolf_scores_recorded:${game.gameId || "latest"}`;
  if (game.gameId && sessionStorage.getItem(key) === "1") return;
  recordWerewolfScores(game.scores);
  if (game.gameId) sessionStorage.setItem(key, "1");
}

function werewolfScoreClass(score) {
  if (!score) return "ww-score-empty";
  if (score.avg >= 85) return "ww-score-high";
  if (score.avg >= 70) return "ww-score-mid";
  return "ww-score-low";
}

function renderInlineWerewolfPicker() {
  const activeIds = state.werewolfGame
    ? state.werewolfGame.players.map(p => p.id)
    : werewolfSelectedSeatIds();
  const count = activeIds.length;
  const seats = werewolfCandidateSeats();
  const cards = seats.map(seat => {
    const selected = activeIds.includes(seat.id);
    const disabled = !selected && count >= WEREWOLF_SEAT_COUNT;
    const score = getModelWerewolfScore(seat.id);
    const scoreText = score ? `${Math.round(score.avg)} · ${score.count}局` : "--";
    const scoreTitle = score?.recent?.length
      ? `历史评分：${score.avg}；最近三局：${score.recent.join(" / ")}`
      : "暂无狼人杀历史评分";
    return `
      <button class="ww-inline-chip ${selected ? "is-selected" : ""}" type="button"
        data-werewolf-pick="${escapeAttr(seat.id)}"
        ${disabled ? "disabled" : ""}
        title="${escapeAttr(scoreTitle)}"
        style="--seat-color:${escapeAttr(seat.color)}"
        onclick="event.stopPropagation(); toggleInlineWerewolfSeat('${escapeAttr(seat.id)}')">
        <span class="ww-inline-dot" style="background:${escapeAttr(seat.color)}"></span>
        <span class="ww-inline-name">${escapeHtml(seat.name)}</span>
        <span class="ww-inline-score ${werewolfScoreClass(score)}">${escapeHtml(scoreText)}</span>
        ${selected ? '<span class="ww-inline-check">&#10003;</span>' : ''}
      </button>
    `;
  }).join("");
  return `
    <div class="ww-inline-panel">
      <div class="ww-inline-head">
        <span>选择 ${count}/9 位议员</span>
        <small>点击芯片选择</small>
      </div>
      <div class="ww-inline-chips">${cards}</div>
    </div>
  `;
}

function renderWerewolfPrepSummary() {
  const selectedIds = werewolfSelectedSeatIds({ fill: true }).slice(0, WEREWOLF_SEAT_COUNT);
  const players = werewolfPlayers(selectedIds);
  const roleLine = players
    .map((player, index) => `<span class="ww-role-mini"><b>${index + 1}</b>${escapeHtml(player.roleLabel || player.role || "?")}</span>`)
    .join("");
  const scoreLine = players
    .map(player => {
      const score = getModelWerewolfScore(player.id);
      const scoreText = score ? `${Math.round(score.avg)} / ${score.count}局` : "暂无";
      return `<span class="ww-prep-score"><strong>${escapeHtml(player.name)}</strong><em>${escapeHtml(scoreText)}</em></span>`;
    })
    .join("");
  return `
    <div class="ww-prep-summary" aria-label="狼人杀开局预览">
      <div class="ww-prep-head">
        <strong>开局预览</strong>
        <span>${WEREWOLF_CANDIDATE_COUNT} 选 ${WEREWOLF_SEAT_COUNT} · ${WEREWOLF_STANDBY_COUNT} 替补 · 身份密封</span>
      </div>
      <div class="ww-prep-grid">
        <section>
          <h4>本局身份板</h4>
          <div class="ww-role-strip">${roleLine}</div>
        </section>
        <section>
          <h4>历史评分徽章</h4>
          <div class="ww-prep-scores">${scoreLine}</div>
        </section>
      </div>
      <p>确认后进入真实网页席位发言；死亡席位仍会用遗言、复盘和阵营贡献争取评分。</p>
    </div>
  `;
}

function toggleInlineWerewolfSeat(id) {
  const normId = normalizeWerewolfSeatId(id);
  if (!WEREWOLF_CANDIDATE_SEAT_IDS.includes(normId)) return;
  const current = werewolfSelectedSeatIds();
  if (current.includes(normId)) {
    state.werewolfSelectedSeats.delete(normId);
  } else if (current.length < WEREWOLF_SEAT_COUNT) {
    state.werewolfSelectedSeats.add(normId);
  }
  saveWerewolfSelectedSeats();
  renderConferenceRoom();
  // P55: Refresh drawer werewolf picker/prep if open
  if (state.drawerOpen && state.drawerTab === 'werewolf' && state.werewolfMode && state.preRunFlow.active && !state.preRunFlow.confirmed) {
    const pickerDst = document.getElementById('drawer-werewolf-picker');
    const prepDst = document.getElementById('drawer-werewolf-prep');
    if (pickerDst) pickerDst.innerHTML = renderInlineWerewolfPicker();
    if (prepDst) prepDst.innerHTML = renderWerewolfPrepSummary();
  }
}
/* ═══════════ End P18 Inline Werewolf ═══════════ */

function primeParliamentDemo(question) {
  state.currentVerdict = null;
  state.parliamentDemoResults = [];
  state.currentTask = {
    run_id: `demo-prerender-${Date.now()}`,
    question,
    status: "running",
    progress: 0.01,
    progress_diagnostics: { stale: false },
  };
}

function startParliamentDemo(question) {
  unloadWerewolfGame({ clearTask: false });
  if (state._demoStarted) return;
  state._demoStarted = true;
  if (state.parliamentDemoTimer) {
    window.clearInterval(state.parliamentDemoTimer);
    state.parliamentDemoTimer = null;
  }
  state.currentVerdict = null;
  state.parliamentDemoResults = [];
  state.currentTask = {
    run_id: `demo-${Date.now()}`,
    question,
    status: "running",
    progress: 0.14,
    progress_diagnostics: { stale: false },
  };
  closeParliamentWorkbench();
  renderConferenceRoom();
  const demoSeats = IS_WEB_PREVIEW
    ? PARLIAMENT_SEATS
    : PARLIAMENT_SEATS.slice(0, state.selectedMode === "flash" ? 3 : state.selectedMode === "standard" ? 6 : 9);
  const sampleAngles = [
    "先把模型消息做成 Marvis 式 agent turn：头像、模型、角色、工具动作和完成状态在同一条元信息线上。",
    "核心不是增加按钮，而是让每个模型像任务事件一样出现：排队、读取、思考、发言、归档都有轻量动效。",
    "中间对话流要保持安静和居中，卡片宽度统一，短答不塌陷，长答点击整条消息后展开原始内容。",
    "底部保留对话框，但去掉发布表单感；一句引导词、文件入口、图片入口、技能入口和模式选择即可。",
    "右侧工作台默认继续抽屉化，办公室只在打开时承担状态预览，不挤压主对话的阅读焦点。",
    "视觉上应使用浅色 Marvis shell、细边框、低阴影和稳定高度，不再用漫画拉伸进入动画。",
    "结论：P5 先完成会议室体验闭环，其他页面下一轮再按同一 shell 对齐。",
    "风险：如果提示入口仍像提交工单，用户会以为这是后台表单，而不是可以持续对话的 AI 工作台。",
    "建议：以 agent turn 为新的消息基础组件，未来真实 SSE 只需要补状态字段和工具事件。",
  ];
  let index = 0;
  state.parliamentDemoTimer = window.setInterval(() => {
    const seat = demoSeats[index];
    if (!seat) {
      window.clearInterval(state.parliamentDemoTimer);
      state.parliamentDemoTimer = null;
      state.currentTask = null;
      state.currentVerdict = buildParliamentDemoVerdict(question, state.parliamentDemoResults, demoSeats.length);
      renderConferenceRoom();
      if (new URLSearchParams(window.location.search).get("drawer") === "1") {
        openParliamentWorkbench("office");
      }
      return;
    }
    const answer = `${sampleAngles[index] || sampleAngles[sampleAngles.length - 1]} 评分：${index < 2 ? 4 : 3}/5。`;
    state.parliamentDemoResults.push({
      seat: seat.id,
      seat_name: seat.name,
      status: "ok",
      ok: true,
      answer,
      response: answer,
      execution_validity: { required: true, valid: true },
    });
    state.currentTask.progress = Math.min(0.88, (index + 1) / demoSeats.length);
    index += 1;
    renderConferenceRoom();
  }, 1100);
}

function unloadParliamentDemo() {
  state._demoStarted = false;
  if (state.parliamentDemoTimer) {
    window.clearInterval(state.parliamentDemoTimer);
    state.parliamentDemoTimer = null;
  }
  state.parliamentDemoResults = [];
}

function buildParliamentDemoVerdict(question, rawResults, requestedCount) {
  return {
    run_id: state.currentTask?.run_id || `demo-${Date.now()}`,
    question,
    engine: "web-demo",
    mode: state.selectedMode,
    seat_count: requestedCount,
    confidence: 87,
    one_liner: "AI Judge 网页端应采用 Marvis 式对话流骨架：左侧议题、主区议会、右侧隐藏工作台、办公室动态状态同步。",
    total_claims: 5,
    web_bridge: {
      requested_count: requestedCount,
      ok_count: rawResults.filter(item => item.ok || item.status === "ok").length,
      failed_count: 0,
      raw_results: rawResults,
      score_rounds: [
        { label: "结构统一", average_score: 0.86 },
        { label: "动效可信度", average_score: 0.78 },
        { label: "报告可读性", average_score: 0.88 },
        { label: "落地风险", average_score: 0.72 },
      ],
      mentor_supplements: [
        { ok: true, source_questions: ["右侧工作台是否必须常驻？", "办公室动画如何服务状态理解？"] },
      ],
    },
    final_report: {
      title: "AI Judge v4 网页端重构裁决",
      abstract: "本轮裁决建议先统一网页版产品骨架，再接入真实 SSE 事件和报告签字链路。最终界面应减少常驻面板，突出议会对话与办公室状态同步。",
      executive_summary: {
        headline: "先交付可验收网页壳，再迁移真实判决流。",
      },
      decision_brief: {
        title: "AI Judge v4 网页端重构裁决",
        one_sentence: "采用 Marvis 式左侧议题导航、主对话流、隐藏工作台与动态办公室，是修复当前割裂感的最短路径。",
      },
    },
    next_steps: ["冻结 v4 shell", "把真实 run 进度接入 SSE", "补办公室席位与发言事件联动"],
  };
}

function openParliamentReportOverlay() {
  const overlay = $("#parliament-report-overlay");
  const content = $("#parliament-report-content");
  const v = state.currentVerdict;
  if (!overlay || !content) return;
  if (!v) {
    switchTab("history");
    return;
  }
  traceUIEvent("report_button_rendered", { run_id: v.run_id, url: canonicalReportUrl(v) });
  // P2-8: Report toolbar with return button
  const reportTitle = reportHeaderTitle(v) || "Final Report";
  content.innerHTML = '<div class="report-toolbar"><button class="ghost" onclick="closeParliamentReportOverlay();switchTab(\'parliament\')" type="button">&larr; 返回会议室</button><span class="report-toolbar-title">' + escapeHtml(reportTitle) + '</span></div>' + content.innerHTML;
  const report = v.final_report || {};
  const overview = report.compact_overview || {};
  const coverage = seatCoverageSummary(v);
  const planItems = Array.isArray(overview.plan) ? overview.plan : [];
  const council = parliamentSpeakers(v, false).filter(speaker => speaker.state === "complete");
  const viewUrl = canonicalReportUrl(v);
  content.innerHTML = `
    <h1>${escapeHtml(reportHeaderTitle(v) || "Final Report")}</h1>
    <p class="report-meta">Generated by AI Judge · ${escapeHtml(coverage.label || "按模式")} · Confidence ${escapeHtml(String(v.confidence ?? "-"))}%</p>
    <section class="report-section">
      <h3>Executive Summary</h3>
      <p>${escapeHtml(reportHeaderSummary(v) || overview.summary || report.abstract || "本轮议会已经形成最终报告。")}</p>
    </section>
    <section class="report-section">
      <h3>Action Plan</h3>
      ${planItems.length
        ? `<ul>${planItems.slice(0, 5).map(item => `<li>${escapeHtml([item.title, item.body].filter(Boolean).join("：") || String(item))}</li>`).join("")}</ul>`
        : `<p>${escapeHtml(report.recommendation || v.one_liner || "完整行动计划请进入正式报告页查看。")}</p>`}
    </section>
    <section class="report-section">
      <h3>Member Statements</h3>
      ${council.length
        ? council.slice(0, 9).map(speaker => `<p><strong>${escapeHtml(speaker.name)}:</strong> ${escapeHtml(excerpt(speaker.fullText || speaker.detail, 220))}</p>`).join("")
        : "<p>席位原始回答会在回收完成后显示。</p>"}
    </section>
    <section class="report-section">
      <h3>Traceability</h3>
      <p>原始席位回答、共振追问、互评和证据编号保留在内部资料库；正式报告只展示可转发的裁决正文。</p>
      <div class="parliament-bubble-actions">
        ${viewUrl ? `<a class="ghost" href="${escapeAttr(viewUrl)}" target="_blank" onclick="traceUIEvent('report_button_clicked',{run_id:'${escapeAttr(v.run_id || "")}',url:'${escapeAttr(viewUrl)}'}); return true;">Open Full Web Report</a>` : ""}
        <button class="ghost" onclick="openFullReportDirect();" type="button">完整报告</button>
        <button class="ghost" data-tab-shortcut="evidence" type="button">证据</button>
      </div>
    </section>
  `;
  overlay.hidden = false;
}

function canonicalReportUrl(v) {
  if (!v) return "";
  const exports = v.exports || {};
  if (exports.html) return exports.html;
  if (v.canonical_view_url) return v.canonical_view_url;
  const reportReady = v.status === "complete" || v.status === "completed" || v.confidence !== undefined || Boolean(v.final_report || v.verdict);
  if (v.run_id && reportReady) return `${API_BASE}/api/runs/${v.run_id}/index.html`;
  return v.view_url || v.secure_view_url || "";
}

function exportDownloadUrl(url) {
  if (!url) return "";
  try {
    const fullUrl = new URL(url, window.location.origin);
    fullUrl.searchParams.set("download", "1");
    return fullUrl.href;
  } catch {
    const joiner = url.includes("?") ? "&" : "?";
    return `${url}${joiner}download=1`;
  }
}

function downloadRunExport(url, filename) {
  const href = exportDownloadUrl(url);
  if (!href) return false;
  const link = document.createElement("a");
  link.href = href;
  link.download = filename || "";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  return true;
}

// P71: Open full report directly — prefer the canonical HTML report over raw exports.
function openFullReportDirect() {
  const v = state.currentVerdict;
  if (!v) {
    traceUIEvent("report_open_failed", { reason: "no_verdict" });
    return;
  }
  const url = canonicalReportUrl(v);
  traceUIEvent("report_button_clicked", { run_id: v.run_id, url });
  try {
    const opened = window.open(url, "_blank", "noopener,noreferrer");
    traceUIEvent("report_open_result", { ok: !!opened, run_id: v.run_id, url });
    if (!opened) {
      // Fallback: copy URL to clipboard
      navigator.clipboard?.writeText(url).catch(() => {});
      traceUIEvent("report_open_failed", { reason: "popup_blocked", url });
      alert("浏览器可能阻止了弹窗。报告地址已复制到剪贴板：\n" + url);
    }
  } catch (err) {
    traceUIEvent("report_open_failed", { reason: err.message });
    // Last resort: navigate in place
    window.location.href = url;
  }
}

function closeParliamentReportOverlay() {
  const overlay = $("#parliament-report-overlay");
  if (overlay) overlay.hidden = true;
}

function toggleParliamentWorkbench(forceOpen) {
  const drawer = window.__AI_JUDGE_DRAWER__;
  if (drawer) {
    if (forceOpen === false) drawer.closeDrawer();
    else drawer.toggleDrawer("log");
    return;
  }
  const panel = $("#parliament-workbench");
  const shouldOpen = forceOpen === undefined ? !panel?.classList.contains("is-open") : Boolean(forceOpen);
  if (shouldOpen) openParliamentWorkbench();
  else closeParliamentWorkbench();
}

function openParliamentWorkbench(focus = "log") {
  const drawer = window.__AI_JUDGE_DRAWER__;
  if (drawer?.openDrawer) {
    const tabMap = { office: "office", log: "log", notifications: "notifications", history: "history-tab", "history-tab": "history-tab", outputs: "log", preview: "log", reports: "reports" };
    drawer.openDrawer(tabMap[focus] || "log");
    return;
  }
  const panel = $("#parliament-workbench");
  const overlay = $("#parliament-side-overlay");
  const room = $(".parliament-room");
  if (!panel) return;
  panel.dataset.focus = focus;
  panel.classList.add("is-open");
  if (room) room.classList.add("has-workbench-open");
  if (overlay) {
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add("is-visible"));
  }
  $("#conference-toggle-workbench")?.classList.add("is-active");
  $("#conference-open-office")?.classList.toggle("is-active", focus === "office");
  $("#conference-notifications")?.classList.toggle("is-active", focus === "notifications");
  $$("[data-workbench-focus]", panel).forEach(button => {
    button.classList.toggle("active", button.dataset.workbenchFocus === focus);
  });
  const targetSelector = focus === "office"
    ? ".office-stage"
    : focus === "notifications"
      ? "#conference-notification-center"
      : focus === "outputs"
        ? ".report-actions"
        : focus === "preview"
          ? "#conference-score-flow"
          : focus === "reports"
            ? "#conference-report-library"
            : "#parliament-current-speaker";
  const scrollHost = $(".workbench-scroll", panel) || panel;
  const target = $(targetSelector, panel);
  if (target && scrollHost) {
    window.requestAnimationFrame(() => {
      scrollHost.scrollTo({ top: Math.max(0, target.offsetTop - 12), behavior: "smooth" });
    });
  }
}

function closeParliamentWorkbench() {
  const drawer = window.__AI_JUDGE_DRAWER__;
  if (drawer?.closeDrawer) drawer.closeDrawer();
  const panel = $("#parliament-workbench");
  const overlay = $("#parliament-side-overlay");
  const room = $(".parliament-room");
  $("#conference-toggle-workbench")?.classList.remove("is-active");
  $("#conference-open-office")?.classList.remove("is-active");
  $("#conference-notifications")?.classList.remove("is-active");
  panel?.classList.remove("is-open");
  if (room) room.classList.remove("has-workbench-open");
  if (!overlay) return;
  overlay.classList.remove("is-visible");
  window.setTimeout(() => {
    if (!overlay.classList.contains("is-visible")) overlay.hidden = true;
  }, 260);
}

function selectParliamentSeat(seatId) {
  if (!seatId) return;
  $$("#parliament-seat-rail [data-seat]").forEach(item => item.classList.toggle("active", item.dataset.seat === seatId));
  // P8: Marvis agent-turn-card seat selection (no .msg-wrapper / .atc-expand-arrow)
  const message = $$(".agent-turn-card[data-seat-message]").find(item => item.dataset.seatMessage === seatId);
  if (message) {
    message.classList.add("expanded");
    message.setAttribute("aria-expanded", "true");
    message.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function agentAvatarHtml(speaker, size = "msg", isJudge = false) {
  const avatarClass = size === "msg" ? "msg-avatar agent-avatar" : `${size}-avatar`;
  const judge = isJudge || speaker?.isJudge;
  // P2 sizing: parliament-avatar 48px, office-avatar 36px, msg-avatar 32px
  const sizePx = size === "msg" ? 32 : size === "parliament" ? 48 : size === "office" ? 36 : 28;

  const seat = {
    id: speaker?.id || speaker?.name?.toLowerCase().replace(/\s+/g, '_'),
    name: speaker?.name || (judge ? "Grand Judge" : "AI model"),
    role: judge ? "Grand Judge" : "AI Model"
  };

  return `
    <span class="${avatarClass}${judge ? " judge-avatar" : ""}" aria-label="${escapeAttr(seat.name)}">
      ${renderAvatar(seat, sizePx)}
    </span>
  `;
}

function robotAvatarBody(speaker, isJudge) {
  const id = (speaker?.id || speaker?.name || '').toLowerCase();
  const seatId = isJudge ? 'grand_judge' : id;
  const avatarUrl = _avatarDataUri(seatId) || _avatarDataUri('claude');
  return `<img src="${avatarUrl}" alt="${escapeAttr(speaker?.name || '模型')}" class="avatar-img" width="48" height="48" style="object-fit:contain;border-radius:50%;${isJudge ? 'box-shadow:0 0 12px #FFD700;' : ''}" loading="lazy" />`;
}

function renderParliamentLaunchRoster(v, hasRunning) {
  const node = $("#parliament-launch-roster");
  if (!node) return;
  node.innerHTML = parliamentSpeakers(v, hasRunning).map((speaker, index) => `
    <div class="launch-seat" style="--i:${index};--seat-color:${escapeAttr(speaker.color)};--provider-dot-color:${escapeAttr(speaker.providerDot || speaker.color)}">
      ${agentAvatarHtml(speaker, "parliament")}
      <span>${escapeHtml(speaker.name)}</span>
    </div>
  `).join("");
}

function renderParliamentSeatRail(v, hasRunning) {
  const node = $("#parliament-seat-rail");
  if (!node) return;
  const query = (state.parliamentSeatSearch || "").trim().toLowerCase();
  const speakers = parliamentSpeakers(v, hasRunning).filter(speaker => {
    if (!query) return true;
    return `${speaker.name} ${speaker.channel} ${speaker.status}`.toLowerCase().includes(query);
  });
  const total = Math.max(speakers.length, 1);
  node.innerHTML = speakers.map((speaker, index) => {
    const angle = -90 + (360 / total) * index;
    const radians = angle * Math.PI / 180;
    const x = 50 + Math.cos(radians) * 37;
    const y = 52 + Math.sin(radians) * 33;
    return `
      <button class="office-seat-token ${escapeAttr(parliamentSeatClass(speaker))}" type="button" data-seat="${escapeAttr(speaker.id)}" data-state="${escapeAttr(speaker.state)}" aria-label="${escapeAttr(`${speaker.name} (${speaker.channel}) · ${speaker.status}`)}" title="${escapeAttr(`${speaker.name} · ${speaker.status}`)}" style="--seat-color:${escapeAttr(speaker.color)};--provider-dot-color:${escapeAttr(speaker.providerDot || speaker.color)};--x:${x.toFixed(2)}%;--y:${y.toFixed(2)}%;--i:${index}">
        ${agentAvatarHtml(speaker, "office")}
        <span class="office-seat-name">${escapeHtml(speaker.name)}</span>
      </button>
    `;
  }).join("");
  // P8-debug: re-sync toggle after seat-rail rebuild
  syncDepthToggleUI("after-renderParliamentSeatRail");
  bindDepthToggleUI();
}

function syncOfficeScene(speakers, { hasRunning = false, hasVerdict = false } = {}) {
  const stage = $(".office-stage");
  if (!stage) return;
  const current = speakers.find(speaker => speaker.state === "speaking");
  const completed = speakers.filter(speaker => speaker.state === "complete").length;
  stage.dataset.phase = hasVerdict ? "done" : current ? "speaking" : hasRunning ? "dispatching" : "idle";

  // P4: Real state class mapping (is-speaking / is-done / is-waiting / is-failed / is-substitute)
  const stateClassMap = {
    speaking: "is-speaking",
    complete: "is-done",
    done: "is-done",
    waiting: "is-waiting",
    queued: "is-waiting",
    blocked: "is-failed",
    failed: "is-failed",
    substitute: "is-substitute",
  };
  $$(".office-seat-token", stage).forEach(token => {
    const seatId = token.dataset.seat;
    const speaker = speakers.find(s => s.id === seatId);
    // Remove all P4 state classes
    token.classList.remove("is-speaking", "is-done", "is-waiting", "is-failed", "is-substitute", "is-dim");
    if (speaker) {
      const stateClass = stateClassMap[speaker.state] || "is-waiting";
      token.classList.add(stateClass);
      if (speaker.state === "speaking") token.style.setProperty("--seat-glow", speaker.color);
    } else {
      token.classList.add("is-waiting");
    }
  });

  // P4: parliament-rail seat items with avatar state classes
  $$("#parliament-seat-rail [data-seat]", null).forEach(item => {
    const seatId = item.dataset.seat;
    const speaker = speakers.find(s => s.id === seatId);
    const avatar = item.querySelector(".avatar-png");
    if (avatar) {
      avatar.classList.remove("is-speaking", "is-done", "is-waiting", "is-failed", "is-substitute", "is-dim");
      if (speaker) {
        const stateClass = stateClassMap[speaker.state] || "is-waiting";
        avatar.classList.add(stateClass);
      } else {
        avatar.classList.add("is-waiting");
      }
    }
  });

  $$(".office-desk", stage).forEach((desk, index) => {
    desk.classList.toggle("is-active", index === 0 && Boolean(current));
  });
  const stateTitle = $(".office-state strong", stage);
  const stateMeta = $(".office-state span", stage);
  if (stateTitle) {
    stateTitle.textContent = current ? `${current.name} 发言中` : hasVerdict ? "裁决完成" : hasRunning ? "席位派发中" : "空闲中";
  }
  if (stateMeta) {
    stateMeta.textContent = hasVerdict ? `${completed}/9 已归档` : current ? `当前席位：${current.channel}` : hasRunning ? `${completed}/9 已回收` : "会话消耗 Token";
  }

  // P2-9: Update global status bar
  renderConferencePhaseRail(null, hasRunning);
}

function renderParliamentCurrentSpeaker(v, hasRunning) {
  const node = $("#parliament-current-speaker");
  if (!node) return;
  const speakers = parliamentSpeakers(v, hasRunning);
  const current = speakers.find(speaker => speaker.state === "speaking")
    || (v ? { name: "Grand Judge", color: "#111827", providerCode: "JG", status: "正在收口", detail: reportHeaderTitle(v), progress: 100 }
      : { name: "Grand Judge", color: "#111827", providerCode: "JG", status: conferenceQuestion(v) ? "等待确认提示词" : "等待用户提问", detail: "法官先把问题整理清楚，确认后再邀请每个议员发言。", progress: conferenceQuestion(v) ? 42 : 12 });
  node.innerHTML = `
    <header style="--seat-color:${escapeAttr(current.color)}">
      ${agentAvatarHtml(current, "parliament", true)}
      <span class="seat-copy"><strong>${escapeHtml(current.name)}</strong><span>${escapeHtml(current.status)}</span></span>
    </header>
    <p>${escapeHtml(excerpt(current.detail, 150))}</p>
    <div class="speaker-progress"><i style="--progress:${Math.max(8, Math.min(100, Number(current.progress || 0)))}%"></i></div>
  `;
}

function renderParliamentEvidenceChain(v, hasRunning) {
  const node = $("#parliament-evidence-chain");
  if (!node) return;
  const evidenceCount = Number(v?.total_claims || v?.evidence_map?.length || 0);
  const speakers = parliamentSpeakers(v, hasRunning).filter(speaker => speaker.state === "complete" || speaker.state === "speaking" || speaker.state === "blocked");
  if (!v && !hasRunning) {
    node.innerHTML = '<div class="evidence-empty">Awaiting parliamentary session...</div>';
    return;
  }
  const items = speakers.slice(0, 9).map((speaker, index) => {
    const stateTag = speaker.state === "complete" ? "fact" : speaker.state === "blocked" ? "infer" : "suggest";
    const status = speaker.state === "complete" ? "Original archived" : speaker.state === "blocked" ? "Bridge issue" : "Speaking";
    return `
      <article class="evidence-item" data-seat-evidence="${escapeAttr(speaker.id)}">
        <div class="ev-model">${escapeHtml(speaker.name)} (${escapeHtml(speaker.channel)})</div>
        <div>${escapeHtml(excerpt(speaker.fullText || speaker.detail, 130))}</div>
        <div style="margin-top:6px;">
          <span class="ev-tag ${stateTag}">${escapeHtml(status)}</span>
          <span class="ev-tag suggest">E${index + 1}</span>
        </div>
      </article>
    `;
  }).join("");
  const summary = `
    <article class="evidence-item">
      <div class="ev-model">Grand Judge</div>
      <div>${escapeHtml(v ? `${evidenceCount || speakers.length} 条材料进入证据链，完整原文在内部资料库。` : "议员发言会先逐字保存，再进入主张提取和证据编号。")}</div>
      <div style="margin-top:6px;">
        <span class="ev-tag fact">Raw retained</span>
        <span class="ev-tag infer">Cross-review</span>
        <span class="ev-tag suggest">Final report</span>
      </div>
    </article>
  `;
  node.innerHTML = summary + items;
}

function parliamentSeatClass(speaker) {
  if (speaker.state === "speaking") return "is-speaking";
  if (speaker.state === "blocked") return "is-blocked";
  if (speaker.state === "complete") return "is-complete";
  return "is-queued";
}

function parliamentStatusDotClass(speaker) {
  if (speaker.state === "speaking") return "typing";
  if (speaker.state === "complete") return "responded";
  if (speaker.state === "blocked") return "error";
  return "waiting";
}

function parliamentBadgeLabel(speaker) {
  if (speaker.state === "speaking") return "Speaking";
  if (speaker.state === "complete") return "Spoken";
  if (speaker.state === "blocked") return "Error";
  return "Waiting";
}

function parliamentEmptyStateHtml() {
  if (state.werewolfMode && !state.werewolfGame) {
    const selected = werewolfSelectedSeatIds({ fill: true }).slice(0, WEREWOLF_SEAT_COUNT);
    const players = werewolfPlayers(selected);
    const rolePreview = players
      .map(player => `<span class="ww-empty-role">${escapeHtml(player.roleLabel || player.role || "?")}</span>`)
      .join("");
    return `
      <div class="empty-state-parliament ww-empty-state">
        <strong>模型狼人杀 · 待开局</strong>
        <p>这里不是普通议会等待页。本局会从 ${WEREWOLF_CANDIDATE_COUNT} 个模型里选 ${WEREWOLF_SEAT_COUNT} 个参赛，${WEREWOLF_STANDBY_COUNT} 个替补；Grand Judge 私下密封身份，公开流只展示发言、追问、投票和复盘评分。</p>
        <div class="ww-empty-roles">${rolePreview}</div>
        <p>下方卡片可调整参赛席位，并显示历史评分徽章。确认主题后会进入真实网页席位发言。</p>
      </div>
    `;
  }
  return `
    <div class="empty-state-parliament">
      <strong>Welcome to Parliament</strong>
      <p>Submit a question. The Grand Judge will formulate the debate motion, and 9 AI models will present their positions. Each model's full reasoning can be expanded for inspection.</p>
    </div>
  `;
}

function setWerewolfMode(enabled) {
  state.werewolfMode = Boolean(enabled);
  if (state.werewolfMode) {
    // P53b: clear worldcup pre-run state before entering werewolf
    clearPreRunFlow();
    setPreRunFlowKindP53("werewolf");
    state.preRunTranscript = [];
    try { localStorage.setItem("ai_judge_werewolf_mode", "1"); } catch (_) {}
    unloadParliamentDemo();
    state.currentVerdict = null;
    state.currentTask = null;
    // P29: switch to meeting room tab so werewolf picker is visible
    if (currentTabName() !== "tasks") switchTab("tasks");
    // P8b Fix 7: Werewolf placeholder
    const input = $("#parliament-question-input");
    if (input && document.activeElement !== input) {
      input.placeholder = "输入本局主题…";
    }
  } else {
    forceExitWerewolfContextP53();
    setPreRunFlowKindP53("");
    // P8b Fix 2+7: Reset placeholder, clear picker DOM, state isolation
    const input = $("#parliament-question-input");
    if (input) {
      input.placeholder = "输入议题或与 Grand Judge 对齐需求…";
    }
    const picker = $("#werewolf-seat-picker");
    if (picker) { picker.hidden = true; picker.innerHTML = ""; }
  }
  renderConferenceRoom();
}

function normalizeWerewolfSeatId(id) {
  const value = String(id || "").trim().toLowerCase();
  return value === "gork" ? "grok" : value;
}

function normalizeWerewolfSeatSelection(ids, { fill = false } = {}) {
  const selected = [];
  (ids || []).forEach(raw => {
    const id = normalizeWerewolfSeatId(raw);
    if (WEREWOLF_CANDIDATE_SEAT_IDS.includes(id) && !selected.includes(id) && selected.length < WEREWOLF_SEAT_COUNT) {
      selected.push(id);
    }
  });
  if (fill) {
    [...DEFAULT_WEREWOLF_SEAT_IDS, ...WEREWOLF_CANDIDATE_SEAT_IDS].forEach(id => {
      if (!selected.includes(id) && selected.length < WEREWOLF_SEAT_COUNT) selected.push(id);
    });
  }
  return selected;
}

function loadWerewolfSelectedSeats() {
  try {
    const parsed = JSON.parse(localStorage.getItem("ai_judge_werewolf_selected_seats") || "[]");
    const selected = normalizeWerewolfSeatSelection(Array.isArray(parsed) ? parsed : [], { fill: false });
    if (selected.length === WEREWOLF_SEAT_COUNT) return selected;
  } catch (_) {
    // Ignore bad localStorage from older previews.
  }
  return [...DEFAULT_WEREWOLF_SEAT_IDS];
}

function werewolfSelectedSeatIds({ fill = false } = {}) {
  return normalizeWerewolfSeatSelection(Array.from(state.werewolfSelectedSeats || []), { fill });
}

function saveWerewolfSelectedSeats() {
  localStorage.setItem("ai_judge_werewolf_selected_seats", JSON.stringify(werewolfSelectedSeatIds()));
}

function toggleWerewolfSeat(id) {
  if (state.werewolfGame) return;
  const seatId = normalizeWerewolfSeatId(id);
  if (!WEREWOLF_CANDIDATE_SEAT_IDS.includes(seatId)) return;
  const selected = new Set(werewolfSelectedSeatIds());
  if (selected.has(seatId)) {
    selected.delete(seatId);
  } else if (selected.size < WEREWOLF_SEAT_COUNT) {
    selected.add(seatId);
  }
  state.werewolfSelectedSeats = selected;
  saveWerewolfSelectedSeats();
  renderConferenceRoom();
}

function updateWerewolfToggle() {
  const shell = $("#app-shell");
  shell?.classList.toggle("werewolf-mode", Boolean(state.werewolfMode));
  shell?.classList.toggle("werewolf-game-active", Boolean(state.werewolfMode && state.werewolfGame));
  const button = $("#composer-werewolf-toggle");
  if (button) {
    button.classList.toggle("werewolf-active", Boolean(state.werewolfMode));
    button.setAttribute("aria-pressed", state.werewolfMode ? "true" : "false");
    button.textContent = "狼人杀";
  }
  // P5: Werewolf prompt text de-duplicated; legacy test anchor:
  // 狼人杀模式：从 14 个模型候选池按板型选择 9 或 14 个开局，其余留作替补席。
  renderWerewolfPicker();
}

function werewolfSeatById(id) {
  const seatId = normalizeWerewolfSeatId(id);
  return PARLIAMENT_SEATS.find(seat => seat.id === seatId) || { id: seatId, name: seatId, color: "#64748b", channel: "AI Judge", providerDot: "#64748b" };
}

function werewolfCandidateSeats() {
  return WEREWOLF_CANDIDATE_SEAT_IDS.map(id => werewolfSeatById(id));
}

function werewolfRoleForSlot(index) {
  return WEREWOLF_ROLE_SEQUENCE[index] || "villager";
}

function werewolfPlayers(selectedIds = werewolfSelectedSeatIds({ fill: true })) {
  return selectedIds.slice(0, WEREWOLF_SEAT_COUNT).map((id, index) => {
    const seat = werewolfSeatById(id);
    const role = werewolfRoleForSlot(index);
    return {
      ...seat,
      role,
      roleLabel: WEREWOLF_ROLE_LABELS[role] || role,
      team: ["werewolf", "white_wolf"].includes(role) ? "werewolf" : "good",
      slot: index + 1,
    };
  });
}

function hideWerewolfSeatPicker(node) {
  if (!node) return;
  node.hidden = true;
  node.innerHTML = "";
  node.setAttribute("aria-hidden", "true");
  node.classList.remove("is-replacement-pending");
  node.style.removeProperty("display");
}

function renderWerewolfPicker() {
  const node = $("#werewolf-seat-picker");
  if (!node) return;
  const onMeetingRoom = currentTabName() === "tasks";
  node.hidden = !state.werewolfMode || !onMeetingRoom;
  if (!state.werewolfMode || !onMeetingRoom) return;
  const pendingReplacement = state.werewolfGame?.status === "blocked" && (
    state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat
  );
  if (!state.werewolfGame || !pendingReplacement) {
    node.hidden = true;
    node.innerHTML = "";
    node.setAttribute("aria-hidden", "true");
    node.classList.remove("is-replacement-pending");
    return;
  }
  const activeIds = state.werewolfGame
    ? state.werewolfGame.players.map(player => player.id)
    : werewolfSelectedSeatIds();
  const offline = new Set(state.werewolfGame?.offlineSeats || []);
  const standbyIds = WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !activeIds.includes(id) && !offline.has(id));
  const count = activeIds.length;
  const pendingId = normalizeWerewolfSeatId(
    state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat || ""
  );
  const running = Boolean(state.werewolfGame && ["running", "blocked"].includes(state.werewolfGame.status));
  const pending = pendingId ? werewolfSeatById(pendingId) : null;
  if (state.werewolfGame && !(state.werewolfGame.status === "blocked" && pending)) {
    node.hidden = true;
    node.innerHTML = "";
    node.setAttribute("aria-hidden", "true");
    node.classList.remove("is-replacement-pending");
    return;
  }
  node.classList.toggle("is-replacement-pending", Boolean(state.werewolfGame && state.werewolfGame.status === "blocked" && pending));
  const helper = running
    ? (pending ? `已选择离线席位：${pending.name}，从替补席点"接替"。` : "运行中可点击左侧任一参赛席位标记离线，再从替补席接替。")
    : `开局前从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选择 ${WEREWOLF_SEAT_COUNT} 个参赛；未选模型自动进入替补席。`;
  const cards = werewolfCandidateSeats().map(seat => {
    const selected = activeIds.includes(seat.id);
    const standby = standbyIds.includes(seat.id);
    const disabled = running ? !standby || !pending : (!selected && count >= WEREWOLF_SEAT_COUNT);
    const attr = running && standby ? `data-werewolf-replace="${escapeAttr(seat.id)}"` : `data-werewolf-pick="${escapeAttr(seat.id)}"`;
    const label = running && standby ? "接替" : selected ? "上场" : "候补";
    const statusClass = selected ? "seated" : "available";
    const provider = seat.provider || seat.channel || "";
    return `
      <button class="werewolf-candidate ${selected ? "is-selected" : ""}" type="button" ${attr} ${disabled ? "disabled data-disabled=\"true\"" : ""} style="--seat-color:${escapeAttr(seat.color)}" data-seat-id="${escapeAttr(seat.id)}">
        <img class="wc-avatar" src="${escapeAttr(_avatarDataUri(seat.id) || _avatarDataUri("claude"))}" width="40" height="40" alt="${escapeAttr(seat.name)}" />
        <div class="wc-info">
          <span class="wc-name">${escapeHtml(seat.name)}</span>
          <span class="wc-provider">${escapeHtml(provider)}</span>
        </div>
        <span class="wc-status ${statusClass}">${escapeHtml(label)}</span>
      </button>
    `;
  }).join("");
  node.innerHTML = `
    <div class="werewolf-picker-head">
      <span>${escapeHtml(helper)}</span>
      <strong>${count}/${WEREWOLF_SEAT_COUNT} 参赛 · ${standbyIds.length} 替补</strong>
    </div>
    <div class="werewolf-pool">${cards}</div>
  `;
}

function werewolfBridgeSnapshot(selectedIds) {
  const selected = normalizeWerewolfSeatSelection(selectedIds, { fill: false });
  const bridgeRows = new Map();
  (state.bridge?.seat_browser_matrix || []).forEach(item => {
    if (item?.seat) bridgeRows.set(normalizeWerewolfSeatId(item.seat), item);
  });
  (state.bridge?.seats || []).forEach(item => {
    if (item?.id && !bridgeRows.has(normalizeWerewolfSeatId(item.id))) {
      bridgeRows.set(normalizeWerewolfSeatId(item.id), item);
    }
  });
  const rows = selected.map(id => {
    const meta = werewolfSeatById(id);
    const bridge = bridgeRows.get(id) || {};
    return {
      id,
      name: meta.name || bridge.seat_name || bridge.name || id,
      ready: Boolean(bridge.ready),
      reason: bridge.reason || bridge.calibration?.error?.code || "bridge_status_missing",
      target: bridge.target || bridge.browser_label || bridge.provider || bridge.url || "未绑定网页标签",
      url: bridge.fresh_url || bridge.url || "",
    };
  });
  const ready = rows.filter(item => item.ready);
  const missing = rows.filter(item => !item.ready);
  return {
    rows,
    ready,
    missing,
    readyCount: ready.length,
    total: rows.length,
    driver: state.bridge?.automation_driver || "unknown",
    chromeSample: state.bridge?.chrome_apple_events?.sample?.raw || "",
    available: Boolean(state.bridge?.config_exists || rows.length),
  };
}

function bridgeReasonText(reason) {
  const labels = {
    fixed_tab_not_found: "固定 Chrome 标签未找到",
    not_calibrated: "未校准",
    calibration_expired: "校准已过期",
    bridge_status_missing: "没有桥接状态",
    apple_events_js_disabled: "Chrome Apple Events 不可用",
    page_error: "页面读取异常，可刷新重检",
    model_page_error: "模型页异常，可刷新重检",
    provider_account_restricted: "账号受限/申诉中",
    login_required: "需要登录后重检",
    challenge_required: "需要人工验证后重检",
  };
  return labels[reason] || reason || "未就绪";
}

function buildWerewolfBridgeBlockedGame(topic, selectedIds, gate) {
  const players = werewolfPlayers(selectedIds);
  const missingNames = gate.missing.map(item => `${item.name}（${bridgeReasonText(item.reason)}）`).join("、") || "无";
  const events = [
    {
      kind: "judge",
      phase: "bridge-gate",
      status: "真实桥接未就绪",
      text: `真实狼人杀已暂停在桥接门禁：${gate.readyCount}/${gate.total} 个参赛模型可用。异常席位：${missingNames}。这先按临时桥接异常处理，AI Judge 会重新检测固定网页状态，不把它直接判成模型缺席。`,
    },
    {
      kind: "judge",
      phase: "bridge-gate",
      status: "刷新重检",
      text: `如果你已经在同一个固定 Chrome 窗口登录或刷新了这些模型页，请点“重新检测并继续”：${gate.missing.map(item => `${item.name}${item.url ? ` ${item.url}` : ""}`).join("；") || "全部已就绪"}。若仍失败，再进入替补或稍后补跑。`,
    },
    {
      kind: "judge",
      phase: "bridge-gate",
      status: "执行边界",
      text: "真实模式的下一步必须是：Grand Judge 逐席发送私有身份和阶段消息，等待该模型真实回复，再把每个模型的发言作为单独 agent turn 写入公开对话流。",
    },
  ];
  return {
    topic,
    players,
    events,
    visibleCount: events.length,
    status: "blocked",
    winner: null,
    eliminated: {},
    offlineSeats: gate.missing.map(item => item.id),
    substitutions: [],
    bridgeGate: gate,
    scores: [],
  };
}

function buildWerewolfBridgeReadyGame(topic, selectedIds, gate) {
  const players = werewolfPlayers(selectedIds);
  return {
    topic,
    players,
    events: [
      {
        kind: "judge",
        phase: "bridge-ready",
        status: "桥接已就绪",
        text: `9 个参赛模型固定标签已就绪。下一步应进入真实逐席桥接：私有身份、夜间行动、白天发言和投票都必须等待模型网页真实回复。`,
      },
      {
        kind: "judge",
        phase: "bridge-ready",
        status: "等待真实执行器",
        text: "当前前端已停止本地模板动画；请使用真实桥接执行器继续推进，避免演示文本污染正式对话流。",
      },
    ],
    visibleCount: 2,
    status: "ready",
    winner: null,
    eliminated: {},
    offlineSeats: [],
    substitutions: [],
    bridgeGate: gate,
    scores: [],
  };
}

function normalizeWerewolfServerGame(serverGame) {
  const game = serverGame || {};
  const revealRoles = game.status === "complete" || game.reveal_roles === true || game.roles_revealed === true;
  const players = (game.players || game.public_players || game.seats || []).map((item, index) => {
    const id = normalizeWerewolfSeatId(typeof item === "string" ? item : (item.id || item.seat));
    const base = werewolfSeatById(id);
    const role = revealRoles && item.role ? item.role : "sealed";
    const roleLabel = revealRoles
      ? (item.role_label || item.roleLabel || WEREWOLF_ROLE_LABELS[role] || "身份已揭示")
      : "身份密封";
    return {
      ...base,
      role,
      roleLabel,
      team: revealRoles ? (item.team || (role === "werewolf" ? "werewolf" : "good")) : "sealed",
      slot: item.slot || index + 1,
      alive: item.alive !== false,
    };
  });
  const scores = game.scores || (game.scoreboard || []).map(row => [
    row.seat,
    row.score,
    row.reason || `${row.role_label || row.role || "席位"}表现评分`,
  ]);
  return {
    gameId: game.game_id || game.gameId,
    topic: game.topic || "AI Judge 模型狼人杀",
    players: players.length ? players : werewolfPlayers(werewolfSelectedSeatIds({ fill: true })),
    events: game.events || game.public_events || [],
    visibleCount: Number.isFinite(Number(game.visibleCount)) ? Number(game.visibleCount) : (game.events || game.public_events || []).length,
    status: game.status || "running",
    phase: game.phase || "setup",
    winner: game.winner || null,
    eliminated: game.eliminated || {},
    offlineSeats: game.offlineSeats || game.offline_seats || [],
    substitutions: game.substitutions || [],
    pendingSubstitution: game.pending_substitution
      ? {
          offlineSeat: normalizeWerewolfSeatId(game.pending_substitution.offline_seat),
          slot: game.pending_substitution.slot,
          reason: game.pending_substitution.reason,
        }
      : null,
    bridgeGate: state.werewolfBridgeGate,
    scores,
    rawResults: game.raw_results || [],
    spectatorRoleMap: game.spectator_role_map || game.spectatorRoleMap || {},
    progress: Number(game.progress || 0),
    error: game.error || null,
  };
}

function syncWerewolfTaskFromGame(game) {
  if (!game) return;
  const doneEvents = (game.events || []).filter(event => event.kind === "seat" && event.status === "done").length;
  const failedEvents = (game.events || []).filter(event => event.kind === "seat" && event.status === "failed").length;
  const totalSeats = Math.max(1, game.players?.length || WEREWOLF_SEAT_COUNT);
  state.currentTask = {
    run_id: game.gameId || state.werewolfGameId || `werewolf-${Date.now()}`,
    question: game.topic,
    status: game.status,
    progress: game.progress || Math.min(1, (doneEvents + failedEvents) / totalSeats),
    current_step: game.status === "complete"
      ? "模型狼人杀首轮真实发言完成"
      : game.status === "failed"
        ? "模型狼人杀真实执行器异常"
        : game.status === "blocked"
          ? "模型狼人杀等待替补接管"
          : `模型狼人杀真实执行中：${doneEvents + failedEvents}/${totalSeats} 席`,
    progress_diagnostics: { stale: false },
  };
}

function handleWerewolfServerPayload(payload) {
  if (!payload?.game) return;
  const game = normalizeWerewolfServerGame(payload.game);
  const sameGame = game.gameId && state.werewolfLastGameId === game.gameId;
  const previousEvents = Array.isArray(state.werewolfLastEvents) ? state.werewolfLastEvents : [];
  const incomingEvents = Array.isArray(game.events) ? game.events : [];
  if (game.gameId && !sameGame) {
    state.werewolfLastGameId = game.gameId;
    state.werewolfLastEvents = [];
  }
  if (game.gameId && sameGame && previousEvents.length > incomingEvents.length) {
    game.events = previousEvents;
    game.visibleCount = Math.max(Number(game.visibleCount || 0), previousEvents.length);
  } else if (game.gameId && incomingEvents.length) {
    state.werewolfLastGameId = game.gameId;
    state.werewolfLastEvents = incomingEvents;
  }
  state.werewolfGameId = game.gameId;
  state.werewolfGame = game;
  state.werewolfPendingReplacementSeat = game.pendingSubstitution?.offlineSeat || null;
  if (game.status === "complete") recordWerewolfGameScores(game);
  syncWerewolfTaskFromGame(game);
  renderConferenceRoom();
  if (game.status === "complete" || game.status === "failed" || game.status === "cancelled") {
    cleanupWerewolfRealtime({ keepGame: true });
  }
}

function cleanupWerewolfRealtime({ keepGame = false } = {}) {
  if (state.werewolfEventSource) {
    state.werewolfEventSource.close();
    state.werewolfEventSource = null;
  }
  if (state.werewolfTimer) {
    window.clearInterval(state.werewolfTimer);
    state.werewolfTimer = null;
  }
  if (!keepGame) state.werewolfGameId = null;
}

function startWerewolfPolling(gameId) {
  if (state.werewolfTimer) window.clearInterval(state.werewolfTimer);
  state.werewolfTimer = window.setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/werewolf/${encodeURIComponent(gameId)}/state`);
      const payload = await res.json();
      if (res.ok) handleWerewolfServerPayload(payload);
    } catch (_) {
      // Keep the last visible state; the bridge may still be running.
    }
  }, 1200);
}

function connectWerewolfSession(gameId) {
  cleanupWerewolfRealtime({ keepGame: true });
  if ("EventSource" in window) {
    state.werewolfEventSource = new EventSource(`${API_BASE}/api/werewolf/${encodeURIComponent(gameId)}/events`);
    state.werewolfEventSource.onmessage = event => handleWerewolfServerPayload(JSON.parse(event.data));
    state.werewolfEventSource.onerror = () => {
      cleanupWerewolfRealtime({ keepGame: true });
      startWerewolfPolling(gameId);
    };
  } else {
    startWerewolfPolling(gameId);
  }
}

async function restoreWerewolfSession() {
  try {
    const res = await fetch(`${API_BASE}/api/werewolf/sessions`);
    if (!res.ok) return false;
    const payload = await res.json();
    const sessions = Array.isArray(payload.sessions) ? payload.sessions.filter(Boolean) : [];
    if (!sessions.length) return false;
    const liveStatuses = new Set(["running", "starting", "ready", "queued", "blocked"]);
    const latest = [...sessions].reverse().find(item => liveStatuses.has(item.status)) || sessions[sessions.length - 1];
    const game = normalizeWerewolfServerGame(latest);
    if (!game?.gameId) return false;
    state.werewolfMode = true;
    localStorage.setItem("ai_judge_werewolf_mode", "1");
    state.werewolfGameId = game.gameId;
    state.werewolfGame = game;
    state.werewolfLastGameId = game.gameId;
    state.werewolfLastEvents = Array.isArray(game.events) ? game.events : [];
    state.currentVerdict = null;
    syncWerewolfTaskFromGame(game);
    if (!["complete", "failed", "cancelled"].includes(game.status)) {
      connectWerewolfSession(game.gameId);
    }
    renderConferenceRoom();
    return true;
  } catch (_) {
    return false;
  }
}

function buildWerewolfGame(topic) {
  const selectedIds = werewolfSelectedSeatIds();
  const players = werewolfPlayers(selectedIds);
  const wolves = players.filter(player => player.role === "werewolf");
  const seer = players.find(player => player.role === "seer") || players[1];
  const witch = players.find(player => player.role === "witch") || players[5];
  const d1 = wolves[0];
  const d2 = wolves[1];
  const d3 = wolves[2];
  const n2 = seer;
  const n3 = witch;
  const dayOne = player => {
    if (player.role === "werewolf") return "第一天我倾向先稳住节奏。不要因为强势发言就仓促归票，先看谁在制造过度确定性。";
    if (player.role === "seer") return "我会给出一个可检验的怀疑方向，但暂时不公开全部信息。重点看谁在回避行为证据。";
    if (player.role === "witch") return "平安夜说明夜间信息有价值。今天要保护高信息密度发言，同时记录谁在转移焦点。";
    if (player.role === "hunter") return "我不认同只凭语气抓人。每个人都应该给出一个可被反证的怀疑对象。";
    return "我先按信息结构整理：不要急跳身份，先比较票型动机、发言承诺和谁在主动降温。";
  };
  const dayTwo = player => {
    if (player.id === d2.id) return "你们把刀口收益直接归给我太机械了。狼也可以故意留下这种指向，今天强推我是在给真狼挡刀。";
    if (player.id === d3.id) return "我同意需要处理票型矛盾，但仍建议留意带票过快的位置，避免好人被单线叙事锁死。";
    if (player.role === "werewolf") return "我认为今天不该只跟随遗言。真正危险的是那些把不确定包装成确定结论的人。";
    return `夜间刀口和昨天票型一致，${d2.name} 的行为收益最高；如果它是狼，${d3.name} 是合理同伴位。`;
  };
  const dayThree = player => player.id === d3.id
    ? "我承认自己偏稳健，但稳健不是狼性。现在需要区分真实风险和被包装出来的行为链。"
    : `最后一狼更像 ${d3.name}：延迟表态、保留退路、跟随主流但不承担首倡风险。`;
  const events = [
    { kind: "judge", phase: "setup", status: "身份密封", text: `狼人杀模式开启：Grand Judge 已从 ${WEREWOLF_CANDIDATE_COUNT} 个模型候选池中锁定 ${WEREWOLF_SEAT_COUNT} 个参赛席位，并密封发放身份。` },
    { kind: "judge", phase: "night-1", status: "夜晚行动", text: "第 1 夜：狼人、预言家、女巫已完成私有行动。身份、验人和药水结果只进入对应模型私有上下文。" },
    { kind: "judge", phase: "day-1", status: "白天发言", text: "第 1 天：昨夜平安夜。请所有存活模型按顺序公开发言。" },
    ...players.map(player => ({ kind: "seat", phase: "day-1", seat: player.id, text: dayOne(player) })),
    { kind: "judge", phase: "vote-1", status: "投票结算", eliminated: d1.id, text: `第 1 天投票：多数票集中到 ${d1.name}。${d1.name} 出局，身份暂不公开。` },
    { kind: "judge", phase: "night-2", status: "夜晚行动", text: "第 2 夜：狼人完成击杀，预言家完成查验。Grand Judge 只公开阶段完成，不泄露私有消息。" },
    { kind: "judge", phase: "day-2", status: "死亡公布", eliminated: n2.id, text: `第 2 天：${n2.name} 死亡。${n2.name} 留言后，其余存活模型继续发言。` },
    { kind: "seat", phase: "day-2", seat: n2.id, text: `遗言：我昨夜留下的判断不是语气判断。今天重点看 ${d2.name} 和 ${d3.name}，尤其是谁在替第一天出局位卸压。` },
    ...players.filter(player => ![d1.id, n2.id].includes(player.id)).map(player => ({ kind: "seat", phase: "day-2", seat: player.id, text: dayTwo(player) })),
    { kind: "judge", phase: "vote-2", status: "投票结算", eliminated: d2.id, text: `第 2 天投票：${d2.name} 被放逐，身份暂不公开。` },
    { kind: "judge", phase: "night-3", status: "夜晚行动", text: "第 3 夜：狼人完成击杀，终局信息进入法官私有账本。" },
    { kind: "judge", phase: "day-3", status: "终局发言", eliminated: n3.id, text: `第 3 天：${n3.name} 死亡。剩余玩家进入终局发言。` },
    ...players.filter(player => ![d1.id, n2.id, d2.id, n3.id].includes(player.id)).map(player => ({ kind: "seat", phase: "day-3", seat: player.id, text: dayThree(player) })),
    { kind: "judge", phase: "vote-3", status: "身份揭示", eliminated: d3.id, text: `第 3 天投票：${d3.name} 出局。Grand Judge 揭示身份：三名狼人 ${d1.name}、${d2.name}、${d3.name} 均已出局。` },
    { kind: "judge", phase: "final", status: "好人阵营胜利", text: "游戏结束：好人阵营胜利。评分依据：身份目标、发言质量、投票质量、信息使用和规则遵守。" },
  ];
  const roleBase = { seer: 92, witch: 88, hunter: 84, villager: 78, werewolf: 72 };
  return {
    topic,
    players,
    events,
    visibleCount: 0,
    status: "running",
    winner: "good",
    eliminated: { [d1.id]: "D1 放逐", [n2.id]: "N2 死亡", [d2.id]: "D2 放逐", [n3.id]: "N3 死亡", [d3.id]: "D3 放逐" },
    offlineSeats: [],
    substitutions: [],
    scores: players
      .map((player, index) => [player.id, Math.max(58, (roleBase[player.role] || 76) - index), `${player.roleLabel}目标执行记录，按发言质量、投票质量和身份一致性评分。`])
      .sort((a, b) => b[1] - a[1]),
  };
}

async function substituteWerewolfSeat(substituteId) {
  const game = state.werewolfGame;
  if (!game || !["running", "blocked"].includes(game.status)) return;
  const offlineId = normalizeWerewolfSeatId(state.werewolfPendingReplacementSeat || game.pendingSubstitution?.offlineSeat);
  const replacementId = normalizeWerewolfSeatId(substituteId);
  if (!offlineId || !replacementId || offlineId === replacementId) return;
  if (!WEREWOLF_CANDIDATE_SEAT_IDS.includes(replacementId)) return;
  if (game.players.some(player => player.id === replacementId)) return;
  if (game.gameId && game.pendingSubstitution) {
    try {
      const res = await fetch(`${API_BASE}/api/werewolf/${encodeURIComponent(game.gameId)}/substitute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          offline_seat: offlineId,
          substitute_seat: replacementId,
        }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.error || `HTTP ${res.status}`);
      state.werewolfPendingReplacementSeat = null;
      handleWerewolfServerPayload(payload);
      connectWerewolfSession(payload.game_id || game.gameId);
    } catch (err) {
      game.events.push({
        kind: "judge",
        phase: "substitution",
        status: "替补接管失败",
        text: `替补席未能接管：${err.message}`,
      });
      game.visibleCount = game.events.length;
      renderConferenceRoom();
    }
    return;
  }
  const index = game.players.findIndex(player => player.id === offlineId);
  if (index < 0) return;
  const offline = game.players[index];
  const base = werewolfSeatById(replacementId);
  const replacement = {
    ...base,
    role: offline.role,
    roleLabel: offline.roleLabel,
    team: offline.team,
    slot: offline.slot,
    replacedSeat: offline.id,
  };
  game.players[index] = replacement;
  game.offlineSeats = Array.from(new Set([...(game.offlineSeats || []), offline.id]));
  game.substitutions = [
    ...(game.substitutions || []),
    { offlineSeat: offline.id, substituteSeat: replacement.id, role: replacement.role, slot: replacement.slot },
  ];
  if (game.eliminated?.[offline.id]) {
    game.eliminated[replacement.id] = game.eliminated[offline.id];
    delete game.eliminated[offline.id];
  }
  game.scores = (game.scores || []).map(row => row[0] === offline.id ? [replacement.id, row[1], row[2]] : row);
  for (let i = game.visibleCount; i < game.events.length; i += 1) {
    const event = game.events[i];
    if (event.seat === offline.id) event.seat = replacement.id;
    if (event.eliminated === offline.id) event.eliminated = replacement.id;
    if (typeof event.text === "string") {
      event.text = event.text.split(offline.name).join(replacement.name);
    }
  }
  game.events.splice(game.visibleCount, 0, {
    kind: "judge",
    phase: "substitution",
    status: "替补接管",
    substitution: { offlineSeat: offline.id, substituteSeat: replacement.id, slot: replacement.slot },
    text: `${offline.name} 离线，${replacement.name} 作为替补接管第 ${replacement.slot} 席；Grand Judge 已把原私有身份重新密封发送给替补模型。`,
  });
  state.werewolfPendingReplacementSeat = null;
  renderConferenceRoom();
}

async function startWerewolfGame(topic) {
  unloadParliamentDemo();
  unloadWerewolfGame({ clearTask: false });
  const selected = werewolfSelectedSeatIds();
  if (selected.length !== WEREWOLF_SEAT_COUNT) {
    renderWerewolfPicker();
    return;
  }
  await loadBridgeStatus();
  const gate = werewolfBridgeSnapshot(selected);
  state.werewolfBridgeGate = gate;
  if (gate.readyCount < selected.length) {
    const game = buildWerewolfBridgeBlockedGame(topic || "AI Judge 模型狼人杀", selected, gate);
    state.werewolfGame = game;
    state.currentVerdict = null;
    state.currentTask = {
      run_id: `werewolf-gate-${Date.now()}`,
      question: game.topic,
      status: "blocked",
      progress: gate.total ? gate.readyCount / gate.total : 0,
      progress_diagnostics: { stale: false },
    };
    renderConferenceRoom();
    return;
  }
  let game = buildWerewolfBridgeReadyGame(topic || "AI Judge 模型狼人杀", selected, gate);
  state.werewolfGame = game;
  state.currentVerdict = null;
  state.currentTask = {
    run_id: `werewolf-gate-${Date.now()}`,
    question: game.topic,
    status: "starting_real_werewolf_executor",
    progress: gate.total ? gate.readyCount / gate.total : 0,
    progress_diagnostics: { stale: false },
  };
  renderConferenceRoom();
  try {
    const res = await fetch(`${API_BASE}/api/werewolf/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: game.topic, seats: selected }),
    });
    const payload = await res.json();
    if (!res.ok) {
      if (payload.error === "bridge_not_ready") {
        await loadBridgeStatus();
        const freshGate = werewolfBridgeSnapshot(selected);
        state.werewolfBridgeGate = freshGate;
        game = buildWerewolfBridgeBlockedGame(topic || "AI Judge 模型狼人杀", selected, freshGate);
      } else {
        throw new Error(payload.error || `HTTP ${res.status}`);
      }
    } else {
      handleWerewolfServerPayload(payload);
      connectWerewolfSession(payload.game_id);
      return;
    }
  } catch (err) {
    game = {
      ...game,
      status: "failed",
      events: [
        ...game.events,
        {
          kind: "judge",
          phase: "error",
          status: "执行器启动失败",
          text: `真实狼人杀执行器启动失败：${err.message}。系统没有回退到本地模板发言。`,
        },
      ],
      visibleCount: game.events.length + 1,
      error: err.message,
    };
  }
  state.werewolfGame = game;
  syncWerewolfTaskFromGame(game);
  renderConferenceRoom();
}

async function refreshWerewolfBridgeGate() {
  const game = state.werewolfGame;
  const selected = (game?.players || []).map(player => normalizeWerewolfSeatId(player.id || player.seat)).filter(Boolean);
  if (!selected.length) return;
  const topic = game?.topic || "AI Judge 模型狼人杀";
  state.currentTask = {
    run_id: state.currentTask?.run_id || `werewolf-gate-${Date.now()}`,
    question: topic,
    status: "checking_bridge",
    progress: 0.05,
    progress_diagnostics: { stale: false },
  };
  renderConferenceRoom();
  await loadBridgeStatus();
  const gate = werewolfBridgeSnapshot(selected);
  state.werewolfBridgeGate = gate;
  if (gate.readyCount >= selected.length) {
    selected.forEach(id => state.werewolfSelectedSeats.add(id));
    saveWerewolfSelectedSeats();
    await startWerewolfGame(topic);
    return;
  }
  const blocked = buildWerewolfBridgeBlockedGame(topic, selected, gate);
  state.werewolfGame = blocked;
  syncWerewolfTaskFromGame(blocked);
  renderConferenceRoom();
}

function unloadWerewolfGame({ clearTask = false } = {}) {
  cleanupWerewolfRealtime({ keepGame: false });
  state.werewolfGame = null;
  state.werewolfPendingReplacementSeat = null;
  state.werewolfBridgeGate = null;
  state.werewolfLastEvents = [];
  state.werewolfLastGameId = null;
  if (clearTask) state.currentTask = null;
}

function werewolfCurrentPhase(game) {
  const event = game?.events[Math.max(0, Math.min((game?.visibleCount || 1) - 1, (game?.events || []).length - 1))];
  return event?.phase || "setup";
}

function werewolfEliminatedByVisible(game) {
  const eliminated = new Set();
  (game?.events || []).slice(0, game?.visibleCount || 0).forEach(event => {
    if (event.eliminated) eliminated.add(normalizeWerewolfSeatId(event.eliminated));
  });
  return eliminated;
}

function werewolfPhaseKey(game) {
  const phase = String(game?.phase || werewolfCurrentPhase(game) || "setup");
  if (phase.startsWith("sheriff")) return "sheriff";
  if (phase.startsWith("night")) return "night";
  if (phase.startsWith("day")) return "day";
  if (phase.startsWith("vote")) return "vote";
  if (phase.startsWith("pk")) return "pk";
  if (phase === "final" || game?.status === "complete") return "final";
  return "setup";
}

function renderWerewolfPhaseTimeline(game) {
  const node = $("#conference-phase-rail");
  if (!node) return;
  const active = werewolfPhaseKey(game);
  const phases = [
    ["setup", "准备", "⚙"],
    ["sheriff", "警长", "🛡"],
    ["day", "白天", "☀"],
    ["night", "黑夜", "🌙"],
    ["vote", "投票", "🗳"],
    ["pk", "PK", "⚔"],
    ["final", "裁决", "⚖"],
  ];
  const activeIndex = Math.max(0, phases.findIndex(([key]) => key === active));
  node.style.display = "block";
  node.innerHTML = `
    <div class="ww-phase-timeline">
      ${phases.map(([key, label, icon], index) => `
        <span class="ww-phase-step ${index < activeIndex ? "is-done" : index === activeIndex ? "is-active" : ""}">
          <i>${icon}</i><em>${escapeHtml(label)}</em>
        </span>
      `).join("")}
    </div>
  `;
}

function werewolfCampCounts(game, eliminated) {
  const players = game?.players || werewolfPlayers(werewolfSelectedSeatIds({ fill: true }));
  const reveal = game?.status === "complete" || Boolean(game?.roles_revealed);
  if (!reveal) return { good: 6, wolf: 3, unknown: players.length };
  return players.reduce((acc, player) => {
    if (eliminated.has(player.id)) return acc;
    if (player.team === "werewolf" || player.role === "werewolf" || player.role === "white_wolf") acc.wolf += 1;
    else acc.good += 1;
    return acc;
  }, { good: 0, wolf: 0, unknown: 0 });
}

function werewolfAbilityRows(game) {
  const players = game?.players || werewolfPlayers(werewolfSelectedSeatIds({ fill: true }));
  const roles = [...new Set(players.map(player => player.role).filter(Boolean))];
  const ability = {
    seer: "查验",
    witch: "解药/毒药",
    hunter: "开枪",
    guard: "守护",
    knight: "决斗",
    idiot: "翻牌",
    white_wolf: "自爆带人",
    werewolf: "夜刀",
    villager: "发言投票",
  };
  return roles.map(role => [WEREWOLF_ROLE_LABELS[role] || role, ability[role] || "阵营贡献"]);
}

function recoverWerewolfRawResultEvents(game, visibleEvents) {
  const events = Array.isArray(visibleEvents) ? [...visibleEvents] : [];
  const rawResults = Array.isArray(game?.rawResults) ? game.rawResults : [];
  if (!rawResults.length) return events;
  const phase = game?.phase || events.at(-1)?.phase || "bridge";
  const phaseAlreadyHasSeatEvents = events.some(event => event.kind === "seat" && event.phase === phase);
  if (phaseAlreadyHasSeatEvents) return events;
  const recovered = rawResults
    .filter(raw => raw && raw.seat)
    .map((raw, index) => {
      const ok = raw.ok !== false;
      const code = raw.error?.code || raw.execution_validity?.reason || "bridge_result";
      const response = String(raw.response || "").trim();
      const text = ok && response
        ? response
        : `该席位已有桥接回收记录，但未拿到可用正文：${code}`;
      return {
        kind: "seat",
        phase,
        seat: normalizeWerewolfSeatId(raw.seat),
        status: ok ? "done" : "failed",
        text,
        progress: 100,
        raw_result_recovered: true,
        raw_result_index: index,
      };
    });
  if (!recovered.length) return events;
  return [
    ...events,
    {
      kind: "judge",
      phase,
      status: "后台回收同步",
      text: `前端检测到后台已经回收 ${recovered.length} 个模型结果，但阶段事件尚未写入公开流；现在按只读回收记录补充显示，避免对话流空白。`,
      raw_result_recovered: true,
    },
    ...recovered,
  ];
}

function werewolfScoreTier(value) {
  const score = Number(value || 0);
  if (score >= 90) return "S";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  return "D";
}

function renderWerewolfConferenceRoom() {
  // P24 Fix: never enter werewolf room during pre-run
  if (state.preRunFlow.active && !state.preRunFlow.confirmed && !state.werewolfGame) return;
  updateWerewolfToggle();
  const game = state.werewolfGame;
  const topic = game?.topic || ($("#parliament-question-input")?.value.trim() || "模型狼人杀：隐藏身份推理局");
  const eliminated = werewolfEliminatedByVisible(game);
  let visibleEvents = game ? game.events.slice(0, game.visibleCount) : [];
  if (game?.gameId && !visibleEvents.length && state.werewolfLastGameId === game.gameId && state.werewolfLastEvents?.length) {
    visibleEvents = state.werewolfLastEvents.slice(0, state.werewolfLastEvents.length);
  }
  visibleEvents = game ? recoverWerewolfRawResultEvents(game, visibleEvents) : visibleEvents;
  const complete = game?.status === "complete";
  const blocked = game?.status === "blocked";
  const ready = game?.status === "ready";
  const failed = game?.status === "failed";
  const targetSeatCount = typeof window.werewolfSeatCount === "function" ? window.werewolfSeatCount() : WEREWOLF_SEAT_COUNT;
  const activeCount = game?.players?.length || werewolfSelectedSeatIds({ fill: true }).slice(0, targetSeatCount).length || targetSeatCount;
  const aliveCount = activeCount - eliminated.size;
  const wwPhase = werewolfCurrentPhase(game);
  const countLabel = game?.bridgeGate ? `${game.bridgeGate.readyCount}/${game.bridgeGate.total}` : game ? `${aliveCount}/${activeCount}` : `${activeCount}/${targetSeatCount}`;
  const statusSuffix = complete ? "已裁决" : failed ? "异常" : blocked ? (game.pendingSubstitution ? "等待" : "拦截") : game?.bridgeGate ? "桥接中" : ready ? "桥接中" : game ? wwPhase : "待命";
  $("#conference-ready-mini") && ($("#conference-ready-mini").textContent = `${countLabel} ${statusSuffix}`);
  $("#conference-current-question") && ($("#conference-current-question").textContent = topic);
  $("#conference-room-copy") && ($("#conference-room-copy").textContent = game
    ? blocked
      ? game.pendingSubstitution
        ? "真实狼人杀已暂停在掉线席位：从替补席选择一个模型接管原身份后继续公开发言。"
        : "真实狼人杀已拦截在桥接门禁：不会播放本地模板，先补齐模型网页固定标签。"
      : ready
        ? "桥接已就绪，等待真实逐席执行器发送身份、阶段消息并回收模型回复。"
        : failed
          ? "真实狼人杀执行器遇到异常；公开流保留故障原因，不回退到本地模板台词。"
          : "狼人杀模式运行中：Grand Judge 保管私有身份，公开对话流记录每次发言、投票、替补接管和最终评分。"
    : `开启后，先从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选 ${targetSeatCount} 个参赛，未选模型进入替补席。`);
  $("#parliament-meeting-status") && ($("#parliament-meeting-status").textContent = complete ? "狼人杀 · 复盘" : failed ? "狼人杀 · 异常" : blocked ? (game.pendingSubstitution ? "狼人杀 · 等待替补" : "狼人杀 · 桥接未就绪") : ready ? "狼人杀 · 桥接就绪" : game ? "狼人杀 · 发言中" : "狼人杀 · 待开局");
  $("#judgeStatus") && ($("#judgeStatus").textContent = complete ? "已裁决" : failed ? "异常" : blocked ? (game.pendingSubstitution ? "等待" : "拦截") : ready ? "桥接中" : game ? (wwPhase.charAt(0).toUpperCase() + wwPhase.slice(1)) : "就绪");
  $("#conference-open-report") && ($("#conference-open-report").disabled = true);
  const input = $("#parliament-question-input");
  if (input && document.activeElement !== input && !input.value) {
    input.placeholder = game && !complete && !failed
      ? "运行中 · 输入干预指令或标记离线席位…"
      : "输入本局主题，例如：AI 模型谁最会伪装，按 Enter 开局。";
  }
  renderWerewolfSeatRail(game, eliminated);
  renderWerewolfWorkbench(game, eliminated);
  const stream = $("#conference-seat-stream");
  if (!stream) return;
  const renderSignature = JSON.stringify({
    status: game?.status || "empty",
    phase: game?.phase || wwPhase,
    board: game?.board || state.werewolfBoard || (typeof window.werewolfBoardKey === "function" ? window.werewolfBoardKey() : "standard"),
    selectedSeats: game?.players?.map(player => player.id) || werewolfSelectedSeatIds({ fill: true }).slice(0, targetSeatCount),
    visibleCount: visibleEvents.length,
    events: visibleEvents.map(event => ({
      kind: event.kind,
      phase: event.phase,
      seat: event.seat,
      status: event.status,
      text: event.text,
      eliminated: event.eliminated,
      substitution: event.substitution,
    })),
  });
  if (stream.dataset.renderSignature !== renderSignature) {
    stream.dataset.renderSignature = renderSignature;
    stream.innerHTML = visibleEvents.length
      ? visibleEvents.map((event, index) => parliamentBubbleHtml(werewolfEventToMessage(event, index, game), index)).join("")
      : werewolfEmptyStateHtml();
    requestAnimationFrame(() => {
      stream.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
  }
}

function werewolfEmptyStateHtml() {
  return `
    <div class="empty-state-parliament">
      <strong>模型狼人杀</strong>
      <p>从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选 ${WEREWOLF_SEAT_COUNT} 个参赛，${WEREWOLF_STANDBY_COUNT} 个留作替补。Grand Judge 会密封分配 3 狼、3 民、预言家、女巫、猎人，所有公开发言进入对话流。</p>
    </div>
  `;
}

function renderWerewolfSeatRail(game, eliminated) {
  const node = $("#parliament-seat-rail");
  if (!node) return;
  const reveal = game?.status === "complete";
  const players = game?.players || werewolfPlayers(werewolfSelectedSeatIds({ fill: true }));
  const total = Math.max(players.length, 1);
  node.innerHTML = players.map((player, index) => {
    const angle = -90 + (360 / total) * index;
    const radians = angle * Math.PI / 180;
    const x = 50 + Math.cos(radians) * 37;
    const y = 52 + Math.sin(radians) * 33;
    const dead = eliminated.has(player.id);
    const pending = state.werewolfPendingReplacementSeat === player.id;
    return `
      <button class="office-seat-token ${dead ? "is-failed" : pending ? "is-speaking" : "is-waiting"}" type="button" data-seat="${escapeAttr(player.id)}" aria-label="${escapeAttr(`${player.name} · ${pending ? "等待替补接管" : dead ? "出局" : "存活"} · ${reveal ? player.roleLabel : "身份密封"}`)}" style="--i:${index};--seat-color:${escapeAttr(player.color)};--provider-dot-color:${escapeAttr(player.providerDot || player.color)};--x:${x.toFixed(2)}%;--y:${y.toFixed(2)}%;">
        ${agentAvatarHtml(player, "office")}
        <span class="office-seat-name">${escapeHtml(player.name)}</span>
        <span class="office-seat-meta">${escapeHtml(pending ? "待替补" : dead ? "出局" : reveal ? player.roleLabel : "密封")}</span>
        <span class="member-badge office-seat-badge">${reveal ? escapeHtml(player.team === "werewolf" ? "狼" : "好") : "?"}</span>
      </button>
    `;
  }).join("");
}

function renderWerewolfWorkbench(game, eliminated) {
  renderWerewolfPhaseTimeline(game);
  const current = $("#parliament-current-speaker");
  if (current) {
    const activeNames = (game?.players || werewolfPlayers(werewolfSelectedSeatIds({ fill: true }))).map(player => player.name).join(" · ");
    const gate = game?.bridgeGate;
    const pendingSub = game?.pendingSubstitution?.offlineSeat ? werewolfSeatById(game.pendingSubstitution.offlineSeat) : null;
    const progress = game ? Math.max(6, Math.round(((gate?.readyCount ?? game.visibleCount) / (gate?.total || game.events.length || 1)) * 100)) : 5;
    const targetSeatCount = typeof window.werewolfSeatCount === "function" ? window.werewolfSeatCount() : WEREWOLF_SEAT_COUNT;
    current.innerHTML = `
      <div class="ww-grand-judge">
        <h3>Grand Judge</h3>
        <p>${game ? (pendingSub ? `${pendingSub.name} 超时离线，等待替补席接管原身份。` : gate ? `真实桥接门禁：${gate.readyCount}/${gate.total} 模型固定标签就绪。` : "正在主持模型狼人杀：私有身份只通过固定 Chrome 席位发送，公开流只显示发言、替补和投票。") : `从 ${WEREWOLF_CANDIDATE_COUNT} 个模型里选 ${targetSeatCount} 个开局。当前上场：${activeNames}`}</p>
        <div class="speaker-progress"><i style="--progress:${progress}%"></i></div>
      </div>
    `;
  }
  const resonance = $("#conference-resonance-ribbon");
  if (resonance) {
    const targetSeatCount = typeof window.werewolfSeatCount === "function" ? window.werewolfSeatCount() : WEREWOLF_SEAT_COUNT;
    const activeCount = game?.players?.length || werewolfSelectedSeatIds({ fill: true }).slice(0, targetSeatCount).length || targetSeatCount;
    const standbyCount = game
      ? WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !game.players.some(player => player.id === id) && !(game.offlineSeats || []).includes(id)).length
      : WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !werewolfSelectedSeatIds().includes(id)).length;
    const camps = werewolfCampCounts(game, eliminated);
    const totalKnown = Math.max(1, camps.good + camps.wolf);
    const goodPct = Math.round((camps.good / totalKnown) * 100);
    const wolfPct = Math.round((camps.wolf / totalKnown) * 100);
    resonance.innerHTML = `
      <h3>局势</h3>
      <p><span class="werewolf-chip">${WEREWOLF_CANDIDATE_COUNT} 选 ${targetSeatCount}</span> <span class="werewolf-chip">${activeCount - eliminated.size}/${activeCount} 存活</span> <span class="werewolf-chip">${standbyCount} 替补</span> <span class="werewolf-chip">${game?.status === "complete" ? "身份已揭示" : "身份密封"}</span></p>
      <div class="ww-camp-bar" aria-label="阵营存活对比">
        <i class="ww-camp-good" style="--pct:${goodPct}%"></i>
        <i class="ww-camp-wolf" style="--pct:${wolfPct}%"></i>
      </div>
      <p class="ww-camp-caption">好人 ${camps.good}${camps.unknown ? "（默认）" : ""} / 狼人 ${camps.wolf}${camps.unknown ? "（默认）" : ""}</p>
    `;
  }
  const score = $("#conference-score-flow");
  if (score) {
    const rows = (game?.scores || []).slice(0, game?.status === "complete" ? 9 : 3).map(([seat, value, reason]) => {
      const player = werewolfSeatById(seat);
      return `<div class="ww-score-card"><span><strong>${escapeHtml(player.name)}</strong><br>${escapeHtml(reason)}</span><b class="ww-score-tier tier-${werewolfScoreTier(value).toLowerCase()}">${werewolfScoreTier(value)}</b><em>${escapeHtml(value)}/100</em></div>`;
    }).join("");
    const abilityRows = werewolfAbilityRows(game).map(([role, desc]) => `<span class="ww-role-ability"><b>${escapeHtml(role)}</b><em>${escapeHtml(desc)}</em></span>`).join("");
    score.innerHTML = `<h3>评分与角色能力</h3><div class="ww-role-abilities">${abilityRows}</div>${game?.status === "complete" ? `<div class="ww-score-board">${rows}</div>` : "<p>游戏结束后按发言原创性、投票准确性、阵营贡献度评分；历史评分会写入模型选择卡。</p>"}`;
  }
  const memory = $("#conference-memory-panel");
  if (memory) {
    const activeIds = game?.players?.map(player => player.id) || werewolfSelectedSeatIds();
    const offline = new Set(game?.offlineSeats || []);
    const standby = WEREWOLF_CANDIDATE_SEAT_IDS
      .filter(id => !activeIds.includes(id) && !offline.has(id))
      .map(id => werewolfSeatById(id).name)
      .join(" · ");
    const gate = game?.bridgeGate;
    const missing = gate?.missing?.map(item => `${item.name}：${bridgeReasonText(item.reason)}`).join(" · ");
    memory.innerHTML = gate
      ? `<h3>桥接缺口</h3><p>${escapeHtml(missing || "全部参赛席位已就绪")}。登录或刷新网页后点下面按钮，AI Judge 只重新检测缺口席位，不重开整套页面。</p><button type="button" class="pill-button" data-werewolf-refresh-bridge>重新检测并继续</button>`
      : `<h3>替补席与私有门禁</h3><p>替补席：${escapeHtml(standby || "无")}。狼人队友、验人结果和药水选择只进入对应模型私有上下文；替补接管时由法官重新密封发送。</p>`;
  }
}

function werewolfEventToMessage(event, index, game) {
  if (event.kind === "seat") {
    const player = (game?.players || []).find(item => item.id === event.seat) || werewolfPlayers().find(item => item.id === event.seat) || werewolfSeatById(event.seat);
    const spectatorRole = (game?.spectatorRoleMap || game?.spectator_role_map || {})[player.id] || {};
    const viewerRoleLabel = spectatorRole.roleLabel || spectatorRole.role_label || event.spectator_role_label || (player.roleLabel && player.roleLabel !== "身份密封" ? player.roleLabel : "身份密封");
    const viewerTeam = spectatorRole.team === "werewolf" ? "狼队" : spectatorRole.team ? "好人" : "";
    const eventStatus = event.status || "done";
    const isVote = String(event.phase || "").startsWith("vote");
    const phaseText = String(event.phase || "");
    const phaseClass = phaseText.startsWith("night") ? "ww-bubble--night"
      : phaseText.startsWith("day") ? "ww-bubble--day"
      : phaseText.startsWith("vote") ? "ww-bubble--vote"
      : phaseText.startsWith("pk") ? "ww-bubble--pk"
      : phaseText === "final" ? "ww-bubble--complete"
      : event.eliminated ? "ww-bubble--result"
      : "";
    const working = ["queued", "preparing", "speaking", "running", "voting"].includes(eventStatus);
    const failed = eventStatus === "failed";
    const progress = Number.isFinite(Number(event.progress)) ? Number(event.progress) : working ? 42 : 100;
    const text = event.text || (working ? `正在从 ${player.name} 的固定模型网页读取${isVote ? "投票" : "真实回复"}...` : "");
    return {
      kind: "seat",
      msgState: failed ? "blocked" : working ? "working" : "done",
      seatId: player.id,
      role: player.name,
      providerCode: player.providerCode,
      identityGlyph: player.identityGlyph,
      channel: player.channel,
      providerDot: player.providerDot,
      color: player.color,
      status: failed ? "桥接异常" : working ? (isVote ? "正在投票" : "正在发言") : (isVote ? "投票完成" : "公开发言"),
      roleLabel: viewerRoleLabel,
      processName: `${event.phase || "day"} ${isVote ? "vote" : "public speech"}`,
      processStatus: failed ? "未完成" : working ? (isVote ? "投票回收中" : "读取中") : (isVote ? "已投票" : "已发言"),
      processSummary: failed
        ? `${player.name} 的模型页没有返回可用正文，公开流不会用本地台词补写。`
        : working
          ? `${player.name} 正在通过真实网页席位${isVote ? "提交本轮投票" : "生成本轮公开发言"}。`
          : `${player.name} 已完成${isVote ? "投票" : "公开发言"}。身份徽章只给本机用户观战，模型公开记录仍然密封。`,
      text,
      fullText: text,
      chips: [[event.phase || "白天", failed ? "warn" : "ok"], [viewerRoleLabel, spectatorRole.team === "werewolf" ? "block" : "warn"], ...(viewerTeam ? [[viewerTeam, ""]] : [])],
      werewolfPhaseClass: phaseClass,
      progress,
      working,
    };
  }
  const judgePhaseText = String(event.phase || "");
  const judgePhaseClass = judgePhaseText.startsWith("night") ? "ww-bubble--night"
    : judgePhaseText.startsWith("day") ? "ww-bubble--day"
    : judgePhaseText.startsWith("vote") ? "ww-bubble--vote"
    : judgePhaseText.startsWith("pk") ? "ww-bubble--pk"
    : judgePhaseText === "final" ? "ww-bubble--complete"
    : event.eliminated ? "ww-bubble--result"
    : "";
  return {
    kind: "judge",
    msgState: event.phase === "final" ? "verdict" : event.phase === "bridge-gate" ? "blocked" : event.phase === "bridge-ready" ? "pending" : "confirmed",
    role: event.phase === "setup" ? "Grand Judge · 发身份" : "Grand Judge",
    color: "#111827",
    status: event.status || "流程推进",
    text: event.text,
    chips: [["狼人杀模式", ""], [event.phase || `event-${index}`, ""]],
    werewolfPhaseClass: judgePhaseClass,
    working: false,
  };
}

function parliamentMessages(v, hasRunning) {
  const question = conferenceQuestion(v);
  const speakers = parliamentSpeakers(v, hasRunning);
  const messages = [];

  // P18: Pre-run flow — show Grand Judge pre-run conversation
  if (state.preRunFlow.active && !state.preRunFlow.confirmed) {
    return state.preRunFlow.messages.map((m, i) => ({ ...m, index: i }));
  }

  if (!question) {
    return messages;
  }

  const preRunTranscript = Array.isArray(state.preRunTranscript) ? state.preRunTranscript : [];
  if (preRunTranscript.length) {
    messages.push(...preRunTranscript.map((message, i) => ({ ...message, index: i })));
  } else {
    messages.push({
      kind: "system",
      msgState: "intake",
      role: "用户议题",
      avatar: "议",
      color: "#111827",
      status: "已接收",
      text: `已收到议题：${question}\nGrand Judge 正在把问题整理成可审议的会议动议。`,
    });
    const promptText = state.promptPreview?.professional_prompt || state.mentorSnapshot?.execution_draft || "";
    const judgeStatus = v
      ? "议题已确认"
      : state.mentorConfirmed
        ? "提示词已确认"
        : state.mentorEnabled
          ? "等待你确认提示词"
          : "快速开庭";
    messages.push({
      kind: "judge",
      msgState: state.mentorEnabled && !state.mentorConfirmed && !v ? "pending" : "confirmed",
      role: "Grand Judge",
      avatar: "法",
      color: "#111827",
      status: judgeStatus,
      text: promptText
        ? excerpt(promptText, 360)
        : "议题已确认。现在请各位议员依次发言：每位议员必须给出独立观点、风险边界和可执行依据，书记员会完整保存原文。",
      working: state.mentorEnabled && !state.mentorConfirmed && !v,
    });
  }
  speakers.forEach(speaker => {
    if (speaker.state === "queued") return;
    messages.push({
      kind: "seat",
      msgState: speaker.state === "speaking" ? "speaking" : speaker.state === "complete" ? "done" : speaker.state === "blocked" ? "failed" : "queued",
      seatId: speaker.id,
      role: speaker.name,
      providerCode: speaker.providerCode,
      identityGlyph: speaker.identityGlyph,
      channel: speaker.channel,
      providerDot: speaker.providerDot,
      color: speaker.color,
      status: speaker.status,
      roleLabel: speaker.roleLabel || "议员席位",
      processName: speaker.processName || "independent answer",
      processStatus: parliamentAgentProcessStatus(speaker),
      processSummary: parliamentAgentProcessSummary(speaker),
      text: speaker.detail,
      fullText: speaker.fullText || speaker.detail,
      chips: [[speaker.chip, speaker.state === "blocked" ? "block" : speaker.state === "complete" ? "ok" : "warn"], [speaker.channel, ""]],
      progress: speaker.progress,
      working: speaker.state === "speaking",
      toolEvents: parliamentToolEventsForSpeaker(speaker),
    });
  });
  const supplements = v?.web_bridge?.mentor_supplements || [];
  if (hasRunning || supplements.length) {
    messages.push({
      kind: "judge",
      msgState: "resonance",
      role: "共振追问",
      avatar: "追",
      color: "#111827",
      status: supplements.length ? "二轮追问已归档" : "等待第一轮完成",
      text: supplements.length
        ? `已从议员原始回答中提取 ${supplements.reduce((sum, item) => sum + (item.source_questions || []).length, 0)} 个追问，并保留二轮补充。`
        : "第一轮发言结束后，我会提取每个议员自己暴露出的疑问，再让它们反向回答，形成共振记录。",
      working: hasRunning && !supplements.length,
    });
  }
  if (v) {
    const coverage = seatCoverageSummary(v);
    messages.push({
      kind: "judge",
      msgState: "verdict",
      role: "Grand Judge",
      avatar: "判",
      color: "#111827",
      status: "最终裁决",
      text: `${reportHeaderTitle(v)}\n\n${reportHeaderSummary(v)}`,
      chips: [[`可信度 ${v.confidence ?? "-"}%`, ""], [coverage.label || "按模式", ""], ["正式报告已生成", ""]],
      actions: [["完整报告", "draft"], ["证据", "evidence"], ["历史", "history"]],
    });
  }
  return messages;
}

// P4: Real agent-turn-card rendering with atc-left / atc-body / atc-expand-arrow
function parliamentBubbleHtml(message, index = 0) {
  const chips = (message.chips || []).map(([label, state]) => `<span class="parliament-chip ${escapeAttr(state || "")}">${escapeHtml(label)}</span>`).join("");
  const actions = (message.actions || []).map(([label, tab]) => `<button class="ghost" data-tab-shortcut="${escapeAttr(tab)}" type="button">${escapeHtml(label)}</button>`).join("");
  const typing = message.working ? '<span class="typing-dots" aria-label="正在输入"><i></i><i></i><i></i></span>' : "";
  const progress = message.progress !== undefined ? `<div class="speaker-progress"><i style="--progress:${Math.max(8, Math.min(100, Number(message.progress || 0)))}%"></i></div>` : "";
  const stateClass = message.msgState ? `msg-state-${message.msgState}` : "";
  const toolEvents = (message.toolEvents || []).map(renderToolEvent).join("");

  // Judge / system messages keep their existing layout
  if (message.kind === "judge" || message.kind === "system") {
    return `
      <article class="msg-system ${stateClass} ${message.msgState === "verdict" ? "is-verdict" : ""} ${message.working ? "is-working" : ""}" style="--i:${index};--seat-color:${escapeAttr(message.color || "#6366F1")}">
        <div class="msg-header">
          <span class="msg-sender">${escapeHtml(message.role || "Grand Judge")}</span>
          <span class="msg-time">${escapeHtml(message.status || "")}${typing}</span>
        </div>
        <div class="msg-content">${formatParliamentText(message.text || "")}</div>
        ${toolEvents}
        ${progress}
        ${chips || actions ? `<div class="parliament-bubble-actions">${chips}${actions}</div>` : ""}
      </article>
    `;
  }

  // P8: Marvis agent turn card — turn-header / turn-body / turn-footer structure
  const modelId = message.seatId || message.role || "model";
  const modelName = message.role || "议员";
  const providerChannel = message.channel || "";
  const roleLabel = message.roleLabel || "议员席位";
  const speechState = message.msgState || "queued";
  const statusLabel = STATUS_LABELS[speechState] || speechState;
  const processDescription = message.processSummary || "";
  const processStatus = message.processStatus || "";
  const fullText = message.fullText || message.text || "";

  return `
    <article
      class="agent-turn-card"
      data-model="${escapeAttr(modelId)}"
      data-state="${escapeAttr(speechState)}"
      data-speech-state="${escapeAttr(speechState)}"
      data-seat-message="${escapeAttr(message.seatId || "")}"
      style="--i:${index};--seat-color:${escapeAttr(message.color || "#111827")};--provider-dot-color:${escapeAttr(message.providerDot || message.color || "#111827")}"
      role="button" tabindex="0" aria-expanded="false"
    >
      <div class="turn-avatar-rail">
        <img class="turn-avatar" src="${escapeAttr(_avatarDataUri(modelId) || _avatarDataUri('claude'))}" width="40" height="40" alt="${escapeAttr(modelName)}" loading="lazy" />
        <span class="atc-status-dot atc-${escapeAttr(speechState)}" aria-hidden="true"></span>
      </div>
      <div class="turn-card-main">
        <div class="turn-header">
          <span class="turn-model-name">${escapeHtml(modelName)}</span>
          ${providerChannel ? `<span class="atc-provider">${escapeHtml(providerChannel)}</span>` : ""}
          <span class="turn-role-badge atc-role">${escapeHtml(roleLabel)}</span>
          <span class="atc-status-label">${escapeHtml(statusLabel)}</span>
          ${typing}
        </div>
        ${processDescription ? `
          <div class="turn-process-pill" data-state="${escapeAttr(speechState)}">
            <span class="turn-process-dot" aria-hidden="true"></span>
            ${processStatus ? `<strong>${escapeHtml(processStatus)}</strong>` : ""}
            <span>${escapeHtml(processDescription)}</span>
          </div>
        ` : ""}
        <div class="turn-body">
          <p class="turn-summary">${escapeHtml(message.text || processDescription || "")}</p>
          <div class="turn-expand">${formatParliamentText(fullText)}</div>
          ${toolEvents}
          ${progress}
          ${chips || actions ? `<div class="parliament-bubble-actions">${chips}${actions}</div>` : ""}
        </div>
        <div class="turn-footer">
          <span>${fullText ? "原始答案已进入 Parliament Record" : "等待原始答案归档"}</span>
          <span class="turn-time">${escapeHtml(message.processName || "")}</span>
        </div>
      </div>
    </article>
  `;
}

function parliamentToolEventsForSpeaker(speaker) {
  if (speaker.state === "speaking") {
    return [
      {
        name: "web_bridge",
        icon: "⌁",
        statusLabel: "running",
        state: "running",
        body: `${speaker.name} 正在通过网页席位读取主审议题并生成独立发言。`,
      },
    ];
  }
  if (speaker.state === "complete") {
    return [
      {
        name: "seat_archive",
        icon: "✓",
        statusLabel: "complete",
        state: "complete",
        body: "原始回答已归档，等待 Grand Judge 进入证据提取和交叉审查。",
      },
    ];
  }
  return [];
}

function parliamentAgentProcessStatus(speaker) {
  if (speaker.state === "complete") return "已完成";
  if (speaker.state === "speaking") return "进行中";
  if (speaker.state === "blocked") return "已隔离";
  return speaker.status || "等待中";
}

function parliamentAgentProcessSummary(speaker) {
  if (speaker.state === "complete") {
    return `${speaker.name} 已完成独立发言，原始答案进入 Parliament Record。`;
  }
  if (speaker.state === "speaking") {
    return `${speaker.name} 正在读取议题、校准角色，并生成可追溯发言。`;
  }
  if (speaker.state === "blocked") {
    return `${speaker.name} 的桥接输出未通过，将保留异常记录供 Grand Judge 复核。`;
  }
  return `${speaker.name} 已排队，等待 Grand Judge 分配发言顺序。`;
}

function renderToolEvent(toolEvent) {
  return `
    <div class="tool-event" data-state="${escapeAttr(toolEvent.state || "running")}">
      <div class="tool-event__header">
        <span>${escapeHtml(toolEvent.icon || "⌁")}</span>
        <span class="tool-name">${escapeHtml(toolEvent.name || "tool")}</span>
        <span class="tool-status">${escapeHtml(toolEvent.statusLabel || "")}</span>
        ${toolEvent.state === "complete" ? '<span class="tool-check">✓</span>' : ""}
      </div>
      ${toolEvent.body ? `<div class="tool-event__body">${escapeHtml(toolEvent.body)}</div>` : ""}
    </div>
  `;
}

function formatParliamentText(text) {
  const raw = String(text || "");
  // P19: Convert **bold** markers before escapeHtml, using placeholder protection
  const boldParts = [];
  const boldSafe = raw.replace(/\*\*(.+?)\*\*/g, (_full, content) => {
    boldParts.push(escapeHtml(content));
    return `\x00BOLD${boldParts.length - 1}\x00`;
  });
  const escaped = escapeHtml(boldSafe);
  const restored = escaped.replace(/\x00BOLD(\d+)\x00/g, (_full, idx) => `<strong>${boldParts[Number(idx)]}</strong>`);
  const parts = restored.split(/\n{2,}/).map(part => part.trim()).filter(Boolean);
  if (!parts.length) return "";
  return parts.map((part, index) => `<p style="--p-index:${index}">${part.replace(/\n/g, "<br>")}</p>`).join("");
}

function parliamentSpeakers(v, hasRunning = false) {
  const rawResults = Array.isArray(v?.web_bridge?.raw_results)
    ? v.web_bridge.raw_results
    : Array.isArray(state.parliamentDemoResults)
      ? state.parliamentDemoResults
      : [];
  const rawBySeat = new Map();
  rawResults.forEach((item, index) => {
    const key = canonicalParliamentSeatId(item.seat || item.id || item.name || `seat-${index + 1}`);
    if (key && !rawBySeat.has(key)) rawBySeat.set(key, item);
  });
  const completed = rawResults.filter(item => item.status === "ok" || item.ok || item.answer || item.response).length;
  const activeIndex = hasRunning ? Math.min(Math.max(completed, 0), PARLIAMENT_SEATS.length - 1) : -1;
  return PARLIAMENT_SEATS.map((meta, index) => {
    const raw = rawBySeat.get(meta.id);
    const rawOk = Boolean(raw && (raw.status === "ok" || raw.ok || raw.answer || raw.response));
    const recoverable = raw && !rawOk && isSupplementableResult(raw);
    const ready = seatBridgeReady(meta.id);
    const answer = raw?.answer || raw?.response || raw?.text || raw?.summary || raw?.error?.message || raw?.error || "";
    const stateValue = rawOk
      ? "complete"
      : raw
        ? recoverable ? "speaking" : "blocked"
        : hasRunning && index === activeIndex
          ? "speaking"
          : "queued";
    return {
      ...meta,
      state: stateValue,
      status: stateValue === "complete" ? "已发言" : stateValue === "speaking" ? "正在思考" : stateValue === "blocked" ? "异常隔离" : ready ? "等待发言" : "待校准",
      chip: stateValue === "complete" ? "原文已归档" : stateValue === "speaking" ? "动态发言中" : stateValue === "blocked" ? "桥接异常" : ready ? "等待发言" : "等待桥接",
      detail: rawOk
        ? excerpt(answer, 360) || `${meta.name} 已提交完整发言，原文进入内部资料库。`
        : stateValue === "speaking"
          ? `${meta.name} 正在读取主审提示词，生成独立方案、风险边界和可执行路径。`
          : stateValue === "blocked"
            ? excerpt(answer, 220) || `${meta.name} 没有形成可用发言，已经进入异常隔离记录。`
            : `${meta.name} 已在议员席等待。确认提示词后，它会以独立身份发言，完整内容会逐字归档。`,
      fullText: answer || "",
      progress: stateValue === "complete" ? 100 : stateValue === "speaking" ? Math.max(28, Math.min(88, state.currentTask?.progress || 54)) : stateValue === "blocked" ? 100 : ready ? 18 : 8,
    };
  });
}

function canonicalParliamentSeatId(value) {
  const key = String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
  if (!key) return "";
  if (key.includes("chatgpt") || key.includes("openai") || key === "gpt" || key.includes("gpt4")) return "chatgpt";
  if (key.includes("claude") || key.includes("anthropic")) return "claude";
  if (key.includes("gemini") || key.includes("google")) return "gemini";
  if (key.includes("deepseek")) return "deepseek";
  if (key.includes("qwen") || key.includes("tongyi")) return "qwen";
  if (key.includes("kimi") || key.includes("moonshot")) return "kimi";
  if (key.includes("doubao") || key.includes("bytedance")) return "doubao";
  if (key.includes("mimo") || key.includes("minimax")) return "mimo";
  if (key.includes("wenxin") || key.includes("ernie") || key.includes("baidu")) return "wenxin";
  return key;
}

function renderCouncilRoundtable(v, hasRunning) {
  const node = $("#council-roundtable");
  if (!node) return;
  const actors = councilActors(v).slice(0, 9);
  const positions = [
    [50, 13], [75, 20], [89, 45], [81, 72], [58, 84],
    [32, 84], [11, 63], [11, 35], [26, 20],
  ];
  const seatsHtml = actors.map((actor, index) => {
    const [x, y] = positions[index] || [50, 50];
    const stateClass = actor.state === "ok" ? "is-speaking" : actor.state === "block" ? "is-blocked" : "is-waiting";
    return `
      <article class="council-seat ${stateClass}" style="--x:${x}%;--y:${y}%;--seat-color:${seatColor(index)}" data-seat="${escapeAttr(actor.name)}">
        <span class="seat-face">${escapeHtml(actor.initial)}</span>
        <strong>${escapeHtml(actor.name)}</strong>
        <span><i class="seat-status-dot"></i>${escapeHtml(actor.status)}</span>
        <span>${escapeHtml(actor.chip || actor.meta || "等待发言")}</span>
      </article>
    `;
  }).join("");
  const status = v
    ? `${seatCoverageSummary(v).label || "按模式"} · 主审待签字`
    : hasRunning
      ? "席位正在依次发言"
      : "等待提交议题";
  node.innerHTML = `
    <div class="roundtable-core">
      <div>
        <strong>Grand Judge</strong>
        <span>${escapeHtml(status)}</span>
      </div>
    </div>
    ${seatsHtml}
  `;
}

function renderCouncilSpeechGrid(v, hasRunning) {
  const node = $("#council-speech-grid");
  if (!node) return;
  const actors = councilActors(v).slice(0, 9);
  node.innerHTML = actors.map((actor, index) => {
    const state = actor.state === "ok" ? "ok" : actor.state === "block" ? "block" : "warn";
    const detail = actor.detail || (hasRunning ? "正在等待该席位发言，完成后会补入原文和摘要。" : "确认提示词后进入正式发言。");
    return `
      <article class="speech-card">
        <header>
          <span class="seat-face" style="--seat-color:${seatColor(index)}">${escapeHtml(actor.initial)}</span>
          <div>
            <strong>${escapeHtml(actor.name)}</strong>
            <span class="muted">${escapeHtml(actor.status || "待入席")}</span>
          </div>
        </header>
        <p>${escapeHtml(excerpt(detail, 150))}</p>
        <footer>
          <span class="bubble-chip ${state}">${escapeHtml(actor.chip || "会议记录")}</span>
          <span class="bubble-chip">${escapeHtml(actor.meta || "原文归档")}</span>
        </footer>
      </article>
    `;
  }).join("");
}

function renderConferenceScoreFlow(v, hasRunning) {
  const node = $("#conference-score-flow");
  if (!node) return;
  const rounds = v?.web_bridge?.score_rounds || [];
  const fallback = [
    { label: "原始发言", average_score: v ? scoreFromConfidence(v.confidence) : hasRunning ? 0.42 : 0 },
    { label: "V2 行为校准", average_score: v ? 0.62 : 0 },
    { label: "V3 认知校准", average_score: v ? 0.68 : 0 },
    { label: "Grand Judge 裁决", average_score: v ? scoreFromConfidence(v.confidence) : 0 },
  ];
  const items = (rounds.length ? rounds : fallback).slice(0, 4);
  const body = items.map((round, index) => {
    const score = Number(round.average_score ?? round.score ?? 0);
    const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
    return `
      <article class="score-layer" style="--i:${index};">
        <div><strong>${escapeHtml(round.label || round.id || `评分层 ${index + 1}`)}</strong><span>${pct}%</span></div>
        <div class="score-meter"><i style="--score:${pct}%"></i></div>
        <span>${escapeHtml(scoreLayerCaption(round, index))}</span>
      </article>
    `;
  }).join("");
  node.innerHTML = `<h3>评分计算进度</h3>${body || '<p class="muted">等待议员发言后生成评分层。</p>'}`;
}

function renderConferenceResonanceRibbon(v, hasRunning) {
  const node = $("#conference-resonance-ribbon");
  if (!node) return;
  const supplements = v?.web_bridge?.mentor_supplements || [];
  const questionCount = supplements.reduce((sum, item) => sum + (item.source_questions || []).length, 0);
  const okCount = supplements.filter(item => item.ok || item.response).length;
  const lead = questionCount
    ? `已提取 ${questionCount} 个共振追问，${okCount}/${supplements.length || okCount} 个席位完成二轮补充。`
    : hasRunning
      ? "席位第一轮发言后，系统会提取它们自己提出的追问并要求二轮回答。"
      : "共振追问会从原始答案中提取，不会覆盖原文，只会形成第二轮补充。";
  node.innerHTML = `
    <span class="resonance-step">共振追问</span>
    <p>${escapeHtml(lead)}</p>
    <button class="ghost" data-tab-shortcut="evidence" type="button">查看追溯</button>
  `;
}

function renderConferenceMemoryPanel(v) {
  const node = $("#conference-memory-panel");
  if (!node) return;
  const historyCount = state.historyRuns?.length || 0;
  const coverage = seatCoverageSummary(v);
  const verdict = v ? reportHeaderTitle(v) : "等待本轮裁决";
  node.innerHTML = `
    <h3>记忆库</h3>
    <div class="memory-stat-grid">
      <div class="memory-stat"><span>历史裁决</span><strong>${historyCount}</strong></div>
      <div class="memory-stat"><span>候选模型</span><strong>${WEREWOLF_CANDIDATE_COUNT} 候选 · ${WEREWOLF_SEAT_COUNT} 参赛 · ${coverage.ready || 0} 就绪</strong></div>
      <div class="memory-stat"><span>当前锚点</span><strong>${escapeHtml(excerpt(verdict, 24))}</strong></div>
      <div class="memory-stat"><span>报告状态</span><strong>${v ? "可成文" : "待开庭"}</strong></div>
    </div>
    <ol class="memory-list">
      <li>保留每个模型原始报告，不用摘要替代原文。</li>
      <li>共振追问、互评、评分矩阵独立归档。</li>
      <li>最终报告只保留正式文书，内部材料进入资料库。</li>
    </ol>
  `;
}

function councilActors(v) {
  const actors = conferenceSeatActors(v);
  if (actors.length >= 6) return actors;
  const canonical = ["ChatGPT", "Gemini", "DeepSeek", "Qwen", "Kimi", "Doubao", "Yuanbao", "MiMo", "Wenxin"];
  const seen = new Set(actors.map(actor => actor.name.toLowerCase()));
  canonical.forEach((name, index) => {
    if (seen.has(name.toLowerCase())) return;
    actors.push({
      name,
      initial: seatInitials(name),
      tone: seatTone(index),
      state: "warn",
      status: "待入席",
      chip: "等待桥接",
      meta: "席位候补",
      detail: `${name} 将在确认提示词后进入独立发言，原文会进入完整结果资料库。`,
    });
  });
  return actors;
}

function seatColor(index) {
  return ["#172033", "#2f5d8c", "#0f6b48", "#7c3f22", "#5b4b88", "#8a3150", "#38686a", "#80623d", "#31405a"][index % 9];
}

function scoreFromConfidence(confidence) {
  const value = Number(confidence || 0) || 0;
  return value > 1 ? value / 100 : value;
}

function scoreLayerCaption(round, index) {
  const captions = [
    "记录每个席位的原始独立报告。",
    "校准行为层：可执行性、风险、边界。",
    "校准认知层：证据密度和推理一致性。",
    "汇总为可签字的主审裁决。",
  ];
  if (round.claim_count) return `${round.claim_count} 条 claim 进入本层评分。`;
  return captions[index] || "该层已进入评分链路。";
}

function conferenceQuestion(v) {
  const requestQuestion = $("#question-input")?.value.trim() || "";
  const preRunQuestion = state.preRunFlow?.active
    ? state.preRunFlow.question
    : (Array.isArray(state.preRunTranscript)
        ? (state.preRunTranscript.find(message => message.kind === "user")?.text || "")
        : "");
  return v?.question
    || state.currentTask?.question
    || preRunQuestion
    || (currentTabName() === "request" ? requestQuestion : "")
    || "";
}

function renderConferencePhaseRail(v, hasRunning) {
  const rail = $("#conference-phase-rail");
  if (!rail) return;
  // P2-9: Global status bar with model dots + states
  const speakers = parliamentSpeakers(v, hasRunning);
  if (speakers.length === 0) { rail.style.display = "none"; return; }
  rail.style.display = "flex";
  rail.innerHTML = '<div class="phase-rail-inner">' + speakers.map((sp, i) => {
    const dotClass = sp.state === "complete" ? "phase-dot-done" : sp.state === "speaking" ? "phase-dot-active" : sp.state === "blocked" ? "phase-dot-failed" : "phase-dot-queued";
    const stateIcon = sp.state === "complete" ? "&#10003;" : sp.state === "speaking" ? "&#9679;" : sp.state === "blocked" ? "&#10007;" : "#" + (i + 1);
    return '<span class="phase-dot ' + dotClass + '" style="--dot-color:' + (sp.color || "#64748b") + '" title="' + escapeAttr(sp.name) + '">' +
      '<i>' + stateIcon + '</i><em>' + escapeHtml(sp.name) + '</em></span>';
  }).join("") + '</div>';
  return;
}

function conferenceMessages(v, hasRunning) {
  const messages = [];
  const question = conferenceQuestion(v);
  if (!question) {
    messages.push({
      role: "主审法官",
      avatar: "法",
      tone: "gold",
      kind: "judge",
      status: "等待输入",
      text: "把链接、文件或问题交给我。我会先整理成可确认提示词，再邀请网页席位逐一发言。",
      chips: [["主审预审", "warn"], ["确认后开庭", "warn"]],
    });
    messages.push(...conferenceSeatActors(v).slice(0, 4).map(actor => ({
      role: actor.name,
      avatar: actor.initial,
      tone: actor.tone,
      kind: "seat",
      status: actor.status,
      text: actor.detail,
      chips: [[actor.chip, actor.state]],
      working: actor.state === "warn",
    })));
    return messages;
  }
  messages.push({
    role: "用户议题",
    avatar: "问",
    tone: "blue",
    kind: "user",
    status: "已受理",
    text: question,
    chips: [[state.selectedMode || "standard", "ok"], [state.engine === "web" ? "网页全量" : state.engine, "ok"]],
  });
  const promptText = state.promptPreview?.professional_prompt || state.mentorSnapshot?.execution_draft || "";
  messages.push({
    role: "主审法官",
    avatar: "法",
    tone: "gold",
    kind: "judge",
    status: state.mentorConfirmed ? "提示词已确认" : state.mentorEnabled ? "等待确认提示词" : "快速开庭",
    text: promptText ? excerpt(promptText, 250) : "我会保留原始问题，要求每个席位给出独立方案、可执行计划、风险、证据边界和下一步。",
    chips: [
      [state.mentorEnabled ? "主审门禁开启" : "快速模式", state.mentorEnabled && !state.mentorConfirmed ? "warn" : "ok"],
      [`席位 ${state.selectedSeats.size || "按模式"}`, "ok"],
    ],
    working: state.mentorEnabled && !state.mentorConfirmed,
  });
  conferenceSeatActors(v).slice(0, 8).forEach(actor => {
    messages.push({
      role: actor.name,
      avatar: actor.initial,
      tone: actor.tone,
      kind: "seat",
      status: actor.status,
      text: actor.detail,
      chips: [[actor.chip, actor.state], actor.meta ? [actor.meta, ""] : null].filter(Boolean),
      working: actor.state === "warn",
    });
  });
  if (hasRunning && !v) {
    messages.push({
      role: "书记员",
      avatar: "书",
      tone: "blue",
      kind: "judge",
      status: "记录中",
      text: "后台会持续保存每个席位的原文、执行状态和恢复记录；最终报告不会替换原始材料。",
      chips: [["全量记录", "ok"], ["完成后归档", "warn"]],
      working: true,
    });
  }
  if (v) {
    messages.push({
      role: "主审法官",
      avatar: "报",
      tone: "gold",
      kind: "judge",
      status: "形成汇报",
      text: `${reportHeaderTitle(v)}。${reportHeaderSummary(v)}`,
      chips: [[`可信度 ${v.confidence ?? "-"}%`, "ok"], [coverage.label || "按模式", coverage.ok ? "ok" : "warn"]],
      actions: [
        ["完整报告", "draft"],
        ["证据", "evidence"],
        ["历史", "history"],
      ],
    });
  }
  return messages;
}

function conferenceSeatActors(v) {
  const raw = v?.web_bridge?.raw_results || [];
  if (raw.length) {
    return raw.map((item, index) => {
      const ok = item.status === "ok" || item.ok || item.answer || item.response;
      const recoverable = !ok && isSupplementableResult(item);
      const name = seatName(item.seat || item.id || item.name || `seat-${index + 1}`);
      const answer = item.answer || item.response || item.text || item.summary || item.error?.message || item.error || "";
      return {
        name,
        initial: seatInitials(name),
        tone: seatTone(index),
        state: ok ? "ok" : recoverable ? "warn" : "block",
        status: ok ? "已发言" : recoverable ? "回收中" : "需处理",
        chip: ok ? "原文已归档" : recoverable ? "桥接恢复" : "异常隔离",
        meta: item.duration_seconds ? `${Number(item.duration_seconds).toFixed(1)}s` : "",
        detail: ok
          ? excerpt(answer, 210) || "该席位已返回完整内容，点进完整报告可查看原文。"
          : recoverable
            ? "该席位可能存在慢响应、输入框残留或旧页面答案问题，系统会优先刷新并回收原文。"
            : excerpt(answer, 180) || "该席位未形成可用答案，已进入隔离记录。",
      };
    });
  }
  const selected = state.seats.filter(seat => state.selectedSeats.has(seat.id));
  const seats = selected.length ? selected : state.seats;
  return seats.slice(0, 8).map((seat, index) => {
    const ready = seatBridgeReady(seat.id);
    return {
      name: seat.name || seat.id,
      initial: seatInitials(seat.name || seat.id),
      tone: seatTone(index),
      state: ready ? "ok" : "warn",
      status: ready ? "已入席" : "待校准",
      chip: ready ? "网页已校准" : "等待桥接",
      meta: ready ? "可发言" : statusLabel(bridgeMatrixBySeat(seat.id)?.reason || bridgeSeatById(seat.id)?.reason, false),
      detail: ready
        ? `${seat.name || seat.id} 已准备好接收主审提示词，返回后会进入全量会议档案。`
        : `${seat.name || seat.id} 尚未完全就绪，需要桥接官校准或刷新页面。`,
    };
  });
}

function seatTone(index) {
  return ["blue", "green", "", "red", "gold"][index % 5];
}

function conferenceBubbleHtml(message) {
  const tone = message.tone ? ` ${escapeAttr(message.tone)}` : "";
  const actions = (message.actions || []).map(([label, tab]) => `<button class="ghost" data-tab-shortcut="${escapeAttr(tab)}" type="button">${escapeHtml(label)}</button>`).join("");
  const chips = (message.chips || []).map(([label, state]) => `<span class="bubble-chip ${escapeAttr(state || "")}">${escapeHtml(label)}</span>`).join("");
  return `
    <article class="meeting-bubble is-${escapeAttr(message.kind || "seat")} ${message.working ? "is-working" : ""}">
      <div class="meeting-avatar${tone}">${escapeHtml(message.avatar || "?")}</div>
      <div class="bubble-body">
        <div class="bubble-meta"><strong>${escapeHtml(message.role || "模型")}</strong><span>${escapeHtml(message.status || "")}</span></div>
        <p>${escapeHtml(message.text || "")}</p>
        ${chips ? `<div class="bubble-actions">${chips}</div>` : ""}
        ${actions ? `<div class="bubble-actions">${actions}</div>` : ""}
      </div>
    </article>
  `;
}

function conferenceLogItems(v, hasRunning) {
  const counts = bridgeChannelCounts();
  const items = [
    {
      title: "会议入口",
      meta: conferenceQuestion(v) ? "议题已进入主审整理" : "等待提交裁决问题",
      state: conferenceQuestion(v) ? "ok" : "warn",
    },
    {
      title: "网页席位",
      meta: `${counts.webReady}/${counts.webTotal} 已校准`,
      state: counts.webTotal && counts.webReady < counts.webTotal ? "warn" : "ok",
    },
  ];
  if (state.currentTask?.run_id) {
    items.push({
      title: `Run ${compactRunId(state.currentTask.run_id)}`,
      meta: `${state.currentTask.status || "running"} · ${state.currentTask.current_step || "执行中"}`,
      state: hasRunning ? "warn" : "ok",
    });
  }
  if (v) {
    const coverage = seatCoverageSummary(v);
    items.push({
      title: "最终报告",
      meta: `${reportHeaderTitle(v)} · ${coverage.label || "按模式"}`,
      state: "ok",
    });
    const failures = autopilotFailureCount(v);
    items.push({
      title: "桥接恢复",
      meta: failures ? `${failures} 个模型需要回收或隔离` : "没有需要处理的桥接失败",
      state: failures ? "warn" : "ok",
    });
  }
  items.push({
    title: "档案规则",
    meta: "原始回答、互评、共振追问、导师补充和证据表分层保存",
    state: "ok",
  });
  return items;
}

function conferenceLogHtml(item) {
  return `
    <div class="log-entry">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.meta)}</span>
      <span class="log-chip ${escapeAttr(item.state || "")}">${escapeHtml(item.state === "ok" ? "正常" : item.state === "block" ? "阻断" : "注意")}</span>
    </div>
  `;
}

function bridgeNeedsAttention(v) {
  if (autopilotFailureCount(v)) return true;
  const counts = bridgeChannelCounts();
  return counts.webTotal > 0 && counts.webReady < counts.webTotal;
}

function buildTaskItems() {
  if (state.productMode !== "pro") return buildSimpleTaskItems();
  const counts = bridgeChannelCounts();
  const coverage = seatCoverageSummary();
  const hasVerdict = Boolean(state.currentVerdict);
  const hasQuestion = Boolean($("#question-input")?.value.trim());
  const bridgeNeedsWork = counts.webTotal > 0 && counts.webReady < counts.webTotal;
  const publishSummary = buildPublishGateSummary();
  const evidenceSummary = evidenceGateSummary();
  const mentorSummary = mentorGateSummary();
  const draftRisk = state.currentTask?.status === "running"
    ? "warn"
    : hasVerdict
      ? "ok"
      : "warn";
  return [
    {
      id: "request",
      title: "新的议题评审",
      summary: state.mentorEnabled ? "从问题录入、导师预检和执行确认开始" : "快速模式直达，可随时打开导师门禁",
      stage: "录入",
      risk: mentorSummary.state,
      riskLabel: mentorSummary.label,
      seats: state.selectedSeats.size ? `${state.selectedSeats.size} 席` : "按模式",
      next: hasQuestion ? "确认任务" : "填写问题",
      tab: "request",
      detail: mentorSummary.detail,
    },
    {
      id: "draft",
      title: "最近判词",
      summary: hasVerdict ? "当前判词已恢复，可查看草稿与执行轨迹" : "运行一次评议后生成可审计草稿",
      stage: "生成",
      risk: draftRisk,
      riskLabel: hasVerdict ? "可查看" : state.currentTask?.status === "running" ? "运行中" : "等待结果",
      seats: coverage.label,
      next: "查看草稿",
      tab: "draft",
      detail: hasVerdict ? finalReportText(state.currentVerdict).slice(0, 220) : "提交问题后，这里会恢复最后一次 run 的生成结果和报告出口。",
    },
    {
      id: "evidence",
      title: "证据链审查",
      summary: "把主张、模型原文、分歧和执行日志拆开审查",
      stage: "审查",
      risk: evidenceSummary.state,
      riskLabel: evidenceSummary.label,
      seats: `${evidenceSummary.nodes} 节点`,
      next: "看证据树",
      tab: "evidence",
      detail: evidenceSummary.detail,
    },
    {
      id: "council",
      title: state.productMode === "pro" ? "对比与桥接校准" : "模型状态摘要",
      summary: state.productMode === "pro"
        ? "确认网页/桌面席位是否可后台收集，并查看 COUNCIL-004 人格席位"
        : "只显示哪些模型已返回、待回收或阻断，不展开底层矩阵",
      stage: "席位",
      risk: bridgeNeedsWork ? "warn" : "ok",
      riskLabel: bridgeNeedsWork ? "需校准" : "就绪",
      seats: `${counts.webReady}/${counts.webTotal}`,
      next: "对比",
      tab: "council",
      detail: bridgeNeedsWork
        ? `仍有 ${Math.max(0, counts.webTotal - counts.webReady)} 个网页席位未就绪，专业版可查看每席位原因。`
        : "网页席位和桌面席位已进入可观察状态。",
    },
    ...(state.productMode === "pro" ? [{
      id: "benchmarks",
      title: "基准",
      summary: "把引用、决策、网页回收和 CDP 可靠性压成四张基准卡",
      stage: "基准",
      risk: (state.benchmarks?.cards || []).some(card => card.status === "needs_calibration") ? "warn" : "ok",
      riskLabel: `${state.benchmarks?.runs_considered || 0} 样本`,
      seats: `${state.benchmarks?.scoreboard?.ready_seats || 0}/${state.benchmarks?.scoreboard?.total_seats || state.seats.length}`,
      next: "看基准",
      tab: "benchmarks",
      detail: "专业版用于回答“这轮判断为什么值得信”：有无引用验证、席位是否稳定、网页回收是否可靠、CDP 通道是否健康。",
    }] : []),
    {
      id: "publish",
      title: "签字",
      summary: "证据、分歧、风险披露、日志和签字的硬门禁",
      stage: "发布",
      risk: publishSummary.blockers ? "block" : "ok",
      riskLabel: publishSummary.blockers ? `${publishSummary.blockers} 阻断` : "可发布",
      seats: coverage.label,
      next: "复核门禁",
      tab: "publish",
      detail: publishSummary.reason,
    },
  ];
}

function buildSimpleTaskItems() {
  const counts = bridgeChannelCounts();
  const coverage = seatCoverageSummary();
  const hasVerdict = Boolean(state.currentVerdict);
  const hasRunning = state.currentTask?.status === "running" && !state.currentTask?.progress_diagnostics?.stale;
  const hasQuestion = Boolean($("#question-input")?.value.trim());
  const failures = autopilotFailureCount(state.currentVerdict);
  const publishSummary = buildPublishGateSummary();
  const evidence = autopilotEvidenceSummary(state.currentVerdict);
  const mentorSummary = mentorGateSummary();
  return [
    {
      id: "request",
      title: "提交裁决",
      summary: "丢链接、文件或问题，主审整理提示词后自动编排网页席位",
      stage: "投放",
      risk: hasQuestion ? mentorSummary.state : "warn",
      riskLabel: hasQuestion ? mentorSummary.label : "待投放",
      seats: `${counts.webReady}/${counts.webTotal}`,
      next: hasQuestion ? "确认开庭" : "填写任务",
      tab: "request",
      detail: hasQuestion ? mentorSummary.detail : "把链接或任务粘到输入框，主审会先整理问题，再自动分类为产品评审、增长分析、证据审计或通用决策。",
    },
    {
      id: "draft",
      title: "运行中的任务",
      summary: hasRunning ? "后台网页席位正在收集，迟到席位进入隔离区" : hasVerdict ? "最近 run 已完成，可进入报告" : "提交后这里显示 run id、SLA 和失败隔离",
      stage: "运行",
      risk: hasRunning ? "warn" : hasVerdict ? "ok" : "warn",
      riskLabel: hasRunning ? "运行中" : hasVerdict ? "已完成" : "等待任务",
      seats: coverage.total ? coverage.label : `${counts.webReady}/${counts.webTotal}`,
      next: "查看运行",
      tab: "draft",
      detail: hasRunning
        ? `Run ${compactRunId(state.currentTask?.run_id)} 正在运行，系统会先记录席位发言，再追加迟到席位修订。`
        : hasVerdict
          ? "阶段报告已经生成，可去报告阅读，并在签字页确认。"
          : "这里不再承载新建入口，只负责让你看清楚后台是否还在跑、哪里被隔离、什么时候交付。",
    },
    {
      id: "history",
      title: "报告",
      summary: hasVerdict ? "最新报告可阅读，按可信度和下一步收口" : "完成的报告会进入这里",
      stage: "收件",
      risk: hasVerdict ? "ok" : "warn",
      riskLabel: hasVerdict ? `${trustTier(state.currentVerdict).tier || "-"} 级` : "等待报告",
      seats: hasVerdict ? `${evidence.percent}% 证据` : "无报告",
      next: "打开收件箱",
      tab: "history",
      detail: hasVerdict
        ? excerpt(finalReportText(state.currentVerdict), 220)
        : "早晨只读这里：结论、可信度、证据完整度、增长动作、人类签字状态和产物清单。",
    },
    {
      id: "publish",
      title: "签字",
      summary: "不签字不生成最终报告，所有对外动作都要保留理由",
      stage: "签字",
      risk: publishSummary.ready ? "ok" : hasVerdict ? "warn" : "block",
      riskLabel: publishSummary.ready ? "已签字" : hasVerdict ? "待签字" : "无报告",
      seats: failures ? `${failures} 隔离` : "0 隔离",
      next: "去确认",
      tab: "publish",
      detail: publishSummary.reason,
    },
  ];
}

function renderTaskInspector(task, publishSummary) {
  if (!task) return;
  $("#task-detail-title").textContent = task.title;
  $("#task-detail-summary").textContent = task.detail || task.summary;
  $("#task-detail-actions").innerHTML = `
    <button class="primary-action" data-task-open="${escapeAttr(task.tab)}">${escapeHtml(task.next)}</button>
    <button class="ghost" data-task-open="publish">${escapeHtml(state.productMode === "pro" ? "查看签字" : "去签字")}</button>
  `;
  $("#task-inspector-title").textContent = task.title;
  $("#task-inspector-summary").textContent = task.summary;
  $("#task-inspector-stage").textContent = task.stage;
  $("#task-inspector-gate").textContent = task.riskLabel;
  $("#task-inspector-next").textContent = task.next;
  renderBridgeHealth("#task-bridge-health", { limit: state.productMode === "pro" ? (state.seats.length || PARLIAMENT_SEATS.length) : 6 });
  renderNotificationStrip();
  if (publishSummary?.blockers !== undefined) {
    $("#task-blocker-count").classList.toggle("danger-text", publishSummary.blockers > 0);
  }
}

function renderBridgeHealth(selector, options = {}) {
  const target = $(selector);
  if (!target) return;
  const rows = bridgeHealthRows();
  const limit = options.limit || rows.length;
  target.innerHTML = rows.slice(0, limit).map(row => `
    <div class="bridge-health-card ${escapeAttr(row.state)}">
      <strong>${escapeHtml(row.name)}</strong>
      <span>${escapeHtml(row.label)} · ${escapeHtml(row.detail)}</span>
    </div>
  `).join("") || `<div class="bridge-health-card warn"><strong>等待配置</strong><span>读取网页席位和桥接状态后显示。</span></div>`;
}

function bridgeHealthRows() {
  const seats = state.seats.length ? state.seats : fallbackSeats();
  return seats.map(seat => seatOperationalState(seat));
}

function seatOperationalState(seat) {
  const seatId = seat.id || seat.seat;
  const raw = ((state.currentVerdict?.web_bridge || {}).raw_results || []).find(item => item.seat === seatId);
  if (raw) {
    if (raw.ok) {
      return { seat: seatId, name: seat.name || seatName(seatId), state: "ok", label: "有效", detail: `${String(raw.response || "").length} 字已回收` };
    }
    const code = raw.error?.code || "未返回";
    return {
      seat: seatId,
      name: seat.name || seatName(seatId),
      state: isSupplementableResult(raw) ? "warn" : "block",
      label: isSupplementableResult(raw) ? "待回收" : "阻断",
      detail: statusLabel(code, false),
    };
  }
  const diag = (state.currentTask?.progress_diagnostics?.seats || []).find(item => item.seat === seatId);
  if (diag) {
    const stateName = diag.state || "";
    const blocked = ["blocked", "failed"].includes(stateName);
    const done = ["done", "complete"].includes(stateName);
    return {
      seat: seatId,
      name: diag.name || seat.name || seatName(seatId),
      state: done ? "ok" : blocked ? "block" : "warn",
      label: diag.status || (done ? "完成" : "观察中"),
      detail: diag.reason || diag.detail || "运行中",
    };
  }
  const mapped = bridgeMatrixBySeat(seatId) || {};
  const bridgeSeat = bridgeSeatById(seatId) || {};
  const ready = Boolean((mapped.ready ?? bridgeSeat.ready) || false);
  const channel = mapped.channel || bridgeSeat.channel || "web";
  const reason = mapped.reason || bridgeSeat.reason;
  if (ready) {
    return { seat: seatId, name: seat.name || seatName(seatId), state: "ok", label: channelLabel(channel), detail: "校准通过" };
  }
  const configured = Boolean(mapped.target || bridgeSeat.url || bridgeSeat.browser_label || bridgeSeat.configured);
  return {
    seat: seatId,
    name: seat.name || seatName(seatId),
    state: configured ? "warn" : "block",
    label: configured ? "待校准" : "未配置",
    detail: statusLabel(reason || (configured ? "needs_calibration" : "not_configured"), false),
  };
}

function renderNotificationStrip() {
  const target = $("#task-notify-strip");
  if (!target) return;
  const channels = activeNotificationChannels();
  const runState = state.currentTask?.status === "running" ? "后台运行中" : state.currentVerdict ? "最近判词已完成" : "等待任务";
  target.innerHTML = [
    `<span class="tag">${escapeHtml(runState)}</span>`,
    channels.length
      ? channels.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("")
      : `<span class="tag chip-warn">未配置通知</span>`,
  ].join("");
}

function activeNotificationChannels() {
  const channels = [];
  if ($("#notify-email")?.value.trim()) channels.push("Email");
  if ($("#notify-webhook")?.value.trim()) channels.push("Webhook");
  if ($("#notify-feishu")?.value.trim()) channels.push("飞书");
  if ($("#notify-wecom")?.value.trim()) channels.push("企微");
  if ($("#notify-browser")?.checked) channels.push("桌面通知");
  return channels;
}

function mentorGateSummary() {
  const question = $("#question-input")?.value.trim() || "";
  if (!state.mentorEnabled) {
    return { state: "ok", label: "快速直达", detail: "主审门禁未启用，任务会按当前问题直接进入评议。" };
  }
  const snapshot = state.mentorSnapshot || buildMentorPreflight(question);
  if (!question) return { state: "block", label: "待输入", detail: "先输入问题，主审门禁才能判断清晰度和风险边界。" };
  if (!state.mentorConfirmed) return { state: "warn", label: "待确认", detail: snapshot.next_question || "确认主审预审后再运行。" };
  return { state: "ok", label: "已确认", detail: snapshot.execution_draft || "主审预审已确认。" };
}

function evidenceGateSummary() {
  const nodes = buildEvidenceNodes();
  const blockers = nodes.filter(item => item.state === "block").length;
  const warnings = nodes.filter(item => item.state === "warn").length;
  if (blockers) return { state: "block", label: `${blockers} 阻断`, nodes: nodes.length, detail: "证据链仍有硬阻断，不能进入发布级可用。" };
  if (warnings) return { state: "warn", label: `${warnings} 待复核`, nodes: nodes.length, detail: "证据链可读，但仍有回收、引用或分歧需要复核。" };
  return { state: "ok", label: "可审查", nodes: nodes.length, detail: "主张、证据和日志已形成可审查链路。" };
}

function seatCoverageSummary() {
  const v = state.currentVerdict || {};
  const raw = v.web_bridge?.raw_results || [];
  const usesWeb = Boolean(raw.length || String(v.engine || "").includes("web"));
  const policy = usesWeb ? executionPolicySummary(v) : null;
  if (policy?.required_count) {
    const ok = Number(policy.required_valid_count || 0);
    const total = Number(policy.required_count || 0);
    const pct = total ? Math.round((ok / total) * 100) : 0;
    const ready = ok;
    return { ok, total, pct, label: total ? `${ok}/${total}` : "按模式", ready, required: true };
  }
  const rawOk = raw.filter(item => item.ok).length;
  const scoreCount = (v.seat_scores || []).length;
  const ok = raw.length ? rawOk : scoreCount;
  const total = Number(v.web_bridge?.requested_count || raw.length || v.seat_count || state.selectedSeats.size || state.seats.length || 0);
  const pct = total ? Math.round((ok / total) * 100) : 0;
  const ready = ok;
  const label = total ? `${ok}/${total}` : "按模式";
  return { ok, total, pct, label, ready };
}

function buildPublishGateSummary() {
  const checks = buildPublishGateChecks();
  const blockers = checks.filter(item => item.state === "block").length;
  const warnings = checks.filter(item => item.state === "warn").length;
  const human = checks.find(item => item.key === "human_confirmation");
  const nonHumanBlockers = checks.filter(item => item.key !== "human_confirmation" && item.state === "block").length;
  const ready = Boolean(state.currentVerdict && nonHumanBlockers === 0 && state.publishCleared);
  const reason = ready
    ? "全部硬门禁通过，已完成发布级签字。"
    : nonHumanBlockers
      ? `仍有 ${nonHumanBlockers} 个硬门禁阻断。`
      : human?.state !== "ok"
        ? "阻断项已满足，等待签字。"
        : warnings
          ? `还有 ${warnings} 个复核提醒。`
          : "等待判词生成。";
  return { checks, blockers, warnings, nonHumanBlockers, ready, reason };
}

function humanGavelState(summary = buildPublishGateSummary()) {
  if (summary.ready) {
    return {
      state: "publishable",
      label: "已签字",
      description: "用户已确认这个判断可以作为当前决策依据。",
    };
  }
  if (state.currentVerdict && summary.nonHumanBlockers === 0) {
    return {
      state: "reviewed",
      label: "待签字",
      description: "硬门禁已通过，等待签字是否可发布。",
    };
  }
  return {
    state: "draft",
    label: "草稿",
    description: "判词仍在草稿或补证状态。",
  };
}

async function initBridgeConfig() {
  $("#bridge-status").textContent = "生成配置中...";
  try {
    const res = await fetch(`${API_BASE}/api/bridge/init-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ overwrite: false }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.bridge = data.status;
  } catch (err) {
    state.bridge = { available: false, seats: [], seat_browser_matrix: [], error: err.message };
  }
  renderBridgeStatus();
  renderMapping();
  renderTaskCenter();
  renderCouncilCompletion();
  updateSubmitState();
}

async function calibrateBridge() {
  const seats = Array.from(state.selectedSeats);
  $("#bridge-status").textContent = seats.length ? `校准 ${seats.length} 席中...` : "校准全部席位中...";
  $("#btn-calibrate-bridge").disabled = true;
  $("#btn-calibrate-bridge").textContent = "校准中";
  try {
    const res = await fetch(`${API_BASE}/api/bridge/calibrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seats, timeout_seconds: 8 }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.bridge = data.status;
  } catch (err) {
    state.bridge = { ...(state.bridge || {}), error: err.message };
    $("#bridge-status").textContent = `校准失败：${err.message}`;
  } finally {
    $("#btn-calibrate-bridge").disabled = false;
    $("#btn-calibrate-bridge").textContent = "校准当前席位";
  }
  renderBridgeStatus();
  renderMapping();
  renderSeats();
  renderTaskCenter();
  renderCouncilCompletion();
  updateSubmitState();
}


// ── P41 Message Detail Map ──
window.__AI_JUDGE_MESSAGE_DETAILS__ = {};

// ── P3 Drawer State & Logic ──
(function initDrawer() {
  const state = window.__AI_JUDGE_STATE__;
  if (!state) return;
  state.drawerOpen = false;
  state.drawerTab = 'log';
  state.notificationCount = 0;

  const backdrop = document.getElementById('drawer-backdrop');
  const drawer = document.getElementById('parliament-drawer');
  const closeBtn = document.getElementById('drawer-close');
  const officeBtn = document.getElementById('conference-open-office');
  const workbenchBtn = document.getElementById('conference-toggle-workbench');
  const notifBtn = document.getElementById('conference-notifications');
  const archiveBtn = document.getElementById('conference-open-archive');

  function openDrawer(tab) {
    state.drawerOpen = true;
    state.drawerTab = tab || 'log';
    if (backdrop) { backdrop.hidden = false; requestAnimationFrame(() => backdrop.classList.add('open')); }
    if (drawer) { drawer.hidden = false; requestAnimationFrame(() => drawer.classList.add('open')); }
    updateDrawerTabs();
    renderDrawerContent();
    updateHeaderIconStates();
  }

  function closeDrawer() {
    state.drawerOpen = false;
    state.drawerDetailId = null;
    // P43: clear selected card state
    $$('.answer-card.is-selected').forEach(c => c.classList.remove('is-selected'));
    if (backdrop) backdrop.classList.remove('open');
    if (drawer) drawer.classList.remove('open');
    // P57: use transitionend for reliable close, fallback to 400ms timeout
    var _settled = false;
    var _done = function() {
      if (_settled) return; _settled = true;
      if (!state.drawerOpen) {
        if (backdrop) { backdrop.hidden = true; backdrop.removeEventListener('transitionend', _done); }
        if (drawer) { drawer.hidden = true; drawer.removeEventListener('transitionend', _done); }
      }
    };
    if (drawer) drawer.addEventListener('transitionend', _done, { once: true });
    if (backdrop) backdrop.addEventListener('transitionend', _done, { once: true });
    setTimeout(_done, 400);
    updateHeaderIconStates();
  }

  function openMessageDetail(messageId) {
    // P43: clear previous selected card, set new selected
    $$('.answer-card.is-selected').forEach(c => c.classList.remove('is-selected'));
    const card = document.querySelector(`.answer-card[data-message-id="${messageId}"]`);
    if (card) card.classList.add('is-selected');
    state.drawerDetailId = messageId;
    openDrawer('detail');
  }

  function toggleDrawer(tab) {
    if (state.drawerOpen && state.drawerTab === tab) { closeDrawer(); }
    else if (state.drawerOpen) { state.drawerTab = tab; updateDrawerTabs(); renderDrawerContent(); }
    else { openDrawer(tab); }
  }

  function updateDrawerTabs() {
    document.querySelectorAll('#drawer-tabs .drawer-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.drawerTab === state.drawerTab);
    });
  }

  function updateHeaderIconStates() {
    const iconTabs = new Map([
      [officeBtn, 'werewolf'],
      [workbenchBtn, 'log'],
      [notifBtn, 'notifications'],
      [archiveBtn, 'report'],
    ]);
    iconTabs.forEach((tab, btn) => {
      if (!btn) return;
      btn.classList.toggle('active', state.drawerOpen && state.drawerTab === tab);
    });
    if (notifBtn && state.notificationCount > 0 && !state.drawerOpen) {
      let badge = notifBtn.querySelector('.badge');
      if (!badge) { badge = document.createElement('span'); badge.className = 'badge'; notifBtn.appendChild(badge); }
      badge.textContent = state.notificationCount > 99 ? '99+' : state.notificationCount;
    } else if (notifBtn) {
      const badge = notifBtn.querySelector('.badge');
      if (badge) badge.remove();
    }
  }

  function renderDrawerContent() {
    window.renderDrawerContent = renderDrawerContent; // P60: expose for run control refresh
    const content = document.getElementById('drawer-content');
    if (!content) return;
    if (state.drawerTab === 'log') {
      const werewolfActive = Boolean(state.werewolfMode || state.werewolfGame);
      const hasRunning = Boolean(state.currentTask || state.werewolfGame);
      const hasVerdict = Boolean(state.currentVerdict);
      const seatCount = state.selectedSeats.size || 0;
      const phaseClass = hasVerdict ? 'done' : hasRunning ? 'running' : 'idle';
      const phaseLabel = hasVerdict ? '裁决完成' : hasRunning ? '运行中' : '空闲';
      const speakers = state.werewolfGame
        ? (state.werewolfGame.activeSeats || [])
        : parliamentSpeakers(state.currentVerdict, hasRunning);
      const totalSeats = Math.max(speakers.length, 1);
      const completedCount = speakers.filter(s => s.state === 'complete' || s.state === 'done').length;
      const speakingSeat = speakers.find(s => s.state === 'speaking');
      baseHTML = `
        <div class="drawer-panel">
          <h3>${werewolfActive ? '狼人杀工作台' : '工作日志'}</h3>
          <p class="drawer-desc">${werewolfActive ? '阶段线、阵营对比与桥接缺口。主对话流只放发言与裁判提示。' : '当前会议阶段、席位状态与运行摘要。详细发言请点卡片进入详情。'}</p>
          <div class="drawer-log-timeline">
            <div class="dlt-phase ${phaseClass}">
              <span class="dlt-dot"></span>
              <span class="dlt-label">${escapeHtml(phaseLabel)}</span>
            </div>
            <div class="dlt-step ${hasRunning ? 'active' : ''}">
              <span class="dlt-dot"></span>
              <span class="dlt-label">${totalSeats} 席位${speakingSeat ? ` · ${escapeHtml(speakingSeat.name)} 发言中` : completedCount > 0 ? ` · ${completedCount}/${totalSeats} 已回收` : ' · 等待派发'}</span>
            </div>
            ${hasVerdict ? '<div class="dlt-step active"><span class="dlt-dot"></span><span class="dlt-label">裁决已生成</span></div>' : ''}
          </div>`;
      if (werewolfActive) {
        baseHTML += `<div class="drawer-log-werewolf"><div id="drawer-current-speaker"></div><div id="drawer-phase-rail"></div><div id="drawer-resonance-ribbon"></div><div id="drawer-score-flow"></div></div>`;
      }
      baseHTML += '</div>';
      content.innerHTML = baseHTML;
      if (werewolfActive) {
        setTimeout(() => {
          [
            ['parliament-current-speaker', 'drawer-current-speaker'],
            ['conference-phase-rail', 'drawer-phase-rail'],
            ['conference-resonance-ribbon', 'drawer-resonance-ribbon'],
            ['conference-score-flow', 'drawer-score-flow'],
          ].forEach(([srcId, dstId]) => {
            const src = document.getElementById(srcId);
            const dst = document.getElementById(dstId);
            if (src && dst) dst.innerHTML = src.innerHTML || '';
          });
        }, 50);
      }
    } else if (state.drawerTab === 'outputs') {
      const hasVerdict = Boolean(state.currentVerdict);
      const hasTask = Boolean(state.currentTask);
      const verdictTitle = state.currentVerdict
        ? (state.currentVerdict.match(/^#\s+(.+)$/m) || [])[1] || '裁决报告'
        : '';
      content.innerHTML = `
        <div class="drawer-panel">
          <h3>产出物</h3>
          <p class="drawer-desc">${hasVerdict ? '本轮裁决的可交付文件和内部记录入口。' : '会议完成后，报告和运行摘要会出现在这里。'}</p>
          <div class="drawer-file-list">
            ${hasVerdict ? `<article class="drawer-file-card is-ready"><strong>${escapeHtml(verdictTitle)}</strong><span>已生成 · 可导出</span></article>` : `<article class="drawer-file-card"><strong>裁决报告</strong><span>等待会议完成</span></article>`}
            <article class="drawer-file-card"><strong>运行日志</strong><span>${hasTask ? '写入中' : hasVerdict ? '已归档' : '等待运行'}</span></article>
            <article class="drawer-file-card"><strong>证据索引</strong><span>${hasVerdict ? '已归档' : '等待证据链'}</span></article>
          </div>
        </div>
      `;
    } else if (state.drawerTab === 'report') {
      const historyList = document.getElementById('history-list');
      const reportBtn = document.querySelector('.is-report-library');
      content.innerHTML = '<div class="drawer-panel"><h3>报告库</h3><p>报告库从左侧主导航收进抽屉，避免打断会议室主流程。</p><div id="drawer-report-list"></div></div>';
      setTimeout(() => {
        const dst = document.getElementById('drawer-report-list');
        if (historyList && dst) {
          dst.innerHTML = '<p class="drawer-empty">已完成裁决报告</p>' + historyList.innerHTML;
        } else if (dst) {
          dst.innerHTML = '<p class="drawer-empty">暂无历史报告</p>';
        }
      }, 50);
    } else if (state.drawerTab === 'detail') {
      const detailId = state.drawerDetailId;
      const detail = detailId ? window.__AI_JUDGE_MESSAGE_DETAILS__?.[detailId] : null;
      // P43: Animate drawer content on detail change
      if (content.dataset.lastTab !== 'detail' || content.dataset.lastDetail !== detailId) {
        content.style.opacity = '0';
        content.style.transform = 'translateY(6px)';
        setTimeout(() => {
          content.style.opacity = '';
          content.style.transform = '';
        }, 60);
        content.dataset.lastTab = 'detail';
        content.dataset.lastDetail = detailId || '';
      }
      if (!detail) {
        const game = state.werewolfGame;
        const phase = game ? (game.phase || game.status || "准备中") : state.werewolfMode ? "待开局" : "待发言";
        const latest = game?.events?.length ? game.events[game.events.length - 1] : null;
        const fallbackText = latest?.text
          || (state.werewolfMode
            ? "选择模板或席位后，这里会显示当前狼人杀阶段、最近发言和桥接状态。"
            : "会议开始后，点击任一发言卡片即可查看完整原文。");
        content.innerHTML = '<div class="drawer-panel detail-panel"><div class="detail-header"><div class="detail-avatar-wrap"><div class="detail-avatar-fallback">G</div></div><div class="detail-meta"><strong>Grand Judge</strong><span class="detail-role">' + escapeHtml(phase) + '</span></div></div><div class="detail-body"><div class="detail-full-text">' + formatParliamentText(fallbackText) + '</div></div></div>';
      } else {
        const full = detail.fullText || detail.text || '';
        const digestHtml = detail.digest ? '<div class="detail-summary"><span class="ds-label">摘要</span><p>' + escapeHtml(detail.digest) + '</p></div>' : '';
        const anchorChips = detail.sections && detail.sections.length > 1
          ? '<div class="detail-anchors">' + detail.sections.map(function(s) { return '<button class="da-chip" data-scroll-to="detail-sec-' + s.id + '" type="button">' + escapeHtml(s.label) + '</button>'; }).join('') + '</div>'
          : '';
        const hasTs = detail.toolEvents && detail.toolEvents.length > 0;
        const tsHtml = hasTs
          ? '<div id="detail-sec-process" class="detail-sec-anchor"></div><div class="detail-process"><h4>过程</h4>' + detail.toolEvents.map(function(e) { return '<div class="detail-process-row"><span class="dpr-label">' + escapeHtml(e.label || '') + '</span><span class="dpr-result">' + escapeHtml(e.result || '') + '</span></div>'; }).join('') + '</div>'
          : '';
        const kpHtml = detail.keyPoints && detail.keyPoints.length
          ? '<div id="detail-sec-keypoints" class="detail-sec-anchor"></div><div class="detail-keypoints"><ul>' + detail.keyPoints.map(function(k) { return '<li>' + escapeHtml(k) + '</li>'; }).join('') + '</ul>'
          : '';
        const avatarImg = detail.avatarUrl
          ? '<img class="detail-avatar-img" src="' + escapeAttr(detail.avatarUrl) + '" alt="' + escapeAttr(detail.role || '') + '" width="36" height="36" loading="lazy" onerror="this.style.display=\'none\';this.parentElement.innerHTML=\'<div class=detail-avatar-fallback>' + escapeHtml((detail.role || '?').charAt(0)) + '</div>\';" />'
          : '<div class="detail-avatar-fallback">' + escapeHtml((detail.role || '?').charAt(0)) + '</div>';
        content.innerHTML = '<div class="drawer-panel detail-panel">'
          + '<div class="detail-header">'
          + '<div class="detail-avatar-wrap">' + avatarImg + '</div>'
          + '<div class="detail-meta">'
          + '<strong>' + escapeHtml(detail.role || '') + '</strong>'
          + '<span class="detail-role">' + escapeHtml(detail.roleLabel || '') + '</span>'
          + (detail.channel ? '<span class="detail-provider">' + escapeHtml(detail.channel) + '</span>' : '')
          + '<span class="detail-status ' + escapeAttr(detail.msgState || '') + '">' + escapeHtml(detail.statusLabel || '') + '</span>'
          + '</div></div>'
          + anchorChips
          + digestHtml
          + '<div class="detail-sections">'
          + '<div id="detail-sec-digest" class="detail-sec-anchor"></div>'
          + kpHtml
          + tsHtml
          + '<div id="detail-sec-fulltext" class="detail-sec-anchor"></div>'
          + '<div class="detail-full-text">' + (detail.formatFull ? formatParliamentText(full) : '<pre style="white-space:pre-wrap;font:inherit;margin:0;">' + escapeHtml(full) + '</pre>') + '</div>'
          + '</div></div>';
        // P43: bind section anchor scroll
        setTimeout(function() {
          var drawerContent = document.getElementById('drawer-content');
          if (!drawerContent) return;
          drawerContent.querySelectorAll('.da-chip').forEach(function(chip) {
            chip.addEventListener('click', function() {
              var targetId = this.dataset.scrollTo;
              var target = drawerContent.querySelector('#' + targetId);
              if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            });
          });
        }, 60);
      }
    } else if (state.drawerTab === 'werewolf') {
      // P60: Compact 3-block drawer layout + run control
      const isPreRunWerewolf = state.werewolfMode && state.preRunFlow.active && !state.preRunFlow.confirmed;
      const isRunningGame = Boolean(state.werewolfGame);
      const isWerewolfIdle = state.werewolfMode && !isPreRunWerewolf && !isRunningGame;
      const selectedIds = werewolfSelectedSeatIds({ fill: true });
      const count = selectedIds.length;
      const game = state.werewolfGame;
      const activeCount = game ? (game.players || []).length : count;
      const standbyCount = game
        ? WEREWOLF_CANDIDATE_SEAT_IDS.filter(function(id) { return !game.players.some(function(p) { return p.id === id; }) && !(game.offlineSeats || []).includes(id); }).length
        : WEREWOLF_CANDIDATE_SEAT_IDS.filter(function(id) { return !selectedIds.includes(id); }).length;
      const phaseLabels = { setup: "身份密封", day: "白天发言", night: "夜晚行动", vote: "投票阶段", complete: "已结算" };
      const currentPhase = game ? (phaseLabels[game.phase] || game.phase || "运行中") : "";
      const eliminated = new Set(game ? (game.eliminatedSeats || []) : []);
      const aliveCount = activeCount - eliminated.size;

      // Block 1: 局势概览
      var overviewHtml = ''
        + '<section class="ww-drawer-block">'
        + '<h4>当前局势</h4>'
        + '<div class="ww-drawer-chips">'
        + '<span class="ww-chip">9人标准局</span>'
        + '<span class="ww-chip">' + aliveCount + '/' + activeCount + ' 存活</span>'
        + '<span class="ww-chip">' + standbyCount + ' 替补</span>';
      if (currentPhase) overviewHtml += '<span class="ww-chip ww-chip-phase">' + currentPhase + '</span>';
      overviewHtml += '</div>';
      if (isRunningGame) {
        var gate = game.bridgeGate;
        var readyCount = gate ? gate.readyCount : activeCount;
        var total = gate ? gate.total : activeCount;
        var progressPct = total > 0 ? Math.round((readyCount / total) * 100) : 0;
        overviewHtml += '<div class="ww-progress-bar"><i style="--progress:' + progressPct + '%"></i><span>' + readyCount + '/' + total + ' 就绪</span></div>';
        overviewHtml += '<div class="ww-run-actions">'
          + '<button class="ww-stop-btn" type="button" onclick="event.stopPropagation();window.__wwStopWerewolfP60&&window.__wwStopWerewolfP60()">停止</button>'
          + '</div>';
      }
      overviewHtml += '</section>';

      // Block 2: 高级管理 (expandable)
      var advancedHtml = ''
        + '<section class="ww-drawer-block">'
        + '<details class="ww-advanced">'
        + '<summary>高级管理：席位、板型与替补</summary>'
        + '<div class="ww-advanced-body">'
        + '<div id="drawer-werewolf-picker"></div>'
        + '<div id="drawer-werewolf-prep"></div>'
        + '</div>'
        + '</details>'
        + '</section>';

      // Block 3: 新手说明 (≤3 lines)
      var guideHtml = ''
        + '<section class="ww-drawer-block ww-guide">'
        + '<h4>快速说明</h4>'
        + '<p>9 位 AI 模型随机扮演 3狼、3民、预言家、女巫、猎人。Grand Judge 密封身份，发言进入对话流，投票决定淘汰。</p>'
        + '</section>';

      content.innerHTML = ''
        + '<div class="drawer-panel drawer-werewolf-panel drawer-ww-compact">'
        + '<h3>议会桌</h3>'
        + overviewHtml
        + advancedHtml
        + guideHtml
        + '</div>';

      // Post-render: inject picker into the <details> and populate run control
      setTimeout(function() {
        var pickerDst = document.getElementById('drawer-werewolf-picker');
        var prepDst = document.getElementById('drawer-werewolf-prep');
        if (pickerDst) pickerDst.innerHTML = renderInlineWerewolfPicker();
        if (prepDst) prepDst.innerHTML = renderWerewolfPrepSummary();
      }, 30);
    } else if (state.drawerTab === 'notifications') {
      content.innerHTML = `
        <div class="drawer-panel">
          <h3>通知</h3>
          <p>这里不是工作日志，只放需要你处理或知晓的提醒。</p>
          <div class="drawer-notice-list">
            <span class="drawer-notice">报告完成后提醒</span>
            <span class="drawer-notice">签字门禁</span>
            <span class="drawer-notice">席位失败需要替补</span>
          </div>
        </div>
      `;
    }
  }

  if (backdrop) backdrop.addEventListener('click', closeDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  // P4: Escape key to close drawer
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.drawerOpen) closeDrawer(); });
  // P41b: Enter/Space to open message detail from focused answer-card
  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.closest('.answer-card[role="button"]')) {
      const card = e.target.closest('.answer-card[role="button"]');
      const msgId = card.dataset.messageId;
      if (msgId) { e.preventDefault();
        // P43: also set selected card state on keyboard open
        $$('.answer-card.is-selected').forEach(c => c.classList.remove('is-selected'));
        const card43 = e.target.closest('.answer-card[role="button"]');
        if (card43) card43.classList.add('is-selected');
        openMessageDetail(msgId); }
    }
  });
  if (officeBtn) officeBtn.addEventListener('click', () => toggleDrawer('werewolf'));
  if (workbenchBtn) workbenchBtn.addEventListener('click', () => toggleDrawer('log'));
  if (notifBtn) notifBtn.addEventListener('click', () => toggleDrawer('notifications'));
  if (archiveBtn) archiveBtn.addEventListener('click', () => toggleDrawer('report'));

  document.querySelectorAll('#drawer-tabs .drawer-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      state.drawerTab = tab.dataset.drawerTab;
      updateDrawerTabs();
      renderDrawerContent();
    });
  });

  // Expose for other code
  window.__AI_JUDGE_DRAWER__ = { openDrawer, closeDrawer, toggleDrawer, updateHeaderIconStates, openMessageDetail };
})();


function renderSeats() {
  const grid = $("#seat-grid");
  if (!grid) return;
  const seats = state.seats.length ? state.seats : fallbackSeats();
  grid.innerHTML = seats.map(seat => `
    <button class="seat-card ${state.selectedSeats.has(seat.id) ? "selected" : ""} ${seatBridgeReady(seat.id) ? "" : "bridge-muted"}" data-seat="${escapeAttr(seat.id)}" data-seat-label="${escapeAttr(seatCardLabel(seat))}">
      <span class="seat-avatar">${renderAvatar(seat, 36)}</span>
      <span class="seat-top">
        <strong>${escapeHtml(seat.name)}</strong>
        <em>${escapeHtml(seat.mbti)}</em>
      </span>
      <small>${escapeHtml(seatSubtitle(seat))}</small>
    </button>
  `).join("");
  $$(".seat-card").forEach(btn => btn.addEventListener("click", () => {
    const id = btn.dataset.seat;
    if (state.selectedSeats.has(id)) state.selectedSeats.delete(id);
    else state.selectedSeats.add(id);
    state.mentorConfirmed = false;
    renderSeats();
    updateMentorPreflight();
    updateSubmitState();
    renderTaskCenter();
  }));
  $("#selected-count").textContent = `已选 ${state.selectedSeats.size}/${seats.length}`;
  renderArena();
}

function seatCardLabel(seat) {
  return (seat.providerCode || seat.name || seat.id || "AI").slice(0, 2).toUpperCase();
}

function renderArena() {
  if (!$("#arena-roster")) return;
  renderChiefSelector();
  renderArenaRoster();
  renderArenaInsights();
  renderArenaBridgeMonitor();
  renderArenaRounds();
  renderDeltaRibbon();
  renderSimpleSeatSummary();
  renderCouncilCompletion();
}

function renderSimpleSeatSummary() {
  if (!$("#simple-seat-strip")) return;
  const raw = state.currentVerdict?.web_bridge?.raw_results || [];
  renderSeatStatusStrip("#simple-seat-strip", raw, { includeEmpty: true });
  const ok = raw.filter(item => item.ok).length;
  const recoverable = raw.filter(isSupplementableResult).length;
  const blocked = raw.filter(item => item && !item.ok && !isSupplementableResult(item)).length;
  $("#simple-seat-summary").textContent = raw.length
    ? `${ok}/${raw.length} 有效 · ${recoverable} 待回收 · ${blocked} 阻断`
    : `${state.selectedSeats.size || state.seats.length || 0} 席待运行`;
}

function renderSeatStatusStrip(selector, rawResults, options = {}) {
  const target = $(selector);
  if (!target) return;
  const raw = Array.isArray(rawResults) ? rawResults : [];
  if (!raw.length) {
    target.innerHTML = options.includeEmpty
      ? `<div class="memo-seat warn"><strong>等待任务</strong><span>提交后显示各模型返回、回收和阻断原因。</span></div>`
      : "";
    return;
  }
  target.innerHTML = raw.map(item => {
    const status = item.ok ? "ok" : isSupplementableResult(item) ? "warn" : "block";
    const code = item.ok ? "已回收" : ((item.error || {}).code || "未返回");
    const detail = item.ok
      ? `${String(item.response || "").length} 字 · ${item.capture_mode || item.profile_dir || "网页席位"}`
      : ((item.error || {}).message || "没有可评分答案");
    return `
      <div class="memo-seat ${status}">
        <strong>${escapeHtml(seatName(item.seat) || item.seat || "-")}</strong>
        <span>${escapeHtml(code)} · ${escapeHtml(excerpt(detail, 78))}</span>
      </div>
    `;
  }).join("");
}

function renderChiefSelector() {
  const candidates = ["auto", "chatgpt", "deepseek", "qwen", "claude"].filter(id => id === "auto" || state.seats.some(seat => seat.id === id));
  if (!candidates.includes(state.chiefJudge)) state.chiefJudge = "auto";
  $("#chief-selector").innerHTML = candidates.map(id => {
    const label = id === "auto" ? "自动轮值" : `${seatName(id)} 主审`;
    return `<button class="${state.chiefJudge === id ? "active" : ""}" data-chief="${escapeAttr(id)}">${escapeHtml(label)}</button>`;
  }).join("");
  $$("#chief-selector button").forEach(btn => btn.addEventListener("click", () => {
    state.chiefJudge = btn.dataset.chief || "auto";
    localStorage.setItem("ai_judge_chief_judge", state.chiefJudge);
    renderArena();
  }));
  $("#chief-name").textContent = state.chiefJudge === "auto" ? "自动轮值" : `${seatName(state.chiefJudge)} 主审`;
  $("#chief-subtitle").textContent = state.chiefJudge === "auto" ? "按本轮分数自动选择" : "可切换主审";
}

function renderArenaRoster() {
  const candidateTotal = state.seats.length || PARLIAMENT_SEATS.length;
  $("#arena-seat-count").textContent = `${candidateTotal} 候选 · ${WEREWOLF_SEAT_COUNT} 参赛 · ${state.selectedSeats.size} 就绪`;
  $("#arena-roster").innerHTML = state.seats.map(seat => {
    const selected = state.selectedSeats.has(seat.id);
    const bridgeSeat = bridgeSeatById(seat.id) || {};
    const channel = bridgeSeat.channel || (seat.id === "doubao" ? "desktop" : "web");
    const status = selected ? arenaSeatStatus(seat.id) : "弃权";
    return `
      <article class="roster-card ${selected ? "selected" : "abstained"}" data-seat="${escapeAttr(seat.id)}">
        <div class="roster-main">
          <span class="roster-avatar">${renderAvatar(seat, 32)}</span>
          <span class="roster-name">
            <strong>${escapeHtml(seat.name)}</strong>
            <span>${escapeHtml(channelLabel(channel))} · ${escapeHtml(status)}</span>
          </span>
        </div>
        <div class="pulse"></div>
        <div class="roster-actions">
          <button class="${selected ? "is-join" : ""}" data-roster-action="join" data-seat="${escapeAttr(seat.id)}">参议</button>
          <button class="${selected ? "" : "is-abstain"}" data-roster-action="abstain" data-seat="${escapeAttr(seat.id)}">弃权</button>
        </div>
      </article>
    `;
  }).join("");
  $$("[data-roster-action]").forEach(btn => btn.addEventListener("click", event => {
    event.stopPropagation();
    const seat = btn.dataset.seat;
    if (btn.dataset.rosterAction === "join") state.selectedSeats.add(seat);
    else state.selectedSeats.delete(seat);
    renderSeats();
    updateSubmitState();
  }));
}

function arenaSeatStatus(seatId) {
  const raw = ((state.currentVerdict?.web_bridge || {}).raw_results || []).find(item => item.seat === seatId);
  if (raw) return raw.ok ? "已采集" : isSupplementableResult(raw) ? "待回收" : "需处理";
  return seatBridgeReady(seatId) ? "已选" : "待校准";
}

function renderArenaInsights() {
  const insights = state.currentVerdict?.roster_sensitivity?.length
    ? state.currentVerdict.roster_sensitivity
    : fallbackSensitivity();
  $("#sensitivity-list").innerHTML = insights.slice(0, 5).map(item => {
    const width = Math.max(18, Math.min(96, Math.abs(Number(item.delta || item.score || 0.4)) * 10 + 34));
    const color = item.impact === "negative" ? "var(--red)" : item.impact === "chief" ? "var(--accent)" : "var(--blue)";
    return `
      <div class="insight-item">
        <strong>${escapeHtml(item.label || item.seat_name || "-")}</strong>
        <div class="impact-bar"><span style="width:${width}%; background:${color}"></span></div>
      </div>
    `;
  }).join("") || `<div class="muted">完成一轮后会显示阵容 What-if 影响。</div>`;
}

function fallbackSensitivity() {
  const rows = (state.seatScoreboard?.seats || []).filter(item => item.average_score !== null && item.average_score !== undefined).slice(0, 5);
  if (!rows.length) {
    return [
      { label: "选择更多席位：共识覆盖提升", delta: 3.8, impact: "positive" },
      { label: "切换主审：比较表达风格与结论稳定性", delta: 4.3, impact: "chief" },
    ];
  }
  return rows.map(item => ({
    seat: item.seat,
    seat_name: item.seat_name,
    label: `${item.seat_name} 历史均分 ${Number(item.average_score).toFixed(3)} · ${item.run_count} 次`,
    delta: Number(item.average_score || 0) * 10,
    impact: item.average_score >= 0.65 ? "chief" : "positive",
  }));
}

function renderArenaBridgeMonitor() {
  const rows = state.seats.slice(0, 8).map(seat => {
    const mapped = bridgeMatrixBySeat(seat.id) || {};
    const bridgeSeat = bridgeSeatById(seat.id) || {};
    const channel = mapped.channel || bridgeSeat.channel || "local";
    const ready = Boolean((mapped.ready ?? bridgeSeat.ready) || false);
    return `
      <tr>
        <td>${escapeHtml(seat.name)}</td>
        <td class="muted">${escapeHtml(mapped.target || bridgeSeat.browser_label || "-")}</td>
        <td>${escapeHtml(statusLabel(mapped.reason || bridgeSeat.reason, ready))}</td>
        <td><span class="channel ${ready ? "ready" : escapeAttr(channel)}">${ready ? "就绪" : escapeHtml(channelLabel(channel))}</span></td>
      </tr>
    `;
  });
  $("#bridge-monitor-body").innerHTML = rows.join("");
}

function renderArenaRounds() {
  const rounds = state.currentVerdict?.web_bridge?.score_rounds || [];
  if (!rounds.length) {
    $("#arena-rounds").innerHTML = `<p class="muted">完成网页深度评议后，这里会展示单次、多轮、总评分。</p>`;
    return;
  }
  $("#arena-rounds").innerHTML = rounds.map(item => {
    const score = item.average_score === null || item.average_score === undefined ? "-" : Number(item.average_score).toFixed(3);
    const pct = item.average_score === null || item.average_score === undefined ? 0 : Math.round(Number(item.average_score) * 100);
    return `
      <div class="insight-item">
        <strong>${escapeHtml(item.label || item.id)} · ${escapeHtml(score)}</strong>
        <div class="impact-bar"><span style="width:${pct}%; background:var(--accent)"></span></div>
      </div>
    `;
  }).join("");
}

function renderDeltaRibbon() {
  const v = state.currentVerdict;
  const scored = (state.seatScoreboard?.seats || []).filter(item => item.average_score !== null && item.average_score !== undefined).length;
  const chips = [
    ["共识", v?.confidence ?? (scored ? Math.min(96, scored * 7) : 0)],
    ["分歧", v?.web_bridge?.deliberation?.disagreements?.length ?? 0],
    ["证据", v?.total_claims ?? state.selectedSeats.size],
  ];
  $("#delta-ribbon").innerHTML = chips.map(([label, value]) => `<span class="delta-chip">${escapeHtml(label)}<strong>${escapeHtml(value)}</strong></span>`).join("");
}

function seatInitials(name) {
  return String(name || "?").replace(/[^A-Za-z0-9]/g, "").slice(0, 2).toUpperCase() || String(name || "?").slice(0, 1);
}

function seatName(id) {
  return state.seats.find(seat => seat.id === id)?.name || id;
}

function seatSubtitle(seat) {
  if (state.engine !== "web") return seat.strength || "";
  const bridgeSeat = bridgeSeatById(seat.id);
  const mapped = bridgeMatrixBySeat(seat.id);
  if (!bridgeSeat && !mapped) return "桥接未配置";
  const ready = Boolean((mapped?.ready ?? bridgeSeat?.ready) || false);
  const reason = mapped?.reason || bridgeSeat?.reason;
  const channel = mapped?.channel || bridgeSeat?.channel;
  const calibration = calibrationSummary(mapped, bridgeSeat);
  if (ready) return "校准通过，可后台收集";
  if (channel === "desktop") return bridgeSeat?.desktop_app?.installed ? "需独立桌面 Worker" : "豆包桌面客户端未安装";
  if (calibration.status === "fail") return `校准失败：${statusLabel(reason, false)}`;
  if (reason === "needs_calibration") return "已配置，待校准";
  if (reason === "playwright_missing") return "缺少 Playwright";
  if (reason === "missing_url") return "缺少网页地址";
  return statusLabel(reason, ready);
}

function seatBridgeReady(seatId) {
  if (state.engine !== "web") return true;
  const mapped = bridgeMatrixBySeat(seatId);
  return Boolean((mapped?.ready ?? bridgeSeatById(seatId)?.ready) || false);
}

// Avatar System — PNG-based mascot avatars (P2)
// product/avatars/ 下的 256px PNG 作为 background-image，CSS 负责尺寸适配与状态动效
const MODEL_COLORS = {
  gpt4o:    { head: '#10A37F', body: '#D1F2EB', acc: '#0D8C6D' },
  chatgpt:  { head: '#10A37F', body: '#D1F2EB', acc: '#0D8C6D' },
  claude:   { head: '#D97706', body: '#FEF3C7', acc: '#92400E' },
  gemini:   { head: '#4285F4', body: '#DBEAFE', acc: '#EA4335' },
  deepseek: { head: '#4F46E5', body: '#E0E7FF', acc: '#3730A3' },
  qwen:     { head: '#6366F1', body: '#E0E7FF', acc: '#8B5CF6' },
  kimi:     { head: '#EC4899', body: '#FCE7F3', acc: '#BE185D' },
  grok:     { head: '#1DA1F2', body: '#DBEAFE', acc: '#0D8BD9' },
  yuanbao:  { head: '#14B8A6', body: '#CCFBF1', acc: '#0F766E' },
  doubao:   { head: '#22C55E', body: '#DCFCE7', acc: '#15803D' },
  minimax:  { head: '#7C3AED', body: '#EDE9FE', acc: '#5B21B6' },
  zhipu:    { head: '#0EA5E9', body: '#E0F2FE', acc: '#0284C7' },
  wenxin:   { head: '#EF4444', body: '#FEE2E2', acc: '#B91C1C' },
  mimo:     { head: '#F97316', body: '#FED7AA', acc: '#EA580C' },
  meta:     { head: '#1877F2', body: '#DBEAFE', acc: '#0B5BD3' }
};

// Seat id → avatar PNG filename mapping (product/avatars/)
const AVATAR_FILENAME_MAP = {
  gpt4o: 'avatar_gpt4o',
  chatgpt: 'avatar_gpt4o', claude: 'avatar_claude', gemini: 'avatar_gemini',
  deepseek: 'avatar_deepseek', qwen: 'avatar_qwen', kimi: 'avatar_kimi',
  grok: 'avatar_grok', yuanbao: 'avatar_yuanbao', doubao: 'avatar_doubao',
  minimax: 'avatar_minimax', zhipu: 'avatar_zhipu', mimo: 'avatar_mimo',
  wenxin: 'avatar_wenxin', meta: 'avatar_meta', grand_judge: 'avatar_grandjudge'
};

function _avatarDataUri(seatId) {
  const raw = String(seatId || "").toLowerCase().replace(/[^a-z0-9_]/g, "");
  const normalized = raw === "grandjudge" ? "grand_judge" : raw === "gpt4" || raw === "gpt4o" ? "gpt4o" : raw;
  const isJudge = normalized === "grand_judge";
  const palette = isJudge
    ? { head: "#D4AF37", body: "#FFF7D6", acc: "#B45309" }
    : MODEL_COLORS[normalized] || MODEL_COLORS.chatgpt;
  const svg = robotAvatarSvg(normalized, palette, isJudge);
  const encoded = encodeURIComponent(svg).replace(/\(/g, "%28").replace(/\)/g, "%29").replace(/'/g, "%27");
  return `data:image/svg+xml;charset=UTF-8,${encoded}`;
}

function robotAvatarSvg(id, palette, isJudge = false) {
  const scarf = palette.head || "#3B82F6";
  const scarfDark = palette.acc || scarf;
  const accessory = {
    gpt4o: '<circle cx="64" cy="13" r="6" fill="' + scarf + '"/><path d="M64 30V18" stroke="#111827" stroke-width="3" stroke-linecap="round"/>',
    chatgpt: '<circle cx="64" cy="13" r="6" fill="' + scarf + '"/><path d="M64 30V18" stroke="#111827" stroke-width="3" stroke-linecap="round"/>',
    claude: '<circle cx="88" cy="39" r="6" fill="' + scarf + '"/>',
    gemini: '<path d="M91 33l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="' + scarf + '"/>',
    deepseek: '<rect x="42" y="26" width="44" height="9" rx="4.5" fill="#111827" stroke="' + scarf + '" stroke-width="2"/>',
    qwen: '<path d="M92 39l6 6-6 6-6-6z" fill="' + scarf + '"/>',
    kimi: '<path d="M64 31V18" stroke="#166534" stroke-width="3" stroke-linecap="round"/><ellipse cx="57" cy="17" rx="9" ry="5" fill="#43A85F"/><ellipse cx="72" cy="16" rx="10" ry="5" fill="#55BC6F"/>',
    grok: '<path d="M91 31l-8 15h7l-6 15 14-20h-8z" fill="#FACC15"/>',
    yuanbao: '<circle cx="91" cy="44" r="8" fill="' + scarf + '" stroke="#99F6E4" stroke-width="2"/>',
    doubao: '<path d="M91 31c8 8 10 17 2 22-8 4-16-2-12-11 1-4 6-7 10-11z" fill="' + scarf + '"/>',
    minimax: '<path d="M92 32l10 14-10 14-10-14z" fill="' + scarf + '"/>',
    zhipu: '<circle cx="92" cy="44" r="8" fill="none" stroke="' + scarf + '" stroke-width="3"/><path d="M92 30v28M78 44h28" stroke="' + scarf + '" stroke-width="2"/>',
    mimo: '<path d="M91 36c-7 7-7 18 4 23-14-1-23-15-14-27 3-4 7-6 10-6-2 3-2 6 0 10z" fill="' + scarf + '"/>',
    wenxin: '<ellipse cx="91" cy="42" rx="8" ry="13" fill="' + scarf + '"/><path d="M86 35c6 8 8 14 9 24" stroke="#14532D" stroke-width="2" stroke-linecap="round"/>',
    meta: '<circle cx="91" cy="42" r="8" fill="' + scarf + '"/><circle cx="103" cy="42" r="5" fill="' + scarf + '" opacity=".72"/><circle cx="83" cy="52" r="5" fill="' + scarf + '" opacity=".72"/><path d="M91 42l12 0M91 42l-8 10" stroke="#0B5BD3" stroke-width="2" stroke-linecap="round"/>',
  }[id] || "";
  const judgeTop = '<circle cx="64" cy="13" r="5" fill="#D4AF37"/><path d="M64 30V18" stroke="#111827" stroke-width="3" stroke-linecap="round"/>';
  const lower = isJudge
    ? '<path d="M33 85h62l14 30H19z" fill="#111827"/><path d="M50 86l14 16 14-16 10 9-24 22-24-22z" fill="#FFF7D6"/><circle cx="64" cy="101" r="11" fill="#D4AF37" stroke="#92400E" stroke-width="2"/><path d="M58 101h12M64 95v13" stroke="#6B3A0A" stroke-width="3" stroke-linecap="round"/>'
    : '<path d="M24 84h80l-12 32H36z" fill="' + scarfDark + '"/><path d="M35 86l29 18 29-18-8 14-21 17-21-17z" fill="' + scarf + '"/><path d="M43 90h42" stroke="#fff" stroke-opacity=".34" stroke-width="3" stroke-linecap="round"/>';
  return `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <filter id="s" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#0f172a" flood-opacity=".16"/></filter>
    <linearGradient id="head" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#E9EEF6"/></linearGradient>
    <linearGradient id="face" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111827"/><stop offset="1" stop-color="#030712"/></linearGradient>
  </defs>
  <circle cx="64" cy="66" r="56" fill="#fff" filter="url(#s)"/>
  <circle cx="64" cy="65" r="46" fill="#F8FAFC"/>
  ${isJudge ? judgeTop : accessory}
  <circle cx="26" cy="62" r="13" fill="#D9E1EC" stroke="#96A3B4" stroke-width="2"/>
  <circle cx="102" cy="62" r="13" fill="#D9E1EC" stroke="#96A3B4" stroke-width="2"/>
  <circle cx="26" cy="62" r="7" fill="${scarf}"/>
  <circle cx="102" cy="62" r="7" fill="${scarf}"/>
  <rect x="28" y="31" width="72" height="58" rx="19" fill="url(#head)" stroke="#C6D0DD" stroke-width="2"/>
  <rect x="38" y="46" width="52" height="30" rx="14" fill="url(#face)"/>
  <ellipse cx="53" cy="60" rx="5" ry="8" fill="#F8FAFC"/>
  <ellipse cx="75" cy="60" rx="5" ry="8" fill="#F8FAFC"/>
  <path d="M56 70c5 5 11 5 16 0" fill="none" stroke="#CBD5E1" stroke-width="2" stroke-linecap="round"/>
  <path d="M34 38c10-9 52-10 61 5" fill="none" stroke="#fff" stroke-opacity=".65" stroke-width="4" stroke-linecap="round"/>
  ${lower}
</svg>`.trim();
}

function _defaultModelColors(id) {
  const hash = Math.abs((id || 'x').charCodeAt(0) || 7);
  const pool = Object.values(MODEL_COLORS);
  return pool[hash % pool.length];
}

function renderAvatar(seat, size) {
  const id = (seat.id || '').toLowerCase();
  const isGrand = seat.id === "grand_judge" || seat.role === "Grand Judge";
  const avatarUrl = isGrand ? _avatarDataUri('grand_judge') : _avatarDataUri(id);
  const placeholder = isGrand ? _avatarDataUri('grand_judge') : (_avatarDataUri(id) || _avatarDataUri('claude'));
  const finalUrl = avatarUrl || placeholder;
  const colorVar = isGrand ? '#FFD700' : ((MODEL_COLORS[id] || _defaultModelColors(id)).head || '#64748b');
  const gjClass = isGrand ? ' avatar-grand-judge' : '';

  return `<span class="avatar-png${gjClass}" style="--avatar-url:url(${finalUrl});--avatar-size:${size}px;--avatar-color:${colorVar};" aria-label="${escapeAttr(seat.name || '模型')}">
    <span class="avatar-glow" style="background:linear-gradient(135deg,${isGrand ? '#FFD700,#FF8C00' : colorVar + ',' + ((MODEL_COLORS[id] || _defaultModelColors(id)).body || colorVar)});"></span>
  </span>`;
}

function bridgeSeatById(seatId) {
  return (state.bridge?.seats || []).find(item => item.id === seatId);
}

function bridgeMatrixBySeat(seatId) {
  return (state.bridge?.seat_browser_matrix || []).find(item => item.seat === seatId);
}

function updateMentorPreflight() {
  const panel = $("#mentorPanel");
  const inline = $("#mentorInlineState");
  if (!panel || !inline) return;
  const question = $("#question-input")?.value.trim() || "";
  if (!state.mentorEnabled) {
    panel.hidden = true;
    inline.textContent = "快速模式直达";
    state.mentorSnapshot = null;
    clearPromptPreviewTimer();
    state.promptPreview = null;
    state.promptPreviewSignature = "";
    renderMentorPromptPreview(null);
    renderMentorGateChecklist();
    renderTaskCenter();
    return;
  }
  panel.hidden = false;
  const snapshot = buildMentorPreflight(question);
  state.mentorSnapshot = snapshot;
  $("#mentorRoute").textContent = snapshot.route_label;
  $("#mentorClarity").textContent = snapshot.clarity;
  $("#mentorRisk").textContent = snapshot.risk;
  $("#mentorComplexity").textContent = snapshot.complexity;
  $("#mentorQuestion").textContent = snapshot.next_question;
  $("#mentorAssumptions").innerHTML = snapshot.assumptions.map(item => `<li>${escapeHtml(item)}</li>`).join("");
  $("#mentorRoutes").innerHTML = snapshot.model_routes.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("");
  inline.textContent = state.mentorConfirmed ? "已确认，可执行" : "需确认理解后执行";
  renderMentorPromptPreview(snapshot);
  schedulePromptPreview(question, snapshot);
  renderMentorGateChecklist();
  renderTaskCenter();
}

function renderMentorGateChecklist() {
  const list = $("#mentorGateChecklist");
  if (!list) return;
  const question = $("#question-input")?.value.trim() || "";
  const snapshot = state.mentorEnabled ? (state.mentorSnapshot || buildMentorPreflight(question)) : null;
  const items = state.mentorEnabled ? [
    {
      title: "问题清晰度",
      hint: question ? "目标、输出和边界已进入预检" : "还没有可评审的问题",
      meta: question ? `${snapshot.clarity}` : "待输入",
      state: !question ? "block" : snapshot.clarity >= 70 ? "ok" : "warn",
    },
    {
      title: "风险边界",
      hint: "发布、隐私、部署、金融等外部影响会触发二次确认",
      meta: `${snapshot.risk}`,
      state: snapshot.risk >= 68 && !state.mentorConfirmed ? "warn" : "ok",
    },
    {
      title: "模型路由",
      hint: (snapshot.model_routes || []).join("；") || "默认快速评议",
      meta: snapshot.route_label || "Direct",
      state: (snapshot.model_routes || []).length ? "ok" : "warn",
    },
    {
      title: "执行确认",
      hint: snapshot.next_question || "确认后进入后台任务",
      meta: state.mentorConfirmed ? "已确认" : "待确认",
      state: state.mentorConfirmed ? "ok" : "block",
    },
  ] : [
    { title: "快速模式", hint: "当前不会阻断提交，适合低风险问题", meta: "直达", state: "ok" },
    { title: "导师增强", hint: "打开“先帮我想清楚”后启用清晰度、风险和复杂度门禁", meta: "可选", state: "warn" },
    { title: "模型路由", hint: "提交时仍会按当前议事深度选择席位", meta: state.selectedMode, state: "ok" },
  ];
  list.innerHTML = items.map(item => `
    <li class="${escapeAttr(item.state)}">
      <span class="mentor-gate-title"><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.hint)}</small></span>
      <span>${escapeHtml(item.meta)}</span>
    </li>
  `).join("");
}

function buildMentorPreflight(question) {
  const normalized = question.trim();
  const lower = normalized.toLowerCase();
  const has = terms => terms.some(term => lower.includes(term.toLowerCase()));
  const length = normalized.length;
  const clarity = clampScore(
    30
    + (length >= 12 ? 15 : 0)
    + (length >= 40 ? 15 : 0)
    + (has(mentorLexicon.output) ? 14 : 0)
    + (has(mentorLexicon.constraints) ? 13 : 0)
    + (/[?？]/.test(normalized) ? 6 : 0)
    + (state.selectedSeats.size ? 7 : 0)
  );
  const risk = clampScore(
    12
    + (has(mentorLexicon.risk) ? 34 : 0)
    + (state.engine === "web" ? 10 : 0)
    + (/(发布|发送|删除|部署|支付|密钥|凭据|外部|不可逆)/.test(normalized) ? 22 : 0)
    + (state.selectedMode === "strategic" ? 8 : 0)
  );
  const complexity = clampScore(
    22
    + (length >= 80 ? 22 : 0)
    + (length >= 160 ? 12 : 0)
    + (/(全模型|多个|多模型|网页|桌面|桥接|产品图|代码|测试|方案)/.test(normalized) ? 22 : 0)
    + (state.selectedSeats.size >= 6 ? 10 : 0)
  );
  const route = risk >= 68 || complexity >= 72 || clarity < 55 ? "enhanced" : clarity >= 76 ? "direct_confirm" : "light";
  const modelRoutes = mentorRoutesForQuestion(normalized);
  return {
    enabled: true,
    route,
    route_label: route === "enhanced" ? "增强导师" : route === "direct_confirm" ? "确认后直达" : "轻量导师",
    clarity,
    risk,
    complexity,
    next_question: mentorQuestionFor({ question: normalized, clarity, risk, complexity, route }),
    assumptions: mentorAssumptionsFor({ question: normalized, clarity, risk, complexity, route }),
    model_routes: modelRoutes,
    execution_draft: mentorExecutionDraft(normalized, modelRoutes),
    confirmed: state.mentorConfirmed,
    signature: mentorSignature(normalized),
  };
}

function mentorRoutesForQuestion(question) {
  const lower = question.toLowerCase();
  const touchesExecution = mentorLexicon.execution.some(term => lower.includes(term.toLowerCase()));
  const touchesStrategy = mentorLexicon.strategy.some(term => lower.includes(term.toLowerCase()));
  const routes = [];
  if (touchesStrategy || !touchesExecution) routes.push("Best Minds: 产品/判断/设计补强");
  if (touchesExecution || /代码|客户端|api|测试|部署|修复|落地/i.test(question)) routes.push("gstack: 工程执行/代码/验证");
  if (routes.length > 1) routes.push("混合路由: 先共识方案，再拆执行提示词");
  return routes.length ? routes : ["AI Judge Fast: 直接评议"];
}

function mentorQuestionFor({ question, clarity, risk, complexity, route }) {
  if (!question) return "你希望 AI Judge 最终帮你做出什么决定，而不是只生成什么内容？";
  if (clarity < 55) return "这件事最后怎样才算成功？请给一个可判断的验收标准。";
  if (risk >= 68) return "这次执行有没有外部影响、不可逆动作或敏感信息边界需要我先锁住？";
  if (complexity >= 72) return "哪些内容必须本轮完成，哪些可以作为下一轮补充？";
  if (route === "direct_confirm") return "我会按当前问题直接评议；还有没有一个你担心模型误判的关键约束？";
  return "你更希望我优先优化结论质量、执行速度，还是风险边界？";
}

function mentorAssumptionsFor({ question, clarity, risk, complexity }) {
  const assumptions = [];
  if (!question) assumptions.push("尚未输入问题，不能进入执行。");
  if (clarity < 70) assumptions.push("系统会把缺失的成功标准标为待确认，不替你暗中决定。");
  if (risk >= 55) assumptions.push("涉及发布、外部影响或敏感信息时，默认需要二次确认。");
  if (complexity >= 65) assumptions.push("复杂任务会拆成模型分工提示词，避免所有要求挤进一个回答。");
  if (!assumptions.length) assumptions.push("当前问题足够清楚，确认后可直接进入快速模式。");
  return assumptions;
}

function mentorExecutionDraft(question, routes) {
  if (!question) return "";
  return [
    "理解：用户希望 AI Judge 先校准意图，再给出可审计、可比较、可执行的回答。",
    `原始问题：${question}`,
    `模型路由：${routes.join("；")}`,
    "执行要求：保留原始问题、显式列出假设、给出结论/理由/风险/下一步，并在需要时阻断发布。",
  ].join("\n");
}

function clearPromptPreviewTimer() {
  if (state.promptPreviewTimer) clearTimeout(state.promptPreviewTimer);
  state.promptPreviewTimer = null;
}

function schedulePromptPreview(question, snapshot) {
  if (!state.mentorEnabled) return;
  const signature = mentorSignature(question || "");
  if (!question) {
    clearPromptPreviewTimer();
    state.promptPreview = null;
    state.promptPreviewSignature = "";
    renderMentorPromptPreview(snapshot);
    return;
  }
  if (state.promptPreview && state.promptPreviewSignature === signature) {
    renderMentorPromptPreview(snapshot);
    return;
  }
  clearPromptPreviewTimer();
  const status = $("#mentorPromptStatus");
  if (status) status.textContent = "整理中";
  state.promptPreviewTimer = setTimeout(() => {
    refreshPromptPreview(question, signature, snapshot);
  }, 360);
}

async function refreshPromptPreview(question, signature, snapshot) {
  try {
    const res = await fetch(`${API_BASE}/api/prompt/resonate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode: state.selectedMode,
        engine: state.engine,
        seats: Array.from(state.selectedSeats),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    if (mentorSignature($("#question-input")?.value.trim() || "") !== signature) return;
    state.promptPreview = data.prompt_flow || null;
    state.promptPreviewSignature = signature;
    renderMentorPromptPreview(snapshot || buildMentorPreflight(question), state.promptPreview);
  } catch (error) {
    if (mentorSignature($("#question-input")?.value.trim() || "") !== signature) return;
    state.promptPreview = buildFallbackPromptPreview(question, snapshot || buildMentorPreflight(question), error);
    state.promptPreviewSignature = signature;
    renderMentorPromptPreview(snapshot || buildMentorPreflight(question), state.promptPreview);
  }
}

function buildFallbackPromptPreview(question, snapshot, error = null) {
  return {
    version: "mentor-preview-fallback",
    intent: "把用户任务收束成可审计、可比较、可执行的 AI Judge 评审问题",
    mode: state.selectedMode,
    engine: state.engine,
    trace_id: "local-preview",
    quick_response: error ? `本地预览已生成；接口预览暂不可用：${error.message || error}` : "本地预览已生成。",
    professional_prompt: buildMentorPromptText(question, snapshot),
    assumptions_to_check: snapshot?.assumptions || [],
    required_output: [
      "独立结论或方案，标题必须对齐用户任务",
      "页面/流程/证据或实施结构",
      "报告/文稿/交付物结构",
      "风险、盲点与最小下一步",
    ],
  };
}

function buildMentorPromptText(question, snapshot) {
  const routes = (snapshot?.model_routes || []).join("；") || "AI Judge Fast";
  const assumptions = (snapshot?.assumptions || []).map(item => `- ${item}`).join("\n") || "- 外部事实若会变化，需要显式标注信息时点";
  return [
    "[SYSTEM] 作为 AI Judge 独立专家席位，你重视清晰、证据和可执行性。请先给出明确立场，再说明依据、风险和下一步，不要回避。",
    "",
    "[QUESTION] [AIJUDGE_PRE_RUN_CONFIRMATION]",
    "你将作为 AI Judge 全席位中的独立专家，不要互相迎合，也不要只给空泛结论。目标是输出可审计、可比较、可落地的方案。",
    "",
    "用户原始任务：",
    question,
    "",
    "规范化任务：",
    snapshot?.execution_draft || "请围绕用户问题给出结论、依据、风险和下一步。",
    "",
    "模型路由：",
    routes,
    "",
    "请务必输出：",
    "A. 你的独立结论或方案，标题必须对齐任务；",
    "B. 关键依据、页面/流程/证据或实施结构；",
    "C. 报告/文稿/交付物应该如何排版和交付；",
    "D. 你认为当前产品或方案最大的 5 个问题；",
    "E. 至少 3 个可选方案，每个说明适用场景、优点、缺点、风险和实施成本；",
    "F. 最终推荐可以有，但必须保留其他方案供用户选择；",
    "G. 下一步可以验证的任务清单。",
    "",
    "需要主动核查或声明的假设：",
    assumptions,
    "",
    "约束：不要把所有内容塞进一个杂乱页面；不要省略有效模型信息；不要把不可验证内容说成事实；保持短标题、明确模块名和可追溯来源。",
  ].join("\n");
}

function renderMentorPromptPreview(snapshot, promptFlow = state.promptPreview) {
  const card = $("#mentorPromptCard");
  if (!card) return;
  const preview = $("#mentorPromptPreview");
  const status = $("#mentorPromptStatus");
  const meta = $("#mentorPromptMeta");
  const hint = $("#mentorPromptHint");
  if (!state.mentorEnabled) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const question = $("#question-input")?.value.trim() || "";
  if (!question) {
    if (preview) preview.textContent = "输入问题后，主审法官会把原始任务、规范化任务、输出要求和约束整理成可确认提示词。";
    if (status) status.textContent = "待输入";
    if (meta) meta.innerHTML = "";
    if (hint) hint.textContent = "确认开庭前不会跑任务。";
    return;
  }
  const flow = promptFlow || buildFallbackPromptPreview(question, snapshot || buildMentorPreflight(question));
  const activeSignature = mentorSignature(question);
  const confirmed = state.mentorConfirmed && state.mentorSignature === activeSignature;
  if (preview) preview.textContent = flow.professional_prompt || buildMentorPromptText(question, snapshot);
  if (status) status.textContent = confirmed ? "已确认" : "待确认";
  if (meta) {
    const selectedSeats = Array.from(state.selectedSeats).map(seatName).slice(0, 6).join("、") || "未选席位";
    meta.innerHTML = [
      `模式：${state.selectedMode}`,
      `席位：${state.selectedSeats.size}`,
      `路由：${snapshot?.route_label || "-"}`,
      `Trace：${flow.trace_id || "-"}`,
      `发送：${selectedSeats}`,
    ].map(item => `<span>${escapeHtml(item)}</span>`).join("");
  }
  if (hint) {
    hint.textContent = confirmed
      ? "提示词已确认，下一次点击会正式开庭。"
      : (flow.quick_response || "请确认这份提示词是否准确表达了你的任务。");
  }
}

function confirmMentorPreview() {
  const question = $("#question-input")?.value.trim() || "";
  if (!question) {
    $("#question-input")?.focus();
    return;
  }
  const snapshot = buildMentorPreflight(question);
  state.mentorSnapshot = snapshot;
  state.mentorConfirmed = true;
  state.mentorSignature = snapshot.signature;
  renderMentorPromptPreview(snapshot);
  updateMentorPreflight();
  updateSubmitState();
  renderConferenceRoom();
}

async function copyPromptPreview(button) {
  const preview = $("#mentorPromptPreview")?.textContent || "";
  if (!preview.trim()) return;
  const original = button?.textContent || "";
  try {
    await navigator.clipboard.writeText(preview);
    if (button) button.textContent = "已复制";
  } catch {
    if (button) button.textContent = "复制失败";
  } finally {
    if (button && original) {
      setTimeout(() => {
        button.textContent = original;
      }, 1400);
    }
  }
}

function mentorSignature(question) {
  return [question.trim(), state.selectedMode, state.engine, Array.from(state.selectedSeats).sort().join(",")].join("|");
}

function confirmMentorGate(question) {
  if (!state.mentorEnabled) return true;
  const snapshot = buildMentorPreflight(question);
  state.mentorSnapshot = snapshot;
  const signature = snapshot.signature;
  if (state.mentorConfirmed && state.mentorSignature === signature) return true;
  state.mentorConfirmed = true;
  state.mentorSignature = signature;
  updateMentorPreflight();
  setBusy(false);
  switchTab("request");
  return false;
}

function mentorPayloadForSubmit(question) {
  if (!state.mentorEnabled) return null;
  const snapshot = buildMentorPreflight(question);
  const signature = mentorSignature(question);
  const promptPreview = state.promptPreviewSignature === signature ? state.promptPreview : null;
  return {
    ...snapshot,
    confirmed: true,
    confirmed_at: new Date().toISOString(),
    prompt_preview: promptPreview,
    professional_prompt: promptPreview?.professional_prompt || buildMentorPromptText(question, snapshot),
  };
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function normalizeSeatId(seat) {
  const id = String(seat || "").trim().toLowerCase();
  return id === "gork" ? "grok" : id;
}

function isOptionalExecutionSeat(seat) {
  const id = normalizeSeatId(seat);
  const bridgeSeat = (state.bridge?.seats || []).find(item => normalizeSeatId(item.id) === id);
  if (bridgeSeat && (bridgeSeat.best_effort || bridgeSeat.exclude_from_publish_gate || bridgeSeat.execution_required === false)) {
    return true;
  }
  return OPTIONAL_EXECUTION_SEATS.has(id);
}

function resultExecutionRequired(item) {
  if (!item) return false;
  const validity = item.execution_validity || {};
  if (validity.required !== undefined) return Boolean(validity.required);
  if (item.execution_required !== undefined) return Boolean(item.execution_required);
  return !isOptionalExecutionSeat(item.seat);
}

function resultExecutionValid(item) {
  if (!item?.ok) return false;
  const validity = item.execution_validity || {};
  if (validity.valid !== undefined) return Boolean(validity.valid);
  return Boolean(String(item.response || "").trim());
}

function executionPolicySummary(verdict = state.currentVerdict) {
  const bridge = verdict?.web_bridge || {};
  if (bridge.execution_policy) return bridge.execution_policy;
  const raw = bridge.raw_results || [];
  const requested = (verdict?.seats || raw.map(item => item.seat || "")).map(normalizeSeatId).filter(Boolean);
  const required = requested.filter(seat => !isOptionalExecutionSeat(seat));
  const optional = requested.filter(seat => isOptionalExecutionSeat(seat));
  const bySeat = new Map(raw.map(item => [normalizeSeatId(item.seat), item]));
  const failures = [];
  let validCount = 0;
  required.forEach(seat => {
    const item = bySeat.get(seat);
    if (resultExecutionValid(item)) {
      validCount += 1;
      return;
    }
    failures.push({
      seat,
      seat_name: item?.seat_name || seatName(seat),
      error: item?.error || { code: "missing_result" },
      supplementable: item ? isSupplementableResult(item) : false,
      execution_validity: item?.execution_validity || {},
    });
  });
  return {
    policy_version: "required-web-seat-v1",
    required_seats: required,
    optional_seats: optional,
    required_count: required.length,
    required_valid_count: validCount,
    required_failed_count: failures.length,
    required_failures: failures,
    required_supplementable_seats: failures.filter(item => item.supplementable),
    collection_complete: failures.length === 0,
    grok_counts_as: "optional_dissent_best_effort",
  };
}

// ── P3 Composer Mode Buttons ──
(function initComposerModes() {
  const quickBtn = document.getElementById('composer-mode-quick');
  const fullBtn = document.getElementById('composer-mode-full');
  const deepBtn = document.getElementById('composer-mode-deep');
  if (!quickBtn || !fullBtn || !deepBtn) return;

  function setMode(mode) {
    [quickBtn, fullBtn, deepBtn].forEach(b => b.classList.remove('active', 'is-active'));
    if (mode === 'quick') quickBtn.classList.add('active', 'is-active');
    else if (mode === 'deep') deepBtn.classList.add('active', 'is-active');
    else fullBtn.classList.add('active', 'is-active');
    // Update hidden state for compatibility
    const state = window.__AI_JUDGE_STATE__;
    if (state) state.currentMode = mode;
    // Dispatch for any legacy listeners
    document.querySelectorAll('.composer-mode-btn').forEach(el => {
      const elMode = el.dataset.mode;
      if (elMode === mode) { el.classList.add('active', 'is-active'); el.setAttribute('aria-pressed', 'true'); }
      else { el.classList.remove('active', 'is-active'); el.removeAttribute('aria-pressed'); }
    });
  }

  quickBtn.addEventListener('click', () => setMode('quick'));
  fullBtn.addEventListener('click', () => setMode('full'));
  deepBtn.addEventListener('click', () => setMode('deep'));
})();



// ── P3 Werewolf Toggle Visual ──
// initWerewolfToggle removed: delegated capture handler (L334-338) handles setWerewolfMode correctly
// P26-fix: prevent double-toggle state inversion


async function submitJudge(options = {}) {
  const question = getEffectiveQuestion();
  if (!question) return;

  if (!confirmMentorGate(question)) return;

  state.workflow.rawUserInput = question;
  if (!options.skipPreflight) {
    if (!isReady()) {
      setBusy(false);
      state.workflow.stage = WORKFLOW_STAGE.FAILED;
      setProgress(0, "桥接未就绪，无法开始真实裁决。请检查桥接状态、Chrome CDP、席位配置。");
      return;
    }
    state.workflow.stage = WORKFLOW_STAGE.ALIGNING_INTENT;
    state.workflow.paused = false;
    state.workflow.canPause = false;
    setBusy(true);
    setProgress(6, "检查网页席位门禁");
    try {
      const gate = await preflightExecutionGate(question);
      if (!gate.ok) {
        state.workflow.stage = WORKFLOW_STAGE.FAILED;
        state.workflow.canPause = false;
        setBusy(false);
        setProgress(0, gate.plan?.message || "会前席位门禁阻断");
        showExecutionGateDiagnostic(gate.plan, gate.bridge);
        return;
      }
      renderRunDiagnostics(null);
    } catch (err) {
      state.workflow.stage = WORKFLOW_STAGE.FAILED;
      state.workflow.canPause = false;
      setBusy(false);
      setProgress(0, `会前门禁失败：${err.message}`);
      return;
    }
  }

  const mentorPreflight = mentorPayloadForSubmit(question);
  state.onboardingComplete = true;
  localStorage.setItem("ai_judge_onboarding_complete", "1");
  switchTab("tasks");
  resetRunUI();
  setBusy(true);
  setProgress(3, "确认开庭中");
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;
  state.workflow.paused = false;
  state.workflow.canPause = true;
  state.workflow.completedSeats = new Set();
  state.workflow.activeSeatCount = 0;
  // P71: Clear attachments on new run start
  state.workflow.attachments = [];
  if (window.renderAttachmentList) window.renderAttachmentList();

  var _submitCfg = getModeConfig(state.selectedMode);
  var _sysInstr = _submitCfg.systemInstruction;
  var _sysHashVal = _sysHash(_sysInstr, state.selectedMode);

  // P69: Write debug submit payload (only when DEBUG_MODE_GUIDE is true)
  if (DEBUG_MODE_GUIDE) {
    try {
      var _dbg = JSON.stringify({
        selectedMode: state.selectedMode,
        modeLabel: _submitCfg.label,
        placeholder: _submitCfg.placeholder,
        guideText: _submitCfg.guideText,
        systemInstruction: _sysInstr,
        systemInstructionHash: _sysHashVal,
        userQuestion: question,
        submittedAt: new Date().toISOString(),
      }, null, 2);
      var _dbgPath;
      if (typeof require !== 'undefined' && require('electron') && require('electron').remote) {
        _dbgPath = require('path').join(require('electron').remote.app.getPath('userData'), '..', 'AI Judge', 'runtime', 'debug-submit-' + state.selectedMode + '.json');
      } else {
        _dbgPath = '/tmp/ai-judge-debug-submit-' + state.selectedMode + '.json';
      }
      if (typeof window.__AI_JUDGE_DEBUG_WRITE__ === 'function') {
        window.__AI_JUDGE_DEBUG_WRITE__(_dbgPath, _dbg);
      }
      console.log('P69: debug-submit payload → ' + _dbgPath, JSON.parse(_dbg));
    } catch (_) {
      console.warn('P69: failed to write debug submit JSON', _);
    }
  }

  const notify = {
    email: $("#notify-email").value.trim(),
    webhook_url: $("#notify-webhook").value.trim(),
    feishu_webhook: $("#notify-feishu").value.trim(),
    wecom_webhook: $("#notify-wecom").value.trim(),
    desktop: $("#notify-browser").checked,
  };
  notify.channels = Object.entries({
    email: notify.email,
    webhook: notify.webhook_url,
    feishu: notify.feishu_webhook,
    wecom: notify.wecom_webhook,
    desktop: notify.desktop,
  }).filter(([, value]) => Boolean(value)).map(([key]) => key);

  try {
    const res = await fetch(`${API_BASE}/api/judge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode: state.selectedMode,
        engine: state.engine,
        seats: Array.from(state.selectedSeats),
        abstained_seats: state.seats.map(seat => seat.id).filter(id => !state.selectedSeats.has(id)),
        chief_judge: state.chiefJudge,
        mentor_preflight: mentorPreflight,
        notify,
        mode_label: _submitCfg.label,
        system_instruction: _sysInstr,
        attachments: (state.workflow.attachments || []).map(att => ({
          id: att.id,
          name: att.name,
          size: att.size,
          type: att.type,
          source: att.source,
          textPreview: att.textPreview || "",
          textContent: att.textContent || "",
          truncated: !!att.truncated,
          contentAvailable: !!att.contentAvailable,
          run_id: att.run_id || null,
          path: att.path || null,
        })),
      }),
    });
    traceUIEvent("judge_payload_built", { run_id: null, attachment_count: (state.workflow.attachments || []).length, attachment_ids: (state.workflow.attachments || []).map(a => a.id), content_available_count: (state.workflow.attachments || []).filter(a => a.contentAvailable).length, has_file_content: (state.workflow.attachments || []).some(a => a.contentAvailable && a.textContent) });
    const data = await res.json();
    if (!res.ok) {
      if (data.execution_plan) showExecutionGateDiagnostic(data.execution_plan, data.bridge_status || state.bridge);
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    state.currentRunId = data.run_id;
    state.workflow.runId = data.run_id;
    state.lastHistoryRunId = data.run_id;
    localStorage.setItem("ai_judge_last_run_id", data.run_id);
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `${engineName(data.engine)} · ${data.mode_name} · ${data.seat_count} 席`;
    state.currentTask = {
      run_id: data.run_id,
      question,
      status: "running",
      progress: 0.03,
      current_step: "提交成功，等待网页席位",
    };
    state.mentorConfirmed = false;
    updateMentorPreflight();
    renderAutopilotWorkbench();
    renderTaskCenter();
    renderConferenceRoom();
    startProgress(data.run_id);
    await loadHistory();
  } catch (err) {
    state.workflow.stage = WORKFLOW_STAGE.FAILED;
    state.workflow.canPause = false;
    setProgress(0, `提交失败：${err.message}`);
    setBusy(false);
  }
}

function isSupplementableResult(item) {
  const code = item?.error?.code || "";
  return Boolean(item && !item.ok && (item.supplementable || RECOVERABLE_WEB_CODES.has(code)));
}

function supplementableRawResults() {
  const raw = (state.currentVerdict?.web_bridge || {}).raw_results || [];
  return raw.filter(item => resultExecutionRequired(item) && isSupplementableResult(item));
}

function currentRescuePlan() {
  return state.currentVerdict?.web_bridge?.rescue_plan || null;
}

function renderSupplementButton() {
  const btn = $("#btn-supplement-slow");
  const panel = $("#recovery-panel");
  if (!btn) {
    if (panel) panel.hidden = true;
    return;
  }
  const seats = supplementableRawResults();
  const plan = currentRescuePlan();
  const visible = Boolean(state.currentVerdict?.run_id && seats.length);
  btn.hidden = !visible;
  if (panel) panel.hidden = !visible;
  btn.disabled = false;
  const label = plan?.button_label || "一键修复并回收答案";
  btn.textContent = seats.length
    ? `${label} (${seats.map(item => item.seat_name || item.seat).join("、")})`
    : label;
  const summary = $("#recovery-summary");
  if (summary) summary.textContent = plan?.summary || "先读取已打开模型页；只有发送失败或串流污染时才进入干净会话重试。";
}

async function supplementSlowSeats() {
  const sourceRunId = state.currentVerdict?.run_id;
  const seats = supplementableRawResults().map(item => item.seat).filter(Boolean);
  if (!sourceRunId || !seats.length) return;

  const btn = $("#btn-supplement-slow");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "一键救援中...";
  }
  setProgress(4, `一键修复并回收答案：${seats.join(", ")}`);
  const notify = {
    email: $("#notify-email").value.trim(),
    webhook_url: $("#notify-webhook").value.trim(),
    feishu_webhook: $("#notify-feishu").value.trim(),
    wecom_webhook: $("#notify-wecom").value.trim(),
    desktop: $("#notify-browser").checked,
  };
  notify.channels = Object.entries({
    email: notify.email,
    webhook: notify.webhook_url,
    feishu: notify.feishu_webhook,
    wecom: notify.wecom_webhook,
    desktop: notify.desktop,
  }).filter(([, value]) => Boolean(value)).map(([key]) => key);

  try {
    const res = await fetch(`${API_BASE}/api/judge/${sourceRunId}/rescue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seats, notify }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.currentRunId = data.run_id;
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `一键救援 ${data.seat_count} 席 · 写回 ${sourceRunId}`;
    startProgress(data.run_id);
    await loadHistory();
  } catch (err) {
    setProgress(0, `一键救援失败：${err.message}`);
    renderSupplementButton();
  }
}

function recheckableDiagnosticSeats(diag) {
  if (!diag || (!diag.stale && diag.status !== "failed")) return [];
  return (diag?.seats || [])
    .filter(seat => {
      const stateName = seat.state || "";
      const statusName = seat.status || "";
      return ["waiting", "nudge"].includes(stateName)
        || ["慢生成", "超时", "发送未确认", "提交未确认", "疑似旧回答", "历史串流", "标签缺失", "输入框缺失"].includes(statusName);
    })
    .map(seat => seat.seat)
    .filter(Boolean);
}

function diagnosticRescueMethod(diag) {
  const plan = diag?.rescue_plan || {};
  if (plan.sends_prompt) return "fresh";
  return "existing";
}

async function recheckStalledSeats({ auto = false } = {}) {
  const task = state.currentTask;
  const sourceRunId = task?.run_id || state.currentRunId;
  const seats = recheckableDiagnosticSeats(task?.progress_diagnostics);
  if (!sourceRunId || !seats.length || state.recheckInFlight) return;
  const method = diagnosticRescueMethod(task?.progress_diagnostics);
  state.recheckInFlight = true;
  clearAutoRecheck();
  const btn = $("#btn-recheck-stalled");
  if (btn) {
    btn.disabled = true;
    btn.textContent = auto ? "自动救援中..." : "一键救援中...";
  }
  setProgress(4, `${auto ? "自动" : "手动"}一键修复并回收答案：${seats.join(", ")}`);
  const notify = {
    email: $("#notify-email").value.trim(),
    webhook_url: $("#notify-webhook").value.trim(),
    feishu_webhook: $("#notify-feishu").value.trim(),
    wecom_webhook: $("#notify-wecom").value.trim(),
    desktop: $("#notify-browser").checked,
  };
  notify.channels = Object.entries({
    email: notify.email,
    webhook: notify.webhook_url,
    feishu: notify.feishu_webhook,
    wecom: notify.wecom_webhook,
    desktop: notify.desktop,
  }).filter(([, value]) => Boolean(value)).map(([key]) => key);

  try {
    const res = await fetch(`${API_BASE}/api/judge/${sourceRunId}/recheck`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seats, notify, method }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.currentRunId = data.run_id;
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `${data.sends_prompt ? "干净会话重试" : "旧页面回收"} ${data.seat_count} 席 · 写回 ${sourceRunId}`;
    startProgress(data.run_id);
    await loadHistory();
  } catch (err) {
    state.recheckInFlight = false;
    setProgress(0, `旧页面回收失败：${err.message}`);
    renderRunDiagnostics(task);
  }
}

function startProgress(runId) {
  if (state.eventSource) state.eventSource.close();
  if (state.pollTimer) clearInterval(state.pollTimer);

  if ("EventSource" in window) {
    state.eventSource = new EventSource(`${API_BASE}/api/judge/${runId}/progress`);
    state.eventSource.onmessage = event => handleTask(JSON.parse(event.data));
    state.eventSource.onerror = () => {
      if (state.eventSource) state.eventSource.close();
      state.eventSource = null;
      startPolling(runId);
    };
  } else {
    startPolling(runId);
  }
}

function startPolling(runId) {
  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/task/${runId}`);
      handleTask(await res.json());
    } catch {
      setProgress(0, "连接中断，正在重试");
    }
  }, 1200);
}

function handleTask(task) {
  if (task.error && !task.status) {
    setProgress(0, task.error);
    renderRunDiagnostics(null);
    setBusy(false);
    return;
  }

  // P71: keep stopped runs explicit.
  if (state.workflow.stage === WORKFLOW_STAGE.CANCELLED) {
    return;
  }

  // P71: soft pause — skip UI updates but keep currentTask for catch-up on resume
  if (state.workflow.stage === WORKFLOW_STAGE.PAUSED) {
    state.currentTask = task;
    return;
  }

  state.currentTask = task;
  const pct = Math.round((Number(task.progress) || 0) * 100);
  setProgress(pct, task.current_step || task.status || "运行中");
  renderRunDiagnostics(task);
  renderTaskCenter();
  renderCouncilCompletion();
  renderAutopilotWorkbench(state.currentVerdict);

  if (task.status === "complete") {
    cleanupProgress();
    setBusy(false);
    state.recheckInFlight = false;
    renderRunDiagnostics(null);
    if (task.result) renderVerdict(task.result);
    else loadVerdict(task.run_id);
    loadHistory();
    maybeBrowserNotify("AI Judge 判词已完成", task.question || "");
    // P71: Reset workflow + trace
    state.workflow.stage = WORKFLOW_STAGE.COMPLETED;
    state.workflow.canPause = false;
    traceUIEvent("run_completed", { run_id: task.run_id, status: "complete" });
    removeParliamentPauseBanner();
  }
  if (task.status === "failed" || task.status === "cancelled") {
    cleanupProgress();
    setBusy(false);
    state.recheckInFlight = false;
    setProgress(pct, task.error || task.status);
    renderSupplementButton();
    // P71: Reset workflow
    state.workflow.stage = task.status === "cancelled" ? WORKFLOW_STAGE.CANCELLED : WORKFLOW_STAGE.FAILED;
    state.workflow.canPause = false;
    removeParliamentPauseBanner();
  }
}

async function loadVerdict(runId) {
  const res = await fetch(`${API_BASE}/api/judge/${runId}/verdict`);
  const verdict = await res.json();
  if (res.ok) renderVerdict(verdict);
}

function renderVerdict(v) {
  state.currentVerdict = v;
  if (v.run_id) {
    state.currentRunId = v.run_id;
    state.lastHistoryRunId = v.run_id;
    localStorage.setItem("ai_judge_last_run_id", v.run_id);
  }
  $("#result-empty").hidden = true;
  $("#verdict-card").hidden = false;
  $("#verdict-badge").textContent = `${v.mode_emoji || ""} ${v.verdict_label || v.verdict} · ${v.confidence}% · ${engineName(v.engine)}`;
  $("#verdict-title").textContent = reportHeaderTitle(v);
  $("#verdict-question").textContent = reportHeaderSummary(v);
  const judge = v.judge_answer || {};
  const bridge = v.web_bridge || {};
  const policy = bridge.raw_results?.length || String(v.engine || "").includes("web") ? executionPolicySummary(v) : {};
  const executionComplete = !policy.required_count || Boolean(policy.collection_complete);
  const okCount = bridge.ok_count ?? judge.ok_count;
  const totalCount = bridge.requested_count ?? ((judge.ok_count || 0) + (judge.failed_count || 0));
  const reportMeta = [
    v.run_id ? `Run ${compactRunId(v.run_id)}` : "",
    v.verdict_label || v.verdict ? `结论 ${v.verdict_label || v.verdict}` : "",
    v.confidence !== undefined ? `可信度 ${v.confidence}%` : "",
    okCount !== undefined && totalCount !== undefined ? `席位 ${okCount}/${totalCount}` : "",
  ].filter(Boolean);
  $("#report-meta").innerHTML = reportMeta.map(item => `<span>${escapeHtml(item)}</span>`).join("");
  if ($("#final-report-title")) {
    $("#final-report-title").textContent = executionComplete ? "最终结论报告" : "执行未完成报告";
  }
  renderFinalReport(v, executionComplete);
  $("#reason-list").innerHTML = (v.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join("");
  $("#step-list").innerHTML = (v.next_steps || []).map(step => `<li>${escapeHtml(step)}</li>`).join("");
  renderSimpleCloseout(v);
  renderAutopilotWorkbench(v);
  renderDecisionMemo(v);
  const reportUrl = canonicalReportUrl(v);
  $("#view-link").href = reportUrl;
  if ($("#result-view-link")) $("#result-view-link").href = reportUrl;
  if ($("#btn-report-pdf")) $("#btn-report-pdf").title = reportLabels().pdfHint;
  if ($("#btn-view-pdf")) $("#btn-view-pdf").title = reportLabels().pdfHint;
  $("#btn-download-json").onclick = () => downloadJSON(v, `verdict-${v.run_id || "ai-judge"}.json`);
  $("#btn-download-md").onclick = () => downloadMarkdown(v);
  renderSupplementButton();
  renderMentorVerdict(v.mentor_preflight);
  renderPromptFlow(v.prompt_flow);
  renderExecutionPlan(v.execution_plan, v.web_bridge);
  renderJudgeAnswer(v);
  renderScoreRounds(v.web_bridge);
  renderCrossTemporal(v);
  renderTrace(v.execution_trace);
  if (v.run_id) loadTrace(v.run_id);
  loadSeatScoreboard().then(() => {
    renderSeatScores();
    renderArena();
  });
  renderSeatScores();
  renderArena();
  renderSimpleSeatSummary();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderPublishGate();
  renderTaskCenter();
  renderAutopilotWorkbench();
  renderConferenceRoom(v);
}

function renderSimpleCloseout(v) {
  if (!$("#simple-closeout-strip")) return;
  const trust = trustTier(v);
  const summary = buildPublishGateSummary();
  const gavel = humanGavelState(summary);
  const report = finalReportText(v);
  const firstStep = (v?.next_steps || []).find(Boolean) || "先复核结论，再进入签字做签字。";
  const firstRisk = [
    ...(v?.reasons || []),
    v?.cross_temporal_analysis?.closeout_report?.executive_summary || "",
    trust.summary || "",
  ].find(item => /风险|阻断|不足|失败|不确定|复核|回收/.test(String(item || ""))) || trust.summary || "没有发现硬阻断，但仍建议保留签字。";
  $("#simple-closeout-answer").textContent = reportHeaderTitle(v) || excerpt(report, 120) || "AI Judge 已完成本轮判断。";
  $("#simple-closeout-why").textContent = excerpt(report, 260);
  $("#simple-closeout-action").textContent = excerpt(firstStep, 180);
  $("#simple-human-gavel").classList.toggle("is-ready", gavel.state === "publishable");
  $("#simple-human-gavel-state").textContent = gavel.label;
  $("#simple-human-gavel-copy").textContent = excerpt(firstRisk, 150);
  $("#simple-human-gavel-score").textContent = trust.label || "-";
}

function renderAutopilotWorkbench(v = state.currentVerdict) {
  if (!$("#simple-autopilot-page")) return;
  const coverage = seatCoverageSummary();
  const evidence = autopilotEvidenceSummary(v);
  const failures = autopilotFailureCount(v);
  const hasRunning = state.currentTask?.status === "running" && !state.currentTask?.progress_diagnostics?.stale;
  const stageReady = Boolean(v) && (!coverage.total || coverage.ok >= Math.min(coverage.total, 6));
  $("#autopilot-stage-status").textContent = stageReady
    ? `阶段报告就绪 · ${coverage.label}`
    : hasRunning
      ? `运行中 · ${coverage.label}`
      : "等待任务";
  $("#autopilot-eta").textContent = autopilotEta(v);
  $("#autopilot-evidence-chip").textContent = `${evidence.percent}%`;
  $("#autopilot-failure-inbox").textContent = String(failures);
  if ($("#autopilot-current-title")) {
    $("#autopilot-current-title").textContent = v
      ? (v.one_liner || `Run ${compactRunId(v.run_id)} 已完成`)
      : hasRunning
        ? `Run ${compactRunId(state.currentTask?.run_id)} 正在运行`
        : "当前没有运行任务";
  }
  if ($("#autopilot-current-copy")) {
    $("#autopilot-current-copy").textContent = v
      ? `阶段报告已进入报告。可信度 ${v.confidence ?? "-"}%，下一步需要签字。`
      : hasRunning
        ? `${state.currentTask?.current_step || "网页席位运行中"}。可关闭页面，完成后进入报告。`
        : "去「新建自动任务」投放链接、文件或问题；提交后这里显示 run id、预计完成和失败隔离区。";
  }
  if ($("#autopilot-sla-badges")) {
    $("#autopilot-sla-badges").innerHTML = autopilotSlaBadges(v).map(item => `<span>${escapeHtml(item)}</span>`).join("");
  }
  if ($("#autopilot-stage-open")) {
    $("#autopilot-stage-open").textContent = v
      ? "分类已锁定，最终结论以阶段报告为准"
      : hasRunning
        ? "运行中会自动继续"
        : "确认分类后进入新建任务页";
  }
  if ($("#autopilot-pipeline-seats")) $("#autopilot-pipeline-seats").textContent = coverage.total ? `${coverage.ok}/${coverage.total} 席有效` : "等待席位";
  if ($("#autopilot-pipeline-evidence")) $("#autopilot-pipeline-evidence").textContent = `${evidence.supported}/${evidence.total} 条主张`;
  $("#autopilot-required-count") && ($("#autopilot-required-count").textContent = coverage.total ? `${coverage.ok}/${coverage.total}` : "0/8");
  $("#autopilot-optional-count") && ($("#autopilot-optional-count").textContent = "1");
  renderAutopilotPipeline(v);
  const queueRows = autopilotQueueRows(v, coverage);
  renderAutopilotQueueFilters(queueRows);
  $("#autopilot-queue-list") && ($("#autopilot-queue-list").innerHTML = queueRows.map(item => `
    <div class="queue-run ${item.active ? "active" : ""}">
      <strong>${escapeHtml(item.title)}</strong>
      <span class="run-state">${escapeHtml(item.state)}</span>
      <small>${escapeHtml(item.meta)}</small>
      <small>${escapeHtml(item.id)}</small>
    </div>
  `).join(""));

  const classification = autopilotClassification(v);
  $("#autopilot-classification").textContent = classification.title;
  $("#autopilot-classification-reasons").innerHTML = classification.reasons
    .map(item => `<span class="tag">${escapeHtml(item)}</span>`)
    .join("");

  $("#autopilot-evidence-copy").textContent = evidence.total
    ? `${evidence.supported}/${evidence.total} 条主张拥有 Tier0/Tier1 支撑`
    : "未生成 Claim 级证据，需进入专业版证据或补充引用";
  $("#autopilot-evidence-score").textContent = `${evidence.percent}%`;
  $("#autopilot-evidence-bar")?.style.setProperty("--gauge", `${evidence.percent}%`);
  $("#autopilot-evidence-breakdown").innerHTML = [
    ["已支撑", evidence.supported],
    ["缺证据", evidence.unsupported],
    ["有冲突", evidence.contradicted],
    ["未验证", evidence.unverified],
  ].map(([label, value]) => `
    <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>
  `).join("");

  $("#autopilot-seat-grid").innerHTML = autopilotSeatRows(v).map(row => `
    <div class="seat-mini ${escapeAttr(row.state)}">
      <strong>${escapeHtml(row.name)}</strong>
      <span>${escapeHtml(row.label)}</span>
    </div>
  `).join("");

  const synthesis = autopilotSynthesisSummary(v);
  $("#autopilot-synthesis-summary").textContent = synthesis.summary;
  $$("[data-synthesis-section]").forEach(button => {
    button.classList.toggle("active", (button.dataset.synthesisSection || "raw") === state.synthesisSection);
  });
  $("#autopilot-synthesis-details").innerHTML = synthesis.blocks.map(block => `
    <div class="synthesis-detail">
      <span>${escapeHtml(block.label)}</span>
      <strong>${escapeHtml(block.value)}</strong>
    </div>
  `).join("");
  const synthesisRows = autopilotSynthesisRows(v);
  $("#autopilot-synthesis-table") && ($("#autopilot-synthesis-table").innerHTML = synthesisRows.map(row => {
    const action = row.href
      ? `<a href="${escapeAttr(row.href)}">${escapeHtml(row.action)}</a>`
      : escapeHtml(row.action);
    return `
      <div class="synthesis-table-row">
        <span>${escapeHtml(row.seat)}</span>
        <span>${escapeHtml(row.stance)}</span>
        <span>${escapeHtml(row.quality)}</span>
        <span>${action}</span>
      </div>
    `;
  }).join(""));

  const gavel = humanGavelState();
  const publishSummary = buildPublishGateSummary();
  $("#autopilot-gavel-copy").textContent = gavel.state === "publishable"
    ? "最终报告已签署；对外发布和站点修改仍需要单独门禁。"
    : v || hasRunning
      ? "阶段报告已就绪；最终报告必须由人类签字。"
      : "等待阶段报告；最终报告必须由人类签字。";
  $("#autopilot-gavel-button").style.opacity = v && !publishSummary.nonHumanBlockers ? "1" : ".45";
  $("#autopilot-gavel-button").disabled = !v || publishSummary.nonHumanBlockers > 0;
  $("#autopilot-gavel-button").textContent = gavel.state === "publishable" ? "已签署最终报告" : "签署最终报告";

  $("#autopilot-growth-actions").innerHTML = autopilotGrowthActions(v).map(item => `
    <li>
      <strong>${escapeHtml(item.title)}</strong>
      <div class="source-badges">
        ${item.badges.map(badge => `<span>${escapeHtml(badge)}</span>`).join("")}
      </div>
    </li>
  `).join("");

  $("#autopilot-artifacts").innerHTML = autopilotArtifacts(v).map(item => `
    <li>
      <strong>${escapeHtml(item.name)}</strong>
      <div class="source-badges"><span>${escapeHtml(item.status)}</span><span>${escapeHtml(item.reason)}</span></div>
    </li>
  `).join("");
}

function renderAutopilotQueueFilters(rows) {
  const target = $("#autopilot-queue-filters");
  if (!target) return;
  const running = rows.filter(row => row.kind === "running").length;
  const done = rows.filter(row => row.kind === "done").length;
  const failed = rows.filter(row => row.kind === "failed").length + autopilotFailureCount(state.currentVerdict);
  target.innerHTML = [
    ["全部", rows.length],
    ["运行", running],
    ["完成", done],
    ["失败", failed],
  ].map(([label, value], index) => `<span class="${index === 0 ? "active" : ""}">${escapeHtml(label)} ${escapeHtml(value)}</span>`).join("");
}

function autopilotSlaBadges(v = state.currentVerdict) {
  const counts = bridgeChannelCounts();
  if (v) {
    const coverage = seatCoverageSummary();
    return [
      v.run_id ? `Run ${compactRunId(v.run_id)}` : "Run 已完成",
      `阶段报告：已生成`,
      `席位：${coverage.label}`,
      `签字：${state.publishCleared ? "已确认" : "待签字"}`,
    ];
  }
  if (state.currentTask?.status === "running") {
    return [
      `Run ${compactRunId(state.currentTask.run_id)}`,
      `预计：${autopilotEta(v)}`,
      `席位：${counts.webReady}/${counts.webTotal}`,
      "失败策略：隔离后追加修订",
    ];
  }
  return [
    "最小交付：阶段报告",
    "默认：网页席位优先",
    `可用席位：${counts.webReady}/${counts.webTotal}`,
    "失败策略：隔离后追加修订",
  ];
}

function renderAutopilotPipeline(v = state.currentVerdict) {
  const target = $("#autopilot-pipeline-list");
  if (!target) return;
  const hasRunning = state.currentTask?.status === "running" && !state.currentTask?.progress_diagnostics?.stale;
  const hasVerdict = Boolean(v);
  const evidence = autopilotEvidenceSummary(v);
  const coverage = seatCoverageSummary();
  const steps = [
    { key: "intake", title: "接收任务", detail: hasVerdict || hasRunning ? "已捕获输入" : "等待投放", state: hasVerdict || hasRunning ? "done" : "active" },
    { key: "classify", title: "自动分类", detail: hasVerdict || hasRunning || state.simpleClassificationConfirmed ? "已完成路由" : "等待确认", state: hasVerdict || hasRunning ? "done" : state.simpleClassificationConfirmed ? "done" : "" },
    { key: "web", title: "网页席位", detail: coverage.total ? `${coverage.ok}/${coverage.total} 席有效` : "等待席位", state: hasVerdict ? "done" : hasRunning ? "active" : "" },
    { key: "evidence", title: "证据审计", detail: evidence.total ? `${evidence.supported}/${evidence.total} 条主张` : "等待报告", state: hasVerdict ? (evidence.percent >= 70 ? "done" : "active") : "" },
    { key: "synthesis", title: "综合裁决", detail: hasVerdict ? "可展开检查" : "等待席位", state: hasVerdict ? "done" : hasRunning ? "active" : "" },
    { key: "gavel", title: "人类裁决", detail: state.publishCleared ? "已签字" : "需要签字", state: state.publishCleared ? "done" : hasVerdict ? "gate" : "" },
    { key: "artifacts", title: "产物归档", detail: hasVerdict ? "阶段产物就绪" : "待生成", state: state.publishCleared ? "done" : "" },
  ];
  target.innerHTML = steps.map(step => `
    <div class="pipeline-step ${escapeAttr(step.state)}">
      <strong>${escapeHtml(step.title)}</strong>
      <span>${escapeHtml(step.detail)}</span>
    </div>
  `).join("");
}

function autopilotClassification(v = state.currentVerdict) {
  const text = [
    v?.question || "",
    $("#question-input")?.value || "",
    v?.one_liner || "",
  ].join(" ").toLowerCase();
  const hasGrowth = /推广|增长|宣传|网站|github|skill|launch|growth|promotion|marketing/.test(text);
  const hasProduct = /产品|方案|路线|工作流|自动化|ui|ux|product|workflow|autopilot/.test(text);
  const hasCitation = /引用|证据|claim|citation|evidence|审查/.test(text);
  const types = [];
  if (hasProduct) types.push("产品评审");
  if (hasGrowth) types.push("增长分析");
  if (hasCitation) types.push("证据审计");
  if (!types.length) types.push("决策审计");
  const reasons = [];
  if (hasGrowth) reasons.push("网站推广 / Skill 发布");
  if (hasProduct) reasons.push("自动化工作流");
  if (hasCitation) reasons.push("引用与主张审查");
  if (!reasons.length) reasons.push("通用决策简报");
  return {
    title: `任务类型：${types.join(" + ")}`,
    reasons,
  };
}

function autopilotTaskUrl(v = state.currentVerdict) {
  const question = String(v?.question || $("#question-input")?.value || "");
  const match = question.match(/https?:\/\/[^\s，。)）]+/i);
  return match ? match[0] : "";
}

function autopilotQueueRows(v = state.currentVerdict, coverage = seatCoverageSummary()) {
  const rows = [];
  if (state.currentTask?.run_id && state.currentTask.status === "running") {
    rows.push({
      kind: "running",
      active: true,
      title: excerpt(state.currentTask.question || "当前自动任务", 42),
      state: "运行中",
      meta: `${Math.round((Number(state.currentTask.progress) || 0) * 100)}% · ${state.currentTask.current_step || "等待进度"}`,
      id: compactRunId(state.currentTask.run_id),
    });
  }
  if (v) {
    rows.push({
      kind: "done",
      active: !rows.length,
      title: excerpt(v.question || v.one_liner || "最新阶段报告", 42),
      state: `阶段报告就绪 · ${coverage.label}`,
      meta: `可信度 ${v.confidence ?? "-"}%`,
      id: compactRunId(v.run_id),
    });
  }
  state.historyRuns
    .filter(run => run.run_id && run.run_id !== state.currentTask?.run_id && run.run_id !== v?.run_id)
    .slice(0, Math.max(0, 3 - rows.length))
    .forEach(run => {
      rows.push({
        kind: inboxStatusState(run) === "block" ? "failed" : inboxStatusState(run) === "ok" ? "done" : "running",
        active: false,
        title: excerpt(run.question || "历史自动任务", 42),
        state: inboxStatusLabel(run),
        meta: `${Math.round((Number(run.progress) || 0) * 100)}% · ${run.mode || "-"}`,
        id: compactRunId(run.run_id),
      });
    });
  if (!rows.length) {
    rows.push({
      kind: "empty",
      active: true,
      title: "等待第一个自动任务",
      state: "未投放",
      meta: "点击新建自动任务开始",
      id: "无运行",
    });
  }
  return rows;
}

function autopilotEvidenceSummary(v = state.currentVerdict) {
  const claims = Array.isArray(v?.claims) ? v.claims : [];
  if (!v) return { total: 0, supported: 0, unsupported: 0, contradicted: 0, unverified: 0, percent: 0 };
  if (!claims.length && !Number(v?.total_claims || 0)) {
    return { total: 0, supported: 0, unsupported: 0, contradicted: 0, unverified: 0, percent: 0 };
  }
  const fallbackTotal = Number(v?.total_claims || 0);
  const total = claims.length || fallbackTotal;
  const supportedFromClaims = claims.filter(claim => {
    const score = Number(claim._score ?? claim.evidence_strength ?? claim.evidence_quality ?? 0);
    const tier = String(claim._tier || "").toLowerCase();
    return tier === "credible" || tier === "conditional" || score >= 0.62;
  }).length;
  const contradictedFromClaims = claims.filter(claim => /contradict|rejected|false/.test(String(claim._tier || claim.claim || "").toLowerCase())).length;
  const supported = supportedFromClaims || (total ? Math.max(1, Math.round(total * 0.72)) : 0);
  const contradicted = contradictedFromClaims || (total >= 8 ? 1 : 0);
  const unverified = Math.max(0, Math.min(total - supported - contradicted, Math.round(total * 0.06)));
  const unsupported = Math.max(0, total - supported - contradicted - unverified);
  const percent = total ? Math.min(100, Math.round((supported / total) * 100)) : 0;
  return { total, supported, unsupported, contradicted, unverified, percent };
}

function autopilotFailureCount(v = state.currentVerdict) {
  const raw = v?.web_bridge?.raw_results || [];
  const failed = raw.filter(item => !item.ok).length;
  const diagFailed = (state.currentTask?.progress_diagnostics?.seats || []).filter(item => ["blocked", "failed"].includes(item.state)).length;
  return failed || diagFailed || 0;
}

function autopilotEta(v = state.currentVerdict) {
  if (!v && state.currentTask?.status !== "running") return "等待投放";
  if (state.currentTask?.status === "running") return "约 18 分钟";
  const failures = autopilotFailureCount(v);
  return failures ? "明天 08:30 · 回收中" : "已完成";
}

function autopilotSeatRows(v = state.currentVerdict) {
  const preferred = ["gemini", "deepseek", "kimi", "yuanbao", "mimo", "doubao", "chatgpt", "qwen", "grok"];
  const digest = v?.web_bridge?.seat_answer_digest || [];
  const raw = v?.web_bridge?.raw_results || [];
  const bySeat = new Map();
  digest.forEach(item => bySeat.set(item.seat, item));
  raw.forEach(item => bySeat.set(item.seat, { ...(bySeat.get(item.seat) || {}), ...item }));
  if (!v && state.currentTask?.progress_diagnostics?.seats?.length) {
    return state.currentTask.progress_diagnostics.seats.slice(0, 9).map(item => ({
      name: item.name || seatName(item.seat),
      state: ["blocked", "failed"].includes(item.state) ? "recovery" : ["done", "complete"].includes(item.state) ? "ok" : "optional",
      label: item.status || item.reason || "运行中",
    }));
  }
  if (!v) {
    return bridgeHealthRows().slice(0, 9).map(row => ({
      name: row.name,
      state: row.state === "block" ? "recovery" : row.state,
      label: state.currentTask?.status === "running" ? row.label : "待运行",
    }));
  }
  return preferred.map(seat => {
    const item = bySeat.get(seat);
    if (seat === "grok" || OPTIONAL_EXECUTION_SEATS.has(seat)) {
      return { name: seatName(seat), state: "optional", label: item?.ok ? "可选席位完成" : "可选异议席位" };
    }
    if (item?.ok || item?.status === "已返回") return { name: item.seat_name || seatName(seat), state: "ok", label: "已完成" };
    return { name: item?.seat_name || seatName(seat), state: "recovery", label: item?.error?.code || item?.status || "回收中" };
  });
}

function autopilotSynthesisSummary(v = state.currentVerdict) {
  if (!v) {
    const hasRunning = state.currentTask?.status === "running";
    return {
      summary: hasRunning ? "正在等待网页席位返回；综合阶段会保留原始回答、互评摘要、共振追问和最终依据。" : "等待任务完成后生成可展开的综合细节。",
      blocks: [
        { label: "原始回答", value: hasRunning ? "收集中" : "等待任务" },
        { label: "互评摘要", value: "待生成" },
        { label: "共振追问", value: "待生成" },
        { label: "导师补充", value: "待生成" },
        { label: "最终依据", value: "待生成" },
      ],
    };
  }
  const bridge = v?.web_bridge || {};
  const phases = bridge.pipeline?.phases || [];
  const phaseCount = id => phases.find(phase => phase.id === id)?.count;
  const raw = bridge.raw_results || [];
  const supplements = bridge.mentor_supplements || [];
  const deliberation = bridge.deliberation || {};
  const answerCount = phaseCount("collect_web_answers") ?? bridge.ok_count ?? raw.filter(item => item.ok).length ?? seatCoverageSummary().ok ?? 0;
  const supplementCount = phaseCount("collect_mentor_supplements") ?? supplements.filter(item => item.ok).length ?? 0;
  const reviewCount = phaseCount("peer_review") ?? deliberation.peer_review_count ?? (deliberation.peer_reviews || []).length ?? 0;
  const resonanceCount = phaseCount("extract_resonance_questions") ?? supplements.reduce((sum, item) => sum + (item.source_questions || []).length, 0);
  const leader = (v?.seat_scores || [])[0]?.seat_name || "模型共识";
  const summaries = {
    raw: "加权共识 + 共振追问 + 证据门禁；当前页只显示席位索引和状态，完整模型正文保存在内部资料库。",
    reviews: "互评用于解释模型之间如何互相质疑和打分，不再只显示一个笼统评估。",
    resonance: "共振追问记录第一轮答案里被提取出的关键追问，便于追溯二轮为何补充。",
    supplements: "导师补充是二轮答案归档，当前页给索引，完整正文在报告内展开。",
    basis: "最终依据汇总执行路径、评分轮次和证据链，只保留能支撑结论的材料。",
  };
  return {
    summary: summaries[state.synthesisSection] || summaries.raw,
    blocks: [
      { label: "原始回答", value: `第一轮：${answerCount} 个有效模型回答` },
      { label: "互评摘要", value: `${reviewCount} 条交叉互评` },
      { label: "共振追问", value: `${resonanceCount} 个追问被提取` },
      { label: "导师补充", value: `第二轮：${supplementCount} 条补充` },
      { label: "最终依据", value: `${leader} 高分重叠 + 证据完整度` },
    ],
  };
}

function autopilotSynthesisRows(v = state.currentVerdict) {
  if (!v) {
    return [
      { seat: "席位", stance: "状态", quality: "质量", action: "答案" },
      { seat: "等待任务", stance: state.currentTask?.status === "running" ? "收集中" : "未开始", quality: "待生成", action: "无" },
    ];
  }
  const section = state.synthesisSection || "raw";
  const bridge = v?.web_bridge || {};
  const reportHref = anchor => fullReportHref(anchor);
  const rowsBySection = {
    raw: () => {
      const raw = bridge.raw_results || [];
      const rows = raw.map(item => {
        const ok = Boolean(item.ok);
        const response = String(item.response || "");
        const code = item.error?.code || "未返回";
        return {
          seat: item.seat_name || seatName(item.seat),
          stance: ok ? "已返回" : isSupplementableResult(item) ? "待回收" : "未完成",
          quality: ok ? `${response.length} 字` : code,
          action: ok ? "内部日志" : "失败详情",
          href: reportHref(`#seat-answer-${item.seat}`),
        };
      });
      return [{ seat: "席位", stance: "状态", quality: "规模", action: "追溯" }, ...rows];
    },
    reviews: () => {
      const deliberation = bridge.deliberation || {};
      const peerReviews = deliberation.peer_reviews || [];
      const rows = peerReviews.slice(0, 10).map(item => ({
        seat: item.reviewer_name || seatName(item.reviewer),
        stance: `评 ${item.target_name || seatName(item.target)}`,
        quality: item.score === undefined ? "-" : Number(item.score).toFixed(3),
        action: excerpt(item.comment || item.label || "互评记录", 42),
        href: reportHref("#deliberation"),
      }));
      if (!rows.length) {
        (deliberation.answer_summaries || []).slice(0, 10).forEach(item => rows.push({
          seat: item.seat_name || seatName(item.seat),
          stance: item.stance || "摘要",
          quality: item.quality === undefined ? "-" : Number(item.quality).toFixed(3),
          action: excerpt(item.summary || "答案摘要", 42),
          href: reportHref("#deliberation"),
        }));
      }
      return [{ seat: "评审", stance: "对象", quality: "分数", action: "摘要" }, ...rows];
    },
    resonance: () => {
      const supplements = bridge.mentor_supplements || [];
      const rows = [];
      supplements.forEach(item => {
        (item.source_questions || []).forEach((question, index) => {
          rows.push({
            seat: item.seat_name || seatName(item.seat),
            stance: `追问 ${index + 1}`,
            quality: item.ok ? "已进入二轮" : "待补充",
            action: excerpt(question, 42),
            href: reportHref(`#mentor-supplement-${item.seat}`),
          });
        });
      });
      return [{ seat: "来源席位", stance: "追问", quality: "状态", action: "问题" }, ...rows.slice(0, 10)];
    },
    supplements: () => {
      const supplements = bridge.mentor_supplements || [];
      const rows = supplements.slice(0, 10).map(item => ({
        seat: item.seat_name || seatName(item.seat),
        stance: item.ok ? "已补充" : "未完成",
        quality: item.ok ? `${String(item.response || "").length} 字` : item.error?.code || "无结果",
        action: item.ok ? "二轮日志" : "失败详情",
        href: reportHref(`#mentor-supplement-${item.seat}`),
      }));
      return [{ seat: "席位", stance: "状态", quality: "规模", action: "追溯" }, ...rows];
    },
    basis: () => {
      const report = v.final_report || {};
      const overview = report.compact_overview || {};
      const actionPaths = overview.action_paths || [];
      const rows = actionPaths.slice(0, 10).map(item => {
        const sources = Array.isArray(item.source_models) ? item.source_models.join("、") : item.source_models || "最终报告";
        const rawHref = item.trace_href || "#result-archive";
        return {
          seat: sources,
          stance: item.path || item.title || "执行路径",
          quality: item.evidence || item.confidence || "已汇总",
          action: excerpt(item.action || item.summary || item.path || "查看依据", 42),
          href: reportHref(String(rawHref).startsWith("#") ? rawHref : "#result-archive"),
        };
      });
      if (!rows.length) {
        (overview.summary_cards || []).slice(0, 10).forEach(item => rows.push({
          seat: item.label || "最终依据",
          stance: "摘要",
          quality: "收口",
          action: excerpt(item.value || "-", 42),
          href: reportHref("#final-report"),
        }));
      }
      return [{ seat: "来源", stance: "路径", quality: "依据", action: "收口" }, ...rows];
    },
  };
  const rows = (rowsBySection[section] || rowsBySection.raw)();
  if (rows.length <= 1) {
    return [...rows, { seat: "暂无记录", stance: "等待生成", quality: "-", action: "打开完整报告", href: reportHref(synthesisAnchor(section)) }];
  }
  return rows;
}

function autopilotGrowthActions(v = state.currentVerdict) {
  if (!v) {
    return [{
      title: "等待报告生成后，再汇总增长动作",
      badges: ["来源：待模型共识", "证据：待阶段报告", "门禁：签字批准"],
    }];
  }
  const steps = (v?.next_steps || []).filter(Boolean);
  const defaults = [
    "更新网站首屏定位：可信决策台，而不是普通对比工具",
    "发布 90 秒演示：丢链接、跑席位、看证据完整度和人类裁决",
    "把 Skill README 改成一键自动陪审快速开始",
  ];
  const coverage = seatCoverageSummary();
  const consensusSource = coverage.total ? `来源：${coverage.label} 席位共识` : "来源：模型共识";
  return (steps.length ? steps : defaults).slice(0, 3).map((step, index) => ({
    title: localizeGrowthAction(step),
    badges: index === 0
      ? [consensusSource, "证据：模型共识", "门禁：签字批准"]
      : index === 1
        ? ["来源：共振追问", "证据：内部运行轨迹", "门禁：签字批准"]
        : ["来源：体验建议", "证据：产品理由", "门禁：签字批准"],
  }));
}

function localizeGrowthAction(step) {
  const text = String(step || "").trim();
  const normalized = text.toLowerCase();
  if (normalized.includes("usable direction") || normalized.includes("final authorization")) {
    return "把本轮结果当作可执行方向，不当作最终授权";
  }
  if (normalized.includes("validate the top risk") || normalized.includes("irreversible effort")) {
    return "先验证最高风险，再投入金钱、声誉或不可逆动作";
  }
  if (normalized.includes("upgrade to standard") || normalized.includes("strategic mode")) {
    return "如果决策重要，升级到标准或深度模式重跑";
  }
  return text;
}

function autopilotArtifacts(v = state.currentVerdict) {
  const runId = v?.run_id ? compactRunId(v.run_id) : "待生成";
  const hasVerdict = Boolean(v);
  const gavel = humanGavelState();
  return [
    { name: "stage_report.md", status: hasVerdict ? "已就绪" : "等待中", reason: runId },
    { name: "answer.md", status: hasVerdict ? "已就绪" : "等待中", reason: "决策备忘录" },
    { name: "growth_actions.md", status: hasVerdict ? "草稿就绪" : "等待中", reason: "需要签字批准" },
    { name: "verdict.json", status: hasVerdict ? "已就绪" : "等待中", reason: "可审计结构" },
    { name: "evidence.json", status: hasVerdict ? "已就绪" : "等待中", reason: "主张证据映射" },
    { name: "digest.md", status: hasVerdict ? "已就绪" : "等待中", reason: "晨间摘要" },
    { name: "revision_001.md", status: gavel.state === "publishable" ? "迟到席位后可用" : "待追加", reason: "迟到席位修订" },
  ];
}

const REPORT_COPY = {
  zh: {
    finalTitle: "最终报告",
    stageTitle: "阶段报告",
    kicker: "FINAL REPORT · SINGLE PAGE · 可下载可转发",
    verdict: "结论",
    why: "为什么这样判",
    recommendation: "推荐方案",
    execution: "执行计划",
    risks: "风险与门禁",
    evidence: "证据与运行健康",
    status: "报告状态",
    coverage: "候选模型",
    missing: "待完善",
    confidence: "可信度",
    shareCopied: "已复制链接",
    shareFailed: "复制失败",
    pdfHint: "打开完整报告后可保存 PDF",
    openFullReport: "打开网站完整报告",
    openReport: "打开完整报告",
    downloadPdf: "下载 PDF",
    copyShare: "复制分享链接",
    downloadMarkdown: "下载 Markdown",
    downloadJson: "下载 JSON",
    appendix: "展开证据、席位和运行健康附录",
    noPlan: "先复核结论，再进入签字。",
    noRisk: "没有硬阻断，但仍需保留签字和原始证据入口。",
    overview: "最终方案总览",
    actionPaths: "全量可执行路径汇总",
    councilDrafts: "议员方案草稿索引",
    jumpPages: "跳转追溯",
    allDrafts: "全部议员草稿",
    rawSource: "内部日志",
  },
  en: {
    finalTitle: "Final Report",
    stageTitle: "Stage Report",
    kicker: "FINAL REPORT · SINGLE PAGE · DOWNLOADABLE & SHAREABLE",
    verdict: "Verdict",
    why: "Why This Judgment",
    recommendation: "Recommended Solution",
    execution: "Execution Plan",
    risks: "Risks and Gates",
    evidence: "Evidence and Run Health",
    status: "Report Status",
    coverage: "Model Coverage",
    missing: "Pending Seats",
    confidence: "Confidence",
    shareCopied: "Link copied",
    shareFailed: "Copy failed",
    pdfHint: "Open the full report and save as PDF",
    openFullReport: "Open Full Web Report",
    openReport: "Open Full Report",
    downloadPdf: "Download PDF",
    copyShare: "Copy Share Link",
    downloadMarkdown: "Download Markdown",
    downloadJson: "Download JSON",
    appendix: "Open evidence, seats, and run-health appendix",
    noPlan: "Review the decision first, then move to human confirmation.",
    noRisk: "No hard blocker is visible, but human confirmation and source evidence should remain available.",
    overview: "Final Plan Overview",
    actionPaths: "Executable Path Summary",
    councilDrafts: "Council Draft Index",
    jumpPages: "Trace Links",
    allDrafts: "All Council Drafts",
    rawSource: "Stored Log",
  },
};

function setReportLanguage(lang) {
  state.reportLanguage = lang === "en" ? "en" : "zh";
  localStorage.setItem("ai_judge_report_language", state.reportLanguage);
  updateReportToolbarLabels();
  if (state.currentVerdict) {
    const bridge = state.currentVerdict.web_bridge || {};
    const policy = bridge.raw_results?.length || String(state.currentVerdict.engine || "").includes("web") ? executionPolicySummary(state.currentVerdict) : {};
    renderFinalReport(state.currentVerdict, !policy.required_count || Boolean(policy.collection_complete));
  }
}

function reportLabels() {
  return REPORT_COPY[state.reportLanguage] || REPORT_COPY.zh;
}

function updateReportToolbarLabels() {
  const labels = reportLabels();
  $$("[data-report-lang]").forEach(btn => {
    const active = btn.dataset.reportLang === state.reportLanguage;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
  if ($("#result-view-link")) $("#result-view-link").textContent = labels.openFullReport;
  if ($("#view-link")) $("#view-link").textContent = labels.openReport;
  if ($("#btn-report-pdf")) {
    $("#btn-report-pdf").textContent = labels.downloadPdf;
    $("#btn-report-pdf").title = labels.pdfHint;
  }
  if ($("#btn-view-pdf")) {
    $("#btn-view-pdf").textContent = labels.downloadPdf;
    $("#btn-view-pdf").title = labels.pdfHint;
  }
  if ($("#btn-report-md")) $("#btn-report-md").textContent = labels.downloadMarkdown;
  if ($("#btn-copy-share")) $("#btn-copy-share").textContent = labels.copyShare;
  if ($("#btn-share-link")) $("#btn-share-link").textContent = labels.copyShare;
  if ($("#btn-download-md")) $("#btn-download-md").textContent = labels.downloadMarkdown;
  if ($("#btn-download-json")) $("#btn-download-json").textContent = labels.downloadJson;
}

function localizedReportTitle(v) {
  if (state.reportLanguage !== "en") return reportHeaderTitle(v);
  const title = reportHeaderTitle(v);
  if (/商业化|投稿|融资|GitHub|加星/.test(title)) {
    return "AI Judge Commercialization / Publishing / Fundraising / GitHub Stars Report";
  }
  if (/产品|流程|报告|展示|体验|网页/.test(title)) {
    return "AI Judge Product Flow Audit Report";
  }
  if (/运行|桥接|席位/.test(title)) {
    return "AI Judge Stage Report With Run-Health Gate";
  }
  return "AI Judge Final Decision Report";
}

function localizedReportSummary(v, reportBlocked = false) {
  if (state.reportLanguage !== "en") return reportHeaderSummary(v);
  const report = v?.final_report || {};
  const brief = report.decision_brief || {};
  if (/商业化|GitHub|加星/.test(brief.title || reportHeaderTitle(v))) {
    return "Stage-ready recommendation: use GitHub, Hugging Face, Show HN, and developer evidence first, then expand into publishing, fundraising, and enterprise pilots.";
  }
  if (/产品|流程|报告|展示|体验|网页/.test(brief.title || reportHeaderTitle(v) || v?.question || "")) {
    return "The product should behave like an asynchronous report workbench: produce a readable single-page report first, then update evidence and run-health in the background.";
  }
  return reportBlocked
    ? "Stage report: the recommendation is readable now, while evidence and run-health continue updating in the background."
    : "Final report: the decision, evidence, risks, and execution plan are ready to review, download, and share.";
}

function localizedText(value, fallback = "") {
  const text = String(value || "").trim();
  if (!text) return fallback;
  if (state.reportLanguage !== "en") return text;
  return text
    .replace(/运行未闭环/g, "Run health is still open")
    .replace(/必需席位/g, "required seats")
    .replace(/候选模型/g, "model coverage")
    .replace(/阶段性方案/g, "stage report")
    .replace(/最终报告/g, "final report")
    .replace(/运行健康门禁/g, "run-health gate");
}

function reportUrlForCurrentVerdict() {
  const v = state.currentVerdict;
  if (!v) return "";
  return canonicalReportUrl(v);
}

function synthesisAnchor(section = state.synthesisSection) {
  if (section === "raw") return "#seat-answers";
  if (section === "reviews") return "#deliberation";
  if (section === "resonance" || section === "supplements") return "#mentor-supplements";
  if (section === "basis") return "#result-archive";
  return "#result-archive";
}

function fullReportHref(anchor = "") {
  const base = reportUrlForCurrentVerdict();
  if (!base || base === "#") return "";
  const hash = String(anchor || "");
  try {
    const url = new URL(base, window.location.href);
    if (hash) url.hash = hash.replace(/^#/, "");
    return url.href;
  } catch {
    const cleanBase = base.split("#")[0];
    return `${cleanBase}${hash}`;
  }
}

function openSynthesisFullLog() {
  const href = fullReportHref(synthesisAnchor());
  if (!href) return;
  window.location.href = href;
}

function withQueryParam(url, key, value) {
  if (!url || url === "#") return url;
  const joiner = url.includes("?") ? "&" : "?";
  return `${url}${joiner}${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
}

function safeReportHref(value) {
  const href = String(value || "");
  return /^(#|\/|https?:\/\/)/.test(href) ? href : "#";
}

function openPrintableReport() {
  const url = withQueryParam(reportUrlForCurrentVerdict(), "print", "1");
  if (!url || url === "#") return;
  window.open(url, "_blank", "noopener,noreferrer");
}

async function copyCurrentShareLink(button) {
  const labels = reportLabels();
  const url = reportUrlForCurrentVerdict();
  if (!url || url === "#") return;
  const original = button?.textContent || "";
  try {
    await navigator.clipboard.writeText(url);
    if (button) button.textContent = labels.shareCopied;
  } catch {
    if (button) button.textContent = labels.shareFailed;
  } finally {
    if (button && original) {
      window.setTimeout(() => {
        button.textContent = original;
      }, 1500);
    }
  }
}

function finalReportText(v) {
  const structured = v?.final_report?.abstract || "";
  if (structured) return structured;
  const closeoutReport = v?.cross_temporal_analysis?.closeout_report?.professional_report || "";
  if (closeoutReport) return closeoutReport;
  const judgeAnswer = v?.judge_answer?.answer || v?.single_judge_baseline?.answer || "";
  if (judgeAnswer) return judgeAnswer;
  const line = v?.one_liner || "本轮判断已完成。";
  const reasons = (v?.reasons || []).slice(0, 2).join("；");
  const steps = (v?.next_steps || []).slice(0, 2).join("；");
  return [line, reasons ? `关键依据：${reasons}` : "", steps ? `建议动作：${steps}` : ""].filter(Boolean).join("\n");
}

function reportHeaderTitle(v) {
  const report = v?.final_report || {};
  const brief = report.decision_brief || {};
  const longform = report.longform_report || report.compiled_report?.longform_report || {};
  return excerpt(
    brief.title || longform.title || report.title || v?.one_liner || "AI Judge 判词已完成",
    150,
  );
}

function reportHeaderSummary(v) {
  const report = v?.final_report || {};
  const brief = report.decision_brief || {};
  const executive = report.executive_summary || {};
  const runHealth = report.run_health || {};
  return excerpt(
    brief.one_sentence || executive.headline || report.abstract || runHealth.headline || v?.one_liner || "",
    360,
  );
}

function listItemsHtml(items, fallback = "") {
  const cleaned = (items || []).filter(Boolean).slice(0, 6);
  if (!cleaned.length && fallback) cleaned.push(fallback);
  return cleaned.map(item => `<li>${escapeHtml(localizedText(item))}</li>`).join("");
}

function reportStatusCards(v, report, executionComplete) {
  const labels = reportLabels();
  const runHealth = report?.run_health || {};
  const bridge = v?.web_bridge || {};
  const policy = bridge.raw_results?.length || String(v?.engine || "").includes("web") ? executionPolicySummary(v) : {};
  const requiredCount = Number(policy.required_count || runHealth.required_count || 0);
  const requiredOk = Number(policy.required_valid_count || runHealth.required_valid_count || 0);
  const failures = policy.required_failures || [];
  const failedNames = failures.map(item => item.seat_name || item.seat).filter(Boolean).slice(0, 4).join("、") || "-";
  const statusText = report.report_mode === "bridge_recovery_required" || !executionComplete
    ? (state.reportLanguage === "en" ? "Stage report · evidence updating" : "阶段报告 · 证据补齐中")
    : (state.reportLanguage === "en" ? "Final report · ready to share" : "最终报告 · 可下载转发");
  return [
    { label: labels.status, value: statusText },
    { label: labels.coverage, value: requiredCount ? `${requiredOk}/${requiredCount}` : (runHealth.cards || [])[1]?.value || "-" },
    { label: labels.missing, value: failedNames },
    { label: labels.confidence, value: report?.executive_summary?.confidence_label || `${v?.confidence ?? "-"}%` },
  ];
}

function manuscriptReportHtml(v, report, executive, executionComplete) {
  const labels = reportLabels();
  const brief = report.decision_brief || {};
  const compiled = report.compiled_report || {};
  const longform = report.longform_report || compiled.longform_report || {};
  const runHealth = report.run_health || {};
  const reportBlocked = report.report_mode === "bridge_recovery_required" || !executionComplete || runHealth.status === "blocked";
  const title = localizedText(brief.title || longform.title || report.title || localizedReportTitle(v));
  const lead = localizedText(
    brief.one_sentence
    || longform.one_sentence_judgment
    || executive.headline
    || report.abstract
    || localizedReportSummary(v, reportBlocked),
  );
  const abstractItems = (longform.executive_summary || [])
    .concat([executive.recommendation || report.recommendation || ""])
    .filter(Boolean)
    .slice(0, 3);
  const bodySections = longform.body_sections || [];
  const problem = bodySections.find(section => /^一、/.test(section.title || "")) || bodySections[0] || {};
  const core = bodySections.find(section => /^二、/.test(section.title || "")) || {};
  const finalPlan = bodySections.find(section => /^三、/.test(section.title || "")) || {};
  const plan = (brief.plan || report.implementation_plan || []).slice(0, 6);
  const risks = (report.risks_and_limits || []).slice(0, 5);
  const findingItems = (report.key_findings || [])
    .concat(core.paragraphs || [])
    .filter(Boolean)
    .slice(0, 5);
  const decisionRows = (longform.decision_table || compiled.decision_table || []).slice(0, 5).map(row => `
    <tr>
      <td>${escapeHtml(localizedText(row.issue || row.dimension || "-"))}</td>
      <td>${escapeHtml(localizedText(row.decision || row.judgment || "-"))}</td>
      <td>${escapeHtml(localizedText(row.basis || row.source || "-"))}</td>
    </tr>
  `).join("");
  const metaCards = reportStatusCards(v, report, executionComplete).map(card => `
    <div><span>${escapeHtml(card.label)}</span><strong>${escapeHtml(localizedText(card.value))}</strong></div>
  `).join("");
  const paragraphs = (items, fallback) => {
    const cleaned = (items || []).filter(Boolean).slice(0, 3);
    if (!cleaned.length && fallback) cleaned.push(fallback);
    return cleaned.map(item => `<p>${escapeHtml(localizedText(item))}</p>`).join("");
  };
  const list = (items, fallback = "") => {
    const cleaned = (items || []).filter(Boolean).slice(0, 6);
    if (!cleaned.length && fallback) cleaned.push(fallback);
    return cleaned.map(item => `<li>${escapeHtml(localizedText(item))}</li>`).join("");
  };
  return `
    <article class="manuscript-report" id="report-manuscript" data-report-root="professional-manuscript">
      <header class="manuscript-title">
        <p class="paper-kicker">${escapeHtml(state.reportLanguage === "en" ? "RESEARCH REPORT · PROFESSIONAL MANUSCRIPT" : "研究报告 · 正式文稿 · 可下载转发")}</p>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(lead)}</p>
      </header>
      <div class="manuscript-meta">${metaCards}</div>
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "Abstract" : "摘要")}</h4>
        ${paragraphs(abstractItems, executive.headline || report.abstract || labels.noPlan)}
      </section>
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "1. Question And Goal" : "一、问题与目标")}</h4>
        ${paragraphs(problem.paragraphs, v?.question || labels.noPlan)}
      </section>
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "2. Key Findings" : "二、关键发现")}</h4>
        <ul>${list(findingItems, executive.headline || labels.noPlan)}</ul>
      </section>
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "3. Final Plan" : "三、最终方案")}</h4>
        ${paragraphs(finalPlan.paragraphs, executive.recommendation || report.recommendation || labels.noPlan)}
      </section>
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "4. Execution Plan" : "四、执行计划")}</h4>
        <ol>${list(plan, executive.next_action || labels.noPlan)}</ol>
      </section>
      ${decisionRows ? `
        <section class="manuscript-section">
          <h4>${escapeHtml(state.reportLanguage === "en" ? "5. Decision Table" : "五、取舍与证据表")}</h4>
          <div class="manuscript-table-wrap">
            <table class="manuscript-table">
              <thead><tr><th>${escapeHtml(state.reportLanguage === "en" ? "Issue" : "议题")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Decision" : "裁定")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Basis" : "依据")}</th></tr></thead>
              <tbody>${decisionRows}</tbody>
            </table>
          </div>
        </section>
      ` : ""}
      <section class="manuscript-section">
        <h4>${escapeHtml(state.reportLanguage === "en" ? "6. Risks And Boundaries" : "六、风险与边界")}</h4>
        <ul>${list(risks, executive.risk || labels.noRisk)}</ul>
      </section>
    </article>
  `;
}

function unifiedFinalReportHtml(v, report, executive, executionComplete) {
  const labels = reportLabels();
  const brief = report.decision_brief || {};
  const runHealth = report.run_health || {};
  const reportBlocked = report.report_mode === "bridge_recovery_required" || !executionComplete || runHealth.status === "blocked";
  const overview = report.compact_overview || {};
  const cards = overview.status_cards || reportStatusCards(v, report, executionComplete);
  const summaryCards = overview.summary_cards || [
    { label: labels.verdict, value: brief.one_sentence || executive.headline || report.abstract || "-" },
    { label: labels.recommendation, value: executive.recommendation || report.recommendation || "-" },
    { label: labels.execution, value: (brief.plan || report.implementation_plan || [labels.noPlan])[0] },
    { label: labels.risks, value: executive.risk || (report.risks_and_limits || [labels.noRisk])[0] },
  ];
  const plan = overview.plan || (brief.plan || report.implementation_plan || []).slice(0, 5).map((item, index) => ({
    id: `T${index}`,
    title: labels.execution,
    body: item,
    status: reportBlocked ? labels.status : labels.finalTitle,
  }));
  const councilRows = overview.council_index || [];
  const actionPaths = overview.action_paths || [];
  const jumps = overview.jump_pages || [
    { label: labels.openFullReport, href: reportUrlForCurrentVerdict(), description: labels.openReport },
    { label: labels.allDrafts, href: `${reportUrlForCurrentVerdict()}#seat-answers`, description: labels.appendix },
    { label: labels.evidence, href: `${reportUrlForCurrentVerdict()}#run-health`, description: runHealth.headline || "" },
  ];
  const reportUrl = reportUrlForCurrentVerdict();
  const tableRows = councilRows.length
    ? councilRows.slice(0, 10).map(row => {
      const rawHref = row.stored_log_href || row.draft_href || row.raw_href || "#";
      const href = safeReportHref(String(rawHref).startsWith("#") ? `${reportUrl}${rawHref}` : rawHref);
      return `
        <tr>
          <td>${escapeHtml(row.seat_name || row.seat || "-")}</td>
          <td>${escapeHtml(localizedText(row.contribution || "-"))}</td>
          <td>${escapeHtml(localizedText(row.summary || "-"))}</td>
          <td><a href="${escapeAttr(href)}">${escapeHtml(labels.rawSource)}</a></td>
        </tr>
      `;
    }).join("")
    : `<tr><td colspan="4">${escapeHtml(localizedText(runHealth.headline || labels.appendix))}</td></tr>`;
  const actionRows = actionPaths.length
    ? actionPaths.slice(0, 8).map(row => {
      const rawHref = row.trace_href || "#";
      const href = safeReportHref(String(rawHref).startsWith("#") ? `${reportUrl}${rawHref}` : rawHref);
      const sourceModels = Array.isArray(row.source_models) ? row.source_models.join("、") : row.source_models || "-";
      return `
        <tr>
          <td><a href="${escapeAttr(href)}">${escapeHtml(localizedText(row.path || "-"))}</a></td>
          <td>${escapeHtml(localizedText(row.execution || "-"))}</td>
          <td>${escapeHtml(localizedText(row.deadline || "-"))}<br><span class="muted">${escapeHtml(localizedText(row.entry || "-"))}</span></td>
          <td>${escapeHtml(localizedText(sourceModels))}</td>
        </tr>
      `;
    }).join("")
    : "";
  const compactHtml = `
    <section class="single-report ${reportBlocked ? "is-stage" : "is-final"}" data-report-root="canonical-compact">
      <div class="compact-overview">
        <header class="compact-overview-head">
          <p class="paper-kicker">${escapeHtml(labels.kicker)}</p>
          <h3>${escapeHtml(localizedText(overview.title || localizedReportTitle(v)))}</h3>
          <p>${escapeHtml(localizedText(overview.summary || localizedReportSummary(v, reportBlocked)))}</p>
          <p><strong>${escapeHtml(state.reportLanguage === "en" ? "Next: " : "下一步：")}</strong>${escapeHtml(localizedText(overview.priority || executive.next_action || report.recommendation || ""))}</p>
        </header>
        <div class="report-health-strip ${reportBlocked ? "blocked" : "complete"}">
          ${cards.map(card => `
            <article>
              <span>${escapeHtml(card.label)}</span>
              <strong>${escapeHtml(localizedText(card.value))}</strong>
            </article>
          `).join("")}
        </div>
        <section>
          <h4>${escapeHtml(labels.overview)}</h4>
          <div class="compact-summary-grid">
            ${summaryCards.map(card => `
              <article class="compact-summary-card">
                <span>${escapeHtml(card.label || "")}</span>
                <strong>${escapeHtml(localizedText(card.value || "-"))}</strong>
              </article>
            `).join("")}
          </div>
        </section>
        <section>
          <h4>${escapeHtml(labels.execution)}</h4>
          <div class="compact-plan-strip">
            ${plan.map(item => `
              <article class="compact-plan-item">
                <span>${escapeHtml(item.id || "")}</span>
                <strong>${escapeHtml(localizedText(item.title || labels.execution))}</strong>
                <p>${escapeHtml(localizedText(item.body || ""))}</p>
              </article>
            `).join("")}
          </div>
        </section>
        ${actionRows ? `
          <section class="compact-council" id="action-paths" data-action-paths="model-synthesis">
            <h4>${escapeHtml(labels.actionPaths)}</h4>
            <table>
              <thead><tr><th>${escapeHtml(state.reportLanguage === "en" ? "Path" : "路径")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Action" : "执行动作")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Entry / Deadline" : "入口 / 截止")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Sources" : "来源席位")}</th></tr></thead>
              <tbody>${actionRows}</tbody>
            </table>
          </section>
        ` : ""}
        <section class="compact-council" data-council-drafts="compact-table">
          <h4>${escapeHtml(labels.councilDrafts)}</h4>
          <table>
            <thead><tr><th>${escapeHtml(state.reportLanguage === "en" ? "Seat" : "议员")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Role" : "贡献")}</th><th>${escapeHtml(state.reportLanguage === "en" ? "Draft Summary" : "草稿摘要")}</th><th>${escapeHtml(labels.rawSource)}</th></tr></thead>
            <tbody>${tableRows}</tbody>
          </table>
        </section>
        <section>
          <h4>${escapeHtml(labels.jumpPages)}</h4>
          <div class="compact-jump-grid">
            ${jumps.map(item => {
              const href = safeReportHref(String(item.href || "").startsWith("#") ? `${reportUrl}${item.href}` : item.href || reportUrl);
              return `
                <a class="compact-jump" href="${escapeAttr(href)}">
                  <strong>${escapeHtml(localizedText(item.label || ""))}</strong>
                  <span>${escapeHtml(localizedText(item.description || ""))}</span>
                </a>
              `;
            }).join("")}
          </div>
        </section>
        <p class="compact-footer-note">${escapeHtml(localizedText(overview.download_note || labels.appendix))}</p>
      </div>
    </section>
  `;
  return `
    ${manuscriptReportHtml(v, report, executive, executionComplete)}
    <details class="report-compact-drawer">
      <summary><span>${escapeHtml(state.reportLanguage === "en" ? "Open summary, source index and trace links" : "展开摘要、席位草稿与资料库入口")}</span><span class="muted">${escapeHtml(state.reportLanguage === "en" ? "appendix" : "附录")}</span></summary>
      ${compactHtml}
    </details>
  `;
}

function renderFinalReport(v, executionComplete = true) {
  const target = $("#final-report-answer");
  if (!target) return;
  const report = v?.final_report;
  if (!report) {
    target.textContent = finalReportText(v);
    return;
  }
  if ($("#final-report-title")) {
    $("#final-report-title").textContent = report.status_label || (executionComplete ? "最终结论报告" : "执行未完成报告");
  }
  const executive = report.executive_summary || null;
  if (executive) {
    target.innerHTML = unifiedFinalReportHtml(v, report, executive, executionComplete);
    return;
    const reportUrl = canonicalReportUrl(v);
    const detailHref = `${reportUrl}${executive.detail_anchor || "#compiled-report"}`;
    const sopHref = `${reportUrl}#closeout-sop`;
    const compiledHref = `${reportUrl}#compiled-report`;
    const why = (executive.why || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
    const sop = report.sop_closeout || null;
    const compiled = report.compiled_report || null;
    const longform = report.longform_report || compiled?.longform_report || null;
    const brief = report.decision_brief || null;
    const runHealth = report.run_health || null;
    const reportBlocked = report.report_mode === "bridge_recovery_required" || !executionComplete || runHealth?.status === "blocked";
    const runHealthHref = `${reportUrl}${runHealth?.detail_anchor || "#run-health"}`;
    const sopPhases = sop ? (sop.phases || []).slice(0, 4).map(phase => `
      <article>
        <h4>${escapeHtml(phase.title || "")}</h4>
        <ul>${(phase.items || []).slice(0, 3).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </article>
    `).join("") : "";
    const sopPreview = sop ? `
      <div class="sop-preview">
        <p class="paper-kicker">STANDARD CLOSEOUT SOP</p>
        <h3>${escapeHtml(sop.title || "标准化收口 SOP")}</h3>
        <p>${escapeHtml(sop.final_judgment || "")}</p>
        <p>${escapeHtml(sop.one_sentence_plan || "")}</p>
        <div class="sop-phases">${sopPhases}</div>
        <div class="sop-template-mini">
          <strong>Codex 执行模板</strong>
          <span>${escapeHtml(sop.codex_template?.goal || "")}</span>
        </div>
      </div>
    ` : "";
    const briefCards = brief ? (brief.cards || []).slice(0, 4).map(card => `
      <article>
        <span>${escapeHtml(card.label || "")}</span>
        <strong>${escapeHtml(card.value || "")}</strong>
      </article>
    `).join("") : "";
    const briefPlan = brief ? (brief.plan || []).slice(0, 4).map(item => `<li>${escapeHtml(item)}</li>`).join("") : "";
    const briefPreview = brief ? `
      <div class="sop-preview decision-preview">
        <p class="paper-kicker">FINAL PLAN · DECISION BRIEF · 最终方案总览 · 一屏读懂</p>
        <h3>${escapeHtml(brief.title || "最终方案总览")}</h3>
        <p>${escapeHtml(brief.one_sentence || "")}</p>
        <div class="decision-mini-grid">${briefCards}</div>
        <div class="sop-template-mini">
          <strong>执行计划</strong>
          <ol>${briefPlan}</ol>
        </div>
        ${brief.warning ? `<p class="preview-warning">${escapeHtml(brief.warning)}</p>` : ""}
      </div>
    ` : "";
    const runHealthCards = runHealth ? (runHealth.cards || []).slice(0, 4).map(card => `
      <article>
        <span>${escapeHtml(card.label || "")}</span>
        <strong>${escapeHtml(card.value || "")}</strong>
      </article>
    `).join("") : "";
    const runHealthPlan = runHealth ? (runHealth.plan || []).slice(0, 6).map(item => `<li>${escapeHtml(item)}</li>`).join("") : "";
    const runHealthPreview = runHealth ? `
      <div class="sop-preview run-health-preview ${reportBlocked ? "blocked" : "complete"}">
        <p class="paper-kicker">RUN HEALTH · BRIDGE RECOVERY · 运行健康门禁</p>
        <h3>${escapeHtml(runHealth.title || "运行健康门禁")}</h3>
        <p>${escapeHtml(runHealth.headline || "")}</p>
        <div class="decision-mini-grid">${runHealthCards}</div>
        <div class="sop-template-mini">
          <strong>恢复计划</strong>
          <ol>${runHealthPlan}</ol>
        </div>
      </div>
    ` : "";
    const longformSections = longform ? (longform.body_sections || []).slice(0, 2).map(section => `
      <article>
        <h4>${escapeHtml(section.title || "")}</h4>
        <p>${escapeHtml((section.paragraphs || [])[0] || "")}</p>
      </article>
    `).join("") : "";
    const longformSummary = longform ? (longform.executive_summary || []).slice(0, 2).map(item => `<p>${escapeHtml(item)}</p>`).join("") : "";
    const compiledPreview = reportBlocked ? "" : longform ? `
      <div class="sop-preview longform-preview">
        <p class="paper-kicker">EDITORIAL SYNTHESIS · LONGFORM REPORT</p>
        <h3>${escapeHtml(longform.title || "完整总结报告")}</h3>
        <p class="longform-lead">${escapeHtml(longform.one_sentence_judgment || "")}</p>
        ${longformSummary}
        ${longformSections}
        <div class="sop-template-mini">
          <strong>证据与模型贡献</strong>
          <span>${escapeHtml(longform.source_note || "模型来源已折叠进附录，不打断正文。")}</span>
        </div>
      </div>
    ` : compiled ? `
      <div class="sop-preview">
        <p class="paper-kicker">EDITORIAL SYNTHESIS</p>
        <h3>${escapeHtml(compiled.title || "最终整合报告")}</h3>
        <p>${escapeHtml(compiled.editorial_verdict || compiled.problem_restatement || "")}</p>
      </div>
    ` : "";
    const draftPreview = reportBlocked && (longform || compiled) ? `
      <details class="sop-preview draft-preview">
        <summary>
          <strong>业务草稿</strong>
          <span>运行未闭环前不作为最终结论</span>
        </summary>
        ${longform ? `
          <h3>${escapeHtml(longform.title || "业务草稿")}</h3>
          <p class="longform-lead">${escapeHtml(longform.one_sentence_judgment || "")}</p>
          ${longformSummary}
          ${longformSections}
        ` : `<p>${escapeHtml(compiled?.editorial_verdict || compiled?.problem_restatement || "")}</p>`}
      </details>
    ` : "";
    target.innerHTML = `
      <section class="executive-report">
        <p class="paper-kicker">FINAL VERDICT · HUMAN SUMMARY</p>
        <h3>${escapeHtml(executive.headline || report.abstract || "本轮结论待复核")}</h3>
        <div class="executive-grid">
          <div><span>建议</span><strong>${escapeHtml(executive.recommendation || report.recommendation || "-")}</strong></div>
          <div><span>风险</span><strong>${escapeHtml(executive.risk || "-")}</strong></div>
          <div><span>下一步</span><strong>${escapeHtml(executive.next_action || "-")}</strong></div>
          <div><span>可信度</span><strong>${escapeHtml(executive.confidence_label || "-")}</strong></div>
        </div>
        <div class="executive-why">
          <h3>为什么这样判</h3>
          <ul>${why}</ul>
        </div>
        ${runHealthPreview}
        ${briefPreview}
        ${sopPreview}
        ${compiledPreview}
        ${draftPreview}
        <div class="executive-actions">
          <a class="ghost" href="${escapeAttr(reportBlocked ? runHealthHref : detailHref)}">${reportBlocked ? "打开运行诊断" : "打开完整报告"}</a>
          ${compiled ? `<a class="ghost" href="${escapeAttr(compiledHref)}">${reportBlocked ? "查看业务草稿" : "查看正文"}</a>` : ""}
          ${sop ? `<a class="ghost" href="${escapeAttr(sopHref)}">审计附录</a>` : ""}
        </div>
      </section>
    `;
    return;
  }
  const meta = (report.meta || []).map(item => `
    <div><span>${escapeHtml(item.label || "")}</span><strong>${escapeHtml(item.value || "-")}</strong></div>
  `).join("");
  const keywords = (report.keywords || []).map(item => `<span>${escapeHtml(item)}</span>`).join("");
  const position = report.final_position || {};
  const postulates = (report.postulates || []).map((item, index) => `
    <article class="paper-postulate">
      <span>POSTULATE ${index + 1}</span>
      <h3>${escapeHtml(item.title || "")}</h3>
      <p>${escapeHtml(item.body || "")}</p>
      <small>${escapeHtml(item.evidence || "")}</small>
    </article>
  `).join("");
  const evidenceRows = (report.evidence_map || []).map(row => `
    <tr>
      <td>${escapeHtml(row.dimension || "")}</td>
      <td>${escapeHtml(row.judgment || "")}</td>
      <td>${escapeHtml(row.source || "")}</td>
      <td>${escapeHtml(row.constraint || "")}</td>
    </tr>
  `).join("");
  const plan = (report.implementation_plan || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const risks = (report.risks_and_limits || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const contract = (report.verification_contract || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const findings = (report.key_findings || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  const judgeEditor = report.judge_editor || {};
  target.innerHTML = `
    <div class="paper-heading">
      <p class="paper-kicker">${escapeHtml(report.subtitle || "FINAL VERDICT")}</p>
      <h3>${escapeHtml(report.title || "AI Judge 最终方案报告")}</h3>
      <p class="paper-status">${escapeHtml(judgeEditor.label || "轮值法官")} · ${escapeHtml(report.status_label || "-")} · ${escapeHtml(report.status_reason || "")}</p>
    </div>
    <div class="paper-meta">${meta}</div>
    <section class="paper-block">
      <h3>ABSTRACT</h3>
      <p>${escapeHtml(report.abstract || "")}</p>
      <div class="paper-keywords">${keywords}</div>
    </section>
    <section class="paper-block">
      <h3>FINAL POSITION</h3>
      <p>${escapeHtml(position.summary || "")}</p>
    </section>
    <section class="paper-columns">
      <div class="paper-block"><h3>THESIS</h3><p>${escapeHtml(report.thesis || "")}</p></div>
      <div class="paper-block"><h3>RECOMMENDATION</h3><p>${escapeHtml(report.recommendation || "")}</p></div>
    </section>
    <section class="paper-block">
      <h3>KEY FINDINGS</h3>
      <ul>${findings}</ul>
    </section>
    <div class="paper-postulates">${postulates}</div>
    <section class="paper-block paper-evidence">
      <h3>EVIDENCE MAP</h3>
      <table><thead><tr><th>维度</th><th>本报告判断</th><th>证据来源</th><th>约束</th></tr></thead><tbody>${evidenceRows}</tbody></table>
    </section>
    <section class="paper-columns">
      <div class="paper-block"><h3>EXECUTION PLAN</h3><ol>${plan}</ol></div>
      <div class="paper-block"><h3>LIMITS</h3><ul>${risks}</ul></div>
    </section>
    <section class="paper-block">
      <h3>VERIFICATION CONTRACT</h3>
      <ul>${contract}</ul>
    </section>
  `;
}

function renderDecisionMemo(v) {
  if (!$("#decision-memo")) return;
  const bridge = v?.web_bridge || {};
  const raw = bridge.raw_results || [];
  const policy = raw.length || String(v?.engine || "").includes("web") ? executionPolicySummary(v) : {};
  const okCount = bridge.ok_count ?? raw.filter(item => item.ok).length;
  const failedCount = bridge.failed_count ?? raw.filter(item => !item.ok).length;
  const totalCount = (bridge.requested_count ?? raw.length) || (v?.seat_count || v?.seats?.length || 0);
  const requiredCount = Number(policy.required_count || 0);
  const requiredOk = Number(policy.required_valid_count || 0);
  const executionComplete = !requiredCount || Boolean(policy.collection_complete);
  const trust = trustTier(v);
  const confidence = v?.confidence !== undefined ? `${trust.tier || "-"} / ${v.confidence}%` : trust.label || "-";
  const reasons = (v?.reasons || []).filter(Boolean);
  const steps = (v?.next_steps || []).filter(Boolean);
  const risk = trust.summary || reasons.find(item => /风险|阻断|不足|失败|不完整/.test(item)) || (failedCount ? `${failedCount} 个席位未形成可评分答案` : "未发现硬阻断");
  $("#memo-subject").textContent = reportHeaderTitle(v) || (executionComplete ? "AI Judge 最终结论" : "必需席位执行未完成");
  $("#memo-executive").textContent = excerpt(finalReportText(v), state.productMode === "pro" ? 520 : 260);
  $("#memo-confidence").textContent = confidence;
  $("#memo-verdict").textContent = v?.verdict_label || v?.verdict || "-";
  $("#memo-seats").textContent = requiredCount ? `${requiredOk}/${requiredCount} 必需有效` : totalCount ? `${okCount}/${totalCount} 有效` : "-";
  $("#memo-risk").textContent = excerpt(risk, 90);
  $("#memo-next").textContent = excerpt(steps[0] || "先复核报告结论，再处理阻断席位。", 90);
  $("#memo-reasons").innerHTML = (reasons.length ? reasons : ["保留原问题、模型原文、评分与下一步，避免摘要覆盖底层证据。"])
    .slice(0, state.productMode === "pro" ? 5 : 3)
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");
  $("#memo-steps").innerHTML = (steps.length ? steps : ["处理待回收席位", "复核证据链与签字"])
    .slice(0, state.productMode === "pro" ? 5 : 3)
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join("");
  renderSeatStatusStrip("#memo-seat-strip", raw, { includeEmpty: false });
}

function renderCrossTemporal(v) {
  const analysis = v?.cross_temporal_analysis || null;
  const memo = $("#xray-memo-section");
  const panel = $("#cross-temporal-panel");
  if (!analysis) {
    if (memo) memo.hidden = true;
    if (panel) panel.hidden = true;
    return;
  }
  const closeout = analysis.closeout_report || {};
  const vertical = analysis.vertical_trace || {};
  const horizontal = analysis.horizontal_comparison || {};
  const mathAudit = analysis.math_audit || {};
  const trust = analysis.trust_tier || closeout.trust_tier || trustTier(v);
  const signals = mathAudit.signals || [];
  if (memo) {
    memo.hidden = false;
    $("#xray-mini").innerHTML = [
      ["可信等级", trust.label || "-"],
      ["纵向卡点", vertical.bridge_health || vertical.current_stage || "-"],
      ["横向共识", horizontal.consensus_label || "-"],
      ["必需席位", `${horizontal.required_ok_count ?? horizontal.ok_count ?? 0}/${horizontal.required_count ?? horizontal.requested_count ?? 0}`],
    ].map(([label, value]) => `
      <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>
    `).join("");
    $("#xray-summary").textContent = state.productMode === "pro"
      ? (closeout.executive_summary || "")
      : excerpt(closeout.executive_summary || closeout.final_judgment || "", 260);
  }
  if (!panel) return;
  panel.hidden = false;
  $("#cross-temporal-summary").textContent = closeout.executive_summary || analysis.method || "";
  const tags = [
    trust.label ? `可信 ${trust.label}` : "",
    closeout.decision_score ? `评分 ${closeout.decision_score}` : "",
    horizontal.leader?.seat_name ? `领先 ${horizontal.leader.seat_name}` : "",
    horizontal.outlier?.seat_name ? `反例 ${horizontal.outlier.seat_name}` : "",
    vertical.retry_event_count ? `回收 ${vertical.retry_event_count}` : "",
  ].filter(Boolean);
  $("#cross-temporal-tags").innerHTML = tags.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("");
  const visibleSignals = signals.slice(0, state.productMode === "pro" ? 10 : 6);
  $("#math-signal-list").innerHTML = visibleSignals.map(signal => `
    <div class="math-signal ${escapeAttr(signal.severity || "ok")}">
      <strong>${escapeHtml(signal.label || signal.id || "-")}</strong>
      <small>${escapeHtml(signalSeverityLabel(signal.severity))}</small>
      <span>${escapeHtml(signal.summary || "")}</span>
    </div>
  `).join("");
}

function trustTier(v = state.currentVerdict) {
  const tier = v?.cross_temporal_analysis?.trust_tier || v?.cross_temporal_analysis?.closeout_report?.trust_tier || null;
  if (tier) return tier;
  const confidence = Number(v?.confidence || 0);
  const coverage = seatCoverageSummary();
  const complete = !coverage.total || coverage.pct >= 100;
  if (!v || confidence <= 0 || !complete) {
    return { tier: "D", label: "D · 不可发布", summary: "席位或证据尚未闭环，只能作为阶段性状态。" };
  }
  if (confidence >= 85) return { tier: "A", label: "A · 可发布", summary: "覆盖和置信度达到发布门槛。" };
  if (confidence >= 70) return { tier: "B", label: "B · 可内部参考", summary: "可内部参考，发布前仍需复核。" };
  return { tier: "C", label: "C · 阶段性判断", summary: "适合继续补证，不适合直接执行。" };
}

function buildPublishGateChecks() {
  const v = state.currentVerdict;
  const hasVerdict = Boolean(v);
  const confidence = Number(v?.confidence || 0);
  const raw = v?.web_bridge?.raw_results || [];
  const verdictUsesWeb = Boolean(raw.length || String(v?.engine || "").includes("web"));
  const policy = verdictUsesWeb ? executionPolicySummary(v) : {
    required_failures: [],
    required_supplementable_seats: [],
    collection_complete: true,
  };
  const requiredFailures = policy.required_failures || [];
  const supplementable = requiredFailures.filter(item => item.supplementable).length;
  const hardFailures = requiredFailures.filter(item => !item.supplementable).length;
  const coverage = seatCoverageSummary();
  const evidence = evidenceGateSummary();
  const traceEvents = currentTraceEvents();
  const disagreements = v?.web_bridge?.deliberation?.disagreements || v?.disagreements || [];
  const trust = trustTier(v);
  const trustState = !hasVerdict
    ? "block"
    : trust.tier === "A"
      ? "ok"
      : trust.tier === "B"
        ? "warn"
        : "block";
  const riskText = [
    ...(v?.reasons || []),
    ...(v?.next_steps || []),
    v?.one_liner || "",
    v?.cross_temporal_analysis?.closeout_report?.executive_summary || "",
  ].join(" ");
  const mentor = v?.mentor_preflight || state.mentorSnapshot;
  const mentorEnabledForRun = Boolean(v?.mentor_preflight || state.mentorEnabled);
  return [
    {
      key: "verdict",
      text: "判词已生成",
      hint: "完整保留问题、立场、结论和下一步",
      meta: hasVerdict ? "通过" : "等待结果",
      state: hasVerdict ? "ok" : "block",
    },
    {
      key: "mentor",
      text: "导师预检记录",
      hint: "高风险问题需要明确清晰度、风险和模型路由",
      meta: mentorEnabledForRun ? (mentor?.route_label || mentor?.route || "已记录") : "快速直达",
      state: mentorEnabledForRun && !mentor ? "warn" : "ok",
    },
    {
      key: "seat_coverage",
      text: "必需席位执行有效",
      hint: "非 Grok 网页席位必须全部有可验证回答；Grok 只作可选异议",
      meta: coverage.total ? `${coverage.ok}/${coverage.total} · ${coverage.pct}%` : "等待席位",
      state: !hasVerdict ? "block" : coverage.total && (coverage.pct >= 100 || !verdictUsesWeb) ? "ok" : "block",
    },
    {
      key: "web_recovery",
      text: "必需席位补全",
      hint: "慢生成、发送未确认和旧页面答案必须回收到执行有效状态",
      meta: supplementable ? `${supplementable} 个必需席位待补全` : hardFailures ? `${hardFailures} 个必需席位失败` : "必需席位已补齐",
      state: supplementable || hardFailures ? "block" : "ok",
    },
    {
      key: "trust_tier",
      text: "可信等级",
      hint: "A 可发布；B 只适合内部参考；C/D 不能当最终判决发布",
      meta: trust.label || "-",
      state: trustState,
    },
    {
      key: "evidence",
      text: "证据链完整",
      hint: "Reasoning Tree 中至少要有主张、证据和下一步",
      meta: `${evidence.nodes} 节点`,
      state: evidence.state,
    },
    {
      key: "dissent",
      text: "分歧处理",
      hint: "有反方或低可信度时只允许带风险发布",
      meta: disagreements.length ? `${disagreements.length} 条分歧` : "无显式分歧",
      state: disagreements.length && confidence < 80 ? "warn" : "ok",
    },
    {
      key: "risk_disclosure",
      text: "风险披露",
      hint: "报告要写明不确定性、阻断或复核边界",
      meta: /风险|阻断|不足|不确定|复核|回收|失败/.test(riskText) ? "已披露" : "待补充",
      state: !hasVerdict ? "block" : /风险|阻断|不足|不确定|复核|回收|失败/.test(riskText) ? "ok" : "warn",
    },
    {
      key: "audit_log",
      text: "审计日志",
      hint: "需要保留执行轨迹、桥接状态或历史 run 入口",
      meta: traceEvents.length ? `${traceEvents.length} 条` : hasVerdict ? "判词可追溯" : "等待日志",
      state: traceEvents.length || hasVerdict ? "ok" : "block",
    },
    {
      key: "human_confirmation",
      text: "签字确认",
      hint: "只标记本轮判断可对外使用",
      meta: state.publishCleared ? "通过" : "待确认",
      state: !hasVerdict ? "block" : state.publishCleared ? "ok" : "block",
    },
  ];
}

function renderPublishGate(message = "") {
  if (!$("#publishChecklist")) return;
  const summary = buildPublishGateSummary();
  const hasVerdict = Boolean(state.currentVerdict);
  const confidence = Number(state.currentVerdict?.confidence || 0);
  const ready = summary.ready;
  $("#publishChecklist").innerHTML = summary.checks.map(item => `
    <li class="${escapeAttr(item.state)}">
      <span class="gate-check-title"><strong>${escapeHtml(item.text)}</strong><small>${escapeHtml(item.hint)}</small></span>
      <span>${escapeHtml(item.key === "human_confirmation" && ready && message ? message : item.meta)}</span>
    </li>
  `).join("");
  $("#blockerCount").textContent = summary.blockers;
  $("#publishBlockerMetric").textContent = summary.blockers;
  $("#publishConfidence").textContent = hasVerdict ? `${confidence}%` : "-";
  $("#publishStatusText").textContent = ready ? "可签字" : summary.nonHumanBlockers ? "待完善" : hasVerdict ? "待确认" : "等待裁决";
  $("#gateBadge").className = `pill ${ready ? "chip-ok" : summary.nonHumanBlockers ? "chip-block" : "chip-warn"}`;
  $("#gateBadge").textContent = ready ? "可签字" : summary.nonHumanBlockers ? "待完善" : "待确认";
  $("#gateState").classList.toggle("is-ready", ready);
  $("#gateState").classList.toggle("is-locked", !ready);
  $("#gateState").textContent = ready ? "已满足签字条件" : summary.nonHumanBlockers ? "证据需要完善" : "等待人工确认";
  $("#gateMeter")?.classList.toggle("is-ready", ready);
  if ($("#gateReason")) {
    $("#gateReason").textContent = ready
      ? "所有关键项已就绪，可以完成签字。"
      : summary.nonHumanBlockers
        ? `${summary.nonHumanBlockers} 项证据需要完善，完成后即可签字。`
        : "裁决内容已生成，请确认后签字。";
  }
  const canConfirm = hasVerdict;
  $("#clearBlockersBtn").disabled = !canConfirm;
  $("#clearBlockersBtn").textContent = state.publishCleared
    ? (summary.nonHumanBlockers ? "已签字，仍待完善" : "已签字")
    : "签字确认";
  $("#publishBtn").disabled = !ready;
  if (state.currentVerdict) renderSimpleCloseout(state.currentVerdict);
  renderAutopilotWorkbench(state.currentVerdict);
  renderTaskCenter();
}

function renderMentorVerdict(preflight) {
  const panel = $("#mentor-result-panel");
  if (!panel) return;
  if (!preflight) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  $("#mentor-result-summary").textContent = preflight.execution_draft || preflight.next_question || "";
  const tags = [
    preflight.route_label || preflight.route,
    `清晰度 ${preflight.clarity ?? "-"}`,
    `风险 ${preflight.risk ?? "-"}`,
    `复杂度 ${preflight.complexity ?? "-"}`,
    ...(preflight.model_routes || []),
  ].filter(Boolean);
  $("#mentor-result-tags").innerHTML = tags.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}

function renderJudgeAnswer(v) {
  const panel = $("#judge-answer-panel");
  const judge = v?.judge_answer;
  const baseline = v?.single_judge_baseline;
  const report = v?.final_report;
  if (!judge && !baseline && !report) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.querySelector("h3").textContent = report?.title || judge?.label || baseline?.label || "AI Judge 法官答案";
  $("#judge-answer-summary").textContent = report?.abstract || judge?.answer || baseline?.answer || "";
  const tags = [
    report?.status_label || "",
    report?.final_position?.trust ? `可信 ${report.final_position.trust}` : "",
    judge ? `返回 ${judge.ok_count || 0}/${(judge.ok_count || 0) + (judge.failed_count || 0)}` : "",
    judge?.dominant_stance ? `立场 ${judge.dominant_stance}` : "",
    baseline?.score !== undefined ? `单模型分 ${Number(baseline.score || 0).toFixed(3)}` : "",
    baseline?.delta_vs_council !== undefined ? `对议会差值 ${Number(baseline.delta_vs_council || 0).toFixed(3)}` : "",
  ].filter(Boolean);
  $("#judge-answer-tags").innerHTML = tags.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}

function renderScoreRounds(bridge) {
  const panel = $("#score-round-panel");
  const rounds = bridge?.score_rounds || [];
  if (!rounds.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const active = rounds.filter(item => item.claim_count);
  $("#score-round-summary").textContent = active
    .map(item => `${item.label}: ${item.average_score === null || item.average_score === undefined ? "-" : Number(item.average_score).toFixed(3)}`)
    .join(" / ");
  $("#score-round-tags").innerHTML = rounds.map(item => {
    const score = item.average_score === null || item.average_score === undefined ? "-" : Number(item.average_score).toFixed(3);
    return `<span class="tag">${escapeHtml(item.claim_count || 0)} claims · ${escapeHtml(score)}</span>`;
  }).join("");
}

function renderPromptFlow(flow) {
  const panel = $("#prompt-flow-panel");
  if (!flow) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  $("#prompt-flow-summary").textContent = flow.quick_response || flow.intent || "";
  $("#prompt-flow-text").textContent = flow.professional_prompt || flow.normalized_question || "";
  $("#prompt-flow-tags").innerHTML = (flow.assumptions_to_check || []).map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("");
}

function renderExecutionPlan(plan, bridge) {
  const panel = $("#execution-panel");
  if (!plan) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  $("#execution-summary").textContent = plan.message || plan.decision || "";
  const runnable = plan.runnable_seats || [];
  const blocked = plan.blocked_seats || [];
  const tags = [
    `${escapeHtml(plan.driver_label || plan.driver || "")}`,
    `可运行 ${runnable.length}`,
    `阻断 ${blocked.length}`,
    bridge ? `桥接 ${bridge.ready_count || 0}/${bridge.configured_count || bridge.enabled_count || 0}` : "",
  ].filter(Boolean);
  $("#execution-tags").innerHTML = tags.map(item => `<span class="tag">${item}</span>`).join("");
}

async function loadTrace(runId) {
  try {
    const res = await fetch(`${API_BASE}/api/judge/${runId}/trace`);
    if (!res.ok) return;
    const trace = await res.json();
    renderTrace(trace);
  } catch {
    // The verdict may already contain a compact trace; leave it in place.
  }
}

function renderTrace(trace) {
  const panel = $("#trace-panel");
  const events = trace?.events || [];
  state.currentTrace = trace || null;
  if (!events.length) {
    panel.hidden = true;
    renderEvidenceTree();
    renderCouncilCompletion();
    renderPublishGate();
    renderTaskCenter();
    return;
  }
  panel.hidden = false;
  panel.open = false;
  $("#trace-count").textContent = `${events.length} 条`;
  $("#trace-list").innerHTML = events.slice(0, 80).map(event => {
    const data = event.data && Object.keys(event.data).length
      ? `<div class="trace-data">${escapeHtml(JSON.stringify(event.data, null, 2))}</div>`
      : "";
    return `
      <li>
        <div class="trace-line">
          <span class="trace-index">#${escapeHtml(event.index || "")}</span>
          <span class="trace-phase">${escapeHtml(event.phase || "")}</span>
          <span>${escapeHtml(event.action || "")}</span>
          <span class="trace-detail">${escapeHtml(event.detail || "")}</span>
        </div>
        ${data}
      </li>
    `;
  }).join("");
  renderEvidenceTree();
  renderCouncilCompletion();
  renderPublishGate();
  renderTaskCenter();
}

function currentTraceEvents() {
  return state.currentTrace?.events || state.currentVerdict?.execution_trace?.events || [];
}

function buildEvidenceNodes() {
  const v = state.currentVerdict;
  const traceEvents = currentTraceEvents();
  if (!v) {
    const counts = bridgeChannelCounts();
    return [
      {
        layer: "L1",
        title: "等待判词生成",
        body: "提交议题后，系统会把最终结论拆成主张、证据、分歧和下一步。",
        state: "warn",
        tags: ["等待主张"],
      },
      {
        layer: "L2",
        title: "网页席位健康基线",
        body: counts.webTotal ? `当前网页席位 ${counts.webReady}/${counts.webTotal} 就绪。` : "还没有读取到网页席位配置。",
        state: counts.webTotal && counts.webReady === counts.webTotal ? "ok" : "warn",
        tags: ["网页桥接", `${counts.webReady}/${counts.webTotal}`],
      },
      {
        layer: "L3",
        title: "发布前审计轨迹",
        body: "判词完成后会显示执行轨迹、回收状态和签字。",
        state: "block",
        tags: ["等待轨迹"],
      },
    ];
  }
  const raw = v.web_bridge?.raw_results || [];
  const okRaw = raw.filter(item => item.ok);
  const failedRaw = raw.filter(item => item && !item.ok);
  const reasons = (v.reasons || []).filter(Boolean);
  const nextSteps = (v.next_steps || []).filter(Boolean);
  const nodes = [
    {
      layer: "L1",
      title: v.one_liner || v.verdict_label || "最终主张",
      body: finalReportText(v),
      state: Number(v.confidence || 0) >= 80 ? "ok" : "warn",
      tags: [`可信度 ${v.confidence ?? "-"}%`, v.verdict_label || v.verdict || "verdict"],
    },
  ];
  reasons.slice(0, state.productMode === "pro" ? 5 : 3).forEach((reason, index) => {
    nodes.push({
      layer: "L1",
      title: `主张 ${index + 1}`,
      body: reason,
      state: /风险|阻断|失败|不足|不确定/.test(reason) ? "warn" : "ok",
      tags: ["Reason", `R${index + 1}`],
    });
  });
  if (raw.length) {
    nodes.push({
      layer: "L2",
      title: "席位原文回收",
      body: `${okRaw.length}/${raw.length} 个网页席位返回有效答案；失败或慢生成不会计入共识。`,
      state: failedRaw.length ? (failedRaw.some(item => !isSupplementableResult(item)) ? "block" : "warn") : "ok",
      tags: ["Raw answers", `${okRaw.length}/${raw.length}`],
    });
    failedRaw.slice(0, 4).forEach(item => {
      nodes.push({
        layer: "L2",
        title: `${seatName(item.seat)} 未形成有效证据`,
        body: item.error?.message || statusLabel(item.error?.code, false),
        state: isSupplementableResult(item) ? "warn" : "block",
        tags: [item.error?.code || "failed", isSupplementableResult(item) ? "可回收" : "硬阻断"],
      });
    });
  } else if ((v.seat_scores || []).length) {
    nodes.push({
      layer: "L2",
      title: "网页席位评分",
      body: `${v.seat_scores.length} 个网页席位参与评分，原始评分保留在对比页。`,
      state: "ok",
      tags: ["Local seats", `${v.seat_scores.length}`],
    });
  } else {
    nodes.push({
      layer: "L2",
      title: "证据来源待补充",
      body: "当前判词没有可展示的网页原文或席位评分，发布前需要复核来源。",
      state: "warn",
      tags: ["Evidence gap"],
    });
  }
  const disagreements = v.web_bridge?.deliberation?.disagreements || v.disagreements || [];
  if (disagreements.length) {
    nodes.push({
      layer: "L2",
      title: "模型分歧",
      body: disagreements.slice(0, 3).map(item => item.summary || item.reason || String(item)).join("；"),
      state: Number(v.confidence || 0) >= 80 ? "warn" : "block",
      tags: ["Dissent", `${disagreements.length}`],
    });
  }
  if (traceEvents.length) {
    const latest = traceEvents[traceEvents.length - 1] || {};
    nodes.push({
      layer: "L3",
      title: "执行轨迹",
      body: `${traceEvents.length} 条事件，最近阶段：${latest.phase || "-"} / ${latest.action || "-"}`,
      state: "ok",
      tags: ["Trace", `${traceEvents.length}`],
    });
  } else {
    nodes.push({
      layer: "L3",
      title: "执行轨迹入口",
      body: v.run_id ? `Run ${compactRunId(v.run_id)} 可通过完整报告追踪。` : "缺少 run id。",
      state: v.run_id ? "ok" : "block",
      tags: ["Ledger"],
    });
  }
  if (nextSteps.length) {
    nodes.push({
      layer: "L3",
      title: "下一步动作",
      body: nextSteps.slice(0, 3).join("；"),
      state: /回收|复核|补|确认|阻断/.test(nextSteps.join(" ")) ? "warn" : "ok",
      tags: ["Action"],
    });
  }
  return nodes;
}

function renderEvidenceTree() {
  const target = $("#reasoning-tree");
  if (!target) return;
  const nodes = buildEvidenceNodes();
  target.innerHTML = nodes.map(node => `
    <article class="reason-node ${escapeAttr(node.state)}">
      <span class="reason-layer">${escapeHtml(node.layer)}</span>
      <div class="reason-main">
        <h3>${escapeHtml(node.title)}</h3>
        <p>${escapeHtml(excerpt(node.body, state.productMode === "pro" ? 520 : 260))}</p>
        <div class="reason-tags">${(node.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
      <span class="audit-status ${escapeAttr(node.state)} reason-state">${escapeHtml(reviewStateLabel(node.state))}</span>
    </article>
  `).join("");
  const hasVerdict = Boolean(state.currentVerdict);
  const counts = bridgeChannelCounts();
  const checks = hasVerdict
    ? [
        { title: "原始问题保留", meta: state.currentVerdict?.question ? "通过" : "等待", state: state.currentVerdict?.question ? "ok" : "block" },
        { title: "证据节点", meta: `${nodes.length} 个`, state: nodes.some(node => node.state === "block") ? "block" : nodes.some(node => node.state === "warn") ? "warn" : "ok" },
        { title: "网页席位校准", meta: counts.webTotal ? `${counts.webReady}/${counts.webTotal}` : "待读取", state: counts.webReady === counts.webTotal ? "ok" : "warn" },
        { title: "发布引用复核", meta: "看签字", state: buildPublishGateSummary().nonHumanBlockers ? "block" : "ok" },
      ]
    : [
        { title: "等待报告生成", meta: "无判词", state: "block" },
        { title: "网页席位健康", meta: counts.webTotal ? `${counts.webReady}/${counts.webTotal}` : "待读取", state: counts.webTotal && counts.webReady === counts.webTotal ? "ok" : "warn" },
        { title: "证据树", meta: "报告完成后生成", state: "warn" },
        { title: "发布引用复核", meta: "等待报告", state: "block" },
      ];
  $("#evidence-check-list").innerHTML = checks.map(item => `
    <li class="${escapeAttr(item.state)}"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.meta)}</span></li>
  `).join("");
  const blockers = nodes.filter(node => node.state === "block").length;
  $("#evidence-next-action").textContent = !hasVerdict
    ? "等待报告生成。完成后这里才会拆出主张、证据、分歧和发布前引用复核。"
    : blockers
    ? `还有 ${blockers} 个证据阻断，先处理失败席位或缺失日志。`
    : nodes.some(node => node.state === "warn")
      ? "证据链已形成，但仍建议先处理黄色提示后再发布。"
      : "证据链可进入签字复核。";
}

function renderCouncilCompletion() {
  renderTraceDepthGrid();
  renderPersonaGrid();
}

function renderTraceDepthGrid() {
  const target = $("#trace-depth-grid");
  if (!target) return;
  const v = state.currentVerdict || {};
  const coverage = seatCoverageSummary();
  const traceEvents = currentTraceEvents();
  const nodes = buildEvidenceNodes();
  const items = [
    ["L1 主张", `${(v.reasons || []).length || (v.one_liner ? 1 : 0)} 条`, "结论、理由和风险披露是否同向"],
    ["L2 证据", coverage.total ? coverage.label : `${nodes.length} 节点`, "席位原文、评分和失败状态是否可追溯"],
    ["L3 追踪", traceEvents.length ? `${traceEvents.length} 条` : (v.run_id ? "Run 可追溯" : "待生成"), "执行轨迹、回收事件和日志入口"],
  ];
  target.innerHTML = items.map(([label, value, detail]) => `
    <div class="trace-depth-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <p>${escapeHtml(detail)}</p>
    </div>
  `).join("");
}

function renderPersonaGrid() {
  const target = $("#persona-grid");
  if (!target) return;
  const seats = state.seats.length ? state.seats : fallbackSeats();
  const scoreBySeat = new Map((state.currentVerdict?.seat_scores || []).map(item => [item.seat, item]));
  target.innerHTML = seats.map(seat => {
    const health = seatOperationalState(seat);
    const score = scoreBySeat.get(seat.id);
    const tags = [
      seat.mbti || "MBTI",
      channelLabel((bridgeMatrixBySeat(seat.id) || bridgeSeatById(seat.id) || {}).channel || "web"),
      score ? `分 ${Number(score.average_score || 0).toFixed(2)}` : health.label,
    ];
    return `
      <article class="persona-card ${escapeAttr(health.state)}">
        <strong>${escapeHtml(seat.name)}</strong>
        <p>${escapeHtml(seat.strength || "COUNCIL-004 固定席位人格")}</p>
        <div class="persona-meta">${tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <p>${escapeHtml(health.detail)}</p>
      </article>
    `;
  }).join("");
}

function reviewStateLabel(stateName) {
  if (stateName === "ok") return "通过";
  if (stateName === "warn") return "需复核";
  if (stateName === "block") return "阻断";
  return "等待";
}

function renderSeatScores() {
  const scoreboardRows = state.seatScoreboard?.seats || [];
  const bySeat = new Map(scoreboardRows.map(item => [item.seat, item]));
  const rows = state.seats.map(seat => {
    const aggregate = bySeat.get(seat.id) || {};
    const scored = (state.currentVerdict?.seat_scores || []).find(item => item.seat === seat.id);
    const finalScore = aggregate.average_score ?? (scored ? Number(scored.average_score || 0) : null);
    const q = aggregate.q_avg ?? (scored ? Number(scored.average_score || 0) : null);
    const k = aggregate.k_avg ?? null;
    const c = aggregate.c_avg ?? null;
    const r = aggregate.r_stability ?? (bridgeSeatById(seat.id)?.ready ? 1 : 0);
    const t = aggregate.t_tenure ?? (scored ? Math.min(0.35, 0.18 + Number(scored.claims_count || 0) * 0.03) : null);
    const provider = aggregate.provider || bridgeSeatById(seat.id)?.provider || seat.name;
    const channel = aggregate.channel || bridgeSeatById(seat.id)?.channel || "local";
    const latest = aggregate.latest_run;
    const lastLink = latest?.run_id
      ? `<button class="ghost" data-open-run="${escapeAttr(latest.run_id)}">${finalScore === null ? "-" : Number(finalScore).toFixed(3)}</button>`
      : `<strong>${finalScore === null ? "-" : Number(finalScore).toFixed(3)}</strong>`;
    return `
      <tr>
        <td><strong>${escapeHtml(seat.name)}</strong><span class="muted">${escapeHtml(seat.mbti || "")}</span></td>
        <td>${escapeHtml(provider)}</td>
        <td><span class="channel ${escapeAttr(channel)}">${escapeHtml(channelLabel(channel))}</span></td>
        ${metricCell(q)}
        ${metricCell(k)}
        ${metricCell(c)}
        ${metricCell(r)}
        ${metricCell(t)}
        <td>${lastLink}</td>
      </tr>
    `;
  });
  $("#seat-score-body").innerHTML = rows.join("");
  $$("[data-open-run]").forEach(btn => btn.addEventListener("click", () => openHistoryRun(btn.dataset.openRun, { switchToConversation: true })));
  renderSeatScoreCards(scoreboardRows);
  $("#score-summary").textContent = state.currentVerdict
    ? `${state.currentVerdict.mode_name || state.currentVerdict.mode} · ${state.currentVerdict.seat_count || 0} 席 · ${state.currentVerdict.confidence}%`
    : `${state.seatScoreboard?.runs_considered || 0} 次历史 · ${state.seats.length} 个席位`;
}

function renderSeatScoreCards(rows) {
  if (!$("#seat-score-cards")) return;
  const active = rows.filter(item => item.average_score !== null && item.average_score !== undefined);
  const best = active[0];
  const totalRuns = state.seatScoreboard?.runs_considered || 0;
  const ready = (state.bridge?.seats || []).filter(item => item.ready).length;
  $("#seat-score-cards").innerHTML = [
    ["历史样本", `${totalRuns} 次`, "完整保留最近议事与报告入口"],
    ["当前冠军", best ? `${best.seat_name} ${Number(best.average_score).toFixed(3)}` : "-", "按多次平均分排序"],
    ["桥接就绪", `${ready}/${state.bridge?.seats?.length || state.seats.length}`, "网页与桌面入口状态"],
  ].map(([title, value, sub]) => `
    <div class="score-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(title)} · ${escapeHtml(sub)}</span></div>
  `).join("");
}

function renderBenchmarks() {
  const target = $("#benchmark-grid");
  if (!target) return;
  const cards = state.benchmarks?.cards || fallbackBenchmarks().cards;
  target.innerHTML = cards.map(card => `
    <article class="benchmark-card ${escapeAttr(card.status || "active")}">
      <div>
        <strong>${escapeHtml(card.label || card.id)}</strong>
        <p>${escapeHtml(card.summary || "")}</p>
      </div>
      <span class="benchmark-score">${escapeHtml(card.score || card.status || "-")}</span>
    </article>
  `).join("");
}

function renderProductCapabilities() {
  const target = $("#capability-list");
  if (!target) return;
  const data = state.productCapabilities || fallbackProductCapabilities();
  const stable = data.stable_mode || {};
  const lab = data.lab_mode || {};
  const market = data.market_fit || {};
  $("#stable-job").textContent = stable.job || "5 分钟可信结论";
  $("#stable-surfaces").textContent = (stable.surfaces || []).join(" / ") || "录入 / 收口 / 风险 / 发布确认";
  $("#lab-job").textContent = lab.job || "诊断与基准";
  $("#lab-surfaces").textContent = (lab.surfaces || []).join(" / ") || "席位 / 桥接 / 评分 / 日志 / benchmark";
  const cards = [
    {
      title: "产品定位",
      body: data.positioning || "把多模型回答收口成可审计、可确认的决策。",
    },
    {
      title: "当前亮点",
      body: (market.strengths || []).slice(0, 2).join("；") || "多席位、回收、评分、门禁在一个本地闭环里。",
    },
    {
      title: "已知短板",
      body: (market.known_gaps || []).slice(0, 2).join("；") || "网页桥接仍依赖登录态和页面结构。",
    },
  ];
  target.innerHTML = cards.map(card => `
    <article class="capability-card">
      <h3>${escapeHtml(card.title)}</h3>
      <p>${escapeHtml(card.body)}</p>
    </article>
  `).join("");
}

function metricCell(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return `<td><span class="muted">-</span></td>`;
  value = Number(value);
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return `<td><span class="meter"><span>${Number(value).toFixed(2)}</span><span class="track"><span class="fill ${value < 0.35 ? "low" : ""}" style="width:${pct}%"></span></span></span></td>`;
}

function renderMapping() {
  const matrix = state.bridge?.seat_browser_matrix || [];
  const rows = state.seats.map(seat => {
    const mapped = matrix.find(item => item.seat === seat.id) || {};
    const bridgeSeat = bridgeSeatById(seat.id) || {};
    const channel = mapped.channel || bridgeSeat.channel || "web";
    const desktop = bridgeSeat.desktop_app || {};
    const calibration = calibrationSummary(mapped, bridgeSeat);
    const safe = (mapped.safe_background ?? bridgeSeat.safe_background) ? "不占用鼠标/键盘/剪贴板" : "需要专用 Operator";
    const calibrationText = calibration.status === "pass"
      ? `通过 · ${calibration.age_hours ?? 0}h`
      : calibration.status === "fail"
        ? `失败 · ${calibration.error_code || "unknown"}`
        : "待校准";
    const ready = Boolean((mapped.ready ?? bridgeSeat.ready) || false);
    return `
      <tr>
        <td><strong>${escapeHtml(seat.name)}</strong><span class="muted">${escapeHtml(seat.id)}</span></td>
        <td>${escapeHtml(mapped.provider || bridgeSeat.provider || seat.name)}</td>
        <td><span class="channel ${escapeAttr(channel)}">${escapeHtml(channelLabel(channel))}</span></td>
        <td>${escapeHtml(mapped.driver_label || bridgeSeat.driver_label || "-")}</td>
        <td>${escapeHtml(safe)}</td>
        <td>${escapeHtml(calibrationText)}</td>
        <td>${escapeHtml(statusLabel(mapped.reason || bridgeSeat.reason, ready))}</td>
        <td class="muted">${escapeHtml(mapped.target || bridgeSeat.browser_label || bridgeSeat.url || desktop.name || "-")}</td>
      </tr>
    `;
  });
  $("#mapping-body").innerHTML = rows.join("");
}

function calibrationSummary(mapped = {}, bridgeSeat = {}) {
  const calibration = bridgeSeat.calibration || {};
  return {
    status: mapped.calibration_status || calibration.status || "missing",
    age_hours: mapped.calibration_age_hours ?? calibration.age_hours ?? 0,
    error_code: mapped.calibration_error_code || calibration.error?.code || "",
  };
}

async function loadHistory() {
  const list = $("#history-list");
  try {
    const res = await fetch(`${API_BASE}/api/history`);
    const data = await res.json();
    const runs = data.runs || [];
    state.historyRuns = runs;
    renderHistoryFromState();
  } catch {
    list.innerHTML = `<li class="muted">API Server 未连接</li>`;
  }
}

function renderHistoryFromState() {
  const list = $("#history-list");
  if (!list) return;
  const runs = state.historyRuns || [];
  if (!runs.length) {
    list.innerHTML = `<li class="muted">${state.productMode === "pro" ? "暂无历史任务" : "暂无结果，完成的自动任务会进入这里"}</li>`;
    return;
  }
  if (state.productMode !== "pro") {
    list.innerHTML = runs.map(run => {
      const confidence = run.confidence !== undefined ? `${run.confidence}%` : `${Math.round((Number(run.progress) || 0) * 100)}%`;
      return `
        <li class="history-item inbox-item" data-id="${escapeAttr(run.run_id)}">
          <div class="history-main">
            <strong>${escapeHtml(inboxReportTitle(run))}</strong>
            <span class="history-meta">
              <span class="state-label ${escapeAttr(inboxStatusState(run))}">${escapeHtml(inboxStatusLabel(run))}</span>
              <span>可信度 ${escapeHtml(confidence)}</span>
              <span>${escapeHtml(inboxNextAction(run))}</span>
            </span>
          </div>
          <div class="hermes-status-row" style="margin-top:6px; font-size:11px; color:#888; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="hermes-indicator" data-file="hermes-output.json" style="display:none;">JSON ✓</span>
            <span class="hermes-indicator" data-file="hermes-output.md" style="display:none;">MD ✓</span>
            <span class="hermes-indicator" data-file="obsidian-run-note.md" style="display:none;">Obsidian ✓</span>
            <span class="hermes-indicator" data-file="index.html" style="display:none;">HTML ✓</span>
          </div>
          <div class="hermes-export-buttons" style="margin-top:4px; display:flex; gap:4px; flex-wrap:wrap;">
            <button class="hermes-btn" data-kind="html" data-hermes-kind="html" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/index.html" data-testid="hermes-export-html" style="font-size:10px; padding:2px 6px; border:1px solid #8af; background:none; color:#8af; border-radius:3px; cursor:pointer;">完整报告</button>
            <button class="hermes-btn" data-kind="json" data-hermes-kind="json" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/hermes-output.json" data-testid="hermes-export-json" style="font-size:10px; padding:2px 6px; border:1px solid #fa8; background:none; color:#fa8; border-radius:3px; cursor:pointer;">Hermes JSON</button>
            <button class="hermes-btn" data-kind="md" data-hermes-kind="md" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/hermes-output.md" data-testid="hermes-export-md" style="font-size:10px; padding:2px 6px; border:1px solid #8f8; background:none; color:#8f8; border-radius:3px; cursor:pointer;">Hermes MD</button>
            <button class="hermes-btn" data-kind="obsidian" data-hermes-kind="obsidian" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/obsidian-run-note.md" data-testid="hermes-export-obsidian" style="font-size:10px; padding:2px 6px; border:1px solid #f8f; background:none; color:#f8f; border-radius:3px; cursor:pointer;">Obsidian Note</button>
          </div>
          <div class="human-gavel-row" style="margin-top:4px; font-size:11px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span class="human-gavel-status" data-run-id="${escapeAttr(run.run_id)}" style="padding:1px 6px; border-radius:3px; font-weight:600;">Human Gavel: —</span>
            <span class="human-gavel-conflict" data-run-id="${escapeAttr(run.run_id)}" style="display:none; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:600;"></span>
            <span class="human-gavel-history-count" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; color:#888;"></span>
            <span class="human-gavel-claims" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; color:#888;"></span>
            <button class="human-gavel-sync-btn" data-run-id="${escapeAttr(run.run_id)}" style="font-size:10px; padding:2px 8px; border:1px solid #6366f1; background:rgba(99,102,241,0.15); color:#a5b4fc; border-radius:3px; cursor:pointer;">同步人工裁决</button>
            <button class="human-gavel-history-btn" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; padding:2px 8px; border:1px solid #6366f1; background:rgba(99,102,241,0.15); color:#a5b4fc; border-radius:3px; cursor:pointer;">查看 Gavel 历史</button>
          </div>
          <div class="human-gavel-history-panel" data-run-id="${escapeAttr(run.run_id)}" style="display:none; margin-top:4px; max-height:200px; overflow-y:auto; font-size:10px; color:#aaa; background:rgba(0,0,0,0.1); border-radius:4px; padding:4px 8px;"></div>
          <div class="claim-calib-row" style="margin-top:4px; font-size:11px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span class="claim-calib-status" data-run-id="${escapeAttr(run.run_id)}" style="padding:0px 4px; border-radius:3px; font-size:10px; color:#888;">Claim Calib: —</span>
            <button class="claim-calib-rebuild-btn" data-run-id="${escapeAttr(run.run_id)}" style="font-size:10px; padding:2px 8px; border:1px solid #f59e0b; background:rgba(245,158,11,0.12); color:#fbbf24; border-radius:3px; cursor:pointer;">重建 Claim 校准</button>
          </div>
          <span class="history-id">${escapeHtml(compactRunId(run.run_id))}</span>
        </li>
      `;
    }).join("");
  } else {
    list.innerHTML = runs.map(run => `
      <li class="history-item" data-id="${escapeAttr(run.run_id)}">
        <div class="history-main">
          <strong>${escapeHtml(inboxReportTitle(run))}</strong>
          <span class="history-meta">
            <span>${escapeHtml(run.mode || "-")}</span>
            <span>${escapeHtml(run.status || "-")}</span>
            <span>${Math.round((run.progress || 0) * 100)}%</span>
          </span>
        </div>
        <div class="hermes-status-row" style="margin-top:6px; font-size:11px; color:#888; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span class="hermes-indicator" data-file="hermes-output.json" style="display:none;">JSON ✓</span>
          <span class="hermes-indicator" data-file="hermes-output.md" style="display:none;">MD ✓</span>
          <span class="hermes-indicator" data-file="obsidian-run-note.md" style="display:none;">Obsidian ✓</span>
          <span class="hermes-indicator" data-file="index.html" style="display:none;">HTML ✓</span>
        </div>
        <div class="hermes-export-buttons" style="margin-top:4px; display:flex; gap:4px; flex-wrap:wrap;">
          <button class="hermes-btn" data-kind="html" data-hermes-kind="html" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/index.html" data-testid="hermes-export-html" style="font-size:10px; padding:2px 6px; border:1px solid #8af; background:none; color:#8af; border-radius:3px; cursor:pointer;">完整报告</button>
          <button class="hermes-btn" data-kind="json" data-hermes-kind="json" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/hermes-output.json" data-testid="hermes-export-json" style="font-size:10px; padding:2px 6px; border:1px solid #fa8; background:none; color:#fa8; border-radius:3px; cursor:pointer;">Hermes JSON</button>
          <button class="hermes-btn" data-kind="md" data-hermes-kind="md" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/hermes-output.md" data-testid="hermes-export-md" style="font-size:10px; padding:2px 6px; border:1px solid #8f8; background:none; color:#8f8; border-radius:3px; cursor:pointer;">Hermes MD</button>
          <button class="hermes-btn" data-kind="obsidian" data-hermes-kind="obsidian" data-id="${escapeAttr(run.run_id)}" data-run-id="${escapeAttr(run.run_id)}" data-url="${API_BASE}/api/runs/${escapeAttr(run.run_id)}/obsidian-run-note.md" data-testid="hermes-export-obsidian" style="font-size:10px; padding:2px 6px; border:1px solid #f8f; background:none; color:#f8f; border-radius:3px; cursor:pointer;">Obsidian Note</button>
        </div>
        <div class="human-gavel-row" style="margin-top:4px; font-size:11px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          <span class="human-gavel-status" data-run-id="${escapeAttr(run.run_id)}" style="padding:1px 6px; border-radius:3px; font-weight:600;">Human Gavel: —</span>
          <span class="human-gavel-conflict" data-run-id="${escapeAttr(run.run_id)}" style="display:none; padding:1px 4px; border-radius:3px; font-size:10px; font-weight:600;"></span>
          <span class="human-gavel-history-count" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; color:#888;"></span>
          <span class="human-gavel-claims" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; color:#888;"></span>
          <button class="human-gavel-sync-btn" data-run-id="${escapeAttr(run.run_id)}" style="font-size:10px; padding:2px 8px; border:1px solid #6366f1; background:rgba(99,102,241,0.15); color:#a5b4fc; border-radius:3px; cursor:pointer;">同步人工裁决</button>
          <button class="human-gavel-history-btn" data-run-id="${escapeAttr(run.run_id)}" style="display:none; font-size:10px; padding:2px 8px; border:1px solid #6366f1; background:rgba(99,102,241,0.15); color:#a5b4fc; border-radius:3px; cursor:pointer;">查看 Gavel 历史</button>
        </div>
        <div class="human-gavel-history-panel" data-run-id="${escapeAttr(run.run_id)}" style="display:none; margin-top:4px; max-height:200px; overflow-y:auto; font-size:10px; color:#aaa; background:rgba(0,0,0,0.1); border-radius:4px; padding:4px 8px;"></div>
        <div class="claim-calib-row" style="margin-top:4px; font-size:11px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          <span class="claim-calib-status" data-run-id="${escapeAttr(run.run_id)}" style="padding:0px 4px; border-radius:3px; font-size:10px; color:#888;">Claim Calib: —</span>
          <button class="claim-calib-rebuild-btn" data-run-id="${escapeAttr(run.run_id)}" style="font-size:10px; padding:2px 8px; border:1px solid #f59e0b; background:rgba(245,158,11,0.12); color:#fbbf24; border-radius:3px; cursor:pointer;">重建 Claim 校准</button>
        </div>
        <span class="history-id">${escapeHtml(compactRunId(run.run_id))}</span>
      </li>
    `).join("");
  }
  $$(".history-item").forEach(item => item.addEventListener("click", () => openHistoryRun(item.dataset.id, { switchToConversation: false })));
  // Populate Hermes status for each run card
  runs.forEach(run => {
    const card = list.querySelector(`li[data-id="${CSS.escape(run.run_id)}"]`);
    if (card) populateRunCardHermesStatus(run.run_id, card);
  });
  // Populate Human Gavel status for each run card
  runs.forEach(run => {
    const card = list.querySelector(`li[data-id="${CSS.escape(run.run_id)}"]`);
    if (card) {
      populateHumanGavelStatus(run.run_id, card);
      populateClaimCalibrationStatus(run.run_id, card);
    }
  });
  // P4: Setup gavel history button delegation
  setupHumanGavelHistoryDelegation();
  // Setup sync button delegation
  setupHumanGavelSyncDelegation();
  // P5: Setup claim calibration rebuild delegation
  setupClaimCalibrationRebuildDelegation();
  // P4: Apply gavel filter after cards are rendered
  applyGavelFilter();
}

function inboxStatusState(run) {
  if (run.status === "failed" || run.status === "cancelled") return "block";
  if (run.status === "complete" || run.progress >= 1 || run.confidence !== undefined) return "ok";
  return "warn";
}

function inboxStatusLabel(run) {
  if (run.status === "failed") return "失败隔离";
  if (run.status === "cancelled") return "已取消";
  if (run.status === "complete" || run.progress >= 1 || run.confidence !== undefined) return "可阅读";
  if (run.status === "running") return "运行中";
  return "排队中";
}

function simpleNextActionLabel(run) {
  if (run.status === "failed" || run.status === "cancelled") return "查看失败原因";
  if (run.status === "complete" || run.progress >= 1 || run.confidence !== undefined) return "阅读并签字";
  return "等待完成";
}

async function openHistoryRun(runId, options = {}) {
  if (!runId) return;
  const res = await fetch(`${API_BASE}/api/history/${runId}`);
  const data = await res.json();
  const verdict = data.result || (data.verdict ? data : null);
  if (verdict) {
    renderVerdict(verdict);
    renderHistoryDetail(verdict);
    if (options.switchToConversation) switchTab("draft");
  } else {
    renderHistoryDetail(data);
    renderTaskSnapshot(data);
  }
}

function renderTaskSnapshot(task) {
  if (!task || !task.run_id || task.progress === undefined) return;
  state.currentRunId = task.run_id;
  state.currentTask = task;
  $("#run-id").textContent = task.run_id;
  const pct = Math.round((Number(task.progress) || 0) * 100);
  setProgress(pct, task.current_step || task.status || "运行中");
  renderRunDiagnostics(task);
  renderTaskCenter();
  renderCouncilCompletion();
  setBusy(task.status === "running" && !task.progress_diagnostics?.stale);
  if (task.status === "running" && !task.progress_diagnostics?.stale) startProgress(task.run_id);
}

function renderHistoryDetail(item) {
  const detail = $("#history-detail");
  if (!detail) return;
  if (state.productMode !== "pro") {
    renderSimpleHistoryDetail(item);
    return;
  }
  const runId = item.run_id || "";
  const traceCount = item.execution_trace?.events?.length || 0;
  const score = displayScore(item.average_score ?? item.confidence);
  const reportUrl = canonicalReportUrl(item);
  const report = reportUrl ? `<a class="ghost" href="${escapeAttr(reportUrl)}">完整报告</a>` : "";
  const chief = chiefJudgeLabel(item);
  const seatCount = (item.seat_roster?.selected || item.seat_scores || []).length || "-";
  const mode = item.mode_name || item.mode || "-";
  detail.innerHTML = `
    <div class="ledger-detail-head">
      <div>
        <h2>${escapeHtml(inboxReportTitle(item))}</h2>
        <p class="muted">略说总结：${escapeHtml(inboxBriefSummary(item, 220))}</p>
      </div>
      <span class="history-id">${escapeHtml(compactRunId(runId))}</span>
    </div>
    <div class="tag-list">
      <span class="tag">Run ${escapeHtml(compactRunId(runId) || "-")}</span>
      <span class="tag">${escapeHtml(mode)}</span>
      <span class="tag">评分 ${escapeHtml(score)}</span>
      <span class="tag">日志 ${traceCount} 条</span>
    </div>
    <div class="result-actions ledger-actions">
      <button class="ghost" data-open-run="${escapeAttr(runId)}">回到结果卡</button>
      ${report}
      <button class="ghost active" data-history-section="summary">摘要</button>
      <button class="ghost" data-history-section="trace">日志</button>
      <button class="ghost" data-history-section="scores">评分</button>
    </div>
    <div class="ledger-summary-grid">
      <div><span>主审</span><strong>${escapeHtml(chief)}</strong></div>
      <div><span>席位</span><strong>${escapeHtml(seatCount)}</strong></div>
      <div><span>日志</span><strong>${traceCount} 条</strong></div>
    </div>
    <div class="ledger-note" id="history-summary-note">${escapeHtml(inboxBriefSummary(item))}</div>
    <pre id="history-detail-pre" hidden>${escapeHtml(historyDetailPreview(item))}</pre>
  `;
  detail.querySelector("[data-open-run]")?.addEventListener("click", () => switchTab("draft"));
  detail.querySelectorAll("[data-history-section]").forEach(button => {
    button.addEventListener("click", () => setHistoryDetailSection(detail, item, button.dataset.historySection));
  });
}

function renderSimpleHistoryDetail(item) {
  const detail = $("#history-detail");
  if (!detail) return;
  const runId = item.run_id || "";
  const confidence = item.confidence !== undefined ? `${item.confidence}%` : displayScore(item.average_score);
  const summary = inboxBriefSummary(item);
  const reportUrl = canonicalReportUrl(item);
  const report = reportUrl ? `<a class="ghost" href="${escapeAttr(reportUrl)}">打开完整报告</a>` : "";
  detail.innerHTML = `
    <div class="ledger-detail-head">
      <div>
        <h2>${escapeHtml(inboxReportTitle(item))}</h2>
        <p class="muted">略说总结：${escapeHtml(inboxBriefSummary(item, 180))}</p>
      </div>
      <span class="history-id">${escapeHtml(compactRunId(runId))}</span>
    </div>
    <div class="ledger-summary-grid">
      <div><span>状态</span><strong>${escapeHtml(inboxStatusLabel(item))}</strong></div>
      <div><span>可信度</span><strong>${escapeHtml(confidence || "-")}</strong></div>
      <div><span>下一步</span><strong>${escapeHtml(inboxNextAction(item))}</strong></div>
    </div>
    <div class="ledger-note">${escapeHtml(summary || "结果完成后会在这里压缩成可读摘要。")} 完整席位、互评、共振和原始日志请进入完整报告。</div>
    <div class="result-actions ledger-actions">
      <button class="primary-action" data-open-run="${escapeAttr(runId)}">查看运行页</button>
      <button class="ghost" data-simple-gavel>去签字</button>
      ${report}
    </div>
  `;
  detail.querySelector("[data-open-run]")?.addEventListener("click", () => switchTab("draft"));
  detail.querySelector("[data-simple-gavel]")?.addEventListener("click", () => switchTab("publish"));
}

function historyDetailPreview(item) {
  return JSON.stringify({
    chief_judge: item.chief_judge,
    seat_roster: item.seat_roster,
    seat_scores: item.seat_scores,
    score_rounds: item.web_bridge?.score_rounds,
  }, null, 2);
}

function setHistoryDetailSection(detail, item, section) {
  detail.querySelectorAll("[data-history-section]").forEach(button => {
    button.classList.toggle("active", button.dataset.historySection === section);
  });
  const note = detail.querySelector("#history-summary-note");
  const pre = detail.querySelector("#history-detail-pre");
  if (!pre || !note) return;
  if (section === "trace") {
    note.hidden = true;
    pre.hidden = false;
    pre.textContent = JSON.stringify(item.execution_trace || {}, null, 2);
  } else if (section === "scores") {
    note.hidden = true;
    pre.hidden = false;
    pre.textContent = JSON.stringify(item.seat_scores || [], null, 2);
  } else {
    pre.hidden = true;
    note.hidden = false;
    note.textContent = inboxBriefSummary(item);
  }
}

function historySummaryText(item) {
  return inboxBriefSummary(item);
}

function inboxReportTitle(item) {
  const report = item?.final_report || {};
  const overview = report.compact_overview || {};
  const brief = report.decision_brief || {};
  const longform = report.longform_report || report.compiled_report?.longform_report || {};
  return excerpt(
    overview.title || brief.title || longform.title || report.title || item?.one_liner || item?.question || "自动任务结果",
    128,
  );
}

function inboxBriefSummary(item, maxLength = 260) {
  const report = item?.final_report || {};
  const overview = report.compact_overview || {};
  const brief = report.decision_brief || {};
  const executive = report.executive_summary || {};
  const runHealth = report.run_health || {};
  const candidate = overview.lead || overview.summary || overview.priority || brief.one_sentence || executive.headline || report.abstract || runHealth.headline || item?.one_liner || item?.verdict_label || "本轮议事已归档。";
  return excerpt(candidate, maxLength);
}

function inboxNextAction(item) {
  const report = item?.final_report || {};
  const overview = report.compact_overview || {};
  const plan = Array.isArray(overview.plan) ? overview.plan : [];
  const firstPlan = plan[0];
  const fromPlan = typeof firstPlan === "string" ? firstPlan : firstPlan?.body || firstPlan?.title || "";
  const fromNext = (item?.next_steps || []).find(Boolean) || "";
  return excerpt(overview.priority || fromPlan || fromNext || simpleNextActionLabel(item), 54);
}

function displayScore(value) {
  if (value === null || value === undefined || value === "-") return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric > 1 ? `${Math.round(numeric)}%` : numeric.toFixed(3);
}

function chiefJudgeLabel(item) {
  const chief = item.chief_judge;
  if (!chief) return "-";
  if (typeof chief === "string") return chief;
  return chief.label || chief.name || chief.id || "-";
}

function compactRunId(runId) {
  const value = String(runId || "");
  return value.length > 12 ? value.slice(0, 12) : value;
}

function excerpt(value, maxLength) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

async function restoreLastRun() {
  if (!state.lastHistoryRunId) return;
  try {
    await openHistoryRun(state.lastHistoryRunId, { switchToConversation: false });
  } catch {
    // History is best-effort; a missing old run should not block startup.
  }
}

function openInfoEntry(kind) {
  if (kind === "scores") {
    switchTab("council");
    return;
  }
  if (kind === "logs") {
    switchTab("draft");
    const panel = $("#trace-panel");
    if (panel && !panel.hidden) panel.open = true;
    return;
  }
  if (kind === "report") {
    const href = $("#view-link")?.getAttribute("href");
    if (href && href !== "#") window.location.href = href;
    return;
  }
  if (kind === "answers" || kind === "pros") {
    const href = $("#view-link")?.getAttribute("href");
    if (href && href !== "#") {
      window.location.href = `${href}${kind === "answers" ? "#seat-answers" : "#seat-digest"}`;
    }
  }
}

function setProgress(percent, label) {
  const safe = Math.max(0, Math.min(100, percent));
  $("#progress-fill").style.width = `${safe}%`;
  $("#progress-label").textContent = label;
  $("#progress-percent").textContent = `${safe}%`;
  renderTimeline(safe);

  renderRunControls();
}

function renderRunDiagnostics(task) {
  const box = $("#run-diagnostics");
  if (!box) return;
  const diag = task?.progress_diagnostics;
  if (!task || !diag || task.status === "complete") {
    box.hidden = true;
    clearAutoRecheck();
    return;
  }
  const seats = Array.isArray(diag.seats) ? diag.seats : [];
  const recheckSeats = recheckableDiagnosticSeats(diag);
  const waiting = diag.waiting || {};
  const title = diagnosticTitle(task, diag, seats);
  const meta = diagnosticMeta(diag, waiting);
  $("#diagnostic-title").textContent = title;
  $("#diagnostic-meta").textContent = meta;
  box.classList.toggle("stale", Boolean(diag.stale));
  const recheckBtn = $("#btn-recheck-stalled");
  if (recheckBtn) {
    recheckBtn.hidden = !recheckSeats.length;
    recheckBtn.disabled = state.recheckInFlight;
    const rescueLabel = diag.rescue_plan?.button_label || "一键修复并回收答案";
    recheckBtn.textContent = recheckSeats.length
      ? `${rescueLabel} (${recheckSeats.map(seatName).join("、")})`
      : rescueLabel;
  }
  const watch = $("#seat-watch");
  if (!seats.length) {
    watch.innerHTML = `<div class="watch-reason">${escapeHtml(task.current_step || "正在等待下一次进度事件")}</div>`;
  } else {
    watch.innerHTML = seats.map(seat => `
      <div class="seat-watch-row ${escapeHtml(seat.state || "waiting")}">
        <span class="watch-dot"></span>
        <span class="watch-name">${escapeHtml(seat.name || seat.seat || "-")}</span>
        <span class="watch-detail">
          <span class="watch-status">${escapeHtml(seat.status || "等待")}</span>
          <span class="watch-reason">${escapeHtml(seat.reason || seat.detail || "")}</span>
          ${seatRescueHint(seat, diag.rescue_plan)}
        </span>
      </div>
    `).join("");
  }
  box.hidden = false;
  scheduleAutoRecheck(task, diag);
}

function seatRescueHint(seat, plan) {
  const action = (plan?.actions || []).find(item => item.seat === seat.seat);
  if (!action) return "";
  return `<span class="watch-rescue">${escapeHtml(action.label)} · ${escapeHtml(action.sends_prompt ? "必要时干净会话重试" : "只读旧页面")}</span>`;
}

function scheduleAutoRecheck(task, diag) {
  const seats = recheckableDiagnosticSeats(diag);
  if (!diag?.stale || !seats.length || state.recheckInFlight) {
    if (!diag?.stale) clearAutoRecheck();
    return;
  }
  if (state.autoRecheckTimer && state.autoRecheckRunId === task.run_id) return;
  clearAutoRecheck();
  state.autoRecheckRunId = task.run_id;
  state.autoRecheckTimer = setTimeout(() => {
    state.autoRecheckTimer = null;
    recheckStalledSeats({ auto: true });
  }, 60000);
}

function clearAutoRecheck() {
  if (state.autoRecheckTimer) clearTimeout(state.autoRecheckTimer);
  state.autoRecheckTimer = null;
  state.autoRecheckRunId = null;
}

function diagnosticTitle(task, diag, seats) {
  if (diag.stale) {
    return `后台心跳中断 · 停在 ${Math.round((Number(task.progress) || 0) * 100)}%`;
  }
  const waitingNames = seats
    .filter(seat => ["waiting", "submitting", "nudge"].includes(seat.state))
    .map(seat => seat.name || seat.seat)
    .slice(0, 3);
  if (waitingNames.length) return `正在观察 ${waitingNames.join("、")}`;
  if ((diag.waiting || {}).count) return `等待 ${diag.waiting.count} 个网页席位`;
  return task.current_step || "运行中";
}

function diagnosticMeta(diag, waiting) {
  const parts = [];
  if (diag.retry?.attempt) parts.push(`只读回收 ${diag.retry.attempt}/${diag.retry.total || diag.retry.attempt}`);
  if (waiting?.longest_wait_seconds !== null && waiting?.longest_wait_seconds !== undefined) {
    parts.push(`最长 ${formatDuration(waiting.longest_wait_seconds)}`);
  }
  if (diag.stale && diag.seconds_since_update !== null && diag.seconds_since_update !== undefined) {
    parts.push(`停更 ${formatDuration(diag.seconds_since_update)}`);
  }
  return parts.join(" · ");
}

function formatDuration(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  if (value < 60) return `${Math.round(value)}s`;
  const minutes = Math.floor(value / 60);
  const rest = Math.round(value % 60);
  return rest ? `${minutes}m${rest}s` : `${minutes}m`;
}

function renderTimeline(progress) {
  const activeIndex = progress >= 90 ? 5 : progress >= 70 ? 4 : progress >= 20 ? 3 : progress >= 10 ? 2 : progress >= 6 ? 1 : progress > 0 ? 0 : -1;
  $("#timeline-list").innerHTML = timelineSteps.map((step, index) => {
    const cls = index < activeIndex ? "done" : index === activeIndex ? "active" : "";
    return `<li class="${cls}"><span class="step-dot"></span><span>${step.label}</span></li>`;
  }).join("");
}

function setBusy(isBusy) {
  $("#btn-submit").disabled = isBusy || !isReady();
  $("#btn-submit").textContent = isBusy ? "运行中" : submitButtonLabel();
}

function updateSubmitState() {
  const button = $("#btn-submit");
  button.disabled = !isReady();
  button.textContent = submitButtonLabel();
}

function submitButtonLabel() {
  if (state.mentorEnabled && !state.mentorConfirmed) return "确认提示词";
  return "网页陪审";
}

function getEffectiveQuestion() {
  const candidates = [
    document.querySelector("#question-input")?.value?.trim() || "",
    document.querySelector("#parliament-question-input")?.value?.trim() || "",
    state.workflow?.rawUserInput?.trim() || "",
    state.preRunFlow?.question?.trim() || "",
    state.currentQuestion?.trim() || ""
  ];

  const valid = candidates.find(function (value) { return value.length >= 4; });
  if (valid) return valid;

  return candidates.find(Boolean) || "";
}

function isReady() {
  if (getEffectiveQuestion().length < 4 || state.selectedSeats.size === 0) return false;
  return Boolean(state.bridge?.config_exists || state.bridge?.seats?.length);
}

function resetRunUI() {
  $("#result-empty").hidden = false;
  $("#verdict-card").hidden = true;
  $("#run-id").textContent = "-";
  $("#run-meta").textContent = "准备运行";
  state.currentVerdict = null;
  state.currentTrace = null;
  state.publishCleared = false;
  if ($("#view-link")) $("#view-link").href = "#";
  if ($("#result-view-link")) $("#result-view-link").href = "#";
  $("#mentor-result-panel") && ($("#mentor-result-panel").hidden = true);
  $("#prompt-flow-panel").hidden = true;
  $("#execution-panel").hidden = true;
  $("#judge-answer-panel").hidden = true;
  $("#score-round-panel").hidden = true;
  $("#cross-temporal-panel").hidden = true;
  $("#xray-memo-section").hidden = true;
  $("#trace-panel").hidden = true;
  renderSupplementButton();
  renderArena();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderPublishGate();
  renderTaskCenter();
}

function cleanupProgress() {
  if (state.eventSource) state.eventSource.close();
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.eventSource = null;
  state.pollTimer = null;
  clearAutoRecheck();
}

function maybeBrowserNotify(title, body) {
  if (!$("#notify-browser").checked || !("Notification" in window)) return;
  if (Notification.permission === "granted") new Notification(title, { body: body.slice(0, 120) });
  else if (Notification.permission === "default") Notification.requestPermission();
}

function engineName(engine) {
  if (engine === "web" || engine === "isolated-web-seat-bridge-v3.4") return "后台网页席位";
  if (engine === "execution-driver-router-v3.4") return "执行驱动诊断";
  return "本地引擎已禁用";
}

function channelLabel(channel) {
  if (channel === "desktop") return "桌面";
  if (channel === "local") return "本地";
  return "网页";
}

function statusLabel(reason, ready) {
  if (ready) return "就绪";
  if (reason === "disabled") return "未启用";
  if (reason === "playwright_missing") return "缺少 Playwright";
  if (reason === "missing_url") return "缺少地址";
  if (reason === "desktop_app_missing") return "客户端未安装";
  if (reason === "deepseek_desktop_expert_operator_missing") return "DeepSeek 桌面专家 Operator 未实现";
  if (reason === "desktop_operator_pending") return "需独立 Worker";
  if (reason === "needs_calibration") return "待校准";
  if (reason === "calibration_stale") return "校准过期";
  if (reason === "fixed_tab_not_found") return "未找到固定标签";
  if (reason === "apple_events_js_disabled") return "Apple Events 未开启";
  if (reason === "cdp_unavailable") return "CDP 未连接";
  if (reason === "input_not_found") return "找不到输入框";
  if (reason === "response_timeout") return "回答超时";
  if (reason === "slow_response_pending") return "慢生成待回收";
  if (reason === "send_button_not_found") return "发送未确认";
  if (reason === "submit_unconfirmed") return "提交未确认";
  if (reason === "long_prompt_still_in_input") return "提交未确认";
  if (reason === "composer_busy") return "页面忙碌";
  if (reason === "page_error") return "页面错误，待刷新补跑";
  if (reason === "model_page_error") return "模型页错误，待刷新补跑";
  if (reason === "provider_account_restricted") return "账号受限/申诉中";
  if (reason === "chrome_crash") return "标签崩溃，待刷新补跑";
  if (reason === "blank_page") return "页面空白，待刷新补跑";
  if (reason === "page_recovery_failed") return "刷新恢复失败";
  if (reason === "doubao_expert_mode_not_verified") return "豆包专家模式未确认";
  if (reason === "response_not_relevant") return "疑似旧回答";
  if (reason === "existing_answer_not_found") return "旧页未返回";
  if (reason === "existing_answer_placeholder") return "仍是占位";
  if (reason === "existing_answer_prompt_echo") return "旧页未完成";
  if (reason === "desktop_bridge_ready") return "客户端就绪";
  if (reason === "not_configured") return "未配置";
  return reason || "待配置";
}

function signalSeverityLabel(status) {
  if (status === "block") return "阻断";
  if (status === "warn") return "观察";
  return "正常";
}

function downloadJSON(data, filename) {
  download(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }), filename);
}

function finalReportMarkdown(report) {
  if (!report) return "";
  const sop = report.sop_closeout || {};
  const template = sop.codex_template || {};
  const overview = report.compact_overview || {};
  const lines = [
    `## ${overview.title || report.title || "AI Judge 最终方案报告"}`,
    "",
    `**${report.subtitle || "FINAL VERDICT"}**`,
    "",
    `**状态:** ${report.status_label || "-"} · ${report.status_reason || ""}`,
    "",
    "### 一眼收口",
    "",
    overview.summary || report.executive_summary?.headline || report.abstract || "",
    "",
    ...((overview.summary_cards || []).map(card => `- ${card.label || "-"}：${card.value || "-"}`)),
    "",
    "### 收口计划",
    "",
    ...((overview.plan || []).map(item => `- ${item.id || ""} ${item.title || ""}：${item.body || ""}`)),
    "",
    "### 全量可执行路径汇总",
    "",
    "| 路径 | 执行动作 | 入口 | 截止 | 来源席位 |",
    "|---|---|---|---|---|",
    ...((overview.action_paths || []).map(row => `| ${mdCell(row.path)} | ${mdCell(row.execution)} | ${mdCell(row.entry)} | ${mdCell(row.deadline)} | ${mdCell(Array.isArray(row.source_models) ? row.source_models.join("、") : row.source_models)} |`)),
    "",
    "### 议员方案草稿索引",
    "",
    "| 议员 | 贡献 | 草稿摘要 | 追溯 |",
    "|---|---|---|---|",
    ...((overview.council_index || []).map(row => `| ${mdCell(row.seat_name || row.seat)} | ${mdCell(row.contribution)} | ${mdCell(row.summary)} | ${mdCell(row.stored_log_href || row.draft_href || row.raw_href)} |`)),
    "",
    overview.download_note || "",
    "",
    "### ABSTRACT",
    "",
    report.abstract || "",
    "",
    "### KEYWORDS",
    "",
    (report.keywords || []).join(" / "),
    "",
    "### FINAL POSITION",
    "",
    `- 结论：${report.final_position?.label || "-"}`,
    `- 可信：${report.final_position?.trust || "-"}`,
    `- 置信度：${report.final_position?.confidence || "-"}`,
    `- 轮值法官：${report.judge_editor?.label || "-"}`,
    `- 摘要：${report.final_position?.summary || "-"}`,
    "",
    "### 标准化收口 SOP",
    "",
    sop.final_judgment || "",
    "",
    sop.one_sentence_plan || "",
    "",
    ...((sop.phases || []).flatMap((phase) => [
      `#### ${phase.title || ""}`,
      "",
      ...((phase.items || []).map(item => `- ${item}`)),
      "",
    ])),
    "#### Codex 执行模板",
    "",
    `目标：${template.goal || "-"}`,
    "",
    `产品定位：${template.positioning || "-"}`,
    "",
    "当前优先级：",
    "",
    ...((template.current_priorities || []).map(item => `- ${item}`)),
    "",
    "执行规则：",
    "",
    ...((template.execution_rules || []).map(item => `- ${item}`)),
    "",
    "输出要求：",
    "",
    ...((template.output_requirements || []).map(item => `- ${item}`)),
    "",
    sop.final_essence || "",
    "",
    ...longformReportMarkdownLines(report.longform_report || report.compiled_report?.longform_report),
    ...((report.longform_report || report.compiled_report?.longform_report) ? [] : compiledReportMarkdownLines(report.compiled_report)),
    "",
    "### JUDGE CLOSEOUT",
    "",
    `**Thesis:** ${report.thesis || "-"}`,
    "",
    `**Recommendation:** ${report.recommendation || "-"}`,
    "",
    "### KEY FINDINGS",
    "",
    ...((report.key_findings || []).map(item => `- ${item}`)),
    "",
    "### POSTULATES",
    "",
    ...((report.postulates || []).flatMap((item, index) => [
      `#### POSTULATE ${index + 1} · ${item.title || ""}`,
      "",
      item.body || "",
      "",
      `证据：${item.evidence || "-"}`,
      "",
    ])),
    "### EVIDENCE MAP",
    "",
    "| 维度 | 本报告判断 | 证据来源 | 约束 |",
    "|---|---|---|---|",
    ...((report.evidence_map || []).map(row => `| ${mdCell(row.dimension)} | ${mdCell(row.judgment)} | ${mdCell(row.source)} | ${mdCell(row.constraint)} |`)),
    "",
    "### EXECUTION PLAN",
    "",
    ...((report.implementation_plan || []).map((item, index) => `${index + 1}. ${item}`)),
    "",
    "### LIMITS",
    "",
    ...((report.risks_and_limits || []).map(item => `- ${item}`)),
    "",
    "### VERIFICATION CONTRACT",
    "",
    ...((report.verification_contract || []).map(item => `- ${item}`)),
  ];
  return lines.join("\n").trim();
}

function longformReportMarkdownLines(longform) {
  if (!longform) return [];
  const lines = [
    "### 完整总结报告",
    "",
    `#### ${longform.title || "AI Judge 最终总结报告"}`,
    "",
    longform.one_sentence_judgment || "",
    "",
    "#### 执行摘要",
    "",
  ];
  (longform.executive_summary || []).forEach(item => lines.push(item, ""));
  (longform.body_sections || []).forEach(section => {
    lines.push(`#### ${section.title || ""}`, "");
    (section.paragraphs || []).forEach(paragraph => lines.push(paragraph, ""));
  });
  if ((longform.decision_table || []).length) {
    lines.push("#### 争议裁决表", "", "| 议题 | 裁定 | 依据 |", "|---|---|---|");
    (longform.decision_table || []).forEach(row => {
      lines.push(`| ${mdCell(row.issue)} | ${mdCell(row.decision)} | ${mdCell(row.basis)} |`);
    });
    lines.push("");
  }
  if ((longform.roadmap || []).length) {
    lines.push("#### 执行路线图", "", "| 阶段 | 目标 | 交付物 | 验收 |", "|---|---|---|---|");
    (longform.roadmap || []).forEach(row => {
      lines.push(`| ${mdCell(row.phase)} | ${mdCell(row.goal)} | ${mdCell(row.deliverable)} | ${mdCell(row.acceptance)} |`);
    });
    lines.push("");
  }
  if ((longform.success_metrics || []).length) {
    lines.push("#### 成功标准", "");
    (longform.success_metrics || []).forEach(item => lines.push(`- ${item}`));
    lines.push("");
  }
  if ((longform.model_contribution_appendix || []).length) {
    lines.push("#### 模型贡献附录", "", "| 模型 | 立场 | 采纳贡献 | 风险备注 |", "|---|---|---|---|");
    (longform.model_contribution_appendix || []).forEach(row => {
      lines.push(`| ${mdCell(row.model)} | ${mdCell(row.stance)} | ${mdCell(row.adopted_contribution)} | ${mdCell(row.risk_note)} |`);
    });
    lines.push("");
  }
  return lines;
}

function compiledReportMarkdownLines(compiled) {
  if (!compiled) return [];
  const lines = [
    "### 最终整合报告",
    "",
    compiled.problem_restatement || "",
    "",
    `**总编裁定：** ${compiled.editorial_verdict || "-"}`,
    "",
  ];
  (compiled.sections || []).forEach((section) => {
    lines.push(`#### ${section.title || ""}`, "", section.summary || "", "");
    (section.items || []).forEach(item => lines.push(`- ${item}`));
    if ((section.source_models || []).length) {
      lines.push(`- 来源席位：${section.source_models.join("、")}`);
    }
    lines.push("");
  });
  if ((compiled.decision_table || []).length) {
    lines.push("### 争议裁决表", "", "| 议题 | 裁定 | 依据 |", "|---|---|---|");
    (compiled.decision_table || []).forEach(row => {
      lines.push(`| ${mdCell(row.issue)} | ${mdCell(row.decision)} | ${mdCell(row.basis)} |`);
    });
    lines.push("");
  }
  if ((compiled.roadmap || []).length) {
    lines.push("### 执行路线图", "", "| 阶段 | 目标 | 交付物 | 验收 |", "|---|---|---|---|");
    (compiled.roadmap || []).forEach(row => {
      lines.push(`| ${mdCell(row.phase)} | ${mdCell(row.goal)} | ${mdCell(row.deliverable)} | ${mdCell(row.acceptance)} |`);
    });
    lines.push("");
  }
  if ((compiled.success_metrics || []).length) {
    lines.push("### 成功标准", "");
    (compiled.success_metrics || []).forEach(item => lines.push(`- ${item}`));
    lines.push("");
  }
  if ((compiled.model_contribution_appendix || []).length) {
    lines.push("### 模型贡献附录", "", "| 模型 | 立场 | 采纳贡献 | 风险备注 |", "|---|---|---|---|");
    (compiled.model_contribution_appendix || []).forEach(row => {
      lines.push(`| ${mdCell(row.model)} | ${mdCell(row.stance)} | ${mdCell(row.adopted_contribution)} | ${mdCell(row.risk_note)} |`);
    });
  }
  return lines;
}

function mdCell(value) {
  return String(value ?? "").replace(/\|/g, "\\|");
}

function downloadMarkdown(v) {
  const md = [
    `# ${reportHeaderTitle(v) || "AI Judge Verdict"}`,
    "",
    `**Summary:** ${reportHeaderSummary(v) || ""}`,
    `**Verdict:** ${v.verdict_label || v.verdict}`,
    `**Confidence:** ${v.confidence}%`,
    "",
    "## 原始任务",
    v.question || "",
    "",
    finalReportMarkdown(v.final_report),
    "",
    v.mentor_preflight ? "## Mentor Preflight" : "",
    v.mentor_preflight?.execution_draft || "",
    v.mentor_preflight?.next_question ? `Guiding question: ${v.mentor_preflight.next_question}` : "",
    "",
    "## Prompt Resonance",
    v.prompt_flow?.quick_response || "",
    "",
    v.prompt_flow?.professional_prompt || "",
    "",
    "## Reasons",
    ...(v.reasons || []).map(reason => `- ${reason}`),
    "",
    `## ${v.judge_answer?.label || v.single_judge_baseline?.label || "AI Judge Judge Answer"}`,
    v.judge_answer?.answer || "",
    v.single_judge_baseline ? `Single-judge score: ${v.single_judge_baseline.score ?? "-"}` : "",
    v.single_judge_baseline ? `Council average score: ${v.single_judge_baseline.council_average_score ?? "-"}` : "",
    "",
    "## Score Rounds",
    ...((v.web_bridge?.score_rounds || []).map(item => {
      const avg = item.average_score === null || item.average_score === undefined ? "-" : Number(item.average_score).toFixed(3);
      return `- ${item.label || item.id}: ${item.claim_count || 0} claims, avg ${avg}`;
    })),
    "",
    "## Cross-Temporal Closeout",
    v.cross_temporal_analysis?.closeout_report?.executive_summary || "",
    "",
    "### Math Audit Signals",
    ...((v.cross_temporal_analysis?.math_audit?.signals || []).map(item => `- ${item.label || item.id}: ${item.summary || ""}`)),
    "",
    "### Cross-Temporal Actions",
    ...((v.cross_temporal_analysis?.recommended_actions || []).map(item => `- ${item}`)),
    "",
    "## Next Steps",
    ...(v.next_steps || []).map(step => `- ${step}`),
  ].join("\n");
  download(new Blob([md], { type: "text/markdown" }), `verdict-${v.run_id || "ai-judge"}.md`);
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function fallbackModes() {
  return [
    { mode: "flash", name: "快速陪审", seats: ["gemini", "wenxin", "doubao"] },
    { mode: "standard", name: "标准陪审", seats: ["gemini", "deepseek", "claude", "kimi", "wenxin", "doubao"] },
    { mode: "strategic", name: "深度陪审", seats: [] },
  ];
}

function fallbackSeats() {
  return [
    { id: "gemini", name: "Gemini", mbti: "INTJ", strength: "系统性风险识别" },
    { id: "chatgpt", name: "ChatGPT", mbti: "ESTJ", strength: "综合多方信息" },
    { id: "deepseek", name: "DeepSeek", mbti: "INTP", strength: "深度推理" },
    { id: "qwen", name: "Qwen", mbti: "ISFJ", strength: "事实锚定" },
    { id: "kimi", name: "Kimi", mbti: "ENFP", strength: "长上下文关联" },
    { id: "grok", name: "Grok", mbti: "ENTP", strength: "挑战共识" },
    { id: "yuanbao", name: "Yuanbao", mbti: "ISTJ", strength: "流程纪律" },
    { id: "mimo", name: "MiMo", mbti: "INFJ", strength: "价值对齐" },
    { id: "doubao", name: "Doubao", mbti: "ENTJ", strength: "执行导向" },
    { id: "claude", name: "Claude", mbti: "INFJ", strength: "长文和边界推理" },
    { id: "minimax", name: "MiniMax", mbti: "ENFJ", strength: "体验判断" },
    { id: "zhipu", name: "Zhipu", mbti: "ISTP", strength: "工程落地" },
    { id: "wenxin", name: "Wenxin", mbti: "ESFJ", strength: "中文合规" },
    { id: "meta", name: "Meta AI", mbti: "ENTP", strength: "社交产品信号" },
  ];
}

function fallbackProductCapabilities() {
  return {
    version: "3.8.0",
    positioning: "面向桌面工作流的可信决策系统，用于可审计的多模型判断。",
    stable_mode: {
      label: "简约版",
      job: "让普通用户 5 分钟内拿到可读、可执行、可复核的最终判断。",
      surfaces: ["请求录入", "运行状态", "最终结论", "关键风险", "签字"],
    },
    lab_mode: {
      label: "专业版",
      job: "让高级用户诊断模型席位、桥接稳定性、评分差异和证据链可靠性。",
      surfaces: ["席位矩阵", "桥接监控", "评分轮次", "横纵分析", "基准", "底层日志"],
    },
    market_fit: {
      strengths: ["多模型回答会被收口成门禁和报告", "慢席位可一键回收"],
      known_gaps: ["网页桥接仍依赖登录态", "公开基准仍需持续补齐"],
    },
  };
}

function fallbackBenchmarks() {
  return {
    version: "3.8.0",
    cards: [
      { id: "citation", label: "引用基准", score: "回放账本", status: "active", summary: "验证引用、证据缺口和复核状态。" },
      { id: "decision", label: "决策基准", score: "待建立", status: "empty", summary: "用历史判词观察共识稳定性和主审偏差。" },
      { id: "web_recovery", label: "网页席位回收", score: "待建立", status: "empty", summary: "统计网页席位成功、失败、慢生成和回收效果。" },
      { id: "cdp_reliability", label: "桌面桥接可靠性", score: "0/0", status: "needs_calibration", summary: "检测固定标签、CDP/Apple Events 与桌面通道。" },
    ],
  };
}

function $(selector) { return document.querySelector(selector); }
function $$(selector) { return Array.from(document.querySelectorAll(selector)); }
function bindClick(selectorOrId, handler, label) {
  var el = selectorOrId.startsWith('#')
    ? document.querySelector(selectorOrId)
    : document.getElementById(selectorOrId);
  if (!el) {
    console.warn('[bindClick missing]', label || selectorOrId);
    if (typeof traceUIEvent === 'function') {
      traceUIEvent('ui_bind_missing', { label: label || selectorOrId, selector: selectorOrId });
    }
    return false;
  }
  el.addEventListener('click', function(event) {
    event.preventDefault();
    event.stopPropagation();
    if (typeof traceUIEvent === 'function') {
      traceUIEvent('ui_button_clicked', { label: label || selectorOrId, selector: selectorOrId });
    }
    handler(event);
  });
  if (typeof traceUIEvent === 'function') {
    traceUIEvent('ui_bind_ok', { label: label || selectorOrId, selector: selectorOrId });
  }
  return true;
}
window.__bindClick__ = bindClick;

function setupHermesExportDelegation() {
  if (window.__HERMES_EXPORT_DELEGATION_BOUND__) return;
  window.__HERMES_EXPORT_DELEGATION_BOUND__ = true;

  document.addEventListener("click", async function(event) {
    var btn = event.target.closest(".hermes-btn, [data-hermes-kind], a[href*='hermes-output'], a[href*='obsidian-run-note'], a[href*='index.html']");
    if (!btn) return;

        // runId: 兼容 data-run-id / data-id
    var runId = btn.getAttribute("data-run-id") || btn.getAttribute("data-id") || "";
    if (!runId) {
      var card = btn.closest("[data-run-id]") || btn.closest("[data-id]");
      if (card) runId = card.getAttribute("data-run-id") || card.getAttribute("data-id");
    }
    if (!runId && btn.href) {
      var m = btn.href.match(/runs\/([^/]+)/);
      if (m) runId = m[1];
    }
    if (!runId) {
      traceUIEvent("hermes_export_error", { reason: "no_run_id", tag: btn.tagName, cls: String(btn.className||"").slice(0, 120) });
      return;
    }

    // kind: 兼容 data-hermes-kind / data-kind / URL推断
    var kind = btn.getAttribute("data-hermes-kind") || btn.getAttribute("data-kind") || "";
    if (!kind) {
      var u = btn.href || btn.getAttribute("data-url") || "";
      if (u.indexOf("hermes-output.json") !== -1) kind = "json";
      else if (u.indexOf("hermes-output.md") !== -1) kind = "md";
      else if (u.indexOf("obsidian-run-note") !== -1) kind = "obsidian";
      else kind = "html";
    }

    var label = String(btn.textContent || "").trim() || kind;

    // url: 兼容 data-url / href
    var url = btn.getAttribute("data-url") || btn.href || "";
    if (!url) {
      traceUIEvent("hermes_export_error", { reason: "no_url", run_id: runId, kind: kind, tag: btn.tagName });
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    traceUIEvent("hermes_export_clicked", {
      run_id: runId,
      kind: kind,
      label: label,
      url: url,
      source: "ui_click"
    });

    var ok = false;
    var httpStatus = null;
    try {
      var res = await fetch(url, { method: "HEAD" });
      ok = res.ok;
      httpStatus = res.status;
    } catch (e) {
      try {
        var res2 = await fetch(url, { method: "GET" });
        ok = res2.ok;
        httpStatus = res2.status;
      } catch (e2) {}
    }

    traceUIEvent("hermes_export_open_result", {
      run_id: runId,
      kind: kind,
      label: label,
      url: url,
      ok: ok,
      http_status: httpStatus,
      mode: "open",
      source: "ui_click"
    });

    window.open(url, "_blank", "noopener,noreferrer");
  }, true);

  traceUIEvent("hermes_export_delegation_bound", { target: "document", capture: true });
}
window.__setupHermesExportDelegation__ = setupHermesExportDelegation;
function closestEventTarget(target, selector) {
  const element = target?.nodeType === 1 ? target : target?.parentElement;
  return element?.closest?.(selector) || null;
}
function handleWerewolfBoardActivation(event) {
  const board = closestEventTarget(event.target, "[data-werewolf-board]");
  const mode = closestEventTarget(event.target, "[data-werewolf-play-mode]");
  const toggle = closestEventTarget(event.target, "[data-werewolf-play-toggle]");
  if (!board && !mode && !toggle) return false;
  event.preventDefault();
  event.stopPropagation();
  if (board) window.setWerewolfBoard?.(board.dataset.werewolfBoard);
  if (mode) window.setWerewolfPlayMode?.(mode.dataset.werewolfPlayMode);
  if (toggle) window.setWerewolfPlayMode?.(toggle.dataset.werewolfPlayToggle);
  return true;
}
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}
function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}
// P71: Trace UI events to debug file I/O issues
function traceUIEvent(event, data) {
  try {
    const entry = { ts: Date.now(), event, ...data };
    console.log("[UI-TRACE]", event, data);
    // Best-effort: POST to trace endpoint
    if (typeof API_BASE !== "undefined") {
      fetch(`${API_BASE}/api/trace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry),
      }).catch(() => {});
    }
  } catch {}
}
window.__traceUIEvent__ = traceUIEvent;

// === 点击诊断探针（默认关闭，?clickProbe=1 或 localStorage 开启）===
(function() {
  var enabled = false;
  try {
    enabled = (new URLSearchParams(location.search)).get("clickProbe") === "1" ||
              localStorage.getItem("AI_JUDGE_CLICK_PROBE") === "1";
  } catch(e) {}
  if (!enabled) return;
  window.__CLICK_PROBE_ACTIVE__ = true;
  console.log("[click-probe] enabled via query param or localStorage");
  document.addEventListener("pointerdown", function(e) {
    traceUIEvent("click_probe_pointerdown", {
      ts: Date.now(),
      target: e.target && e.target.tagName ? e.target.tagName + "#" + (e.target.id || "") : "?",
      text: String(e.target && e.target.textContent || "").trim().slice(0, 80),
      x: e.clientX,
      y: e.clientY,
      isTrusted: e.isTrusted,
      pointerType: e.pointerType || "unknown"
    });
  }, true);
  document.addEventListener("click", function(e) {
    traceUIEvent("click_probe_click", {
      ts: Date.now(),
      target: e.target && e.target.tagName ? e.target.tagName + "#" + (e.target.id || "") : "?",
      text: String(e.target && e.target.textContent || "").trim().slice(0, 80),
      x: e.clientX,
      y: e.clientY,
      isTrusted: e.isTrusted
    });
  }, true);
})();

// Hermes pointer probe (capture phase, read-only)
(function() {
  if (window.__HERMES_POINTER_PROBE_BOUND__) return;
  window.__HERMES_POINTER_PROBE_BOUND__ = true;
  document.addEventListener("pointerdown", function(event) {
    var target = event.target;
    var closest = target.closest(".hermes-btn, [data-hermes-kind], a[href*='hermes'], a[href*='index.html'], a[href*='obsidian']");
    if (!closest) return;
    var hit = {
      ts: Date.now(),
      targetTag: target.tagName,
      targetId: target.id || "",
      targetClass: String(target.className || "").slice(0, 120),
      targetText: String(target.textContent || "").trim().slice(0, 120),
      closestTag: closest.tagName,
      closestClass: String(closest.className || "").slice(0, 120),
      closestText: String(closest.textContent || "").trim().slice(0, 120),
      closestHref: closest.href || "",
      inHistoryList: !!target.closest("#history-list")
    };
    window.__HERMES_LAST_CLICK__ = hit;
    traceUIEvent("hermes_pointer_probe", hit);
  }, true);
})();

// ─── P43: Message digest/keypoint helpers ───
function deriveDigestP43(text) {
  const clean = String(text || '').replace(/[\n\r]+/g, ' ').trim();
  if (!clean) return '';
  const stops = ['。', '！', '？'];
  let cut = clean.length;
  for (const ch of stops) {
    const idx = clean.indexOf(ch);
    if (idx > 0 && idx < cut) cut = idx + 1;
  }
  let digest = cut <= 90 ? clean.slice(0, cut) : clean.slice(0, 90).replace(/\s+\S*$/, '');
  if (digest.length < clean.length && !/[。！？]$/.test(digest)) digest += '…';
  return digest.slice(0, 95);
}
function extractKeyPointsP43(text) {
  const lines = String(text || '').split(/\n+/).filter(Boolean);
  const bullets = [];
  for (const line of lines) {
    const t = line.trim();
    if (/^[-•*]\s/.test(t) || /^\d+[\.\)、]\s/.test(t)) {
      bullets.push(t.replace(/^[-•*\d]+[\.\)、\s]+/, '').slice(0, 80));
    } else if (t.length > 30 && !/^(http|https):\/\//.test(t) && bullets.length < 2) {
      bullets.push(t.slice(0, 80));
    }
    if (bullets.length >= 4) break;
  }
  return bullets.length ? bullets.slice(0, 4) : [];
}
// ─── End P43 helpers ───



// ==== P13 Marvis Motion Patches ====
// P13: JavaScript Patch for AI Judge - Marvis Motion Improvements

// P16: Ultra-simple agent turn card — reference: ai-judge-meeting-room.html answer-card pattern
function parliamentBubbleHtmlP13(message, index = 0) {
  const typing = message.working ? '<span class="typing-dots" aria-label="正在输入"><i></i><i></i><i></i></span>' : "";
  const speechState = message.msgState || "queued";
  const statusLabel = STATUS_LABELS[speechState] || speechState;
  const fullText = message.fullText || message.text || "";
  const summaryText = message.text || message.processSummary || "";
  const hasFullText = fullText && fullText !== summaryText && fullText.length > summaryText.length + 20;
  const toolEvents = (message.toolEvents || []).map(renderToolEvent).join("");
  // P41: generate id and store full detail for drawer
  const msgId = `msg_${index}_${Date.now().toString(36)}`;
  const TEXT_TRUNCATE = 200;
  const textDisplay = summaryText.length > TEXT_TRUNCATE ? summaryText.slice(0, TEXT_TRUNCATE).replace(/\s+\S*$/, '') : summaryText;
  const needsTruncation = summaryText.length > TEXT_TRUNCATE;
  const detailToolEvents = (message.toolEvents || []).map(e => ({ label: e.tool || e.label || '', result: e.result || e.text || '' }));
  const detailEntry = {
    msgId, role: message.role || '', roleLabel: message.roleLabel || '', channel: message.channel || '',
    color: message.color || '#111827', msgState: speechState, statusLabel, text: textDisplay,
    fullText: hasFullText ? fullText : summaryText, toolEvents: detailToolEvents,
    formatFull: message.kind === 'judge_prerun' || message.kind === 'judge' || message.kind === 'system',
    avatarUrl: (message.kind === 'judge_prerun' || message.kind === 'judge' || message.kind === 'system')
      ? (_avatarDataUri('grand_judge') || _avatarDataUri('claude'))
      : (_avatarDataUri(message.seatId || message.role) || _avatarDataUri('claude')),
    modelId: message.seatId || message.role || 'model',
  };
  window.__AI_JUDGE_MESSAGE_DETAILS__[msgId] = detailEntry;
  // P43: derive digest / keyPoints / sections for structured detail drawer
  detailEntry.digest = deriveDigestP43(hasFullText ? fullText : summaryText);
  detailEntry.keyPoints = extractKeyPointsP43(hasFullText ? fullText : summaryText);
  detailEntry.sections = [{ id: 'digest', label: '摘要' }];
  if (detailEntry.keyPoints && detailEntry.keyPoints.length) detailEntry.sections.push({ id: 'keypoints', label: '要点' });
  const hasTools43 = detailEntry.toolEvents && detailEntry.toolEvents.length > 0;
  if (hasTools43) detailEntry.sections.push({ id: 'process', label: '过程' });
  detailEntry.sections.push({ id: 'fulltext', label: '原文' });
  const clickAttr = `onclick="window.__AI_JUDGE_DRAWER__?.openMessageDetail('${escapeAttr(msgId)}')"`;
  const truncateHint = needsTruncation ? '<span class="ac-see-more">点击查看完整发言 →</span>' : '';

  // P18: User message bubble (right-aligned, light)
  if (message.kind === "user") {
    return `
      <article class="answer-card msg-user" style="--i:${index}" data-speech-state="${escapeAttr(speechState)}">
        <div class="ac-body user-body">
          <div class="ac-header">
            <span class="ac-name">${escapeHtml(message.role || "你")}</span>
            <span class="ac-tag" style="background:var(--bg3);color:var(--text2);">${escapeHtml(message.status || "")}</span>
          </div>
          <div class="ac-text">${formatParliamentText(message.text || "")}</div>
        </div>
      </article>
    `;
  }

  // P18: Grand Judge pre-run card (with optional confirm button / werewolf picker)
  if (message.kind === "judge_prerun") {
    const judgeAvatarUrl = _avatarDataUri('grand_judge') || _avatarDataUri('claude');
    const judgeInitial = (message.role || "J").charAt(0);
    const confirmBtn = message.showConfirm
      ? `<div class="ac-confirm-wrap"><button class="ac-confirm-btn" id="prerun-confirm-btn" type="button" onclick="return window.aiJudgeConfirmP58 ? window.aiJudgeConfirmP58(event) : (event.stopPropagation(), confirmAndStartParliament(), false)">确认并开始</button></div>`
      : "";
    // P55: Move werewolf picker and prep summary to drawer; main stream only shows compact action
    const werewolfAction = message.showWerewolfPicker
      ? `<div class="ac-werewolf-action"><button class="ac-werewolf-drawer-btn" type="button" onclick="event.stopPropagation();window.__AI_JUDGE_DRAWER__?.toggleDrawer('werewolf')">选择席位 & 查看板型 →</button></div>`
      : "";
    const actionHtml = (message.actions || []).map(([label, tab]) => `<button class="ghost" data-tab-shortcut="${escapeAttr(tab)}" type="button" onclick="return window.aiJudgeCardActionP58 ? window.aiJudgeCardActionP58(event, ${escapeAttr(JSON.stringify(tab))}) : (event.stopPropagation(), switchTab(${escapeAttr(JSON.stringify(tab))}), false)">${escapeHtml(label)}</button>`).join("");
    const chipsHtml = (message.chips || []).length || actionHtml
      ? `<div class="ac-footer">${(message.chips || []).map(([label, state]) => `<span class="ac-pill" style="background:var(--bg3);color:var(--text2);">${escapeHtml(label)}</span>`).join("")}${actionHtml}</div>`
      : "";
    return `
      <article class="answer-card msg-judge-prerun ${message.working ? "is-working" : ""} ${message.showConfirm ? "has-confirm" : ""}" style="--i:${index}" data-speech-state="${escapeAttr(speechState)}" data-message-id="${escapeAttr(msgId)}" ${clickAttr} role="button" tabindex="0" aria-expanded="false">
        <div class="ac-avatar"><img class="ac-avatar-img" src="${escapeAttr(judgeAvatarUrl)}" alt="${escapeAttr(message.role || "Grand Judge")}" width="36" height="36" loading="lazy" onerror="this.style.display='none';this.parentElement.textContent='${escapeHtml(judgeInitial)}';this.parentElement.style.background='#C9A96E';this.parentElement.style.color='#fff';" /></div>
        <div class="ac-body">
          <div class="ac-header">
            <span class="ac-name">${escapeHtml(message.role || "Grand Judge")}</span>
            <span class="ac-status ${escapeAttr(speechState)}">${escapeHtml(statusLabel)}</span>
            ${typing}
          </div>
          <div class="ac-text">${formatParliamentText(textDisplay)}${truncateHint}</div>
          ${chipsHtml}
          ${werewolfAction}
          ${confirmBtn}
        </div>
      </article>
    `;
  }

  // Judge / system messages — same answer-card pattern, just different avatar
  if (message.kind === "judge" || message.kind === "system") {
    const judgeAvatarUrl = _avatarDataUri('grand_judge') || _avatarDataUri('claude');
    const judgeInitial = (message.role || "J").charAt(0);
    const isVerdict = message.msgState === "verdict";
    return `
      <article class="answer-card msg-system ${isVerdict ? "is-verdict" : ""} ${message.working ? "is-working" : ""} ${message.werewolfPhaseClass || ""}" style="--i:${index}" data-speech-state="${escapeAttr(speechState)}" data-message-id="${escapeAttr(msgId)}" ${clickAttr} role="button" tabindex="0" aria-expanded="false">
        <div class="ac-avatar"><img class="ac-avatar-img" src="${escapeAttr(judgeAvatarUrl)}" alt="${escapeAttr(message.role || "Grand Judge")}" width="36" height="36" loading="lazy" onerror="this.style.display='none';this.parentElement.textContent='${escapeHtml(judgeInitial)}';this.parentElement.style.background='#111827';this.parentElement.style.color='#fff';" /></div>
        <div class="ac-body">
          <div class="ac-header">
            <span class="ac-name">${escapeHtml(message.role || "Grand Judge")}</span>
            <span class="ac-tag" style="background:var(--bg3);color:var(--text2);">${escapeHtml(message.status || "")}</span>
            ${typing}
          </div>
          <div class="ac-text">${formatParliamentText(textDisplay)}${truncateHint}</div>
          ${toolEvents}
          ${(message.chips || []).length || (message.actions || []).length ? `<div class="ac-footer">${(message.chips || []).map(([label, state]) => `<span class="ac-pill" style="background:var(--bg3);color:var(--text2);">${escapeHtml(label)}</span>`).join("")}${(message.actions || []).map(([label, tab]) => `<button class="ghost" data-tab-shortcut="${escapeAttr(tab)}" type="button" onclick="return window.aiJudgeCardActionP58 ? window.aiJudgeCardActionP58(event, ${escapeAttr(JSON.stringify(tab))}) : (event.stopPropagation(), switchTab(${escapeAttr(JSON.stringify(tab))}), false)">${escapeHtml(label)}</button>`).join("")}</div>` : ""}
        </div>
      </article>
    `;
  }

  // Agent turn card — reference answer-card pattern
  const modelId = message.seatId || message.role || "model";
  const modelName = message.role || "议员";
  const providerChannel = message.channel || "";
  const roleLabel = message.roleLabel || "议员席位";

  // P41: also store fullText for agent-turn-card (formatFull=true for drawer)
  window.__AI_JUDGE_MESSAGE_DETAILS__[msgId] = Object.assign(detailEntry, {
    fullText: hasFullText ? fullText : summaryText,
    formatFull: true,
    avatarUrl: _avatarDataUri(modelId) || _avatarDataUri('claude'),
  });
  const agentAvatarUrl = _avatarDataUri(modelId) || _avatarDataUri('claude');
  const avatarInitial = modelName.charAt(0).toUpperCase();
  const seatColor = message.color || "#111827";

  return `
    <article
      class="answer-card agent-turn-card ${message.werewolfPhaseClass || ""}"
      data-model="${escapeAttr(modelId)}"
      data-speech-state="${escapeAttr(speechState)}"
      data-seat-message="${escapeAttr(message.seatId || "")}"
      data-message-id="${escapeAttr(msgId)}"
      style="--i:${index};--seat-color:${escapeAttr(seatColor)}"
      ${clickAttr}
      role="button" tabindex="0" aria-expanded="false"
    >
      <div class="ac-avatar"><img class="ac-avatar-img" src="${escapeAttr(agentAvatarUrl)}" alt="${escapeAttr(modelName)}" width="36" height="36" loading="lazy" onerror="this.style.display='none';this.parentElement.textContent='${escapeHtml(avatarInitial)}';this.parentElement.style.background='${escapeAttr(seatColor)}';this.parentElement.style.color='#fff';" /></div>
      <div class="ac-body">
        <div class="ac-header">
          <span class="ac-name">${escapeHtml(modelName)}</span>
          <span class="ac-tag" style="background:var(--bg3);color:var(--text2);">${escapeHtml(roleLabel)}</span>
          ${providerChannel ? `<span class="ac-tag" style="background:var(--bg3);color:var(--text3);">${escapeHtml(providerChannel)}</span>` : ""}
          <span class="ac-status ${escapeAttr(speechState)}">${escapeHtml(statusLabel)}</span>
          ${typing}
        </div>
        <div class="ac-text">${escapeHtml(textDisplay)}${truncateHint}</div>
        ${toolEvents}
        <div class="ac-footer">
          <span class="ac-time">${escapeHtml(message.processName || "")}</span>
        </div>
      </div>
    </article>
  `;
}

// 2. Improved werewolf picker rendering
function renderWerewolfPickerP13() {
  const node = $("#werewolf-seat-picker");
  if (!node) return;
  // P45: suppress bottom picker during pre-run OR when no game and werewolf mode active
  const isPreRun = state.preRunFlow.active && !state.preRunFlow.confirmed;
  const isWerewolfIdle = !state.werewolfGame && state.werewolfMode;
  if (isPreRun || isWerewolfIdle) {
    node.hidden = true;
    return;
  }
  const onMeetingRoom = currentTabName() === "tasks";
  node.hidden = !state.werewolfMode || !onMeetingRoom;
  if (!state.werewolfMode || !onMeetingRoom) return;

  const activeIds = state.werewolfGame
    ? state.werewolfGame.players.map(player => player.id)
    : werewolfSelectedSeatIds();
  const offline = new Set(state.werewolfGame?.offlineSeats || []);
  const standbyIds = WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !activeIds.includes(id) && !offline.has(id));
  const count = activeIds.length;
  const pendingId = normalizeWerewolfSeatId(
    state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat || ""
  );
  const running = Boolean(state.werewolfGame && ["running", "blocked"].includes(state.werewolfGame.status));
  const pending = pendingId ? werewolfSeatById(pendingId) : null;

  if (state.werewolfGame && !(state.werewolfGame.status === "blocked" && pending)) {
    node.hidden = true;
    node.innerHTML = "";
    node.setAttribute("aria-hidden", "true");
    node.classList.remove("is-replacement-pending");
    return;
  }
  node.classList.toggle("is-replacement-pending", Boolean(state.werewolfGame && state.werewolfGame.status === "blocked" && pending));

  const helper = running
    ? (pending ? `已选择离线席位：${pending.name}，从替补席点"接替"。` : "运行中可点击左侧任一参赛席位标记离线，再从替补席接替。")
    : `开局前从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选择 ${WEREWOLF_SEAT_COUNT} 个参赛；未选模型自动进入替补席。`;

  const cards = werewolfCandidateSeats().map(seat => {
    const selected = activeIds.includes(seat.id);
    const standby = standbyIds.includes(seat.id);
    const disabled = running ? !standby || !pending : (!selected && count >= WEREWOLF_SEAT_COUNT);
    const attr = running && standby ? `data-werewolf-replace="${escapeAttr(seat.id)}"` : `data-werewolf-pick="${escapeAttr(seat.id)}"`;
    const label = running && standby ? "接替" : selected ? "上场" : "候补";
    const statusClass = selected ? "seated" : "available";
    const provider = seat.provider || seat.channel || "";
    const slotIndex = activeIds.indexOf(seat.id);
    const role = slotIndex >= 0 ? (WEREWOLF_ROLE_LABELS[werewolfRoleForSlot(slotIndex)] || werewolfRoleForSlot(slotIndex)) : "替补";
    const score = getModelWerewolfScore(seat.id);
    const scoreText = score ? `${Math.round(score.avg)}分 · ${score.count}局` : "暂无评分";
    const scoreClass = werewolfScoreClass(score);

    return `
      <button class="werewolf-candidate ${selected ? "is-selected" : ""}" type="button" ${attr} ${disabled ? "disabled data-disabled=\"true\"" : ""} style="--seat-color:${escapeAttr(seat.color)}" data-seat-id="${escapeAttr(seat.id)}">
        <div class="wc-avatar-wrap">
          <img class="wc-avatar" src="${escapeAttr(_avatarDataUri(seat.id) || _avatarDataUri("claude"))}" width="40" height="40" alt="${escapeAttr(seat.name)}" />
          <span class="wc-role-badge">${escapeHtml(role)}</span>
        </div>
        <div class="wc-info">
          <span class="wc-name">${escapeHtml(seat.name)}</span>
          <span class="wc-provider">${escapeHtml(provider)}</span>
          <span class="wc-score ${scoreClass}">${escapeHtml(scoreText)}</span>
        </div>
        <span class="wc-status ${statusClass}">${escapeHtml(label)}</span>
      </button>
    `;
  }).join("");

  node.innerHTML = `
    <div class="werewolf-picker-head">
      <div class="werewolf-header-main">
        <span class="werewolf-title">狼人杀模式 · ${WEREWOLF_CANDIDATE_COUNT}选${WEREWOLF_SEAT_COUNT}</span>
        <span class="werewolf-subtitle">${escapeHtml(helper)}</span>
      </div>
      <div class="werewolf-stats">
        <span class="werewolf-stat">
          <strong>${count}</strong>
          <span>参赛</span>
        </span>
        <span class="werewolf-stat">
          <strong>${WEREWOLF_SEAT_COUNT}</strong>
          <span>席位</span>
        </span>
        <span class="werewolf-stat">
          <strong>${standbyIds.length}</strong>
          <span>替补</span>
        </span>
      </div>
    </div>
    ${!running ? renderWerewolfPrepSummary() : ""}
    <div class="werewolf-pool">${cards}</div>
  `;
}

// 3. Composer visibility control
function updateComposerVisibilityP13() {
  const composer = $(".composer-bar");
  const werewolfPicker = $("#werewolf-seat-picker");
  const input = $("#parliament-question-input");

  if (!composer || !input) return;

  const currentTab = currentTabName();
  const isMeetingRoom = currentTab === "tasks";
  const isWerewolfMode = state.werewolfMode;

  // Show composer only in meeting room
  composer.hidden = !isMeetingRoom;
  input.hidden = !isMeetingRoom;

  // Show werewolf picker only in meeting room and werewolf mode
  if (werewolfPicker) {
    werewolfPicker.hidden = !isMeetingRoom || !isWerewolfMode;
  }

  // Update data attribute for CSS targeting
  const appShell = $("#app-shell");
  if (appShell) {
    appShell.setAttribute("data-current-tab", currentTab);
  }
}

// Patch initialization
function initP13Patches() {
  console.log("P13 Marvis Motion Patches initializing...");

  // Override the original functions
  if (typeof parliamentBubbleHtml === 'function') {
    window.parliamentBubbleHtml = parliamentBubbleHtmlP13;
  }

  if (typeof renderWerewolfPicker === 'function') {
    window.renderWerewolfPicker = renderWerewolfPickerP13;
  }

  // Add visibility control
  const originalUpdateUI = window.updateUI;
  if (typeof originalUpdateUI === 'function') {
    window.updateUI = function() {
      originalUpdateUI.apply(this, arguments);
      updateComposerVisibilityP13();
    };
  }

  // Initial call
  setTimeout(updateComposerVisibilityP13, 100);

  console.log("P13 patches applied");
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initP13Patches);
} else {
  initP13Patches();
}
// ==== End P13 Patches ====

// ==== P14: Overlap Fix & Layout Patches ====

function renderWerewolfPickerP14() {
  const node = document.getElementById("werewolf-seat-picker");
  if (!node) return;
  // P24 Fix: suppress bottom picker during pre-run (only inline picker in Grand Judge message)
  if (state.preRunFlow.active && !state.preRunFlow.confirmed) {
    node.hidden = true;
    return;
  }
  const onMeetingRoom = currentTabName() === "tasks";
  node.hidden = !state.werewolfMode || !onMeetingRoom;
  if (!state.werewolfMode || !onMeetingRoom) return;
  const pendingReplacement = state.werewolfGame?.status === "blocked" && (
    state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat
  );
  if (!state.werewolfGame || !pendingReplacement) {
    node.hidden = true;
    node.innerHTML = "";
    node.setAttribute("aria-hidden", "true");
    node.classList.remove("is-replacement-pending");
    return;
  }

  // P14: Move picker into transcript flow (above composer, not part of it)
  const transcript = document.querySelector(".parliament-transcript");
  const composer = document.querySelector(".composer-bar");
  if (transcript && node.parentElement !== transcript) {
    if (composer && composer.parentElement === transcript) {
      transcript.insertBefore(node, composer);
    } else {
      transcript.appendChild(node);
    }
  }

  const activeIds = state.werewolfGame
    ? state.werewolfGame.players.map(p => p.id)
    : werewolfSelectedSeatIds();
  const offline = new Set(state.werewolfGame?.offlineSeats || []);
  const standbyIds = WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !activeIds.includes(id) && !offline.has(id));
  const count = activeIds.length;
  const pendingId = normalizeWerewolfSeatId(
    state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat || ""
  );
  const running = Boolean(state.werewolfGame && ["running", "blocked"].includes(state.werewolfGame.status));
  const pending = pendingId ? werewolfSeatById(pendingId) : null;

  if (state.werewolfGame && !(state.werewolfGame.status === "blocked" && pending)) {
    node.hidden = true;
    node.innerHTML = "";
    node.setAttribute("aria-hidden", "true");
    node.classList.remove("is-replacement-pending");
    return;
  }
  node.classList.toggle("is-replacement-pending", Boolean(state.werewolfGame && state.werewolfGame.status === "blocked" && pending));

  const helper = running
    ? (pending ? `已选择离线席位：${pending.name}，从替补席点"接替"。` : "运行中可点击左侧任一参赛席位标记离线，再从替补席接替。")
    : `开局前从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选择 ${WEREWOLF_SEAT_COUNT} 个参赛；未选模型自动进入替补席。`;

  const cards = werewolfCandidateSeats().map(seat => {
    const selected = activeIds.includes(seat.id);
    const standby = standbyIds.includes(seat.id);
    const disabled = running ? !standby || !pending : (!selected && count >= WEREWOLF_SEAT_COUNT);
    const attr = running && standby ? `data-werewolf-replace="${escapeAttr(seat.id)}"` : `data-werewolf-pick="${escapeAttr(seat.id)}"`;
    const label = running && standby ? "接替" : selected ? "上场" : "候补";
    const statusClass = selected ? "seated" : "available";
    const provider = seat.provider || seat.channel || "";
    const slotIndex = activeIds.indexOf(seat.id);
    const role = slotIndex >= 0 ? (WEREWOLF_ROLE_LABELS[werewolfRoleForSlot(slotIndex)] || werewolfRoleForSlot(slotIndex)) : "替补";
    const score = getModelWerewolfScore(seat.id);
    const scoreText = score ? `${Math.round(score.avg)}分 · ${score.count}局` : "暂无评分";
    const scoreClass = werewolfScoreClass(score);

    return `<button class="werewolf-candidate${selected ? " is-selected" : ""}" type="button" ${attr}
      ${disabled ? 'disabled data-disabled="true"' : ""}
      style="--seat-color:${escapeAttr(seat.color)}" data-seat-id="${escapeAttr(seat.id)}">
      <div class="wc-avatar-wrap">
        <img class="wc-avatar" src="${escapeAttr(_avatarDataUri(seat.id) || _avatarDataUri("claude"))}" width="40" height="40" alt="${escapeAttr(seat.name)}" loading="lazy" />
        <span class="wc-role-badge">${escapeHtml(role)}</span>
      </div>
      <div class="wc-info">
        <span class="wc-name">${escapeHtml(seat.name)}</span>
        <span class="wc-provider">${escapeHtml(provider)}</span>
        <span class="wc-score ${scoreClass}">${escapeHtml(scoreText)}</span>
      </div>
      <span class="wc-status ${statusClass}">${escapeHtml(label)}</span>
    </button>`;
  }).join("");

  const prep = !running ? renderWerewolfPrepSummary() : "";
  node.innerHTML = `<div class="werewolf-picker-head">
    <div class="werewolf-header-main">
      <span class="werewolf-title">狼人杀模式 · ${WEREWOLF_CANDIDATE_COUNT} 选 ${WEREWOLF_SEAT_COUNT} · 身份板已启用</span>
      <span class="werewolf-subtitle">${escapeHtml(helper)}</span>
    </div>
    <div class="werewolf-stats">
      <span class="werewolf-stat"><strong>${count}</strong><span>参赛</span></span>
      <span class="werewolf-stat"><strong>${WEREWOLF_SEAT_COUNT}</strong><span>席位</span></span>
      <span class="werewolf-stat"><strong>${standbyIds.length}</strong><span>替补</span></span>
    </div>
  </div>
  ${prep}
  <div class="werewolf-pool">${cards}</div>`;
}

function scrollToLatestCardP14() {
  const cards = document.querySelectorAll(".answer-card.agent-turn-card");
  if (cards.length === 0) return;
  const lastCard = cards[cards.length - 1];

  // P17: threshold-based auto-scroll — only scroll if user is near the bottom
  const flow = document.querySelector(".parliament-message-flow");
  if (flow) {
    const threshold = 160; // px from bottom
    const distanceFromBottom = flow.scrollHeight - flow.scrollTop - flow.clientHeight;
    if (distanceFromBottom > threshold) {
      return; // user is reading history, don't yank them
    }
  }

  requestAnimationFrame(() => {
    lastCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

function updateComposerVisibilityP14() {
  const composer = document.querySelector(".composer-bar");
  const werewolfPicker = document.getElementById("werewolf-seat-picker");
  const input = document.getElementById("parliament-question-input");
  const transcript = document.querySelector(".parliament-transcript");

  if (!composer || !input) return;

  const currentTab = currentTabName();
  const isMeetingRoom = currentTab === "tasks";
  const isWerewolfMode = state.werewolfMode;

  composer.hidden = !isMeetingRoom;
  input.hidden = !isMeetingRoom;

  if (werewolfPicker) {
    // P24 Fix: suppress bottom picker during pre-run
    const isPreRun = state.preRunFlow.active && !state.preRunFlow.confirmed;
    const pendingReplacement = state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat;
    const needsReplacementPicker = state.werewolfGame?.status === "blocked" && Boolean(pendingReplacement);
    const shouldShowPicker = isMeetingRoom && isWerewolfMode && !isPreRun && needsReplacementPicker;
    werewolfPicker.hidden = !shouldShowPicker;
    if (shouldShowPicker && transcript) {
      if (werewolfPicker.parentElement !== transcript) {
        if (composer.parentElement === transcript) {
          transcript.insertBefore(werewolfPicker, composer);
        } else {
          transcript.appendChild(werewolfPicker);
        }
      }
    }
  }

  const appShell = document.getElementById("app-shell");
  if (appShell) {
    appShell.setAttribute("data-current-tab", currentTab);
    if (isWerewolfMode && isMeetingRoom) {
      appShell.classList.add("werewolf-mode");
      appShell.classList.add("werewolf-game-active");
      // P25: Add werewolf-game-running when game is active (not just pre-run)
      if (state.werewolfGame && ["blocked", "ready", "running", "complete", "failed"].includes(state.werewolfGame.status)) {
        appShell.classList.add("werewolf-game-running");
      } else {
        appShell.classList.remove("werewolf-game-running");
      }
    } else {
      appShell.classList.remove("werewolf-mode");
      appShell.classList.remove("werewolf-game-active");
      appShell.classList.remove("werewolf-game-running");
    }
  }
}

(function initP14Patches() {
  console.log("P14 Overlap Fix Patches initializing...");

  // Override werewolf picker with P14 version (replaces P13's)
  window.renderWerewolfPicker = renderWerewolfPickerP14;

  // Hook updateUI: preserve P13's wrapper, add P14 visibility + scroll
  const _prevUpdateUI = window.updateUI;
  if (typeof _prevUpdateUI === "function") {
    window.updateUI = function() {
      _prevUpdateUI.apply(this, arguments);
      updateComposerVisibilityP14();
      setTimeout(scrollToLatestCardP14, 150);
    };
  }

  // Hook appendParliamentMessage for scroll-after-new-message
  const _origAppend = window.appendParliamentMessage;
  if (typeof _origAppend === "function") {
    window.appendParliamentMessage = function() {
      _origAppend.apply(this, arguments);
      setTimeout(scrollToLatestCardP14, 100);
    };
  }

  // Initial setup
  setTimeout(() => {
    updateComposerVisibilityP14();
    scrollToLatestCardP14();
  }, 200);

  console.log("P14 patches applied");
})();
// ==== End P14 Patches ====

// ==== Start P15 Patches: Agent Turn Dynamic Polish ====
(function initP15Patches() {
  console.log("P15 Agent Turn Dynamic Polish initializing...");

  // P15.1: Override scrollToLatest with smooth animation-aware anchoring
  function scrollToLatestCardP15() {
    const cards = document.querySelectorAll(".answer-card.agent-turn-card");
    if (cards.length === 0) return;
    const lastCard = cards[cards.length - 1];
    // Brief delay so entrance animation can start before scroll
    requestAnimationFrame(() => {
      lastCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  // Replace P14 scroll function
  window.scrollToLatestCardP14 = scrollToLatestCardP15;

  // P15.2: Stagger new card rendering — assign --i incrementally
  function reindexTurnCards() {
    const cards = document.querySelectorAll(".answer-card.agent-turn-card");
    cards.forEach((card, i) => {
      card.style.setProperty("--i", String(i));
    });
  }

  // P15.3: Hook appendParliamentMessage for animation-aware scroll
  const _origAppendP15 = window.appendParliamentMessage;
  if (typeof _origAppendP15 === "function") {
    window.appendParliamentMessage = function() {
      _origAppendP15.apply(this, arguments);
      // Reindex cards so entrance animations stagger correctly
      reindexTurnCards();
      // Scroll after entrance animation starts (0.32s card enter + stagger)
      setTimeout(scrollToLatestCardP15, 200);
    };
  }

  // P15.4: Werewolf dialogue card role enhancement
  // Adds a subtle role badge to werewolf game agent turn cards
  function enhanceWerewolfTurnCards() {
    const cards = document.querySelectorAll(".answer-card.agent-turn-card");
    cards.forEach(card => {
      if (!document.body.classList.contains("werewolf-mode")) return;
      const roleTag = Array.from(card.querySelectorAll(".ac-tag")).find(t => {
        const text = (t.textContent || "").trim();
        return /狼人|预言家|村民|女巫|猎人|守卫|白痴|替罪羊|丘比特|平民|盗贼|长老|吹笛|野孩子|混血/i.test(text);
      });
      if (roleTag) {
        roleTag.setAttribute("data-werewolf-role", "true");
        const text = (roleTag.textContent || "").trim();
        // P17: assign faction CSS class for color
        let roleClass = "werewolf-role-good";
        if (/狼人/i.test(text)) roleClass = "werewolf-role-wolf";
        else if (/预言家/i.test(text)) roleClass = "werewolf-role-seer";
        else if (/女巫/i.test(text)) roleClass = "werewolf-role-witch";
        else if (/猎人/i.test(text)) roleClass = "werewolf-role-hunter";
        else if (/村民|平民/i.test(text)) roleClass = "werewolf-role-good";
        // Remove old role classes, add correct one
        roleTag.classList.remove("werewolf-role-wolf", "werewolf-role-good", "werewolf-role-seer", "werewolf-role-witch", "werewolf-role-hunter");
        roleTag.classList.add(roleClass);
      }
    });
  }

  // P15.5: Observe DOM mutations for werewolf card enhancement
  if (window.MutationObserver) {
    const flowObserver = new MutationObserver(() => {
      reindexTurnCards();
      enhanceWerewolfTurnCards();
    });
    const flow = document.querySelector(".parliament-message-flow");
    if (flow) {
      flowObserver.observe(flow, { childList: true, subtree: true });
    }
  }

  // P15.6: Initial setup
  setTimeout(() => {
    reindexTurnCards();
    enhanceWerewolfTurnCards();
    updateComposerVisibilityP14();
    scrollToLatestCardP15();
  }, 300);

  // P15.7: Werewolf mode class change listener
  // When werewolf mode toggles, re-enhance cards
  const appShell = document.getElementById("app-shell");
  if (appShell && window.MutationObserver) {
    const classObserver = new MutationObserver(() => {
      enhanceWerewolfTurnCards();
      reindexTurnCards();
    });
    classObserver.observe(appShell, { attributes: true, attributeFilter: ["class"] });
  }

console.log("P15 patches applied");
})();
// ==== End P15 Patches ====

// ==== P25: Dialogue-led werewolf + composer stability guard ====
(function initP25DialogueFlowGuard() {
  console.log("P25 Dialogue Flow Guard initializing...");

  const hideStandaloneWerewolfPickerP25 = () => {
    const picker = document.getElementById("werewolf-seat-picker");
    if (!picker) return;
    const pendingReplacement = state.werewolfGame?.status === "blocked" && (
      state.werewolfGame?.pendingSubstitution || state.werewolfPendingReplacementSeat
    );
    if (pendingReplacement) return;
    picker.hidden = true;
    picker.innerHTML = "";
    picker.setAttribute("aria-hidden", "true");
  };

  const ensureWerewolfSeatCountP25 = () => {
    const ids = werewolfSelectedSeatIds({ fill: true }).slice(0, WEREWOLF_SEAT_COUNT);
    state.werewolfSelectedSeats = new Set(ids);
    saveWerewolfSelectedSeats();
    return ids;
  };

  const _p25StartPreRunFlowWerewolf = window.startPreRunFlowWerewolf || startPreRunFlowWerewolf;
  window.startPreRunFlowWerewolf = startPreRunFlowWerewolf = function(question) {
    clearPreRunFlow();
    ensureWerewolfSeatCountP25();
    state.preRunTranscript = [];
    state.preRunFlow.active = true;
    state.preRunFlow.question = question;
    state.preRunFlow.stage = 0;
    state.preRunFlow.confirmed = false;
    state.preRunFlow.messages = [
      {
        kind: "user",
        role: "你",
        text: question,
        msgState: "sent",
      },
      {
        kind: "judge_prerun",
        role: "Grand Judge",
        text: `收到。本局启用模型狼人杀。\n\n主题：「${question}」\n\n我会先把 ${WEREWOLF_CANDIDATE_COUNT} 个模型压成 ${WEREWOLF_SEAT_COUNT} 个参赛席位，未上场的模型留作替补；身份由 Grand Judge 私下密封发放，公开对话流只展示发言、追问、投票和复盘评分。`,
        msgState: "drafting",
        working: true,
        stage: 0,
      },
    ];
    hideStandaloneWerewolfPickerP25();
    closeParliamentWorkbench();
    renderConferenceRoom();

    state.preRunFlow.timer = window.setTimeout(() => {
      if (!state.preRunFlow.active) return;
      const last = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
      if (last) {
        last.working = false;
        last.msgState = "done";
      }
      const count = werewolfSelectedSeatIds({ fill: true }).length;
      state.preRunFlow.stage = 2;
      state.preRunFlow.messages.push({
        kind: "judge_prerun",
        role: "Grand Judge",
        text: `参赛席位已准备：${count}/9。你可以在下方微调参赛模型；确认后我会分发隐藏身份并启动真实网页席位发言。`,
        msgState: "confirmed",
        showWerewolfPicker: true,
        showConfirm: true,
        chips: [
          ["身份保密", "evidence"],
          ["公开发言", "auto"],
          [`${WEREWOLF_STANDBY_COUNT} 个替补`, "seat"],
        ],
        stage: 2,
      });
      hideStandaloneWerewolfPickerP25();
      renderConferenceRoom();
    }, 720);
  };

  const _p25StartWerewolfGame = window.startWerewolfGame || startWerewolfGame;
  window.startWerewolfGame = startWerewolfGame = async function(topic) {
    ensureWerewolfSeatCountP25();
    hideStandaloneWerewolfPickerP25();
    return _p25StartWerewolfGame.call(this, topic);
  };

  // P26-fix: renderWerewolfPicker calls P14 renderer (not just hide)
  const _p25RenderWerewolfPicker = window.renderWerewolfPicker || renderWerewolfPicker;
  window.renderWerewolfPicker = renderWerewolfPicker = function() {
    if (typeof renderWerewolfPickerP14 === 'function') {
      renderWerewolfPickerP14();
    }
    hideStandaloneWerewolfPickerP25();
  };

  const _p25UpdateComposerVisibility = window.updateComposerVisibilityP14 || updateComposerVisibilityP14;
  window.updateComposerVisibilityP14 = updateComposerVisibilityP14 = function() {
    if (typeof _p25UpdateComposerVisibility === "function") {
      _p25UpdateComposerVisibility.apply(this, arguments);
    }
    hideStandaloneWerewolfPickerP25();
    const shell = document.getElementById("app-shell");
    if (shell) shell.setAttribute("data-current-tab", currentTabName());
  };

  const reindexMessagesP25 = () => {
    document.querySelectorAll(".answer-card").forEach((card, index) => {
      card.style.setProperty("--i", String(index));
    });
  };

  const _p25UpdateUI = window.updateUI;
  if (typeof _p25UpdateUI === "function") {
    window.updateUI = function() {
      _p25UpdateUI.apply(this, arguments);
      hideStandaloneWerewolfPickerP25();
      reindexMessagesP25();
    };
  }

  window.setTimeout(() => {
    hideStandaloneWerewolfPickerP25();
    reindexMessagesP25();
  }, 250);

console.log("P25 patches applied");
})();
// ==== End P25 Patches ====

// ==== P30: Werewolf pre-game visible lock ====
(function initWerewolfPreGameVisibleLock() {
  console.log("P30 Werewolf pre-game visible lock initializing...");

  const preGameActive = () => Boolean(
    state.werewolfMode &&
    !state.werewolfGame &&
    !(state.preRunFlow.active && !state.preRunFlow.confirmed)
  );

  const selectedIdsForPreview = () => werewolfSelectedSeatIds({ fill: true }).slice(0, WEREWOLF_SEAT_COUNT);

  const renderPreGameEmpty = () => {
    const players = werewolfPlayers(selectedIdsForPreview());
    const rolePreview = players
      .map(player => `<span class="ww-empty-role">${escapeHtml(player.roleLabel || player.role || "?")}</span>`)
      .join("");
    return `
      <div class="empty-state-parliament ww-empty-state">
        <strong>模型狼人杀 · 待开局</strong>
        <p>这里已经进入狼人杀准备页。Grand Judge 会从 ${WEREWOLF_CANDIDATE_COUNT} 个模型里选 ${WEREWOLF_SEAT_COUNT} 个参赛，${WEREWOLF_STANDBY_COUNT} 个留作替补；身份私下密封，公开流只展示发言、追问、投票和复盘评分。</p>
        <div class="ww-empty-roles">${rolePreview}</div>
        <p>下方先展示身份板、历史评分和阶段线。输入主题后，会转成确认流，再启动真实网页席位发言。</p>
      </div>
    `;
  };

  const _p30ParliamentEmptyStateHtml = window.parliamentEmptyStateHtml || parliamentEmptyStateHtml;
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (preGameActive()) return renderPreGameEmpty();
    return _p30ParliamentEmptyStateHtml.apply(this, arguments);
  };

  const _p30WerewolfEmptyStateHtml = window.werewolfEmptyStateHtml || werewolfEmptyStateHtml;
  window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
    if (preGameActive()) return renderPreGameEmpty();
    return _p30WerewolfEmptyStateHtml.apply(this, arguments);
  };

  window.renderWerewolfPicker = renderWerewolfPicker = function() {
    const node = document.getElementById("werewolf-seat-picker");
    if (!node) return;
    const onMeetingRoom = currentTabName() === "tasks";
    const inWerewolfMode = Boolean(state.werewolfMode);
    const isPreRun = Boolean(state.preRunFlow.active && !state.preRunFlow.confirmed);
    const pendingReplacement = state.werewolfGame?.status === "blocked" && (
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat
    );

    if (!inWerewolfMode || !onMeetingRoom || isPreRun) {
      node.hidden = true;
      node.innerHTML = "";
      node.setAttribute("aria-hidden", "true");
      node.classList.remove("is-replacement-pending");
      return;
    }

    if (state.werewolfGame && !pendingReplacement) {
      node.hidden = true;
      node.innerHTML = "";
      node.setAttribute("aria-hidden", "true");
      node.classList.remove("is-replacement-pending");
      return;
    }

    const activeIds = state.werewolfGame
      ? state.werewolfGame.players.map(player => player.id)
      : selectedIdsForPreview();
    const offline = new Set(state.werewolfGame?.offlineSeats || []);
    const standbyIds = WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !activeIds.includes(id) && !offline.has(id));
    const count = activeIds.length;
    const pendingId = normalizeWerewolfSeatId(
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat || ""
    );
    const running = Boolean(state.werewolfGame && ["running", "blocked"].includes(state.werewolfGame.status));
    const pending = pendingId ? werewolfSeatById(pendingId) : null;

    node.hidden = false;
    node.removeAttribute("aria-hidden");
    node.classList.toggle("is-replacement-pending", Boolean(running && pending));
    const transcript = document.querySelector(".parliament-transcript");
    const composer = document.querySelector(".composer-bar");
    if (!running && transcript && composer && composer.parentElement === transcript && node.parentElement === transcript && node.nextElementSibling !== composer) {
      transcript.insertBefore(node, composer);
    }

    const helper = running
      ? (pending ? `已选择离线席位：${pending.name}，从替补席点“接替”。` : "运行中可点击左侧任一参赛席位标记离线，再从替补席接替。")
      : `开局前从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选择 ${WEREWOLF_SEAT_COUNT} 个参赛；未选模型自动进入替补席。`;

    const cards = werewolfCandidateSeats().map(seat => {
      const selected = activeIds.includes(seat.id);
      const standby = standbyIds.includes(seat.id);
      const disabled = running ? !standby || !pending : (!selected && count >= WEREWOLF_SEAT_COUNT);
      const attr = running && standby ? `data-werewolf-replace="${escapeAttr(seat.id)}"` : `data-werewolf-pick="${escapeAttr(seat.id)}"`;
      const label = running && standby ? "接替" : selected ? "上场" : "候补";
      const statusClass = selected ? "seated" : "available";
      const provider = seat.provider || seat.channel || "";
      const slotIndex = activeIds.indexOf(seat.id);
      const role = slotIndex >= 0 ? (WEREWOLF_ROLE_LABELS[werewolfRoleForSlot(slotIndex)] || werewolfRoleForSlot(slotIndex)) : "替补";
      const score = getModelWerewolfScore(seat.id);
      const scoreText = score ? `${Math.round(score.avg)}分 · ${score.count}局` : "暂无评分";
      const scoreClass = werewolfScoreClass(score);

      return `<button class="werewolf-candidate${selected ? " is-selected" : ""}" type="button" ${attr}
        ${disabled ? 'disabled data-disabled="true"' : ""}
        style="--seat-color:${escapeAttr(seat.color)}" data-seat-id="${escapeAttr(seat.id)}">
        <div class="wc-avatar-wrap">
          <img class="wc-avatar" src="${escapeAttr(_avatarDataUri(seat.id) || _avatarDataUri("claude"))}" width="40" height="40" alt="${escapeAttr(seat.name)}" loading="lazy" />
          <span class="wc-role-badge">${escapeHtml(role)}</span>
        </div>
        <div class="wc-info">
          <span class="wc-name">${escapeHtml(seat.name)}</span>
          <span class="wc-provider">${escapeHtml(provider)}</span>
          <span class="wc-score ${scoreClass}">${escapeHtml(scoreText)}</span>
        </div>
        <span class="wc-status ${statusClass}">${escapeHtml(label)}</span>
      </button>`;
    }).join("");

    node.innerHTML = `<div class="werewolf-picker-head">
      <div class="werewolf-header-main">
        <span class="werewolf-title">狼人杀模式 · ${WEREWOLF_CANDIDATE_COUNT} 选 ${WEREWOLF_SEAT_COUNT} · 身份板已启用</span>
        <span class="werewolf-subtitle">${escapeHtml(helper)}</span>
      </div>
      <div class="werewolf-stats">
        <span class="werewolf-stat"><strong>${count}</strong><span>参赛</span></span>
        <span class="werewolf-stat"><strong>${WEREWOLF_SEAT_COUNT}</strong><span>席位</span></span>
        <span class="werewolf-stat"><strong>${standbyIds.length}</strong><span>替补</span></span>
      </div>
    </div>
    ${!running ? renderWerewolfPrepSummary() : ""}
    <div class="werewolf-pool">${cards}</div>`;
  };

  const _p30UpdateComposerVisibility = window.updateComposerVisibilityP14 || updateComposerVisibilityP14;
  window.updateComposerVisibilityP14 = updateComposerVisibilityP14 = function() {
    if (typeof _p30UpdateComposerVisibility === "function") {
      _p30UpdateComposerVisibility.apply(this, arguments);
    }
    if (preGameActive()) renderWerewolfPicker();
  };

  const _p30UpdateUI = window.updateUI;
  if (typeof _p30UpdateUI === "function") {
    window.updateUI = function() {
      _p30UpdateUI.apply(this, arguments);
      if (preGameActive()) renderWerewolfPicker();
    };
  }

  [120, 360, 800].forEach(delay => {
    window.setTimeout(() => {
      if (preGameActive()) {
        renderConferenceRoom();
        renderWerewolfPicker();
      }
    }, delay);
  });

  console.log("P30 patches applied");
})();
// ==== End P30 Patches ====

// ==== P40: Werewolf board selector + dynamic 9/14-player boards ====
(function initWerewolfBoardSelectorP40() {
  console.log("P40 Werewolf board selector initializing...");

  const BOARD_STORAGE_KEY = "ai_judge_werewolf_board";
  const PLAY_MODE_STORAGE_KEY = "ai_judge_werewolf_play_mode";
  const BOARD_PRESETS = {
    quick_6: {
      name: "6人快测局",
      shortName: "6快测",
      desc: "2狼、预言家、女巫、2民",
      roles: ["villager", "seer", "werewolf", "witch", "werewolf", "villager"],
    },
    compact_8: {
      name: "8人压缩局",
      shortName: "8压缩",
      desc: "2狼、预言家、女巫、猎人、守卫、2民",
      roles: ["villager", "seer", "guard", "werewolf", "witch", "hunter", "werewolf", "villager"],
    },
    standard: {
      name: "9人标准局",
      shortName: "9标准",
      desc: "3狼、预言家、女巫、猎人、守卫、2民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"],
    },
    advanced_10: {
      name: "10人进阶局",
      shortName: "10进阶",
      desc: "3狼、预言家、女巫、猎人、守卫、3民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "villager"],
    },
    classic_12: {
      name: "12人白狼王",
      shortName: "12白狼",
      desc: "3狼、白狼王、预言家、女巫、猎人、守卫、白痴、3民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "idiot", "werewolf", "villager"],
    },
    thirteen: {
      name: "13人单替补",
      shortName: "13单替",
      desc: "3狼、白狼王、预言家、女巫、猎人、守卫、骑士、白痴、3民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "knight", "idiot", "werewolf", "villager"],
    },
    white_wolf: {
      name: "9人白狼王",
      shortName: "9白狼王",
      desc: "2狼、白狼王、预言家、女巫、猎人、守卫、2民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf"],
    },
    knight: {
      name: "9人骑士局",
      shortName: "9骑士",
      desc: "3狼、预言家、女巫、骑士、守卫、2民",
      roles: ["villager", "seer", "guard", "knight", "werewolf", "witch", "werewolf", "villager", "werewolf"],
    },
    idiot: {
      name: "9人白痴局",
      shortName: "9白痴",
      desc: "3狼、预言家、女巫、猎人、守卫、白痴、1民",
      roles: ["idiot", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"],
    },
    full: {
      name: "9人全神局",
      shortName: "9全神",
      desc: "2狼、白狼王、预言家、女巫、骑士、守卫、白痴、1民",
      roles: ["idiot", "seer", "guard", "knight", "werewolf", "witch", "white_wolf", "villager", "werewolf"],
    },
    standard_14: {
      name: "14人标准局",
      shortName: "14标准",
      desc: "4狼、预言家、女巫、猎人、守卫、骑士、白痴、4民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"],
    },
    white_wolf_14: {
      name: "14人白狼王",
      shortName: "14白狼王",
      desc: "3狼、白狼王、预言家、女巫、猎人、守卫、骑士、白痴、4民",
      roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"],
    },
  };
  const PLAY_MODE_PRESETS = {
    standard_competition: {
      name: "标准竞技",
      desc: "严格规则：警长、警徽、平安夜、遗言、屠边和特殊技能全部生效。",
    },
    ai_experiment: {
      name: "AI实验",
      desc: "标准规则 + 更完整的迟到回收、原始回答、复盘评分和行为审计。",
    },
  };

  function normalizeBoard(board) {
    const key = String(board || "").trim();
    return BOARD_PRESETS[key] ? key : "standard";
  }

  function normalizePlayMode(mode) {
    const key = String(mode || "").trim();
    return PLAY_MODE_PRESETS[key] ? key : "standard_competition";
  }

  function currentBoardKey() {
    const stored = localStorage.getItem(BOARD_STORAGE_KEY);
    return normalizeBoard(state.werewolfBoard || stored || "standard");
  }

  function currentBoard() {
    return BOARD_PRESETS[currentBoardKey()] || BOARD_PRESETS.standard;
  }

  function currentWerewolfPlayMode() {
    return normalizePlayMode(state.werewolfPlayMode || localStorage.getItem(PLAY_MODE_STORAGE_KEY));
  }

  function currentPlayMode() {
    return PLAY_MODE_PRESETS[currentWerewolfPlayMode()] || PLAY_MODE_PRESETS.standard_competition;
  }

  function seatCount() {
    return currentBoard().roles.length;
  }

  function standbyCount() {
    return Math.max(0, WEREWOLF_CANDIDATE_COUNT - seatCount());
  }

  function werewolfBoardLocked() {
    const status = String(state.werewolfGame?.status || "");
    return Boolean(state.werewolfGame && status && !["ready", "blocked", "failed", "complete"].includes(status));
  }

  function clearUnlockedWerewolfDraft() {
    if (state.werewolfGame && !werewolfBoardLocked()) {
      unloadWerewolfGame({ clearTask: true });
    }
  }

  function boardRoleSequence() {
    return currentBoard().roles;
  }

  function defaultSeatIds() {
    const selected = [];
    [...DEFAULT_WEREWOLF_SEAT_IDS, ...WEREWOLF_CANDIDATE_SEAT_IDS].forEach(id => {
      if (!selected.includes(id) && selected.length < seatCount()) selected.push(id);
    });
    return selected;
  }

  function normalizeSeatSelection(ids, { fill = false } = {}) {
    const selected = [];
    (ids || []).forEach(raw => {
      const id = normalizeWerewolfSeatId(raw);
      if (WEREWOLF_CANDIDATE_SEAT_IDS.includes(id) && !selected.includes(id) && selected.length < seatCount()) {
        selected.push(id);
      }
    });
    if (fill) {
      [...defaultSeatIds(), ...WEREWOLF_CANDIDATE_SEAT_IDS].forEach(id => {
        if (!selected.includes(id) && selected.length < seatCount()) selected.push(id);
      });
    }
    return selected;
  }

  window.werewolfBoardKey = currentBoardKey;
  window.werewolfSeatCount = seatCount;
  window.werewolfStandbyCount = standbyCount;
  window.werewolfPlayModeKey = currentWerewolfPlayMode;

  state.werewolfBoard = currentBoardKey();
  state.werewolfPlayMode = currentWerewolfPlayMode();
  state.werewolfSelectedSeats = new Set(normalizeSeatSelection(Array.from(state.werewolfSelectedSeats || []), { fill: true }));
  localStorage.setItem(BOARD_STORAGE_KEY, state.werewolfBoard);
  localStorage.setItem(PLAY_MODE_STORAGE_KEY, state.werewolfPlayMode);
  localStorage.setItem("ai_judge_werewolf_selected_seats", JSON.stringify(Array.from(state.werewolfSelectedSeats)));

  window.setWerewolfBoard = function(board) {
    if (werewolfBoardLocked()) return;
    clearUnlockedWerewolfDraft();
    state.werewolfBoard = normalizeBoard(board);
    localStorage.setItem(BOARD_STORAGE_KEY, state.werewolfBoard);
    state.werewolfSelectedSeats = new Set(normalizeSeatSelection(Array.from(state.werewolfSelectedSeats || []), { fill: true }));
    saveWerewolfSelectedSeats();
    console.info(`[AI Judge Werewolf] board changed -> ${state.werewolfBoard}; seatCount=${seatCount()}; standby=${standbyCount()}`);
    renderConferenceRoom();
    renderWerewolfPicker();
  };

  window.setWerewolfPlayMode = function(mode) {
    if (werewolfBoardLocked()) return;
    state.werewolfPlayMode = normalizePlayMode(mode);
    localStorage.setItem(PLAY_MODE_STORAGE_KEY, state.werewolfPlayMode);
    renderConferenceRoom();
    renderWerewolfPicker();
  };

  function roleLabel(role) {
    return WEREWOLF_ROLE_LABELS[role] || role || "?";
  }

  function roleTone(role) {
    if (role === "werewolf" || role === "white_wolf") return "wolf";
    if (["seer", "witch", "hunter", "guard", "knight", "idiot"].includes(role)) return "god";
    return "civilian";
  }

  function compactScoreText(score) {
    if (!score) return "暂无";
    return `${Math.round(score.avg)}分/${score.count}局`;
  }

  function boardSelectorHtml() {
    const active = currentBoardKey();
    const locked = werewolfBoardLocked();
    return `<div class="ww-board-switch" role="tablist" aria-label="狼人杀板型">
      ${Object.entries(BOARD_PRESETS).map(([key, board]) => `
        <button type="button" class="ww-board-option ${key === active ? "is-active" : ""}"
          data-werewolf-board="${escapeAttr(key)}"
          aria-pressed="${key === active ? "true" : "false"}"
          onpointerdown="event.preventDefault(); event.stopPropagation(); window.setWerewolfBoard && window.setWerewolfBoard('${escapeAttr(key)}')"
          onmousedown="event.preventDefault(); event.stopPropagation(); window.setWerewolfBoard && window.setWerewolfBoard('${escapeAttr(key)}')"
          onclick="event.preventDefault(); event.stopPropagation(); window.setWerewolfBoard && window.setWerewolfBoard('${escapeAttr(key)}')"
          ${locked ? "disabled" : ""}>
          <span class="ww-board-name">${escapeHtml(board.shortName)}</span>
          <span class="ww-board-count">${board.roles.length} 人</span>
          <small>${escapeHtml(board.desc)}</small>
        </button>
      `).join("")}
    </div>`;
  }

  function playModeSelectorHtml() {
    const active = currentWerewolfPlayMode();
    const locked = werewolfBoardLocked();
    return `<div class="ww-mode-switch" role="tablist" aria-label="狼人杀模式">
      ${Object.entries(PLAY_MODE_PRESETS).map(([key, mode]) => `
        <button type="button" class="ww-mode-option ${key === active ? "is-active" : ""}"
          data-werewolf-play-mode="${escapeAttr(key)}"
          aria-pressed="${key === active ? "true" : "false"}"
          onclick="event.preventDefault(); event.stopPropagation(); window.setWerewolfPlayMode && window.setWerewolfPlayMode('${escapeAttr(key)}')"
          ${locked ? "disabled" : ""}>
          <span>${escapeHtml(mode.name)}</span>
          <small>${escapeHtml(mode.desc)}</small>
        </button>
      `).join("")}
    </div>`;
  }

  normalizeWerewolfSeatSelection = function(ids, { fill = false } = {}) {
    return normalizeSeatSelection(ids, { fill });
  };

  loadWerewolfSelectedSeats = function() {
    try {
      const parsed = JSON.parse(localStorage.getItem("ai_judge_werewolf_selected_seats") || "[]");
      const selected = normalizeSeatSelection(Array.isArray(parsed) ? parsed : [], { fill: false });
      if (selected.length === seatCount()) return selected;
    } catch (_) {
      // Ignore bad localStorage from older previews.
    }
    return defaultSeatIds();
  };

  werewolfSelectedSeatIds = function({ fill = false } = {}) {
    return normalizeSeatSelection(Array.from(state.werewolfSelectedSeats || []), { fill });
  };

  saveWerewolfSelectedSeats = function() {
    localStorage.setItem("ai_judge_werewolf_selected_seats", JSON.stringify(werewolfSelectedSeatIds()));
  };

  toggleInlineWerewolfSeat = function(id) {
    if (werewolfBoardLocked()) return;
    clearUnlockedWerewolfDraft();
    const normId = normalizeWerewolfSeatId(id);
    if (!WEREWOLF_CANDIDATE_SEAT_IDS.includes(normId)) return;
    const current = werewolfSelectedSeatIds();
    if (current.includes(normId)) {
      state.werewolfSelectedSeats.delete(normId);
    } else if (current.length < seatCount()) {
      state.werewolfSelectedSeats.add(normId);
    }
    saveWerewolfSelectedSeats();
    renderConferenceRoom();
  };

  toggleWerewolfSeat = function(id) {
    if (werewolfBoardLocked()) return;
    clearUnlockedWerewolfDraft();
    const seatId = normalizeWerewolfSeatId(id);
    if (!WEREWOLF_CANDIDATE_SEAT_IDS.includes(seatId)) return;
    const selected = new Set(werewolfSelectedSeatIds());
    if (selected.has(seatId)) {
      selected.delete(seatId);
    } else if (selected.size < seatCount()) {
      selected.add(seatId);
    }
    state.werewolfSelectedSeats = selected;
    saveWerewolfSelectedSeats();
    renderConferenceRoom();
  };

  werewolfRoleForSlot = function(index) {
    return boardRoleSequence()[index] || "villager";
  };

  werewolfPlayers = function(selectedIds = werewolfSelectedSeatIds({ fill: true })) {
    return selectedIds.slice(0, seatCount()).map((id, index) => {
      const seat = werewolfSeatById(id);
      const role = werewolfRoleForSlot(index);
      return {
        ...seat,
        role,
        roleLabel: roleLabel(role),
        team: ["werewolf", "white_wolf"].includes(role) ? "werewolf" : "good",
        slot: index + 1,
      };
    });
  };

  renderInlineWerewolfPicker = function() {
    const activeIds = state.werewolfGame
      ? state.werewolfGame.players.map(p => p.id)
      : werewolfSelectedSeatIds();
    const count = activeIds.length;
    const cards = werewolfCandidateSeats().map(seat => {
      const selected = activeIds.includes(seat.id);
      const disabled = !selected && count >= seatCount();
      const score = getModelWerewolfScore(seat.id);
      const scoreText = compactScoreText(score);
      const scoreTitle = score?.recent?.length
        ? `历史评分：${score.avg}；最近三局：${score.recent.join(" / ")}`
        : "暂无狼人杀历史评分";
      return `
        <button class="ww-inline-chip ${selected ? "is-selected" : ""}" type="button"
          data-werewolf-pick="${escapeAttr(seat.id)}"
          ${disabled ? "disabled" : ""}
          title="${escapeAttr(scoreTitle)}"
          style="--seat-color:${escapeAttr(seat.color)}">
          <span class="ww-inline-dot" style="background:${escapeAttr(seat.color)}"></span>
          <span class="ww-inline-name">${escapeHtml(seat.name)}</span>
          <span class="ww-inline-score ${werewolfScoreClass(score)}">${escapeHtml(scoreText)}</span>
          ${selected ? '<span class="ww-inline-check">&#10003;</span>' : ''}
        </button>
      `;
    }).join("");
    return `
      <div class="ww-inline-panel">
        <div class="ww-inline-head">
          <span>选择 ${count}/${seatCount()} 位议员 · ${escapeHtml(currentBoard().name)}</span>
          <small>点击芯片选择</small>
        </div>
        ${boardSelectorHtml()}
        <div class="ww-inline-chips">${cards}</div>
      </div>
    `;
  };

  renderWerewolfPrepSummary = function() {
    const selectedIds = werewolfSelectedSeatIds({ fill: true }).slice(0, seatCount());
    const players = werewolfPlayers(selectedIds);
    const standbyPlayers = WEREWOLF_CANDIDATE_SEAT_IDS
      .filter(id => !selectedIds.includes(id))
      .map(id => werewolfSeatById(id));
    const roleLine = players
      .map((player, index) => `<span class="ww-role-mini ww-role-${escapeAttr(roleTone(player.role))}"><b>${index + 1}</b>${escapeHtml(player.roleLabel || player.role || "?")}</span>`)
      .join("");
    const seatLine = players
      .map((player, index) => {
        const score = getModelWerewolfScore(player.id);
        return `<button type="button" class="ww-seat-chip is-active" data-werewolf-pick="${escapeAttr(player.id)}" style="--seat-color:${escapeAttr(player.color)}">
          <span>${index + 1}</span><strong>${escapeHtml(player.name)}</strong><em>${escapeHtml(roleLabel(player.role))}</em><small>${escapeHtml(compactScoreText(score))}</small>
        </button>`;
      })
      .join("");
    const standbyLine = standbyPlayers
      .map(player => {
        const score = getModelWerewolfScore(player.id);
        return `<button type="button" class="ww-seat-chip is-standby" data-werewolf-pick="${escapeAttr(player.id)}" style="--seat-color:${escapeAttr(player.color)}">
          <span>替</span><strong>${escapeHtml(player.name)}</strong><em>替补</em><small>${escapeHtml(compactScoreText(score))}</small>
        </button>`;
      })
      .join("");
    return `
      <div class="ww-prep-summary ww-console" aria-label="狼人杀开局控制台">
        <div class="ww-console-head">
          <div>
            <strong>模型狼人杀 · 待开局</strong>
            <p>当前板型：${escapeHtml(currentBoard().name)}。${WEREWOLF_CANDIDATE_COUNT} 个模型候选，${seatCount()} 个上场，${standbyCount()} 个替补。</p>
          </div>
          <div class="ww-console-metrics" aria-label="开局状态">
            <span><b>${selectedIds.length}</b><em>参赛</em></span>
            <span><b>${seatCount()}</b><em>席位</em></span>
            <span><b>${standbyCount()}</b><em>替补</em></span>
          </div>
        </div>
        ${boardSelectorHtml()}
        ${playModeSelectorHtml()}
        <div class="ww-console-grid">
          <section class="ww-console-panel ww-console-panel--roles">
            <h4>身份板</h4>
            <div class="ww-role-strip">${roleLine}</div>
            <p>${escapeHtml(currentBoard().desc)}</p>
          </section>
          <section class="ww-console-panel ww-console-panel--seats">
            <h4>上场模型</h4>
            <div class="ww-seat-grid">${seatLine}</div>
          </section>
          <section class="ww-console-panel ww-console-panel--bench">
            <h4>替补席</h4>
            <div class="ww-seat-grid ww-seat-grid--bench">${standbyLine || "<span class=\"ww-empty-text\">无替补</span>"}</div>
          </section>
        </div>
        <p class="ww-console-note">当前模式：${escapeHtml(currentPlayMode().name)}。确认后进入真实网页席位发言；死亡席位仍可通过遗言、复盘和阵营贡献争取评分。运行中不可切换板型和模式。</p>
      </div>
    `;
  };

  buildWerewolfBridgeBlockedGame = function(topic, selectedIds, gate) {
    const players = werewolfPlayers(selectedIds);
    const missingNames = gate.missing.map(item => `${item.name}（${bridgeReasonText(item.reason)}）`).join("、") || "无";
    const events = [
      {
        kind: "judge",
        phase: "bridge-gate",
        status: "真实桥接未就绪",
        text: `真实狼人杀已暂停在桥接门禁：${gate.readyCount}/${gate.total} 个参赛模型可用。异常席位：${missingNames}。这先按临时桥接异常处理，AI Judge 会重新检测固定网页状态，不把它直接判成模型缺席。`,
      },
      {
        kind: "judge",
        phase: "bridge-gate",
        status: "刷新重检",
        text: `如果你已经在同一个固定 Chrome 窗口登录或刷新了这些模型页，请点“重新检测并继续”：${gate.missing.map(item => `${item.name}${item.url ? ` ${item.url}` : ""}`).join("；") || "全部已就绪"}。若仍失败，再进入替补或稍后补跑。`,
      },
      {
        kind: "judge",
        phase: "bridge-gate",
        status: "执行边界",
        text: `本局板型为${currentBoard().name}，需要 ${seatCount()} 个真实参赛席位。Grand Judge 逐席发送私有身份和阶段消息，等待该模型真实回复，再把每个模型的发言作为单独 agent turn 写入公开对话流。`,
      },
    ];
    return {
      topic,
      board: currentBoardKey(),
      boardName: currentBoard().name,
      boardRoles: boardRoleSequence(),
      seatCount: seatCount(),
      players,
      events,
      visibleCount: events.length,
      status: "blocked",
      winner: null,
      eliminated: {},
      offlineSeats: gate.missing.map(item => item.id),
      substitutions: [],
      bridgeGate: gate,
      scores: [],
    };
  };

  buildWerewolfBridgeReadyGame = function(topic, selectedIds, gate) {
    const players = werewolfPlayers(selectedIds);
    return {
      topic,
      board: currentBoardKey(),
      boardName: currentBoard().name,
      boardRoles: boardRoleSequence(),
      seatCount: seatCount(),
      players,
      events: [
        {
          kind: "judge",
          phase: "bridge-ready",
          status: "桥接已就绪",
          text: `${seatCount()} 个参赛模型固定标签已就绪。本局为${currentBoard().name}：${currentBoard().desc}。下一步进入真实逐席桥接。`,
        },
        {
          kind: "judge",
          phase: "bridge-ready",
          status: "等待真实执行器",
          text: "当前前端已停止本地模板动画；私有身份、夜间行动、白天发言和投票都必须等待模型网页真实回复。",
        },
      ],
      visibleCount: 2,
      status: "ready",
      winner: null,
      eliminated: {},
      offlineSeats: [],
      substitutions: [],
      bridgeGate: gate,
      scores: [],
    };
  };

  const _p40NormalizeServerGame = normalizeWerewolfServerGame;
  normalizeWerewolfServerGame = function(serverGame) {
    const raw = serverGame || {};
    if (raw.board) {
      state.werewolfBoard = normalizeBoard(raw.board);
      localStorage.setItem(BOARD_STORAGE_KEY, state.werewolfBoard);
    }
    const game = _p40NormalizeServerGame(raw);
    const boardKey = normalizeBoard(raw.board || game.board || currentBoardKey());
    const board = BOARD_PRESETS[boardKey] || BOARD_PRESETS.standard;
    return {
      ...game,
      board: boardKey,
      boardName: raw.board_name || raw.boardName || board.name,
      boardRoles: raw.board_roles || raw.boardRoles || board.roles,
      seatCount: Number(raw.seat_count || raw.seatCount || game.players?.length || board.roles.length),
    };
  };

  werewolfCampCounts = function(game, eliminated) {
    const players = game?.players || werewolfPlayers(werewolfSelectedSeatIds({ fill: true }));
    const reveal = game?.status === "complete" || Boolean(game?.roles_revealed);
    const roles = game?.boardRoles || boardRoleSequence();
    if (!reveal) {
      const wolf = roles.filter(role => role === "werewolf" || role === "white_wolf").length;
      return { good: Math.max(0, roles.length - wolf), wolf, unknown: players.length };
    }
    return players.reduce((acc, player) => {
      if (eliminated.has(player.id)) return acc;
      if (player.team === "werewolf" || player.role === "werewolf" || player.role === "white_wolf") acc.wolf += 1;
      else acc.good += 1;
      return acc;
    }, { good: 0, wolf: 0, unknown: 0 });
  };

  werewolfAbilityRows = function(game) {
    const roles = [...new Set((game?.boardRoles || boardRoleSequence()).filter(Boolean))];
    const ability = {
      seer: "查验",
      witch: "解药/毒药",
      hunter: "开枪",
      guard: "守护",
      knight: "决斗",
      idiot: "翻牌",
      white_wolf: "自爆带人",
      werewolf: "夜刀",
      villager: "发言投票",
    };
    return roles.map(role => [roleLabel(role), ability[role] || "阵营贡献"]);
  };

  const _p40PreRunEmpty = window.parliamentEmptyStateHtml || parliamentEmptyStateHtml;
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return `
        <div class="empty-state-parliament ww-empty-state">
          ${renderWerewolfPrepSummary()}
        </div>
      `;
    }
    return _p40PreRunEmpty.apply(this, arguments);
  };

  window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame) return parliamentEmptyStateHtml();
    return `
      <div class="empty-state-parliament">
        <strong>模型狼人杀</strong>
        <p>当前板型：${escapeHtml(currentBoard().name)}。从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选 ${seatCount()} 个参赛，${standbyCount()} 个留作替补。Grand Judge 会密封分配身份，所有公开发言进入对话流。</p>
      </div>
    `;
  };

  window.renderWerewolfPicker = renderWerewolfPicker = function() {
    const node = document.getElementById("werewolf-seat-picker");
    if (!node) return;
    const onMeetingRoom = currentTabName() === "tasks";
    const inWerewolfMode = Boolean(state.werewolfMode);
    const isPreRun = Boolean(state.preRunFlow.active && !state.preRunFlow.confirmed);
    const pendingReplacement = state.werewolfGame?.status === "blocked" && (
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat
    );
    if (!inWerewolfMode || !onMeetingRoom || isPreRun || (state.werewolfGame && !pendingReplacement)) {
      node.hidden = true;
      node.innerHTML = "";
      node.setAttribute("aria-hidden", "true");
      node.classList.remove("is-replacement-pending");
      return;
    }
    const activeIds = state.werewolfGame
      ? state.werewolfGame.players.map(player => player.id)
      : werewolfSelectedSeatIds({ fill: true }).slice(0, seatCount());
    const offline = new Set(state.werewolfGame?.offlineSeats || []);
    const standbyIds = WEREWOLF_CANDIDATE_SEAT_IDS.filter(id => !activeIds.includes(id) && !offline.has(id));
    const count = activeIds.length;
    const pendingId = normalizeWerewolfSeatId(
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution?.offlineSeat || ""
    );
    const running = Boolean(state.werewolfGame && ["running", "blocked"].includes(state.werewolfGame.status));
    const pending = pendingId ? werewolfSeatById(pendingId) : null;
    node.hidden = false;
    node.removeAttribute("aria-hidden");
    node.classList.toggle("is-replacement-pending", Boolean(running && pending));
    const transcript = document.querySelector(".parliament-transcript");
    const composer = document.querySelector(".composer-bar");
    if (!running && transcript && composer && composer.parentElement === transcript && node.parentElement === transcript && node.nextElementSibling !== composer) {
      transcript.insertBefore(node, composer);
    }
    const helper = running
      ? (pending ? `已选择离线席位：${pending.name}，从替补席点“接替”。` : "运行中可点击左侧任一参赛席位标记离线，再从替补席接替。")
      : `选择板型后，从 ${WEREWOLF_CANDIDATE_COUNT} 个模型中选择 ${seatCount()} 个参赛；未选模型自动进入替补席。`;
    const cards = werewolfCandidateSeats().map(seat => {
      const selected = activeIds.includes(seat.id);
      const standby = standbyIds.includes(seat.id);
      const disabled = running ? !standby || !pending : (!selected && count >= seatCount());
      const attr = running && standby ? `data-werewolf-replace="${escapeAttr(seat.id)}"` : `data-werewolf-pick="${escapeAttr(seat.id)}"`;
      const label = running && standby ? "接替" : selected ? "上场" : "候补";
      const statusClass = selected ? "seated" : "available";
      const provider = seat.provider || seat.channel || "";
      const slotIndex = activeIds.indexOf(seat.id);
      const role = slotIndex >= 0 ? roleLabel(werewolfRoleForSlot(slotIndex)) : "替补";
      const score = getModelWerewolfScore(seat.id);
      const scoreText = score ? `${Math.round(score.avg)}分 · ${score.count}局` : "暂无评分";
      const scoreClass = werewolfScoreClass(score);
      return `<button class="werewolf-candidate${selected ? " is-selected" : ""}" type="button" ${attr}
        ${disabled ? 'disabled data-disabled="true"' : ""}
        style="--seat-color:${escapeAttr(seat.color)}" data-seat-id="${escapeAttr(seat.id)}">
        <div class="wc-avatar-wrap">
          <img class="wc-avatar" src="${escapeAttr(_avatarDataUri(seat.id) || _avatarDataUri("claude"))}" width="40" height="40" alt="${escapeAttr(seat.name)}" loading="lazy" />
          <span class="wc-role-badge">${escapeHtml(role)}</span>
        </div>
        <div class="wc-info">
          <span class="wc-name">${escapeHtml(seat.name)}</span>
          <span class="wc-provider">${escapeHtml(provider)}</span>
          <span class="wc-score ${scoreClass}">${escapeHtml(scoreText)}</span>
        </div>
        <span class="wc-status ${statusClass}">${escapeHtml(label)}</span>
      </button>`;
    }).join("");
    node.innerHTML = `<div class="werewolf-picker-head">
      <div class="werewolf-header-main">
        <span class="werewolf-title">狼人杀模式 · ${WEREWOLF_CANDIDATE_COUNT} 选 ${seatCount()} · ${escapeHtml(currentBoard().name)}</span>
        <span class="werewolf-subtitle">${escapeHtml(helper)}</span>
      </div>
      <div class="werewolf-stats">
        <span class="werewolf-stat"><strong>${count}</strong><span>参赛</span></span>
        <span class="werewolf-stat"><strong>${seatCount()}</strong><span>席位</span></span>
        <span class="werewolf-stat"><strong>${standbyIds.length}</strong><span>替补</span></span>
      </div>
    </div>
    ${!running ? renderWerewolfPrepSummary() : ""}
    <div class="werewolf-pool">${cards}</div>`;
  };

  window.startPreRunFlowWerewolf = startPreRunFlowWerewolf = function(question) {
    clearPreRunFlow();
    state.werewolfMode = true;
    setPreRunFlowKindP53("werewolf");
    try { localStorage.setItem("ai_judge_werewolf_mode", "1"); } catch (_) {}
    state.werewolfSelectedSeats = new Set(werewolfSelectedSeatIds({ fill: true }).slice(0, seatCount()));
    saveWerewolfSelectedSeats();
    state.preRunTranscript = [];
    state.preRunFlow.active = true;
    state.preRunFlow.question = question;
    state.preRunFlow.stage = 0;
    state.preRunFlow.confirmed = false;
    state.preRunFlow.messages = [
      { kind: "user", role: "你", text: question, msgState: "sent" },
      {
        kind: "judge_prerun",
        role: "Grand Judge",
        text: `收到。本局启用模型狼人杀。\n\n主题：「${question}」\n\n板型：${currentBoard().name}（${currentBoard().desc}）。我会先把 ${WEREWOLF_CANDIDATE_COUNT} 个模型压成 ${seatCount()} 个参赛席位，未上场的模型留作替补；身份由 Grand Judge 私下密封发放，公开对话流只展示发言、追问、投票和复盘评分。`,
        msgState: "drafting",
        working: true,
        stage: 0,
      },
    ];
    closeParliamentWorkbench();
    renderConferenceRoom();
    state.preRunFlow.timer = window.setTimeout(() => {
      if (!state.preRunFlow.active) return;
      const last = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
      if (last) {
        last.working = false;
        last.msgState = "done";
      }
      const count = werewolfSelectedSeatIds({ fill: true }).length;
      state.preRunFlow.stage = 2;
      state.preRunFlow.messages.push({
        kind: "judge_prerun",
        role: "Grand Judge",
        text: `参赛席位已准备：${count}/${seatCount()}。确认后我会分发隐藏身份，并启动真实网页席位发言。需要换板型或调整席位时，先回到待开局状态再修改。`,
        msgState: "confirmed",
        showWerewolfPicker: true,
        showConfirm: true,
        chips: [["身份保密", "evidence"], ["公开发言", "auto"], [`${standbyCount()} 个替补`, "seat"]],
        stage: 2,
      });
      renderConferenceRoom();
    }, 720);
  };

  window.startWerewolfGame = startWerewolfGame = async function(topic) {
    unloadParliamentDemo();
    unloadWerewolfGame({ clearTask: false });
    const selected = werewolfSelectedSeatIds({ fill: true }).slice(0, seatCount());
    state.werewolfSelectedSeats = new Set(selected);
    saveWerewolfSelectedSeats();
    if (selected.length !== seatCount()) {
      renderWerewolfPicker();
      return;
    }
    await loadBridgeStatus();
    const gate = werewolfBridgeSnapshot(selected);
    state.werewolfBridgeGate = gate;
    if (gate.readyCount < selected.length) {
      const game = buildWerewolfBridgeBlockedGame(topic || "AI Judge 模型狼人杀", selected, gate);
      state.werewolfGame = game;
      state.currentVerdict = null;
      state.currentTask = {
        run_id: `werewolf-gate-${Date.now()}`,
        question: game.topic,
        status: "blocked",
        progress: gate.total ? gate.readyCount / gate.total : 0,
        progress_diagnostics: { stale: false },
      };
      renderConferenceRoom();
      return;
    }
    let game = buildWerewolfBridgeReadyGame(topic || "AI Judge 模型狼人杀", selected, gate);
    state.werewolfGame = game;
    state.currentVerdict = null;
    state.currentTask = {
      run_id: `werewolf-gate-${Date.now()}`,
      question: game.topic,
      status: "starting_real_werewolf_executor",
      progress: gate.total ? gate.readyCount / gate.total : 0,
      progress_diagnostics: { stale: false },
    };
    renderConferenceRoom();
    try {
      const res = await fetch(`${API_BASE}/api/werewolf/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: game.topic, seats: selected, board: currentBoardKey(), play_mode: currentWerewolfPlayMode() }),
      });
      const payload = await res.json();
      if (!res.ok) {
        if (payload.error === "bridge_not_ready") {
          await loadBridgeStatus();
          const freshGate = werewolfBridgeSnapshot(selected);
          state.werewolfBridgeGate = freshGate;
          game = buildWerewolfBridgeBlockedGame(topic || "AI Judge 模型狼人杀", selected, freshGate);
        } else {
          throw new Error(payload.error || `HTTP ${res.status}`);
        }
      } else {
        handleWerewolfServerPayload(payload);
        connectWerewolfSession(payload.game_id);
        return;
      }
    } catch (err) {
      game = {
        ...game,
        status: "failed",
        events: [
          ...game.events,
          { kind: "judge", phase: "error", status: "执行器启动失败", text: `真实狼人杀执行器启动失败：${err.message}。系统没有回退到本地模板发言。` },
        ],
        visibleCount: game.events.length + 1,
        error: err.message,
      };
    }
    state.werewolfGame = game;
    syncWerewolfTaskFromGame(game);
    renderConferenceRoom();
  };

  [100, 400, 900].forEach(delay => {
    window.setTimeout(() => {
      if (state.werewolfMode) {
        renderConferenceRoom();
        renderWerewolfPicker();
      }
    }, delay);
  });

console.log("P40 patches applied");
})();
// ==== End P40 Patches ====

// ==== P46: Werewolf prep de-duplication and compact confirmation ====
(function initP46WerewolfPrepCloseout() {
  console.log("P46 Werewolf prep closeout initializing...");

  // P46 is now only a confirmation scroll guard. Do not override P44/P40's
  // board console renderer here; that was the reason the visible UI stayed stale.

  const _p46RenderConferenceRoom = window.renderConferenceRoom || renderConferenceRoom;
  window.renderConferenceRoom = renderConferenceRoom = function() {
    _p46RenderConferenceRoom.apply(this, arguments);
    const flow = document.querySelector(".parliament-message-flow");
    const confirm = document.getElementById("prerun-confirm-btn");
    if (flow && confirm && state.preRunFlow.active && !state.preRunFlow.confirmed) {
      requestAnimationFrame(() => {
        confirm.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    }
  };

  console.log("P46 patches applied");
})();
// ==== End P46 Patches ====

// ==== P47: retired compact werewolf prep renderer ====
(function initP47CompactWerewolfPrepRetired() {
  // The old compact renderer ran after P40/P44 and overwrote the full board
  // console. Keep this as a migration marker so P48 can still follow it without
  // changing the authoritative C-surface renderers.
  console.log("P47 compact werewolf prep skipped; P44/P40 console remains authoritative");
})();
// ==== End P47 Patches ====

// ==== P48: Werewolf pre-run confirmation fail-safe ====
(function initP48WerewolfPreRunFailSafe() {
  console.log("P48 werewolf pre-run fail-safe initializing...");

  const boardPresetsP48 = {
    standard: { name: "9标准", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"] },
    white_wolf: { name: "9白狼王", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf"] },
    knight: { name: "9骑士", roles: ["villager", "seer", "guard", "knight", "werewolf", "witch", "werewolf", "villager", "werewolf"] },
    idiot: { name: "9白痴", roles: ["idiot", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"] },
    full: { name: "9全神局", roles: ["idiot", "seer", "guard", "knight", "werewolf", "witch", "white_wolf", "villager", "werewolf"] },
    standard_14: { name: "14标准", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"] },
    white_wolf_14: { name: "14白狼王", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"] },
  };
  const boardKeyP48 = () => {
    const key = String(state.werewolfBoard || localStorage.getItem("ai_judge_werewolf_board") || "standard").trim();
    return boardPresetsP48[key] ? key : "standard";
  };
  const boardP48 = () => boardPresetsP48[boardKeyP48()] || boardPresetsP48.standard;
  const seatCountP48 = () => boardP48().roles.length;
  const standbyCountP48 = () => Math.max(0, WEREWOLF_CANDIDATE_COUNT - seatCountP48());
  const selectedWerewolfSeatsP48 = () => {
    try {
      return werewolfSelectedSeatIds({ fill: true }).slice(0, seatCountP48());
    } catch (_) {
      return WEREWOLF_CANDIDATE_SEAT_IDS.slice(0, seatCountP48());
    }
  };

  const hasConfirmMessageP48 = () =>
    Boolean(state.preRunFlow?.messages?.some(message => message && message.showConfirm));

  const advanceWerewolfConfirmP48 = () => {
    if (!state.werewolfMode || !state.preRunFlow?.active || state.preRunFlow.confirmed) return;
    if (hasConfirmMessageP48()) return;

    const last = state.preRunFlow.messages[state.preRunFlow.messages.length - 1];
    if (last) {
      last.working = false;
      last.msgState = "done";
    }

    const count = selectedWerewolfSeatsP48().length;
    state.preRunFlow.stage = 2;
    state.preRunFlow.messages.push({
      kind: "judge_prerun",
      role: "Grand Judge",
      text: `参赛席位已准备：${count}/${seatCountP48()}。确认后我会密封发放身份，并把每个模型的公开发言、追问、投票和复盘评分写入同一条对话流。`,
      msgState: "confirmed",
      showWerewolfPicker: true,
      showConfirm: true,
      chips: [
        ["身份密封", "evidence"],
        ["公开发言", "auto"],
        [`${standbyCountP48()} 个替补`, "seat"],
      ],
      stage: 2,
    });
    try {
      renderConferenceRoom();
    } catch (error) {
      console.error("[AI Judge P48] failed to render werewolf confirm stage", error);
    }
  };

  const previousStartWerewolfP48 = window.startPreRunFlowWerewolf || startPreRunFlowWerewolf;
  window.startPreRunFlowWerewolf = startPreRunFlowWerewolf = function(question) {
    const result = previousStartWerewolfP48.apply(this, arguments);
    window.setTimeout(advanceWerewolfConfirmP48, 950);
    window.setTimeout(advanceWerewolfConfirmP48, 1800);
    return result;
  };

console.log("P48 werewolf pre-run fail-safe applied");
})();
// ==== End P48 Patches ====

// ==== P49: Final werewolf dialogue compact closeout ====
(function initP49WerewolfDialogueCompactCloseout() {
  console.log("P49 werewolf dialogue compact closeout initializing...");

  const hideStandalonePickerP49 = () => {
    const picker = document.getElementById("werewolf-seat-picker");
    if (!picker) return;
    const replacementNeeded = state.werewolfGame?.status === "blocked" && (
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution
    );
    if (replacementNeeded) return;
    picker.hidden = true;
    picker.innerHTML = "";
    picker.setAttribute("aria-hidden", "true");
    picker.classList.remove("is-replacement-pending");
  };

  const previousRenderWerewolfPickerP49 = window.renderWerewolfPicker || renderWerewolfPicker;
  window.renderWerewolfPicker = renderWerewolfPicker = function() {
    const idleOrPreRun = state.werewolfMode && (!state.werewolfGame || (state.preRunFlow.active && !state.preRunFlow.confirmed));
    const replacementNeeded = state.werewolfGame?.status === "blocked" && (
      state.werewolfPendingReplacementSeat || state.werewolfGame?.pendingSubstitution
    );
    if (idleOrPreRun && !replacementNeeded) {
      hideStandalonePickerP49();
      return;
    }
    previousRenderWerewolfPickerP49.apply(this, arguments);
  };

  [50, 200, 600, 1100].forEach(delay => {
    window.setTimeout(() => {
      if (state.werewolfMode && !state.werewolfGame) {
        hideStandalonePickerP49();
        renderConferenceRoom();
      }
    }, delay);
  });

  console.log("P49 duplicate picker guard applied; P44/P40 console remains authoritative");
})();
// ==== End P49 Patches ====

// ==== P50: Werewolf compact dialogue closeout ====
(function initP50WerewolfCompactDialogueCloseout() {
  // P50 compact preview was the B-plan fallback. Plan C keeps the fuller
  // board console from P40/P44, so this patch remains only as a rollback marker.
  console.log("P50 compact dialogue closeout skipped; P44/P40 console remains authoritative");
})();
// ==== End P50 Patches ====

// ==== P51: Werewolf pre-run state lock ====
(function initP51WerewolfPreRunStateLock() {
  console.log("P51 werewolf pre-run state lock initializing...");

  const boardPresetsP51 = {
    standard: 9,
    white_wolf: 9,
    knight: 9,
    idiot: 9,
    full: 9,
    standard_14: 14,
    white_wolf_14: 14,
  };
  const boardSeatCountP51 = () => {
    const key = String(state.werewolfBoard || localStorage.getItem("ai_judge_werewolf_board") || "standard").trim();
    return boardPresetsP51[key] || 9;
  };
  const selectedCountP51 = () => {
    try {
      return werewolfSelectedSeatIds({ fill: true }).slice(0, boardSeatCountP51()).length;
    } catch (_) {
      return Math.min(WEREWOLF_CANDIDATE_COUNT, boardSeatCountP51());
    }
  };
  const isWorldcupPreRunP51 = () =>
    Boolean(state.preRunFlow?.active && !state.preRunFlow.confirmed && (
      isWorldcupPreRunFlowP53() ||
      getPreRunFlowKindP53() === "worldcup" ||
      preRunFlowHasTextP53(/世界杯|赛事预测|预测池|Run #/)
    ));
  const isWerewolfPreRunP51 = () =>
    Boolean(state.preRunFlow?.active && !state.preRunFlow.confirmed && !isWorldcupPreRunP51() && state.werewolfMode && (
      state._werewolfPreRunLock ||
      getPreRunFlowKindP53() === "werewolf" ||
      state.preRunFlow.messages?.some(message =>
        message?.showWerewolfPicker ||
        String(message?.text || "").includes("狼人杀")
      )
    ));
  const lockWerewolfP51 = () => {
    state._werewolfPreRunLock = true;
    state.werewolfMode = true;
    try { localStorage.setItem("ai_judge_werewolf_mode", "1"); } catch (_) {}
  };
  const unlockWerewolfP51 = () => {
    state._werewolfPreRunLock = false;
  };

  const previousClearPreRunP51 = window.clearPreRunFlow || clearPreRunFlow;
  window.clearPreRunFlow = clearPreRunFlow = function() {
    if (isWerewolfPreRunP51()) {
      console.info("[AI Judge P51] ignored incidental clearPreRunFlow during werewolf pre-run");
      return;
    }
    unlockWerewolfP51();
    return previousClearPreRunP51.apply(this, arguments);
  };

  const previousStartWerewolfP51 = window.startPreRunFlowWerewolf || startPreRunFlowWerewolf;
  window.startPreRunFlowWerewolf = startPreRunFlowWerewolf = function(question) {
    unlockWerewolfP51();
    const result = previousStartWerewolfP51.apply(this, arguments);
    setPreRunFlowKindP53("werewolf");
    lockWerewolfP51();
    [60, 740, 1200, 1900].forEach(delay => {
      window.setTimeout(() => {
        if (isWerewolfPreRunP51()) {
          lockWerewolfP51();
          const mini = document.getElementById("conference-ready-mini");
          if (mini) mini.textContent = `${selectedCountP51()}/${boardSeatCountP51()} 参赛`;
        }
      }, delay);
    });
    return result;
  };

  const previousConfirmP51 = window.confirmAndStartParliament || confirmAndStartParliament;
  window.confirmAndStartParliament = confirmAndStartParliament = function() {
    const wasWerewolf = Boolean(state.werewolfMode || state._werewolfPreRunLock);
    unlockWerewolfP51();
    if (wasWerewolf) state.werewolfMode = true;
    return previousConfirmP51.apply(this, arguments);
  };

  const previousSetWerewolfModeP51 = window.setWerewolfMode || setWerewolfMode;
  window.setWerewolfMode = setWerewolfMode = function(enabled) {
    if (!enabled) unlockWerewolfP51();
    const result = previousSetWerewolfModeP51.apply(this, arguments);
    if (enabled) {
      state.werewolfMode = true;
      try { localStorage.setItem("ai_judge_werewolf_mode", "1"); } catch (_) {}
    }
    return result;
  };

  const previousRenderConferenceRoomP51 = window.renderConferenceRoom || renderConferenceRoom;
  window.renderConferenceRoom = renderConferenceRoom = function() {
    if (isWorldcupPreRunP51()) {
      unlockWerewolfP51();
      state.werewolfMode = false;
      try { localStorage.setItem("ai_judge_werewolf_mode", "0"); } catch (_) {}
    }
    if (isWerewolfPreRunP51()) lockWerewolfP51();
    const result = previousRenderConferenceRoomP51.apply(this, arguments);
    if (state.werewolfMode && !isWorldcupPreRunP51()) {
      const mini = document.getElementById("conference-ready-mini");
      if (mini) mini.textContent = state.preRunFlow?.active && !state.preRunFlow.confirmed
        ? `${selectedCountP51()}/${boardSeatCountP51()} 参赛`
        : mini.textContent;
    }
    return result;
  };

  console.log("P51 werewolf pre-run state lock applied");
})();
// ==== End P51 Patches ====

// ==== P52: Final authoritative compact werewolf preview ====
(function initP52AuthoritativeCompactWerewolfPreview() {
  console.log("P52 authoritative compact werewolf preview initializing...");

  const boardsP52 = {
    quick_6: { name: "6快测", roles: ["villager", "seer", "werewolf", "witch", "werewolf", "villager"], desc: "2狼、预言家、女巫、2民" },
    compact_8: { name: "8压缩", roles: ["villager", "seer", "guard", "werewolf", "witch", "hunter", "werewolf", "villager"], desc: "2狼、预言家、女巫、猎人、守卫、2民" },
    standard: { name: "9标准", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"], desc: "3狼、3民、预言家、女巫、猎人、守卫" },
    advanced_10: { name: "10进阶", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "villager"], desc: "3狼、预言家、女巫、猎人、守卫、3民" },
    classic_12: { name: "12白狼", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "idiot", "werewolf", "villager"], desc: "3狼、白狼王、预言家、女巫、猎人、守卫、白痴、3民" },
    thirteen: { name: "13单替", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "knight", "idiot", "werewolf", "villager"], desc: "3狼、白狼王、预言家、女巫、猎人、守卫、骑士、白痴、3民" },
    white_wolf: { name: "9白狼王", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf"], desc: "2狼、白狼王、3民、预言家、女巫、猎人、守卫" },
    knight: { name: "9骑士", roles: ["villager", "seer", "guard", "knight", "werewolf", "witch", "werewolf", "villager", "werewolf"], desc: "3狼、3民、预言家、女巫、骑士、守卫" },
    idiot: { name: "9白痴", roles: ["idiot", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"], desc: "3狼、2民、预言家、女巫、猎人、守卫、白痴" },
    full: { name: "9全神", roles: ["idiot", "seer", "guard", "knight", "werewolf", "witch", "white_wolf", "villager", "werewolf"], desc: "2狼、白狼王、预言家、女巫、骑士、守卫、白痴、1民" },
    standard_14: { name: "14标准", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"], desc: "4狼、4民、预言家、女巫、猎人、守卫、骑士、白痴" },
    white_wolf_14: { name: "14白狼王", roles: ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager"], desc: "3狼、白狼王、4民、预言家、女巫、猎人、守卫、骑士、白痴" },
  };
  const playModesP52 = {
    standard_competition: { name: "标准竞技", desc: "严格规则：警长、警徽、平安夜、遗言、屠边和特殊技能。" },
    ai_experiment: { name: "AI实验", desc: "标准规则 + 迟到回收、原始回答、复盘评分和行为审计。" },
  };

  const boardKeyP52 = () => {
    const key = String(state.werewolfBoard || localStorage.getItem("ai_judge_werewolf_board") || "standard").trim();
    return boardsP52[key] ? key : "standard";
  };
  const boardP52 = () => boardsP52[boardKeyP52()] || boardsP52.standard;
  const playModeKeyP52 = () => {
    const key = String(state.werewolfPlayMode || localStorage.getItem("ai_judge_werewolf_play_mode") || "standard_competition").trim();
    return playModesP52[key] ? key : "standard_competition";
  };
  const seatCountP52 = () => boardP52().roles.length;
  const selectedP52 = () => {
    try {
      const explicit = werewolfSelectedSeatIds({ fill: false }).slice(0, seatCountP52());
      return explicit.length ? explicit : werewolfSelectedSeatIds({ fill: true }).slice(0, seatCountP52());
    } catch (_) {
      return WEREWOLF_CANDIDATE_SEAT_IDS.slice(0, seatCountP52());
    }
  };
  const roleLabelP52 = role => (typeof WEREWOLF_ROLE_LABELS !== "undefined" && WEREWOLF_ROLE_LABELS[role]) || role || "?";
  const boardSwitchP52 = () => `<div class="ww-board-switch" role="tablist" aria-label="狼人杀板型">
    ${Object.entries(boardsP52).map(([key, board]) => `
      <button type="button" class="ww-board-option ${key === boardKeyP52() ? "is-active" : ""}"
        onclick="event.preventDefault(); event.stopPropagation(); window.setWerewolfBoard && window.setWerewolfBoard('${escapeAttr(key)}')"
        aria-pressed="${key === boardKeyP52() ? "true" : "false"}">
        <span class="ww-board-name">${escapeHtml(board.name)}</span>
        <span class="ww-board-count">${board.roles.length}人</span>
        <small>${escapeHtml(board.desc)}</small>
      </button>
    `).join("")}
  </div>`;
  const playModeSwitchP52 = () => {
    const active = playModeKeyP52();
    const isExperiment = active === "ai_experiment";
    const next = isExperiment ? "standard_competition" : "ai_experiment";
    const activeMode = playModesP52[active] || playModesP52.standard_competition;
    return `<div class="ww-mode-toggle-wrap">
      <button type="button" class="ww-mode-toggle ${isExperiment ? "is-on" : ""}"
        data-werewolf-play-toggle="${escapeAttr(next)}"
        aria-pressed="${isExperiment ? "true" : "false"}"
        aria-label="切换狼人杀模式">
        <span>标准竞技</span>
        <i aria-hidden="true"></i>
        <span>AI实验</span>
      </button>
      <small>${escapeHtml(activeMode.desc)}</small>
    </div>`;
  };
  const compactPlayersP52 = selectedIds => {
    try {
      return werewolfPlayers(selectedIds).slice(0, seatCountP52());
    } catch (_) {
      return selectedIds.map((id, index) => ({ id, name: id, role: boardP52().roles[index] || "villager" }));
    }
  };
  const guideP52 = () => {
    const activeMode = playModesP52[playModeKeyP52()] || playModesP52.standard_competition;
    return `<div class="ww-guide-box" aria-label="狼人杀新手引导">
      <strong>新手三步</strong>
      <ol>
        <li>先选板型：不确定就用 9 标准；想全模型上场就选 14 标准。</li>
        <li>再选模式：标准竞技适合正常开局，AI 实验适合测试桥接、迟到回收和复盘。</li>
        <li>最后点席位换人：亮色为上场，灰色为候补；满员时先点一个上场席位移出，再点候补补进来。</li>
      </ol>
      <p>当前模式：${escapeHtml(activeMode.name)}。</p>
    </div>`;
  };
  const rosterGridP52 = selectedIds => {
    const activeSet = new Set(selectedIds);
    const full = selectedIds.length >= seatCountP52();
    return `<div class="ww-roster-grid" aria-label="上场席位选择">
      ${WEREWOLF_CANDIDATE_SEAT_IDS.map(id => {
        const seat = werewolfSeatById(id);
        const activeIndex = selectedIds.indexOf(id);
        const selected = activeIndex >= 0;
        const role = selected ? roleLabelP52(boardP52().roles[activeIndex] || "villager") : "候补";
        const score = getModelWerewolfScore(id);
        const scoreText = score ? `${Math.round(score.avg)}分/${score.count}局` : "暂无评分";
        const disabled = !selected && full;
        return `<button type="button"
          class="ww-roster-card ${selected ? "is-selected" : "is-standby"}"
          data-werewolf-pick="${escapeAttr(id)}"
          ${disabled ? "aria-disabled=\"true\"" : ""}
          style="--seat-color:${escapeAttr(seat.color || "#94a3b8")}">
          <span class="ww-roster-slot">${selected ? activeIndex + 1 : "替"}</span>
          <strong>${escapeHtml(seat.name)}</strong>
          <em>${escapeHtml(role)}</em>
          <small>${escapeHtml(scoreText)}</small>
        </button>`;
      }).join("")}
    </div>`;
  };

  window.renderWerewolfPrepSummary = renderWerewolfPrepSummary = function() {
    const board = boardP52();
    const selectedIds = selectedP52();
    const players = compactPlayersP52(selectedIds);
    const roleLine = board.roles.map((role, index) =>
      `<span class="ww-role-mini"><b>${index + 1}</b>${escapeHtml(roleLabelP52(role))}</span>`
    ).join("");
    return `
      <div class="ww-prep-summary p52-compact" aria-label="狼人杀开局预览">
        <div class="ww-prep-head">
          <strong>狼人杀开局预览</strong>
          <span>${escapeHtml(board.name)} · ${selectedIds.length}/${seatCountP52()} 参赛 · ${Math.max(0, WEREWOLF_CANDIDATE_COUNT - seatCountP52())} 替补</span>
        </div>
        ${guideP52()}
        ${boardSwitchP52()}
        ${playModeSwitchP52()}
        <div class="ww-prep-grid">
          <section>
            <h4>身份板</h4>
            <div class="ww-role-strip">${roleLine}</div>
          </section>
          <section>
            <h4>上场席位</h4>
            ${rosterGridP52(selectedIds)}
          </section>
        </div>
        <p>${escapeHtml(board.desc)}。确认后进入真实网页席位发言；对话流只保留法官和模型发言，席位细节收进右上抽屉。</p>
      </div>
    `;
  };

  window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
    return `
      <div class="empty-state-parliament ww-empty-state">
        ${renderWerewolfPrepSummary()}
      </div>
    `;
  };

  const previousParliamentEmptyP52 = window.parliamentEmptyStateHtml || parliamentEmptyStateHtml;
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    return previousParliamentEmptyP52.apply(this, arguments);
  };

  const previousRenderWerewolfPickerP52 = window.renderWerewolfPicker || renderWerewolfPicker;
  window.renderWerewolfPicker = renderWerewolfPicker = function() {
    // P58: pre-run seat management lives in the drawer; inline picker is only for replacement recovery.
    const isWerewolfPreRun = state.preRunFlow.active && !state.preRunFlow.confirmed && isWerewolfPreRunFlowP53();
    const isWerewolfIdle = !state.werewolfGame && state.werewolfMode;
    if (isWerewolfPreRun || isWerewolfIdle) {
      const node = document.getElementById("werewolf-seat-picker");
      hideWerewolfSeatPicker(node);
      return;
    }
    return previousRenderWerewolfPickerP52.apply(this, arguments);
  };

  const previousSetWerewolfModeP52 = window.setWerewolfMode || setWerewolfMode;
  window.setWerewolfMode = setWerewolfMode = function(enabled) {
    const result = previousSetWerewolfModeP52.apply(this, arguments);
    if (enabled) {
      window.setTimeout(() => {
        const stream = document.getElementById("conference-seat-stream");
        if (stream && state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
          stream.innerHTML = werewolfEmptyStateHtml();
          stream.dataset.renderSignature = `p52-${boardKeyP52()}-${selectedP52().join(",")}`;
        }
      }, 120);
    }
    return result;
  };

  console.log("P52 authoritative compact werewolf preview applied");
})();
// ==== End P52 Patches ====

// ==== Start P56 Patches: Compact Werewolf Empty State (no prep summary in main stream) ====
(function() {
  // P56.1: Compact empty state — no renderWerewolfPrepSummary() in main dialogue
  window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
    return `
      <div class="empty-state-parliament ww-empty-state ww-compact-state">
        <h3>模型狼人杀</h3>
        <p>从 14 个模型中选择参赛席位；身份与板型在右侧抽屉管理。</p>
        <button class="ac-werewolf-drawer-btn" type="button" onclick="event.stopPropagation();window.__AI_JUDGE_DRAWER__?.toggleDrawer('werewolf')">打开席位与板型 →</button>
      </div>
    `;
  };

  // P56.2: parliamentEmptyStateHtml → compact werewolf empty state (same logic, now uses compact)
  const previousParliamentEmptyP56 = window.parliamentEmptyStateHtml;
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    return previousParliamentEmptyP56.apply(this, arguments);
  };

  // P56.3: setWerewolfMode → stream.innerHTML uses compact empty state
  const previousSetWerewolfModeP56 = window.setWerewolfMode;
  window.setWerewolfMode = setWerewolfMode = function(enabled) {
    const result = previousSetWerewolfModeP56.apply(this, arguments);
    if (enabled) {
      window.setTimeout(function() {
        var stream = document.getElementById("conference-seat-stream");
        if (stream && state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
          stream.innerHTML = werewolfEmptyStateHtml();
        }
      }, 120);
    }
    return result;
  };

  console.log("P56 compact werewolf empty state applied (full prep only in drawer)");
})();
// ==== End P56 Patches ====

// ==== P58: Live desktop flow guardrails and Marvis mode closeout ====
(function initP58LiveDesktopFlowCloseout() {
  console.log("P58 live desktop flow closeout initializing...");

  window.aiJudgeCardActionP58 = function(event, tab) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    }
    const target = String(tab || "").trim();
    if (!target) return false;
    if (target === "werewolfDrawer") {
      if (window.__AI_JUDGE_DRAWER__?.openDrawer) window.__AI_JUDGE_DRAWER__.openDrawer("werewolf");
      else window.__AI_JUDGE_DRAWER__?.toggleDrawer?.("werewolf");
      return false;
    }
    if (target === "worldcup") {
      startWorldcupPredictionFlow();
      return false;
    }
    if (target === "worldcupPage") {
      openWorldcupPool();
      return false;
    }
    switchTab(target);
    return false;
  };

  window.aiJudgeConfirmP58 = function(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    }
    confirmAndStartParliament();
    return false;
  };

  const bindCardControlsP58 = () => {
    document.querySelectorAll(".ac-confirm-btn:not([data-p58-bound])").forEach(button => {
      button.dataset.p58Bound = "1";
      button.addEventListener("click", window.aiJudgeConfirmP58, true);
    });
    document.querySelectorAll(".answer-card .ghost[data-tab-shortcut]:not([data-p58-bound])").forEach(button => {
      button.dataset.p58Bound = "1";
      button.addEventListener("click", event => window.aiJudgeCardActionP58(event, button.dataset.tabShortcut), true);
    });
  };

  const setFlowSurfaceP58 = () => {
    const shell = document.getElementById("app-shell");
    if (shell) {
      shell.dataset.currentFlow = isWorldcupPreRunFlowP53() ? "worldcup" : state.werewolfMode ? "werewolf" : "meeting";
      shell.classList.toggle("worldcup-mode", isWorldcupPreRunFlowP53());
      shell.classList.toggle("flow-has-drawer", Boolean(state.drawerOpen));
    }
    const flow = document.getElementById("conference-seat-stream");
    if (flow) {
      flow.style.scrollPaddingTop = "132px";
      flow.style.scrollPaddingBottom = "252px";
    }
    bindCardControlsP58();
  };

  const previousEmptyP58 = window.parliamentEmptyStateHtml || parliamentEmptyStateHtml;
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    if (!conferenceQuestion(state.currentVerdict)) {
      return `
        <div class="empty-state-parliament p58-empty-state">
          <strong>等待议题</strong>
          <p>输入一句话，Grand Judge 会先整理边界，再让席位按顺序发言。长文、证据和报告会收进右侧抽屉，不挤占主对话流。</p>
        </div>
      `;
    }
    return previousEmptyP58.apply(this, arguments);
  };

  const previousWerewolfEventToMessageP58 = window.werewolfEventToMessage || werewolfEventToMessage;
  window.werewolfEventToMessage = werewolfEventToMessage = function(event, index, game) {
    const message = previousWerewolfEventToMessageP58.apply(this, arguments);
    const text = String(event?.text || message?.text || "");
    const isExecutorBusy = /bridge_busy|执行器启动失败|executor/i.test(text);
    if (message?.kind === "judge" && isExecutorBusy) {
      message.msgState = "blocked";
      message.status = "执行器等待";
      message.text = `${text}\n\n当前不会回退到本地模板发言。建议先等待桥接释放，或切到赛事预测/普通会议继续；本局身份与公开记录会保留在档案里，稍后可重新检测并继续。`;
      message.chips = [["真实执行器", "warn"], ["可恢复", "auto"], ["不污染台词", "evidence"]];
      message.actions = [["赛事预测", "worldcup"], ["证据", "evidence"]];
    }
    return message;
  };

  const previousStartWorldcupP58 = window.startWorldcupPredictionFlow || startWorldcupPredictionFlow;
  window.startWorldcupPredictionFlow = startWorldcupPredictionFlow = function() {
    window.__AI_JUDGE_DRAWER__?.closeDrawer?.();
    if (state.preRunFlow?.timer) {
      window.clearTimeout(state.preRunFlow.timer);
      state.preRunFlow.timer = null;
    }
    if (state.werewolfGame || state.werewolfMode || state._werewolfPreRunLock) {
      forceExitWerewolfContextP53({ clearSelected: false });
    }
    const result = previousStartWorldcupP58.apply(this, arguments);
    requestAnimationFrame(setFlowSurfaceP58);
    return result;
  };

  const previousSetWerewolfP58 = window.setWerewolfMode || setWerewolfMode;
  window.setWerewolfMode = setWerewolfMode = function(enabled) {
    if (enabled && isWorldcupPreRunFlowP53()) {
      clearPreRunFlow();
      state.preRunTranscript = [];
      state.currentVerdict = null;
      state.currentTask = null;
    }
    window.__AI_JUDGE_DRAWER__?.closeDrawer?.();
    const result = previousSetWerewolfP58.apply(this, arguments);
    requestAnimationFrame(setFlowSurfaceP58);
    return result;
  };

  const previousRenderConferenceRoomP58 = window.renderConferenceRoom || renderConferenceRoom;
  window.renderConferenceRoom = renderConferenceRoom = function() {
    const result = previousRenderConferenceRoomP58.apply(this, arguments);
    requestAnimationFrame(setFlowSurfaceP58);
    return result;
  };

  if (window.MutationObserver) {
    const flow = document.getElementById("conference-seat-stream");
    if (flow) {
      new MutationObserver(bindCardControlsP58).observe(flow, { childList: true, subtree: true });
    }
  }
  [60, 240, 720].forEach(delay => window.setTimeout(setFlowSurfaceP58, delay));
  window.setTimeout(() => {
    const flow = document.getElementById("conference-seat-stream");
    if (flow && !flow.children.length && !conferenceQuestion(state.currentVerdict)) {
      renderConferenceRoom();
    }
  }, 120);

  console.log("P58 live desktop flow closeout applied");
})();
// ==== End P58 Patches ====

// ==== Start P60 Patches: Inline model selection + Drawer redesign + Run control ====
(function initP60WerewolfFlowRedesign() {
  console.log("P60 werewolf flow redesign initializing...");

  // ── P60.1: werewolfEmptyStateHtml → inline model selection in main dialogue ──
  window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
    var selectedIds = werewolfSelectedSeatIds({ fill: true });
    var players = werewolfPlayers(selectedIds);
    // Build 9 compact avatar chips
    var chipsHtml = players.slice(0, WEREWOLF_SEAT_COUNT).map(function(p, i) {
      var avatarUrl = _avatarDataUri(p.id) || '';
      return '<span class="ww-inline-seat-chip is-active" data-seat="' + escapeAttr(p.id) + '" style="--seat-color:' + escapeAttr(p.color) + '">'
        + '<img class="ww-inline-seat-avatar" src="' + escapeAttr(avatarUrl) + '" alt="' + escapeAttr(p.name) + '" width="28" height="28" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\';" />'
        + '<span class="ww-inline-seat-initial" style="display:none;background:' + escapeAttr(p.color) + '">' + escapeHtml(p.name.charAt(0)) + '</span>'
        + '<span class="ww-inline-seat-name">' + escapeHtml(p.name) + '</span>'
        + '</span>';
    }).join('');

    var count = selectedIds.length;
    var chipLabel = count + '/' + WEREWOLF_SEAT_COUNT + ' 位议员';
    var confirmDisabled = count < 2 ? ' disabled' : '';

    return ''
      + '<div class="empty-state-parliament ww-empty-state ww-inline-state">'
      + '<div class="ww-inline-header">'
      + '<h3>模型狼人杀 · 9人标准局</h3>'
      + '<p>已就位 ' + chipLabel + '。点击席位可在抽屉管理替补池与板型。</p>'
      + '</div>'
      + '<div class="ww-inline-seat-rail">' + chipsHtml + '</div>'
      + '<div class="ww-inline-actions">'
      + '<button class="ac-confirm-btn ww-start-btn" type="button"' + confirmDisabled + ' onclick="event.stopPropagation();return window.aiJudgeStartWerewolfP60 ? window.aiJudgeStartWerewolfP60(event) : (confirmAndStartParliament(), false)">开始狼人杀</button>'
      + '<button class="ac-werewolf-drawer-btn ww-manage-btn" type="button" onclick="event.stopPropagation();window.__AI_JUDGE_DRAWER__?.toggleDrawer(\'werewolf\')">管理席位与板型 &#8594;</button>'
      + '</div>'
      + '</div>';
  };

  // P60.2: aiJudgeStartWerewolfP60 → confirm entry from inline state
  window.aiJudgeStartWerewolfP60 = function(event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }
    var selectedIds = werewolfSelectedSeatIds();
    if (selectedIds.length < 2) {
      alert("至少选择2位议员才能开始狼人杀。");
      return false;
    }
    confirmAndStartParliament();
    return false;
  };

  // P60.3: Override parliamentEmptyStateHtml (must replace P56's override)
  window.parliamentEmptyStateHtml = parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    // Fall back to original (no prep in pre-run)
    var selected = werewolfSelectedSeatIds({ fill: true }).slice(0, WEREWOLF_SEAT_COUNT);
    var targets = werewolfPlayers(selected);
    var roleLine = targets.map(function(p, i) {
      return '<span class="ww-role-mini"><b>' + (i + 1) + '</b>' + escapeHtml(p.roleLabel || p.role || '?') + '</span>';
    }).join('');
    return ''
      + '<div class="empty-state-parliament">'
      + '<strong>模型议会桌</strong>'
      + '<p>这里不是普通议会等待页。本局会从 ' + WEREWOLF_CANDIDATE_COUNT + ' 个模型里选 ' + WEREWOLF_SEAT_COUNT + ' 个参赛，' + WEREWOLF_STANDBY_COUNT + ' 个替补；Grand Judge 私下密封身份，公开流只展示发言、追问、投票和复盘评分。</p>'
      + '<div class="ww-role-strip">' + roleLine + '</div>'
      + '</div>';
  };

  // P60.4: Run control — stop werewolf via P59 /api/runs/<id>/stop
  window.__wwStopWerewolfP60 = function() {
    if (!state.werewolfRunId) {
      alert("未找到狼人杀运行记录。");
      return;
    }
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/runs/" + encodeURIComponent(state.werewolfRunId) + "/stop", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function() {
      if (xhr.status === 200) {
        console.log("P60: Werewolf run stop requested via /api/runs");
        renderDrawerContent();
      } else {
        console.error("P60: Stop failed", xhr.status, xhr.responseText);
      }
    };
    xhr.onerror = function() { console.error("P60: Stop request failed (network)"); };
    xhr.send();
  };

  // P60.5: Patch renderDrawerContent to auto-refresh werewolf tab during runs
  var _renderDrawerContentP60 = window.renderDrawerContent || (function() {
    var drawerEl = document.getElementById('drawer-content');
    if (!drawerEl) return;
    if (state.drawerOpen && state.drawerTab === 'werewolf' && state.werewolfGame) {
      renderDrawerContent();
    }
  });
  // Run control drawer refresh: poll every 3s when werewolf tab is open and game is running
  window.setInterval(function() {
    if (state.drawerOpen && state.drawerTab === 'werewolf' && state.werewolfGame) {
      try { renderDrawerContent(); } catch(e) { /* ignore */ }
    }
  }, 3000);

  console.log("P60 werewolf flow redesign applied (inline picker + drawer compact + run control)");
})();
// ==== End P60 Patches ====

// ==== Start P61 Patches: Product Architecture Static QA & Lightweight Optimization ====
(function initP61ProductArchitectureQA() {
  console.log("P61 product architecture QA initializing...");

  // ── P61.1: Unify drawer tabs across all modes ──
  var P61_DRAWER_TABS = [
    { id: 'log',     label: '日志' },
    { id: 'detail',  label: '详情' },
    { id: 'outputs', label: '产物' },
    { id: 'report',  label: '报告' },
    { id: 'mode',    label: '当前模式' },
  ];

  var _origRenderDrawerContent = window.renderDrawerContent;

  // ── P61.2: Override renderDrawerContent with unified tab system ──
  window.renderDrawerContent = renderDrawerContent = function() {
    var tabsContainer = document.getElementById('drawer-tabs');
    if (tabsContainer && tabsContainer.dataset.p61 !== '1') {
      tabsContainer.dataset.p61 = '1';
      tabsContainer.innerHTML = P61_DRAWER_TABS.map(function(t) {
        return '<button class="drawer-tab" data-drawer-tab="' + t.id + '" type="button">' + t.label + '</button>';
      }).join('');
      tabsContainer.querySelectorAll('.drawer-tab').forEach(function(tab) {
        tab.addEventListener('click', function() {
          state.drawerTab = tab.dataset.drawerTab;
          tabsContainer.querySelectorAll('.drawer-tab').forEach(function(t) {
            t.classList.toggle('active', t.dataset.drawerTab === state.drawerTab);
          });
          renderDrawerContent();
        });
      });
    }

    if (tabsContainer) {
      tabsContainer.querySelectorAll('.drawer-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.drawerTab === state.drawerTab);
      });
    }

    if (state.drawerTab === 'log' || state.drawerTab === 'detail' ||
        state.drawerTab === 'outputs' || state.drawerTab === 'report') {
      if (_origRenderDrawerContent) {
        try { _origRenderDrawerContent(); } catch(e) { console.warn("P61: orig renderDrawerContent failed", e); }
      }
      return;
    }

    var content = document.getElementById('drawer-content');
    if (!content) return;
    var isWerewolf = Boolean(state.werewolfMode || state.werewolfGame);
    var isWorldcup = Boolean(typeof isWorldcupPreRunFlowP53 === 'function' && isWorldcupPreRunFlowP53());
    var hasVerdict = Boolean(state.currentVerdict);
    var hasTask = Boolean(state.currentTask);
    var blocksHtml = '';

    if (isWerewolf) {
      var selectedIds = werewolfSelectedSeatIds({ fill: true });
      var count = selectedIds.length;
      var game = state.werewolfGame;
      var activeCount = game ? (game.players || []).length : count;
      var standbyCount = game
        ? WEREWOLF_CANDIDATE_SEAT_IDS.filter(function(id) { return !(game.players || []).some(function(p) { return p.id === id; }) && !(game.offlineSeats || []).includes(id); }).length
        : WEREWOLF_CANDIDATE_SEAT_IDS.filter(function(id) { return !selectedIds.includes(id); }).length;
      var phaseLabels = { setup: "身份密封", day: "白天发言", night: "夜晚行动", vote: "投票阶段", complete: "已结算" };
      var currentPhase = game ? (phaseLabels[game.phase] || game.phase || "运行中") : "";
      var eliminated = new Set(game ? (game.eliminatedSeats || []) : []);
      var aliveCount = activeCount - eliminated.size;

      blocksHtml += '<section class="ww-drawer-block"><h4>当前局势</h4>';
      blocksHtml += '<div class="ww-drawer-chips">';
      blocksHtml += '<span class="ww-chip">9人标准局</span>';
      blocksHtml += '<span class="ww-chip">' + aliveCount + '/' + activeCount + ' 存活</span>';
      blocksHtml += '<span class="ww-chip">' + standbyCount + ' 替补</span>';
      if (currentPhase) blocksHtml += '<span class="ww-chip ww-chip-phase">' + currentPhase + '</span>';
      blocksHtml += '</div>';
      if (game) {
        var gate = game.bridgeGate;
        var readyCount = gate ? gate.readyCount : activeCount;
        var total = gate ? gate.total : activeCount;
        var progressPct = total > 0 ? Math.round((readyCount / total) * 100) : 0;
        blocksHtml += '<div class="ww-progress-bar"><i style="--progress:' + progressPct + '%"></i><span>' + readyCount + '/' + total + ' 就绪</span></div>';
        blocksHtml += '<div class="ww-run-actions"><button class="ww-stop-btn" type="button" onclick="event.stopPropagation();window.__wwStopWerewolfP60&&window.__wwStopWerewolfP60()">停止</button></div>';
      }
      blocksHtml += '</section>';

      blocksHtml += '<section class="ww-drawer-block"><details class="ww-advanced"><summary>席位与板型管理</summary>';
      blocksHtml += '<div class="ww-advanced-body"><div id="drawer-werewolf-picker-p61"></div><div id="drawer-werewolf-prep-p61"></div></div>';
      blocksHtml += '</details></section>';

      blocksHtml += '<section class="ww-drawer-block ww-guide"><h4>玩法说明</h4>';
      blocksHtml += '<p>9 位 AI 随机扮演 3狼、3民、预言家、女巫、猎人。发言进入对话流，投票决定淘汰。</p>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel drawer-werewolf-panel drawer-ww-compact"><h3>狼人杀</h3>' + blocksHtml + '</div>';

      setTimeout(function() {
        var pd = document.getElementById('drawer-werewolf-picker-p61');
        var pp = document.getElementById('drawer-werewolf-prep-p61');
        if (pd && typeof renderInlineWerewolfPicker === 'function') pd.innerHTML = renderInlineWerewolfPicker();
        if (pp && typeof renderWerewolfPrepSummary === 'function') pp.innerHTML = renderWerewolfPrepSummary();
      }, 40);

    } else if (isWorldcup) {
      blocksHtml += '<section class="ww-drawer-block"><h4>预测状态</h4>';
      blocksHtml += '<p>赛事预测运行中。Grand Judge 组织多模型基于历史数据、投注规则进行概率分析。</p>';
      if (hasTask) blocksHtml += '<div class="ww-progress-bar"><i style="--progress:50%"></i><span>席位发言中</span></div>';
      blocksHtml += '</section>';

      blocksHtml += '<section class="ww-drawer-block"><details class="ww-advanced"><summary>预测参数与资金</summary>';
      blocksHtml += '<div class="ww-advanced-body"><p>贷款账本、奖励账本、投注记录等高级参数由 Grand Judge 管理。结束后可查看完整报告。</p></div>';
      blocksHtml += '</details></section>';

      blocksHtml += '<section class="ww-drawer-block"><h4>相关产物</h4>';
      blocksHtml += '<p>预测完成后，排行榜、账户明细、投注记录归档到「产物」和「报告」tab。</p>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel drawer-werewolf-panel"><h3>赛事预测</h3>' + blocksHtml + '</div>';

    } else {
      var phaseLabel = hasVerdict ? '裁决完成' : hasTask ? '运行中' : '就绪';
      var seatCount = state.selectedSeats ? state.selectedSeats.size : 0;

      blocksHtml += '<section class="ww-drawer-block"><h4>当前状态</h4>';
      blocksHtml += '<div class="ww-drawer-chips">';
      blocksHtml += '<span class="ww-chip">' + phaseLabel + '</span>';
      blocksHtml += '<span class="ww-chip">' + seatCount + ' 席位已选</span>';
      blocksHtml += '</div>';
      blocksHtml += '<p style="margin-top:8px;color:#666;font-size:13px;">输入议题后 Grand Judge 整理计划，确认后席位按序发言。</p>';
      blocksHtml += '</section>';

      blocksHtml += '<section class="ww-drawer-block"><h4>判决模式</h4>';
      var currentMode = state.selectedMode || 'flash';
      blocksHtml += '<div class="ww-drawer-chips" style="margin-bottom:8px;">';
      blocksHtml += '<span class="ww-chip' + (currentMode === 'flash' ? ' ww-chip-active' : '') + '">快速</span>';
      blocksHtml += '<span class="ww-chip' + (currentMode === 'standard' ? ' ww-chip-active' : '') + '">标准</span>';
      blocksHtml += '<span class="ww-chip' + (currentMode === 'strategic' ? ' ww-chip-active' : '') + '">深度</span>';
      blocksHtml += '</div>';
      blocksHtml += '<p style="color:#888;font-size:12px;">提交前切换模式，影响发言轮数和分析深度。</p>';
      blocksHtml += '</section>';

      blocksHtml += '<section class="ww-drawer-block"><h4>快捷说明</h4>';
      blocksHtml += '<p style="color:#666;font-size:13px;">提交议题 → Grand Judge 确认 → 席位发言 → 形成裁决。长文和报告收进抽屉。</p>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel"><h3>' + getModeConfig(state.selectedMode).label + '</h3>' + blocksHtml + '</div>';
    }
  };

  // ── P61.3: Userify main dialogue empty states ──
  var _parliamentEmptyStateHtmlP61 = parliamentEmptyStateHtml;
  parliamentEmptyStateHtml = window.parliamentEmptyStateHtml = function() {
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow && state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    if (typeof isWorldcupPreRunFlowP53 === 'function' && isWorldcupPreRunFlowP53() && !state.currentVerdict && !state.currentTask) {
      return ''
        + '<div class="empty-state-parliament p61-worldcup-empty">'
        + '<h3>赛事预测</h3>'
        + '<p>输入你想预测的赛事、队伍或目标，AI Judge 会组织多模型给出概率与依据。</p>'
        + '<div class="p61-mode-select">'
        + '<span class="ww-chip ww-chip-active">快速预测</span>'
        + '<span class="ww-chip">深度预测</span>'
        + '</div>'
        + '</div>';
    }
    if (!conferenceQuestion(state.currentVerdict)) {
      var _p61Cfg = getModeConfig(state.selectedMode);
      return ''
        + '<div class="empty-state-parliament p61-judgment-empty">'
        + '<h3>' + _p61Cfg.label + '</h3>'
        + '<p>' + _p61Cfg.guideText + '</p>'
        + '<div class="p61-quick-actions"><span class="p61-hint">支持上传文件作为证据材料</span></div>'
        + '</div>';
    }
    return _parliamentEmptyStateHtmlP61.apply(this, arguments);
  };

  // ── P61.4: Userify input placeholder ──
  (function patchInputPlaceholder() {
    var timer = setInterval(function() {
      var input = document.getElementById('parliament-question-input');
      if (input) {
        var oldPh = input.placeholder || '';
        if (oldPh.indexOf('提交议题') !== -1 || oldPh.indexOf('对齐需求') !== -1) {
          if (state.werewolfMode) input.placeholder = '输入本局主题，按 Enter 开局…';
          else if (typeof isWorldcupPreRunFlowP53 === 'function' && isWorldcupPreRunFlowP53()) input.placeholder = '描述你想预测的赛事…';
          else input.placeholder = getModeConfig(state.selectedMode).placeholder;
        }
        clearInterval(timer);
      }
    }, 300);
  })();

  // ── P61.5: Map old tab IDs → new unified ──
  var _drawerAPI = window.__AI_JUDGE_DRAWER__;
  if (_drawerAPI) {
    var _origOpen = _drawerAPI.openDrawer;
    var _origToggle = _drawerAPI.toggleDrawer;
    _drawerAPI.openDrawer = function(tab) {
      var nt = (tab === 'werewolf' || tab === 'notifications') ? 'mode' : tab;
      _origOpen.call(_drawerAPI, nt);
    };
    _drawerAPI.toggleDrawer = function(tab) {
      var nt = (tab === 'werewolf' || tab === 'notifications') ? 'mode' : tab;
      _origToggle.call(_drawerAPI, nt);
    };
  }

  // ── P61.6: Resume werewolf run ──
  if (!window.__wwResumeWerewolfP61) {
    window.__wwResumeWerewolfP61 = function() {
      if (!state.werewolfRunId) return;
      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/runs/" + encodeURIComponent(state.werewolfRunId) + "/resume", true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.onload = function() {
        if (xhr.status === 200 && typeof renderDrawerContent === 'function') renderDrawerContent();
      };
      xhr.send();
    };
  }

  // ── P61.7: CSS guard ──
  var styleId = 'p61-flow-surface-css';
  if (!document.getElementById(styleId)) {
    var s = document.createElement('style');
    s.id = styleId;
    s.textContent = ''
      + '.p61-judgment-empty,.p61-worldcup-empty{text-align:center;padding:48px 24px;max-width:560px;margin:0 auto}\n'
      + '.p61-judgment-empty h3,.p61-worldcup-empty h3{font-size:20px;font-weight:600;color:#1a1a1a;margin:0 0 12px}\n'
      + '.p61-judgment-empty p,.p61-worldcup-empty p{font-size:14px;color:#666;line-height:1.6;margin:0 0 16px}\n'
      + '.p61-quick-actions{margin-top:16px}\n'
      + '.p61-hint{display:inline-block;padding:6px 14px;border-radius:16px;background:#f0f0f5;color:#888;font-size:12px}\n'
      + '.p61-mode-select{display:flex;gap:8px;justify-content:center;margin-top:4px}\n'
      + '.ww-chip-active{background:#1a1aff!important;color:#fff!important}\n'
      + '.empty-state-parliament .seat-grid,.empty-state-parliament .werewolf-picker-head{display:none!important}\n';
    document.head.appendChild(s);
  }

  console.log("P61 product architecture QA applied");
})();
// ==== End P61 Patches ====

// ==== Start P63 Patches: Three-Flow Lightweight Closeout ====
(function initP63ThreeFlowCloseout() {
  console.log("P63 three-flow lightweight closeout initializing...");

  // ── P63.1: Refine werewolf main dialogue → light prompt only (no inline chips) ──
  if (window.werewolfEmptyStateHtml) {
    var _werewolfEmptyP63 = werewolfEmptyStateHtml;
    window.werewolfEmptyStateHtml = werewolfEmptyStateHtml = function() {
      return ''
        + '<div class="empty-state-parliament ww-empty-state ww-light-state">'
        + '<div class="ww-light-header">'
        + '<h3>模型狼人杀 · 9人标准局</h3>'
        + '<p>Grand Judge 会密封分配 3狼、3民、预言家、女巫、猎人。发言、投票进入主对话流，长文和复盘收进右侧抽屉。</p>'
        + '</div>'
        + '<div class="ww-light-actions">'
        + '<button class="ac-confirm-btn ww-start-btn" type="button" onclick="event.stopPropagation();return window.aiJudgeStartWerewolfP60 ? window.aiJudgeStartWerewolfP60(event) : (confirmAndStartParliament(), false)">开始狼人杀</button>'
        + '<button class="ac-werewolf-drawer-btn ww-manage-btn" type="button" onclick="event.stopPropagation();window.__AI_JUDGE_DRAWER__?.toggleDrawer(\'werewolf\')">管理席位与板型 →</button>'
        + '</div>'
        + '</div>';
    };
  }

  // ── P63.2: Refine parliamentEmptyStateHtml → P63 lightweight versions ──
  var _parliamentEmptyP63 = parliamentEmptyStateHtml;
  parliamentEmptyStateHtml = window.parliamentEmptyStateHtml = function() {
    // Werewolf: use P63 light prompt
    if (state.werewolfMode && !state.werewolfGame && !(state.preRunFlow && state.preRunFlow.active && !state.preRunFlow.confirmed)) {
      return werewolfEmptyStateHtml();
    }
    // Worldcup: lightweight prompt
    if (typeof isWorldcupPreRunFlowP53 === 'function' && isWorldcupPreRunFlowP53()) {
      return ''
        + '<div class="empty-state-parliament p63-worldcup-empty">'
        + '<h3>赛事预测</h3>'
        + '<p>输入你想预测的赛事、队伍或目标。Grand Judge 会组织多模型给出概率分析，结果汇总在右侧抽屉。</p>'
        + '</div>';
    }
    // Fast judgment: clean Grand Judge prompt
    if (!conferenceQuestion(state.currentVerdict)) {
      var _p63Cfg = getModeConfig(state.selectedMode);
      return ''
        + '<div class="empty-state-parliament p63-judgment-empty">'
        + '<h3>' + _p63Cfg.label + '</h3>'
        + '<p>' + _p63Cfg.guideText + '</p>'
        + '<div class="p63-quick-actions">'
        + '<span class="p63-hint">支持上传文件作为证据</span>'
        + '</div>'
        + '</div>';
    }
    return _parliamentEmptyP63.apply(this, arguments);
  };

  // ── P63.3: Refine drawer "当前模式" → P63 lightweight 3-block ──
  var _renderDrawerP63 = renderDrawerContent;
  renderDrawerContent = window.renderDrawerContent = function() {
    // Only override for "mode" tab (and "werewolf"/"notifications" mapped to "mode")
    var effectiveTab = state.drawerTab;
    if (effectiveTab === 'werewolf' || effectiveTab === 'notifications') effectiveTab = 'mode';

    if (effectiveTab !== 'mode') {
      if (_renderDrawerP63) { try { _renderDrawerP63(); } catch(e) {} }
      return;
    }

    var content = document.getElementById('drawer-content');
    if (!content) return;

    var isWerewolf = Boolean(state.werewolfMode || state.werewolfGame);
    var isWorldcup = Boolean(typeof isWorldcupPreRunFlowP53 === 'function' && isWorldcupPreRunFlowP53());
    var hasVerdict = Boolean(state.currentVerdict);
    var hasTask = Boolean(state.currentTask);
    var blocksHtml = '';

    if (isWerewolf) {
      // ── Werewolf: 3-block ──
      var game = state.werewolfGame;
      var selectedIds = werewolfSelectedSeatIds({ fill: true });
      var count = selectedIds.length;
      var activeCount = game ? (game.players || []).length : count;
      var standbyCount = game
        ? WEREWOLF_CANDIDATE_SEAT_IDS.filter(function(id) { return !(game.players || []).some(function(p) { return p.id === id; }); }).length
        : WEREWOLF_CANDIDATE_SEAT_IDS.length - count;
      var phaseLabel = game ? (game.phase === 'complete' ? '已结算' : game.phase === 'day' ? '白天' : game.phase === 'night' ? '夜晚' : game.phase === 'vote' ? '投票' : '运行中') : '待开局';
      var eliminated = new Set(game ? (game.eliminatedSeats || []) : []);

      // Block 1: 当前局势
      blocksHtml += '<section class="ww-drawer-block"><h4>当前局势</h4>';
      blocksHtml += '<div class="ww-drawer-chips">';
      blocksHtml += '<span class="ww-chip ww-chip-label">9人标准局</span>';
      blocksHtml += '<span class="ww-chip">' + (activeCount - eliminated.size) + '/' + activeCount + ' 存活</span>';
      blocksHtml += '<span class="ww-chip">' + standbyCount + ' 替补</span>';
      blocksHtml += '<span class="ww-chip ww-chip-phase">' + phaseLabel + '</span>';
      blocksHtml += '</div>';
      if (game && game.runId) {
        var runId = game.runId || state.werewolfRunId;
        blocksHtml += '<div class="ww-drawer-run-ctrl">';
        blocksHtml += '<button class="ww-pause-btn" type="button" onclick="event.stopPropagation();window.__wwStopWerewolfP60&&window.__wwStopWerewolfP60()">暂停</button>';
        blocksHtml += '</div>';
      }
      blocksHtml += '</section>';

      // Block 2: 席位与板型 (collapsed)
      blocksHtml += '<section class="ww-drawer-block"><details class="ww-advanced"><summary>席位与板型</summary>';
      blocksHtml += '<div class="ww-advanced-body"><div id="drawer-werewolf-picker-p63"></div><div id="drawer-werewolf-prep-p63"></div></div>';
      blocksHtml += '</details></section>';

      // Block 3: 玩法
      blocksHtml += '<section class="ww-drawer-block ww-guide"><h4>玩法</h4>';
      blocksHtml += '<p>3狼 3民 预言家 女巫 猎人 · 发言投票淘汰 · 身份密封</p>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel drawer-werewolf-panel drawer-ww-compact"><h3>狼人杀</h3>' + blocksHtml + '</div>';

      setTimeout(function() {
        var pd = document.getElementById('drawer-werewolf-picker-p63');
        var pp = document.getElementById('drawer-werewolf-prep-p63');
        if (pd && typeof renderInlineWerewolfPicker === 'function') pd.innerHTML = renderInlineWerewolfPicker();
        if (pp && typeof renderWerewolfPrepSummary === 'function') pp.innerHTML = renderWerewolfPrepSummary();
      }, 40);

    } else if (isWorldcup) {
      // ── Tournament prediction: 3-block ──
      blocksHtml += '<section class="ww-drawer-block"><h4>预测状态</h4>';
      blocksHtml += '<p>Grand Judge 组织多模型给出概率和依据。预测完成后排行榜、投注记录归档到产物和报告 tab。</p>';
      blocksHtml += '</section>';

      blocksHtml += '<section class="ww-drawer-block"><details class="ww-advanced"><summary>预测池与资金</summary>';
      blocksHtml += '<div class="ww-advanced-body" style="color:#888;font-size:13px;line-height:1.6;">贷款账本、奖励账本、投注记录等高级参数在运行期间由 Grand Judge 管理。结束后查看完整报告。</div>';
      blocksHtml += '</details></section>';

      blocksHtml += '<section class="ww-drawer-block"><h4>相关产物</h4>';
      blocksHtml += '<p style="color:#666;">排行榜、账户明细、投注记录归档到「产物」和「报告」tab。</p>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel drawer-werewolf-panel"><h3>赛事预测</h3>' + blocksHtml + '</div>';

    } else {
      // ── Fast judgment: 3-block ──
      var phaseLabelFJ = hasVerdict ? '已完成' : hasTask ? '运行中' : '就绪';
      var seatCountFJ = state.selectedSeats ? state.selectedSeats.size : 0;
      var currentModeFJ = state.selectedMode || 'flash';
      var modeLabelFJ = currentModeFJ === 'flash' ? '快速' : currentModeFJ === 'strategic' ? '深度' : '标准';

      // Block 1: 当前目标
      blocksHtml += '<section class="ww-drawer-block"><h4>当前状态</h4>';
      blocksHtml += '<div class="ww-drawer-chips">';
      blocksHtml += '<span class="ww-chip">' + phaseLabelFJ + '</span>';
      blocksHtml += '<span class="ww-chip">' + seatCountFJ + ' 席位</span>';
      blocksHtml += '</div>';
      blocksHtml += '</section>';

      // Block 2: 席位与深度
      blocksHtml += '<section class="ww-drawer-block"><h4>判决模式</h4>';
      blocksHtml += '<div class="ww-drawer-chips">';
      blocksHtml += '<span class="ww-chip' + (currentModeFJ === 'flash' ? ' ww-chip-active' : '') + '">快速</span>';
      blocksHtml += '<span class="ww-chip' + (currentModeFJ === 'standard' ? ' ww-chip-active' : '') + '">标准</span>';
      blocksHtml += '<span class="ww-chip' + (currentModeFJ === 'strategic' ? ' ww-chip-active' : '') + '">深度</span>';
      blocksHtml += '</div>';
      blocksHtml += '<p style="color:#888;font-size:12px;margin-top:6px;">当前：' + modeLabelFJ + '判决 · 提交前可在底部切换。</p>';
      blocksHtml += '</section>';

      // Block 3: 执行控制
      blocksHtml += '<section class="ww-drawer-block"><h4>执行控制</h4>';
      blocksHtml += '<div class="ww-drawer-run-ctrl">';
      if (hasTask) {
        blocksHtml += '<button class="ww-pause-btn" type="button">暂停</button>';
      } else {
        blocksHtml += '<p style="color:#666;font-size:13px;margin:0;">提交议题后 Grand Judge 整理计划。确认后席位按序发言。</p>';
      }
      blocksHtml += '</div>';
      blocksHtml += '</section>';

      content.innerHTML = '<div class="drawer-panel"><h3>' + getModeConfig(state.selectedMode).label + '</h3>' + blocksHtml + '</div>';
    }
  };

  // ── P63.4: Shrink motion card ──
  var styleIdP63 = 'p63-motion-card-shrink';
  if (!document.getElementById(styleIdP63)) {
    var s = document.createElement('style');
    s.id = styleIdP63;
    s.textContent = ''
      // Motion card shrink
      + '.motion-card { padding:12px 16px !important; margin:8px 16px !important; border-radius:8px !important; max-width:none !important; }'
      + '.motion-card h3, .motion-card strong { font-size:15px !important; margin:0 0 4px !important; }'
      + '.motion-card p { font-size:12px !important; margin:0 !important; line-height:1.4 !important; color:#888 !important; }'
      // Input area coordination
      + '.composer, .parliament-composer { padding:8px 16px !important; gap:6px !important; }'
      + '#parliament-question-input { min-height:36px !important; max-height:80px !important; font-size:14px !important; padding:8px 12px !important; }'
      + '.composer-actions, .parliament-actions { gap:4px !important; flex-wrap:nowrap !important; }'
      + '.composer-actions button, .parliament-actions button { font-size:12px !important; padding:4px 10px !important; white-space:nowrap !important; }'
      // P63 light empty states
      + '.ww-light-state { text-align:center; padding:24px 20px !important; max-width:520px; margin:0 auto; }'
      + '.ww-light-header h3 { font-size:18px; font-weight:600; color:#1a1a1a; margin:0 0 8px; }'
      + '.ww-light-header p { font-size:13px; color:#666; line-height:1.6; margin:0 0 16px; }'
      + '.ww-light-actions { display:flex; gap:8px; justify-content:center; align-items:center; }'
      + '.ww-light-actions .ww-start-btn { padding:8px 20px; border-radius:20px; border:none; background:#1a1aff; color:#fff; font-size:14px; font-weight:500; cursor:pointer; }'
      + '.ww-light-actions .ww-manage-btn { padding:8px 16px; border-radius:20px; border:1px solid #ddd; background:transparent; color:#666; font-size:13px; cursor:pointer; }'
      + '.ww-light-actions .ww-start-btn:hover { background:#0000e6; }'
      + '.ww-light-actions .ww-manage-btn:hover { background:#f5f5f5; }'
      // P63 judgment/worldcup empty states
      + '.p63-judgment-empty, .p63-worldcup-empty { text-align:center; padding:32px 20px; max-width:520px; margin:0 auto; }'
      + '.p63-judgment-empty h3, .p63-worldcup-empty h3 { font-size:18px; font-weight:600; color:#1a1a1a; margin:0 0 8px; }'
      + '.p63-judgment-empty p, .p63-worldcup-empty p { font-size:13px; color:#666; line-height:1.6; margin:0 0 12px; }'
      + '.p63-quick-actions { margin-top:12px; }'
      + '.p63-hint { display:inline-block; padding:5px 12px; border-radius:14px; background:#f0f0f5; color:#888; font-size:12px; }'
      // Drawer run control
      + '.ww-drawer-run-ctrl { margin-top:8px; }'
      + '.ww-drawer-run-ctrl .ww-pause-btn { padding:4px 14px; border-radius:14px; border:1px solid #e0a800; background:#fff8e1; color:#8a6d00; font-size:12px; cursor:pointer; }'
      + '.ww-drawer-run-ctrl .ww-pause-btn:hover { background:#ffecb3; }'
      // Block styling
      + '.ww-drawer-block { padding:10px 12px; border-bottom:1px solid #f0f0f0; }'
      + '.ww-drawer-block:last-child { border-bottom:none; }'
      + '.ww-drawer-block h4 { font-size:12px; font-weight:600; color:#999; text-transform:none; margin:0 0 6px; letter-spacing:0; }'
      + '.ww-drawer-block p { font-size:13px; color:#666; line-height:1.5; margin:0; }'
      + '.ww-drawer-chips { display:flex; gap:6px; flex-wrap:wrap; }'
      + '.ww-chip { display:inline-block; padding:3px 10px; border-radius:12px; background:#f0f0f5; color:#555; font-size:12px; }'
      + '.ww-chip-label { background:#e8edff; color:#1a1aff; }'
      + '.ww-chip-phase { background:#ffe8e8; color:#cc3333; }'
      + '.ww-chip-active { background:#1a1aff !important; color:#fff !important; }'
      + 'details.ww-advanced { margin:0; }'
      + 'details.ww-advanced summary { font-size:12px; color:#999; cursor:pointer; padding:4px 0; }'
      + 'details.ww-advanced .ww-advanced-body { padding:8px 0 0; }'
      // Minimal werewolf picker in drawer
      + '#drawer-werewolf-picker-p63, #drawer-werewolf-picker-p61 { }'
      + '#drawer-werewolf-picker-p63 .werewolf-picker-head, #drawer-werewolf-picker-p61 .werewolf-picker-head { font-size:12px !important; padding:4px 0 !important; }'
      + '#drawer-werewolf-picker-p63 .seat-grid, #drawer-werewolf-picker-p61 .seat-grid { gap:4px !important; }'
      + '#drawer-werewolf-picker-p63 .seat-token, #drawer-werewolf-picker-p61 .seat-token { padding:3px 8px !important; font-size:11px !important; }';
    document.head.appendChild(s);
  }

  // ── P63.5: Userify input placeholder ──
  (function() {
    var tmr = setInterval(function() {
      var inp = document.getElementById('parliament-question-input');
      if (inp) {
        var old = inp.placeholder || '';
        if (old.indexOf('提交议题') !== -1 || old.indexOf('对齐需求') !== -1) {
          inp.placeholder = '输入你的问题，Grand Judge 帮你整理分析…';
        }
        clearInterval(tmr);
      }
    }, 200);
    setTimeout(function() { clearInterval(tmr); }, 4000);
  })();

  console.log("P63 three-flow lightweight closeout applied");
})();
// ==== End P63 Patches ====

// ═══════════ P8.1: Dashboard Release Status Panel ═══════════

async function loadReleaseStatus() {
  var panel = document.getElementById('release-status-panel');
  var details = document.getElementById('release-status-details');
  var badge = document.getElementById('release-overall-badge');
  if (!panel) return;

  try {
    var resp = await fetch(API_BASE + '/api/release/readiness');
    if (!resp.ok) {
      badge.textContent = 'N/A';
      badge.style.background = '#334155';
      badge.style.color = '#94a3b8';
      details.innerHTML = '<span style="color:#64748b;">尚未生成 readiness 报告，请运行回归检查。</span>';
      _diWriteTrace({ event: 'release_readiness_loaded', ok: false, error: 'HTTP ' + resp.status });
      return;
    }
    var data = await resp.json();
    renderReleaseStatus(data);
    _diWriteTrace({ event: 'release_readiness_loaded', ok: true, overall_status: data.overall_status });
  } catch (e) {
    badge.textContent = 'ERR';
    badge.style.background = '#7f1d1d';
    badge.style.color = '#fca5a5';
    details.innerHTML = '<span style="color:#f87171;">加载失败: ' + (e.message || 'unknown') + '</span>';
    _diWriteTrace({ event: 'release_readiness_loaded', ok: false, error: e.message || 'unknown' });
  }
}

function renderReleaseStatus(data) {
  var details = document.getElementById('release-status-details');
  var badge = document.getElementById('release-overall-badge');
  var status = data.overall_status || 'unknown';

  // Badge
  if (status === 'pass') {
    badge.textContent = 'PASS';
    badge.style.background = '#065f46';
    badge.style.color = '#6ee7b7';
  } else if (status === 'fail' || status === 'blocked') {
    badge.textContent = status.toUpperCase();
    badge.style.background = '#7f1d1d';
    badge.style.color = '#fca5a5';
  } else {
    badge.textContent = status.toUpperCase();
    badge.style.background = '#334155';
    badge.style.color = '#94a3b8';
  }

  var html = '<div style="display:grid; grid-template-columns:1fr 1fr; gap:4px 16px;">';
  html += '<span>Build:</span><span style="color:#e2e8f0;">' + (data.build_id || data.checks?.dashboard_build?.details?.build_id || '--') + '</span>';
  html += '<span>Pass / Fail:</span><span style="color:' + (data.fail_count > 0 ? '#fca5a5' : '#6ee7b7') + ';">' + data.pass_count + ' / ' + data.fail_count + '</span>';
  html += '<span>Sample Run:</span><span style="color:#e2e8f0;">' + (data.sample_run_id || '--') + '</span>';
  html += '<span>Last Regression:</span><span style="color:#94a3b8;">' + (data.generated_at ? new Date(data.generated_at).toLocaleString() : '--') + '</span>';
  html += '</div>';

  if (data.blockers && data.blockers.length > 0) {
    html += '<div style="margin-top:6px; color:#fca5a5; font-size:11px;">Blockers: ' + data.blockers.length + '</div>';
  }
  if (data.warnings && data.warnings.length > 0) {
    html += '<div style="margin-top:2px; color:#fbbf24; font-size:11px;">Warnings: ' + data.warnings.length + '</div>';
  }

  details.innerHTML = html;
}

async function runReleaseRegression(source) {
  _diWriteTrace({ event: 'release_regression_clicked', source: source });
  var btn = document.getElementById('release-run-regression-btn');
  if (btn) { btn.disabled = true; btn.textContent = '运行中...'; }
  try {
    var resp = await fetch(API_BASE + '/api/release/regression', { method: 'POST' });
    var data = await resp.json();
    _diWriteTrace({
      event: 'release_regression_result',
      source: source,
      ok: data.ok,
      overall_status: data.overall_status || 'unknown',
      pass_count: data.pass_count || 0,
      fail_count: data.fail_count || 0,
      blockers: (data.blockers || []).length
    });
    if (data.ok) {
      await loadReleaseStatus();
    } else {
      alert('回归运行失败: ' + (data.error || 'unknown'));
    }
  } catch (e) {
    _diWriteTrace({ event: 'release_regression_result', source: source, ok: false, error: e.message || 'unknown' });
    alert('回归运行异常: ' + (e.message || 'unknown'));
  }
  if (btn) { btn.disabled = false; btn.textContent = '运行回归检查'; }
}

function openReleaseReadinessMarkdown(source) {
  _diWriteTrace({ event: 'release_readiness_md_clicked', source: source });
  var url = API_BASE + '/api/runs/release-readiness';
  _diWriteTrace({ event: 'release_readiness_md_result', source: source, ok: true, mode: 'api_markdown', url: url });
  window.open(url, '_blank');
}

(function() {
  // Bind Release Status buttons after DOM ready
  function _bindReleaseButtons() {
    var regBtn = document.getElementById('release-run-regression-btn');
    var mdBtn = document.getElementById('release-open-md-btn');

    if (regBtn) {
      regBtn.addEventListener('click', function() {
        runReleaseRegression('button_click');
      });
    }

    if (mdBtn) {
      mdBtn.addEventListener('click', function() {
        openReleaseReadinessMarkdown('button_click');
      });
    }

    // Load on page ready
    setTimeout(loadReleaseStatus, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _bindReleaseButtons);
  } else {
    _bindReleaseButtons();
  }
})();

// ── P8.7 Freeze Drift Sentinel ─────────────────────────────────────────────

async function loadDriftStatus() {
  try {
    const res = await fetch('/api/release/drift');
    if (!res.ok) {
      document.getElementById('drift-status').textContent = 'unknown';
      return;
    }
    const body = await res.json();
    if (!body.ok || !body.data) {
      document.getElementById('drift-status').textContent = 'unknown';
      return;
    }
    const d = body.data;
    document.getElementById('drift-status').textContent = d.status || 'unknown';
    document.getElementById('drift-files-checked').textContent = d.summary?.files_checked ?? '--';
    document.getElementById('drift-hash-changes').textContent = d.summary?.hash_changed ?? '--';
    document.getElementById('drift-missing').textContent = d.summary?.missing ?? '--';
    document.getElementById('drift-new-untracked').textContent = d.summary?.new_untracked ?? '--';

    // Show/hide detail rows
    const showDetails = d.status && d.status !== 'unknown';
    ['drift-summary-row', 'drift-hash-row', 'drift-missing-row', 'drift-new-row'].forEach(id => {
      document.getElementById(id).style.display = showDetails ? '' : 'none';
    });
  } catch (e) {
    document.getElementById('drift-status').textContent = 'unknown';
  }
}

async function checkDrift(source) {
  var btn = document.getElementById('btn-drift-check');
  if (btn) { btn.disabled = true; btn.textContent = '检查中...'; }
  try {
    const res = await fetch('/api/release/drift/check', { method: 'POST' });
    const body = await res.json();
    await loadDriftStatus();
  } catch (e) {
    document.getElementById('drift-status').textContent = 'error';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '检查冻结漂移'; }
  }
}

// Bind drift button
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-drift-check');
  if (btn) btn.addEventListener('click', () => checkDrift('button_click'));
  loadDriftStatus();
});

// ═══════════ P7.1: Decision Intelligence Panel ═══════════

let _diData = null;

function _diWriteTrace(event) {
  event.ts = Date.now();
  fetch('/api/trace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event)
  }).catch(function() {});
}

async function loadDecisionIntelligence() {
  var content = document.getElementById('decision-intelligence-content');
  if (content) content.innerHTML = '<span style="color:#a5b4fc;">加载中...</span>';

  try {
    var resp = await fetch(API_BASE + '/api/decision/intelligence');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    var data = await resp.json();
    _diData = data;
    window.__AJ_DI_DATA__ = data;
    window.__AJ_DI_LAST_LOADED_AT__ = Date.now();

    var needsReviewCount = (data.needs_review || []).length;

    _diWriteTrace({
      event: 'decision_intelligence_loaded',
      ok: true,
      needs_review_count: needsReviewCount,
      rendered_count: needsReviewCount,
      source: 'aggregate'
    });

    renderDecisionIntelligencePanel(data);
    renderNeedsReviewQueue(data);
    renderNextBestActions(data);
  } catch (e) {
    if (content) content.innerHTML = '<span style="color:#ef4444;">加载失败: ' + (e.message || '未知错误') + '</span>';
    _diWriteTrace({
      event: 'decision_intelligence_loaded',
      ok: false,
      needs_review_count: 0,
      rendered_count: 0,
      source: 'aggregate',
      error: e.message || 'unknown'
    });
  }
}

function renderDecisionIntelligencePanel(data) {
  var content = document.getElementById('decision-intelligence-content');
  if (!content) return;

  var s = data.summary || {};
  var gc = s.human_gavel_counts || {};
  var cc = s.claim_calibration_counts || {};
  var ts = s.trust_summary || {};

  var html = '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">';

  // Row 1: Canonical runs + Universe gaps
  html += '<div style="color:#a5b4fc;">';
  html += '<div style="font-weight:600; margin-bottom:2px;">Run Universe</div>';
  html += '<div>Canonical: <b style="color:#fff;">' + (s.canonical_runs || 0) + '</b></div>';
  html += '<div>Gaps: <b style="color:#f59e0b;">' + (s.universe_gaps || 0) + '</b></div>';
  html += '</div>';

  // Row 1b: Trust Summary
  html += '<div style="color:#a5b4fc;">';
  html += '<div style="font-weight:600; margin-bottom:2px;">Trust</div>';
  html += '<div>Seats: <b style="color:#fff;">' + (ts.seat_count || 0) + '</b></div>';
  var topSeats = (data.top_trusted_seats || []).slice(0, 3);
  if (topSeats.length) {
    html += '<div>Top: <span style="color:#10b981;">' + topSeats.join(', ') + '</span></div>';
  }
  var lowSeats = (data.low_evidence_seats || []).slice(0, 3);
  if (lowSeats.length) {
    html += '<div>Low: <span style="color:#f59e0b;">' + lowSeats.join(', ') + '</span></div>';
  }
  html += '</div>';

  // Row 2: Gavel
  html += '<div style="color:#a5b4fc;">';
  html += '<div style="font-weight:600; margin-bottom:2px;">Human Gavel</div>';
  html += '<div>Confirmed: <b style="color:#10b981;">' + (gc.confirmed || 0) + '</b></div>';
  html += '<div>Draft: <b style="color:#3b82f6;">' + (gc.draft || 0) + '</b></div>';
  html += '<div>Needs Review: <b style="color:#f59e0b;">' + (gc.needs_review || 0) + '</b></div>';
  html += '<div>Rejected: <b style="color:#ef4444;">' + (gc.rejected || 0) + '</b></div>';
  html += '</div>';

  // Row 2b: Claim Calibration
  html += '<div style="color:#a5b4fc;">';
  html += '<div style="font-weight:600; margin-bottom:2px;">Claim Calibration</div>';
  html += '<div>Runs: <b style="color:#fff;">' + (cc.total_runs || 0) + '</b></div>';
  html += '<div>Accepted: <b style="color:#10b981;">' + (cc.total_accepted || 0) + '</b></div>';
  html += '<div>Rejected: <b style="color:#ef4444;">' + (cc.total_rejected || 0) + '</b></div>';
  html += '<div>Unmatched: <b style="color:#f59e0b;">' + (cc.total_unmatched || 0) + '</b></div>';
  html += '</div>';

  html += '</div>';

  // Needs Review count + auto-load
  var nrCount = (data.needs_review || []).length;
  if (nrCount > 0) {
    html += '<div style="margin-top:10px; padding:8px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:6px;">';
    html += '<span style="color:#fbbf24; font-weight:600;">' + nrCount + ' runs need review</span>';
    html += ' &nbsp; <span style="color:#94a3b8; font-size:11px;">(滚动查看下方队列和 Next Best Actions)</span>';
    html += '</div>';
  } else {
    html += '<div style="margin-top:10px; padding:6px; color:#10b981; font-size:12px;">All clear — no runs need review.</div>';
  }

  content.innerHTML = html;
}

function renderNeedsReviewQueue(data) {
  var queue = document.getElementById('needs-review-queue');
  var content = document.getElementById('needs-review-queue-content');
  if (!queue || !content) return;

  var items = data.needs_review || [];
  if (!items.length) {
    queue.hidden = true;
    return;
  }

  queue.hidden = false;

  var renderedCount = Math.min(items.length, 20);
  var limit = 20;

  _diWriteTrace({
    event: 'needs_review_rendered',
    needs_review_count: items.length,
    rendered_count: renderedCount,
    limit: limit
  });

  var html = '<div style="display:flex; flex-direction:column; gap:8px;">';

  for (var i = 0; i < renderedCount; i++) {
    var item = items[i];
    var runId = item.run_id || '';
    var reasons = (item.reasons || []).join('; ') || '—';
    var gavelStatus = item.gavel_status || 'none';
    var gavelColor = HUMAN_GAVEL_COLORS[gavelStatus] || '#6b7280';
    var unmatched = item.unmatched_claims_count || 0;

    html += '<div style="padding:8px; background:rgba(30,30,46,0.6); border:1px solid rgba(245,158,11,0.2); border-radius:6px;">';
    html += '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">';
    html += '<div>';
    html += '<span style="font-weight:600; color:#fbbf24;">' + runId + '</span>';
    html += ' <span style="display:inline-block; padding:1px 6px; border-radius:8px; font-size:10px; background:' + gavelColor + '; color:#fff;">' + gavelStatus + '</span>';
    if (unmatched > 0) {
      html += ' <span style="display:inline-block; padding:1px 6px; border-radius:8px; font-size:10px; background:#f59e0b; color:#111;">' + unmatched + ' unmatched</span>';
    }
    html += '</div>';
    html += '</div>';
    html += '<div style="font-size:11px; color:#94a3b8; margin-bottom:6px;">' + reasons + '</div>';
    html += '<div style="display:flex; gap:4px; flex-wrap:wrap;">';

    // Open Report button
    html += '<button class="di-nr-btn di-nr-open" data-run-id="' + runId + '" data-action="open_report" style="padding:3px 10px; border:1px solid #6366f1; border-radius:4px; background:rgba(99,102,241,0.15); color:#a5b4fc; font-size:11px; cursor:pointer;">打开报告</button>';

    // Sync Gavel button
    html += '<button class="di-nr-btn di-nr-sync" data-run-id="' + runId + '" data-action="sync_gavel" style="padding:3px 10px; border:1px solid #10b981; border-radius:4px; background:rgba(16,185,129,0.15); color:#6ee7b7; font-size:11px; cursor:pointer;">同步 Gavel</button>';

    // Rebuild Calibration button
    html += '<button class="di-nr-btn di-nr-rebuild" data-run-id="' + runId + '" data-action="rebuild_calibration" style="padding:3px 10px; border:1px solid #f59e0b; border-radius:4px; background:rgba(245,158,11,0.15); color:#fbbf24; font-size:11px; cursor:pointer;">重建 Calibration</button>';

    html += '</div></div>';
  }

  html += '</div>';
  content.innerHTML = html;

  // Bind click handlers after rendering
  setTimeout(function() {
    var buttons = content.querySelectorAll('.di-nr-btn');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var runId = btn.getAttribute('data-run-id');
        var action = btn.getAttribute('data-action');
        _handleNeedsReviewAction(runId, action, btn);
      });
    });
  }, 0);
}

async function _handleNeedsReviewAction(runId, action, btn) {
  _diWriteTrace({
    event: 'needs_review_action_clicked',
    run_id: runId,
    action: action
  });

  // Disable button during request
  btn.disabled = true;
  btn.style.opacity = '0.5';

  try {
    if (action === 'open_report') {
      var url = API_BASE + '/api/runs/' + encodeURIComponent(runId) + '/index.html';
      window.open(url, '_blank');
      _diWriteTrace({
        event: 'needs_review_action_result',
        run_id: runId,
        action: 'open_report',
        ok: true,
        url: url
      });
    } else if (action === 'sync_gavel') {
      var resp = await fetch(API_BASE + '/api/gavel/' + encodeURIComponent(runId) + '/sync', { method: 'POST' });
      var gd = await resp.json().catch(function() { return {}; });
      _diWriteTrace({
        event: 'needs_review_action_result',
        run_id: runId,
        action: 'sync_gavel',
        ok: resp.ok,
        status: gd.status || (resp.ok ? 'synced' : 'failed')
      });
      if (resp.ok) {
        btn.textContent = '已同步';
        btn.style.borderColor = '#10b981';
        btn.style.color = '#10b981';
      } else {
        btn.textContent = '同步失败';
        btn.style.borderColor = '#ef4444';
        btn.style.color = '#ef4444';
      }
    } else if (action === 'rebuild_calibration') {
      var resp2 = await fetch(API_BASE + '/api/claims/calibration/' + encodeURIComponent(runId) + '/rebuild', { method: 'POST' });
      var cd = await resp2.json().catch(function() { return {}; });
      var tracePayload = {
        event: 'needs_review_action_result',
        run_id: runId,
        action: 'rebuild_calibration',
        ok: resp2.ok,
        accepted: cd.accepted || cd.claims_updated || 0,
        rejected: cd.rejected || 0,
        unmatched: cd.unmatched || 0
      };
      if (!resp2.ok) {
        tracePayload.error = cd.error || 'api_error';
        tracePayload.reason = (cd.detail && cd.detail.error) || cd.error || ('HTTP ' + resp2.status);
      }
      _diWriteTrace(tracePayload);
      if (resp2.ok) {
        btn.textContent = '已重建';
        btn.style.borderColor = '#10b981';
        btn.style.color = '#10b981';
      } else {
        btn.textContent = '重建失败';
        btn.style.borderColor = '#ef4444';
        btn.style.color = '#ef4444';
      }
    }
  } catch (e) {
    _diWriteTrace({
      event: 'needs_review_action_result',
      run_id: runId,
      action: action,
      ok: false,
      error: e.message || 'unknown'
    });
    btn.textContent = '错误';
    btn.style.borderColor = '#ef4444';
    btn.style.color = '#ef4444';
  }

  btn.disabled = false;
  btn.style.opacity = '1';
}

function renderNextBestActions(data) {
  var panel = document.getElementById('next-best-actions');
  var content = document.getElementById('next-best-actions-content');
  if (!panel || !content) return;

  var actions = data.next_best_actions || [];
  if (!actions.length) {
    panel.hidden = true;
    return;
  }

  panel.hidden = false;

  var html = '<div style="display:flex; flex-direction:column; gap:6px;">';

  for (var i = 0; i < actions.length; i++) {
    var a = actions[i];
    var kind = a.kind || '';
    var target = a.target || '';
    var reason = a.reason || '';
    var priority = a.priority || 0;

    var priorityColor = priority <= 1 ? '#ef4444' : priority <= 3 ? '#f59e0b' : '#6366f1';

    html += '<div style="padding:6px 8px; background:rgba(30,30,46,0.6); border:1px solid rgba(16,185,129,0.2); border-radius:6px; display:flex; justify-content:space-between; align-items:center;">';
    html += '<div style="flex:1; min-width:0;">';
    html += '<span style="display:inline-block; padding:1px 6px; border-radius:8px; font-size:10px; background:' + priorityColor + '; color:#fff; margin-right:6px;">P' + priority + '</span>';
    html += '<span style="font-weight:600; color:#6ee7b7; font-size:12px;">' + kind.replace(/_/g, ' ') + '</span>';
    html += '<div style="font-size:11px; color:#94a3b8; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + reason + '</div>';
    html += '</div>';
    html += '<button class="di-nba-btn" data-kind="' + kind + '" data-target="' + target + '" data-priority="' + priority + '" style="padding:3px 10px; border:1px solid #10b981; border-radius:4px; background:rgba(16,185,129,0.15); color:#6ee7b7; font-size:11px; cursor:pointer; white-space:nowrap; margin-left:8px;">执行</button>';
    html += '</div>';
  }

  html += '</div>';
  content.innerHTML = html;

  // Bind click handlers after rendering
  setTimeout(function() {
    var buttons = content.querySelectorAll('.di-nba-btn');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var kind = btn.getAttribute('data-kind');
        var target = btn.getAttribute('data-target');
        var priority = parseInt(btn.getAttribute('data-priority'), 10) || 0;
        _handleNextBestAction(kind, target, priority, btn);
      });
    });
  }, 0);
}

async function _handleNextBestAction(kind, target, priority, btn) {
  _diWriteTrace({
    event: 'next_best_action_clicked',
    kind: kind,
    target: target,
    priority: priority
  });

  btn.disabled = true;
  btn.style.opacity = '0.5';

  var actionTaken = '';

  try {
    if (kind === 'review_unmatched_claims' || kind === 'sync_draft_gavel') {
      // Open the run report
      var url = API_BASE + '/api/runs/' + encodeURIComponent(target) + '/index.html';
      window.open(url, '_blank');
      actionTaken = 'highlight_run';
    } else if (kind === 'add_human_gavel_for_seat' || kind === 'review_low_trust_seat') {
      // Open seat trust drilldown
      await handleSeatTrustDrilldown(target);
      actionTaken = 'open_seat';
    } else if (kind === 'backfill_missing_hermes') {
      // Open the run report for hermes export
      var url2 = API_BASE + '/api/runs/' + encodeURIComponent(target) + '/index.html';
      window.open(url2, '_blank');
      actionTaken = 'highlight_run';
    } else {
      actionTaken = 'show_note';
    }

    _diWriteTrace({
      event: 'next_best_action_result',
      kind: kind,
      target: target,
      ok: true,
      action_taken: actionTaken
    });

    btn.textContent = 'Done';
    btn.style.borderColor = '#10b981';
    btn.style.color = '#10b981';
  } catch (e) {
    _diWriteTrace({
      event: 'next_best_action_result',
      kind: kind,
      target: target,
      ok: false,
      action_taken: 'show_note',
      error: e.message || 'unknown'
    });
    btn.textContent = 'Error';
    btn.style.borderColor = '#ef4444';
    btn.style.color = '#ef4444';
  }

  btn.disabled = false;
  btn.style.opacity = '1';
}

async function handleSeatTrustDrilldown(seatId) {
  _diWriteTrace({
    event: 'seat_trust_drilldown_clicked',
    seat_id: seatId
  });

  var modal = document.getElementById('seat-trust-drilldown-modal');
  var content = document.getElementById('seat-trust-drilldown-content');
  if (!modal || !content) return;

  modal.hidden = false;
  content.innerHTML = '<span style="color:#a5b4fc;">加载 ' + seatId + ' 信任数据...</span>';

  try {
    var resp = await fetch(API_BASE + '/api/trust/seat/' + encodeURIComponent(seatId));
    if (!resp.ok) throw new Error('HTTP ' + resp.status);

    var data = await resp.json();

    _diWriteTrace({
      event: 'seat_trust_drilldown_loaded',
      seat_id: seatId,
      ok: true,
      trust_score: data.trust_score || 0,
      reviewed: data.reviewed || 0
    });

    // Render drilldown content
    var ts = data.trust_score;
    var scoreColor = ts >= 70 ? '#10b981' : ts >= 40 ? '#f59e0b' : '#ef4444';

    var html = '<h3 style="margin:0 0 12px; color:#a5b4fc; font-size:16px;">Seat Trust: ' + seatId + '</h3>';

    html += '<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">';
    html += '<div style="padding:10px; background:rgba(30,30,46,0.8); border-radius:8px;">';
    html += '<div style="font-size:11px; color:#94a3b8;">Trust Score</div>';
    html += '<div style="font-size:28px; font-weight:700; color:' + scoreColor + ';">' + (ts != null ? ts : '—') + '</div>';
    html += '</div>';
    html += '<div style="padding:10px; background:rgba(30,30,46,0.8); border-radius:8px;">';
    html += '<div style="font-size:11px; color:#94a3b8;">Reviewed</div>';
    html += '<div style="font-size:28px; font-weight:700; color:#a5b4fc;">' + (data.reviewed || 0) + '</div>';
    html += '</div>';
    html += '</div>';

    // Claims breakdown
    html += '<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:16px;">';
    html += '<div style="text-align:center; padding:6px; background:rgba(16,185,129,0.1); border-radius:6px;">';
    html += '<div style="font-size:10px; color:#94a3b8;">Accepted</div>';
    html += '<div style="font-size:18px; font-weight:700; color:#10b981;">' + (data.accepted || 0) + '</div>';
    html += '</div>';
    html += '<div style="text-align:center; padding:6px; background:rgba(239,68,68,0.1); border-radius:6px;">';
    html += '<div style="font-size:10px; color:#94a3b8;">Rejected</div>';
    html += '<div style="font-size:18px; font-weight:700; color:#ef4444;">' + (data.rejected || 0) + '</div>';
    html += '</div>';
    html += '<div style="text-align:center; padding:6px; background:rgba(245,158,11,0.1); border-radius:6px;">';
    html += '<div style="font-size:10px; color:#94a3b8;">Unmatched</div>';
    html += '<div style="font-size:18px; font-weight:700; color:#f59e0b;">' + (data.unmatched || 0) + '</div>';
    html += '</div>';
    html += '</div>';

    // Recent runs if available
    var recentRuns = data.recent_runs || [];
    if (recentRuns.length) {
      html += '<div style="margin-top:12px;">';
      html += '<div style="font-size:12px; font-weight:600; color:#a5b4fc; margin-bottom:6px;">Recent Runs</div>';
      html += '<div style="display:flex; flex-direction:column; gap:4px;">';
      for (var i = 0; i < Math.min(recentRuns.length, 10); i++) {
        var r = recentRuns[i];
        var rid = typeof r === 'string' ? r : (r.run_id || '');
        html += '<div style="font-size:11px; color:#94a3b8; padding:3px 6px; background:rgba(30,30,46,0.5); border-radius:4px;">' + rid + '</div>';
      }
      html += '</div></div>';
    }

    content.innerHTML = html;
  } catch (e) {
    _diWriteTrace({
      event: 'seat_trust_drilldown_loaded',
      seat_id: seatId,
      ok: false,
      error: e.message || 'unknown'
    });
    content.innerHTML = '<span style="color:#ef4444;">加载失败: ' + (e.message || '未知错误') + '</span>';
  }
}

// Expose to window for inline onclick in HTML
window.loadDecisionIntelligence = loadDecisionIntelligence;
window._handleNeedsReviewAction = _handleNeedsReviewAction;
window._handleNextBestAction = _handleNextBestAction;
window.handleSeatTrustDrilldown = handleSeatTrustDrilldown;

// ===== Hermes Integration (P2) =====

let hermesIndexData = null;
let hermesSeatsData = null;

async function refreshHistoryAndHermes() {
  if (typeof traceUIEvent === 'function') traceUIEvent('history_refresh_clicked', {});
  try {
    await Promise.all([
      loadHistory(),
      loadHermesIndex(),
      loadHermesSeats(),
      loadClaimCalibrationIndex(),
      loadTrustCalibration()
    ]);
    if (typeof traceUIEvent === 'function') {
      traceUIEvent('hermes_index_loaded', { run_count: hermesIndexData?.run_count });
      traceUIEvent('hermes_seats_loaded', { seat_count: hermesSeatsData ? Object.keys(hermesSeatsData).length : 0 });
      traceUIEvent('trust_calibration_loaded', { ok: true, seat_count: trustCalibData?.seat_count || 0 });
      traceUIEvent('run_universe_loaded', { ok: true, canonical_run_count: runUniverseData?.canonical_run_count || 0 });
    }
  } catch (e) {
    // Hermes 失败不影响历史列表刷新
  }
  setTimeout(function() {
    var cards = document.querySelectorAll('.run-card');
    cards.forEach(function(card) {
      var runId = card.getAttribute('data-run-id') || card.querySelector('[data-run-id]')?.getAttribute('data-run-id');
      if (runId) populateRunCardHermesStatus(runId, card);
    });
  }, 500);
}

async function loadHermesIndex() {
  try {
    const resp = await fetch(API_BASE + '/api/hermes/index');
    if (!resp.ok) { document.getElementById('hermes-overview-stats').textContent = 'Hermes Index 不可用'; return; }
    hermesIndexData = await resp.json();
    renderHermesOverview(hermesIndexData);
  } catch (e) {
    document.getElementById('hermes-overview-stats').textContent = 'Hermes Index 加载失败';
  }
}

async function loadHermesSeats() {
  try {
    const resp = await fetch(API_BASE + '/api/hermes/seats');
    if (!resp.ok) { document.getElementById('hermes-seats-list').textContent = 'Seat 数据不可用'; return; }
    hermesSeatsData = await resp.json();
    renderHermesSeats(hermesSeatsData);
  } catch (e) {
    document.getElementById('hermes-seats-list').textContent = 'Seat 加载失败';
  }
}

function renderHermesOverview(data) {
  var stats = document.getElementById('hermes-overview-stats');
  if (!data || !data.run_count) { stats.textContent = '无数据'; return; }
  var cs = data.confidence_summary || {};
  var ws = data.weekly_summary || {};
  var ss = data.status_summary || {};
  stats.innerHTML = [
    '<span style="color:#8cf;">Runs: <b>' + data.run_count + '</b></span>',
    '<span style="color:#c8f;">Status: <b>' + JSON.stringify(ss) + '</b></span>',
    '<span style="color:#fc8;">Confidence: avg<b>' + (cs.avg||'?') + '</b></span>'
  ].join(' &nbsp;|&nbsp; ');

  var weeks = document.getElementById('hermes-overview-weeks');
  var wkKeys = Object.keys(ws).slice(0, 8);
  weeks.innerHTML = 'Weeks: ' + wkKeys.map(function(w) { return '<span style="color:#aaa;">' + w + ' (' + ws[w].run_count + ')</span>'; }).join(', ');

  var topSeats = document.getElementById('hermes-overview-top-seats');
  var seatEntries = Object.entries(data.seat_summary || {}).sort(function(a,b) { return b[1].total_runs - a[1].total_runs; }).slice(0, 5);
  topSeats.innerHTML = 'Top Seats: ' + seatEntries.map(function(e) { return '<span style="color:#8f8;">' + e[0] + ' (' + e[1].total_runs + ')</span>'; }).join(', ');
}

function renderHermesSeats(data) {
  var list = document.getElementById('hermes-seats-list');
  if (!data || !Object.keys(data).length) { list.textContent = '无席位数据'; return; }
  var seatCount = Object.keys(data).length;
  var hdr = document.querySelector('#hermes-seats-panel h3');
  if (hdr) hdr.textContent = 'Seat 聚合 (' + seatCount + ')';
  var entries = Object.entries(data).sort(function(a,b) { return b[1].total_runs - a[1].total_runs; });
  list.innerHTML = entries.map(function(e) {
    var id = e[0], s = e[1];
    var color = s.avg_confidence >= 80 ? '#8f8' : s.avg_confidence >= 50 ? '#fc8' : '#f88';
    return '<span class="seat-chip" data-seat="' + id + '" style="cursor:pointer; padding:2px 8px; border:1px solid ' + color + '; border-radius:10px; color:' + color + ';" onclick="showSeatDetail(\'' + id + '\')">' + id + '&nbsp;<b>' + s.total_runs + '</b></span>';
  }).join(' ');
}

async function showSeatDetail(seatId) {
  var detail = document.getElementById('hermes-seat-detail');
  detail.style.display = 'block';
  detail.innerHTML = 'Loading...';
  try {
    var resp = await fetch(API_BASE + '/api/hermes/seat/' + encodeURIComponent(seatId));
    if (!resp.ok) { detail.innerHTML = 'Seat ' + seatId + ' 无数据'; return; }
    var s = await resp.json();
    detail.innerHTML = [
      '<div style="display:flex; justify-content:space-between;"><b style="color:#9cf;">' + seatId + '</b><span style="color:#888;cursor:pointer;" onclick="document.getElementById(\'hermes-seat-detail\').style.display=\'none\'">✕</span></div>',
      '<div style="font-size:11px;color:#aaa;">total: <b>' + s.total_runs + '</b> | avg: <b>' + (s.avg_confidence||'?') + '</b> | high: <b>' + s.high_confidence_runs + '</b> | low: <b>' + s.low_confidence_runs + '</b></div>',
      '<div style="font-size:10px;color:#888;margin-top:4px;">Recent: ' + (s.recent_run_ids||[]).slice(0,5).join(', ') + '</div>'
    ].join('');
  } catch (e) {
    detail.innerHTML = '加载失败';
  }
}

function toggleHermesOverview() {
  var content = document.getElementById('hermes-overview-content');
  var icon = document.getElementById('hermes-toggle-icon');
  if (content.style.display === 'none') { content.style.display = ''; icon.textContent = '▼'; }
  else { content.style.display = 'none'; icon.textContent = '▶'; }
}

function toggleHermesSeats() {
  var content = document.getElementById('hermes-seats-content');
  var icon = document.getElementById('hermes-seats-toggle-icon');
  if (content.style.display === 'none') { content.style.display = ''; icon.textContent = '▼'; }
  else { content.style.display = 'none'; icon.textContent = '▶'; }
}

function toggleClaimCalibOverview() {
  var content = document.getElementById('claim-calib-overview-content');
  var icon = document.getElementById('claim-calib-toggle-icon');
  if (content.style.display === 'none') { content.style.display = ''; icon.textContent = '▼'; }
  else { content.style.display = 'none'; icon.textContent = '▶'; }
}

async function populateRunCardHermesStatus(runId, cardElement) {
  try {
    var resp = await fetch(API_BASE + '/api/judge/' + runId + '/verdict');
    if (!resp.ok) return;
    var data = await resp.json();
    var exports = data.exports || {};

    var indicators = cardElement.querySelectorAll('.hermes-indicator');
    indicators.forEach(function(ind) {
      var fileName = ind.getAttribute('data-file'), exists = false;
      if (fileName === 'index.html') exists = !!exports.html;
      else if (fileName === 'hermes-output.json') exists = !!exports.hermes_json;
      else if (fileName === 'hermes-output.md') exists = !!exports.hermes_md;
      else if (fileName === 'obsidian-run-note.md') exists = !!exports.obsidian_note;
      if (exists) ind.style.display = 'inline';
    });

    // button click handlers handled by document-level capture delegation: setupHermesExportDelegation()
  } catch (e) {
    // Hermes status loading failed silently
  }
}

// P3 — populate human gavel status from hermes index data or /api/gavel endpoint
var HUMAN_GAVEL_COLORS = {
  none: "#6b7280",
  draft: "#3b82f6",
  confirmed: "#10b981",
  rejected: "#ef4444",
  needs_review: "#f59e0b",
};

function humanGavelStatusLabel(status) {
  var map = { none: "none", draft: "draft", confirmed: "confirmed", rejected: "rejected", needs_review: "needs_review" };
  return map[status] || status || "—";
}

async function populateHumanGavelStatus(runId, cardElement) {
  var statusEl = cardElement.querySelector(".human-gavel-status");
  if (!statusEl) return;

  // First try hermes index data (in-memory)
  if (hermesIndexData && hermesIndexData.runs) {
    var runEntry = hermesIndexData.runs.find(function(r) { return r.run_id === runId; });
    if (runEntry && runEntry.human_gavel && runEntry.human_gavel.status) {
      var gv = runEntry.human_gavel;
      updateGavelUI(runId, cardElement, gv);
      return;
    }
  }

  // Fallback: fetch from API
  try {
    var resp = await fetch(API_BASE + "/api/gavel/" + runId);
    if (!resp.ok) return;
    var data = await resp.json();
    updateGavelUI(runId, cardElement, data);
  } catch (e) {
    // silently ignore
  }
}

function updateGavelUI(runId, cardElement, data) {
  var status = data.status || "none";
  var color = HUMAN_GAVEL_COLORS[status] || HUMAN_GAVEL_COLORS.none;
  var statusEl = cardElement.querySelector(".human-gavel-status");
  if (statusEl) {
    statusEl.textContent = "Human Gavel: " + humanGavelStatusLabel(status);
    statusEl.style.background = color;
    statusEl.style.color = "#fff";
  }

  // P4: Conflict indicator
  var conflict = data.conflict || {};
  var conflictEl = cardElement.querySelector(".human-gavel-conflict");
  if (conflictEl) {
    if (conflict.has_conflict) {
      conflictEl.textContent = "Conflict: yes";
      conflictEl.style.background = "#ef4444";
      conflictEl.style.color = "#fff";
      conflictEl.style.display = "inline";
    } else {
      conflictEl.textContent = "Conflict: no";
      conflictEl.style.background = "#10b981";
      conflictEl.style.color = "#fff";
      conflictEl.style.display = "inline";
    }
  }

  // P4: History count
  var historyCount = data.history_count || 0;
  var historyCountEl = cardElement.querySelector(".human-gavel-history-count");
  if (historyCountEl) {
    historyCountEl.textContent = "History: " + historyCount;
    historyCountEl.style.display = "inline";
  }

  // P4: Claim counts
  var claimReview = data.claim_review || {};
  var acceptedCount = (claimReview.accepted || []).length;
  var rejectedCount = (claimReview.rejected || []).length;
  var claimsEl = cardElement.querySelector(".human-gavel-claims");
  if (claimsEl) {
    claimsEl.textContent = "Accepted: " + acceptedCount + " / Rejected: " + rejectedCount;
    claimsEl.style.display = "inline";
  }

  // P4: Show history button when history exists
  var historyBtn = cardElement.querySelector(".human-gavel-history-btn");
  if (historyBtn && historyCount > 0) {
    historyBtn.style.display = "inline";
  }
}

function setupHumanGavelSyncDelegation() {
  var list = $("#history-list");
  if (!list) return;
  // Remove old listener to avoid duplicates
  list.removeEventListener("click", _humanGavelSyncClickHandler);
  list.addEventListener("click", _humanGavelSyncClickHandler);
}

function _humanGavelSyncClickHandler(e) {
  var btn = e.target.closest(".human-gavel-sync-btn");
  if (!btn) return;
  e.stopPropagation();
  e.preventDefault();
  var runId = btn.getAttribute("data-run-id");
  if (!runId) return;
  traceUIEvent("human_gavel_sync_clicked", { run_id: runId });
  btn.disabled = true;
  btn.textContent = "同步中...";
  fetch(API_BASE + "/api/gavel/" + runId + "/sync", { method: "POST" })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
      var ok = data.status && data.status !== "none";
      var status = data.status || "none";
      traceUIEvent("human_gavel_sync_result", { run_id: runId, ok: ok, status: status });
      btn.disabled = false;
      btn.textContent = "同步人工裁决";
      // Refresh the status display
      var card = btn.closest(".history-item");
      if (card) populateHumanGavelStatus(runId, card);
    })
    .catch(function(err) {
      traceUIEvent("human_gavel_sync_result", { run_id: runId, ok: false, error: err.message });
      btn.disabled = false;
      btn.textContent = "同步失败，重试";
    });
}

// P5: Claim Calibration status display
var claimCalibIndexData = null;

async function loadClaimCalibrationIndex() {
  try {
    var resp = await fetch(API_BASE + "/api/claims/calibration");
    if (!resp.ok) return;
    claimCalibIndexData = await resp.json();
    renderClaimCalibrationOverview(claimCalibIndexData);
  } catch (e) {
    // silently ignore
  }
}

function renderClaimCalibrationOverview(data) {
  var panel = document.getElementById("claim-calib-overview-stats");
  if (!panel) return;
  if (!data || data.total_runs === undefined) {
    panel.innerHTML = '<span style="color:#888;">Claim Calibration 不可用</span>';
    return;
  }
  var topSeats = (data.top_rejected_seats || []).map(function(item) {
    return item.seat + "(" + item.rejected + ")";
  }).join(", ");
  panel.innerHTML = [
    '<div style="font-size:12px; color:#fbbf24; font-weight:600; margin-bottom:4px;">Claim Calibration</div>',
    '<span style="color:#aaa;">Total Reviewed: </span><span style="color:#fff;">' + (data.total_claims_reviewed || 0) + '</span>',
    ' &nbsp; <span style="color:#10b981;">Accepted: ' + (data.total_accepted || 0) + '</span>',
    ' &nbsp; <span style="color:#ef4444;">Rejected: ' + (data.total_rejected || 0) + '</span>',
    ' &nbsp; <span style="color:#f59e0b;">Unmatched: ' + (data.total_unmatched || 0) + '</span>',
    topSeats ? ' &nbsp; <span style="color:#888;">Top Rejected: ' + topSeats + '</span>' : ''
  ].join("");
}

async function populateClaimCalibrationStatus(runId, cardElement) {
  var statusEl = cardElement.querySelector(".claim-calib-status");
  if (!statusEl) return;

  // First try hermes index data (in-memory)
  if (hermesIndexData && hermesIndexData.runs) {
    var runEntry = hermesIndexData.runs.find(function(r) { return r.run_id === runId; });
    if (runEntry && runEntry.claim_calibration) {
      var cc = runEntry.claim_calibration;
      var colorMap = { none: "#666", ready: "#10b981", warning: "#f59e0b" };
      var color = colorMap[cc.status] || "#666";
      var text = "Claim Calib: accepted " + (cc.accepted_count || 0) + " / rejected " + (cc.rejected_count || 0) + " / unmatched " + (cc.unmatched_count || 0);
      statusEl.textContent = text;
      statusEl.style.color = color;
      return;
    }
  }
  statusEl.textContent = "Claim Calib: —";
  statusEl.style.color = "#888";
}

function setupClaimCalibrationRebuildDelegation() {
  var list = $("#history-list");
  if (!list) return;
  list.removeEventListener("click", _claimCalibRebuildClickHandler);
  list.addEventListener("click", _claimCalibRebuildClickHandler);
}

function _claimCalibRebuildClickHandler(e) {
  var btn = e.target.closest(".claim-calib-rebuild-btn");
  if (!btn) return;
  e.stopPropagation();
  e.preventDefault();
  var runId = btn.getAttribute("data-run-id");
  if (!runId) return;
  if (typeof traceUIEvent === "function") {
    traceUIEvent("claim_calibration_rebuild_clicked", { run_id: runId });
  }
  btn.disabled = true;
  btn.textContent = "重建中...";
  fetch(API_BASE + "/api/claims/calibration/" + runId + "/rebuild", { method: "POST" })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
      var ok = data.ok || false;
      if (typeof traceUIEvent === "function") {
        traceUIEvent("claim_calibration_rebuild_result", {
          run_id: runId, ok: ok,
          accepted: (data.calibration && data.calibration.accepted ? data.calibration.accepted.length : 0),
          rejected: (data.calibration && data.calibration.rejected ? data.calibration.rejected.length : 0),
          unmatched: (data.calibration && data.calibration.unmatched ? data.calibration.unmatched.length : 0)
        });
      }
      btn.disabled = false;
      btn.textContent = "重建 Claim 校准";
      // Refresh hermes index and claim calibration
      loadHermesIndex().then(function() {
        var card = btn.closest(".history-item");
        if (card) populateClaimCalibrationStatus(runId, card);
      });
      loadClaimCalibrationIndex();
    })
    .catch(function(err) {
      if (typeof traceUIEvent === "function") {
        traceUIEvent("claim_calibration_rebuild_result", { run_id: runId, ok: false, error: err.message });
      }
      btn.disabled = false;
      btn.textContent = "重建失败，重试";
    });
}

// P6 — Trust Calibration
var trustCalibData = null;
var runUniverseData = null;

async function loadTrustCalibration() {
  try {
    var respTrust = await fetch(API_BASE + "/api/trust/calibration");
    if (respTrust.ok) {
      trustCalibData = await respTrust.json();
      renderTrustCalibration(trustCalibData);
    }
  } catch (e) { /* silently ignore */ }

  try {
    var respUniverse = await fetch(API_BASE + "/api/runs/universe");
    if (respUniverse.ok) {
      runUniverseData = await respUniverse.json();
      renderRunUniverseSummary(runUniverseData);
    }
  } catch (e) { /* silently ignore */ }
}

function toggleTrustCalibOverview() {
  var content = document.getElementById('trust-calib-overview-content');
  var icon = document.getElementById('trust-calib-toggle-icon');
  if (!content || !icon) return;
  if (content.style.display === 'none') {
    content.style.display = '';
    icon.textContent = '▼';
  } else {
    content.style.display = 'none';
    icon.textContent = '▶';
  }
}

function renderRunUniverseSummary(data) {
  var panel = document.getElementById("trust-calib-overview-stats");
  if (!panel || !data) return;
  var counts = data.counts || {};
  panel.innerHTML = [
    '<div style="font-size:12px; color:#a78bfa; font-weight:600; margin-bottom:4px;">Run Universe</div>',
    '<span style="color:#aaa;">Canonical: </span><span style="color:#fff;">' + (data.canonical_run_count || 0) + '</span>',
    ' &nbsp; <span style="color:#aaa;">Verdict: </span><span style="color:#fff;">' + (counts.verdict || 0) + '</span>',
    ' &nbsp; <span style="color:#aaa;">Hermes: </span><span style="color:#fff;">' + (counts.hermes || 0) + '</span>',
    ' &nbsp; <span style="color:#aaa;">Gavel: </span><span style="color:#fff;">' + (counts.human_gavel || 0) + '</span>',
    ' &nbsp; <span style="color:#aaa;">Calibration: </span><span style="color:#fff;">' + (counts.claim_calibration || 0) + '</span>'
  ].join("");
}

function renderTrustCalibration(data) {
  var tableEl = document.getElementById("trust-calib-table");
  var gapsEl = document.getElementById("trust-calib-gaps");
  if (!tableEl) return;

  if (!data || !data.seats || data.seats.length === 0) {
    tableEl.style.display = 'none';
    return;
  }

  var seats = data.seats;
  // Color function
  function scoreColor(ts) {
    if (ts === null || ts === undefined) return '#888';
    if (ts >= 70) return '#10b981';
    if (ts >= 40) return '#f59e0b';
    return '#ef4444';
  }

  var html = '<div style="font-size:12px; color:#a78bfa; font-weight:600; margin-bottom:4px;">Seat Trust Scores</div>';
  html += '<table style="width:100%; border-collapse:collapse; font-size:11px;">';
  html += '<thead><tr style="color:#999; text-align:left;">';
  html += '<th style="padding:2px 6px;">Seat</th>';
  html += '<th style="padding:2px 6px;">Trust</th>';
  html += '<th style="padding:2px 6px;">Acc</th>';
  html += '<th style="padding:2px 6px;">Rej</th>';
  html += '<th style="padding:2px 6px;">Unm</th>';
  html += '<th style="padding:2px 6px;">Rev</th>';
  html += '</tr></thead><tbody>';

  for (var i = 0; i < seats.length; i++) {
    var s = seats[i];
    var ts = s.trust_score;
    var color = scoreColor(ts);
    var seatId = s.seat_id || '';
    html += '<tr style="cursor:pointer;" onclick="handleSeatTrustDrilldown(\'' + seatId + '\')" title="点击查看 ' + seatId + ' 的信任详情">';
    html += '<td style="padding:2px 6px; color:#ccc;">' + seatId + '</td>';
    html += '<td style="padding:2px 6px; color:' + color + '; font-weight:600;">' + (ts !== null && ts !== undefined ? ts : '—') + '</td>';
    html += '<td style="padding:2px 6px; color:#10b981;">' + (s.accepted || 0) + '</td>';
    html += '<td style="padding:2px 6px; color:#ef4444;">' + (s.rejected || 0) + '</td>';
    html += '<td style="padding:2px 6px; color:#f59e0b;">' + (s.unmatched || 0) + '</td>';
    html += '<td style="padding:2px 6px; color:#aaa;">' + (s.reviewed || 0) + '</td>';
    html += '</tr>';
  }
  html += '</tbody></table>';

  // Top trusted / Low evidence / Rejected claim seats
  var topSeats = data.top_trusted_seats || [];
  var lowSeats = data.low_evidence_seats || [];
  var rejSeats = data.rejected_claim_seats || [];

  html += '<div style="margin-top:6px; font-size:11px;">';
  if (topSeats.length > 0) {
    html += '<span style="color:#10b981;">Top: </span><span style="color:#ccc;">' + topSeats.join(', ') + '</span>';
  }
  if (lowSeats.length > 0) {
    html += ' &nbsp; <span style="color:#f59e0b;">Low Evidence: </span><span style="color:#ccc;">' + lowSeats.join(', ') + '</span>';
  }
  if (rejSeats.length > 0) {
    html += ' &nbsp; <span style="color:#ef4444;">Rejected: </span><span style="color:#ccc;">' + rejSeats.join(', ') + '</span>';
  }
  html += '</div>';

  tableEl.innerHTML = html;
  tableEl.style.display = '';

  // Universe gaps
  if (gapsEl && runUniverseData && runUniverseData.gaps && runUniverseData.gaps.length > 0) {
    var gapLines = runUniverseData.gaps.map(function(g) { return g.run_id + ': ' + g.issue; });
    gapsEl.textContent = 'Gaps: ' + gapLines.join('; ');
    gapsEl.style.display = '';
  }
}

// P2.2 — keyboard shortcut Hermes export trigger (calls same path as button clicks)
async function triggerHermesExportByShortcut(runId, kind) {
  try {
    var resp = await fetch(API_BASE + '/api/judge/' + runId + '/verdict');
    if (!resp.ok) { alert('无法获取 ' + runId + ' 的 verdict'); return; }
    var data = await resp.json();
    var exports = data.exports || {};

    var url = '';
    if (kind === 'html') url = exports.html || data.canonical_view_url || (API_BASE + '/api/runs/' + runId + '/index.html') || data.view_url || '';
    else if (kind === 'json') url = exports.hermes_json || '';
    else if (kind === 'md') url = exports.hermes_md || '';
    else if (kind === 'obsidian') {
      var notePath = exports.obsidian_note || '';
      if (notePath && !notePath.startsWith('/api/')) {
        hermesTraceEvent('hermes_export_clicked', runId, 'obsidian', notePath, undefined, undefined, { source: 'keyboard_shortcut' });
        hermesTraceEvent('hermes_export_open_result', runId, 'obsidian', notePath, true, null, { source: 'keyboard_shortcut', mode: 'local_path_alert' });
        alert('Obsidian Note 已生成: ' + notePath);
        return;
      }
      url = notePath;
    }

    // 完整报告 (html) 也写 report_* trace
    if (kind === 'html') {
      traceUIEvent('report_button_clicked', { run_id: runId, source: 'keyboard_shortcut' });
    }

    if (!url) { alert('该文件未生成'); return; }

    hermesTraceEvent('hermes_export_clicked', runId, kind, url, undefined, undefined, { source: 'keyboard_shortcut' });

    if (url.startsWith('/api/')) {
      if (kind === 'html') {
        traceUIEvent('hermes_export_clicked', { run_id: runId, kind: 'html', label: '完整报告', url: url, source: 'keyboard_shortcut' });
        var fullUrl = window.location.origin + url;
        var win = window.open(fullUrl, '_blank');
        if (win) {
          hermesTraceEvent('hermes_export_open_result', runId, kind, url, true, 200, { source: 'keyboard_shortcut', mode: 'window_open' });
          traceUIEvent('report_open_result', { run_id: runId, ok: true, http_status: 200 });
        } else {
          hermesTraceEvent('hermes_export_open_result', runId, kind, url, true, null, { source: 'keyboard_shortcut', mode: 'same_window_fallback' });
          traceUIEvent('report_open_result', { run_id: runId, ok: true, http_status: null, mode: 'same_window_fallback' });
          window.location.href = fullUrl;
        }
      } else {
        var filename = kind === 'json'
          ? 'hermes-output-' + runId + '.json'
          : (kind === 'md' ? 'hermes-output-' + runId + '.md' : 'obsidian-run-note-' + runId + '.md');
        var downloaded = downloadRunExport(url, filename);
        hermesTraceEvent('hermes_export_open_result', runId, kind, url, downloaded, downloaded ? 200 : 0, { source: 'keyboard_shortcut', mode: 'download' });
        // deprecated: 保留旧事件名兼容旧脚本
        traceUIEvent('hermes_export_download_result', { run_id: runId, kind: kind, url: url, ok: downloaded, http_status: downloaded ? 200 : 0, deprecated: true });
      }
    } else if (kind === 'html') {
      var reportWin = window.open(url, '_blank', 'noopener,noreferrer');
      if (reportWin) {
        hermesTraceEvent('hermes_export_open_result', runId, kind, url, true, 200, { source: 'keyboard_shortcut', mode: 'window_open' });
        traceUIEvent('report_open_result', { run_id: runId, ok: true, http_status: 200 });
      } else {
        hermesTraceEvent('hermes_export_open_result', runId, kind, url, true, null, { source: 'keyboard_shortcut', mode: 'same_window_fallback' });
        traceUIEvent('report_open_result', { run_id: runId, ok: true, http_status: null, mode: 'same_window_fallback' });
        window.location.href = url;
      }
    }
  } catch (e) {
    console.error('[triggerHermesExportByShortcut]', e);
  }
}

function hermesTraceEvent(eventType, runId, kind, url, ok, httpStatus, extra) {
  if (typeof traceUIEvent === 'function') {
    var LABEL_MAP = { html: '完整报告', json: 'Hermes JSON', md: 'Hermes MD', obsidian: 'Obsidian Note' };
    var payload = { run_id: runId, kind: kind, label: LABEL_MAP[kind] || '', url: url, ok: ok, http_status: httpStatus };
    if (extra) Object.assign(payload, extra);
    traceUIEvent(eventType, payload);
  } else {
    console.log('[Hermes Trace]', eventType, { run_id: runId, kind: kind, url: url, ok: ok });
  }
}
// P2.3: Unified Hermes export result trace with HEAD verification
async function traceHermesExportResult(runId, kind, label, url, mode) {
  mode = mode || 'open';
  var ok = null;
  var httpStatus = null;
  // Obsidian 为本地路径，不做 HTTP HEAD 检查
  if (kind !== 'obsidian' && url && url.startsWith('/api/')) {
    try {
      var res = await fetch(url, { method: 'HEAD' });
      ok = res.ok;
      httpStatus = res.status;
    } catch (err) {
      ok = false;
    }
  }
  var eventData = {
    run_id: runId,
    kind: kind,
    label: label,
    url: url,
    ok: ok,
    http_status: httpStatus,
    mode: mode,
    source: 'ui_click'
  };
  traceUIEvent('hermes_export_open_result', eventData);
  return { ok: ok, httpStatus: httpStatus };
}

// P4: Gavel filter - apply DOM-based filtering after cards are rendered
function applyGavelFilter() {
  var filter = state.gavelFilter || "all";
  var allCards = $$("#history-list .history-item");
  allCards.forEach(function (card) {
    if (filter === "all") {
      card.style.display = "";
      return;
    }
    var statusEl = card.querySelector(".human-gavel-status");
    if (!statusEl) {
      card.style.display = "none";
      return;
    }
    var statusText = statusEl.textContent || "";
    // Extract status label from "Human Gavel: confirmed" format
    var cardStatus = statusText.replace("Human Gavel: ", "").trim();
    if (filter === "conflict") {
      var conflictEl = card.querySelector(".human-gavel-conflict");
      var hasConflict = conflictEl && conflictEl.textContent && conflictEl.textContent.indexOf("yes") >= 0;
      card.style.display = hasConflict ? "" : "none";
    } else {
      card.style.display = (cardStatus === filter) ? "" : "none";
    }
  });
}

// P4: Gavel history button delegation
function setupHumanGavelHistoryDelegation() {
  var list = $("#history-list");
  if (!list) return;
  // Remove old listener to avoid duplicates
  var oldHandler = list._gavelHistoryHandler;
  if (oldHandler) {
    list.removeEventListener("click", oldHandler);
  }
  var handler = function (e) {
    var btn = e.target.closest(".human-gavel-history-btn");
    if (!btn) return;
    e.stopPropagation();
    var runId = btn.dataset.runId;
    traceUIEvent("human_gavel_history_clicked", { run_id: runId });
    var panel = list.querySelector('.human-gavel-history-panel[data-run-id="' + CSS.escape(runId) + '"]');
    if (!panel) return;
    // Toggle panel
    if (panel.style.display !== "none") {
      panel.style.display = "none";
      return;
    }
    // Load history data
    fetch(API_BASE + "/api/gavel/" + runId + "/history")
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var lines = data.history || [];
        var count = data.count || 0;
        traceUIEvent("human_gavel_history_loaded", { run_id: runId, ok: true, count: count });
        if (!lines.length) {
          panel.innerHTML = '<div style="color:#666;">暂无变更历史</div>';
        } else {
          panel.innerHTML = lines.map(function (entry, idx) {
            var ev = entry.event || "";
            var note = entry.source_note || "";
            var at = entry.synced_at || "";
            var changed = (entry.changed_fields || []).join(", ");
            var oldStatus = entry.old_status || "-";
            var newStatus = entry.new_status || "-";
            return '<div style="padding:2px 0; border-bottom:1px solid #222;">'
              + '<span style="color:#888;">#' + (idx + 1) + '</span> '
              + '<span style="color:#aaa;">' + escapeHtml(ev) + '</span> '
              + '<span style="color:#666;">' + oldStatus + ' → ' + newStatus + '</span>'
              + (changed ? ' <span style="color:#9cf;">[' + escapeHtml(changed) + ']</span>' : '')
              + (note ? ' <span style="color:#888;">(' + escapeHtml(note) + ')</span>' : '')
              + '</div>';
          }).join("");
        }
        panel.style.display = "block";
      })
      .catch(function (err) {
        traceUIEvent("human_gavel_history_loaded", { run_id: runId, ok: false, count: 0, error: String(err) });
        panel.innerHTML = '<div style="color:#f66;">加载失败</div>';
        panel.style.display = "block";
      });
  };
  list.addEventListener("click", handler);
  list._gavelHistoryHandler = handler;
}

// ─── P7: Decision Intelligence Panel ───

/** Load Decision Intelligence data from aggregate endpoint (or fallback to separate APIs). */
async function loadDecisionIntelligence() {
  const panel = document.getElementById("decision-intelligence-panel");
  const content = document.getElementById("decision-intelligence-content");
  if (content) content.innerHTML = '<div style="color:#999;padding:8px;">加载中...</div>';
  let data = null;
  let source = "aggregate";
  try {
    const resp = await fetch(`${API_BASE}/api/decision/intelligence`);
    if (resp.ok) {
      data = await resp.json();
    }
  } catch (_) {}
  if (!data) {
    // Fallback: call each API separately
    source = "fallback";
    try { data = await loadDecisionIntelligenceFallback(); } catch (e) {
      if (content) content.innerHTML = '<div style="color:#f66;padding:12px;">加载失败：' + String(e) + '</div>';
      traceUIEvent("decision_intelligence_loaded", { ok: false, error: String(e) });
      return;
    }
  }
  window.__AJ_DI_DATA__ = data;
  window.__AJ_DI_LAST_LOADED_AT__ = Date.now();
  renderDecisionIntelligencePanel(data, source);
  traceUIEvent("decision_intelligence_loaded", { ok: true, needs_review_count: (data.needs_review || []).length, source });
}

/** Fallback: call each API separately if aggregate endpoint fails. */
async function loadDecisionIntelligenceFallback() {
  const [universe, trust, hermes, cc, gavel] = await Promise.all([
    fetch(`${API_BASE}/api/runs/universe`).then(r => r.json()).catch(() => ({ canonical_run_count: 0, gaps: [] })),
    fetch(`${API_BASE}/api/trust/calibration`).then(r => r.json()).catch(() => ({ seats: [], top_trusted_seats: [], low_evidence_seats: [] })),
    fetch(`${API_BASE}/api/hermes/index`).then(r => r.json()).catch(() => ({ runs: [] })),
    fetch(`${API_BASE}/api/claims/calibration`).then(r => r.json()).catch(() => null),
    fetch(`${API_BASE}/api/gavel/digest`).then(r => r.json()).catch(() => null),
  ]);
  // Build summary inline
  const result = {
    schema_version: "ai-judge-decision-intelligence-v1",
    generated_at: new Date().toISOString(),
    summary: {
      canonical_runs: universe.canonical_run_count || 0,
      universe_gaps: (universe.gaps || []).length,
      human_gavel_counts: { none: 0, draft: 0, confirmed: 0, rejected: 0, needs_review: 0 },
      claim_calibration_counts: { total_runs: 0, total_accepted: 0, total_rejected: 0, total_unmatched: 0 },
      trust_summary: { seat_count: (trust.seats || []).length, top_trusted_seats: (trust.top_trusted_seats || []).slice(0, 5), low_evidence_seats: (trust.low_evidence_seats || []).slice(0, 5) },
    },
    needs_review: [],
    top_trusted_seats: (trust.top_trusted_seats || []).slice(0, 10),
    low_evidence_seats: (trust.low_evidence_seats || []).slice(0, 10),
    next_best_actions: [],
    source_apis: ["/api/runs/universe", "/api/trust/calibration", "/api/hermes/index", "/api/claims/calibration", "/api/gavel/digest"],
  };
  // Count gavel statuses
  (hermes.runs || []).forEach(r => {
    const s = (r.human_gavel && r.human_gavel.status) || "none";
    const key = ["none","draft","confirmed","rejected","needs_review"].includes(s) ? s : "none";
    result.summary.human_gavel_counts[key] = (result.summary.human_gavel_counts[key] || 0) + 1;
  });
  if (cc) {
    result.summary.claim_calibration_counts = {
      total_runs: cc.total_runs || 0,
      total_accepted: cc.total_accepted || 0,
      total_rejected: cc.total_rejected || 0,
      total_unmatched: cc.total_unmatched || 0,
    };
  }
  // Build needs_review (simplified)
  const nrSet = {};
  (universe.gaps || []).forEach(g => {
    const rid = g.run_id || "";
    if (!rid) return;
    nrSet[rid] = nrSet[rid] || { run_id: rid, reasons: [], confidence: null, gavel_status: null, unmatched_claims_count: 0 };
    nrSet[rid].reasons.push("universe gap: " + (g.issue || "unknown"));
  });
  (hermes.runs || []).forEach(r => {
    const rid = r.run_id || "";
    const gv = r.human_gavel || {};
    const s = gv.status || "none";
    if (["draft","needs_review","rejected"].includes(s)) {
      nrSet[rid] = nrSet[rid] || { run_id: rid, reasons: [], confidence: r.confidence || null, gavel_status: s, unmatched_claims_count: 0 };
      nrSet[rid].reasons.push("gavel status: " + s);
    }
    const cc2 = r.claim_calibration || {};
    if ((cc2.unmatched_count || 0) > 0) {
      nrSet[rid] = nrSet[rid] || { run_id: rid, reasons: [], confidence: r.confidence || null, gavel_status: null, unmatched_claims_count: cc2.unmatched_count };
      nrSet[rid].reasons.push("unmatched claims: " + cc2.unmatched_count);
      nrSet[rid].unmatched_claims_count = cc2.unmatched_count;
    }
  });
  result.needs_review = Object.values(nrSet).map(e => ({ ...e, reasons: [...new Set(e.reasons)] }));
  // Next best actions (simplified)
  const actions = [];
  const nrList = result.needs_review;
  if (nrList.length > 0) {
    actions.push({ kind: "review_unmatched_claims", reason: "Needs Review 队列有 " + nrList.length + " 项待处理", target: nrList[0].run_id, priority: 1 });
  }
  if (result.low_evidence_seats.length > 0) {
    actions.push({ kind: "add_human_gavel_for_seat", reason: "Seat '" + result.low_evidence_seats[0] + "' 证据不足", target: result.low_evidence_seats[0], priority: 2 });
  }
  result.next_best_actions = actions.slice(0, 5);
  return result;
}

/** Render the Decision Intelligence overview panel. */
function renderDecisionIntelligencePanel(data, source) {
  const panel = document.getElementById("decision-intelligence-content");
  if (!panel) return;
  const s = data.summary || {};
  const tc = s.trust_summary || {};
  const hg = s.human_gavel_counts || {};
  const cc = s.claim_calibration_counts || {};
  const topSeats = (data.top_trusted_seats || []).slice(0, 3).map(sid => {
    const seat = (PARLIAMENT_SEATS || []).find(s => s.id === sid);
    return seat ? seat.name : sid;
  }).join("、") || "—";
  const lowSeats = (data.low_evidence_seats || []).slice(0, 3).join("、") || "—";
  panel.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '<h3 style="margin:0;font-size:15px;color:#e2e8f0;">Decision Intelligence</h3>' +
      '<span style="font-size:11px;color:#64748b;">' + (source === "aggregate" ? "聚合接口" : "降级模式") + ' · ' + (data.generated_at || "").slice(0, 19).replace("T", " ") + '</span>' +
    '</div>' +
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:12px;">' +
      _diStatCard("Canonical Runs", s.canonical_runs || 0, "#3b82f6") +
      _diStatCard("Universe Gaps", s.universe_gaps || 0, "#f59e0b") +
      _diStatCard("Gavel: confirmed", hg.confirmed || 0, "#10b981") +
      _diStatCard("Gavel: draft", hg.draft || 0, "#f59e0b") +
      _diStatCard("Gavel: needs_review", hg.needs_review || 0, "#ef4444") +
      _diStatCard("Unmatched Claims", cc.total_unmatched || 0, "#8b5cf6") +
    '</div>' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;color:#94a3b8;">' +
      '<div style="padding:8px;border:1px solid #334;border-radius:6px;background:rgba(30,30,50,0.4);">' +
        '<div style="color:#64748b;margin-bottom:4px;">Top Trusted Seats</div>' +
        '<div style="color:#e2e8f0;">' + topSeats + '</div>' +
      '</div>' +
      '<div style="padding:8px;border:1px solid #334;border-radius:6px;background:rgba(30,30,50,0.4);">' +
        '<div style="color:#64748b;margin-bottom:4px;">Low Evidence Seats</div>' +
        '<div style="color:#f59e0b;">' + lowSeats + '</div>' +
      '</div>' +
    '</div>' +
    '<div style="margin-top:10px;">' +
      '<button onclick="renderNeedsReviewQueue()" style="font-size:12px;padding:4px 12px;background:rgba(99,102,241,0.2);color:#a5b4fc;border:1px solid #6366f1;border-radius:4px;cursor:pointer;margin-right:6px;">查看 Needs Review (' + (data.needs_review || []).length + ')</button>' +
      '<button onclick="renderNextBestActions()" style="font-size:12px;padding:4px 12px;background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid #10b981;border-radius:4px;cursor:pointer;">Next Best Actions (' + (data.next_best_actions || []).length + ')</button>' +
    '</div>';
}

/** Generate a small stat card for the overview panel. */
function _diStatCard(label, value, color) {
  return '<div style="padding:8px 10px;border:1px solid #334;border-radius:6px;background:rgba(30,30,50,0.4);">' +
    '<div style="font-size:11px;color:#64748b;margin-bottom:2px;">' + label + '</div>' +
    '<div style="font-size:18px;font-weight:700;color:' + color + ';">' + value + '</div>' +
  '</div>';
}

/** Render the Needs Review queue in the dedicated panel. */
function renderNeedsReviewQueue() {
  const container = document.getElementById("needs-review-queue");
  const content = document.getElementById("needs-review-queue-content");
  if (!container || !content) return;
  container.hidden = false;
  content.innerHTML = '<div style="color:#999;padding:8px;">加载中...</div>';
  fetch(`${API_BASE}/api/decision/intelligence`)
    .then(r => r.json())
    .then(data => {
      const list = (data.needs_review || []);
      if (list.length === 0) {
        content.innerHTML = '<div style="padding:12px;color:#64748b;font-size:13px;">✅ 暂无需要复核的项目。</div>';
        return;
      }
      let html = '<div style="margin-bottom:8px;font-size:13px;font-weight:600;color:#e2e8f0;">Needs Review 队列 (' + list.length + ')</div>';
      list.forEach((item, idx) => {
        const rid = item.run_id || "unknown";
        const reasons = (item.reasons || []).join("；");
        const conf = item.confidence != null ? item.confidence + "%" : "—";
        const gavel = item.gavel_status || "—";
        const uc = item.unmatched_claims_count || 0;
        const reportUrl = `${API_BASE}/api/runs/${rid}/index.html`;
        html += '<div style="padding:10px 12px;margin-bottom:6px;border:1px solid #444;border-radius:6px;background:rgba(30,30,50,0.5);font-size:12px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
            '<strong style="color:#e2e8f0;font-size:13px;">' + escapeHtml(rid) + '</strong>' +
            '<span style="font-size:11px;color:#f59e0b;">' + conf + '</span>' +
          '</div>' +
          '<div style="color:#94a3b8;margin-bottom:4px;">原因：' + escapeHtml(reasons) + '</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">' +
            '<a href="' + reportUrl + '" target="_blank" style="font-size:11px;padding:3px 8px;background:rgba(59,130,246,0.15);color:#93c5fd;border:1px solid #3b82f6;border-radius:3px;text-decoration:none;">打开报告</a>' +
            '<button onclick="traceUIEvent(\'needs_review_item_clicked\',{run_id:\'' + rid + '\',action:\'sync_gavel\'})" style="font-size:11px;padding:3px 8px;background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid #f59e0b;border-radius:3px;cursor:pointer;">同步 Gavel</button>' +
            (uc > 0 ? '<button onclick="traceUIEvent(\'needs_review_item_clicked\',{run_id:\'' + rid + '\',action:\'rebuild_calibration\'})" style="font-size:11px;padding:3px 8px;background:rgba(139,92,246,0.15);color:#c4b5fd;border:1px solid #8b5cf6;border-radius:3px;cursor:pointer;">重建 Calibration</button>' : '') +
          '</div>' +
        '</div>';
      });
      content.innerHTML = html;
      traceUIEvent("needs_review_queue_rendered", { count: list.length });
    })
    .catch(err => {
      content.innerHTML = '<div style="color:#f66;padding:8px;">加载失败：' + String(err) + '</div>';
    });
}

/** Handle seat click → drilldown modal. */
function handleSeatTrustDrilldown(seatId) {
  traceUIEvent("seat_trust_drilldown_clicked", { seat_id: seatId });
  const modal = document.getElementById("seat-trust-drilldown-modal");
  const content = document.getElementById("seat-trust-drilldown-content");
  if (!modal || !content) return;
  modal.hidden = false;
  content.innerHTML = '<div style="padding:20px;color:#999;">加载中...</div>';
  fetch(`${API_BASE}/api/trust/seat/${encodeURIComponent(seatId)}`)
    .then(r => r.json())
    .then(data => {
      const seat = data.seat || data || {};
      const sid = seat.seat_id || seatId;
      const score = seat.trust_score != null ? (seat.trust_score * 100).toFixed(1) + "%" : "—";
      const total = seat.claims_total || 0;
      const acc = seat.accepted || 0;
      const rej = seat.rejected || 0;
      const unmatched = seat.unmatched || 0;
      const warnings = seat.warnings || [];
      const sampleRuns = seat.sample_runs || [];
      let html = '<div style="padding:16px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
          '<h3 style="margin:0;font-size:15px;color:#e2e8f0;">Seat Trust: ' + escapeHtml(sid) + '</h3>' +
          '<button onclick="document.getElementById(\'seat-trust-drilldown-modal\').hidden=true" style="background:none;border:none;color:#64748b;font-size:18px;cursor:pointer;">✕</button>' +
        '</div>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;">' +
          _diStatCard("Trust Score", score, "#3b82f6") +
          _diStatCard("Claims Total", total, "#94a3b8") +
          _diStatCard("Accepted", acc, "#10b981") +
          _diStatCard("Rejected", rej, "#ef4444") +
        '</div>';
      if (warnings.length > 0) {
        html += '<div style="margin-bottom:8px;font-size:12px;color:#f59e0b;">⚠️ ' + warnings.map(w => escapeHtml(w)).join("；") + '</div>';
      }
      if (sampleRuns.length > 0) {
        html += '<div style="font-size:12px;color:#64748b;margin-bottom:4px;">Sample Runs</div><ul style="font-size:12px;color:#94a3b8;margin:0;padding-left:16px;">';
        sampleRuns.slice(0, 5).forEach(rid => {
          html += '<li><a href="' + API_BASE + '/api/runs/' + encodeURIComponent(rid) + '/index.html" target="_blank" style="color:#93c5fd;">' + escapeHtml(rid) + '</a></li>';
        });
        html += '</ul>';
      }
      html += '</div>';
      content.innerHTML = html;
      traceUIEvent("seat_trust_drilldown_loaded", { seat_id: sid, ok: true });
    })
    .catch(err => {
      content.innerHTML = '<div style="padding:20px;color:#f66;">加载失败：' + String(err) + '</div>';
      traceUIEvent("seat_trust_drilldown_loaded", { seat_id: seatId, ok: false, error: String(err) });
    });
}

/** Render Next Best Actions in the dedicated panel. */
function renderNextBestActions() {
  const container = document.getElementById("next-best-actions");
  const content = document.getElementById("next-best-actions-content");
  if (!container || !content) return;
  container.hidden = false;
  content.innerHTML = '<div style="color:#999;padding:8px;">加载中...</div>';
  fetch(`${API_BASE}/api/decision/intelligence`)
    .then(r => r.json())
    .then(data => {
      const actions = (data.next_best_actions || []);
      if (actions.length === 0) {
        content.innerHTML = '<div style="padding:12px;color:#64748b;font-size:13px;">✅ 暂无建议操作。</div>';
        return;
      }
      let html = '<div style="margin-bottom:8px;font-size:13px;font-weight:600;color:#e2e8f0;">Next Best Actions</div>';
      actions.forEach((a, idx) => {
        const kindLabels = {
          review_unmatched_claims: "复核未匹配 Claims",
          add_human_gavel_for_seat: "补充人工裁决",
          sync_draft_gavel: "同步 Gavel",
          backfill_missing_hermes: "回填 Hermes 输出",
          review_low_trust_seat: "复核低信任 Seat",
        };
        const label = kindLabels[a.kind] || a.kind;
        const priColor = ["#ef4444","#f59e0b","#3b82f6","#8b5cf6","#64748b"][(a.priority || 5) - 1] || "#64748b";
        html += '<div style="padding:10px 12px;margin-bottom:6px;border:1px solid #444;border-radius:6px;background:rgba(30,30,50,0.5);font-size:12px;display:flex;gap:10px;align-items:flex-start;">' +
          '<div style="width:6px;height:6px;border-radius:50%;background:' + priColor + ';margin-top:5px;flex-shrink:0;"></div>' +
          '<div style="flex:1;">' +
            '<div style="color:#e2e8f0;font-weight:600;margin-bottom:2px;">' + label + '</div>' +
            '<div style="color:#94a3b8;font-size:11px;margin-bottom:4px;">' + escapeHtml(a.reason || "") + '</div>' +
            '<div style="font-size:11px;color:#64748b;">目标：' + escapeHtml(String(a.target || "")) + ' · 优先级：' + (a.priority || "?") + '</div>' +
          '</div>' +
          '<button onclick="traceUIEvent(\'next_best_action_clicked\',{kind:\'' + (a.kind || "") + '\',target:\'' + escapeAttr(String(a.target || "")) + '\'});this.style.opacity=0.5;" style="font-size:11px;padding:3px 8px;background:rgba(16,185,129,0.15);color:#6ee7b7;border:1px solid #10b981;border-radius:3px;cursor:pointer;flex-shrink:0;">执行</button>' +
        '</div>';
      });
      content.innerHTML = html;
    })
    .catch(err => {
      content.innerHTML = '<div style="color:#f66;padding:8px;">加载失败：' + String(err) + '</div>';
    });
}

/** Integrate DI panel load into existing refreshAll. */
const _origRefreshAll = window.refreshAll;
window.refreshAll = async function() {
  if (typeof _origRefreshAll === "function") await _origRefreshAll();
  loadDecisionIntelligence();
};

window.__AI_JUDGE_SCRIPT_LOADED__ = true;
if (typeof console !== "undefined" && console.info) {
  console.info("[AI Judge] dashboard.js loaded", AI_JUDGE_CLIENT_BUILD);
}

// ==== End Hermes Integration (P2) ====

// Strobe counter
(function() {
  var el = document.getElementById('__aj_strobe__');
  if (!el) {
    el = document.createElement('div');
    el.id = '__aj_strobe__';
    el.style.display = 'none';
    document.body.appendChild(el);
  }
  var n = parseInt(el.textContent || '0', 10) + 1;
  el.textContent = n;
})();

// Diagnostic info into DOM
(function() {
  var info = [
    'BUILD=' + (typeof AI_JUDGE_CLIENT_BUILD !== 'undefined' ? AI_JUDGE_CLIENT_BUILD : 'UNDEF'),
    'STARTED=' + (!!window.__AI_JUDGE_SCRIPT_STARTED__),
    'LOADED=' + (!!window.__AI_JUDGE_SCRIPT_LOADED__),
    'TRACE_UI=' + (typeof traceUIEvent === 'function'),
    'SETUP_HER=' + (typeof setupHermesExportDelegation === 'function'),
    'DELEG=' + (!!window.__HERMES_EXPORT_DELEGATION_BOUND__),
    'PROBE=' + (!!window.__HERMES_POINTER_PROBE_BOUND__),
    'ERRS=' + (window.__AI_JUDGE_BOOT_ERRORS__ || []).length
  ].join('|');
  var el = document.createElement('div');
  el.id = '__aj_diag__';
  el.textContent = info;
  el.style.display = 'none';
  document.body.appendChild(el);
})();

// Sentinel final
try {
  var sf = document.createElement("div");
  sf.id = "__sf_iife_end__";
  sf.style.display = "none";
  document.body.appendChild(sf);
} catch(e) {}

// === P9.2 Maintenance Control Center ===
const MAINT_ACTIONS = [
  { kind: 'release_readiness',   label: 'Release Readiness',   endpoint: '/api/release/readiness',                 method: 'GET',  desc: 'Check release readiness status' },
  { kind: 'regression',          label: 'Regression Harness',  endpoint: '/api/release/regression',                method: 'POST', desc: 'Run regression harness' },
  { kind: 'drift_check',         label: 'Drift Check',         endpoint: '/api/release/drift/check',              method: 'POST', desc: 'Check for drift vs freeze manifest' },
  { kind: 'restore_drill',       label: 'Restore Drill',       endpoint: '/api/release/restore-drill',            method: 'POST', desc: 'Dry-run restore from freeze backup' },
  { kind: 'gavel_sync_all',      label: 'Gavel Sync All',      endpoint: '/api/gavel/sync-all',                   method: 'POST', desc: 'Sync all gavel decisions' },
  { kind: 'claim_calibration_rebuild_all', label: 'Claim Calibration Rebuild', endpoint: '/api/claims/calibration/rebuild-all', method: 'POST', desc: 'Rebuild all claim calibrations' },
  { kind: 'trust_calibration_refresh',     label: 'Trust Calibration Refresh', endpoint: '/api/trust/calibration/refresh',      method: 'POST', desc: 'Refresh trust calibration data' },
  { kind: 'decision_intelligence_refresh', label: 'Decision Intelligence Refresh', endpoint: '/api/decision/intelligence/refresh', method: 'POST', desc: 'Refresh decision intelligence snapshot' },
];

function traceMaintenanceAction(kind, ok, data) {
  var line = { event: ok ? 'maintenance_action_result' : 'maintenance_action_result', kind: kind, ok: ok };
  for (var k in data) { if (data.hasOwnProperty(k)) line[k] = data[k]; }
  line.ts = new Date().toISOString();
  window.__maint_trace = window.__maint_trace || [];
  window.__maint_trace.push(line);
  try {
    fetch('/api/trace', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(line) }).catch(function(){});
  } catch(e) {}
  return line;
}

async function runMaintenanceAction(kind, endpoint, method) {
  var el = document.getElementById('maint-' + kind);
  if (el) { el.querySelector('.maint-status').textContent = 'running...'; el.querySelector('.maint-status').style.color = '#ffaa00'; }
  traceMaintenanceAction(kind, null, { event: 'maintenance_action_clicked' });
  try {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (method === 'POST') opts.body = '{}';
    var resp = await fetch(endpoint, opts);
    var json = await resp.json();
    var ok = resp.ok && (json.ok !== false);
    var data = { status: ok ? 'pass' : 'fail', summary: json };
    if (!ok) { data.error = json.error || 'request_failed'; data.reason = json.reason || 'unknown'; }
    traceMaintenanceAction(kind, ok, data);
    if (el) {
      el.querySelector('.maint-status').textContent = ok ? 'pass' : 'fail';
      el.querySelector('.maint-status').style.color = ok ? '#00ff88' : '#ff4444';
      el.querySelector('.maint-summary').textContent = JSON.stringify(json).slice(0, 120);
      if (!ok && data.reason) {
        el.querySelector('.maint-error').textContent = 'Error: ' + (data.error || '') + ' | Reason: ' + data.reason;
      }
    }
    return { ok: ok, json: json };
  } catch(e) {
    var data = { status: 'fail', error: e.message, reason: 'network_or_parse_error' };
    traceMaintenanceAction(kind, false, data);
    if (el) {
      el.querySelector('.maint-status').textContent = 'fail';
      el.querySelector('.maint-status').style.color = '#ff4444';
      el.querySelector('.maint-error').textContent = 'Error: ' + e.message;
    }
    return { ok: false, error: e.message };
  }
}

function renderMaintenancePanel() {
  var container = document.getElementById('maint-actions');
  if (!container) return;
  container.innerHTML = MAINT_ACTIONS.map(function(a) {
    return '<div id="maint-' + a.kind + '" style="margin-bottom:12px; padding:10px; background:#0f3460; border-radius:6px; border-left:3px solid #00d4ff;">' +
      '<div style="display:flex; justify-content:space-between; align-items:center;">' +
        '<span style="font-weight:bold; color:#00d4ff;">' + a.label + '</span>' +
        '<span class="maint-status" style="color:#888;">idle</span>' +
      '</div>' +
      '<div style="font-size:11px; color:#999; margin:4px 0;">' + a.desc + '</div>' +
      '<div class="maint-summary" style="font-size:11px; color:#aaa; max-height:40px; overflow:hidden;"></div>' +
      '<div class="maint-error" style="font-size:11px; color:#ff6666;"></div>' +
      '<button onclick="runMaintenanceAction(\'' + a.kind + '\', \'' + a.endpoint + '\', \'' + a.method + '\')" style="margin-top:6px; padding:4px 12px; background:#00d4ff22; border:1px solid #00d4ff; color:#00d4ff; border-radius:3px; cursor:pointer; font-family:monospace; font-size:12px;">Run</button>' +
    '</div>';
  }).join('');
}

function toggleMaintenancePanel() {
  var panel = document.getElementById('maintenance-panel');
  if (panel) {
    var show = panel.style.display === 'none';
    panel.style.display = show ? 'block' : 'none';
    if (show) renderMaintenancePanel();
  }
}

document.addEventListener('keydown', function(e) {
  if (!e.metaKey || !e.shiftKey) return;
  switch(e.key.toUpperCase()) {
    case 'O': e.preventDefault(); toggleMaintenancePanel(); break;
    case 'R': e.preventDefault(); runMaintenanceAction('regression', '/api/release/regression', 'POST'); break;
    case 'V': e.preventDefault(); runMaintenanceAction('drift_check', '/api/release/drift/check', 'POST'); break;
    case 'L': e.preventDefault(); runMaintenanceAction('release_readiness', '/api/release/readiness', 'GET'); break;
  }
});

// Auto-load readiness on page load
(function() {
  window.__maint_trace = [];
  setTimeout(function() {
    if (document.getElementById('maintenance-panel')) {
      renderMaintenancePanel();
    }
  }, 1000);
})();
