"""
Tests for live demo rate limit — public-demo-live-dry-run-v1
"""
import os
import sys
import pytest

# Add security module to path
SECURITY_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/security"
)
sys.path.insert(0, SECURITY_DIR)

from rate_limiter import RateLimiter, RateLimitDecision, get_demo_rate_limiter


class TestLiveDemoRateLimit:
    """Test rate limiter meets live demo requirements."""

    def test_allow_first_request(self):
        """First request must be allowed."""
        limiter = RateLimiter(ip_hourly_limit=5, session_daily_limit=10)
        decision = limiter.allow_request("192.168.1.1", "session-001")
        assert decision.allowed is True
        assert decision.remaining >= 0
        assert decision.reason is None

    def test_block_after_ip_limit_exceeded(self):
        """After IP hourly limit, requests must be blocked."""
        limiter = RateLimiter(ip_hourly_limit=3, session_daily_limit=100)
        ip = "10.0.0.1"

        # Allow 3 requests
        for _ in range(3):
            decision = limiter.allow_request(ip, f"session-{_}")
            assert decision.allowed is True

        # 4th must be blocked
        decision = limiter.allow_request(ip, "session-over")
        assert decision.allowed is False
        assert decision.reason == "rate_limit_exceeded"
        assert decision.retry_after_seconds is not None

    def test_block_after_session_daily_limit(self):
        """After session daily limit, requests must be blocked."""
        limiter = RateLimiter(ip_hourly_limit=100, session_daily_limit=3)
        session = "heavy-user-session"

        # Allow 3 requests
        for _ in range(3):
            decision = limiter.allow_request(f"ip-{_}", session)
            assert decision.allowed is True

        # 4th must be blocked
        decision = limiter.allow_request("ip-extra", session)
        assert decision.allowed is False
        assert decision.reason == "rate_limit_exceeded"

    def test_different_ips_independent(self):
        """Different IPs must have independent limits."""
        limiter = RateLimiter(ip_hourly_limit=2, session_daily_limit=100)

        # Exhaust IP 1
        limiter.allow_request("10.0.0.1", "s1")
        limiter.allow_request("10.0.0.1", "s2")

        # IP 2 should still be allowed
        decision = limiter.allow_request("10.0.0.2", "s3")
        assert decision.allowed is True

    def test_singleton_returns_same_instance(self):
        """get_demo_rate_limiter must return singleton."""
        rl1 = get_demo_rate_limiter()
        rl2 = get_demo_rate_limiter()
        assert rl1 is rl2