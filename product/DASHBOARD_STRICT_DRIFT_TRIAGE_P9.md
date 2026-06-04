# Dashboard Strict Drift Triage — P9.0.1

## Evidence

| Source | SHA256 | BUILD_ID |
|--------|--------|----------|
| PRODUCT | `d726aeb4acc4ed12f5f0bb04717e7bb1c7e6d37ce3b43ab69fb413cbc89e2c5f` | `p8.7-drift-sentinel-e2e-v1` |
| SRC | `780efddd31c83b62709adbf32ad7abe9cb0ea7e6ec64b35b074fa94a7f74927c` | `P2.6-RC1` |
| HTTP (port 8501) | `d726aeb4acc4ed12f5f0bb04717e7bb1c7e6d37ce3b43ab69fb413cbc89e2c5f` | `p8.7-drift-sentinel-e2e-v1` |
| Manifest (expected) | `d726aeb4acc4ed12f5f0bb04717e7bb1c7e6d37ce3b43ab69fb413cbc89e2c5f` | `p8.7-drift-sentinel-e2e-v1` |
| Backup (p8-freeze-20260603_154900) | `d726aeb4acc4ed12f5f0bb04717e7bb1c7e6d37ce3b43ab69fb413cbc89e2c5f` | `p8.7-drift-sentinel-e2e-v1` |

## Diff Summary

- **PRODUCT vs Backup**: no diff (identical files, 0 lines changed)
- **PRODUCT vs SRC**: massive divergence — SRC contains `P2.6-RC1` BUILD_ID vs PRODUCT's `p8.7-drift-sentinel-e2e-v1`. These are fundamentally different codebase versions spanning multiple major release cycles (P2 → P8). Diff not feasible as line-level comparison; entire file is a different version.
- **HTTP vs PRODUCT**: no diff (identical)

## Decision

**source_mismatch_blocked**

## Rationale

1. **PRODUCT / HTTP / Manifest / Backup 四方一致**：运行中的 dashboard.js、HTTP 服务端加载的副本、P8 封板 manifest 记录、以及最近 freeze backup 的 SHA256 完全相同（`d726aeb4`），BUILD_ID 均为 `p8.7-drift-sentinel-e2e-v1`。运行时链路无漂移。

2. **SRC 为完全不同的古旧版本**：`/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js` 的 BUILD_ID 为 `P2.6-RC1`，SHA256 为 `780efddd`，与 P8 基线（`d726aeb4`）无任何关系。这不是 P8 范围内的增量漂移，而是 SRC 目录中的 dashboard.js 被整体替换/回退到了一个跨越 6 个大版本的远古快照。

3. **不符合 intentional_refresh_candidate**：SRC 的 BUILD_ID（P2.6-RC1）比 P8 基线（p8.7）早 6 个 major release，不可能是有意的 P9 前向刷新。

4. **不符合 accidental_revert_required**：PRODUCT 本身未发生回退，运行时状态完好。问题仅限于 SRC 副本与基线不一致，属于源目录对齐问题而非运行时回归。

5. **判定为 source_mismatch_blocked**：SRC 作为源码权威目录，其 dashboard.js 与 PRODUCT/Manifest 基线完全不匹配，必须在对齐源目录之前阻止后续任何依赖 SRC 的操作。

## Recommendation

- **阻断**：在修复 SRC 副本之前，禁止任何依赖 `ai-judge-skill/product/dashboard.js` 的操作（包括 P9.0.2 baseline refresh、manifest 重新生成、SRC→PRODUCT 同步等）。
- **修复方案**：将 PRODUCT（或 backup）中的正确 dashboard.js 覆盖到 SRC 目录：
  ```bash
  cp "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/dashboard.js" \
     "/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js"
  ```
  或从 freeze backup 恢复：
  ```bash
  cp "/Users/audimacmini/Documents/AI-Judge-Freezes/p8-freeze-20260603_154900/product/dashboard.js" \
     "/Users/audimacmini/Documents/ai-judge-skill/product/dashboard.js"
  ```
- **修复后验证**：重新执行 Step 1 hash 收集，确认 SRC hash 变为 `d726aeb4`，BUILD_ID 变为 `p8.7-drift-sentinel-e2e-v1`。
- **修复后**：重新判定 triage，预期变为 `intentional_refresh_candidate`（若 SRC 与 PRODUCT 对齐且无额外漂移）。
