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
from app.core.rate_limit import check_auth_rate_limit
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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)) -> User:
    """Create a new user account."""
    check_auth_rate_limit(request)
    existing = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate and return access + refresh tokens, storing jti for rotation."""
    check_auth_rate_limit(request)
    user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

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
