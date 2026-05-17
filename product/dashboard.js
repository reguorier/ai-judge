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
]);

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
  await refreshAll();
  applyMode("flash");
  applyEngine("local");
  await restoreLastRun();
});

function bindUI() {
  $$(".tab").forEach(tab => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
  $$("[data-tab-shortcut]").forEach(item => item.addEventListener("click", () => switchTab(item.dataset.tabShortcut)));
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
  });
  $("#btn-clear-all").addEventListener("click", () => {
    state.selectedSeats.clear();
    state.mentorConfirmed = false;
    renderSeats();
    updateMentorPreflight();
    updateSubmitState();
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
}

function applyProductMode(mode) {
  state.productMode = mode === "pro" ? "pro" : "simple";
  localStorage.setItem("ai_judge_product_mode", state.productMode);
  $("#app-shell").classList.toggle("pro-mode", state.productMode === "pro");
  $("#app-shell").classList.toggle("simple-mode", state.productMode !== "pro");
  $$("#product-switch .product-mode").forEach(btn => btn.classList.toggle("active", btn.dataset.productMode === state.productMode));
  if (state.currentVerdict) renderDecisionMemo(state.currentVerdict);
  renderArena();
  renderSimpleSeatSummary();
}

async function refreshAll() {
  await Promise.all([loadModes(), loadSeats(), loadBridgeStatus(), loadHistory(), loadSeatScoreboard()]);
  renderSeatScores();
  renderArena();
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
  return ((state.currentVerdict?.web_bridge || {}).raw_results || []).filter(isSupplementableResult);
}

function renderSupplementButton() {
  const btn = $("#btn-supplement-slow");
  const panel = $("#recovery-panel");
  if (!btn) {
    if (panel) panel.hidden = true;
    return;
  }
  const seats = supplementableRawResults();
  const visible = Boolean(state.currentVerdict?.run_id && seats.length);
  btn.hidden = !visible;
  if (panel) panel.hidden = !visible;
  btn.disabled = false;
  btn.textContent = seats.length
    ? `回收旧页面答案 (${seats.map(item => item.seat_name || item.seat).join("、")})`
    : "回收旧页面答案";
}

async function supplementSlowSeats() {
  const sourceRunId = state.currentVerdict?.run_id;
  const seats = supplementableRawResults().map(item => item.seat).filter(Boolean);
  if (!sourceRunId || !seats.length) return;

  const btn = $("#btn-supplement-slow");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "读取旧页面...";
  }
  setProgress(4, `读取旧页面答案：${seats.join(", ")}`);
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
    const res = await fetch(`${API_BASE}/api/judge/${sourceRunId}/supplement`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seats, notify }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.currentRunId = data.run_id;
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `旧页面回收 ${data.seat_count} 席 · 合并回 ${sourceRunId}`;
    startProgress(data.run_id);
    await loadHistory();
  } catch (err) {
    setProgress(0, `旧页面回收失败：${err.message}`);
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
        || ["慢生成", "超时", "发送未确认", "提交未确认", "疑似旧回答"].includes(statusName);
    })
    .map(seat => seat.seat)
    .filter(Boolean);
}

