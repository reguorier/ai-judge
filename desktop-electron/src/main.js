const { app, BrowserWindow, Menu, clipboard, dialog, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const path = require('path');

const APP_NAME = 'AI Judge';
const DEFAULT_PORT = 8501;
const DEFAULT_HOST = '127.0.0.1';

let mainWindow = null;
let serverProcess = null;
let ownsServer = false;
let config = null;
let logPath = null;

function loadConfig() {
  const resourceConfig = app.isPackaged
    ? path.join(process.resourcesPath, 'config.json')
    : path.join(__dirname, '..', 'resources', 'config.json');
  let parsed = {};
  try {
    parsed = JSON.parse(fs.readFileSync(resourceConfig, 'utf8'));
  } catch (_) {
    parsed = {};
  }
  const envRoot = process.env.AI_JUDGE_PROJECT_ROOT;
  const projectRoot = resolveProjectRoot(envRoot || parsed.projectRoot || path.resolve(__dirname, '..', '..'));
  return {
    projectRoot,
    host: parsed.host || DEFAULT_HOST,
    port: Number(parsed.port || DEFAULT_PORT),
    startupPath: parsed.startupPath || '/',
  };
}

function resolveProjectRoot(value) {
  const input = String(value || '').trim();
  if (!input) return path.resolve(__dirname, '..', '..');
  if (input === '$APP_RESOURCES') return process.resourcesPath;
  if (input.startsWith('$APP_RESOURCES/')) {
    return path.join(process.resourcesPath, input.slice('$APP_RESOURCES/'.length));
  }
  if (input.startsWith('~/')) {
    return path.join(app.getPath('home'), input.slice(2));
  }
  return path.resolve(input);
}

function baseUrl() {
  return `http://${config.host}:${config.port}`;
}

function requestJson(url, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, json: JSON.parse(body) });
        } catch (_) {
          resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, text: body });
        }
      });
    });
    req.on('timeout', () => {
      req.destroy();
      resolve({ ok: false, error: 'timeout' });
    });
    req.on('error', (error) => resolve({ ok: false, error: error.message }));
  });
}

async function checkHealth() {
  return requestJson(`${baseUrl()}/api/health`, 1200);
}

function pythonCandidates() {
  const root = config.projectRoot;
  return [
    path.join(root, 'python', 'bin', 'python3.12'),
    path.join(root, 'python', 'bin', 'python3'),
    path.join(root, 'python', 'bin', 'python'),
    path.join(root, '.venv', 'bin', 'python'),
    path.join(root, '.venv', 'bin', 'python3'),
    '/opt/homebrew/bin/python3.14',
    '/opt/homebrew/bin/python3',
    '/usr/bin/python3',
  ];
}

function executableExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch (_) {
    return false;
  }
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function ensureDataDir() {
  const dataDir = path.join(config.projectRoot, 'data');
  fs.mkdirSync(dataDir, { recursive: true });
  logPath = path.join(dataDir, 'electron-shell-server.log');
  return dataDir;
}

function startServer() {
  const root = config.projectRoot;
  const serverScript = path.join(root, 'product', 'api_server.py');
  if (!fs.existsSync(serverScript)) {
    throw new Error(`AI Judge API server was not found: ${serverScript}`);
  }
  const python = pythonCandidates().find(executableExists);
  if (!python) {
    throw new Error('Python runtime was not found. Expected .venv/bin/python or Homebrew python3.');
  }

  ensureDataDir();
  const out = fs.openSync(logPath, 'a');
  const launchCommand = [
    `cd ${shellQuote(root)}`,
    `exec ${shellQuote(python)} ${shellQuote(serverScript)} --host ${shellQuote(config.host)} --port ${shellQuote(String(config.port))}`,
  ].join(' && ');

  const env = {
    ...process.env,
    AI_JUDGE_APP_URL: baseUrl(),
    AI_JUDGE_DESKTOP_CLIENT: '1',
    AI_JUDGE_ELECTRON_SHELL: '1',
    PYTHONUNBUFFERED: '1',
  };
  delete env.__PYVENV_LAUNCHER__;
  const venvBin = path.join(root, '.venv', 'bin');
  env.PATH = `${venvBin}:${env.PATH || '/usr/bin:/bin:/usr/sbin:/sbin'}`;

  serverProcess = spawn('/bin/zsh', ['-lc', launchCommand], {
    cwd: root,
    env,
    stdio: ['ignore', out, out],
  });
  ownsServer = true;
  serverProcess.on('exit', () => {
    serverProcess = null;
    ownsServer = false;
  });
}

async function ensureServer() {
  const health = await checkHealth();
  if (health.ok) return health;
  startServer();
  const started = Date.now();
  while (Date.now() - started < 70000) {
    const next = await checkHealth();
    if (next.ok) return next;
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`AI Judge API did not become ready. Log: ${logPath || '(not created)'}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    title: APP_NAME,
    backgroundColor: '#0f1117',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 18 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
}

function buildMenu() {
  const template = [
    {
      label: APP_NAME,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { label: '重新连接服务', click: () => mainWindow && mainWindow.webContents.send('shell:refresh-status') },
        { label: '打开服务日志', click: () => revealLogs() },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'front' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function revealLogs() {
  if (!logPath) ensureDataDir();
  if (logPath && fs.existsSync(logPath)) return shell.showItemInFolder(logPath);
  return dialog.showMessageBox({ type: 'info', message: '日志文件尚未创建。' });
}

ipcMain.handle('shell:get-config', () => ({
  baseUrl: baseUrl(),
  projectRoot: config.projectRoot,
  port: config.port,
  logPath,
}));

ipcMain.handle('shell:get-status', async () => {
  const [health, bridge] = await Promise.all([
    requestJson(`${baseUrl()}/api/health`, 1200),
    requestJson(`${baseUrl()}/api/bridge/status`, 1800),
  ]);
  return {
    health,
    bridge,
    baseUrl: baseUrl(),
    ownedServer: ownsServer,
    pid: serverProcess ? serverProcess.pid : null,
    logPath,
  };
});

ipcMain.handle('shell:restart-server', async () => {
  if (ownsServer && serverProcess && !serverProcess.killed) {
    serverProcess.kill('SIGTERM');
  }
  await new Promise((resolve) => setTimeout(resolve, 600));
  startServer();
  return ensureServer();
});

ipcMain.handle('shell:open-external', (_, url) => shell.openExternal(url));
ipcMain.handle('shell:copy-text', (_, text) => {
  clipboard.writeText(String(text || ''));
  return true;
});
ipcMain.handle('shell:reveal-logs', () => revealLogs());

app.whenReady().then(async () => {
  config = loadConfig();
  buildMenu();
  createWindow();
  try {
    await ensureServer();
  } catch (error) {
    dialog.showErrorBox('AI Judge 启动失败', error.message);
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => {
  if (ownsServer && serverProcess && !serverProcess.killed) {
    serverProcess.kill('SIGTERM');
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
