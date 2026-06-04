# Page Context Ingest Specification

This file defines a future page-context contract for AI Judge dashboard and web/desktop work. It does not implement a Chrome extension and does not connect to external Claude services.

## Current Project Surfaces

- Product dashboard: `product/dashboard.html` and `product/dashboard.js`.
- Product API server: `product/api_server.py`.
- Desktop wrapper: documented in `docs/DESKTOP_AND_WEB_BRIDGE.md`; it launches the local dashboard in a WKWebView.
- Frontend reference package: `frontend/`.
- Useful health/capability endpoints referenced in README: `/api/health`, `/api/product/capabilities`, `/api/benchmarks/summary`.
- Web-seat bridge status/calibration uses bridge modules and local data such as `data/web_seats.json` and `data/seat_calibration.json`.

## Goal

Agents should work from captured page state, endpoint state, and screenshot evidence instead of guessing what the dashboard or bridge UI shows.

## Input Contract

Store captured context as JSON in the task artifact directory:

```json
{
  "url": "http://127.0.0.1:8501/",
  "title": "AI Judge",
  "captured_at": "2026-06-04T00:00:00Z",
  "viewport": {
    "width": 1440,
    "height": 900,
    "device_scale_factor": 1
  },
  "selected_text": "",
  "dom_summary": {
    "headings": [],
    "landmarks": [],
    "forms": [],
    "buttons": [],
    "links": [],
    "status_regions": []
  },
  "api_state": {
    "/api/health": {},
    "/api/product/capabilities": {},
    "/api/benchmarks/summary": {}
  },
  "bridge_state": {
    "configured_seats": [],
    "ready_seats": [],
    "blocked_seats": []
  },
  "screenshot_path": "artifacts/YYYYMMDD-task-name/screenshots/dashboard.png",
  "assumptions": []
}
```

## Required Evidence For UI Or Dashboard Work

- URL and viewport.
- Screenshot path when visual behavior matters.
- DOM summary or targeted element selectors.
- Relevant API responses.
- Bridge readiness/calibration state if model-seat execution is involved.
- Known auth/session assumptions.
- Console or server errors, if observed.

## Rules

- First check whether existing product/API endpoints already expose the needed state.
- Do not use the user's active browser, mouse, keyboard focus, or clipboard for bridge work unless the task explicitly requires a foreground operator path.
- Do not mark a web seat ready from UI appearance alone; readiness must follow bridge calibration/status rules.
- A screenshot proves visible state only; it does not prove backend correctness.
- Unknown or unavailable page state must be marked `unknown`.
