# AI Judge Electron Desktop Shell

This is the independent AI Judge desktop shell. It keeps AI Judge as its own product
while replacing the previous minimal Swift WKWebView wrapper with a richer Electron
workbench.

Rollback:

- Previous `.app` builds are backed up under `backups/desktop-shell-*`.
- The legacy Swift wrapper remains in `desktop/AIJudgeDesktop.swift`.
- The old build path remains `tools/build_mac_app.py`.

Runtime:

- The shell starts `product/api_server.py` on `127.0.0.1:8501` when it is not already running.
- The Python AI Judge core remains unchanged.
- Logs are written to `data/electron-shell-server.log`.
