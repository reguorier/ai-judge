const frame = document.getElementById('judge-frame');
const loadingLayer = document.getElementById('loading-layer');
const apiStatus = document.getElementById('api-status');
const seatStatus = document.getElementById('seat-status');
const portStatus = document.getElementById('port-status');
const viewTitle = document.getElementById('view-title');
const guideModal = document.getElementById('guide-modal');
const promptList = document.getElementById('prompt-list');
const copyState = document.getElementById('copy-state');
const GUIDE_DISMISSED_KEY = 'aiJudgeElectronGuideDismissedV1';

const prompts = [
  {
    title: '投资/产品判断',
    desc: '适合判断一个方向是否值得继续投入。',
    text: `请作为 AI Judge 对这个产品/投资判断做裁决。

背景：
- 我正在评估：
- 当前证据：
- 最大不确定性：

请输出：
1. 一句话结论
2. 支持与反对证据
3. 关键风险与反证
4. 需要补充验证的事实
5. 是否值得进入下一阶段，以及原因`,
  },
  {
    title: '功能方案评审',
    desc: '适合比较多种实现路径，找出最稳的下一步。',
    text: `请评审下面的功能方案。

目标：
用户场景：
候选方案：
A.
B.
C.

请从用户价值、实现复杂度、风险、可验证性和下一步行动给出裁决。不要只给折中建议，必须选出推荐路径。`,
  },
  {
    title: '事实/引用核查',
    desc: '适合检查报告、网页、论文、宣传内容是否站得住。',
    text: `请做事实和引用核查。

待核查内容：

要求：
1. 拆出关键 claim
2. 标注 supported / unsupported / unverifiable
3. 说明每个 claim 需要什么证据
4. 区分“没有证据”和“证据为假”
5. 给出可以发布或必须修改的结论`,
  },
  {
    title: '运行诊断',
    desc: '适合模型席位、网页桥、超时或失败后的复盘。',
    text: `请诊断这次 AI Judge 运行为什么没有达到可发布状态。

Run ID 或现象：

请检查：
1. 哪些席位真正执行了
2. 哪些席位失败、超时或未校准
3. publish gate 被什么阻断
4. 是否可以补跑或需要重新校准
5. 下一步最小修复动作`,
  },
];

let shellConfig = null;

function setStatus(el, text, tone) {
  el.textContent = text;
  el.className = tone || '';
}

function showGuide(force = false) {
  if (!force && localStorage.getItem(GUIDE_DISMISSED_KEY) === '1') return;
  guideModal.hidden = false;
}

function hideGuide() {
  const dontShow = document.getElementById('dont-show-guide').checked;
  if (dontShow) localStorage.setItem(GUIDE_DISMISSED_KEY, '1');
  guideModal.hidden = true;
}

function renderPrompts() {
  promptList.innerHTML = prompts.map((prompt, index) => `
    <article class="prompt-card">
      <div>
        <h4>${escapeHtml(prompt.title)}</h4>
        <p>${escapeHtml(prompt.desc)}</p>
      </div>
      <div class="prompt-text">${escapeHtml(prompt.text)}</div>
      <button data-copy-prompt="${index}">复制引导词</button>
    </article>
  `).join('');
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function navigate(path = '/') {
  if (!shellConfig) return;
  const target = new URL(path, shellConfig.baseUrl);
  target.searchParams.set('desktop_shell', 'electron');
  target.searchParams.set('ts', String(Date.now()));
  loadingLayer.classList.remove('hidden');
  frame.src = target.toString();
}

async function refreshStatus() {
  const status = await window.AIJudgeShell.getStatus();
  if (status.health && status.health.ok) {
    setStatus(apiStatus, '在线', 'ok');
  } else {
    setStatus(apiStatus, '离线', 'bad');
  }

  const bridge = status.bridge && status.bridge.json;
  if (bridge && bridge.ok !== false) {
    const ready = bridge.ready_count ?? (Array.isArray(bridge.seats) ? bridge.seats.filter((seat) => seat.ready).length : 0);
    const total = bridge.seat_count ?? (Array.isArray(bridge.seats) ? bridge.seats.length : 0);
    setStatus(seatStatus, `${ready}/${total}`, ready > 0 ? 'ok' : 'warn');
  } else {
    setStatus(seatStatus, '未连接', 'warn');
  }

  setStatus(portStatus, String(status.baseUrl || shellConfig.baseUrl).replace('http://', ''), 'ok');
}

async function boot() {
  shellConfig = await window.AIJudgeShell.getConfig();
  portStatus.textContent = String(shellConfig.port);
  renderPrompts();
  navigate('/');
  refreshStatus();
  setInterval(refreshStatus, 8000);
  // First rollout of the new independent shell: surface the coach once even if
  // older localStorage state exists from prior desktop experiments.
  setTimeout(() => showGuide(true), 500);
}

document.querySelectorAll('.nav-item[data-path]').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.nav-item[data-path]').forEach((node) => node.classList.remove('active'));
    button.classList.add('active');
    viewTitle.textContent = button.textContent.trim();
    navigate(button.dataset.path || '/');
  });
});

document.getElementById('refresh-button').addEventListener('click', () => {
  refreshStatus();
  if (frame.src) frame.contentWindow.location.reload();
});

document.getElementById('restart-button').addEventListener('click', async () => {
  setStatus(apiStatus, '重连中', 'warn');
  await window.AIJudgeShell.restartServer();
  await refreshStatus();
  navigate('/');
});

document.getElementById('open-browser-button').addEventListener('click', async () => {
  await window.AIJudgeShell.openExternal(shellConfig.baseUrl);
});

document.getElementById('logs-button').addEventListener('click', () => {
  window.AIJudgeShell.revealLogs();
});

document.getElementById('guide-button').addEventListener('click', () => showGuide(true));
document.getElementById('coach-open-button').addEventListener('click', () => showGuide(true));
document.getElementById('guide-close-button').addEventListener('click', hideGuide);
document.getElementById('guide-start-button').addEventListener('click', hideGuide);

guideModal.addEventListener('click', (event) => {
  if (event.target === guideModal) hideGuide();
});

promptList.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-copy-prompt]');
  if (!button) return;
  const prompt = prompts[Number(button.dataset.copyPrompt)];
  await window.AIJudgeShell.copyText(prompt.text);
  copyState.textContent = `已复制：${prompt.title}`;
  button.textContent = '已复制';
  setTimeout(() => {
    button.textContent = '复制引导词';
  }, 1500);
});

frame.addEventListener('load', () => {
  loadingLayer.classList.add('hidden');
});

boot().catch((error) => {
  setStatus(apiStatus, '启动失败', 'bad');
  loadingLayer.innerHTML = `<p>AI Judge 壳启动失败：${escapeHtml(error.message)}</p>`;
});
