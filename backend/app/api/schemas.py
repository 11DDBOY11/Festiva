"""Pydantic request/response schemas for the REST API."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_policy import normalize_email, validate_password_policy

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_user_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            return normalize_email(v)
        return v

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        validate_password_policy(v)
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_user_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            return normalize_email(v)
        return v


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    event_type: str = Field(..., pattern=r"^(wedding|birthday|community)$")
    event_date: date | None = None
    city: str | None = Field(None, max_length=100)
    guest_count: int | None = Field(None, ge=1, le=10000)
    total_budget: Decimal | None = Field(None, ge=Decimal("1000"), le=Decimal("100000000"))
    currency: str = Field("INR", max_length=3)


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    event_type: str | None = Field(None, pattern=r"^(wedding|birthday|community)$")
    event_date: date | None = None
    city: str | None = Field(None, max_length=100)
    guest_count: int | None = Field(None, ge=1, le=10000)
    total_budget: Decimal | None = Field(None, ge=Decimal("1000"), le=Decimal("100000000"))
    status: str | None = Field(None, pattern=r"^(draft|active|completed|cancelled)$")


class EventResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    event_type: str
    event_date: date | None
    city: str | None
    guest_count: int | None
    total_budget: Decimal | None
    currency: str
    current_version: int | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanVersionResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    version: int
    created_by: str
    change_summary: str | None
    created_at: datetime
    plan: dict[str, Any]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Phase 5: Plan Refinement, Versioning, and Streaming Chat
# ---------------------------------------------------------------------------


class ProposeChangeRequest(BaseModel):
    prompt: str = Field(
        ..., min_length=2, max_length=1000, description="Natural language change request"
    )
    base_version: int | None = Field(
        None,
        ge=1,
        description="Base plan version to apply diff against (defaults to current_version)",
    )


class ProposedChangeResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    base_version: int
    diff: dict[str, Any]
    budget_impact: Decimal
    status: str  # pending | accepted | rejected
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=50)


class PlanVersionSummary(BaseModel):
    version: int
    created_by: str
    change_summary: str | None
    created_at: datetime
    total_budget: Decimal | None = None
