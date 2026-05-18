const API_BASE = "http://127.0.0.1:8501";
const RECOVERABLE_WEB_CODES = new Set([
  "slow_response_pending",
  "response_timeout",
  "send_button_not_found",
  "submit_unconfirmed",
  "composer_busy",
  "response_not_relevant",
  "long_prompt_still_in_input",
  "existing_answer_not_found",
  "existing_answer_placeholder",
  "existing_answer_prompt_echo",
  "fixed_tab_not_found",
  "input_not_found",
  "transcript_pollution",
]);
const OPTIONAL_EXECUTION_SEATS = new Set(["grok", "gork"]);

const timelineSteps = [
  { key: "accept", label: "受理问题" },
  { key: "align", label: "本地共振" },
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
  productMode: localStorage.getItem("ai_judge_product_mode") || "simple",
  selectedMode: "flash",
  engine: "local",
  chiefJudge: localStorage.getItem("ai_judge_chief_judge") || "auto",
  selectedSeats: new Set(),
  lastHistoryRunId: localStorage.getItem("ai_judge_last_run_id") || null,
  currentRunId: null,
  currentTask: null,
  currentVerdict: null,
  currentTrace: null,
  eventSource: null,
  pollTimer: null,
  autoRecheckTimer: null,
  autoRecheckRunId: null,
  recheckInFlight: false,
  selectedTaskId: localStorage.getItem("ai_judge_selected_task") || "request",
  mentorEnabled: localStorage.getItem("ai_judge_mentor_enabled") === "1",
  mentorConfirmed: false,
  mentorSignature: "",
  mentorSnapshot: null,
  publishCleared: false,
};

document.addEventListener("DOMContentLoaded", async () => {
  bindUI();
  applyProductMode(state.productMode);
  renderTimeline(0);
  initMentor();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  await refreshAll();
  applyMode("flash");
  applyEngine("local");
  await restoreLastRun();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
});

