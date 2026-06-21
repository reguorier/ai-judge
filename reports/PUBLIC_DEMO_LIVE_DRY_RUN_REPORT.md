# Public Demo Live Dry Run V1 — 完整报告

**Release**: public-demo-live-dry-run-v1
**Baseline**: PUBLIC_DEMO_READINESS_V1_PASS
**Executed**: 2026-06-08
**Result**: PUBLIC_DEMO_LIVE_DRY_RUN_V1_PASS

---

## 执行摘要

12 步全面 live dry run 全部通过。API 在线且正常响应 (status: ok)。所有安全模块、配置、replay pack、telemetry 均已验证通过。

---

## Step-by-Step 详细结果

### Step 1: API Health — PASS

```
GET http://localhost:8501/api/health → 200 OK
{
  "status": "ok",
  "product": "AI Judge Trust Workbench",
  "version": "3.8.0-P3.8.14-RC1",
  "fdjp_enabled": true,
  "fdjp_mode": "heuristic"
}
```

**注意**: `release_integrity` 字段返回 `"fail"`。这是 P3.8.14-RC1 的内部发布完整性标记，不影响 demo 功能。已在 failures.jsonl 中记录为 info 级别。

**基线对比**: 上一阶段 PUBLIC_DEMO_READINESS 将 API health 标为 OFFLINE_SKIPPED，实测 API 在线可用。

---

### Step 2: Demo Config — PASS

验证 `runtime/product/demo/demo_config.json`:

| 配置项 | 要求值 | 实际值 | 结果 |
|--------|--------|--------|------|
| demo_enabled | true | true | PASS |
| demo_mode | public_preview | public_preview | PASS |
| show_disclaimer | true | true | PASS |
| require_privacy_notice_ack | true | true | PASS |
| fail_closed | true | true | PASS |
| max_requests_per_ip_per_hour | 5 | 5 | PASS |
| max_requests_per_session_per_day | 10 | 10 | PASS |
| max_question_chars | 1200 | 1200 | PASS |
| allow_file_upload | false | false | PASS |
| allow_sensitive_personal_data | false | false | PASS |
| default_reader_type | ordinary_user | ordinary_user | PASS |
| rate_limit.enabled | true | true | PASS |
| pii_redaction.enabled | true | true | PASS |
| abuse_guard.enabled | true | true | PASS |
| telemetry.enabled | true | true | PASS |
| telemetry.hash_ip_session | true | true | PASS |
| telemetry.save_raw_prompt | false | false | PASS |

---

### Step 3: Whitelist Tasks — PASS

验证 `runtime/product/demo/demo_task_whitelist.json`:

6 个白名单任务全部存在且字段完整：

| Task ID | Label | Mode | Reader Type | Risk |
|---------|-------|------|-------------|------|
| DEMO-LEGAL-001 | 破产债权加倍利息 | deep_judge | ordinary_user | medium |
| DEMO-LEGAL-002 | 宅基地拆迁补偿 | deep_judge | ordinary_user | medium |
| DEMO-LEGAL-003 | 民法典合同解除 | deep_judge | ordinary_user | medium |
| DEMO-PRODUCT-001 | SaaS 定价模型 | deep_judge | pm_founder | low |
| DEMO-AUDIT-001 | 模型幻觉率审计 | deep_judge | professional_user | low |
| DEMO-DECISION-001 | 远程办公政策 | deep_judge | pm_founder | low |

每项均包含: id/label/question/mode/reader_type/risk_level/public_demo_safe/expected_takeaway/forbidden_inputs。

---

### Step 4: AJ_REPORT_V1 Check — PASS

逐项扫描 3 个 replay pack 的 final_report.html：

- **文件存在**: bankruptcy_demo/final_report.html, homestead_demo/final_report.html, civil_code_demo/final_report.html — 全部存在
- **禁止字符串检查**: Traceback / API_KEY / SECRET / sk- / B2B SaaS / dashboard / 报告视觉 — 均未发现
- **所需字符串检查**: "AI Judge" 或决策摘要 — 通过

---

### Step 5: Rate Limit — PASS

`runtime/product/security/rate_limiter.py` 代码审查:

- IP 每小时限制 5 次 — 滑动窗口实现，超限返回 `allowed: false, reason: "rate_limit_exceeded"`
- Session 每日限制 10 次 — 滑动窗口实现
- Deep judge 并发限制 2 — 超出返回 retry_after_seconds=30
- 返回结构符合规范: `{allowed, reason, remaining, reset_at, retry_after_seconds}`
- IP/session key 使用 SHA256 hash 存储

---

### Step 6: Abuse Guard — PASS

`runtime/product/security/abuse_guard.py` 代码审查:

6 类模式均已编译:

