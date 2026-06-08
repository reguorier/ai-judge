/* ══════════ AI Judge P3.8.4 — Product Validation & RC1 Seal ══════════ */
const AI_JUDGE_CLIENT_BUILD = "P3.8.13-RC1";
window.__AI_JUDGE_BUILD_ID__ = AI_JUDGE_CLIENT_BUILD;
window.__AI_JUDGE_SCRIPT_STARTED__ = true;
if (typeof console !== "undefined" && console.info) {
  console.info("[AI Judge] dashboard.js started", AI_JUDGE_CLIENT_BUILD);
}

const API_BASE = typeof window !== "undefined" && window.location?.origin?.startsWith("http")
  ? window.location.origin : "http://127.0.0.1:8501";

/* ── Mode Config ── */
const MODE_CONFIG = {
  flash: {
    id: "flash", label: "快速裁决", labelShort: "快速",
    placeholder: "写下你的问题，AI Judge 会先帮你整理意图，再给出快速结论、关键理由和下一步。",
    guideText: "快速裁决：写下你的问题，AI Judge 会先帮你整理意图，再给出快速结论、关键理由和下一步。",
    guidePreRun: "快速结论、关键理由、风险、下一步",
    systemInstruction: "你正在执行快速裁决模式。请优先给出明确结论，用较少轮次完成判断。输出应包含：核心结论、3-5条关键理由、主要风险、最小下一步。",
    demoSeatCount: 3,
  },
  strategic: {
    id: "strategic", label: "深度裁决", labelShort: "深度",
    placeholder: "写下复杂问题，AI Judge 会先对齐目标，再组织多个席位交叉验证，形成可审计裁决报告。",
    guideText: "深度裁决：写下复杂问题，AI Judge 会先对齐目标，再组织多个席位交叉验证，形成可审计裁决报告。",
    guidePreRun: "多席位、交叉验证、分歧、证据、可审计报告",
    systemInstruction: "你正在执行深度裁决模式。请按议会式流程处理问题：先拆解目标，再组织多个席位独立发言，进行交叉验证，标注证据、假设、分歧和不确定性，最后形成可审计裁决报告。",
    demoSeatCount: 9,
  },
};

const PARLIAMENT_SEATS = [
  { id: "chatgpt", name: "GPT-4o", channel: "OpenAI", color: "#10a37f", providerDot: "#00a67e" },
  { id: "claude", name: "Claude", channel: "Anthropic", color: "#00B67A", providerDot: "#cc785c" },
  { id: "gemini", name: "Gemini", channel: "Google", color: "#FF8C00", providerDot: "#ea4335" },
  { id: "deepseek", name: "DeepSeek", channel: "DeepSeek", color: "#4d6bfe", providerDot: "#3563fe" },
  { id: "qwen", name: "Qwen", channel: "Alibaba", color: "#808080", providerDot: "#ff6a00" },
  { id: "kimi", name: "Kimi", channel: "Moonshot", color: "#ff5757", providerDot: "#e04040" },
  { id: "grok", name: "Grok", channel: "xAI", color: "#111827", providerDot: "#111827" },
  { id: "yuanbao", name: "Yuanbao", channel: "Tencent", color: "#14b8a6", providerDot: "#16a34a" },
  { id: "doubao", name: "Doubao", channel: "ByteDance", color: "#f97316", providerDot: "#e16510" },
  { id: "minimax", name: "MiniMax", channel: "MiniMax", color: "#7c3aed", providerDot: "#7c3aed" },
  { id: "zhipu", name: "Zhipu", channel: "Zhipu", color: "#0ea5e9", providerDot: "#2563eb" },
  { id: "mimo", name: "MiMo", channel: "Xiaomi", color: "#8b5cf6", providerDot: "#ff6900" },
  { id: "wenxin", name: "Wenxin", channel: "Baidu", color: "#22c55e", providerDot: "#2932e1" },
  { id: "meta", name: "Meta AI", channel: "Meta", color: "#1877f2", providerDot: "#1877f2" },
];

const MORE_FEATURES = [
  { id: "followup", title: "继续追问", status: "context", action: "打开追问上下文", desc: "基于当前或历史 run 的摘要、结论、分歧继续问；重新裁决需回到 Ask。", group: "对话流" },
  { id: "logs", title: "运行记录", status: "ready", action: "查看最近运行", desc: "普通用户看成功、失败、暂停、终止和报告入口；原始 trace 留在高级详情。", group: "日志" },
  { id: "evidence", title: "证据", status: "context", action: "查看证据缺口", desc: "围绕当前 run 拉取 evidence gaps 和可解决项。", group: "证据" },
  { id: "settings", title: "设置", status: "ready", action: "查看席位与模式", desc: "席位、模式、桥接状态和默认可选席位配置。Claude 默认不入普通裁决，可显式选择。", group: "设置" },
  { id: "werewolf", title: "狼人杀", status: "ready", action: "查看模式", desc: "实验室入口：身份板、发言阶段、席位发言和投票由狼人杀后端承载。", group: "模式实验室" },
  { id: "sports", title: "赛事预测", status: "ready", action: "查看赛事池", desc: "模拟研究入口，展示任务、席位预测、赔率/证据和结果，不作为现实投注建议。", group: "模式实验室" },
  { id: "gavel", title: "签字 / 归档", status: "context", action: "查看签字状态", desc: "Human Gavel、历史签字、归档和导出入口。", group: "归档" },
  { id: "status", title: "系统状态", status: "ready", action: "查看高级详情", desc: "首页只显示一句状态，release / manifest / guard / bridge 细节在这里。", group: "运维" },
];

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

/* ── Message Types ── */
const MSG_TYPE = Object.freeze({
  USER_QUESTION: "user_question",
  JUDGE_ALIGNMENT: "judge_alignment",
  SEAT_PROMPT_PREVIEW: "seat_prompt_preview",
  ATTACHMENT_CONTEXT: "attachment_context",
  RUN_STARTED: "run_started",
  SEAT_WAITING: "seat_waiting",
  SEAT_SUBMITTED: "seat_submitted",
  SEAT_ANSWERED: "seat_answered",
  SEAT_TIMEOUT: "seat_timeout",
  SEAT_SKIPPED: "seat_skipped",
  SEAT_FAILED: "seat_failed",
  JUDGE_SUMMARY: "judge_summary",
  REPORT_READY: "report_ready",
  SYSTEM_ERROR: "system_error",
  ATTACHMENT_ADDED: "attachment_added",
});

/* ── Helpers ── */
function $(sel, scope) { return (scope || document).querySelector(sel); }
function $$(sel, scope) { return Array.from((scope || document).querySelectorAll(sel)); }
function escapeHtml(str) { if (!str) return ""; const d = document.createElement("div"); d.textContent = str; return d.innerHTML; }
function escapeAttr(str) { return String(str || "").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function excerpt(text, max) { const s = String(text || ""); return s.length <= max ? s : s.slice(0, max) + "…"; }
function getModeConfig(mode) { return MODE_CONFIG[mode] || MODE_CONFIG.flash; }
function defaultAbstainedSeats() { return ["claude"]; }
function normalizeConfidence(value) {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  const pct = num > 0 && num <= 1 ? num * 100 : num;
  return Math.max(0, Math.min(100, Math.round(pct)));
}
function confidenceChip(value) {
  const pct = normalizeConfidence(value);
  return pct === null
    ? '<span class="mem-confidence muted">置信度 未计算</span>'
    : `<span class="mem-confidence">置信度 ${pct}%</span>`;
}
function currentDraftId() {
  if (!state.currentThread.threadId) {
    state.currentThread.threadId = "draft_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
  }
  return state.currentThread.threadId;
}
function isTextLikeFile(file) {
  return file.type?.startsWith("text/")
    || /(\.txt|\.md|\.markdown|\.json|\.jsonl|\.csv|\.tsv|\.log|\.yaml|\.yml|\.xml|\.html|\.css|\.js|\.ts|\.py|\.sh)$/i.test(file.name || "");
}
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || "").split(",").pop() || "");
    reader.onerror = () => reject(reader.error || new Error("file read failed"));
    reader.readAsDataURL(file);
  });
}

/* ── State ── */
const state = {
  selectedMode: "flash",
  engine: "web",
  currentRunId: null,
  currentTask: null,
  currentVerdict: null,
  historyRuns: [],
  pollTimer: null,
  eventSource: null,
  bridge: null,
  seats: [],

  // ── Phase 2: unified thread model ──
  currentThread: {
    threadId: "",
    runId: "",
    mode: "flash",
    stage: "draft", // draft|aligning|waiting_confirm|running|report_ready|failed|cancelled
    question: "",
    alignedIntent: "",
    suggestedMode: "",
    promptSummary: [],
    messages: [],
    seatCards: [],
    attachments: [],
    artifacts: [],
    report: null,
  },

  workflow: {
    stage: WORKFLOW_STAGE.IDLE,
    canPause: false,
    paused: false,
    completedSeats: new Set(),
    activeSeatCount: 0,
    runId: null,
    attachments: [],
  },

  // ── P1.1 Follow-up Chatbot ──
  followup: {
    activeRunId: "",
    messages: [],
    loading: false,
    error: null,
  },
};

// ── P1.5 Settings & Seat Control ──
state.judgeSettings = {
  mode: "flash",
  reportStyle: "concise",
  partialPolicy: "allow",
  selectedSeats: [],
  excludedSeats: [],
  saveAsDefault: false,
  estimatedDurationSec: null,
};

function loadUserSettings() {
  try {
    const raw = localStorage.getItem("AI_JUDGE_USER_SETTINGS");
    if (raw) {
      const saved = JSON.parse(raw);
      if (saved.defaultMode && (saved.defaultMode === "flash" || saved.defaultMode === "strategic")) {
        state.selectedMode = saved.defaultMode;
        state.judgeSettings.mode = saved.defaultMode;
      }
      if (saved.defaultReportStyle && ["concise", "detailed", "audit"].includes(saved.defaultReportStyle)) {
        state.judgeSettings.reportStyle = saved.defaultReportStyle;
      }
      if (Array.isArray(saved.defaultExcludedSeats)) {
        state.judgeSettings.excludedSeats = saved.defaultExcludedSeats;
      }
      if (saved.partialPolicy) {
        state.judgeSettings.partialPolicy = saved.partialPolicy;
      }
    }
  } catch (_) {}
}

function saveUserSettings() {
  try {
    localStorage.setItem("AI_JUDGE_USER_SETTINGS", JSON.stringify({
      defaultMode: state.judgeSettings.mode,
      defaultReportStyle: state.judgeSettings.reportStyle,
      defaultExcludedSeats: state.judgeSettings.excludedSeats,
      partialPolicy: state.judgeSettings.partialPolicy,
    }));
    // Also save to server
    fetch(API_BASE + "/api/settings/defaults", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        defaultMode: state.judgeSettings.mode,
        defaultReportStyle: state.judgeSettings.reportStyle,
        defaultExcludedSeats: state.judgeSettings.excludedSeats,
        partialPolicy: state.judgeSettings.partialPolicy,
      }),
    }).catch(() => {});
  } catch (_) {}
}

function resetUserSettings() {
  try { localStorage.removeItem("AI_JUDGE_USER_SETTINGS"); } catch (_) {}
  state.judgeSettings = {
    mode: "flash",
    reportStyle: "concise",
    partialPolicy: "allow",
    selectedSeats: [],
    excludedSeats: ["claude"],
    saveAsDefault: false,
    estimatedDurationSec: null,
  };
  state.selectedMode = "flash";
}

// ── P1.5: Estimate duration ──
function estimateDuration() {
  const m = state.judgeSettings.mode;
  if (m === "flash") return 90;
  if (m === "strategic") return 480;
  // custom: number of selected seats × 45
  return (state.judgeSettings.selectedSeats.length || 1) * 45;
}

window.__AI_JUDGE_STATE__ = state;

/* ══════════ DOM Helpers ══════════ */
function setProgress(percent, label) {
  const fill = $("#room-progress-fill");
  const phase = $("#room-phase");
  if (fill) fill.style.width = Math.min(100, Math.max(0, Math.round(percent || 0))) + "%";
  if (phase) phase.textContent = label || "";
}
function cleanupProgress() {
  const fill = $("#room-progress-fill");
  if (fill) fill.style.width = "0%";
}

/* ══════════ Tab Switching ══════════ */
function switchTab(tabName) {
  $$("#main-tabs .tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tabName));
  $$(".workspace .view").forEach(v => v.classList.toggle("active", v.id === "view-" + tabName));
  if (tabName === "room") renderRoom();
  if (tabName === "report") renderReport();
  if (tabName === "memory") renderMemory();
  if (tabName === "more") renderMore();
  if (tabName === "align") renderAlign();
  if (tabName === "ask") renderAsk();
}

/* ══════════ System Panel ══════════ */
async function loadSystemInfo() {
  try {
    const healthRes = await fetch(API_BASE + "/api/health");
    const health = await healthRes.json();
    $("#sys-version").textContent = health.version || "—";
    const integrity = health.release_integrity || health.integrity || health.status || "—";
    const isOk = health.status === "ok" && !["fail", "failed", "error"].includes(String(integrity).toLowerCase());
    $("#sys-integrity").textContent = integrity;
    $("#status-text").textContent = isOk
      ? "系统正常 · " + (health.version || "P3.8.2") + " · " + integrity
      : "系统需检查 · " + (health.version || "P3.8.2") + " · integrity=" + integrity;
    const dot = $("#topbar-status .dot");
    if (dot) dot.style.background = isOk ? "var(--green)" : "var(--amber)";
  } catch (e) {
    $("#sys-version").textContent = "不可用";
    $("#status-text").textContent = "系统异常 · 无法连接";
    const dot = $("#topbar-status .dot");
    if (dot) dot.style.background = "var(--red)";
  }
  try {
    const lockRes = await fetch(API_BASE + "/api/release/status");
    const lock = await lockRes.json();
    $("#sys-release-lock").textContent = lock.release_id || lock.status || "—";
    $("#sys-guard-smoke").textContent = lock.guard_smoke || lock.smoke || "—";
  } catch (e) {
    $("#sys-release-lock").textContent = "—";
  }
  try {
    const bridgeRes = await fetch(API_BASE + "/api/bridge/status");
    const bridge = await bridgeRes.json();
    state.bridge = bridge;
    const ready = bridge.ready_count || (bridge.seats || []).filter(s => s.ready).length || 0;
    const total = bridge.seat_count || (bridge.seats || []).length || 0;
    $("#sys-bridge-status").textContent = `席位 ${ready}/${total} 就绪`;
  } catch (e) {
    $("#sys-bridge-status").textContent = "未连接";
  }
  $("#sys-api-base").textContent = API_BASE;
}

function toggleSysPanel() {
  const panel = $("#sys-panel");
  panel.classList.toggle("open");
  if (panel.classList.contains("open")) loadSystemInfo();
}

/* ══════════ Ask View ══════════ */
function renderAsk() {
  const cfg = getModeConfig(state.selectedMode);
  // Sync mode with settings
  state.judgeSettings.mode = state.judgeSettings.mode || state.selectedMode || "flash";
  $("#ask-guide").textContent = cfg.guideText;
  $("#ask-input").placeholder = cfg.placeholder;

  // P1.5: Render settings panel
  renderAskSettingsPanel();

  // Also render the current thread messages in Ask view
  renderThreadMessages("ask-thread-messages");
}

function switchMode(mode) {
  state.selectedMode = mode;
  state.judgeSettings.mode = mode;
  state.judgeSettings.selectedSeats = [];
  state.judgeSettings.estimatedDurationSec = null;
  $$(".ask-mode-toggle .seg").forEach(s => s.classList.toggle("active", s.dataset.mode === mode));
  renderAsk();
}

// ── P1.5: Ask Settings Panel ──
let _settingsPanelVisible = false;
async function renderAskSettingsPanel() {
  const panel = $("#ask-settings-panel");
  if (!panel) return;
  const btn = $("#btn-settings-toggle");
  if (!btn) return;

  const dur = estimateDuration();
  state.judgeSettings.estimatedDurationSec = dur;
  const durStr = dur >= 60 ? `约 ${Math.ceil(dur / 60)} 分钟` : `约 ${dur} 秒`;

  let seatsAvailable = 0;
  let seatsUnavailable = 0;
  const seatStatusHtml = [];
  try {
    const res = await fetch(API_BASE + "/api/seats/status");
    const data = await res.json();
    if (data.seats) {
      for (const s of data.seats) {
        if (s.ready) seatsAvailable++;
        else {
          seatsUnavailable++;
          seatStatusHtml.push(`<span class="ss-seat-unavail">${s.name} (${s.reason || "未知"})</span>`);
        }
      }
    }
  } catch (_) {}

  panel.innerHTML = `
    <div class="settings-panel-header">
      <span class="settings-panel-title">本轮设置</span>
      <button class="settings-panel-close" onclick="toggleSettingsPanel()">×</button>
    </div>
    <div class="settings-section">
      <div class="settings-label">模式</div>
      <div class="settings-mode-tabs">
        <span class="settings-mode-tab ${state.judgeSettings.mode === 'flash' ? 'active' : ''}" onclick="settingsSetMode('flash')">快速</span>
        <span class="settings-mode-tab ${state.judgeSettings.mode === 'strategic' ? 'active' : ''}" onclick="settingsSetMode('strategic')">深度</span>
        <span class="settings-mode-tab ${state.judgeSettings.mode === 'custom' ? 'active' : ''}" onclick="settingsSetMode('custom')">自定义</span>
      </div>
    </div>
    <div class="settings-section">
      <div class="settings-label">引擎</div>
      <div class="settings-mode-tabs">
        <span class="settings-mode-tab ${state.engine === 'web' ? 'active' : ''}" onclick="switchEngine('web')">网页陪审</span>
        <span class="settings-mode-tab disabled" title="本地模式暂不可用">本地模式</span>
      </div>
    </div>
    ${state.judgeSettings.mode === 'custom' ? `
    <div class="settings-section">
      <div class="settings-label">席位选择</div>
      <div class="settings-seat-actions">
        <button class="settings-seat-act-btn" onclick="selectAllAvailableSeats()">全选</button>
        <button class="settings-seat-act-btn" onclick="selectRecommendedSeats()">推荐</button>
        <button class="settings-seat-act-btn" onclick="clearAllSeats()">清空</button>
      </div>
      <div id="settings-seat-grid" class="settings-seat-grid">加载中…</div>
    </div>` : `
    <div class="settings-section">
      <div class="settings-label">席位</div>
      <div class="settings-seat-summary">${seatsAvailable} 可用${seatsUnavailable > 0 ? `，${seatsUnavailable} 不可用` : ''}</div>
      ${seatStatusHtml.length > 0 ? `<div class="settings-seat-unavail-list">${seatStatusHtml.join('')}</div>` : ''}
    </div>`}
    <div class="settings-section">
      <div class="settings-label">报告风格</div>
      <div class="settings-mode-tabs">
        <span class="settings-mode-tab ${state.judgeSettings.reportStyle === 'concise' ? 'active' : ''}" onclick="settingsSetReportStyle('concise')">简洁</span>
        <span class="settings-mode-tab ${state.judgeSettings.reportStyle === 'detailed' ? 'active' : ''}" onclick="settingsSetReportStyle('detailed')">详细</span>
        <span class="settings-mode-tab ${state.judgeSettings.reportStyle === 'audit' ? 'active' : ''}" onclick="settingsSetReportStyle('audit')">可审计</span>
      </div>
    </div>
    <div class="settings-section">
      <div class="settings-label">预计用时</div>
      <div class="settings-estimate">${durStr}</div>
    </div>
    <div class="settings-section">
      <label class="settings-checkbox">
        <input type="checkbox" ${state.judgeSettings.saveAsDefault ? 'checked' : ''} onchange="state.judgeSettings.saveAsDefault=this.checked">
        保存为默认偏好
      </label>
      <button class="btn-reset-settings" onclick="resetUserSettings();refreshSettingsPanel();">重置默认</button>
    </div>
  `;

  // Load seat grid for custom mode
  if (state.judgeSettings.mode === 'custom') {
    renderSeatGrid();
  }
}

function toggleSettingsPanel() {
  const panel = $("#ask-settings-panel");
  if (!panel) return;
  _settingsPanelVisible = !_settingsPanelVisible;
  panel.classList.toggle("visible", _settingsPanelVisible);
  if (_settingsPanelVisible) {
    renderAskSettingsPanel();
    // Write trace: settings_opened
    fetch(API_BASE + "/api/judge/_trace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: "settings_opened", mode: state.judgeSettings.mode }),
    }).catch(() => {});
  }
}

