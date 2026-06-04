# P9 Impact Matrix

| Change Item | Affected File | Affected API | Data Risk | UI Risk | Regression Required | Rollback Method |
|---|---|---|---|---|---|---|
| Dashboard Maintenance Panel | dashboard.js (new section only) | None | None (readonly) | Low (new panel, no existing change) | UI smoke test | Remove panel div from dashboard.js |
| Release/Drift/Readiness Shortcut Buttons | dashboard.js (new buttons) | None (call existing endpoints) | None | Low | UI button click test | Remove button elements, revert dashboard.js |
| Operator Action Trace | dashboard.js (trace logger) | None (write to local trace file) | None (append only) | None | Trace append test | Remove trace logger code |
| Vault Index Links | dashboard.js (link elements) | None | None | None | Link click test | Remove link elements |
| API Summary Endpoint (optional) | api_server.py (new route only) | GET /api/p9/summary (new) | None (readonly aggregation) | None | HTTP 200 check | Remove route, restart API |