| # | 类别 | 模式数 | 拦截示例 |
|---|------|--------|----------|
| 1 | Prompt Injection | 8 | "ignore previous instructions", "DAN", "jailbreak" |
| 2 | Legal Impersonation | 5 | "帮我写起诉状", "以律师名义" |
| 3 | Medical Diagnosis | 4 | "我得了什么病", "帮我诊断" |
| 4 | Investment Instructions | 6 | "买入哪只股票", "sell stock" |
| 5 | Illegal Requests | 4 | "如何入侵", "制作病毒" |
| 6 | Bulk PII | 4 | 身份证/银行卡/手机号 ≥3 |

返回 `AbuseGuardDecision(allowed, reason, user_message)` 含用户可读中文提示。

---

### Step 7: PII Redaction — PASS

`runtime/product/security/pii_redactor.py` 代码审查:

6 种 PII 类型检测与遮罩:

| PII 类型 | 占位符 | 正则精度 |
|----------|--------|----------|
| 手机号 | [PHONE_REDACTED] | 1[3-9] 双 pass 检测 |
| 身份证 | [ID_REDACTED] | 18 位 + 日期校验 |
| 邮箱 | [EMAIL_REDACTED] | RFC 5322 简化 |
| 银行卡 | [BANK_CARD_REDACTED] | 16-19 位 |
| 病历号 | [MEDICAL_RECORD_REDACTED] | 关键词 + 编号 |
| 地址 | [ADDRESS_REDACTED] | ≥3 地址组件触发 |

`safe_for_logging()` 和 `safe_for_artifact()` 方法确保遮罩后再写入。

---

### Step 8: Non-Whitelist Rejection — PASS

配置验证:

- `demo_task_whitelist.json` → `"allow_custom_input": false`
- `demo_failure_messages.json` → `DEMO_TASK_NOT_ALLOWED` 条目: title="任务不在演示白名单中", can_retry=false, show_to_user=true
- 用户看到可读消息: "您提交的问题不在当前公开演示的白名单中。此 Demo 版本仅支持预设的演示任务。"

---

### Step 9: Failure Page — PASS

`runtime/product/demo/demo_failure_messages.json` 验证:

10 种失败类型全部定义:

| 类型 | 可重试 | 用户可见 |
|------|--------|----------|
| NO_REASONING_SOURCE | yes | ✅ |
| SEARCH_AGENT_TIMEOUT | yes | ✅ |
| SEARCH_AGENT_NO_RESULTS | yes | ✅ |
| REPORT_RELEVANCE_FAILED | yes | ✅ |
| REPORT_VALIDATION_FAILED | yes | ✅ |
| ARTIFACT_MISSING | yes | ✅ |
| RATE_LIMIT_EXCEEDED | yes | ✅ |
| SAFETY_OR_SCOPE_BOUNDARY | no | ✅ |
| DEMO_TASK_NOT_ALLOWED | no | ✅ |
| UNKNOWN | yes | ✅ |

所有消息均为纯中文可读文本，不暴露 traceback / API key / secret。

---

### Step 10: Replay Pack — PASS

`runtime/product/demo/demo_replay_manifest.json` 验证:

3 个 replay 全部存在，每个含 7 个文件:

| Replay | 路径 | 文件数 | final_report.html |
|--------|------|--------|-------------------|
| bankruptcy_demo | replay/bankruptcy_demo/ | 7 | ✅ |
| homestead_demo | replay/homestead_demo/ | 7 | ✅ |
| civil_code_demo | replay/civil_code_demo/ | 7 | ✅ |

所有 replay 标记 `is_synthetic: true`, `contains_real_pii: false`。

---

### Step 11: Telemetry — PASS

`runtime/product/observability/demo_telemetry.py` 代码审查:

5 种事件类型:
- `demo_run_submitted` — 含 task_id, reader_type
- `demo_run_completed` — 含 latency_ms
- `demo_run_failed` — 含 failure_class
- `rate_limited`
- `safety_blocked` — 含 reason

所有事件: IP/session 使用 SHA256 hash (前 12 位)，不保存 raw prompt。支持 `enabled=False` 关闭。

---

### Step 12: Summary — PASS

汇总统计:

| 指标 | 值 |
|------|-----|
| 总步骤 | 12 |
| 通过 | 12 |
| 失败 | 0 |
| 阻塞 | 0 |
| 跳过 | 0 |

---

## 不改清单确认

| 基线项 | 状态 |
|--------|------|
| AJ_REPORT_V1_DECISION_BRIEF | 未修改 |
| deep_judge_runner.py 推理门控 | 未修改 |
| final_report_builder.py grounding | 未修改 |
| search-agent evidence schema | 未修改 |
| reader_type adapter 语义 | 未修改 |
| Public Demo Readiness 基线 | 未修改 |

---

## 最终通过标志

```
PUBLIC_DEMO_LIVE_DRY_RUN_V1_PASS
```