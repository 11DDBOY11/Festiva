"""Rate limiting and daily LLM quota enforcement."""

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger("festiva.rate_limit")

# 1. IP-based Auth Rate Limiter
AUTH_LIMIT_PER_MINUTE = 30
AUTH_WINDOW_SECONDS = 60

# 2. Account Lockout / Progressive Delay per Email/IP
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes lockout after 5 consecutive failures

_auth_ip_timestamps: dict[str, list[float]] = defaultdict(list)
_auth_failed_attempts: dict[str, list[float]] = defaultdict(list)

# Logging rate limiter for IP resolution
_auth_log_count: int = 0
_last_auth_log_time: float = 0.0

# 3. Per-user Daily LLM Request Cap
DAILY_LLM_CAP_DEFAULT = 50

_user_daily_counts: dict[str, int] = defaultdict(int)


def _mask_ip(ip: str) -> str:
    """Mask the last octet or segment of an IP address for security & privacy."""
    if not ip:
        return "unknown"
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    elif ":" in ip:
        parts = ip.split(":")
        if len(parts) > 1:
            return ":".join(parts[:-1] + ["xxxx"])
    return f"{ip[:4]}...xxx"


def _maybe_log_ip_resolution(num_entries: int, resolved_ip: str, trusted_hops: int) -> None:
    """Log IP resolution: first 5 auth requests, then at most once per minute.

    Masks the last octet; never logs full IPs or tokens.
    """
    global _auth_log_count, _last_auth_log_time
    now = time.time()
    should_log = False
    if _auth_log_count < 5:
        should_log = True
        _auth_log_count += 1
    elif (now - _last_auth_log_time) >= 60.0:
        should_log = True

    if should_log:
        _last_auth_log_time = now
        masked = _mask_ip(resolved_ip)
        logger.info(
            "Auth IP resolution: x_forwarded_for_entries=%d resolved_ip=%s (trusted_hops=%d)",
            num_entries,
            masked,
            trusted_hops,
        )


def _get_client_ip(request: Request, trusted_hops: int | None = None) -> str:
    """Extract client IP taking the Nth entry from the right of X-Forwarded-For.

    N = TRUSTED_PROXY_HOPS (default 1).
    Render (and standard reverse proxies) appends the connecting client's IP to the
    end of the X-Forwarded-For header. If there are fewer entries than N, falls back
    to request.client.host.
    """
    n = trusted_hops if trusted_hops is not None else getattr(settings, "TRUSTED_PROXY_HOPS", 1)
    if n < 1:
        n = 1

    forwarded = request.headers.get("x-forwarded-for")
    num_entries = 0
    resolved_ip = None

    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        num_entries = len(parts)
        if len(parts) >= n:
            resolved_ip = parts[-n]

    if not resolved_ip:
        if request.client and request.client.host:
            resolved_ip = request.client.host
        else:
            resolved_ip = "127.0.0.1"

    _maybe_log_ip_resolution(num_entries, resolved_ip, n)
    return resolved_ip


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


def check_account_lockout(email: str, force_check: bool = False) -> None:
    """Check if account is temporarily locked out due to repeated failed logins."""
    import os

    if not force_check:
        if "PYTEST_CURRENT_TEST" in os.environ or settings.ENV == "test":
            return

    key = email.strip().lower()
    now = time.time()
    cutoff = now - LOCKOUT_WINDOW_SECONDS

    recent_fails = [t for t in _auth_failed_attempts[key] if t > cutoff]
    _auth_failed_attempts[key] = recent_fails

    if len(recent_fails) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Account temporarily locked due to multiple failed login attempts. "
                "Please try again in 5 minutes."
            ),
        )


def record_failed_login(email: str) -> None:
    """Record a failed login attempt for progressive lockout."""
    key = email.strip().lower()
    _auth_failed_attempts[key].append(time.time())


def clear_failed_logins(email: str) -> None:
    """Clear failed login attempts upon successful authentication."""
    key = email.strip().lower()
    _auth_failed_attempts.pop(key, None)


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
    global _auth_log_count, _last_auth_log_time
    _auth_ip_timestamps.clear()
    _auth_failed_attempts.clear()
    _user_daily_counts.clear()
    _auth_log_count = 0
    _last_auth_log_time = 0.0
