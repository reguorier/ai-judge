# OpenRouter BYOK Integration

AI Judge can use OpenRouter as the model access layer for FDJP semantic audit while keeping the evidence audit local-first and source-isolated. OpenRouter collects or synthesizes model reasoning; AI Judge keeps the raw model output, independent evidence, citation/claim-support checks, dissent, and final HTML/JSON report separate.

This path is optional. The default citation-audit demos still run without any model API key.

## What This Enables

- Bring your own OpenRouter API key through `OPENROUTER_API_KEY`.
- Use any OpenRouter chat-completions model by setting `OPENROUTER_MODEL`.
- Route the same provider through AI Judge's FDJP hybrid audit mode.
- Add OpenRouter app attribution headers (`HTTP-Referer`, `X-Title`) without logging the API key.
- Explicitly test OpenRouter Fusion by setting `OPENROUTER_MODEL=openrouter/fusion`.

References:

- OpenRouter quickstart and API docs: <https://openrouter.ai/docs>
- OpenRouter app attribution headers: <https://openrouter.ai/docs/features/app-attribution>
- Works With OpenRouter submission guide: <https://openrouter.ai/docs/guides/community/awesome-openrouter>

## Configuration

Basic OpenRouter route:

```bash
# Set OPENROUTER_API_KEY in your local shell or secret manager before running.
export FDJP_PROVIDER_ENABLE_REAL=1
export OPENROUTER_MODEL="~openai/gpt-latest"
```

OpenRouter endpoint defaults to:

```bash
https://openrouter.ai/api/v1
```

Override it only for testing:

```bash
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
```

Attribution defaults:

```bash
export OPENROUTER_HTTP_REFERER="https://github.com/reguorier/ai-judge"
export OPENROUTER_APP_TITLE="AI Judge"
export OPENROUTER_APP_CATEGORIES="cli-agent"
```

Generic `FDJP_PROVIDER_*` variables still take precedence. This keeps existing OpenAI-compatible deployments unchanged.

## Fusion Mode

OpenRouter Fusion can be tested explicitly:

```bash
# Set OPENROUTER_API_KEY in your local shell or secret manager before running.
export FDJP_PROVIDER_ENABLE_REAL=1
export OPENROUTER_MODEL="openrouter/fusion"
export OPENROUTER_FORCE_FUSION=1
```

`OPENROUTER_FORCE_FUSION=1` adds:

```json
{"tool_choice": "required"}
```

This is intentionally not the default because Fusion can be more expensive than a single routed model.

## Smoke Test

Run a provider-only check:

```bash
PYTHONPATH=. python - <<'PY'
from product.fdjp.provider import create_provider

provider = create_provider("real")
print("available:", provider.is_available())
print(provider.audit('Return exactly this JSON: {"ok": true}', timeout=30))
PY
```

Run a local report plus OpenRouter-backed FDJP audit:

```bash
PYTHONPATH=. python - <<'PY'
from product.run_orchestrator import create_client_run
from product.fdjp.service import run_dimension_audit

run = create_client_run(
    question="A model claims a real source proves a stronger causal conclusion than the source states. What should the audit flag?",
    mode="deep_judge",
    total_seats=3,
    search_agent_output={
        "result": "The isolated source reports association only; it does not establish causation."
    },
)
audit = run_dimension_audit(
    run_id=run["run_id"],
    audit_mode="hybrid",
    provider_kind="real",
    force=True,
)
print("run_id:", run["run_id"])
print("audit_mode:", audit.get("audit_mode"))
print("effective_mode:", audit.get("effective_mode"))
print("artifact_dir:", audit.get("artifact_dir"))
PY
```

The provider metadata written under `fdjp/provider_metadata.json` is safe to publish: it includes model, hashed base URL, latency, retry count, and fallback status, but not the API key.

## Works With OpenRouter Readiness

Current status:

| Requirement | Status |
|---|---|
| Uses OpenRouter for AI model access | Supported through `OPENROUTER_API_KEY` and OpenRouter's OpenAI-compatible chat endpoint |
| Allows BYOK | Supported through environment variables |
| Private docs | This guide lives in the private source repository |
| Public app/project URL | Pending public landing page; source remains closed-core |
| Logo asset | Protected-core hero asset available under `assets/ai-judge-protected-core-hero.png` |
| OpenRouter-backed public demo report | Pending |
| Traction/notability evidence | Pending, tracked in launch and benchmark follow-up notes |

Do not submit the external `OpenRouterTeam/awesome-openrouter` PR until the pending items are complete. The current best next step is to generate one public-safe OpenRouter-backed audit report and a public landing page that explains the product without exposing core implementation.