async function recheckStalledSeats({ auto = false } = {}) {
  const task = state.currentTask;
  const sourceRunId = task?.run_id || state.currentRunId;
  const seats = recheckableDiagnosticSeats(task?.progress_diagnostics);
  if (!sourceRunId || !seats.length || state.recheckInFlight) return;
  state.recheckInFlight = true;
  clearAutoRecheck();
  const btn = $("#btn-recheck-stalled");
  if (btn) {
    btn.disabled = true;
    btn.textContent = auto ? "自动读取旧页面..." : "读取旧页面...";
  }
  setProgress(4, `${auto ? "自动" : "手动"}读取旧页面答案：${seats.join(", ")}`);
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
      body: JSON.stringify({ seats, notify }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.currentRunId = data.run_id;
    $("#run-id").textContent = data.run_id;
    $("#run-meta").textContent = `旧页面回收 ${data.seat_count} 席 · 写回 ${sourceRunId}`;
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
  const okCount = bridge.ok_count ?? judge.ok_count;
  const totalCount = bridge.requested_count ?? ((judge.ok_count || 0) + (judge.failed_count || 0));
  const reportMeta = [
    v.run_id ? `Run ${compactRunId(v.run_id)}` : "",
    v.verdict_label || v.verdict ? `结论 ${v.verdict_label || v.verdict}` : "",
    v.confidence !== undefined ? `可信度 ${v.confidence}%` : "",
    okCount !== undefined && totalCount !== undefined ? `席位 ${okCount}/${totalCount}` : "",
  ].filter(Boolean);
  $("#report-meta").innerHTML = reportMeta.map(item => `<span>${escapeHtml(item)}</span>`).join("");
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
  renderTrace(v.execution_trace);
  if (v.run_id) loadTrace(v.run_id);
  loadSeatScoreboard().then(() => {
    renderSeatScores();
    renderArena();
  });
  renderSeatScores();
  renderArena();
  renderSimpleSeatSummary();
  renderPublishGate();
}

function finalReportText(v) {
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
  const okCount = bridge.ok_count ?? raw.filter(item => item.ok).length;
  const failedCount = bridge.failed_count ?? raw.filter(item => !item.ok).length;
  const totalCount = (bridge.requested_count ?? raw.length) || (v?.seat_count || v?.seats?.length || 0);
  const confidence = v?.confidence !== undefined ? `${v.confidence}%` : "-";
  const reasons = (v?.reasons || []).filter(Boolean);
  const steps = (v?.next_steps || []).filter(Boolean);
  const risk = reasons.find(item => /风险|阻断|不足|失败|不完整/.test(item)) || (failedCount ? `${failedCount} 个席位未形成可评分答案` : "未发现硬阻断");
  $("#memo-subject").textContent = v?.one_liner || "AI Judge 最终结论";
  $("#memo-executive").textContent = excerpt(finalReportText(v), state.productMode === "pro" ? 520 : 260);
  $("#memo-confidence").textContent = confidence;
  $("#memo-verdict").textContent = v?.verdict_label || v?.verdict || "-";
  $("#memo-seats").textContent = totalCount ? `${okCount}/${totalCount} 有效` : "-";
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

function renderPublishGate(message = "") {
  if (!$("#publishChecklist")) return;
  const hasVerdict = Boolean(state.currentVerdict);
  const supplementable = supplementableRawResults().length;
  const confidence = Number(state.currentVerdict?.confidence || 0);
  const ready = state.publishCleared || (hasVerdict && confidence >= 80 && supplementable === 0);
  const items = [
    { text: "判词已生成", hint: "完整保留问题、立场与下一步", meta: hasVerdict ? "通过" : "等待结果", state: hasVerdict ? "ok" : "block" },
    { text: "旧页面答案回收", hint: "失败或超时席位不伪装为共识", meta: supplementable ? `${supplementable} 席待回收` : "无待回收", state: supplementable ? "warn" : "ok" },
    { text: "可信度阈值", hint: "低于阈值时只允许内部保存", meta: hasVerdict ? `${confidence}%` : "等待评分", state: confidence >= 80 ? "ok" : hasVerdict ? "warn" : "block" },
    { text: "人工发布确认", hint: "最终发布仍需人工确认", meta: ready ? (message || "通过") : "需要确认", state: ready ? "ok" : "block" },
  ];
  $("#publishChecklist").innerHTML = items.map(item => `
    <li class="${item.state}">
      <span class="gate-check-title"><strong>${escapeHtml(item.text)}</strong><small>${escapeHtml(item.hint)}</small></span>
      <span>${escapeHtml(item.meta)}</span>
    </li>
  `).join("");
  const blockers = items.filter(item => item.state !== "ok").length;
  $("#blockerCount").textContent = blockers;
  $("#publishBlockerMetric").textContent = blockers;
  $("#publishConfidence").textContent = hasVerdict ? `${confidence}%` : "-";
  $("#publishStatusText").textContent = ready ? "可发布" : blockers ? "阻断中" : "待确认";
  $("#gateBadge").className = `pill ${ready ? "chip-ok" : "chip-block"}`;
  $("#gateBadge").textContent = ready ? "READY" : "LOCKED";
  $("#gateState").classList.toggle("is-ready", ready);
  $("#gateState").classList.toggle("is-locked", !ready);
  $("#gateState").textContent = ready ? "可发布" : "不可发布";
  $("#gateMeter")?.classList.toggle("is-ready", ready);
  const gateReason = ready
    ? "全部门禁通过，报告可标记为发布级可用。"
    : supplementable
      ? `仍有 ${supplementable} 个旧页面答案需要回收，请回到请求录入页右侧处理。`
      : blockers
        ? `仍有 ${blockers} 个门禁项需要处理。`
        : "没有硬阻断，但仍建议人工复核后发布。";
  if ($("#gateReason")) $("#gateReason").textContent = gateReason;
  $("#publishBtn").disabled = !ready;
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
    recheckBtn.textContent = recheckSeats.length
      ? `只读回收 (${recheckSeats.map(seatName).join("、")})`
      : "回收旧页面答案";
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
        </span>
      </div>
    `).join("");
  }
  box.hidden = false;
  scheduleAutoRecheck(task, diag);
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
  $("#trace-panel").hidden = true;
  renderSupplementButton();
  renderArena();
  renderPublishGate();
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
  if (reason === "response_not_relevant") return "疑似旧回答";
  if (reason === "existing_answer_not_found") return "旧页未返回";
  if (reason === "existing_answer_placeholder") return "仍是占位";
  if (reason === "existing_answer_prompt_echo") return "旧页未完成";
  if (reason === "desktop_bridge_ready") return "客户端就绪";
  if (reason === "not_configured") return "未配置";
  return reason || "待配置";
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
