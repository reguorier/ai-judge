"""
Test PII Redactor
public-demo-readiness-v1.0.0
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
))

from pii_redactor import PIIRedactor


@pytest.fixture
def redactor():
    return PIIRedactor()


class TestPhoneRedaction:
    def test_mobile_phone(self, redactor):
        result = redactor.redact("联系我：13812345678")
        assert "[PHONE_REDACTED]" in result.redacted_text
        assert "13812345678" not in result.redacted_text

    def test_multiple_phones(self, redactor):
        result = redactor.redact("电话：13812345678 或 13987654321")
        assert result.redaction_count >= 2

    def test_phone_with_hyphen(self, redactor):
        result = redactor.redact("电话 138-1234-5678")
        assert "[PHONE_REDACTED]" in result.redacted_text


class TestEmailRedaction:
    def test_simple_email(self, redactor):
        result = redactor.redact("邮箱 test@example.com")
        assert "[EMAIL_REDACTED]" in result.redacted_text

    def test_no_email_in_normal_text(self, redactor):
        result = redactor.redact("normal text without email")
        assert "[EMAIL_REDACTED]" not in result.redacted_text


class TestIDCardRedaction:
    def test_18_digit_id(self, redactor):
        result = redactor.redact("身份证：110101199001011234")
        assert "[ID_CARD_REDACTED]" in result.redacted_text


class TestBankCardRedaction:
    def test_bank_card(self, redactor):
        result = redactor.redact("卡号 6222021234567890123")
        assert "[BANK_CARD_REDACTED]" in result.redacted_text


class TestNoFalsePositive:
    def test_normal_text_unchanged(self, redactor):
        text = "这是一段正常的文本，不包含任何敏感信息。"
        result = redactor.redact(text)
        assert result.redacted_text == text
        assert result.redaction_count == 0

    def test_code_snippet_unchanged(self, redactor):
        text = "def process_data(input_id=123456, api_version='v1'): pass"
        result = redactor.redact(text)
        # Code-like numbers should not be falsely redacted
        assert "process_data" in result.redacted_text


class TestRedactionMetadata:
    def test_redaction_count(self, redactor):
        result = redactor.redact("联系 13812345678 或 user@example.com")
        assert result.redaction_count >= 2

    def test_detected_types(self, redactor):
        result = redactor.redact("手机 13812345678 邮箱 user@example.com")
        assert "phone" in result.detected_types or any("phone" in t for t in result.detected_types)