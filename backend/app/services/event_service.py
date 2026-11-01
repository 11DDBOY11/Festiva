"""Event service module for managing user event lifecycles.

Handles creation, retrieval, updates, and deletion with strict tenant isolation.
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import EventCreate, EventUpdate
from app.db.models import Event, PlanVersion, User
from app.domain.plan_generator import generate_plan

logger = logging.getLogger(__name__)


def create_event(db: Session, user: User, data: EventCreate) -> Event:
    """Create a new event owned by the user and initialize Plan Version 1 deterministically."""
    event = Event(owner_id=user.id, **data.model_dump())
    db.add(event)
    db.flush()

    # Generate Plan Version 1 deterministically
    try:
        plan_schema = generate_plan(
            title=event.title,
            event_type=event.event_type,
            event_date=event.event_date,
            guest_count=event.guest_count,
            total_budget=event.total_budget,
            city=event.city or "Mangaluru",
        )
        plan_v1 = PlanVersion(
            event_id=event.id,
            version=1,
            plan=plan_schema.model_dump(mode="json"),
            created_by="ai",
            change_summary="Initial plan generated from brief",
        )
        db.add(plan_v1)
        event.current_version = 1
        event.status = "draft"
    except Exception as exc:
        logger.warning("Plan Version 1 auto-generation failed (%s); event saved as draft.", exc)
        event.current_version = None

    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, user: User, limit: int = 20, offset: int = 0) -> list[Event]:
    """List events owned by the user with pagination, ordered newest first."""
    return list(
        db.execute(
            select(Event)
            .where(Event.owner_id == user.id)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )


def get_user_event(db: Session, user: User, event_id: UUID, for_update: bool = False) -> Event:
    """Retrieve an event strictly owned by the authenticated user.

    Returns HTTP 404 (not 403) for non-existent or other users' resources to prevent enumeration.
    """
    stmt = select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    if for_update:
        stmt = stmt.with_for_update()
    event = db.execute(stmt).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def update_event(db: Session, user: User, event_id: UUID, data: EventUpdate) -> Event:
    """Partially update an event owned by the user (PATCH semantics)."""
    event = get_user_event(db, user, event_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, user: User, event_id: UUID) -> None:
    """Delete an event owned by the user with protection for the seeded showcase demo."""
    event = get_user_event(db, user, event_id)

    if user.email == "demo@festiva.ai" and event.title == "Ananya's 21st Birthday Soiree":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The seeded demo showcase event cannot be deleted.",
        )
    db.delete(event)
    db.commit()
