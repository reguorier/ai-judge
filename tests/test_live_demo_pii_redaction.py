"""
Tests for live demo PII redaction — public-demo-live-dry-run-v1
"""
import os
import sys
import pytest

SECURITY_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
)
sys.path.insert(0, SECURITY_DIR)

from pii_redactor import PIIRedactor, get_pii_redactor


class TestLiveDemoPIIRedaction:
    """Test PII redactor meets live demo requirements."""

    def test_redact_phone_number(self):
        """Phone numbers must be redacted."""
        redactor = PIIRedactor()
        result = redactor.redact("请联系我 13812345678 谢谢")
        assert "13812345678" not in result.redacted_text
        assert "[PHONE_REDACTED]" in result.redacted_text
        assert "phone" in result.detected_types
        assert result.has_pii is True

    def test_redact_id_card(self):
        """Chinese ID card numbers must be redacted."""
        redactor = PIIRedactor()
        # Valid format: area(6) + birth(8) + seq(3) + check(1)
        result = redactor.redact("身份证号 110101199003071234")
        assert "110101199003071234" not in result.redacted_text
        assert "[ID_CARD_REDACTED]" in result.redacted_text
        assert "id_card" in result.detected_types

    def test_redact_email(self):
        """Email addresses must be redacted."""
        redactor = PIIRedactor()
        result = redactor.redact("发送到 user@example.com 即可")
        assert "user@example.com" not in result.redacted_text
        assert "[EMAIL_REDACTED]" in result.redacted_text
        assert "email" in result.detected_types

    def test_redact_multiple_pii_types(self):
        """Multiple PII types must all be redacted."""
        redactor = PIIRedactor()
        text = "手机13800001111 邮箱test@test.com 身份证320102198506152345"
        result = redactor.redact(text)
        assert "[PHONE_REDACTED]" in result.redacted_text
        assert "[EMAIL_REDACTED]" in result.redacted_text
        assert "[ID_CARD_REDACTED]" in result.redacted_text
        assert result.redaction_count >= 3

    def test_clean_text_unchanged(self):
        """Clean text without PII must remain unchanged."""
        redactor = PIIRedactor()
        text = "这是一段没有敏感信息的普通问题描述"
        result = redactor.redact(text)
        assert result.redacted_text == text
        assert result.has_pii is False

    def test_singleton_returns_same_instance(self):
        """get_pii_redactor must return singleton."""
        r1 = get_pii_redactor()
        r2 = get_pii_redactor()
        assert r1 is r2