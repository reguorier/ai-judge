import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product.fdjp.provider_config import FDJPProviderConfig, reset_provider_config
from product.fdjp.real_provider import FDJPRealProvider, reset_circuit_breaker


def _clear_provider_env(monkeypatch):
    for key in (
        "FDJP_PROVIDER_KIND",
        "FDJP_PROVIDER_BASE_URL",
        "FDJP_PROVIDER_API_KEY",
        "FDJP_PROVIDER_MODEL",
        "FDJP_PROVIDER_TIMEOUT_S",
        "FDJP_PROVIDER_MAX_RETRIES",
        "FDJP_PROVIDER_MAX_TOKENS",
        "FDJP_PROVIDER_TEMPERATURE",
        "FDJP_PROVIDER_ENABLE_REAL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
        "OPENROUTER_MODEL",
        "OPENROUTER_HTTP_REFERER",
        "OPENROUTER_APP_TITLE",
        "OPENROUTER_APP_CATEGORIES",
        "OPENROUTER_FORCE_FUSION",
    ):
        monkeypatch.delenv(key, raising=False)
    reset_provider_config()
    reset_circuit_breaker()


def test_openrouter_api_key_enables_openrouter_defaults(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    cfg = FDJPProviderConfig()

    assert cfg.kind == "openrouter"
    assert cfg.base_url == "https://openrouter.ai/api/v1"
    assert cfg.api_key == "sk-or-test"
    assert cfg.model == "~openai/gpt-latest"
    assert cfg.is_openrouter()
    assert cfg.safe_metadata()["provider_kind"] == "openrouter"
    assert cfg.safe_metadata()["openrouter_attribution_enabled"] is True


def test_fdjp_provider_env_still_overrides_openrouter_aliases(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("FDJP_PROVIDER_KIND", "openai_compatible")
    monkeypatch.setenv("FDJP_PROVIDER_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("FDJP_PROVIDER_API_KEY", "sk-generic")
    monkeypatch.setenv("FDJP_PROVIDER_MODEL", "generic-model")

    cfg = FDJPProviderConfig()

    assert cfg.kind == "openai_compatible"
    assert cfg.base_url == "https://example.invalid/v1"
    assert cfg.api_key == "sk-generic"
    assert cfg.model == "generic-model"
    assert not cfg.is_openrouter()


class _FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": "{\"ok\": true}"}}]}
        ).encode("utf-8")


def test_openrouter_request_includes_attribution_headers_and_force_fusion(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/fusion")
    monkeypatch.setenv("OPENROUTER_FORCE_FUSION", "1")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://github.com/reguorier/ai-judge")
    monkeypatch.setenv("OPENROUTER_APP_TITLE", "AI Judge")
    monkeypatch.setenv("OPENROUTER_APP_CATEGORIES", "cli-agent")
    monkeypatch.setenv("FDJP_PROVIDER_ENABLE_REAL", "1")

    captured = {}

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    provider = FDJPRealProvider(FDJPProviderConfig())
    assert provider.audit("Return JSON.", timeout=5) == "{\"ok\": true}"

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer sk-or-test"
    assert captured["headers"]["http-referer"] == "https://github.com/reguorier/ai-judge"
    assert captured["headers"]["x-title"] == "AI Judge"
    assert captured["headers"]["x-openrouter-categories"] == "cli-agent"
    assert captured["payload"]["model"] == "openrouter/fusion"
    assert captured["payload"]["tool_choice"] == "required"


def test_non_openrouter_request_does_not_send_openrouter_headers(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("FDJP_PROVIDER_ENABLE_REAL", "1")
    monkeypatch.setenv("FDJP_PROVIDER_KIND", "openai_compatible")
    monkeypatch.setenv("FDJP_PROVIDER_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("FDJP_PROVIDER_API_KEY", "sk-generic")
    monkeypatch.setenv("FDJP_PROVIDER_MODEL", "generic-model")

    captured = {}

    def fake_urlopen(req, timeout):
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    provider = FDJPRealProvider(FDJPProviderConfig())
    assert provider.audit("Return JSON.", timeout=5) == "{\"ok\": true}"

    assert "http-referer" not in captured["headers"]
    assert "x-title" not in captured["headers"]
    assert "x-openrouter-categories" not in captured["headers"]
    assert "tool_choice" not in captured["payload"]
