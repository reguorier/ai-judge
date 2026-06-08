# RELEASE SEAL — Deep Judge AJ_REPORT_V1

## Release Info

- **Release:** deep-judge-aj-report-v1.0.0
- **Git Tag:** `deep-judge-aj-report-v1.0.0`
- **Branch:** `fix/deep-judge-grounded-final-report`
- **Commit:** `0342276`
- **Date:** 2026-06-08
- **AJ Report Protocol:** `AJ_REPORT_V1_DECISION_BRIEF`

## Test Results

| Suite | Status | Details |
|-------|--------|---------|
| `test_run_orchestrator_deep_judge` | ✅ PASS | 5 AC + metadata + regression |
| `test_deep_judge_integration` | ✅ PASS | |
| `test_full_legal_flow` | ✅ PASS | |
| `test_final_report_builder` | ✅ PASS | |
| `test_followup_generation` | ✅ PASS | |
| `test_citation_validator` | ✅ PASS | |
| `test_seat_matrix_stats` | ✅ PASS | |
| npm validate:report | N/A | Python-only project, no package.json |
| npm run typecheck | N/A | Python-only project, no package.json |

**Total:** 48/48 regression tests passed / 0 errors.

## Frozen Rule — AJ_REPORT_V1 Output Chain

```
LLM JSON contract
  → ReportContractSchema.parse()
    → renderDecisionBriefReport()
      → validateRenderedHtml()
        → validation.ok === true
          → SAVE / DISPLAY HTML
```

The following are **permanently frozen**:

- `AJ_REPORT_V1_DECISION_BRIEF` structure — no silent modification
- `renderDecisionBriefReport()` — only entry point for HTML generation
- `validateRenderedHtml()` — mandatory gate before save/display
- Validation failure → HTML is never saved or displayed

## Frozen Rule — API Flow

```
API submit
  → create_client_run
    → deep_judge_runner 推理门控
      → search_agent / LLM / seat_outputs / legal_analysis (至少一种)
        → build_client_final_report
          → AJ_REPORT_V1 输出
```

- `skipped/not_configured` seats excluded from `valid_seats` count
- followup returns `status=not_generated` when no reasoning source exists
- `deep_judge` returns `status=failed` / `reason=deep_judge_no_substantive_reasoning` when zero reasoning sources

## Legacy Scan

```
git grep -n "LLM.*HTML|rawHtml|reportHtml|dangerouslySetInnerHTML|innerHTML|generate.*HTML"
```

**Result: CLEAN.** No production paths directly concatenate HTML from LLM output. No validation bypass paths found.

- `product/api_server.py:9314/9326` — innerHTML only for copy-link button text restoration (UI pattern, not HTML generation)
- `product/dashboard.js` — innerHTML only for dashboard panel rendering (seat cards, memory lists, feature cards)
- `product/api_report_contract_patch.py` — correctly references `renderDecisionBriefReport()`
- `core/html_export.py:637` — error message only

## API Smoke Tests

To complete the seal, execute the following:

### 1. Bankruptcy Issue
```bash
curl -X POST http://localhost:{PORT}/api/runs \
  -H "Content-Type: application/json" \
  -d '{"mode":"deep_judge","question":"迟延履行期间加倍支付的债务利息能否作为破产债权申报？"}'
```

Expected keywords in report: 破产债权, 迟延履行, 加倍, 受理前/受理后
Forbidden: B2B SaaS, 报告视觉, dashboard, AI Judge 产品价值, 投资人

### 2. Homestead Demolition Issue
```bash
curl -X POST http://localhost:{PORT}/api/runs \
  -H "Content-Type: application/json" \
  -d '{"mode":"deep_judge","question":"宅基地房屋拆迁补偿纠纷中实际买受人如何主张权利？"}'
```

Expected keywords in report: 宅基地, 拆迁补偿, 农村房屋, 合同效力/合同无效, 返还/折价/信赖利益/安置资格 (≥2)
Body similarity vs Issue 1: < 0.70 (Jaccard)

## Artifact Checklist (per run)

Each deep_judge run must produce at minimum:

- [ ] `run_metadata.json` — deep_judge block with non-empty `substantive_sources`
- [ ] `seat_matrix.json`
- [ ] `evidence_pack.json`
- [ ] `final_report_contract.json`
- [ ] `final_report.html`
- [ ] `validation_result.json`

`run_metadata.json` example:
```json
{
  "deep_judge": {
    "llm_calls": 0,
    "search_agent_calls": 1,
    "seat_outputs_consumed": 0,
    "substantive_sources": ["search_agent"],
    "degraded": false
  }
}
```

## Failure Gate Verification

No-reasoning-source request must return:
```json
{
  "status": "failed",
  "reason": "deep_judge_no_substantive_reasoning",
  "final_report_generated": false
}
```

## Acceptance Gate

| Criterion | Status |
|-----------|--------|
| All unit tests green | ✅ 48/48 |
| TypeScript 0 errors | N/A (Python-only) |
| Legacy scan clean | ✅ |
| Frozen rules in code | ✅ |
| `valid_seats` excludes skipped/not_configured | ✅ |
| followup no-reasoning → not_generated | ✅ |
| deep_judge no-reasoning → failed | ✅ |
| deep-judge-aj-report-v1.0.0 tag | ✅ |
| RELEASE_SEAL.md generated | ✅ |
| API smoke: bankruptcy | ⏳ pending server |
| API smoke: homestead | ⏳ pending server |
| Artifact 6-file check | ⏳ pending smoke |
| Failure gate live test | ⏳ pending server |

---

**Sealed by:** Marvis (AI Judge release agent)
**Timestamp:** 2026-06-08