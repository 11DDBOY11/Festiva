import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import EventCreate, EventResponse, EventUpdate, PlanVersionResponse
from app.db.models import Event, PlanVersion, User
from app.db.session import get_db
from app.domain.plan_generator import generate_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Create a new event owned by current user and initialize Plan Version 1."""
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
        logger.warning(f"Plan Version 1 auto-generation failed ({exc}); event saved as draft.")
        event.current_version = None

    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=list[EventResponse])
def list_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Event]:
    """List all events owned by the current user, newest first."""
    return list(
        db.execute(select(Event).where(Event.owner_id == user.id).order_by(Event.created_at.desc()))
        .scalars()
        .all()
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Return a single event (must belong to the current user)."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Partially update an event (PATCH semantics — only sent fields are changed)."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete an event."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    db.delete(event)
    db.commit()


@router.get("/{event_id}/plan", response_model=PlanVersionResponse)
def get_event_plan(
    event_id: UUID,
    version: int | None = Query(None, description="Plan version (defaults to current_version)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Retrieve full plan JSON for the event (single source of truth)."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    target_version = version or event.current_version or 1

    plan_version = db.execute(
        select(PlanVersion).where(
            PlanVersion.event_id == event_id, PlanVersion.version == target_version
        )
    ).scalar_one_or_none()

    # If no plan exists yet, generate version 1 on the fly
    if not plan_version:
        plan_schema = generate_plan(
            title=event.title,
            event_type=event.event_type,
            event_date=event.event_date,
            guest_count=event.guest_count,
            total_budget=event.total_budget,
            city=event.city or "Mangaluru",
        )
        plan_version = PlanVersion(
            event_id=event.id,
            version=1,
            plan=plan_schema.model_dump(mode="json"),
            created_by="ai",
            change_summary="Plan v1 generated on request",
        )
        db.add(plan_version)
        event.current_version = 1
        db.commit()
        db.refresh(plan_version)

    return plan_version


@router.post("/{event_id}/plan/generate", response_model=PlanVersionResponse)
def generate_new_plan_version(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Generate or regenerate a new plan version from current event parameters."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    next_version = (event.current_version or 0) + 1

    plan_schema = generate_plan(
        title=event.title,
        event_type=event.event_type,
        event_date=event.event_date,
        guest_count=event.guest_count,
        total_budget=event.total_budget,
        city=event.city or "Mangaluru",
    )

    new_plan_version = PlanVersion(
        event_id=event.id,
        version=next_version,
        plan=plan_schema.model_dump(mode="json"),
        created_by="ai",
        change_summary=f"Regenerated plan version {next_version}",
    )
    db.add(new_plan_version)
    event.current_version = next_version
    event.status = "active"
    db.commit()
    db.refresh(new_plan_version)

    return new_plan_version
