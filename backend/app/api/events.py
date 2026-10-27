"""Events CRUD — all endpoints are scoped to the authenticated user."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import EventCreate, EventResponse, EventUpdate
from app.db.models import Event, User
from app.db.session import get_db

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Create a new event owned by the current user."""
    event = Event(owner_id=user.id, **data.model_dump())
    db.add(event)
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
        db.execute(
            select(Event).where(Event.owner_id == user.id).order_by(Event.created_at.desc())
        )
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
