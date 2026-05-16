# AI Judge v3.5.1

AI Judge v3.5.1 is a macOS desktop client patch release.

## Fixes

- Restores standard macOS editing commands inside the desktop WKWebView shell.
- Adds the `Edit` menu with Undo, Redo, Cut, Copy, Paste, Paste and Match Style, and Select All.
- Fixes `Command+V` paste, `Command+C` copy, and `Command+A` select-all behavior in the request input box and other text fields.

## Validation

- `swiftc desktop/AIJudgeDesktop.swift -framework Cocoa -framework WebKit`
- `node --check product/dashboard.js`
- `python -m pytest`
- `python -m ruff check product/api_server.py tools/build_mac_app.py tools/install_mac_app.py tests/test_evidence_os.py tests/test_product_state.py tests/test_report_render.py --ignore E402 --no-cache`
- `codesign --verify --deep --strict ~/Applications/AI\ Judge.app`
