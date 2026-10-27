"""Pydantic request/response schemas for the REST API."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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
    title: str = Field(..., min_length=1, max_length=255)
    event_type: str = Field(..., pattern=r"^(wedding|birthday|community)$")
    event_date: date | None = None
    city: str | None = None
    guest_count: int | None = Field(None, gt=0)
    total_budget: Decimal | None = Field(None, gt=0)
    currency: str = "INR"


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    event_type: str | None = Field(None, pattern=r"^(wedding|birthday|community)$")
    event_date: date | None = None
    city: str | None = None
    guest_count: int | None = Field(None, gt=0)
    total_budget: Decimal | None = Field(None, gt=0)
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
