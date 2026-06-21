"""FDJP LLM provider abstraction layer.

Provides a lightweight provider interface that does not bind to a single
vendor.  Includes StubProvider (returns mock LLM JSON for testing) and
NullProvider (simulates provider unavailability).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FDJPAuditProvider(ABC):
    """Abstract provider for FDJP LLM semantic audit."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is ready to accept audit requests."""
        ...

    @abstractmethod
    def audit(self, prompt: str, *, timeout: int = 45) -> str:
        """Send prompt to the LLM and return the raw response string.

        Args:
            prompt: Full audit prompt text.
            timeout: Maximum seconds to wait for a response.

        Returns:
            Raw LLM response string (expected to be JSON or JSON in
            markdown fence).
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class StubProvider(FDJPAuditProvider):
    """Returns a hard-coded valid FDJP LLM JSON response for testing."""

    def __init__(self, response_json: str | None = None):
        self._response = response_json or _DEFAULT_STUB_RESPONSE

    def is_available(self) -> bool:
        return True

    def audit(self, prompt: str, *, timeout: int = 45) -> str:
        return self._response

    def set_response(self, response_json: str) -> None:
        self._response = response_json


class NullProvider(FDJPAuditProvider):
    """Simulates an unavailable provider (always returns is_available=False)."""

    def is_available(self) -> bool:
        return False

    def audit(self, prompt: str, *, timeout: int = 45) -> str:
        raise RuntimeError("NullProvider is never available for audit")


# ── Default stub response ──────────────────────────────────────────────

_DEFAULT_STUB_RESPONSE = """{
  "schema_version": "fdjp_llm_audit_v1",
  "dimensions": {
    "philosophy": {
      "status": "pass",
      "claim": "该问题本质上是法律解释冲突，判断标准应基于司法解释层级与立法原意",
      "confidence": 0.92,
      "evidence_refs": ["verdict.conclusion", "seat.deepseek", "seat.gpt"],
      "reasoning_summary": "多个席位识别出规则冲突，主审已给出法律层级分析框架",
      "risk_if_wrong": "若本质判断错误，可能适用错误的法律依据导致结论完全相反",
      "action_impact": "建议以最高法司法解释为最终判断标准",
      "blocker_id": null,
      "warning_id": null
    },
    "economy": {
      "status": "pass",
      "claim": "利益方涵盖债权人、债务人、管理人三方，已识别清偿顺序和优先权",
      "confidence": 0.88,
      "evidence_refs": ["seat.deepseek", "seat.gemini"],
      "reasoning_summary": "多席分析了清偿顺序和优先权，识别了小额债权人的保护需求",
      "risk_if_wrong": "遗漏关键利益方可能导致清偿方案被异议",
      "action_impact": "优先保护小额债权人，兼顾职工债权",
      "blocker_id": null,
      "warning_id": null
    },
    "politics": {
      "status": "pass",
      "claim": "权力结构清晰：法院终局裁定，管理人执管，债权人会议表决",
      "confidence": 0.85,
      "evidence_refs": ["verdict.conclusion", "seat.qwen"],
      "reasoning_summary": "各席一致认定法院为终局裁定者，管理人拥有日常执管权",
      "risk_if_wrong": "误判权力归属可能导致诉求渠道错误",
      "action_impact": "关注法院态度变化，及时与管理人沟通",
      "blocker_id": null,
      "warning_id": null
    },
    "military": {
      "status": "pass",
      "claim": "行动方案可执行，已识别财产保全作为主攻方向",
      "confidence": 0.90,
      "evidence_refs": ["seat.claude", "seat.deepseek"],
      "reasoning_summary": "多席给出了明确的行动路径和风险预案",
      "risk_if_wrong": "行动顺序错误可能错失保全时机",
      "action_impact": "立即提交财产保全申请，同步准备诉讼材料",
      "blocker_id": null,
      "warning_id": null
    },
    "history": {
      "status": "pass",
      "claim": "参考了类案判决趋势和最高法指导案例，时间线完整",
      "confidence": 0.86,
      "evidence_refs": ["verdict.inferences", "seat.gpt"],
      "reasoning_summary": "已识别类案趋势和法条时效，未发现错误类比风险",
      "risk_if_wrong": "法院观点变化可能影响预期结果",
      "action_impact": "关注最高法最新判例，更新类案检索",
      "blocker_id": null,
      "warning_id": null
    }
  },
  "insights": [
    {
      "type": "structural",
      "target": "topic_1",
      "placement": "after_conclusion",
      "text": "本案核心是清偿顺序的司法解释适用问题，而非一般民事纠纷",
      "weight": 0.90,
      "source": "llm"
    }
  ]
}"""


def create_provider(provider_type: str = "stub", **kwargs: Any) -> FDJPAuditProvider:
    """Factory for creating FDJP audit providers.

    Args:
        provider_type: One of 'stub', 'null', 'real', or a fully-qualified class path.
        **kwargs: Passed to the provider constructor.

    Returns:
        A configured FDJPAuditProvider instance.
    """
    if provider_type == "stub":
        return StubProvider(**kwargs)
    if provider_type == "null":
        return NullProvider(**kwargs)
    if provider_type == "real":
        from product.fdjp.real_provider import FDJPRealProvider
        return FDJPRealProvider(**kwargs)

    # Support dynamic import for future real providers
    raise ValueError(f"Unknown provider_type: {provider_type}")