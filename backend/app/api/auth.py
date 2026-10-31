"""Auth routes: register, login, token refresh with rotation, current user."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.core.password_policy import normalize_email
from app.core.rate_limit import (
    check_account_lockout,
    check_auth_rate_limit,
    clear_failed_logins,
    record_failed_login,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# Dummy hash used for constant-time comparison when user doesn't exist
_DUMMY_HASH = "$2b$12$e8k5.6z6c4N0j5x0mN8qO.8X4bYx3bK8oI7h3wJ0l1k9m2n3p4q5r"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)) -> User:
    """Create a new user account with normalized email and strong password validation."""
    check_auth_rate_limit(request)
    normalized = normalize_email(data.email)
    existing = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        name=data.name.strip(),
        email=normalized,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with constant-time password check and account lockout protection."""
    check_auth_rate_limit(request)
    normalized = normalize_email(data.email)
    check_account_lockout(normalized)

    user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()

    # Equal timing: always perform a bcrypt comparison even if user is not found
    target_hash = user.password_hash if user else _DUMMY_HASH
    is_valid = verify_password(data.password, target_hash)

    if not user or not is_valid:
        record_failed_login(normalized)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    clear_failed_logins(normalized)

    access_token = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)

    # Persist the refresh token record
    rt = RefreshToken(
        user_id=user.id,
        jti=jti,
        expires_at=expires_at,
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    data: TokenRefresh,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Revoke the presented refresh token and log out the user."""
    payload = decode_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti")
        if jti:
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.jti == jti, RefreshToken.user_id == user.id)
                .values(revoked_at=datetime.now(UTC))
            )
            db.commit()
    return {"status": "logged_out"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: TokenRefresh, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair.

    Implements token rotation:
    - The old refresh token is marked as revoked.
    - If a revoked token is presented (reuse attempt), ALL active refresh tokens
      for that user are revoked and 401 is returned.
    """
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token",
        )

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        ) from exc

    token_record = db.execute(
        select(RefreshToken).where(RefreshToken.jti == jti)
    ).scalar_one_or_none()

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    now = datetime.now(UTC)

    # Reuse detection: token already revoked!
    if token_record.revoked_at is not None:
        # Revoke ALL active tokens for this user
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected. All sessions have been revoked.",
        )

    # Check expiration
    if token_record.expires_at < now:
        token_record.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Revoke current token
    token_record.revoked_at = now

    # Issue new token pair
    new_access_token = create_access_token(user_id)
    new_refresh_token, new_jti, new_expires_at = create_refresh_token(user_id)

    new_token_record = RefreshToken(
        user_id=user_id,
        jti=new_jti,
        expires_at=new_expires_at,
    )
    db.add(new_token_record)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return current_user