function bindUI() {
  $$(".tab").forEach(tab => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
  $$("[data-tab-shortcut]").forEach(item => item.addEventListener("click", () => switchTab(item.dataset.tabShortcut)));
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
  $$("#product-switch .product-mode").forEach(btn => btn.addEventListener("click", () => applyProductMode(btn.dataset.productMode)));
  $("#btn-refresh").addEventListener("click", refreshAll);
  $("#btn-history-refresh").addEventListener("click", loadHistory);
  $("#btn-submit").addEventListener("click", submitJudge);
  $("#btn-supplement-slow")?.addEventListener("click", supplementSlowSeats);
  $("#btn-recheck-stalled")?.addEventListener("click", () => recheckStalledSeats({ auto: false }));
  $("#view-link").addEventListener("click", event => {
    const href = event.currentTarget.getAttribute("href");
    if (!href || href === "#") return;
    event.preventDefault();
    window.location.href = href;
  });
  $("#question-input").addEventListener("input", () => {
    state.mentorConfirmed = false;
    updateMentorPreflight();
    updateSubmitState();
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

function applyProductMode(mode) {
  state.productMode = mode === "pro" ? "pro" : "simple";
  localStorage.setItem("ai_judge_product_mode", state.productMode);
  $("#app-shell").classList.toggle("pro-mode", state.productMode === "pro");
  $("#app-shell").classList.toggle("simple-mode", state.productMode !== "pro");
  $$("#product-switch .product-mode").forEach(btn => btn.classList.toggle("active", btn.dataset.productMode === state.productMode));
  if (state.currentVerdict) {
    renderDecisionMemo(state.currentVerdict);
    renderCrossTemporal(state.currentVerdict);
  }
  renderArena();
  renderSimpleSeatSummary();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
}

async function refreshAll() {
  await Promise.all([loadModes(), loadSeats(), loadBridgeStatus(), loadHistory(), loadSeatScoreboard()]);
  renderSeatScores();
  renderArena();
  renderTaskCenter();
  renderEvidenceTree();
  renderCouncilCompletion();
  renderMentorGateChecklist();
  updateTopStatus();
}

function switchTab(tabName) {
  $$(".tab").forEach(tab => tab.classList.toggle("active", tab.dataset.tab === tabName));
  $$(".view").forEach(view => { view.hidden = view.id !== `view-${tabName}`; });
  updateWorkflowForTab(tabName);
}

function updateWorkflowForTab(tabName) {
  const stepByTab = {
    tasks: "intake",
    request: state.mentorEnabled ? "mentor" : "intake",
    draft: "collect",
    evidence: "audit",
    council: "collect",
    publish: "publish",
    history: "audit",
    settings: "intake",
  };
  const order = ["intake", "mentor", "collect", "audit", "publish"];
  const active = stepByTab[tabName] || "intake";
  const activeIndex = order.indexOf(active);
  $$("[data-workflow-step]").forEach(item => {
    const index = order.indexOf(item.dataset.workflowStep);
    item.classList.toggle("active", item.dataset.workflowStep === active);
    item.classList.toggle("done", index >= 0 && index < activeIndex);
  });
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
    state.seats = data.seats || fallbackSeats();
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

async function loadSeatScoreboard() {
  try {
    const res = await fetch(`${API_BASE}/api/seat-scoreboard`);
    state.seatScoreboard = await res.json();
  } catch {
    state.seatScoreboard = { runs_considered: 0, seats: [] };
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

function applyMode(mode) {
  state.selectedMode = mode || "flash";
  $$("#mode-strip .segment").forEach(btn => btn.classList.toggle("active", btn.dataset.mode === state.selectedMode));
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
}

function applyEngine(engine) {
  state.engine = engine || "local";
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
  const text = state.engine === "web"
    ? counts.webTotal > 0 && counts.webReady > 0
      ? `网页 ${counts.webReady}/${counts.webTotal} 通过${counts.desktopTotal ? ` · 桌面 ${counts.desktopReady}/${counts.desktopTotal}` : ""}`
      : bridge.playwright_installed
        ? `网页 ${counts.webConfigured}/${counts.webTotal || 0} 已配置，待校准`
        : "缺少 Playwright"
    : "本地席位就绪";
  $("#bridge-status").textContent = text;
}

function updateTopStatus() {
  const counts = bridgeChannelCounts();
  $("#app-status").textContent = state.engine === "web" ? "网页桥接模式" : "本地引擎就绪";
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
}

function buildTaskItems() {
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
      title: "网页桥接校准",
      summary: "确认网页/桌面席位是否可后台收集，并查看 COUNCIL-004 人格席位",
      stage: "席位",
      risk: bridgeNeedsWork ? "warn" : "ok",
      riskLabel: bridgeNeedsWork ? "需校准" : "就绪",
      seats: `${counts.webReady}/${counts.webTotal}`,
      next: "模型对比",
      tab: "council",
      detail: bridgeNeedsWork
        ? `仍有 ${Math.max(0, counts.webTotal - counts.webReady)} 个网页席位未就绪，专业版可查看每席位原因。`
        : "网页席位和桌面席位已进入可观察状态。",
    },
    {
      id: "publish",
      title: "发布门禁",
      summary: "证据、分歧、风险披露、日志和人工确认的硬门禁",
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

function renderTaskInspector(task, publishSummary) {
  if (!task) return;
  $("#task-detail-title").textContent = task.title;
  $("#task-detail-summary").textContent = task.detail || task.summary;
  $("#task-detail-actions").innerHTML = `
    <button class="primary-action" data-task-open="${escapeAttr(task.tab)}">${escapeHtml(task.next)}</button>
    <button class="ghost" data-task-open="publish">查看发布门禁</button>
  `;
  $("#task-inspector-title").textContent = task.title;
  $("#task-inspector-summary").textContent = task.summary;
  $("#task-inspector-stage").textContent = task.stage;
  $("#task-inspector-gate").textContent = task.riskLabel;
  $("#task-inspector-next").textContent = task.next;
  renderBridgeHealth("#task-bridge-health", { limit: state.productMode === "pro" ? 13 : 6 });
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
  `).join("") || `<div class="bridge-health-card warn"><strong>等待配置</strong><span>读取本地席位和网页桥接状态后显示。</span></div>`;
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
  if (state.engine !== "web") {
    return { seat: seatId, name: seat.name || seatName(seatId), state: "ok", label: "本地", detail: seat.strength || "本地席位就绪" };
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
    return { state: "ok", label: "快速直达", detail: "导师门禁未启用，任务会按当前问题直接进入评议。" };
  }
  const snapshot = state.mentorSnapshot || buildMentorPreflight(question);
  if (!question) return { state: "block", label: "待输入", detail: "先输入问题，导师门禁才能判断清晰度和风险边界。" };
  if (!state.mentorConfirmed) return { state: "warn", label: "待确认", detail: snapshot.next_question || "确认导师预检后再运行。" };
  return { state: "ok", label: "已确认", detail: snapshot.execution_draft || "导师预检已确认。" };
}

function evidenceGateSummary() {
  const nodes = buildEvidenceNodes();
  const blockers = nodes.filter(item => item.state === "block").length;
  const warnings = nodes.filter(item => item.state === "warn").length;
  if (blockers) return { state: "block", label: `${blockers} 阻断`, nodes: nodes.length, detail: "证据链仍有硬阻断，不能进入发布级可用。" };
  if (warnings) return { state: "warn", label: `${warnings} 待复核`, nodes: nodes.length, detail: "证据链可读，但仍有回收、引用或分歧需要人工复核。" };
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
    return { ok, total, pct, label: total ? `${ok}/${total}` : "按模式", required: true };
  }
  const rawOk = raw.filter(item => item.ok).length;
  const scoreCount = (v.seat_scores || []).length;
  const ok = raw.length ? rawOk : scoreCount;
  const total = Number(v.web_bridge?.requested_count || raw.length || v.seat_count || state.selectedSeats.size || state.seats.length || 0);
  const pct = total ? Math.round((ok / total) * 100) : 0;
  return { ok, total, pct, label: total ? `${ok}/${total}` : "按模式" };
}

function buildPublishGateSummary() {
  const checks = buildPublishGateChecks();
  const blockers = checks.filter(item => item.state === "block").length;
  const warnings = checks.filter(item => item.state === "warn").length;
  const human = checks.find(item => item.key === "human_confirmation");
  const nonHumanBlockers = checks.filter(item => item.key !== "human_confirmation" && item.state === "block").length;
  const ready = Boolean(state.currentVerdict && nonHumanBlockers === 0 && state.publishCleared);
  const reason = ready
    ? "全部硬门禁通过，已完成发布级人工确认。"
    : nonHumanBlockers
      ? `仍有 ${nonHumanBlockers} 个硬门禁阻断。`
      : human?.state !== "ok"
        ? "硬门禁已满足，等待人工发布确认。"
        : warnings
          ? `还有 ${warnings} 个复核提醒。`
          : "等待判词生成。";
  return { checks, blockers, warnings, nonHumanBlockers, ready, reason };
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

function renderSeats() {
  const grid = $("#seat-grid");
  grid.innerHTML = state.seats.map(seat => `
    <button class="seat-card ${state.selectedSeats.has(seat.id) ? "selected" : ""} ${seatBridgeReady(seat.id) ? "" : "bridge-muted"}" data-seat="${escapeAttr(seat.id)}">
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
  $("#selected-count").textContent = `当前 ${state.selectedSeats.size} 席`;
  renderArena();
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
  $("#arena-seat-count").textContent = `${state.selectedSeats.size}/${state.seats.length} 席`;
  $("#arena-roster").innerHTML = state.seats.map(seat => {
    const selected = state.selectedSeats.has(seat.id);
    const bridgeSeat = bridgeSeatById(seat.id) || {};
    const localOnly = state.engine !== "web";
    const channel = localOnly ? "local" : bridgeSeat.channel || (seat.id === "doubao" ? "desktop" : "web");
    const status = selected ? arenaSeatStatus(seat.id) : "弃权";
    return `
      <article class="roster-card ${selected ? "selected" : "abstained"}" data-seat="${escapeAttr(seat.id)}">
        <div class="roster-main">
          <span class="seat-icon">${escapeHtml(seatInitials(seat.name))}</span>
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
  if (state.engine === "web") return seatBridgeReady(seatId) ? "已选" : "待校准";
  if (state.currentVerdict?.seat_scores?.some(item => item.seat === seatId)) {
    return state.currentVerdict?.engine === "local-auto-jury-v3.4" ? "本地评分" : "完成";
  }
  if (state.currentRunId) return "等待";
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
  return { ...snapshot, confirmed: true, confirmed_at: new Date().toISOString() };
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

async function submitJudge() {
  const question = $("#question-input").value.trim();
  if (!question) return;

  if (!confirmMentorGate(question)) return;

  const mentorPreflight = mentorPayloadForSubmit(question);
  switchTab("draft");
  resetRunUI();
  setBusy(true);
  setProgress(3, "提交任务中");

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
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.currentRunId = data.run_id;
    state.lastHistoryRunId = data.run_id;
    localStorage.setItem("ai_judge_last_run_id", data.run_id);
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `${engineName(data.engine)} · ${data.mode_name} · ${data.seat_count} 席`;
    state.mentorConfirmed = false;
    updateMentorPreflight();
    startProgress(data.run_id);
    await loadHistory();
  } catch (err) {
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
  state.currentTask = task;
  const pct = Math.round((Number(task.progress) || 0) * 100);
  setProgress(pct, task.current_step || task.status || "运行中");
  renderRunDiagnostics(task);
  renderTaskCenter();
  renderCouncilCompletion();

  if (task.status === "complete") {
    cleanupProgress();
    setBusy(false);
    state.recheckInFlight = false;
    renderRunDiagnostics(null);
    if (task.result) renderVerdict(task.result);
    else loadVerdict(task.run_id);
    loadHistory();
    maybeBrowserNotify("AI Judge 判词已完成", task.question || "");
  }
  if (task.status === "failed" || task.status === "cancelled") {
    cleanupProgress();
    setBusy(false);
    state.recheckInFlight = false;
    setProgress(pct, task.error || task.status);
    renderSupplementButton();
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
  $("#verdict-title").textContent = v.one_liner || "AI Judge 判词已完成";
  $("#verdict-question").textContent = v.question || "";
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
  $("#final-report-answer").textContent = finalReportText(v);
  $("#reason-list").innerHTML = (v.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join("");
  $("#step-list").innerHTML = (v.next_steps || []).map(step => `<li>${escapeHtml(step)}</li>`).join("");
  renderDecisionMemo(v);
  $("#view-link").href = v.view_url || `${API_BASE}/api/judge/${v.run_id}/verdict`;
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
}

function finalReportText(v) {
  const closeoutReport = v?.cross_temporal_analysis?.closeout_report?.professional_report || "";
  if (closeoutReport) return closeoutReport;
  const judgeAnswer = v?.judge_answer?.answer || v?.single_judge_baseline?.answer || "";
  if (judgeAnswer) return judgeAnswer;
  const line = v?.one_liner || "本轮判断已完成。";
  const reasons = (v?.reasons || []).slice(0, 2).join("；");
  const steps = (v?.next_steps || []).slice(0, 2).join("；");
  return [line, reasons ? `关键依据：${reasons}` : "", steps ? `建议动作：${steps}` : ""].filter(Boolean).join("\n");
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
  $("#memo-subject").textContent = executionComplete
    ? (v?.one_liner || "AI Judge 最终结论")
    : (v?.one_liner || "必需席位执行未完成");
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
  $("#memo-steps").innerHTML = (steps.length ? steps : ["处理待回收席位", "复核证据链与发布门禁"])
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
  if (confidence >= 70) return { tier: "B", label: "B · 可内部参考", summary: "可内部参考，发布前仍需人工复核。" };
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
  const nonHumanReady = hasVerdict
    && supplementable === 0
    && hardFailures === 0
    && (!verdictUsesWeb || policy.collection_complete)
    && evidence.state !== "block"
    && coverage.total > 0
    && (coverage.pct >= 100 || !verdictUsesWeb)
    && (traceEvents.length > 0 || hasVerdict);
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
      hint: "报告要写明不确定性、阻断或人工复核边界",
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
      text: "人工发布确认",
      hint: "发布按钮不会发送外部内容，只标记本轮可发布",
      meta: state.publishCleared ? "通过" : "待确认",
      state: state.publishCleared && nonHumanReady ? "ok" : "block",
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
  $("#publishStatusText").textContent = ready ? "可发布" : summary.nonHumanBlockers ? "阻断中" : hasVerdict ? "待人工确认" : "等待判词";
  $("#gateBadge").className = `pill ${ready ? "chip-ok" : summary.nonHumanBlockers ? "chip-block" : "chip-warn"}`;
  $("#gateBadge").textContent = ready ? "READY" : summary.nonHumanBlockers ? "LOCKED" : "REVIEW";
  $("#gateState").classList.toggle("is-ready", ready);
  $("#gateState").classList.toggle("is-locked", !ready);
  $("#gateState").textContent = ready ? "可发布" : summary.nonHumanBlockers ? "不可发布" : "待确认";
  $("#gateMeter")?.classList.toggle("is-ready", ready);
  if ($("#gateReason")) $("#gateReason").textContent = summary.reason;
  const canConfirm = hasVerdict && summary.nonHumanBlockers === 0;
  $("#clearBlockersBtn").disabled = !canConfirm;
  $("#clearBlockersBtn").textContent = state.publishCleared ? "已人工确认" : "人工确认发布级";
  $("#publishBtn").disabled = !ready;
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
  if (!judge && !baseline) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.querySelector("h3").textContent = judge?.label || baseline?.label || "AI Judge 法官答案";
  $("#judge-answer-summary").textContent = judge?.answer || baseline?.answer || "";
  const tags = [
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
        tags: ["Claim pending"],
      },
      {
        layer: "L2",
        title: "网页席位健康基线",
        body: counts.webTotal ? `当前网页席位 ${counts.webReady}/${counts.webTotal} 就绪。` : "还没有读取到网页席位配置。",
        state: counts.webTotal && counts.webReady === counts.webTotal ? "ok" : "warn",
        tags: ["Web bridge", `${counts.webReady}/${counts.webTotal}`],
      },
      {
        layer: "L3",
        title: "发布前审计轨迹",
        body: "判词完成后会显示执行轨迹、回收状态和发布门禁。",
        state: "block",
        tags: ["Trace pending"],
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
      title: "本地席位评分",
      body: `${v.seat_scores.length} 个本地席位参与评分，原始评分保留在模型对比页。`,
      state: "ok",
      tags: ["Local seats", `${v.seat_scores.length}`],
    });
  } else {
    nodes.push({
      layer: "L2",
      title: "证据来源待补充",
      body: "当前判词没有可展示的网页原文或席位评分，发布前需要人工复核来源。",
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
  const checks = [
    { title: "原始问题保留", meta: state.currentVerdict?.question ? "通过" : "等待", state: state.currentVerdict?.question ? "ok" : "block" },
    { title: "证据节点", meta: `${nodes.length} 个`, state: nodes.some(node => node.state === "block") ? "block" : nodes.some(node => node.state === "warn") ? "warn" : "ok" },
    { title: "网页席位校准", meta: bridgeChannelCounts().webTotal ? `${bridgeChannelCounts().webReady}/${bridgeChannelCounts().webTotal}` : "本地", state: bridgeChannelCounts().webReady === bridgeChannelCounts().webTotal ? "ok" : "warn" },
    { title: "发布引用复核", meta: "看发布门禁", state: buildPublishGateSummary().nonHumanBlockers ? "block" : "ok" },
  ];
  $("#evidence-check-list").innerHTML = checks.map(item => `
    <li class="${escapeAttr(item.state)}"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.meta)}</span></li>
  `).join("");
  const blockers = nodes.filter(node => node.state === "block").length;
  $("#evidence-next-action").textContent = blockers
    ? `还有 ${blockers} 个证据阻断，先处理失败席位或缺失日志。`
    : nodes.some(node => node.state === "warn")
      ? "证据链已形成，但仍建议先处理黄色提示后再发布。"
      : "证据链可进入发布门禁复核。";
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
      channelLabel((bridgeMatrixBySeat(seat.id) || bridgeSeatById(seat.id) || {}).channel || (state.engine === "web" ? "web" : "local")),
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
    if (!runs.length) {
      list.innerHTML = `<li class="muted">暂无历史任务</li>`;
      return;
    }
    list.innerHTML = runs.map(run => `
      <li class="history-item" data-id="${escapeAttr(run.run_id)}">
        <div class="history-main">
          <strong>${escapeHtml(run.question || "")}</strong>
          <span class="history-meta">
            <span>${escapeHtml(run.mode || "-")}</span>
            <span>${escapeHtml(run.status || "-")}</span>
            <span>${Math.round((run.progress || 0) * 100)}%</span>
          </span>
        </div>
        <span class="history-id">${escapeHtml(compactRunId(run.run_id))}</span>
      </li>
    `).join("");
    $$(".history-item").forEach(item => item.addEventListener("click", () => openHistoryRun(item.dataset.id, { switchToConversation: false })));
  } catch {
    list.innerHTML = `<li class="muted">API Server 未连接</li>`;
  }
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
  const runId = item.run_id || "";
  const traceCount = item.execution_trace?.events?.length || 0;
  const score = displayScore(item.average_score ?? item.confidence);
  const report = item.view_url ? `<a class="ghost" href="${escapeAttr(item.view_url)}">完整报告</a>` : "";
  const chief = chiefJudgeLabel(item);
  const seatCount = (item.seat_roster?.selected || item.seat_scores || []).length || "-";
  const mode = item.mode_name || item.mode || "-";
  detail.innerHTML = `
    <div class="ledger-detail-head">
      <div>
        <h2>${escapeHtml(excerpt(item.one_liner || item.question || "议事详情", 140))}</h2>
        <p class="muted">${escapeHtml(excerpt(item.question || "", 360))}</p>
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
    <div class="ledger-note" id="history-summary-note">${escapeHtml(historySummaryText(item))}</div>
    <pre id="history-detail-pre" hidden>${escapeHtml(historyDetailPreview(item))}</pre>
  `;
  detail.querySelector("[data-open-run]")?.addEventListener("click", () => switchTab("draft"));
  detail.querySelectorAll("[data-history-section]").forEach(button => {
    button.addEventListener("click", () => setHistoryDetailSection(detail, item, button.dataset.historySection));
  });
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
    note.textContent = historySummaryText(item);
  }
}

function historySummaryText(item) {
  const line = item.one_liner || item.verdict_label || "本轮议事已归档";
  const question = item.question ? `问题：${item.question}` : "";
  const next = (item.next_steps || []).slice(0, 2).join("；");
  return [line, question, next ? `下一步：${next}` : ""].filter(Boolean).join("\n");
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
  if (!button.disabled) button.textContent = submitButtonLabel();
}

function submitButtonLabel() {
  if (state.mentorEnabled && !state.mentorConfirmed) return "确认任务";
  return state.engine === "web" ? "网页陪审" : "开始评议";
}

function isReady() {
  if ($("#question-input").value.trim().length < 4 || state.selectedSeats.size === 0) return false;
  if (state.engine !== "web") return true;
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
  return "本地引擎";
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

function downloadMarkdown(v) {
  const md = [
    "# AI Judge Verdict",
    "",
    `**Question:** ${v.question || ""}`,
    `**Verdict:** ${v.verdict_label || v.verdict}`,
    `**Confidence:** ${v.confidence}%`,
    "",
    "## One Liner",
    v.one_liner || "",
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
    { mode: "flash", name: "Flash 快速陪审", seats: ["gemini", "grok", "doubao"] },
    { mode: "standard", name: "Standard 标准陪审", seats: ["gemini", "deepseek", "claude", "kimi", "grok", "doubao"] },
    { mode: "strategic", name: "Strategic 深度陪审", seats: [] },
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
  ];
}

function $(selector) { return document.querySelector(selector); }
function $$(selector) { return Array.from(document.querySelectorAll(selector)); }
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}
function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}
