const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('AIJudgeShell', {
  getConfig: () => ipcRenderer.invoke('shell:get-config'),
  getStatus: () => ipcRenderer.invoke('shell:get-status'),
  restartServer: () => ipcRenderer.invoke('shell:restart-server'),
  openExternal: (url) => ipcRenderer.invoke('shell:open-external', url),
  copyText: (text) => ipcRenderer.invoke('shell:copy-text', text),
  revealLogs: () => ipcRenderer.invoke('shell:reveal-logs'),
});
