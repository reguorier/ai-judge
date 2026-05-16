# AI Judge v3.5.0

AI Judge v3.5.0 packages the macOS desktop client around the local web command center.

## Highlights

- macOS `AI Judge.app` wrapper with a signed local WebKit shell.
- v3.5 command center UI with request intake, mentor gate, draft generation, evidence review, model comparison, publish gate, recent ledger, and settings.
- Web bridge status and calibration surfaces for 13 model seats.
- Grand Judge citation verification, replay ledger traces, slow-seat supplementation, and publish readiness checks.
- AJ desktop icon and in-app brand mark with a consistent visual system.

## Packaging

Build and install locally:

```bash
./Install-AI-Judge.command
```

Build only:

```bash
python tools/build_mac_app.py
```

The macOS app uses `product/api_server.py` as the local backend and serves the same `product/dashboard.html` and `product/dashboard.js` used by the browser version.

## Validation

- `node --check product/dashboard.js`
- `python -m pytest`
- `python -m ruff check tools/build_mac_app.py tools/install_mac_app.py --no-cache`
- `codesign --verify --deep --strict ~/Applications/AI\ Judge.app`