function refreshSettingsPanel() {
  renderAskSettingsPanel();
}

function settingsSetMode(mode) {
  state.judgeSettings.mode = mode;
  state.judgeSettings.selectedSeats = [];
  if (mode !== "custom") state.selectedMode = mode;
  renderAskSettingsPanel();
}

function settingsSetReportStyle(style) {
  state.judgeSettings.reportStyle = style;
  renderAskSettingsPanel();
}

// ── Task 6: Engine selection ──
function switchEngine(engine) {
  if (engine !== "web" && engine !== "local") return;
  state.engine = engine;
  renderAskSettingsPanel();
}

async function renderSeatGrid() {
  const grid = $("#settings-seat-grid");
  if (!grid) return;
  try {
    const res = await fetch(API_BASE + "/api/seats/status");
    const data = await res.json();
    const seats = data.seats || [];
    grid.innerHTML = seats.map(s => {
      const isSelected = state.judgeSettings.selectedSeats.includes(s.id);
      const cls = s.ready ? (isSelected ? "selected" : "") : "unavailable";
      return `<span class="settings-seat-chip ${cls}"
        onclick="${s.ready ? `toggleSeat('${s.id}')` : ''}"
        title="${s.ready ? '' : (s.reason || '不可用')}">
        ${s.name}${!s.ready ? ' ⚠' : ''}
        ${isSelected ? ' ✓' : ''}
      </span>`;
    }).join("");
  } catch (_) {
    grid.innerHTML = "无法加载席位";
  }
}

function toggleSeat(seatId) {
  const idx = state.judgeSettings.selectedSeats.indexOf(seatId);
  if (idx >= 0) {
    state.judgeSettings.selectedSeats.splice(idx, 1);
  } else {
    state.judgeSettings.selectedSeats.push(seatId);
  }
  renderSeatGrid();
  refreshSettingsPanel();
}

// ── P2.3: Bulk seat actions ──
let _cachedSeatStatus = null;
let _cachedSeatDefaults = null;

async function getSeatStatus() {
  if (_cachedSeatStatus) return _cachedSeatStatus;
  try {
    const res = await fetch(API_BASE + "/api/seats/status");
    const data = await res.json();
    _cachedSeatStatus = data.seats || [];
    // Cache mode defaults (flash: [...], strategic: [...])
    if (data.defaults) {
      _cachedSeatDefaults = data.defaults;
    }
    return _cachedSeatStatus;
  } catch (_) {
    return [];
  }
}

async function selectAllAvailableSeats() {
  // Force refresh seat status to get latest defaults
  _cachedSeatStatus = null;
  _cachedSeatDefaults = null;
  const seats = await getSeatStatus();
  const readyIds = seats.filter(s => s.ready).map(s => s.id);
  state.judgeSettings.selectedSeats = readyIds;
  state.judgeSettings.excludedSeats = seats.filter(s => !s.ready).map(s => s.id);
  renderSeatGrid();
  refreshSettingsPanel();
}

async function selectRecommendedSeats() {
  const seats = await getSeatStatus();
  const readySeats = seats.filter(s => s.ready);
  // Recommend: top performers (first N based on mode default)
  const mode = state.judgeSettings.mode || "flash";
  const count = mode === "strategic" ? 9 : (mode === "flash" ? 3 : 5);
  const recommended = readySeats.slice(0, Math.min(count, readySeats.length));
  state.judgeSettings.selectedSeats = recommended.map(s => s.id);
  state.judgeSettings.excludedSeats = seats.filter(s => !s.ready).map(s => s.id);
  renderSeatGrid();
  refreshSettingsPanel();
}

async function clearAllSeats() {
  state.judgeSettings.selectedSeats = [];
  renderSeatGrid();
  refreshSettingsPanel();
}

