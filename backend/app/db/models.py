"""SQLAlchemy ORM models for Festiva AI.

Includes full schema:
- Global: User, RefreshToken, Vendor, KnowledgeChunk, BudgetRule
- Per-Event: Event, PlanVersion, ProposedChange, EventVendor, Expense, Task, Guest
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Global / Auth Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    events: Mapped[list["Event"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


# ---------------------------------------------------------------------------
# Global Curated Knowledge Models
# ---------------------------------------------------------------------------


class Vendor(Base):
    __tablename__ = "vendor_directory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255))
    area: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(100), default="Mangaluru", index=True)
    capacity_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_low: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_high: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_unit: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # per_plate | flat | per_hour
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_on: Mapped[date | None] = mapped_column(nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")  # high | medium | low
    contact: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(50))  # vendor | guide | checklist
    ref_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    content: Mapped[str] = mapped_column(Text)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[Any | None] = mapped_column(Vector(768), nullable=True)


class BudgetRule(Base):
    __tablename__ = "budget_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # wedding | birthday | community
    tier: Mapped[str] = mapped_column(
        String(30), default="standard", index=True
    )  # economy | standard | premium
    category: Mapped[str] = mapped_column(String(100))
    share_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # percentage e.g. 30.00
    per_guest_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


# ---------------------------------------------------------------------------
# Per-Event Models
# ---------------------------------------------------------------------------


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(50))  # wedding | birthday | community
    event_date: Mapped[date | None] = mapped_column(nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), default="Mangaluru")
    guest_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    current_version: Mapped[int | None] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="events")
    plans: Mapped[list["PlanVersion"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="PlanVersion.version"
    )
    changes: Mapped[list["ProposedChange"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    vendors: Mapped[list["EventVendor"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    guests: Mapped[list["Guest"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class PlanVersion(Base):
    """Immutable full plan version — the single source of truth."""

    __tablename__ = "plan_versions"
    __table_args__ = (
        UniqueConstraint("event_id", "version", name="uq_plan_versions_event_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[str] = mapped_column(String(20), default="ai")  # user | ai
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="plans")


class ProposedChange(Base):
    __tablename__ = "proposed_changes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    base_version: Mapped[int] = mapped_column(Integer, nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    budget_impact: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | accepted | rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="changes")


class EventVendor(Base):
    __tablename__ = "event_vendors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_directory.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(100))
    custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="shortlisted"
    )  # shortlisted | contacted | booked | declined

    event: Mapped["Event"] = relationship(back_populates="vendors")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_on: Mapped[date | None] = mapped_column(nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendor_directory.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped["Event"] = relationship(back_populates="expenses")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # high | medium | low
    status: Mapped[str] = mapped_column(
        String(20), default="todo"
    )  # todo | in_progress | completed

    event: Mapped["Event"] = relationship(back_populates="tasks")


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rsvp: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | attending | declined
    dietary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plus_ones: Mapped[int] = mapped_column(Integer, default=0)

    event: Mapped["Event"] = relationship(back_populates="guests")
