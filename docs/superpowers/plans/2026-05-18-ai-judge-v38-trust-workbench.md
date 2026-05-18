# AI Judge v3.8 Trust Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the compressed v3.8 product layer so AI Judge feels like a trustworthy decision workbench rather than a raw multi-model console.

**Architecture:** Keep the existing Flask + static dashboard architecture. Add product metadata and benchmark summaries to the API, then render simple mode as a final-decision closeout surface and pro mode as the diagnostic/reliability console.

**Tech Stack:** Flask, vanilla HTML/CSS/JS, WKWebView desktop wrapper, pytest, ruff, Swift parse check.

---

### Task 1: Product Metadata And API Surface

**Files:**
- Modify: `product/api_server.py`
- Test: `tests/test_product_state.py`

- [x] Add `PRODUCT_VERSION = "3.8.0"` and return it from `/api/health`.
- [x] Add `/api/product/capabilities` with Stable, Lab, rescue, benchmark, and Human Gavel capability cards.
- [x] Add `/api/benchmarks/summary` with four benchmark cards: citation, decision, web-seat recovery, CDP reliability.
- [x] Add tests that assert the version, capability labels, and benchmark ids.

### Task 2: Simplified Closeout And Pro Reliability Console

**Files:**
- Modify: `product/dashboard.html`
- Modify: `product/dashboard.js`

- [x] Rename the workflow to five user-visible steps: 定义问题, 收集席位, 自动救援, 可信分层, 人工确认.
- [x] Add a simple-mode closeout strip above the decision memo: final answer, recommended action, main risk, Human Gavel state.
- [x] Add a pro-only reliability benchmark page/section under the model console.
- [x] Keep recovery buttons in the request/status right rail, not in publish gate.
- [x] Update footer/title/user agent to v3.8.0.

### Task 3: Desktop Sync

**Files:**
- Modify: `desktop/AIJudgeDesktop.swift`

- [x] Update desktop user agent to `AIJudgeDesktop/3.8.0`.
- [x] Keep the existing AJ logo and paste menu behavior.

### Task 4: Verification And Release

**Commands:**
- [x] `pytest tests/test_product_state.py tests/test_cross_temporal_analysis.py tests/test_web_bridge_retry.py tests/test_web_deliberation.py`
- [x] `ruff check product/api_server.py core/cross_temporal_analysis.py core/seat_execution_policy.py bridges/chrome_fixed_tab_bridge.py bridges/web_seat_bridge.py tests/test_product_state.py`
- [x] `node --check product/dashboard.js`
- [x] `swiftc -parse desktop/AIJudgeDesktop.swift`
- [x] Restart local server on port 8501 and verify `/api/health`, `/api/product/capabilities`, `/api/benchmarks/summary`.
- [x] Full `pytest` suite: 114 passed.
- [x] Full `ruff check .` was attempted; it still reports pre-existing repo-wide lint debt outside this change scope, while touched-file ruff passes.
- [x] Commit and push to GitHub.
