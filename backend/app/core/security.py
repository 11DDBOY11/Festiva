"""Password hashing and JWT token utilities using bcrypt and PyJWT."""

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check *plain* against a bcrypt *hashed* value."""
    pw_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hashed_bytes)


# ---------------------------------------------------------------------------
# JWT helpers (PyJWT)
# ---------------------------------------------------------------------------


def create_access_token(user_id: UUID) -> str:
    """Short-lived token for API access."""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: UUID, jti: str | None = None) -> tuple[str, str, datetime]:
    """Longer-lived token with unique jti for rotation tracking.

    Returns:
        tuple of (encoded_token_str, jti, expire_datetime)
    """
    token_jti = jti or str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    payload = {
        "sub": str(user_id),
        "jti": token_jti,
        "exp": expire,
        "type": "refresh",
    }
    encoded = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return encoded, token_jti, expire


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT using PyJWT. Returns the payload dict, or ``None`` on failure."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
