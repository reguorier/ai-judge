# AI Judge v3.7.0

AI Judge v3.7.0 upgrades the desktop client from a status-oriented command center into a Decision Audit Workbench for execution-gated multi-model review.

## Highlights

- Adds the Decision Audit Workbench surface for request intake, mentor gate, draft synthesis, evidence review, model comparison, and publish readiness.
- Expands web-seat orchestration to 13 configured seats with fixed visible Chrome tabs and per-seat readiness reporting.
- Marks Grok as best-effort while keeping the remaining web seats execution-required for publish confidence.
- Adds Recovery Cockpit behavior for slow or supplementable seats so delayed model pages can be rechecked instead of treated as final failures.
- Adds Reasoning Tree, evidence trace, trust tier, and cross-temporal closeout views to keep claims, dissent, blockers, and follow-up actions inspectable.
- Keeps publish as a hard gate: no external release action should happen without required execution coverage, traceability, risk disclosure, and human confirmation.

## Commands

```bash
PYTHONPATH=. python product/api_server.py
```

Then open:

```text
http://127.0.0.1:8501/
```

Useful checks:

```bash
curl http://127.0.0.1:8501/api/health
curl http://127.0.0.1:8501/api/bridge/status
```

## Validation

- `node --check product/dashboard.js`
- `.venv/bin/python -m pytest tests/test_web_bridge_capture.py tests/test_web_bridge_retry.py tests/test_chrome_fixed_tab_modes.py tests/test_product_state.py`
- `python3 tools/check_eval4sd_packet.py`
