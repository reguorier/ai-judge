---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: c4c8c10647a8bb7136ce0aa675915c5d_ca4d0fef5fd211f191f65254006c9bbf
    ReservedCode1: 13EBPs8LbBx66+U9DlhW9WaoInroap+gfU+NUz5DBmIc5tLGHI1i0J0U/3yfQQk+GecDt7T7wXVpqUsEpDaBBQcCnBZvfHz+6AJrNfnAiN7ng/EqAZVPlm+VtJcpmwW0ROap/Ju8UcUBQGaZx018AJEYJueBnx5hLwWIKqBjv2qgZY8izn7lmGFCHac=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: c4c8c10647a8bb7136ce0aa675915c5d_ca4d0fef5fd211f191f65254006c9bbf
    ReservedCode2: 13EBPs8LbBx66+U9DlhW9WaoInroap+gfU+NUz5DBmIc5tLGHI1i0J0U/3yfQQk+GecDt7T7wXVpqUsEpDaBBQcCnBZvfHz+6AJrNfnAiN7ng/EqAZVPlm+VtJcpmwW0ROap/Ju8UcUBQGaZx018AJEYJueBnx5hLwWIKqBjv2qgZY8izn7lmGFCHac=
---

# P10 Scope Definition

**Generated**: 2026-06-04T05:03:22Z
**Build ID**: p8.7-drift-sentinel-e2e-v1

## Selected Scope

- **P10-A**: Maintenance Center interactive experience enhancement
- **P10-B**: Operator Guide embedded in Dashboard

## Goals

- Make Maintenance Center more usable with progress feedback and action grouping
- Embed key Operator Guide content directly in the Dashboard UI
- Do NOT change underlying AI Judge verdict logic, calibration, or schema

## Non-Scope

- P10-C (Export delivery package)
- P10-D (Trust Calibration explanation view — requires core logic change)
- P10-E (Gavel/Claim batch review UX — requires core logic change)
- P10-F (Run Universe gaps repair assistant)
- P10-G (Electron click-layer stability — high risk)
- AI Judge verdict logic
- Hermes/Gavel/Claim/Trust schema
- New core API beyond thin doc-reading wrappers
- BUILD_ID change (deferred to post-P10.2 process)

## Affected Files

- dashboard.js
- dashboard.html

## Affected APIs

None (or thin read-only doc wrappers only).

## Scope Decision

**APPROVED** — risk_level=low, no schema change, no core logic change.
*（内容由AI生成，仅供参考）*
