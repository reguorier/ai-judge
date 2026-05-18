# AI Judge Command Center Visual Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the desktop AI Judge visual workflow around task details, mentor gate, web bridge health, evidence tree, council trace, publish gate, and report exits.

**Architecture:** Keep the existing single-page dashboard. Add semantic containers in `dashboard.html`, then compute all dynamic state in `dashboard.js` from current verdict, task, trace, bridge, seats, and mentor snapshot. No backend contract changes.

**Tech Stack:** Plain HTML/CSS/JavaScript, existing local API at `http://127.0.0.1:8501`.

---

### Task 1: Command Center Inspector

**Files:**
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.html`
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`

- [ ] Add task detail and inspector containers to the Task Center.
- [ ] Add selected task state and click handlers.
- [ ] Render blocker count, selected task details, bridge health strip, and notification status.

### Task 2: Mentor Gate And Evidence Tree

**Files:**
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.html`
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`

- [ ] Add Mentor Gate Checklist beside the request composer.
- [ ] Replace static evidence rows with a dynamic reasoning tree container.
- [ ] Build evidence nodes from verdict reasons, next steps, web raw results, and trace events.

### Task 3: Council Persona And Trace

**Files:**
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.html`
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`

- [ ] Add COUNCIL-004 persona cards in professional mode.
- [ ] Add L1/L2/L3 trace summary using available verdict and trace data.
- [ ] Keep simple mode focused on seat status only.

### Task 4: Publish Gate Hardening

**Files:**
- Modify: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`

- [ ] Expand publish checks to cover mentor, seat coverage, bridge recovery, evidence, dissent, risk, log, and human confirmation.
- [ ] Compute publish readiness from checks instead of a static 4-row list.
- [ ] Sync task center blocker count with publish checks.

### Task 5: Verification

**Files:**
- Check: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js`
- Check: `/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.html`

- [ ] Run JavaScript syntax check with `node --check product/dashboard.js`.
- [ ] Start the existing API/static server if available.
- [ ] Open the dashboard in a browser and verify Task Center, Evidence, Council, and Publish views render.
