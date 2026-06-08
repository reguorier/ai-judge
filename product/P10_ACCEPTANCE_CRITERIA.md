---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: c4c8c10647a8bb7136ce0aa675915c5d_cb18cd3d5fd211f1a306525400d9a7a1
    ReservedCode1: /NSuTJI0GJfMUyz/4oo3KIwo3EQwcWaG1+wN6MdvE14sKngMyIW2ZVd5LmKUfdD5Imdii3YCti5vYQh6Uc8eY6wcvx35ut6nYKAU3K/eOmwns+SJ2E8NZoDzLiI3P3XTKT/oMM+sjXK8WinngFdydkIoUaDBRLGRCBWKuubpK9uTi0Wl7HXAjeIWdpI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: c4c8c10647a8bb7136ce0aa675915c5d_cb18cd3d5fd211f1a306525400d9a7a1
    ReservedCode2: /NSuTJI0GJfMUyz/4oo3KIwo3EQwcWaG1+wN6MdvE14sKngMyIW2ZVd5LmKUfdD5Imdii3YCti5vYQh6Uc8eY6wcvx35ut6nYKAU3K/eOmwns+SJ2E8NZoDzLiI3P3XTKT/oMM+sjXK8WinngFdydkIoUaDBRLGRCBWKuubpK9uTi0Wl7HXAjeIWdpI=
---

# P10 Acceptance Criteria

**Generated**: 2026-06-04T05:03:22Z
**Build ID**: p8.7-drift-sentinel-e2e-v1

## Functional Criteria

1. Maintenance Center panel still shows all 8 maintenance actions
2. All 8 maintenance actions remain executable and write maintenance_action_clicked/maintenance_action_result trace events
3. Operator Guide panel opens from Dashboard UI
4. Document links/summaries (OPERATOR_GUIDE.md, REGRESSION_CHECKLIST.md) are readable in Dashboard
5. release_readiness = pass (5/5, 0 blockers)
6. freeze drift = generated_only (or strict changes triaged as intentional)
7. no schema changes
8. no runs/vault deletions
9. UI trace events emitted: operator_doc_opened, maintenance_group_toggled

## Regression Criteria

- release_readiness
- freeze_drift_sentinel
- regression
- maintenance_action_trace (all 8 actions)

## Safety Criteria

- No schema changes
- No core logic changes
- No runs/vault deletions
- BUILD_ID unchanged
*（内容由AI生成，仅供参考）*
