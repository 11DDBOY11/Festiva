"""Tests for IP auth rate limiting and daily per-user LLM caps."""

import pytest

from app.core.rate_limit import (
    check_auth_rate_limit,
    check_user_llm_cap,
    reset_rate_limits_for_tests,
)


@pytest.fixture(autouse=True)
def clean_rate_limits():
    reset_rate_limits_for_tests()
    yield
    reset_rate_limits_for_tests()


def test_auth_rate_limiting_exceeded_returns_429():
    """Verify that exceeding AUTH_LIMIT_PER_MINUTE raises HTTP 429."""
    from fastapi import HTTPException
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": [],
        "client": ("192.168.1.100", 12345),
    }
    req = Request(scope)

    # First 15 should pass with limit=15
    for _ in range(15):
        check_auth_rate_limit(req, limit=15, force_check=True)

    # 16th request must raise 429
    with pytest.raises(HTTPException) as exc_info:
        check_auth_rate_limit(req, limit=15, force_check=True)

    assert exc_info.value.status_code == 429
    assert "Too many authentication requests" in exc_info.value.detail


def test_spoofed_x_forwarded_for_cannot_bypass_rate_limit():
    """Verify that an attacker prepending rotating spoofed IPs to X-Forwarded-For

    is still rate-limited based on the last proxy-appended hop (Render reverse proxy).
    """
    from fastapi import HTTPException
    from starlette.requests import Request

    real_proxy_appended_ip = "198.51.100.22"

    # Make 15 requests, each with a different spoofed client IP prepended
    for i in range(15):
        spoofed_header = f"attacker.fake.{i}, 10.0.0.{i}, {real_proxy_appended_ip}"
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": [(b"x-forwarded-for", spoofed_header.encode("latin-1"))],
            "client": ("10.0.0.1", 12345),
        }
        req = Request(scope)
        check_auth_rate_limit(req, limit=15, force_check=True)

    # 16th request with yet another spoofed IP prepended MUST be blocked with 429
    # because the last hop is identical (198.51.100.22)
    with pytest.raises(HTTPException) as exc_info:
        header_val = f"another.fake.ip, {real_proxy_appended_ip}".encode("latin-1")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": [(b"x-forwarded-for", header_val)],
            "client": ("10.0.0.1", 12345),
        }
        req = Request(scope)
        check_auth_rate_limit(req, limit=15, force_check=True)

    assert exc_info.value.status_code == 429
    assert "Too many authentication requests" in exc_info.value.detail


def test_user_llm_daily_cap_enforcement():
    """Verify that user LLM cap allows up to limit and rejects subsequent requests."""
    test_user_id = "user-abc-123"
    cap = 5

    for i in range(cap):
        allowed, count = check_user_llm_cap(test_user_id, cap=cap)
        assert allowed is True
        assert count == i + 1

    # Cap exceeded
    allowed, count = check_user_llm_cap(test_user_id, cap=cap)
    assert allowed is False
    assert count == cap
