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
