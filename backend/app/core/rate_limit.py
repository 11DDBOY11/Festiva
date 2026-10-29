"""Rate limiting and daily LLM quota enforcement."""

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import settings

# 1. IP-based Auth Rate Limiter
AUTH_LIMIT_PER_MINUTE = 15
AUTH_WINDOW_SECONDS = 60

_auth_ip_timestamps: dict[str, list[float]] = defaultdict(list)

# 2. Per-user Daily LLM Request Cap
DAILY_LLM_CAP_DEFAULT = 50

_user_daily_counts: dict[str, int] = defaultdict(int)


def _get_client_ip(request: Request) -> str:
    """Extract client IP respecting X-Forwarded-For when behind proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def check_auth_rate_limit(
    request: Request,
    limit: int = AUTH_LIMIT_PER_MINUTE,
    force_check: bool = False,
) -> None:
    """Enforce IP-based rate limit for authentication endpoints."""
    import os

    if not force_check:
        if "PYTEST_CURRENT_TEST" in os.environ or settings.ENV == "test":
            return

        ip = _get_client_ip(request)
        if ip in ("testclient", "test"):
            return
    else:
        ip = _get_client_ip(request)

    now = time.time()
    cutoff = now - AUTH_WINDOW_SECONDS

    timestamps = [t for t in _auth_ip_timestamps[ip] if t > cutoff]
    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please wait a minute and try again.",
        )
    timestamps.append(now)
    _auth_ip_timestamps[ip] = timestamps


def check_user_llm_cap(user_id: Any, cap: int = DAILY_LLM_CAP_DEFAULT) -> tuple[bool, int]:
    """Check and record user's daily LLM usage.

    Returns:
        (within_cap: bool, current_usage_count: int)
    """
    today_key = datetime.now(UTC).strftime("%Y-%m-%d")
    cache_key = f"{str(user_id)}:{today_key}"
    current = _user_daily_counts[cache_key]

    if current >= cap:
        return False, current

    _user_daily_counts[cache_key] = current + 1
    return True, current + 1


def reset_rate_limits_for_tests() -> None:
    """Helper for unit tests."""
    _auth_ip_timestamps.clear()
    _user_daily_counts.clear()
