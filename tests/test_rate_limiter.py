"""
Test Rate Limiter
public-demo-readiness-v1.0.0
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
))

from rate_limiter import RateLimiter, RateLimitDecision


@pytest.fixture
def limiter():
    return RateLimiter(ip_hourly_limit=5, session_daily_limit=10)


class TestRateLimiter:
    """Core rate limiting behavior."""

    def test_initial_request_allowed(self, limiter):
        d = limiter.allow_request("192.168.1.1", "session_a", "deep_judge")
        assert d.allowed is True
        assert d.remaining == 4
        assert d.reason is None

    def test_ip_limit_enforced(self, limiter):
        ip = "10.0.0.1"
        for i in range(5):
            d = limiter.allow_request(ip, f"sess_{i}", "deep_judge")
            assert d.allowed, f"Request {i+1} should be allowed"
        # 6th request blocked
        d = limiter.allow_request(ip, "sess_6", "deep_judge")
        assert d.allowed is False
        assert d.reason == "rate_limit_exceeded"
        assert d.retry_after_seconds is not None
        assert d.retry_after_seconds > 0

    def test_session_daily_limit(self, limiter):
        session = "heavy_session"
        for i in range(10):
            d = limiter.allow_request(f"10.0.{i}.1", session, "deep_judge")
            assert d.allowed, f"Session request {i+1} should be allowed"
        d = limiter.allow_request("10.0.99.1", session, "deep_judge")
        assert d.allowed is False

    def test_different_ips_independent(self, limiter):
        for i in range(5):
            d = limiter.allow_request(f"172.16.0.{i}", f"sess_{i}", "deep_judge")
            assert d.allowed

    def test_reset_field_present(self, limiter):
        d = limiter.allow_request("10.0.0.1", "sess", "deep_judge")
        assert d.reset_at is not None

    def test_remaining_decrements(self, limiter):
        ip = "10.0.0.50"
        d1 = limiter.allow_request(ip, "s1", "deep_judge")
        assert d1.remaining == 4
        d2 = limiter.allow_request(ip, "s2", "deep_judge")
        assert d2.remaining == 3