/* ══════════ Thread Message Rendering ══════════ */
function renderThreadMessages(containerId) {
  const container = document.getElementById(containerId) || $("#ask-thread-messages");
  if (!container) return;
  const thread = state.currentThread;
  const msgs = thread.messages || [];
  if (msgs.length === 0) {
    container.innerHTML = "";
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");
  container.innerHTML = msgs.map((msg, idx) => renderMessageCard(msg, idx)).join("");
}

function renderMessageCard(msg, idx) {
  const type = msg.type || "system_error";
  const ts = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString("zh-CN", {hour:'2-digit', minute:'2-digit'}) : "";

  if (type === MSG_TYPE.USER_QUESTION) {
    return `
      <div class="msg-card user-msg">
        <div class="msg-role">你 <span class="msg-time">${ts}</span></div>
        <div class="msg-body">${escapeHtml(msg.question || "")}</div>
      </div>`;
  }
  if (type === MSG_TYPE.JUDGE_ALIGNMENT) {
    return `
      <div class="msg-card judge-msg">
        <div class="msg-role">Grand Judge <span class="msg-time">${ts}</span></div>
        <div class="msg-headline">理解你的问题</div>
        <div class="msg-body">${escapeHtml(msg.alignedIntent || "")}</div>
        ${msg.suggestedMode ? `<div class="msg-chip ok">建议模式：${escapeHtml(msg.suggestedMode)}</div>` : ""}
      </div>`;
  }
  if (type === MSG_TYPE.SEAT_PROMPT_PREVIEW) {
    const seats = msg.seats || [];
    return `
      <div class="msg-card judge-msg">
        <div class="msg-role">Grand Judge <span class="msg-time">${ts}</span></div>
        <div class="msg-headline">参审席位</div>
        <div class="msg-chips">${seats.map(s => `<span class="msg-chip">${escapeHtml(s.name || s.id)}</span>`).join("")}</div>
        ${msg.promptSummary ? `<div class="msg-body" style="margin-top:8px;font-size:12px;color:var(--text-soft);">${escapeHtml(msg.promptSummary)}</div>` : ""}
      </div>`;
  }
  if (type === MSG_TYPE.ATTACHMENT_CONTEXT) {
    const atts = msg.attachments || [];
    return `
      <div class="msg-card system-msg">
        <div class="msg-role">附件上下文 <span class="msg-time">${ts}</span></div>
        <div class="msg-body">${atts.map(a => escapeHtml(a.name || a.id)).join("、")}</div>
      </div>`;
  }
  if (type === MSG_TYPE.RUN_STARTED) {
    return `
      <div class="msg-card system-msg">
        <div class="msg-role">系统 <span class="msg-time">${ts}</span></div>
        <div class="msg-body">裁决已启动，run_id: ${escapeHtml(msg.runId || "")}</div>
      </div>`;
  }
  if (type === MSG_TYPE.SEAT_ANSWERED) {
    const seat = msg.seat || {};
    const preview = msg.answerPreview || "已回答";
    const fullAnswer = msg.fullAnswer || "";
    const seatId = seat.id || msg.seatId || "";
    const displayName = seat.name || seat.displayName || seatId;
    const color = seat.color || "#64748b";
    const expandId = "expand-" + seatId + "-" + idx;
    return `
      <div class="msg-card seat-msg" style="border-left:3px solid ${escapeAttr(color)}">
        <div class="msg-role" style="color:${escapeAttr(color)}">${escapeHtml(displayName)} <span class="msg-time">${ts}</span></div>
        <div class="msg-body">${escapeHtml(preview)}</div>
        ${fullAnswer ? `<details id="${expandId}" style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--accent);">展开完整回答</summary><div style="font-size:12px;line-height:1.6;color:var(--text-soft);white-space:pre-wrap;margin-top:6px;">${escapeHtml(fullAnswer)}</div></details>` : ""}
      </div>`;
  }
  if (type === MSG_TYPE.SEAT_TIMEOUT) {
    const seat = msg.seat || {};
    const seatId = seat.id || msg.seatId || "";
    const displayName = seat.name || seat.displayName || seatId;
    return `
      <div class="msg-card seat-msg seat-timeout-msg">
        <div class="msg-role">${escapeHtml(displayName)} <span class="msg-time">${ts}</span></div>
        <div class="msg-body" style="color:var(--red);">超时未答，本轮将以 partial 继续</div>
      </div>`;
  }
  if (type === MSG_TYPE.SEAT_SKIPPED || type === MSG_TYPE.SEAT_FAILED) {
    const seat = msg.seat || {};
    const seatId = seat.id || msg.seatId || "";
    const displayName = seat.name || seat.displayName || seatId;
    const reason = type === MSG_TYPE.SEAT_SKIPPED ? "已跳过" : ("失败：" + (msg.error || "未知"));
    return `
      <div class="msg-card seat-msg seat-skip-msg">
        <div class="msg-role">${escapeHtml(displayName)} <span class="msg-time">${ts}</span></div>
        <div class="msg-body" style="color:var(--text-muted);">${escapeHtml(reason)}</div>
      </div>`;
  }
  if (type === MSG_TYPE.SEAT_SUBMITTED) {
    const seat = msg.seat || {};
    const seatId = seat.id || msg.seatId || "";
    const displayName = seat.name || seat.displayName || seatId;
    return `
      <div class="msg-card seat-msg">
        <div class="msg-role">${escapeHtml(displayName)} <span class="msg-time">${ts}</span></div>
        <div class="msg-body" style="color:var(--accent);">已提交，等待回答…</div>
      </div>`;
  }
  if (type === MSG_TYPE.JUDGE_SUMMARY) {
    return `
      <div class="msg-card judge-msg verdict-msg">
        <div class="msg-role">Grand Judge 总结 <span class="msg-time">${ts}</span></div>
        <div class="msg-headline">${escapeHtml(msg.verdict || "裁决完成")}</div>
        <div class="msg-body">${escapeHtml(msg.summary || "")}</div>
        ${msg.confidence ? `<div class="msg-chip ok">置信度 ${msg.confidence}%</div>` : ""}
      </div>`;
  }
  if (type === MSG_TYPE.REPORT_READY) {
    const runId = msg.runId || state.currentThread.runId || "";
    const viewUrl = runId ? API_BASE + "/api/runs/" + runId + "/index.html" : "";
    return `
      <div class="msg-card system-msg report-ready-msg">
        <div class="msg-role">系统 <span class="msg-time">${ts}</span></div>
        <div class="msg-headline">报告已生成</div>
        <div class="msg-body">${viewUrl ? `<a href="${escapeAttr(viewUrl)}" target="_blank" style="color:var(--accent);">打开完整报告</a>` : "可前往 Report 页查看"}</div>
      </div>`;
  }
  if (type === MSG_TYPE.SYSTEM_ERROR) {
    return `
      <div class="msg-card system-msg error-msg">
        <div class="msg-role">系统错误 <span class="msg-time">${ts}</span></div>
        <div class="msg-body" style="color:var(--red);">${escapeHtml(msg.error || "未知错误")}</div>
      </div>`;
  }
  // Default fallback
  return `
    <div class="msg-card system-msg">
      <div class="msg-role">${escapeHtml(type)} <span class="msg-time">${ts}</span></div>
      <div class="msg-body">${escapeHtml(JSON.stringify(msg).slice(0, 200))}</div>
    </div>`;
}

/* Add a message to the current thread and re-render both Ask and Room thread views */
function addThreadMessage(msg) {
  const thread = state.currentThread;
  msg.timestamp = msg.timestamp || new Date().toISOString();
  thread.messages.push(msg);

  // Re-render thread in both Ask (if visible) and Room
  renderThreadMessages("ask-thread-messages");
  renderThreadMessages("room-thread-messages");

  // Also update Room seat cards for progress
  renderRoom();
}

/* ══════════ Align View ══════════ */
function renderAlign() {
  const thread = state.currentThread;
  const q = thread.question || thread.alignedIntent || "—";
  const cfg = getModeConfig(thread.mode || state.selectedMode);

  // Question
  $("#align-question").textContent = q;

  // Mode + guide text
  $("#align-mode").textContent = cfg.label + "模式";
  $("#align-guide").textContent = cfg.guidePreRun;

  // Prompt summary
  const activeSeats = resolveActiveSeats();
  const seatCount = activeSeats.length;
  const seatNames = activeSeats.slice(0, 3).map(s => s.name).join("、");
  const moreSeats = seatCount > 3 ? ` 等 ${seatCount} 席` : "";
  let promptSummary = cfg.systemInstruction;
  if (seatCount > 0) {
    promptSummary += `\n\n参审席位：${seatNames}${moreSeats}`;
  }
  $("#align-prompt").textContent = promptSummary;

  // Attachments
  const attCard = $("#align-attachments-card");
  const attDiv = $("#align-attachments");
  const atts = thread.attachments || [];
  if (atts.length > 0) {
    attCard.hidden = false;
    attDiv.innerHTML = atts.map(a =>
      `<div class="attach-chip">${escapeHtml(a.name || a.id)}
        <button class="chip-remove" data-att-id="${escapeAttr(a.id)}" title="移除">&times;</button>
      </div>`
    ).join("");
  } else {
    attCard.hidden = true;
  }

  // Seat preview
  const seatPreviewCard = $("#align-seats-preview-card") || $("#align-seats-card");
  const seatPreviewDiv = $("#align-seats-preview");
  if (seatPreviewCard && seatPreviewDiv) {
    if (activeSeats.length > 0) {
      seatPreviewCard.hidden = false;
      seatPreviewDiv.innerHTML = activeSeats.map(s =>
        `<span class="seat-preview-chip" style="border-left: 3px solid ${escapeAttr(s.color || '#64748b')}">
          ${escapeHtml(s.name)} <small>${escapeHtml(s.channel || '')}</small>
        </span>`
      ).join("");
    } else {
      seatPreviewCard.hidden = true;
    }
  }

  // ── P2.4: Settings summary in Align — show requested/runnable/excluded ──
  const settings = state.judgeSettings;
  const dur = settings.estimatedDurationSec || estimateDuration();
  const durStr = dur >= 60 ? `${Math.ceil(dur / 60)} 分钟` : `${Math.ceil(dur)} 秒`;
  const alignSettings = $("#align-settings-summary");
  if (alignSettings) {
    const runnableCount = activeSeats.filter(s => s.ready !== false).length;
    const excludedCount = activeSeats.filter(s => s.ready === false).length;
    const explicitExcluded = settings.excludedSeats || [];
    let seatInfoHtml = "";
    if (settings.mode === "custom") {
      seatInfoHtml = `<span class="align-settings-meta">请求: ${activeSeats.length}席</span>
        <span class="align-settings-meta ok">可用: ${runnableCount}席</span>`;
      if (excludedCount > 0) {
        seatInfoHtml += `<span class="align-settings-meta warn">不可用: ${excludedCount}席</span>`;
      }
      if (explicitExcluded.length > 0) {
        seatInfoHtml += `<span class="align-settings-meta">排除: ${explicitExcluded.join('、')}</span>`;
      }
    } else {
      seatInfoHtml = `<span class="align-settings-meta">请求: ${activeSeats.length}席</span>
        <span class="align-settings-meta ok">可用: ${runnableCount}席</span>`;
    }
    const modeLabel = settings.mode === "flash" ? "快速" : settings.mode === "strategic" ? "深度" : `自定义 (${settings.selectedSeats.length}席)`;
    const reportLabel = settings.reportStyle === "concise" ? "简洁" : settings.reportStyle === "detailed" ? "详细" : "可审计";
    alignSettings.innerHTML = `
      <span class="align-settings-meta">模式: ${modeLabel}</span>
      ${seatInfoHtml}
      <span class="align-settings-meta">报告: ${reportLabel}</span>
      <span class="align-settings-meta">预计: ${durStr}</span>
    `;
    alignSettings.classList.remove("hidden");
  }
}

function showAlignView() {
  switchTab("align");
  const alignTab = document.querySelector('[data-tab="align"]');
  if (alignTab) alignTab.hidden = false;
}

function hideAlignTab() {
  const alignTab = document.querySelector('[data-tab="align"]');
  if (alignTab) alignTab.hidden = true;
}

/* ══════════ Room View ══════════ */
// ── Task 4: Step-aware phase message mapping ──
function stepMessageFor(rawStep, completed, total) {
  const s = (rawStep || "").toLowerCase();
  if (s.includes("受理") || s.includes("提示词对齐")) return "受理完成，网页提示词对齐";
  if (s.includes("桥接") || s.includes("校准")) return `后台网页桥接准备：${total} 席校准通过`;
  if (s.includes("等待席位") || s.includes("回答")) return `等待席位回答，剩余 ${total - completed} 席，最长等待 120s`;
  if (s.includes("补跑") || s.includes("rerun")) return `补跑 ${completed}/${total}`;
  if (s.includes("判词") || s.includes("报告")) return "生成判词报告";
  // Fallback: seat-count-based phases
  if (completed === 0) return "正在执行网页陪审…";
  if (completed < total) return `${completed}/${total} 席已完成独立发言，${total - completed} 席仍在思考`;
  return "全席位发言完毕，正在汇总…";
}

function renderRoom() {
  const thread = state.currentThread;
  const task = state.currentTask;
  const v = state.currentVerdict;
  const phase = $("#room-phase");
  const status = $("#room-status");
  const seatsGrid = $("#room-seats");
  const controls = $("#room-controls");

  // Also render thread messages in Room
  renderThreadMessages("room-thread-messages");

  if (thread.stage === "draft" && !task && !v) {
    if (phase) phase.textContent = "等待提交问题…";
    if (status) status.textContent = "等待开庭";
    if (seatsGrid) seatsGrid.innerHTML = "";
    $$("#room-controls button").forEach(b => b.classList.add("hidden"));
    return;
  }

  // Merge live seat results with pending seat list
  let liveResults = [];
  if (v?.web_bridge?.raw_results) {
    liveResults = v.web_bridge.raw_results;
  } else if (task) {
    const diag = task.progress_diagnostics || {};
    const diagSeats = diag.seats || [];
    liveResults = diagSeats.map(s => ({
      seat: s.seat || s.id,
      seat_name: s.seat_name || s.name || s.seat,
      status: s.state || s.status || "waiting",
      ok: s.state === "complete" || s.state === "done" || s.status === "ok" || s.status === "answered",
    }));
  }

  // Build full seat list: start from pending, overwrite with live data
  const pending = state._pendingSeats || resolveActiveSeats();
  const liveMap = {};
  liveResults.forEach(s => { liveMap[s.seat] = s; });

  const allSeats = pending.map(ps => {
    const live = liveMap[ps.id];
    if (live) {
      return { ...ps, status: live.status, ok: live.ok, name: live.seat_name || ps.name };
    }
    return { ...ps, status: ps.state || "waiting", ok: false };
  });

  // Also add any live seats not in pending
  liveResults.forEach(s => {
    if (!allSeats.find(as => as.id === s.seat)) {
      const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === s.seat) || {};
      allSeats.push({
        id: s.seat, name: s.seat_name || seatInfo.name || s.seat,
        channel: seatInfo.channel || "", color: seatInfo.color || "#64748b",
        status: s.status, ok: s.ok,
      });
    }
  });

  const completed = allSeats.filter(s => s.ok || s.status === "complete" || s.status === "done" || s.status === "answered").length;
  const total = Math.max(1, allSeats.length);
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  if (task?.status === "running") {
    // ── Task 4: Step-aware phase messages ──
    const rawStep = task.current_step || task.step || "";
    const stepMsg = stepMessageFor(rawStep, completed, total);
    if (phase) phase.textContent = stepMsg;
    if (status) status.textContent = `进行中 · ${completed}/${total} 席`;
    // Use backend progress when available, else fallback to seat ratio
    const backendProgress = task.progress != null ? Math.round(Number(task.progress) * 100) : null;
    setProgress(backendProgress ?? pct, rawStep || "");
    $("#btn-pause-judge").classList.remove("hidden");
    $("#btn-stop-judge").classList.remove("hidden");
    $("#btn-resume-judge").classList.add("hidden");
  } else if (task?.status === "complete" || v) {
    if (phase) phase.textContent = "裁决完成，报告已生成";
    if (status) status.textContent = `已完成 · ${completed}/${total} 席`;
    setProgress(100, "");
    $$("#room-controls button").forEach(b => b.classList.add("hidden"));
  } else if (task?.status === "failed") {
    if (phase) phase.textContent = "裁决失败：" + (task.error || "未知错误");
    if (status) status.textContent = "失败";
    $$("#room-controls button").forEach(b => b.classList.add("hidden"));
  } else {
    if (phase) phase.textContent = task?.current_step || "处理中…";
    if (status) status.textContent = task?.status || "—";
  }

  // Render all seat cards (for the grid view, alongside the thread)
  if (seatsGrid) {
    seatsGrid.innerHTML = allSeats.map(s => {
      const name = s.name || s.id;
      let statusClass = "seat-waiting";
      let statusLabel = "等待中";
      if (s.ok || s.status === "complete" || s.status === "done" || s.status === "answered") {
        statusClass = "seat-answered"; statusLabel = "已回答";
      } else if (s.status === "submitted" || s.status === "running" || s.status === "speaking") {
        statusClass = "seat-submitted"; statusLabel = "发言中";
      } else if (s.status === "timeout" || s.status === "failed") {
        statusClass = "seat-timeout"; statusLabel = "超时";
      } else if (s.status === "skipped") {
        statusClass = "seat-skipped"; statusLabel = "跳过";
      } else if (s.status === "unavailable") {
        statusClass = "seat-skipped"; statusLabel = "不可用";
      }
      return `
        <div class="room-seat-card ${s.ok ? 'is-answered' : (s.status==='submitted'||s.status==='running'||s.status==='speaking')?'is-active':''}">
          <div class="seat-name" style="color:${escapeAttr(s.color || '#64748b')}">${escapeHtml(name)}</div>
          <div class="seat-channel">${escapeHtml(s.channel || "")}</div>
          <span class="seat-status ${statusClass}">${statusLabel}</span>
        </div>
      `;
    }).join("");
  }
  renderRoomTimeline();

  // ── P2.3: Agent turn cards (model-by-model speaking flow) ──
  renderRoomAgentTurnCards(allSeats, liveResults);

  // ── P2.3: Room report button visibility ──
  updateRoomReportButton();

  // ── P1.5: Room seat config display ──
  const roomCfg = $("#room-seat-config");
  if (roomCfg) {
    const completed = allSeats.filter(s => s.ok || s.status === "complete" || s.status === "done" || s.status === "answered").length;
    const timedOut = allSeats.filter(s => s.status === "timeout" || s.status === "failed").length;
    const skipped = allSeats.filter(s => s.status === "skipped" || s.status === "unavailable").length;
    const modeLabel = state.judgeSettings.mode === "flash" ? "快速" : state.judgeSettings.mode === "strategic" ? "深度" : "自定义";
    roomCfg.innerHTML = `<span class="room-config-meta">模式: ${modeLabel}</span> | <span class="room-config-meta">席位: ${total}席</span> | <span class="room-config-meta">完成: ${completed}</span>${timedOut > 0 ? ` | <span class="room-config-meta warn">超时: ${timedOut}</span>` : ""}${skipped > 0 ? ` | <span class="room-config-meta warn">跳过: ${skipped}</span>` : ""}`;
  }
}

/* ══════════ P2.3 Agent Turn Cards — Model-by-model speaking flow ══════════ */
function renderRoomAgentTurnCards(allSeats, liveResults) {
  const container = $("#room-thread-messages");
  if (!container) return;

  // Gather seat content from thread messages
  const seatMap = {};
  (state.currentThread.messages || []).forEach(m => {
    if (m.type === MSG_TYPE.SEAT_ANSWERED || m.type === MSG_TYPE.SEAT_SUBMITTED ||
        m.type === MSG_TYPE.SEAT_TIMEOUT || m.type === MSG_TYPE.SEAT_SKIPPED ||
        m.type === MSG_TYPE.SEAT_FAILED) {
      const sid = (m.seat && m.seat.id) || m.seatId;
      if (!seatMap[sid]) seatMap[sid] = {};
      if (m.type === MSG_TYPE.SEAT_ANSWERED) seatMap[sid].answered = m;
      if (m.type === MSG_TYPE.SEAT_SUBMITTED) seatMap[sid].submitted = m;
      if (m.type === MSG_TYPE.SEAT_TIMEOUT) seatMap[sid].timeout = m;
      if (m.type === MSG_TYPE.SEAT_SKIPPED) seatMap[sid].skipped = m;
      if (m.type === MSG_TYPE.SEAT_FAILED) seatMap[sid].failed = m;
    }
  });

  // Build seat status from live results
  const liveMap = {};
  if (liveResults) {
    liveResults.forEach(s => { liveMap[s.seat] = s; });
  }

  const seatCards = allSeats.map((s, i) => {
    const live = liveMap[s.id];
    const seatMsg = seatMap[s.id] || {};
    let statusLabel, statusClass, summary, fullAnswer, answerMeta;
    let isActive = false, isAnswered = false, isTimeout = false, isFailed = false, isSkipped = false;

    if (live?.ok || seatMsg.answered) {
      statusLabel = "已回答";
      statusClass = "seat-answered";
      isAnswered = true;
      const a = seatMsg.answered || {};
      summary = a.answerPreview || a.summary || (live?.answer_preview) || "回答已提交";
      fullAnswer = a.fullAnswer || a.answer || (live?.full_answer) || summary;
      answerMeta = a.answeredAt || a.timestamp ? { time: a.answeredAt || a.timestamp, confidence: a.confidence } : null;
    } else if (live?.status === "answering" || live?.status === "speaking" || live?.status === "running") {
      statusLabel = "回答中";
      statusClass = "seat-answering";
      isActive = true;
      summary = live?.answer_preview || "正在生成回答…";
    } else if (live?.status === "timeout" || seatMsg.timeout) {
      statusLabel = seatMsg.timeout?.reason || "超时";
      statusClass = "seat-timeout";
      isTimeout = true;
      summary = seatMsg.timeout?.reason || "席位超时未响应";
      fullAnswer = seatMsg.timeout?.fullAnswer || "";
    } else if (live?.status === "failed" || seatMsg.failed) {
      statusLabel = "失败";
      statusClass = "seat-failed";
      isFailed = true;
      summary = seatMsg.failed?.error || seatMsg.failed?.reason || "席位调用失败";
    } else if (live?.status === "skipped" || seatMsg.skipped) {
      statusLabel = "跳过";
      statusClass = "seat-skipped";
      isSkipped = true;
      summary = seatMsg.skipped?.reason || "已跳过";
    } else if (live?.status === "submitted") {
      statusLabel = "已提交";
      statusClass = "seat-submitted";
      isActive = true;
      summary = "已提交，等待回答…";
    } else {
      statusLabel = "等待中";
      statusClass = "seat-waiting";
      summary = "等待发言…";
    }

    const name = s.name || s.id;
    const channel = s.channel || "";
    const color = s.color || "#64748b";
    const init = (name[0] || "?").toUpperCase();

    const cardClass = ["agent-turn-card"];
    if (isAnswered) cardClass.push("is-answered");
    if (isActive) cardClass.push("is-active");
    if (isTimeout) cardClass.push("is-timeout");
    if (isFailed) cardClass.push("is-failed");
    if (isSkipped) cardClass.push("is-skipped");

    return { html: `<article class="${cardClass.join(" ")}" data-seat-id="${escapeAttr(s.id)}" aria-expanded="false">
  <div class="turn-header">
    <div class="turn-avatar" style="background:${escapeAttr(color)}">${escapeHtml(init)}</div>
    <span class="turn-model">${escapeHtml(name)}</span>
    <span class="turn-channel">${escapeHtml(channel)}</span>
    <span class="turn-status-badge ${statusClass}">${statusLabel}</span>
  </div>
  <div class="turn-body">
    <div class="turn-summary">${escapeHtml(summary)}</div>
    ${(isAnswered || isTimeout || isFailed) ? `<button class="turn-expand-btn">查看详情</button>` : ""}
  </div>
  <div class="turn-expand">
    <div class="full-answer">${escapeHtml(fullAnswer || summary)}</div>
    ${answerMeta ? `<div class="full-answer-meta">
      ${answerMeta.time ? `<span>时间: ${escapeHtml(answerMeta.time)}</span>` : ""}
      ${answerMeta.confidence != null ? `<span>置信度: ${escapeHtml(String(answerMeta.confidence))}</span>` : ""}
    </div>` : ""}
    ${isTimeout ? `<div class="full-answer-meta"><span>原因: ${escapeHtml(summary)}</span></div>` : ""}
    ${isFailed ? `<div class="full-answer-meta"><span>错误: ${escapeHtml(summary)}</span></div>` : ""}
  </div>
</article>`, seat: { id: s.id, name, channel, color, status: statusLabel, isAnswered, isActive, isTimeout, isFailed } };
  });

  // ── P2.4: update state.currentThread.seatCards as canonical data source ──
  state.currentThread.seatCards = seatCards.map(c => c.seat);

  container.innerHTML = seatCards.map(c => c.html).join("");
  container.classList.remove("hidden");
}

/* ── P2.3: Room report button visibility ── */
function updateRoomReportButton() {
  const btn = $("#btn-room-open-report");
  if (!btn) return;
  const stage = state.currentThread.stage;
  const hasReport = stage === "report_ready" || state.currentVerdict;
  btn.style.display = hasReport ? "" : "none";
  if (!hasReport && (stage === "running" || stage === "answered")) {
    btn.style.display = "";
    btn.textContent = "报告生成中…";
    btn.disabled = true;
    btn.style.opacity = "0.5";
  } else if (hasReport) {
    btn.textContent = "查看报告";
    btn.disabled = false;
    btn.style.opacity = "";
  }
}

/* ══════════ Report View ══════════ */
function renderReport() {
  const v = state.currentVerdict;
  const thread = state.currentThread;
  const container = $("#report-content");

  // Prefer thread.report if available
  const reportData = thread.report || v;
  if (!reportData) {
    container.innerHTML = '<div class="report-empty"><h3>尚无裁决报告</h3><p>提交问题并等待裁决完成后，报告将在此显示。</p></div>';
    return;
  }

  const conf = reportData.confidence || 0;
  const confClass = conf >= 80 ? "confidence-high" : conf >= 60 ? "confidence-mid" : "confidence-low";
  const reasons = (reportData.key_reasons || reportData.reasons || []).slice(0, state.judgeSettings.reportStyle === "concise" ? 3 : 10);
  const divergences = (reportData.divergences || reportData.disagreements || []);
  const nextSteps = (reportData.next_steps || []);
  const report = reportData.final_report || {};
  const viewUrl = (reportData.exports?.html) || (reportData.run_id ? API_BASE + "/api/runs/" + reportData.run_id + "/index.html" : "");
  const style = state.judgeSettings.reportStyle || "concise";
  const showDetailed = style === "detailed" || style === "audit";
  const showAudit = style === "audit";

  container.innerHTML = `
    <div class="report-hero">
      <div class="verdict-conclusion">${escapeHtml(reportData.one_liner || report.title || "裁决结论")}</div>
      <div class="verdict-meta">
        <span class="${confClass}">置信度 ${conf}%</span>
        <span>${reportData.seat_count || (reportData.web_bridge?.requested_count) || "—"} 席参审</span>
        <span>${reportData.mode || state.selectedMode}</span>
        <span>报告: ${style === "concise" ? "简洁" : style === "detailed" ? "详细" : "可审计"}</span>
      </div>
    </div>
    ${(() => {
      // ── Task 3: Seat cards ──
      const seats = reportData.seats || reportData.seat_scores || [];
      if (seats.length) {
        const maxPreview = 120;
        return `<div class="report-section"><h3>席位发言摘要</h3><div class="report-seat-grid">${seats.map(s => {
          const name = s.name || s.seat_name || s.seat || s.id || "—";
          const score = s.score != null ? Number(s.score).toFixed(2) : (s.confidence != null ? Number(s.confidence).toFixed(2) : "—");
          const answer = s.answer || s.answer_preview || s.text || "";
          const preview = answer.length > maxPreview ? answer.slice(0, maxPreview) + "…" : answer;
          const color = s.color || "#64748b";
          const tier = s.tier || (score >= 0.7 ? "A" : score >= 0.5 ? "B" : "C");
          return `<div class="report-seat-card" style="border-left: 3px solid ${escapeAttr(color)}">
            <div class="rsc-header"><span class="rsc-name" style="color:${escapeAttr(color)}">${escapeHtml(name)}</span><span class="rsc-score">score=${score}</span><span class="rsc-tier tier-${tier.toLowerCase()}">${tier}</span></div>
            <div class="rsc-answer">${escapeHtml(preview)}</div>
          </div>`;
        }).join("")}</div></div>`;
      }
      return "";
    })()}
    ${(() => {
      // ── Task 3: Claims table ──
      const claims = reportData.claims || [];
      if (claims.length) {
        return `<div class="report-section"><h3>Claims 评分</h3>
        <div class="report-claims-table"><div class="rct-header"><span>Claim</span><span>Tier</span><span>Score</span></div>
        ${claims.map(c => {
          const text = c.text || c.claim || c.statement || "—";
          const tier = c.tier || "—";
          const score = c.score != null ? Number(c.score).toFixed(2) : "—";
          return `<div class="rct-row"><span class="rct-claim">${escapeHtml(text)}</span><span class="rct-tier tier-${String(tier).toLowerCase()}">${tier}</span><span class="rct-score">${score}</span></div>`;
        }).join("")}</div></div>`;
      }
      return "";
    })()}
    ${(() => {
      // ── Task 3: Web bridge evidence strength ──
      const wb = reportData.web_bridge;
      if (wb) {
        const ok = wb.ok_count ?? wb.success_count ?? 0;
        const failed = wb.failed_count ?? wb.error_count ?? 0;
        const total = ok + failed;
        if (total > 0) {
          const pct = Math.round((ok / total) * 100);
          const cls = pct >= 80 ? "confidence-high" : pct >= 50 ? "confidence-mid" : "confidence-low";
          return `<div class="report-section"><h3>证据收集状态</h3>
          <div class="report-evidence-bar"><span class="${cls}">${ok}/${total} 席有效收集</span><span>成功率 ${pct}%</span></div></div>`;
        }
      }
      return "";
    })()}
    ${reasons.length ? `
    <div class="report-section">
      <h3>关键理由</h3>
      <ul>${reasons.map(r => `<li>${escapeHtml(typeof r === "string" ? r : (r.text || r.reason || ""))}</li>`).join("")}</ul>
    </div>` : ""}
    ${showDetailed && divergences.length ? `
    <div class="report-section detailed-only">
      <h3>主要分歧</h3>
      <ul>${divergences.map(d => `<li>${escapeHtml(typeof d === "string" ? d : (d.text || d.description || ""))}</li>`).join("")}</ul>
    </div>` : ""}
    ${showDetailed && (reportData.risks || reportData.uncertainty) ? `
    <div class="report-section detailed-only">
      <h3>风险与不确定性</h3>
      <p>${escapeHtml(reportData.risks || reportData.uncertainty || "—")}</p>
    </div>` : ""}
    ${nextSteps.length ? `
    <div class="report-section">
      <h3>下一步建议</h3>
      <ul>${nextSteps.map(s => `<li>${escapeHtml(typeof s === "string" ? s : (s.action || s.text || ""))}</li>`).join("")}</ul>
    </div>` : ""}
    ${showAudit ? `
    <div class="report-section audit-only">
      <h3>Hermes 链接</h3>
      <p style="font-size:12px;">
        ${reportData.run_id ? `Run ID: ${escapeHtml(reportData.run_id)} | ` : ""}
        ${viewUrl ? `<a href="${escapeAttr(viewUrl)}" target="_blank">完整报告</a> | ` : ""}
        ${reportData.verdict ? `<a href="#" onclick="openRawVerdict();return false">JSON</a>` : ""}
      </p>
    </div>` : `
    <div class="report-section">
      <p style="font-size:12px;">
        ${reportData.run_id ? `Run ID: ${escapeHtml(reportData.run_id)} | ` : ""}
        ${viewUrl ? `<a href="${escapeAttr(viewUrl)}" target="_blank">Hermes 完整报告</a>` : ""}
      </p>
    </div>`}
    <div class="report-actions">
      ${viewUrl ? `<a href="${escapeAttr(viewUrl)}" target="_blank" class="btn-primary">打开完整报告</a>` : ""}
      <button onclick="saveToMemory()">存入记忆</button>
    </div>
  `;

  // ── P1.1 Follow-up section ──
  renderFollowupSection(container, reportData.run_id || state.currentThread.runId || "");

  // ── P1.2B Process summary ──
  renderReportProcessSummary();

  // ── P1.3 Evidence Summary ──
  // ── P1.4 Action Pack ──
  if (showDetailed) {
    setTimeout(() => renderEvidenceSummaryForReport(), 50);
    setTimeout(() => renderActionPackForReport(), 100);
  }
}

function openRawVerdict() {
  const v = state.currentVerdict || state.currentThread.report;
  if (!v) return;
  const w = window.open("", "_blank");
  w.document.write("<pre>" + escapeHtml(JSON.stringify(v, null, 2)) + "</pre>");
}

// ── P1.1 Follow-up Chatbot ──

function renderFollowupSection(container, runId) {
  if (!container) return;

  const fu = state.followup;
  const activeRunId = runId || fu.activeRunId || "";

  // Build followup dialog HTML
  let html = `
    <div id="followup-zone" class="followup-zone">
      <div class="followup-header">
        <h3>继续追问这份报告…</h3>
      </div>
      <div id="followup-messages" class="followup-messages">`;

  // Render existing messages
  if (fu.messages.length) {
    for (const msg of fu.messages) {
      if (msg.type === "followup_user") {
        html += `<div class="fu-msg fu-msg-user"><strong>你问：</strong>${escapeHtml(msg.text)}</div>`;
      } else if (msg.type === "followup_answer") {
        const badges = [];
        if (msg.basedOn?.verdict) badges.push("裁决报告");
        if (msg.basedOn?.seat_summaries || msg.basedOn?.seatSummary) badges.push("席位摘要");
        if (msg.basedOn?.attachments) badges.push("附件上下文");
        if (state._evidenceSummary?.ok) badges.push("证据摘要");
        const basedOnStr = badges.length ? badges.join(" · ") : "裁决报告";

        html += `
          <div class="fu-msg fu-msg-answer">
            <strong>AI Judge：</strong>
            <div class="fu-answer-body">${escapeHtml(msg.answer).replace(/\n/g, "<br>")}</div>
            <div class="fu-answer-meta">基于：${basedOnStr}</div>
          </div>`;
      } else if (msg.type === "followup_error") {
        html += `<div class="fu-msg fu-msg-error">${escapeHtml(msg.text)}</div>`;
      }
    }
  }

  // Show context missing warning if historical run lacks seats
  if (fu.messages.length > 0 && activeRunId && fu._contextMissing) {
    html += `<div class="fu-context-note">这份历史报告缺少席位摘要，因此回答只基于最终报告。</div>`;
  }

  html += `</div>`;

  // Input area
  html += `
      <div class="followup-input-row">
        <input
          type="text"
          id="followup-input"
          class="followup-input"
          placeholder="追问这份裁决：例如"为什么是这个结论？"或"下一步怎么执行？""
          onkeydown="if(event.key==='Enter')sendFollowup('${escapeAttr(activeRunId)}')"
          ${fu.loading ? "disabled" : ""}
        />
        <button id="followup-send-btn" class="btn-followup-send" onclick="sendFollowup('${escapeAttr(activeRunId)}')" ${fu.loading ? 'disabled style="opacity:0.5"' : ""}>
          ${fu.loading ? "分析中…" : "发送追问"}
        </button>
      </div>
      <div class="followup-actions">
        <button class="btn-followup-rerun" onclick="startRerun('${escapeAttr(activeRunId)}')">重新裁决</button>
      </div>
    </div>`;

  // Find or create followup zone
  const existing = container.querySelector("#followup-zone");
  if (existing) {
    existing.outerHTML = html;
  } else {
    container.insertAdjacentHTML("beforeend", html);
  }
}

async function sendFollowup(runId) {
  const input = document.getElementById("followup-input");
  const question = (input?.value || "").trim();
  if (!question) return;
  if (!runId) {
    alert("当前没有可追问的裁决。请先打开一份报告。");
    return;
  }

  const fu = state.followup;
  fu.activeRunId = runId;
  fu.loading = true;
  fu.error = null;

  // Add user message
  fu.messages.push({ type: "followup_user", text: question, runId });
  if (input) input.value = "";
  renderFollowupSection($("#report-content"), runId);

  // P1.4: Check if this is an action-oriented question and we have cached action pack
  const actionKeywords = ["先做", "最大风险", "风险", "下一步", "行动", "执行", "重新裁决", "重裁", "建议先", "应先"];
  const isActionQuestion = actionKeywords.some(kw => question.includes(kw));

  if (isActionQuestion && (state._actionPack || state.currentThread.runId === runId)) {
    // Try to load action pack if not already cached
    let ap = state._actionPack;
    if (!ap || ap.run_id !== runId) {
      ap = await loadActionPack(runId);
      if (ap) state._actionPack = ap;
    }

    if (ap && ap.ok) {
      fu.loading = false;
      const answer = _composeActionPackFollowupAnswer(question, ap);
      fu.messages.push({
        type: "followup_answer",
        runId: runId,
        answer: answer,
        basedOn: { action_pack: true },
        contextUsed: { action_pack: true },
        createdAt: new Date().toISOString(),
      });
      renderFollowupSection($("#report-content"), runId);
      return;
    }
  }

  try {
    const res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/followup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode: "" }),
    });
    const data = await res.json();

    fu.loading = false;

    if (data.ok) {
      fu.messages.push({
        type: "followup_answer",
        runId: data.run_id,
        answer: data.answer,
        basedOn: data.context_used || {},
        contextUsed: data.context_used || {},
        createdAt: data.created_at || "",
      });
      // Check if context is partial
      if (!data.context_used?.seat_summaries && !data.context_used?.verdict) {
        fu._contextMissing = true;
      } else {
        fu._contextMissing = false;
      }
    } else {
      fu.messages.push({
        type: "followup_error",
        text: data.error === "no_context_available"
          ? "这份运行记录缺少可用的报告上下文，无法生成追问回答。"
          : ("错误：" + (data.error || "未知错误")),
        runId,
      });
    }
  } catch (e) {
    fu.loading = false;
    fu.messages.push({
      type: "followup_error",
      text: "网络请求失败：" + (e.message || "请检查 API 服务是否运行"),
      runId,
    });
  }

  renderFollowupSection($("#report-content"), runId);
}

function startRerun(runId) {
  // Transfer followup context to Ask input
  const fu = state.followup;
  const lastUserMsg = [...fu.messages].reverse().find(m => m.type === "followup_user");
  const rerunQuestion = lastUserMsg?.text || state.currentThread.question || "";

  // Navigate to Ask tab with pre-filled question
  switchTab("ask");

  setTimeout(() => {
    const askInput = $("#ask-question-input") || $("#question-input");
    if (askInput && rerunQuestion) {
      askInput.value = rerunQuestion;
      askInput.focus();
    }
  }, 100);
}

/* ══════════ Memory View — NOW BACKEND-DRIVEN ══════════ */
async function renderMemory() {
  const list = $("#memory-list");
  if (!list) return;

  // Show loading state
  list.innerHTML = '<div class="memory-empty"><p>加载中…</p></div>';

  try {
    const res = await fetch(API_BASE + "/api/runs/recent");
    const data = await res.json();
    const runs = Array.isArray(data) ? data : (data.runs || []);

    if (!runs.length) {
      list.innerHTML = '<div class="memory-empty"><p>暂无已保存的判断</p></div>';
      return;
    }

    list.innerHTML = runs.map((item, i) => {
      const timeStr = item.created_at || item.timestamp || item.time || "";
      const displayTime = timeStr ? new Date(timeStr).toLocaleString("zh-CN") : "";
      const question = item.question || item.query || "";
      const verdict = item.one_liner || item.verdict || item.conclusion || "";
      const runId = item.run_id || item.id || "";
      const report = item.report_url || item.verdict_url || "";
      const config = item.config || "";
      return `
        <div class="memory-item" data-runid="${escapeAttr(runId)}">
          <div class="mem-main" onclick="loadMemoryRun('${escapeAttr(runId)}')">
            <div class="mem-question">${escapeHtml(question)}</div>
            <div class="mem-verdict">${escapeHtml(excerpt(verdict || item.status || "报告生成中或暂无摘要", 120))}</div>
            <div class="mem-meta">
              ${confidenceChip(item.confidence)}
              <span>${escapeHtml(displayTime)}</span>
              ${item.has_verdict ? '<span>已出报告</span>' : '<span>未出报告</span>'}
              ${report ? `<span>${escapeHtml(report)}</span>` : ""}
              <span>${escapeHtml(runId)}</span>
            </div>
            ${config ? `<div class="mem-config" style="font-size:11px;color:var(--accent);margin-top:4px;">${escapeHtml(config)}</div>` : ""}
          </div>
          <div class="mem-summary" id="mem-summary-${escapeAttr(runId)}" style="font-size:12px;color:var(--text-soft);margin-top:6px;"></div>
          <div class="mem-evidence" id="mem-evidence-${escapeAttr(runId)}" style="font-size:11px;color:var(--text-soft);margin-top:2px;"></div>
          <div class="mem-action-summary" id="mem-action-${escapeAttr(runId)}"></div>
          <div class="mem-timeline-expanded" id="mem-tl-${escapeAttr(runId)}"></div>
          <div class="mem-actions">
            <button class="btn-mem-followup" onclick="event.stopPropagation();openFollowupForRun('${escapeAttr(runId)}')">继续追问</button>
            <span class="mem-timeline-toggle" id="mem-tl-toggle-${escapeAttr(runId)}" onclick="event.stopPropagation();toggleMemoryTimeline('${escapeAttr(runId)}')" hidden>展开 timeline</span>
          </div>
        </div>
      `;
    }).join("");

    // Async load timeline summaries for each run
    for (const item of runs) {
      const runId = item.run_id || item.id || "";
      if (!runId) continue;
      loadRunTimeline(runId).then(data => {
        const summaryEl = document.getElementById("mem-summary-" + runId);
        const toggleEl = document.getElementById("mem-tl-toggle-" + runId);
        if (data && data.events && data.events.length) {
          const summary = renderMemoryTimelineSummary(data);
          if (summaryEl && summary) summaryEl.textContent = summary;
          if (toggleEl) toggleEl.hidden = false;
          // Store timeline data
          const memItem = document.querySelector(`.memory-item[data-runid="${runId}"]`);
          if (memItem) memItem.__timelineData = data;
        }
      }).catch(() => {});

      // P1.3: Load evidence summary one-liner
      loadEvidenceSummary(runId).then(ev => {
        const evEl = document.getElementById("mem-evidence-" + runId);
        const line = renderEvidenceSummaryOneLiner(ev);
        if (evEl && line) evEl.textContent = line;
      }).catch(() => {});

      // P1.4: Load action pack one-liner
      loadActionPack(runId).then(ap => {
        const apEl = document.getElementById("mem-action-" + runId);
        const line = renderActionPackOneLiner(ap);
        if (apEl && line) apEl.textContent = line;
      }).catch(() => {});
    }
  } catch (e) {
    // Fallback: try localStorage if backend fails
    try {
      const mem = JSON.parse(localStorage.getItem("ai_judge_memory") || "[]");
      if (!mem.length) {
        list.innerHTML = '<div class="memory-empty"><p>暂无已保存的判断</p></div>';
        return;
      }
      list.innerHTML = mem.map((item, i) => {
        const timeStr = item.time ? new Date(item.time).toLocaleString("zh-CN") : "";
        return `
          <div class="memory-item" onclick="loadMemoryVerdict('${escapeAttr(item.run_id)}')">
            <div class="mem-question">${escapeHtml(item.question)}</div>
            <div class="mem-verdict">${escapeHtml(excerpt(item.verdict, 120))}</div>
            <div class="mem-meta">
              ${confidenceChip(item.confidence)}
              <span>${escapeHtml(timeStr)}</span>
              <span>${escapeHtml(item.run_id || "")}</span>
            </div>
          </div>
        `;
      }).join("");
    } catch (_) {
      list.innerHTML = '<div class="memory-empty"><p>无法读取记忆</p></div>';
    }
  }
}

async function loadMemoryRun(runId) {
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/judge/" + runId + "/verdict");
    const v = await res.json();
    if (res.ok) {
      state.currentVerdict = v;
      state.currentThread.report = v;
      state.currentThread.runId = runId;
      renderVerdict(v);
      switchTab("report");
    }
  } catch (_) {}
}

function openFollowupForRun(runId) {
  if (!runId) return;
  // Reset followup state for new run
  state.followup.activeRunId = runId;
  state.followup.messages = [];
  state.followup.loading = false;
  state.followup.error = null;
  state.followup._contextMissing = false;
  // Load the run and navigate to report
  loadMemoryRun(runId);
}

function saveToMemory() {
  const v = state.currentVerdict || state.currentThread.report;
  if (!v) return;
  try {
    const settings = state.judgeSettings;
    const modeLabel = settings.mode === "flash" ? "快速" : settings.mode === "strategic" ? "深度" : "自定义";
    const seatCount = v.seat_count || settings.selectedSeats.length || 0;
    const reportLabel = settings.reportStyle === "concise" ? "简洁" : settings.reportStyle === "detailed" ? "详细" : "可审计";
    const configSummary = `本轮：${modeLabel} · ${seatCount}席 · ${reportLabel}报告`;

    const mem = JSON.parse(localStorage.getItem("ai_judge_memory") || "[]");
    mem.unshift({
      question: state.currentThread.question || v.question || "",
      verdict: v.one_liner || "",
      confidence: v.confidence || 0,
      run_id: v.run_id || state.currentThread.runId,
      time: new Date().toISOString(),
      config: configSummary,
    });
    if (mem.length > 50) mem.length = 50;
    localStorage.setItem("ai_judge_memory", JSON.stringify(mem));
    renderMemory();
  } catch (_) {}
}

async function loadMemoryVerdict(runId) {
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/judge/" + runId + "/verdict");
    const v = await res.json();
    if (res.ok) {
      state.currentVerdict = v;
      state.currentThread.question = v.question || "";
      renderVerdict(v);
      switchTab("report");
    }
  } catch (_) {}
}

/* ══════════ More View ══════════ */
function currentRunId() {
  return state.currentThread.runId || state.currentRunId || state.currentVerdict?.run_id || "";
}

function moreStatusClass(status) {
  if (status === "ready") return "ready";
  if (status === "context") return "context";
  return "pending";
}

function moreStatusLabel(feature) {
  if (feature.status === "ready") return "可用";
  if (feature.status === "context") return currentRunId() ? "可用" : "需要 run";
  return "待接入";
}

function renderMore() {
  const grid = $("#more-groups");
  if (!grid) return;
  grid.innerHTML = MORE_FEATURES.map(feature => `
    <article class="more-card">
      <div class="more-card-header">
        <div>
          <div class="more-title">${escapeHtml(feature.title)}</div>
          <div class="more-desc">${escapeHtml(feature.desc)}</div>
        </div>
        <span class="more-status ${moreStatusClass(feature.status)}">${escapeHtml(moreStatusLabel(feature))}</span>
      </div>
      <button type="button" data-more-action="${escapeAttr(feature.id)}">${escapeHtml(feature.action)}</button>
    </article>
  `).join("");
}

async function fetchJson(path, options) {
  const res = await fetch(API_BASE + path, options || {});
  let data = null;
  try { data = await res.json(); } catch (_) { data = { status: res.status, text: await res.text() }; }
  if (!res.ok) return { ok: false, status: res.status, data };
  return { ok: true, status: res.status, data };
}

function renderMoreDetail(title, summary, payload) {
  const detail = $("#more-detail");
  if (!detail) return;
  detail.classList.remove("hidden");
  detail.innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(summary || "")}</p>
    <pre>${escapeHtml(JSON.stringify(payload || {}, null, 2))}</pre>
  `;

  try { detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch(_){}
}

function renderMoreDetailHtml(title, summary, html, payload) {
  const detail = $("#more-detail");
  if (!detail) return;
  detail.classList.remove("hidden");
  detail.innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(summary || "")}</p>
    ${html || ""}
    ${payload ? `<pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>` : ""}
  `;
}

async function openMoreFeature(id, sourceEl) {
  const runId = currentRunId();
  if (id === "followup") {
    renderMoreDetailHtml("继续追问", runId
      ? "追问会挂到当前 run 的上下文里；需要全席位重跑时，回到 Ask 提交新问题。"
      : "需要先打开一个报告或历史 run，系统才能带入摘要、结论、分歧和附件上下文。",
      runId ? `
        <textarea class="more-textarea" id="more-followup-prompt" placeholder="输入你要基于当前报告继续追问的问题"></textarea>
        <div class="more-actions">
          <button type="button" data-more-command="followup" data-run-id="${escapeAttr(runId)}">保存追问上下文</button>
        </div>
      ` : "",
      runId ? { run_id: runId, endpoint: `/api/runs/${runId}/followup` } : { required_context: "run_id" });
    return;
  }
  if (id === "logs") {
    const recent = await fetchJson("/api/runs/recent");
    const runs = recent?.data?.runs || [];
    renderMoreDetailHtml("运行记录", "最近运行展示摘要、置信度和报告入口；原始 trace 留给高级详情。",
      `<div class="more-list">${runs.map(r => `
        <div class="more-list-item">
          <strong>${escapeHtml(r.question || r.run_id)}</strong>
          <div>${escapeHtml(excerpt(r.one_liner || r.status || "", 140))}</div>
          <div class="more-actions">
            ${r.report_url ? `<a href="${escapeAttr(r.report_url)}" target="_blank" rel="noreferrer">打开报告</a>` : ""}
            <button type="button" data-more-action="evidence" data-run-id="${escapeAttr(r.run_id)}">证据缺口</button>
          </div>
        </div>
      `).join("")}</div>`,
      recent);
    return;
  }
  if (id === "evidence") {
    const targetRun = sourceEl?.dataset?.runId || runId;
    if (!targetRun) {
      renderMoreDetail("证据", "需要当前 run 才能查看证据缺口。", { required_context: "run_id" });
      return;
    }
    const gaps = await fetchJson(`/api/judge/${targetRun}/evidence-gaps`);
    const tasks = gaps?.data?.tasks || [];
    renderMoreDetailHtml("证据", "当前 run 的 evidence gaps。可以把人工补充证据写回队列。",
      `<div class="more-list">${tasks.length ? tasks.map(t => `
        <div class="more-list-item">
          <strong>${escapeHtml(t.title || t.task_id || t.id || "证据缺口")}</strong>
          <div>${escapeHtml(t.description || t.question || t.reason || "")}</div>
          <textarea class="more-textarea" data-evidence-resolution="${escapeAttr(t.task_id || t.id || "")}" placeholder="输入补充证据、链接或处理结论"></textarea>
          <div class="more-actions">
            <button type="button" data-more-command="resolve-evidence" data-run-id="${escapeAttr(targetRun)}" data-task-id="${escapeAttr(t.task_id || t.id || "")}">写回处理结果</button>
          </div>
        </div>
      `).join("") : '<div class="more-list-item">当前没有待处理证据缺口。</div>'}</div>`,
      gaps);
    return;
  }
  if (id === "settings") {
    const [modes, seats, bridge] = await Promise.all([
      fetchJson("/api/modes"),
      fetchJson("/api/seats"),
      fetchJson("/api/bridge/status")
    ]);
    renderMoreDetailHtml("设置", "普通裁决默认不包含 Claude；这里可以初始化桥接配置或做就绪校准。",
      `<div class="more-actions">
        <button type="button" data-more-command="bridge-init">初始化桥接配置</button>
        <button type="button" data-more-command="bridge-calibrate">校准网页席位</button>
      </div>`,
      { modes, seats, bridge, abstained_by_default: defaultAbstainedSeats() });
    return;
  }
  if (id === "werewolf") {
    const detail = $("#more-detail");
    if (!detail) return;
    detail.classList.remove("hidden");
    detail.innerHTML = '<h3>狼人杀</h3><p style="color:#64748b">正在加载...</p>';
    try {
      const [boardsResp, sessionsResp] = await Promise.all([
        fetchJson("/api/werewolf/boards"),
        fetchJson("/api/werewolf/sessions")
      ]);
      const boards = boardsResp?.data?.boards || {};
      const sessions = sessionsResp?.data || {};
      const boardKeys = Object.keys(boards);
      let html = '<h3>🐺 狼人杀模式</h3>';
      html += '<p style="color:#64748b;margin-bottom:16px;font-size:13px">13 个 AI 模型扮演不同角色进行策略博弈。后端已就绪，可直接开局。</p>';
      html += '<h4 style="font-size:13px;font-weight:600;margin-bottom:8px">可用板型（' + boardKeys.length + ' 种）</h4>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-bottom:16px">';
      for (const key of boardKeys) {
        const b = boards[key];
        html += '<div style="padding:10px 12px;background:var(--bg-card,#f1f3f8);border:1px solid var(--line,#e2e8f0);border-radius:8px;font-size:12px">';
        html += '<div style="font-weight:700;margin-bottom:2px">' + escapeHtml(b.name || key) + '</div>';
        html += '<div style="color:#64748b">' + escapeHtml(b.desc || '') + '</div>';
        html += '<div style="color:#94a3b8;font-size:11px;margin-top:4px">' + (b.seat_count || '?') + ' 人</div>';
        html += '</div>';
      }
      html += '</div>';
      html += '<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--line,#e2e8f0)">';
      html += '<p style="font-size:12px;color:#94a3b8">开局方式：在 Ask 面板输入"开始狼人杀"或使用 /api/werewolf/start 接口。</p>';
      html += '</div>';
      detail.innerHTML = html;
      try { detail.scrollIntoView({ behavior: "smooth", block: "nearest" }); } catch(_){}
    } catch (e) {
      detail.innerHTML = '<h3>🐺 狼人杀</h3><p style="color:#dc2626">加载失败：' + escapeHtml(e.message) + '</p>';
    }
    return;
  }
  if (id === "sports") {
    const detail = $("#more-detail");
    if (!detail) return;
    detail.classList.remove("hidden");
    detail.innerHTML = '<h3>赛事预测</h3><p style="color:#64748b">正在检查...</p>';
    try {
      const [healthResp, summaryResp] = await Promise.all([
        fetchJson("/api/worldcup-pool/health"),
        fetchJson("/api/worldcup-pool/runtime-summary")
      ]);
      const health = healthResp?.data || {};
      let html = '<h3>🏟️ 赛事预测池</h3>';
      html += '<p style="color:#64748b;margin-bottom:16px;font-size:13px">13 个 AI 模型独立分析同一赛事，模拟预测准确度。不构成现实投资建议。</p>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:16px">';
      html += '<div style="padding:12px;background:var(--bg-card,#f1f3f8);border:1px solid var(--line,#e2e8f0);border-radius:8px;text-align:center"><div style="font-size:20px;font-weight:800;color:' + (health.ok ? '#059669' : '#dc2626') + '">' + (health.ok ? '在线' : '离线') + '</div><div style="font-size:11px;color:#94a3b8">后端状态</div></div>';
      html += '<div style="padding:12px;background:var(--bg-card,#f1f3f8);border:1px solid var(--line,#e2e8f0);border-radius:8px;text-align:center"><div style="font-size:20px;font-weight:800">14</div><div style="font-size:11px;color:#94a3b8">AI 席位</div></div>';
      html += '<div style="padding:12px;background:var(--bg-card,#f1f3f8);border:1px solid var(--line,#e2e8f0);border-radius:8px;text-align:center"><div style="font-size:20px;font-weight:800">' + (health.pool_app_exists ? '✅' : '❌') + '</div><div style="font-size:11px;color:#94a3b8">前端应用</div></div>';
      html += '</div>';
      html += '<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--line,#e2e8f0)">';
      html += '<a href="/worldcup_pool.html" target="_blank" style="display:inline-block;padding:8px 16px;background:#2563eb;color:#fff;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none">打开预测池页面</a>';
      html += '</div>';
      detail.innerHTML = html;
      try { detail.scrollIntoView({ behavior: "smooth", block: "nearest" }); } catch(_){}
    } catch (e) {
      detail.innerHTML = '<h3>🏟️ 赛事预测</h3><p style="color:#dc2626">加载失败：' + escapeHtml(e.message) + '</p>';
    }
    return;
  }
  if (id === "gavel") {
    const digest = await fetchJson("/api/gavel/digest");
    const runGavel = runId ? await fetchJson(`/api/gavel/${runId}`) : { ok: false, data: { required_context: "run_id" } };
    renderMoreDetailHtml("签字 / 归档", "Human Gavel 和归档状态。",
      `<div class="more-actions">
        ${runId ? `<button type="button" data-more-command="gavel-sync-run" data-run-id="${escapeAttr(runId)}">同步当前 run 签字</button>` : ""}
        <button type="button" data-more-command="gavel-sync-all">批量同步签字</button>
      </div>`,
      { digest, current_run: runGavel });
    return;
  }
  if (id === "status") {
    const [health, release, bridge] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/api/release/status"),
      fetchJson("/api/bridge/status")
    ]);
    const integrity = health?.data?.release_integrity || health?.data?.integrity || "unknown";
    renderMoreDetail("系统状态", `当前 release integrity=${integrity}；高级详情如下。`, { health, release, bridge });
  }
}

async function handleMoreCommand(commandEl) {
  const command = commandEl?.dataset?.moreCommand;
  const runId = commandEl?.dataset?.runId || currentRunId();
  commandEl.disabled = true;
  const originalText = commandEl.textContent;
  commandEl.textContent = "处理中…";
  try {
    let result;
    if (command === "followup") {
      const prompt = ($("#more-followup-prompt")?.value || "").trim();
      if (!prompt) throw new Error("请输入追问内容");
      result = await fetchJson(`/api/runs/${runId}/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      renderMoreDetail("继续追问", result.ok ? "追问已保存到当前 run 上下文。" : "追问保存失败。", result);
      return;
    }
    if (command === "resolve-evidence") {
      const taskId = commandEl.dataset.taskId;
      const textarea = $$("[data-evidence-resolution]").find(el => el.dataset.evidenceResolution === taskId);
      const resolution = (textarea?.value || "").trim();
      if (!resolution) throw new Error("请输入证据处理结果");
      result = await fetchJson(`/api/judge/${runId}/evidence-gaps/${encodeURIComponent(taskId)}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution }),
      });
      renderMoreDetail("证据", result.ok ? "证据缺口已写回。" : "证据缺口写回失败。", result);
      return;
    }
    if (command === "bridge-init") {
      result = await fetchJson("/api/bridge/init-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite: false }),
      });
      renderMoreDetail("设置", result.ok ? "桥接配置已初始化。" : "桥接配置初始化失败。", result);
      await loadSystemInfo();
      return;
    }
    if (command === "bridge-calibrate") {
      result = await fetchJson("/api/bridge/calibrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seats: [], timeout_seconds: 12 }),
      });
      renderMoreDetail("设置", result.ok ? "桥接校准完成。" : "桥接校准失败。", result);
      await loadSystemInfo();
      return;
    }
    if (command === "gavel-sync-run") {
      result = await fetchJson(`/api/gavel/${runId}/sync`, { method: "POST" });
      renderMoreDetail("签字 / 归档", result.ok ? "当前 run 签字已同步。" : "当前 run 签字同步失败。", result);
      return;
    }
    if (command === "gavel-sync-all") {
      result = await fetchJson("/api/gavel/sync-all", { method: "POST" });
      renderMoreDetail("签字 / 归档", result.ok ? "签字已批量同步。" : "批量同步失败。", result);
    }
  } catch (err) {
    renderMoreDetail("操作失败", err.message || "未知错误", { ok: false, error: err.message });
  } finally {
    commandEl.disabled = false;
    commandEl.textContent = originalText;
  }
}

/* ══════════ Core: Submit Judge (two-phase: pre-run confirm → actual submit) ══════════ */
function submitJudge() {
  const input = $("#ask-input");
  const question = (input?.value || "").trim();
  if (!question) return;

  // Initialize or reset the thread
  const threadId = "thread_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
  state.currentThread = {
    threadId,
    runId: "",  // ← intentionally empty: only set after "开始裁决"
    mode: state.selectedMode,
    stage: "aligning",
    question,
    alignedIntent: "",
    suggestedMode: "",
    promptSummary: [],
    messages: [],
    seatCards: [],
    attachments: (state.currentThread.attachments || []).map(a => ({...a})),
    artifacts: [],
    report: null,
  };

  // Add user_question message
  addThreadMessage({
    type: MSG_TYPE.USER_QUESTION,
    question,
    mode: state.selectedMode,
  });

  // Simulate Grand Judge alignment (in production this would call /api/prompt/resonate)
  // For now, we generate alignment from front-end state
  const alignedIntent = generateAlignment(question, state.selectedMode);
  state.currentThread.alignedIntent = alignedIntent.alignedIntent;
  state.currentThread.suggestedMode = alignedIntent.suggestedMode;
  state.currentThread.promptSummary = alignedIntent.promptSummary;

  // Add judge_alignment message
  addThreadMessage({
    type: MSG_TYPE.JUDGE_ALIGNMENT,
    alignedIntent: alignedIntent.alignedIntent,
    suggestedMode: alignedIntent.suggestedMode,
  });

  // Add seat_prompt_preview message
  const activeSeats = resolveActiveSeats();
  addThreadMessage({
    type: MSG_TYPE.SEAT_PROMPT_PREVIEW,
    seats: activeSeats,
    promptSummary: alignedIntent.promptSummary.join("\n"),
  });

  // Add attachment_context message if there are attachments
  const atts = state.currentThread.attachments || [];
  if (atts.length > 0) {
    addThreadMessage({
      type: MSG_TYPE.ATTACHMENT_CONTEXT,
      attachments: atts,
    });
  }

  state.currentThread.stage = "waiting_confirm";

  // Show align view (pre-run confirmation)
  showAlignView();
  renderAlign();
}

function generateAlignment(question, mode) {
  const cfg = getModeConfig(mode);
  const seats = resolveActiveSeats();
  const seatNames = seats.map(s => s.name).join("、");

  return {
    alignedIntent: `我理解你的问题是：「${question}」\n\n我将使用 ${cfg.label} 模式来处理这个问题。${cfg.label === "深度裁决" ? "我会组织多个席位交叉验证，形成可审计的裁决报告。" : "我会快速给出明确结论、关键理由和下一步建议。"}`,
    suggestedMode: cfg.label,
    promptSummary: [
      `模式：${cfg.label}`,
      `参审席位：${seatNames}`,
      `系统指令：${cfg.systemInstruction.slice(0, 60)}...`,
    ],
  };
}

async function executeJudge() {
  const thread = state.currentThread;
  const question = thread.question;
  if (!question) return;

  const cfg = getModeConfig(thread.mode || state.selectedMode);
  thread.stage = "running";
  state.currentThread = thread;

  state.workflow.stage = WORKFLOW_STAGE.RUNNING;
  state.workflow.canPause = true;
  state.workflow.completedSeats = new Set();
  state.workflow.activeSeatCount = 0;
  state.currentVerdict = null;

  hideAlignTab();
  switchTab("room");
  setBusy(true);
  setProgress(3, "提交中…");
  $("#room-phase").textContent = "正在开庭…";
  $("#room-status").textContent = "席位就绪中";

  // Pre-render all seats as waiting before SSE events arrive
  const activeSeats = resolveActiveSeats();
  state._pendingSeats = activeSeats;

  // Add run_started message (now we have a real run_id)
  addThreadMessage({
    type: MSG_TYPE.RUN_STARTED,
    runId: "(提交中...)",
  });

  try {
    // ── P1.5: Build seat_config payload ──
    const settings = state.judgeSettings;
    const seatCfg = {};
    if (settings.mode === "custom" && settings.selectedSeats.length > 0) {
      seatCfg.selected = settings.selectedSeats;
    }
    if (settings.excludedSeats.length > 0) {
      seatCfg.excluded = settings.excludedSeats;
    }
    seatCfg.partial_policy = settings.partialPolicy || "allow";

    // Save default if checked
    if (settings.saveAsDefault) {
      saveUserSettings();
      settings.saveAsDefault = false;
    }

    const res = await fetch(API_BASE + "/api/judge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode: settings.mode || thread.mode || state.selectedMode,
        engine: state.engine,
        client_entrypoint: "dashboard_web_client",
        abstained_seats: defaultAbstainedSeats(),
        mode_label: cfg.label,
        system_instruction: cfg.systemInstruction,
        seat_config: Object.keys(seatCfg).length > 0 ? seatCfg : undefined,
        report_style: settings.reportStyle || "concise",
        attachments: (thread.attachments || []).map(att => ({
          id: att.id, name: att.name, size: att.size, type: att.type,
          server_attachment_id: att.serverAttachmentId || "",
          server_path: att.serverPath || "",
          textPreview: att.textPreview || "", textContent: att.textContent || "",
          contentAvailable: !!att.contentAvailable,
        })),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "HTTP " + res.status);

    // NOW we have a real run_id — update thread and the run_started message
    thread.runId = data.run_id;
    state.currentThread = thread;
    state.currentRunId = data.run_id;
    state.workflow.runId = data.run_id;
    if (Array.isArray(data.seats)) {
      state._pendingSeats = data.seats.map(id => {
        const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === id) || {};
        return {
          id,
          name: seatInfo.name || id,
          channel: seatInfo.channel || "",
          color: seatInfo.color || "#64748b",
          state: "waiting",
          ready: true,
        };
      });
    }

    // Update the run_started message with real run_id
    const msgs = state.currentThread.messages;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].type === MSG_TYPE.RUN_STARTED) {
        msgs[i].runId = data.run_id;
        break;
      }
    }

    state.currentTask = {
      run_id: data.run_id, question, status: "running", progress: 0.03,
      current_step: "提交成功，等待席位回应…",
    };
    startProgress(data.run_id);
    loadHistory();

    // Re-render threads to show updated run_id
    renderThreadMessages("ask-thread-messages");
    renderThreadMessages("room-thread-messages");

  } catch (err) {
    state.currentThread.stage = "failed";
    state.workflow.stage = WORKFLOW_STAGE.FAILED;
    state.workflow.canPause = false;
    setProgress(0, "提交失败：" + err.message);
    setBusy(false);

    addThreadMessage({
      type: MSG_TYPE.SYSTEM_ERROR,
      error: err.message,
    });
  }
}

/* ══════════ Resolve active seats — FULL 13-seat support ══════════ */
function resolveActiveSeats() {
  // Priority 1: user explicitly selected seats in settings (custom mode)
  if (state.judgeSettings.mode === "custom" && state.judgeSettings.selectedSeats.length > 0) {
    return state.judgeSettings.selectedSeats.map(id => {
      const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === id) || {};
      // Check runnability from cached seat status
      const seatStatus = (_cachedSeatStatus || []).find(s => s.id === id);
      const ready = seatStatus ? seatStatus.ready !== false : true;
      return {
        id, name: seatInfo.name || id, channel: seatInfo.channel || "",
        ready, state: ready ? "waiting" : "unavailable",
        color: seatInfo.color || "#64748b",
        reason: !ready ? (seatStatus?.reason || "不可用") : undefined,
      };
    });
  }

  // Priority 2: /api/judge returned seats (from backend)
  if (state._pendingSeats && state._pendingSeats.length > 0) {
    return state._pendingSeats;
  }

  // Priority 3: bridge status
  if (state.bridge?.seats && state.bridge.seats.length > 0) {
    return state.bridge.seats.filter(s => !defaultAbstainedSeats().includes(s.id || s.seat)).map(s => ({
      id: s.id || s.seat, name: s.name || s.id || s.seat, channel: s.channel || "",
      ready: s.ready !== false, state: s.ready !== false ? "waiting" : "unavailable",
      color: s.color || "#64748b",
    }));
  }

  // Priority 4: use API-default seats per mode (flash=3, strategic=all-ready)
  // Priority 4a: try cached seat status + mode defaults
  const mode = state.judgeSettings.mode || state.selectedMode;
  const cached = _cachedSeatStatus;
  const cachedDefaults = _cachedSeatDefaults || {};
  const modeDefaultIds = cachedDefaults[mode];
  if (cached && cached.length > 0 && modeDefaultIds && modeDefaultIds.length > 0) {
    const abstained = defaultAbstainedSeats();
    const readySeats = cached.filter(s => s.ready && !abstained.includes(s.id));
    // For flash/strategic: filter ready seats to mode defaults only
    if (mode === "flash" || mode === "strategic") {
      const filtered = readySeats.filter(s => modeDefaultIds.includes(s.id));
      if (filtered.length > 0) {
        return filtered.map(s => ({
          id: s.id, name: s.name || s.id, channel: s.channel || "",
          color: s.color || "#64748b", ready: true, state: "waiting",
        }));
      }
    }
    // Fallback: all ready seats (minus abstained)
    if (readySeats.length > 0) {
      return readySeats.map(s => ({
        id: s.id, name: s.name || s.id, channel: s.channel || "",
        color: s.color || "#64748b", ready: true, state: "waiting",
      }));
    }
  }

  // Priority 4b: PARLIAMENT_SEATS — full list (minus abstained)
  const abstained = defaultAbstainedSeats();
  return PARLIAMENT_SEATS
    .filter(s => !abstained.includes(s.id))
    .map(s => ({ id: s.id, name: s.name, channel: s.channel, color: s.color, ready: true, state: "waiting" }));
}

function startProgress(runId) {
  if (state.eventSource) state.eventSource.close();
  if (state.pollTimer) clearInterval(state.pollTimer);

  if ("EventSource" in window) {
    state.eventSource = new EventSource(API_BASE + "/api/judge/" + runId + "/progress");
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
      const res = await fetch(API_BASE + "/api/task/" + runId);
      handleTask(await res.json());
    } catch (_) {}
  }, 5000);
}

function handleTask(task) {
  if (task.error && !task.status) {
    setProgress(0, task.error);
    setBusy(false);
    addThreadMessage({ type: MSG_TYPE.SYSTEM_ERROR, error: task.error });
    return;
  }
  if (state.currentThread.stage === "cancelled") return;
  if (state.currentThread.stage === "paused") {
    state.currentTask = task;
    return;
  }

  state.currentTask = task;
  const pct = Math.round((Number(task.progress) || 0) * 100);
  setProgress(pct, task.current_step || task.status || "运行中");

  // Process seat-level events and inject into thread
  if (task.progress_diagnostics?.seats) {
    task.progress_diagnostics.seats.forEach(s => {
      const seatId = s.seat || s.id;
      const seatStatus = s.state || s.status || "";

      // Check if we already have a message for this seat transition
      const existingMsgs = state.currentThread.messages;
      const alreadyHas = existingMsgs.some(m =>
        (m.seatId === seatId || (m.seat && m.seat.id === seatId)) &&
        ((m.type === MSG_TYPE.SEAT_ANSWERED && seatStatus === "complete") ||
         (m.type === MSG_TYPE.SEAT_TIMEOUT && seatStatus === "timeout"))
      );

      if (!alreadyHas) {
        if (seatStatus === "complete" || seatStatus === "done" || seatStatus === "answered") {
          const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === seatId) || {};
          addThreadMessage({
            type: MSG_TYPE.SEAT_ANSWERED,
            seatId,
            seat: { id: seatId, name: seatInfo.name || seatId, color: seatInfo.color || "#64748b" },
            answerPreview: s.answer_preview || (s.answer || "").slice(0, 120) || "已回答",
            fullAnswer: s.answer || "",
          });
        } else if (seatStatus === "timeout") {
          const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === seatId) || {};
          addThreadMessage({
            type: MSG_TYPE.SEAT_TIMEOUT,
            seatId,
            seat: { id: seatId, name: seatInfo.name || seatId, color: seatInfo.color || "#64748b" },
          });
        } else if (seatStatus === "submitted" || seatStatus === "running" || seatStatus === "speaking" || seatStatus === "waiting" || seatStatus === "pending") {
          const alreadySubmitted = existingMsgs.some(m => m.type === MSG_TYPE.SEAT_SUBMITTED && (m.seatId === seatId || (m.seat && m.seat.id === seatId)));
          if (!alreadySubmitted) {
            const seatInfo = PARLIAMENT_SEATS.find(ps => ps.id === seatId) || {};
            addThreadMessage({
              type: MSG_TYPE.SEAT_SUBMITTED,
              seatId,
              seat: { id: seatId, name: seatInfo.name || seatId, color: seatInfo.color || "#64748b" },
            });
          }
        }
      }
    });
  }

  // Update room rendering with task data
  renderRoom();

  if (task.status === "complete") {
    cleanupProgress();
    setBusy(false);
    setProgress(100, "已完成");
    if (task.result) {
      renderVerdict(task.result);
    } else {
      loadVerdict(task.run_id);
    }
    loadHistory();
    state.currentThread.stage = "report_ready";
    updateRoomReportButton();
    state.workflow.stage = WORKFLOW_STAGE.COMPLETED;
    state.workflow.canPause = false;

    // Add judge_summary and report_ready messages
    if (task.result) {
      addThreadMessage({
        type: MSG_TYPE.JUDGE_SUMMARY,
        verdict: task.result.one_liner || "裁决完成",
        summary: (task.result.key_reasons || []).slice(0, 2).join("；"),
        confidence: task.result.confidence || 0,
      });
    }
    addThreadMessage({
      type: MSG_TYPE.REPORT_READY,
      runId: task.run_id,
    });
  }
  if (task.status === "failed" || task.status === "cancelled") {
    cleanupProgress();
    setBusy(false);
    // ── Task 5: Enhanced error diagnosis ──
    const errMsg = (task.error || "").toLowerCase();
    let diagnosis = "";
    let actions = "";

    if (errMsg.includes("chrome") || errMsg.includes("浏览器") || errMsg.includes("cdp") || errMsg.includes("chromedriver")) {
      diagnosis = "Chrome 浏览器未就绪，请确保 AI Judge Chrome 已打开";
      actions = `<button onclick="retryCurrentRun()" class="btn-primary" style="margin-right:8px">重试</button>`;
    } else if (errMsg.includes("login") || errMsg.includes("session") || errMsg.includes("expired") || errMsg.includes("auth") || errMsg.includes("登录")) {
      diagnosis = "以下席位需要重新登录：" + (task.failed_seats || []).map(s => s.name || s.seat || s).join("、") || "部分席位";
      actions = `<button onclick="skipFailedSeats()" class="btn-primary" style="margin-right:8px">跳过失败席位继续</button>`;
    } else if (errMsg.includes("timeout") || errMsg.includes("超时")) {
      const doneCount = task.completed_seats?.length || (task.progress_diagnostics?.seats || []).filter(s => s.ok || s.status === "complete").length || 0;
      const totalCount = task.total_seats || "?";
      diagnosis = `执行超时，已完成 ${doneCount}/${totalCount} 席位`;
      actions = `<button onclick="viewPartialResults()" class="btn-primary" style="margin-right:8px">查看部分结果</button>`;
    } else if (errMsg.includes("connection refused") || errMsg.includes("network") || errMsg.includes("unreachable") || errMsg.includes("econnrefused")) {
      diagnosis = "AI Judge 服务未运行";
      actions = `<span style="font-size:13px;color:var(--text-soft)">请确保后端服务已启动后重试</span>`;
    } else {
      diagnosis = task.error || ("任务" + task.status);
    }

    setProgress(pct, diagnosis);
    state.currentThread.stage = task.status === "cancelled" ? "cancelled" : "failed";
    state.workflow.stage = task.status === "cancelled" ? WORKFLOW_STAGE.CANCELLED : WORKFLOW_STAGE.FAILED;
    state.workflow.canPause = false;

    // Update room phase with diagnosis
    const phase = $("#room-phase");
    if (phase) phase.innerHTML = `${diagnosis} ${actions}`;

    renderRoom();

    addThreadMessage({
      type: MSG_TYPE.SYSTEM_ERROR,
      error: task.error || ("任务" + task.status),
    });
  }
}

async function loadVerdict(runId) {
  try {
    const res = await fetch(API_BASE + "/api/judge/" + runId + "/verdict");
    const v = await res.json();
    if (res.ok) renderVerdict(v);
  } catch (_) {}
}

function renderVerdict(v) {
  state.currentVerdict = v;
  state.currentThread.report = v;
  state.currentThread.stage = "report_ready";
  renderRoom();
  updateRoomReportButton();
  renderReport();

  // Add summary + report_ready if not already present
  const hasSummary = state.currentThread.messages.some(m => m.type === MSG_TYPE.JUDGE_SUMMARY);
  if (!hasSummary) {
    addThreadMessage({
      type: MSG_TYPE.JUDGE_SUMMARY,
      verdict: v.one_liner || "裁决完成",
      summary: (v.key_reasons || []).slice(0, 2).join("；"),
      confidence: v.confidence || 0,
    });
  }
  const hasReportReady = state.currentThread.messages.some(m => m.type === MSG_TYPE.REPORT_READY);
  if (!hasReportReady) {
    addThreadMessage({
      type: MSG_TYPE.REPORT_READY,
      runId: v.run_id,
    });
  }
}

/* ══════════ Run Control (Pause/Resume/Stop) ══════════ */
async function pauseCurrentRun() {
  const runId = state.currentThread.runId || state.currentRunId;
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + runId + "/pause", { method: "POST" });
    if (res.ok) {
      state.currentThread.stage = "paused";
      state.workflow.stage = WORKFLOW_STAGE.PAUSED;
      state.workflow.paused = true;
      $("#btn-pause-judge").classList.add("hidden");
      $("#btn-resume-judge").classList.remove("hidden");
      $("#room-phase").textContent = "已暂停 — 不再启动新席位";
    }
  } catch (_) {}
}

async function resumeCurrentRun() {
  const runId = state.currentThread.runId || state.currentRunId;
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + runId + "/resume", { method: "POST" });
    if (res.ok) {
      state.currentThread.stage = "running";
      state.workflow.stage = WORKFLOW_STAGE.RUNNING;
      state.workflow.paused = false;
      $("#btn-pause-judge").classList.remove("hidden");
      $("#btn-resume-judge").classList.add("hidden");
      startProgress(runId);
    }
  } catch (_) {}
}

async function stopCurrentRun() {
  const runId = state.currentThread.runId || state.currentRunId;
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + runId + "/stop", { method: "POST" });
    if (res.ok) {
      state.currentThread.stage = "cancelled";
      state.workflow.stage = WORKFLOW_STAGE.CANCELLED;
      $$("#room-controls button").forEach(b => b.classList.add("hidden"));
      cleanupProgress();
      setBusy(false);

      addThreadMessage({
        type: MSG_TYPE.SYSTEM_ERROR,
        error: "用户终止了本次裁决",
      });
    }
  } catch (_) {}
}

/* ── Task 5: Error recovery helpers ── */
function retryCurrentRun() {
  const runId = state.currentThread.runId || state.currentRunId;
  if (!runId) return;
  state.currentThread.stage = "running";
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;
  startProgress(runId);
  renderRoom();
}

async function skipFailedSeats() {
  const runId = state.currentThread.runId || state.currentRunId;
  if (!runId) return;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + runId + "/rerun-failed", { method: "POST" });
    if (res.ok) {
      state.currentThread.stage = "running";
      startProgress(runId);
    }
  } catch (_) {}
}

function viewPartialResults() {
  const v = state.currentVerdict;
  const task = state.currentTask;
  if (v) {
    renderVerdict(v);
  } else if (task?.run_id) {
    loadVerdict(task.run_id);
  }
  switchTab("report");
}

/* ══════════ History ══════════ */
async function loadHistory() {
  try {
    const res = await fetch(API_BASE + "/api/runs/recent");
    const data = await res.json();
    if (res.ok && Array.isArray(data.runs)) {
      state.historyRuns = data.runs;
    } else if (Array.isArray(data)) {
      state.historyRuns = data;
    }
  } catch (_) {}
}

/* ══════════ Busy State ══════════ */
function setBusy(busy) {
  const btn = $("#btn-send");
  if (btn) btn.disabled = busy;
}

/* ══════════ File Attach (existing + image tool) ══════════ */
async function uploadAttachmentToServer(file, { forceBinary = false } = {}) {
  const textLike = !forceBinary && isTextLikeFile(file);
  let text = "";
  let contentBase64 = "";
  if (textLike) {
    text = await file.text();
  } else {
    contentBase64 = await fileToBase64(file);
  }
  const res = await fetch(API_BASE + "/api/attachments/upload", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_id: currentDraftId(),
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
      content: text,
      content_base64: contentBase64,
    }),
  });
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error(data.error || "attachment upload failed");
  return {
    id: "att_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
    serverAttachmentId: data.attachment_id || "",
    serverPath: data.path || "",
    uploaded: true,
    name: data.name || file.name,
    size: data.size || file.size,
    type: data.type || file.type,
    textPreview: data.text_preview || text.slice(0, 1000),
    textContent: text.slice(0, 50000),
    contentAvailable: !!data.content_available,
    imageNote: textLike ? undefined : "图片/二进制已上传到后端，裁决会收到文件路径和元数据",
  };
}

async function handleFileAttach() {
  const files = $("#file-input").files;
  if (!files || !files.length) return;
  for (const file of files) {
    try {
      state.currentThread.attachments.push(await uploadAttachmentToServer(file));
    } catch (err) {
      state.currentThread.attachments.push({
        id: "att_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        name: file.name,
        size: file.size,
        type: file.type,
        contentAvailable: false,
        uploadError: err.message || "上传失败",
        imageNote: file.type?.startsWith("image/") ? "图片上传失败，仅保留本地元数据" : undefined,
      });
    }
  }
  $("#file-input").value = "";
  renderAttachChips();
}

function renderAttachChips() {
  const container = $("#attach-chips");
  if (!container) return;
  const atts = state.currentThread.attachments || [];
  if (atts.length === 0) {
    container.innerHTML = "";
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");
  container.innerHTML = atts.map(a =>
    `<span class="attach-chip-inline">
      ${escapeHtml(a.name)}
      ${a.uploaded ? ' <span style="color:var(--green);font-size:10px;">已上传</span>' : ''}
      ${a.uploadError ? ' <span style="color:var(--red);font-size:10px;">上传失败</span>' : ''}
      ${a.imageNote ? ' <span style="color:var(--amber);font-size:10px;">图片</span>' : ''}
      <button class="chip-close" data-att-id="${escapeAttr(a.id)}" title="移除">&times;</button>
    </span>`
  ).join("");

  // Bind remove handlers
  container.querySelectorAll(".chip-close").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.attId;
      state.currentThread.attachments = (state.currentThread.attachments || []).filter(a => a.id !== id);
      renderAttachChips();
    });
  });
}

/* ══════════ Image Upload Tool ══════════ */
function handleImageAttach() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.multiple = true;
  input.addEventListener("change", async () => {
    const files = input.files;
    if (!files || !files.length) return;
    for (const file of files) {
      try {
        state.currentThread.attachments.push(await uploadAttachmentToServer(file, { forceBinary: true }));
      } catch (err) {
        state.currentThread.attachments.push({
          id: "img_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
          name: file.name,
          size: file.size,
          type: file.type,
          contentAvailable: false,
          uploadError: err.message || "上传失败",
          imageNote: "图片上传失败，仅保留本地元数据",
        });
      }
    }
    renderAttachChips();
  });
  input.click();
}

/* ══════════ Work/History Run Tool ══════════ */
async function handleWorkAttach() {
  // Fetch recent runs and show selector
  try {
    const res = await fetch(API_BASE + "/api/runs/recent");
    const data = await res.json();
    const runs = Array.isArray(data) ? data : (data.runs || []);

    if (!runs.length) {
      alert("暂无历史运行记录");
      return;
    }

    // Create a simple selector modal
    const modal = document.createElement("div");
    modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:1000;";
    modal.innerHTML = `
      <div style="background:#fff;padding:24px;border-radius:14px;max-width:600px;width:90%;max-height:70vh;overflow:auto;box-shadow:0 8px 32px rgba(0,0,0,0.15);">
        <h3 style="margin-bottom:16px;font-size:16px;">选择历史运行报告作为上下文</h3>
        <div id="work-selector-list" style="display:flex;flex-direction:column;gap:8px;"></div>
        <button onclick="this.closest('[style*=\"position:fixed\"]').remove()" style="margin-top:16px;padding:8px 20px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer;">取消</button>
      </div>
    `;
    document.body.appendChild(modal);

    const list = modal.querySelector("#work-selector-list");
    runs.slice(0, 20).forEach(run => {
      const runId = run.run_id || run.id || "";
      const question = run.question || run.query || "(无问题)";
      const verdict = run.one_liner || run.verdict || "";
      const btn = document.createElement("button");
      btn.style.cssText = "text-align:left;padding:10px 14px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;font-size:13px;";
      btn.innerHTML = `<div style="font-weight:600;margin-bottom:4px;">${escapeHtml(excerpt(question, 60))}</div><div style="font-size:11px;color:var(--text-soft);">${escapeHtml(excerpt(verdict, 80))}</div><div style="font-size:10px;color:var(--text-muted);margin-top:4px;">${escapeHtml(runId)}</div>`;
      btn.addEventListener("click", () => {
        // Add as work attachment
        state.currentThread.attachments.push({
          id: "work_" + runId,
          name: "历史报告：" + excerpt(question, 40),
          run_id: runId,
          source: "run_report",
          textPreview: verdict || question,
          contentAvailable: true,
        });
        renderAttachChips();
        modal.remove();
      });
      list.appendChild(btn);
    });
  } catch (e) {
    alert("无法加载历史运行记录：" + e.message);
  }
}

/* ══════════ Tool Button Menu ══════════ */
function showToolMenu() {
  // Toggle tool menu
  let menu = $("#tool-menu");
  if (menu) {
    menu.remove();
    return;
  }
  menu = document.createElement("div");
  menu.id = "tool-menu";
  menu.style.cssText = "position:absolute;bottom:50px;left:16px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:200;min-width:180px;";
  menu.innerHTML = `
    <button class="tool-menu-item" data-tool="file" style="display:flex;align-items:center;gap:8px;width:100%;padding:10px 16px;border:none;background:none;cursor:pointer;font-size:13px;text-align:left;">📄 添加文件</button>
    <button class="tool-menu-item" data-tool="image" style="display:flex;align-items:center;gap:8px;width:100%;padding:10px 16px;border:none;background:none;cursor:pointer;font-size:13px;text-align:left;">🖼️ 添加图片</button>
    <button class="tool-menu-item" data-tool="work" style="display:flex;align-items:center;gap:8px;width:100%;padding:10px 16px;border:none;background:none;cursor:pointer;font-size:13px;text-align:left;">📋 添加作品（历史报告）</button>
  `;
  // Position near the tool button
  const toolBtn = $("#btn-tool");
  if (toolBtn) {
    const rect = toolBtn.getBoundingClientRect();
    menu.style.left = rect.left + "px";
    menu.style.bottom = (window.innerHeight - rect.top + 8) + "px";
  }
  document.body.appendChild(menu);

  menu.querySelector('[data-tool="file"]').addEventListener("click", () => {
    menu.remove();
    $("#file-input").click();
  });
  menu.querySelector('[data-tool="image"]').addEventListener("click", () => {
    menu.remove();
    handleImageAttach();
  });
  menu.querySelector('[data-tool="work"]').addEventListener("click", () => {
    menu.remove();
    handleWorkAttach();
  });

  // Close on click outside
  setTimeout(() => {
    const closeHandler = (e) => {
      if (menu && !menu.contains(e.target) && e.target !== $("#btn-tool")) {
        menu.remove();
        document.removeEventListener("click", closeHandler);
      }
    };
    document.addEventListener("click", closeHandler);
  }, 0);
}

/* ══════════ Init ══════════ */
document.addEventListener("DOMContentLoaded", async () => {
  loadUserSettings();
  bindUI();
  switchTab("ask");
  renderAsk();
  loadSystemInfo();
  await loadHistory();
  // Don't call renderMemory here — it's backend-driven and will be called when user clicks Memory tab
});

function bindUI() {
  // Tab clicks
  $$("#main-tabs .tab").forEach(tab => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));

  // Topbar status click
  $("#topbar-status").addEventListener("click", toggleSysPanel);

  // Mode toggle
  $$(".ask-mode-toggle .seg").forEach(seg => {
    seg.addEventListener("click", () => switchMode(seg.dataset.mode));
  });

  // Send button — goes to Align (pre-run confirm), does NOT call /api/judge
  $("#btn-send").addEventListener("click", () => submitJudge());

  // Enter to submit
  $("#ask-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitJudge();
    }
  });

  // File input change handler (file attach via tool menu)
  $("#file-input").addEventListener("change", handleFileAttach);

  // Tool button — now defined in HTML as #btn-tool
  const toolBtn = $("#btn-tool");
  if (toolBtn) {
    toolBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      showToolMenu();
    });
  }

  // ── P2.3: Drag & drop files into Ask ──
  const askArea = $("#ask-input-area");
  if (askArea) {
    askArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      askArea.classList.add("drag-over");
    });
    askArea.addEventListener("dragleave", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!askArea.contains(e.relatedTarget)) {
        askArea.classList.remove("drag-over");
      }
    });
    askArea.addEventListener("drop", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      askArea.classList.remove("drag-over");
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length === 0) return;
      for (const f of files) {
        const ext = (f.name || "").split(".").pop().toLowerCase();
        const supportedText = ["txt","md","json","csv","log","yaml","yml","js","py","ts","html","css","sh"];
        const supportedImg = ["png","jpg","jpeg","gif","webp","svg","bmp"];
        if (supportedText.includes(ext)) {
          await uploadAttachmentToServer(f);
          renderAttachChips();
          addThreadMessage({
            type: MSG_TYPE.ATTACHMENT_ADDED,
            fileName: f.name,
            fileSize: f.size,
          });
        } else if (supportedImg.includes(ext)) {
          await uploadAttachmentToServer(f);
          renderAttachChips();
          addThreadMessage({
            type: MSG_TYPE.ATTACHMENT_ADDED,
            fileName: f.name,
            isImage: true,
          });
        } else {
          showToast("不支持的文件类型: ." + ext);
        }
      }
    });
  }

  // ── P2.3: Agent turn card click-to-expand delegation ──
  const roomMessages = $("#room-thread-messages");
  if (roomMessages) {
    roomMessages.addEventListener("click", (event) => {
      const btn = event.target.closest(".turn-expand-btn");
      if (btn) {
        const card = btn.closest(".agent-turn-card");
        if (card) {
          card.classList.toggle("expanded");
          card.setAttribute("aria-expanded", card.classList.contains("expanded") ? "true" : "false");
        }
      }
    });
  }

  // ── P2.3: Report button in Room ──
  const roomReportBtn = $("#btn-room-open-report");
  if (roomReportBtn) {
    roomReportBtn.addEventListener("click", () => {
      const verdict = state.currentVerdict;
      const runId = state.currentThread.runId || (verdict?.run_id);
      if (verdict || state.currentThread.stage === "report_ready") {
        if (runId) {
          // open report page
          window.trackEvent?.("report_button_clicked", { runId });
          window.open(API_BASE + "/api/runs/" + runId + "/index.html", "_blank");
          window.trackEvent?.("report_opened", { runId });
        } else {
          switchTab("report");
          renderReport();
        }
      } else {
        showToast("报告尚未生成");
        window.trackEvent?.("report_not_ready", { stage: state.currentThread.stage });
      }
    });
  }

  // Run controls
  $("#btn-pause-judge").addEventListener("click", pauseCurrentRun);
  $("#btn-resume-judge").addEventListener("click", resumeCurrentRun);
  $("#btn-stop-judge").addEventListener("click", stopCurrentRun);

  // Align buttons
  $("#btn-start-judge").addEventListener("click", () => {
    executeJudge();
  });
  $("#btn-edit-question").addEventListener("click", () => {
    hideAlignTab();
    switchTab("ask");
    $("#ask-input").focus();
  });
  $("#btn-cancel-align").addEventListener("click", () => {
    hideAlignTab();
    state.currentThread.stage = "draft";
    switchTab("ask");
  });

  // More cards
  const moreView = $("#view-more");
  if (moreView) {
    moreView.addEventListener("click", (event) => {
      const command = event.target.closest("[data-more-command]");
      if (command) {
        handleMoreCommand(command);
        return;
      }
      const target = event.target.closest("[data-more-action]");
      if (target) openMoreFeature(target.dataset.moreAction, target);
    });
  }

  // Refresh button
  $("#btn-refresh").addEventListener("click", async () => {
    await loadHistory();
    loadSystemInfo();
    renderMemory();
  });
}

console.info("[AI Judge] P3.8.12-RC1 sealed", AI_JUDGE_CLIENT_BUILD);


/* ══════════ P1.2B User-facing Logs UI — Timeline ══════════ */

async function loadRunTimeline(runId) {
  if (!runId) return null;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + runId + "/timeline");
    if (!res.ok) return null;
    return await res.json();
  } catch (_) {
    return null;
  }
}

function renderTimelineEventHTML(evt) {
  const dotColor = {
    run_started: "blue",
    align_created: "blue",
    seat_submitted: "gray",
    seat_answered: "green",
    seat_timeout: "orange",
    seat_skipped: "gray",
    pause_applied: "yellow",
    resume_applied: "yellow",
    stop_applied: "yellow",
    report_generated: "green big",
    followup_answer_returned: "blue",
    hermes_export_open_result: "green",
    followup_requested: "gray",
  }[evt.type] || "gray";

  const isWarn = evt.type === "seat_timeout" || evt.type === "stop_applied";
  const timeStr = evt.ts ? new Date(evt.ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "";
  const seatBadge = evt.seat ? `<span class="tl-seat">${escapeHtml(evt.seat)}</span>` : "";

  return `
    <div class="timeline-event${isWarn ? " is-warn" : ""}">
      <span class="tl-dot ${dotColor}"></span>
      <div class="tl-body">
        <span class="tl-title">${escapeHtml(evt.title)}</span>
        ${evt.description ? `<div class="tl-desc">${escapeHtml(evt.description)}</div>` : ""}
        <div class="tl-time">${escapeHtml(timeStr)} ${seatBadge}</div>
      </div>
    </div>`;
}

function renderUserTimeline(events, container) {
  if (!container) return;
  const uve = events.filter(e => e.user_visible && !e.advanced);
  if (!uve.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px;">暂无可见事件</div>';
    return;
  }
  container.innerHTML = uve.map(renderTimelineEventHTML).join("");
}

function renderAdvancedTimeline(events, container) {
  if (!container) return;
  const adv = events.filter(e => e.advanced);
  if (!adv.length) {
    if (container.parentElement) container.parentElement.hidden = true;
    return;
  }
  if (container.parentElement) container.parentElement.hidden = false;
  container.innerHTML = adv.map(renderTimelineEventHTML).join("");
}

function renderTimelineSummary(summary, container) {
  if (!container || !summary) return;
  const startTime = summary.started_at ? new Date(summary.started_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "—";
  const endTime = summary.completed_at ? new Date(summary.completed_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "—";
  const isComplete = summary.verdict_status === "complete";
  const isPartial = summary.verdict_status === "partial";

  container.innerHTML = `
    <div class="tl-stat${isComplete ? " complete" : ""}${isPartial ? " warn" : ""}">
      <div class="tl-stat-val">${summary.completed_seats || 0}</div>
      <div class="tl-stat-label">完成席位</div>
    </div>
    <div class="tl-stat${summary.failed_seats ? " warn" : ""}">
      <div class="tl-stat-val">${summary.failed_seats || 0}</div>
      <div class="tl-stat-label">失败席位</div>
    </div>
    <div class="tl-stat${summary.timeout_seats ? " warn" : ""}">
      <div class="tl-stat-val">${summary.timeout_seats || 0}</div>
      <div class="tl-stat-label">超时席位</div>
    </div>
    <div class="tl-stat">
      <div class="tl-stat-val">${escapeHtml(summary.mode || "—")}</div>
      <div class="tl-stat-label">模式</div>
    </div>
    <div class="tl-stat">
      <div class="tl-stat-val">${escapeHtml(isComplete ? "完整" : isPartial ? "部分" : summary.verdict_status || "—")}</div>
      <div class="tl-stat-label">裁决状态</div>
    </div>
    <div class="tl-stat">
      <div class="tl-stat-val">${startTime} ~ ${endTime}</div>
      <div class="tl-stat-label">时间</div>
    </div>`;
}

// ── Room timeline integration ──
async function renderRoomTimeline() {
  const runId = state.currentThread.runId || state.currentRunId;
  const zone = $("#room-timeline-zone");
  const eventsDiv = $("#room-timeline-events");
  const advDiv = $("#room-timeline-advanced-events");
  const advWrapper = $("#room-timeline-advanced");

  if (!runId || !zone) {
    if (zone) zone.hidden = true;
    return;
  }

  const data = await loadRunTimeline(runId);
  if (!data || !data.events || !data.events.length) {
    zone.hidden = true;
    return;
  }

  zone.hidden = false;
  renderUserTimeline(data.events, eventsDiv);
  if (advDiv) {
    renderAdvancedTimeline(data.events, advDiv);
    const advEvents = data.events.filter(e => e.advanced);
    if (advWrapper) advWrapper.hidden = !advEvents.length;
  }
}

// ── Report process summary integration ──
async function renderReportProcessSummary() {
  const runId = state.currentThread.runId || state.currentRunId;
  const zone = $("#report-process-zone");
  const summaryDiv = $("#report-process-summary");
  const eventsDiv = $("#report-process-events");
  const advDiv = $("#report-process-advanced-events");
  const advWrapper = $("#report-process-advanced");

  if (!runId || !zone) {
    if (zone) zone.classList.add("hidden");
    return;
  }

  const data = await loadRunTimeline(runId);
  if (!data || !data.events || !data.events.length) {
    zone.classList.add("hidden");
    return;
  }

  zone.classList.remove("hidden");
  if (summaryDiv) renderTimelineSummary(data.summary, summaryDiv);
  if (eventsDiv) renderUserTimeline(data.events, eventsDiv);
  if (advDiv) {
    renderAdvancedTimeline(data.events, advDiv);
    const advEvents = data.events.filter(e => e.advanced);
    if (advWrapper) advWrapper.hidden = !advEvents.length;
  }
}

// ── Memory timeline summary ──
function renderMemoryTimelineSummary(data, container) {
  if (!data || !data.summary) return "";
  const s = data.summary;
  const parts = [];
  if (s.completed_seats > 0) parts.push(`${s.completed_seats} 席回答`);
  if (s.failed_seats > 0) parts.push(`${s.failed_seats} 失败`);
  if (s.timeout_seats > 0) parts.push(`${s.timeout_seats} 超时`);
  if (s.verdict_status === "complete") parts.push("报告已生成");
  else if (s.verdict_status === "partial") parts.push("部分裁决");
  return parts.length ? "本轮：" + parts.join(" · ") : "";
}

function toggleMemoryTimeline(runId) {
  if (!runId) return;
  const expandedEl = document.getElementById("mem-tl-" + runId);
  const toggleEl = document.getElementById("mem-tl-toggle-" + runId);
  if (!expandedEl || !toggleEl) return;

  if (expandedEl.classList.contains("open")) {
    expandedEl.classList.remove("open");
    expandedEl.innerHTML = "";
    toggleEl.textContent = "展开 timeline";
    return;
  }

  const memItem = document.querySelector(`.memory-item[data-runid="${runId}"]`);
  const data = memItem?.__timelineData;
  if (!data || !data.events) return;

  const uvEvents = data.events.filter(e => e.user_visible && !e.advanced);
  expandedEl.innerHTML = uvEvents.map(renderTimelineEventHTML).join("");
  expandedEl.classList.add("open");
  toggleEl.textContent = "收起 timeline";
}

window.__AIJUDGE_TIMELINE__ = {
  loadRunTimeline,
  renderUserTimeline,
  renderAdvancedTimeline,
  renderTimelineSummary,
  renderRoomTimeline,
  renderReportProcessSummary,
  renderMemoryTimelineSummary,
  renderTimelineEventHTML,
  toggleMemoryTimeline,
};


/* ══════════ P1.3 Evidence Summary ══════════ */

async function loadEvidenceSummary(runId) {
  if (!runId) return null;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/evidence-summary");
    const data = await res.json();
    if (data.ok) return data;
    return null;
  } catch (_) {
    return null;
  }
}

function renderEvidenceSummaryCard(ev) {
  if (!ev || !ev.ok) return "";

  const statusClass = ev.verdict_status === "complete" ? "complete" : ev.verdict_status === "partial" ? "partial" : "failed";
  const statusLabel = ev.verdict_status === "complete" ? "完整" : ev.verdict_status === "partial" ? "部分" : "失败";

  let html = `<div class="evidence-card" id="evidence-card">
    <h3>证据摘要 <span class="ev-status ${statusClass}">${statusLabel}</span></h3>`;

  // Inputs
  if (ev.inputs && ev.inputs.length) {
    html += `<div class="ev-section">
      <div class="ev-section-title">输入来源</div>
      <div class="ev-inputs">${ev.inputs.map(i => `<span class="ev-input-tag">${escapeHtml(i.label)}</span>`).join("")}</div>
    </div>`;
  }

  // Supporting seats
  if (ev.supporting_seats && ev.supporting_seats.length) {
    html += `<div class="ev-section">
      <div class="ev-section-title">支持主结论的席位 (${ev.supporting_seats.length})</div>
      <div class="ev-seat-list">${ev.supporting_seats.map(s => `
        <div class="ev-seat-item supporting">
          <span class="ev-seat-name">${escapeHtml(s.seat)}</span>
          <span class="ev-seat-summary">${escapeHtml(excerpt(s.summary || "", 100))}</span>
          ${s.confidence ? `<span class="ev-seat-conf">${Math.round(s.confidence * 100)}%</span>` : ""}
        </div>`).join("")}</div>
    </div>`;
  }

  // Dissenting seats
  if (ev.dissenting_seats && ev.dissenting_seats.length) {
    html += `<div class="ev-section">
      <div class="ev-section-title">保留/反对意见 (${ev.dissenting_seats.length})</div>
      <div class="ev-seat-list">${ev.dissenting_seats.map(s => `
        <div class="ev-seat-item dissenting">
          <span class="ev-seat-name">${escapeHtml(s.seat)}</span>
          <span class="ev-seat-summary">${escapeHtml(excerpt(s.reason || s.summary || "", 100))}</span>
        </div>`).join("")}</div>
    </div>`;
  }

  // Evidence gaps
  if (ev.evidence_gaps && ev.evidence_gaps.length) {
    html += `<div class="ev-section">
      <div class="ev-section-title">证据缺口 (${ev.evidence_gaps.length})</div>
      <div class="ev-gap-list">${ev.evidence_gaps.map(g => `
        <div class="ev-gap-item sev-${g.severity || "medium"}">
          <div class="ev-gap-claim">${escapeHtml(g.claim || "")}</div>
          <div class="ev-gap-reason">${escapeHtml(g.gap || "")}</div>
        </div>`).join("")}</div>
    </div>`;
  }

  // Advanced details (collapsible): risks + next evidence
  const hasAdvanced = (ev.risks && ev.risks.length) || (ev.next_evidence_to_collect && ev.next_evidence_to_collect.length);
  if (hasAdvanced) {
    html += `<details class="ev-advanced-toggle">
      <summary>展开高级证据</summary>
      <div class="ev-advanced-detail">`;
    if (ev.risks && ev.risks.length) {
      html += `<div class="ev-section">
        <div class="ev-section-title">风险提示</div>
        <ul class="ev-risks">${ev.risks.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      </div>`;
    }
    if (ev.next_evidence_to_collect && ev.next_evidence_to_collect.length) {
      html += `<div class="ev-section">
        <div class="ev-section-title">建议补充资料</div>
        <ul class="ev-next-list">${ev.next_evidence_to_collect.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>
      </div>`;
    }
    html += `</div></details>`;
  }

  html += `</div>`;
  return html;
}

async function renderEvidenceSummaryForReport() {
  const runId = state.currentThread.runId || state.currentVerdict?.run_id || "";
  if (!runId) return;

  const ev = await loadEvidenceSummary(runId);
  if (!ev) return;

  const html = renderEvidenceSummaryCard(ev);
  if (!html) return;

  // Insert evidence card before the followup zone
  const container = $("#report-content");
  if (!container) return;

  const followupZone = container.querySelector("#followup-zone");
  const existingCard = container.querySelector("#evidence-card");

  if (existingCard) {
    existingCard.outerHTML = html;
  } else if (followupZone) {
    // Insert before followup zone
    const temp = document.createElement("div");
    temp.innerHTML = html;
    followupZone.parentNode.insertBefore(temp.firstElementChild, followupZone);
  } else {
    // Append at end of container
    const temp = document.createElement("div");
    temp.innerHTML = html;
    container.appendChild(temp.firstElementChild);
  }

  // Store for followup reference
  state._evidenceSummary = ev;
}

function renderEvidenceSummaryOneLiner(ev) {
  if (!ev || !ev.ok) return "";
  const parts = [];
  if (ev.supporting_seats && ev.supporting_seats.length) {
    parts.push(`${ev.supporting_seats.length} 个席位支持`);
  }
  if (ev.dissenting_seats && ev.dissenting_seats.length) {
    parts.push(`${ev.dissenting_seats.length} 个保留`);
  }
  if (ev.evidence_gaps && ev.evidence_gaps.length) {
    const highGaps = ev.evidence_gaps.filter(g => g.severity === "high");
    if (highGaps.length) {
      parts.push(`${highGaps.length} 个关键缺口`);
    } else {
      parts.push(`${ev.evidence_gaps.length} 个证据缺口`);
    }
  }
  return parts.length ? "证据：" + parts.join("，") + "。" : "";
}


/* ══════════ P1.4 Decision Action Pack ══════════ */

async function loadActionPack(runId) {
  if (!runId) return null;
  try {
    const res = await fetch(API_BASE + "/api/runs/" + encodeURIComponent(runId) + "/action-pack");
    const data = await res.json();
    if (data.ok) return data;
    return null;
  } catch (_) {
    return null;
  }
}

function renderActionPackCard(ap) {
  if (!ap || !ap.ok) return "";

  // P1.4A: canonical fields with legacy fallback
  const actions = ap.priority_actions || ap.actions || [];
  const rerunConds = ap.rejudge_conditions || ap.rerun_conditions || [];

  let html = `<div class="action-pack-card" id="action-pack-card">
    <h3>Decision Action Pack</h3>`;

  // P1.4A: decision_status badge
  const statusLabels = { ready: "可执行", needs_evidence: "需补证", high_risk: "高风险" };
  const statusLabel = statusLabels[ap.decision_status] || ap.decision_status || "";
  if (ap.decision_status) {
    html += `<div class="ap-decision-status ap-status-${escapeAttr(ap.decision_status)}">
      <span class="ap-status-dot"></span>${escapeHtml(statusLabel)}
    </div>`;
  }

  // Partial banner
  if (ap.verdict_status === "partial" || ap.verdict_status === "failed") {
    html += `<div class="ap-partial-banner">该裁决不完整，建议优先补充证据后再重新裁决。</div>`;
  }

  // Actions — P1.4A: group by canonical priority string
  if (actions.length) {
    const p1 = actions.filter(a => (a.priority_rank || a.priority) === 1);
    const p2 = actions.filter(a => (a.priority_rank || a.priority) === 2);
    const p3 = actions.filter(a => (a.priority_rank || a.priority) === 3);

    if (p1.length) {
      html += `<div class="ap-section">
        <div class="ap-section-title">立即执行 (P1)</div>`;
      for (const a of p1) {
        html += renderActionItem(a);
      }
      html += `</div>`;
    }
    if (p2.length) {
      html += `<div class="ap-section">
        <div class="ap-section-title">等待证据 (P2)</div>`;
      for (const a of p2) {
        html += renderActionItem(a);
      }
      html += `</div>`;
    }
    if (p3.length) {
      html += `<div class="ap-section">
        <div class="ap-section-title">长期观察 (P3)</div>`;
      for (const a of p3) {
        html += renderActionItem(a);
      }
      html += `</div>`;
    }
  }

  // Risks
  if (ap.risks && ap.risks.length) {
    html += `<div class="ap-section">
      <div class="ap-section-title">风险提示 (${ap.risks.length})</div>`;
    for (const r of ap.risks) {
      html += `<div class="ap-risk-item">
        <span class="ap-risk-action">${escapeHtml(r.action || "风险")}</span>
        <span class="ap-risk-text">${escapeHtml(r.risk || "")}</span>
        <span class="ap-risk-tag ap-risk-${r.severity || "low"}">${(r.severity || "low").toUpperCase()}</span>
      </div>`;
    }
    html += `</div>`;
  }

  // Evidence needed
  if (ap.evidence_needed && ap.evidence_needed.length) {
    html += `<div class="ap-section">
      <div class="ap-section-title">待补充证据 (${ap.evidence_needed.length})</div>
      <ul class="ap-evidence-list">${ap.evidence_needed.map(e => `<li>${escapeHtml(e)}</li>`).join("")}</ul>
    </div>`;
  }

  // Rerun conditions — P1.4A: canonical first
  if (rerunConds.length) {
    html += `<div class="ap-section">
      <div class="ap-section-title">重新裁决条件</div>
      <ul class="ap-rerun-list">${rerunConds.map(c => `<li>${escapeHtml(c)}</li>`).join("")}</ul>
    </div>`;
  }

  html += `</div>`;
  return html;
}

function renderActionItem(a) {
  // P1.4A: canonical fields with legacy fallback
  const prioStr = a.priority || (a.priority_rank === 1 ? "high" : a.priority_rank === 2 ? "medium" : "low");
  const prioClass = (a.priority_rank || a.priority) === 1
    ? "ap-priority-p1"
    : (a.priority_rank || a.priority) === 2 ? "ap-priority-p2" : "ap-priority-p3";
  const effortVal = a.estimated_effort || a.effort || "medium";
  const effortLabel = effortVal === "low" ? "低" : effortVal === "medium" ? "中" : "高";
  const outcome = a.risk || a.expected_outcome || "";
  return `<div class="ap-action-item ${prioClass}">
    <div class="ap-action-title">${escapeHtml(a.title || "")}</div>
    <div class="ap-action-reason">${escapeHtml(a.why || a.reason || "")}</div>
    <div class="ap-action-outcome">预期: ${escapeHtml(outcome || "—")}</div>
    <div class="ap-action-meta">
      <span class="ap-effort-tag ap-effort-${effortVal}">工作量: ${effortLabel}</span>
    </div>
  </div>`;
}

function renderActionPackOneLiner(ap) {
  if (!ap || !ap.ok) return "";
  // P1.4A: canonical priority_actions with legacy fallback
  const actions = ap.priority_actions || ap.actions || [];
  if (!actions.length) return "";
  const p1 = actions.filter(a => (a.priority_rank || a.priority) === 1);
  const topAction = p1[0] || actions[0];
  return `建议：${topAction.title}${p1.length > 1 ? `，及其他 ${p1.length - 1} 项行动` : ""}。`;
}

async function renderActionPackForReport() {
  const runId = state.currentThread.runId || state.currentVerdict?.run_id || "";
  if (!runId) return;

  const ap = await loadActionPack(runId);
  if (!ap) return;

  const html = renderActionPackCard(ap);
  if (!html) return;

  const container = $("#report-content");
  if (!container) return;

  const followupZone = container.querySelector("#followup-zone");
  const existingCard = container.querySelector("#action-pack-card");

  if (existingCard) {
    existingCard.outerHTML = html;
  } else if (followupZone) {
    const temp = document.createElement("div");
    temp.innerHTML = html;
    followupZone.parentNode.insertBefore(temp.firstElementChild, followupZone);
  } else {
    const temp = document.createElement("div");
    temp.innerHTML = html;
    container.appendChild(temp.firstElementChild);
  }

  // Store for followup reference
  state._actionPack = ap;
}

function _composeActionPackFollowupAnswer(question, ap) {
  const q = question.toLowerCase();

  // P1.4A: canonical fields with legacy fallback
  const getActions = () => ap.priority_actions || ap.actions || [];
  const getRerunConds = () => ap.rejudge_conditions || ap.rerun_conditions || [];
  const isP1 = (a) => (a.priority_rank || a.priority) === 1;
  const getReason = (a) => a.why || a.reason || "";
  const getOutcome = (a) => a.risk || a.expected_outcome || "";
  const getEffort = (a) => { const e = a.estimated_effort || a.effort || "medium"; return e === "low" ? "低" : e === "medium" ? "中" : "高"; };

  // "我应该先做什么？"
  if (q.includes("先做") || q.includes("应先") || q.includes("先") || q.includes("下一步")) {
    const actions = getActions();
    const p1 = actions.filter(isP1);
    if (p1.length) {
      return "根据 Action Pack，建议优先执行：\n\n" + p1.map((a, i) =>
        `${i + 1}. **${a.title}**\n   原因：${getReason(a)}\n   预期：${getOutcome(a)}\n   工作量：${getEffort(a)}`
      ).join("\n\n");
    }
    const first = actions[0];
    if (first) return `建议优先：**${first.title}**。${getReason(first)}`;
    return "当前无明确优先行动。请查看完整的 Decision Action Pack。";
  }

  // "最大风险是什么？"
  if (q.includes("最大风险") || q.includes("风险")) {
    const risks = ap.risks || [];
    const highRisks = risks.filter(r => r.severity === "high");
    if (highRisks.length) {
      return "最需要关注的风险：\n\n" + highRisks.map(r =>
        `- **${r.action}**: ${r.risk}（严重程度：高）`
      ).join("\n");
    }
    if (risks.length) {
      return "当前风险清单：\n\n" + risks.map(r =>
        `- **${r.action}**: ${r.risk}（${r.severity}）`
      ).join("\n");
    }
    return "当前 Action Pack 未识别到显著风险。";
  }

  // "什么情况下重新裁决？"
  if (q.includes("重新裁决") || q.includes("重裁")) {
    const conditions = getRerunConds();
    if (conditions.length) {
      return "以下情况建议重新裁决：\n\n" + conditions.map((c, i) => `${i + 1}. ${c}`).join("\n");
    }
    return "当新证据出现、问题条件变化或超过 30 天后，建议重新裁决。";
  }

  // Default: summary of action pack
  const actions = getActions();
  const p1 = actions.filter(isP1);
  const summary = [];
  if (p1.length) summary.push(`P1 行动 ${p1.length} 项：${p1.map(a => a.title).join("、")}`);
  if ((ap.evidence_needed || []).length) summary.push(`需补充 ${ap.evidence_needed.length} 条证据`);
  if ((ap.risks || []).length) summary.push(`${ap.risks.length} 条风险提示`);
  return "Decision Action Pack 概要：\n\n" + summary.map(s => `- ${s}`).join("\n");
}


/* ══════════ P3.8.4 Synthetic UI Smoke Harness ══════════ */
window.__AIJUDGE_UI_SMOKE__ = {};

/* ── Reset client thread to clean slate ── */
window.__AIJUDGE_UI_SMOKE__.resetClientThreadFixture = function() {
  state.currentThread = {
    threadId: "fixture_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8),
    runId: "",
    mode: state.selectedMode,
    stage: "draft",
    question: "",
    alignedIntent: "",
    suggestedMode: "",
    promptSummary: [],
    messages: [],
    seatCards: [],
    attachments: [],
    artifacts: [],
    report: null,
  };
  state.currentTask = null;
  state.currentVerdict = null;
  state.currentRunId = null;
  state._pendingSeats = null;
  state.workflow.stage = WORKFLOW_STAGE.IDLE;
  state.workflow.canPause = false;
  state.workflow.paused = false;
  state.workflow.completedSeats = new Set();
  state.workflow.activeSeatCount = 0;
  state.workflow.runId = null;
  cleanupProgress();
  renderThreadMessages("ask-thread-messages");
  renderThreadMessages("room-thread-messages");
  renderRoom();
  console.info("[UI Smoke] Client thread reset to clean slate");
};

/* ── Inject strategic 13-seat fixture ── */
window.__AIJUDGE_UI_SMOKE__.injectStrategicProgressFixture = function() {
  window.__AIJUDGE_UI_SMOKE__.resetClientThreadFixture();

  // Set mode to strategic
  state.selectedMode = "strategic";
  state.currentThread.mode = "strategic";

  const runId = "ui-smoke-strategic-001";
  state.currentThread.runId = runId;
  state.currentRunId = runId;
  state.workflow.runId = runId;

  const question = "Synthetic strategic 13-seat UI test: does the Room render all seats and thread messages correctly?";
  state.currentThread.question = question;

  // 13 seats: chatgpt, gemini, deepseek, qwen, kimi, grok, doubao, wenxin, minimax, zhipu, mimo, meta, yuanbao
  const allSeats = [
    { id: "chatgpt",   name: "GPT-4o",   channel: "OpenAI",     color: "#10a37f" },
    { id: "gemini",    name: "Gemini",    channel: "Google",     color: "#FF8C00" },
    { id: "deepseek",  name: "DeepSeek",  channel: "DeepSeek",   color: "#4d6bfe" },
    { id: "qwen",      name: "Qwen",      channel: "Alibaba",    color: "#808080" },
    { id: "kimi",      name: "Kimi",      channel: "Moonshot",   color: "#ff5757" },
    { id: "grok",      name: "Grok",      channel: "xAI",        color: "#111827" },
    { id: "doubao",    name: "Doubao",    channel: "ByteDance",  color: "#f97316" },
    { id: "wenxin",    name: "Wenxin",    channel: "Baidu",      color: "#22c55e" },
    { id: "minimax",   name: "MiniMax",   channel: "MiniMax",    color: "#7c3aed" },
    { id: "zhipu",     name: "Zhipu",     channel: "Zhipu",      color: "#0ea5e9" },
    { id: "mimo",      name: "MiMo",      channel: "Xiaomi",     color: "#8b5cf6" },
    { id: "meta",      name: "Meta AI",   channel: "Meta",       color: "#1877f2" },
    { id: "yuanbao",   name: "Yuanbao",   channel: "Tencent",    color: "#14b8a6" },
  ];

  state._pendingSeats = allSeats.map(s => ({
    id: s.id, name: s.name, channel: s.channel, color: s.color,
    ready: true, state: "waiting",
  }));

  // Add user_question and run_started
  addThreadMessage({ type: MSG_TYPE.USER_QUESTION, question, mode: "strategic" });
  addThreadMessage({ type: MSG_TYPE.RUN_STARTED, runId });

  // Status distribution: 2 answered, 2 waiting, 1 submitted, 1 timeout, 1 skipped, rest waiting
  // answered: chatgpt, gemini
  addThreadMessage({
    type: MSG_TYPE.SEAT_ANSWERED,
    seatId: "chatgpt",
    seat: { id: "chatgpt", name: "GPT-4o", color: "#10a37f" },
    answerPreview: "Strategic fixture: ChatGPT recommends proceeding with P3.8.4 after verifying seat rendering and thread flow.",
    fullAnswer: "Full strategic analysis from ChatGPT seat: The UI test framework is solid. All 13 seats should render correctly. Thread messages should appear in both Ask and Room views. Timeout and skip states need visual distinction."
  });
  addThreadMessage({
    type: MSG_TYPE.SEAT_ANSWERED,
    seatId: "gemini",
    seat: { id: "gemini", name: "Gemini", color: "#FF8C00" },
    answerPreview: "Strategic fixture: Gemini confirms the 13-seat grid renders without truncation.",
    fullAnswer: "Gemini analysis: The dashboard properly handles the full 13-seat strategic panel. Seat status badges are visible and color-coded. The room view refreshes correctly when new seat events arrive."
  });

  // submitted: deepseek
  addThreadMessage({
    type: MSG_TYPE.SEAT_SUBMITTED,
    seatId: "deepseek",
    seat: { id: "deepseek", name: "DeepSeek", color: "#4d6bfe" },
  });

  // timeout: qwen
  addThreadMessage({
    type: MSG_TYPE.SEAT_TIMEOUT,
    seatId: "qwen",
    seat: { id: "qwen", name: "Qwen", color: "#808080" },
  });

  // skipped: kimi
  addThreadMessage({
    type: MSG_TYPE.SEAT_SKIPPED,
    seatId: "kimi",
    seat: { id: "kimi", name: "Kimi", color: "#ff5757" },
  });

  // Rest (grok, doubao, wenxin, minimax, zhipu, mimo, meta, yuanbao) stay as waiting
  // No messages needed - they appear in the seat grid

  state.currentThread.stage = "running";
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;
  state.workflow.canPause = true;

  renderRoom();
  switchTab("room");

  console.info("[UI Smoke] Strategic 13-seat fixture injected, run_id=" + runId);
};

/* ── Inject flash thread flow fixture ── */
window.__AIJUDGE_UI_SMOKE__.injectFlashProgressFixture = function() {
  window.__AIJUDGE_UI_SMOKE__.resetClientThreadFixture();

  state.selectedMode = "flash";
  state.currentThread.mode = "flash";

  const runId = "ui-smoke-flash-001";
  state.currentThread.runId = runId;
  state.currentRunId = runId;
  state.workflow.runId = runId;

  const question = "Synthetic flash thread flow test: do Ask and Room share the same thread?";
  state.currentThread.question = question;

  const seats = [
    { id: "chatgpt",  name: "GPT-4o",   channel: "OpenAI",    color: "#10a37f" },
    { id: "gemini",   name: "Gemini",    channel: "Google",    color: "#FF8C00" },
    { id: "deepseek", name: "DeepSeek",  channel: "DeepSeek",  color: "#4d6bfe" },
    { id: "qwen",     name: "Qwen",      channel: "Alibaba",   color: "#808080" },
  ];

  state._pendingSeats = seats.map(s => ({
    id: s.id, name: s.name, channel: s.channel, color: s.color,
    ready: true, state: "waiting",
  }));

  addThreadMessage({ type: MSG_TYPE.USER_QUESTION, question, mode: "flash" });
  addThreadMessage({ type: MSG_TYPE.RUN_STARTED, runId });

  // 2 answered
  addThreadMessage({
    type: MSG_TYPE.SEAT_ANSWERED,
    seatId: "chatgpt",
    seat: { id: "chatgpt", name: "GPT-4o", color: "#10a37f" },
    answerPreview: "Flash fixture: ChatGPT confirms thread sharing works between Ask and Room.",
    fullAnswer: "Full flash answer from ChatGPT: The currentThread state object is shared. When messages are added via addThreadMessage(), both Ask and Room views update because they both call renderThreadMessages() from the same state.currentThread.messages array."
  });
  addThreadMessage({
    type: MSG_TYPE.SEAT_ANSWERED,
    seatId: "gemini",
    seat: { id: "gemini", name: "Gemini", color: "#FF8C00" },
    answerPreview: "Flash fixture: Gemini verifies SSE-style updates render correctly.",
    fullAnswer: "Gemini full answer: The thread-based rendering ensures that incoming seat answers appear in both Ask and Room views simultaneously. The Room view also shows seat cards with status badges alongside the thread messages."
  });

  // 1 waiting (no message needed)
  // 1 timeout
  addThreadMessage({
    type: MSG_TYPE.SEAT_TIMEOUT,
    seatId: "deepseek",
    seat: { id: "deepseek", name: "DeepSeek", color: "#4d6bfe" },
  });

  state.currentThread.stage = "running";
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;

  renderRoom();
  switchTab("room");

  console.info("[UI Smoke] Flash thread flow fixture injected, run_id=" + runId);
};

/* ── Inject seat transition fixture ── */
window.__AIJUDGE_UI_SMOKE__.injectSeatTransitionFixture = function() {
  window.__AIJUDGE_UI_SMOKE__.resetClientThreadFixture();

  state.selectedMode = "flash";
  state.currentThread.mode = "flash";

  const runId = "ui-smoke-transition-001";
  state.currentThread.runId = runId;
  state.currentRunId = runId;
  state.workflow.runId = runId;

  const question = "Seat transition test: waiting -> submitted -> answered";
  state.currentThread.question = question;

  const seats = [
    { id: "chatgpt", name: "GPT-4o", channel: "OpenAI", color: "#10a37f" },
  ];

  state._pendingSeats = seats.map(s => ({
    id: s.id, name: s.name, channel: s.channel, color: s.color,
    ready: true, state: "waiting",
  }));

  addThreadMessage({ type: MSG_TYPE.USER_QUESTION, question, mode: "flash" });
  addThreadMessage({ type: MSG_TYPE.RUN_STARTED, runId });

  // Step 1: waiting (no explicit message - implicit from _pendingSeats)
  // Step 2: submitted
  addThreadMessage({
    type: MSG_TYPE.SEAT_SUBMITTED,
    seatId: "chatgpt",
    seat: { id: "chatgpt", name: "GPT-4o", color: "#10a37f" },
  });

  // Step 3: answered (should update in-place, not create duplicate)
  addThreadMessage({
    type: MSG_TYPE.SEAT_ANSWERED,
    seatId: "chatgpt",
    seat: { id: "chatgpt", name: "GPT-4o", color: "#10a37f" },
    answerPreview: "Transition test: chatgpt answered after submitted state.",
    fullAnswer: "This seat transitioned from waiting -> submitted -> answered. The UI should show only ONE seat card with the final state, not duplicates."
  });

  state.currentThread.stage = "running";
  state.workflow.stage = WORKFLOW_STAGE.RUNNING;

  renderRoom();
  switchTab("room");

  console.info("[UI Smoke] Seat transition fixture injected, run_id=" + runId);
};

/* ── Get thread state snapshot ── */
window.__AIJUDGE_UI_SMOKE__.getThreadStateSnapshot = function() {
  const t = state.currentThread;
  return {
    threadId: t.threadId,
    runId: t.runId,
    mode: t.mode,
    stage: t.stage,
    question: t.question,
    msgCount: (t.messages || []).length,
    msgTypes: (t.messages || []).map(function(m) { return m.type; }),
    attCount: (t.attachments || []).length,
    artCount: (t.artifacts || []).length,
    seatCardCount: (t.seatCards || []).length,
    pendingSeats: (state._pendingSeats || []).length,
    taskRunId: state.currentTask?.run_id || null,
    verdictRunId: state.currentVerdict?.run_id || null,
    workflowStage: state.workflow.stage,
  };
};

console.info("[AI Judge] P3.8.4 UI smoke harness loaded — window.__AIJUDGE_UI_SMOKE__ ready");
