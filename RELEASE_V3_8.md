# AI Judge v3.8.0

AI Judge v3.8.0 upgrades the desktop product into a Trust Workbench: a simple closeout surface for everyday decisions, plus a professional reliability console for seat diagnostics, bridge recovery, and benchmark evidence.

## Highlights

- Adds `/api/product/capabilities` and `/api/benchmarks/summary` so the desktop UI can explain Stable mode, Lab mode, Human Gavel states, and reliability cards from the backend.
- Adds a paper-style `final_report` payload with abstract, postulates, evidence map, execution plan, limits, and verification contract across local and web jury runs.
- Updates the dashboard to v3.8.0 with simplified workflow labels: 定义问题, 收集席位, 自动救援, 可信分层, 人工确认.
- Adds a simple-mode closeout strip and a pro-only reliability benchmark page.
- Updates the macOS wrapper user agent and packaging metadata to `3.8.0`.
- Keeps the parser guardrail for PDF/Docx batch inputs: unsupported document formats are visible in manifests and can fail CI explicitly.

## Validation

- `pytest`
- `ruff check`
- `node --check product/dashboard.js`
- `swiftc -parse desktop/AIJudgeDesktop.swift`
- Local API smoke on `127.0.0.1:8501` for `/api/health`, `/api/product/capabilities`, and `/api/benchmarks/summary`
