"""API routes for celebrations, plan versions, proposals, and vendor interactions.

Routes only validate input parameters and delegate business logic to dedicated services.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import (
    ChatRequest,
    EventCreate,
    EventResponse,
    EventUpdate,
    PlanVersionResponse,
    PlanVersionSummary,
    ProposeChangeRequest,
    ProposedChangeResponse,
)
from app.db.models import Event, PlanVersion, ProposedChange, User
from app.db.session import get_db
from app.domain.message_drafter import (
    DraftMessageRequest,
    VendorInquiryDraft,
)
from app.services import change_service, event_service, plan_service, vendor_service

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Create a new event owned by current user and initialize Plan Version 1."""
    return event_service.create_event(db=db, user=user, data=data)


@router.get("/", response_model=list[EventResponse])
def list_events(
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Event]:
    """List events owned by the current user with limit/offset pagination, newest first."""
    return event_service.list_events(db=db, user=user, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Return a single event (must belong to the current user)."""
    return event_service.get_user_event(db=db, user=user, event_id=event_id)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Event:
    """Partially update an event (PATCH semantics — only sent fields are changed)."""
    return event_service.update_event(db=db, user=user, event_id=event_id, data=data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete an event."""
    event_service.delete_event(db=db, user=user, event_id=event_id)


@router.get("/{event_id}/versions", response_model=list[PlanVersionSummary])
def list_plan_versions(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PlanVersionSummary]:
    """List summary metadata for all plan versions belonging to this event."""
    return plan_service.list_plan_versions(db=db, user=user, event_id=event_id)


@router.get("/{event_id}/plan", response_model=PlanVersionResponse)
def get_event_plan(
    event_id: UUID,
    version: int | None = Query(None, description="Plan version (defaults to current_version)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Retrieve full plan JSON for the event (single source of truth)."""
    return plan_service.get_event_plan(db=db, user=user, event_id=event_id, version=version)


@router.post("/{event_id}/plan/generate", response_model=PlanVersionResponse)
def generate_new_plan_version(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Generate or regenerate a new plan version from current event parameters."""
    return plan_service.generate_new_plan_version(db=db, user=user, event_id=event_id)


# ---------------------------------------------------------------------------
# Phase 5: Refinement, Diff Propose / Accept / Reject, and Streaming Chat
# ---------------------------------------------------------------------------


@router.post("/{event_id}/changes/propose", response_model=ProposedChangeResponse)
def propose_plan_change(
    event_id: UUID,
    req: ProposeChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProposedChange:
    """Analyze change request, compute structured diff, and record proposed change."""
    return change_service.propose_plan_change(db=db, user=user, event_id=event_id, req=req)


@router.post("/{event_id}/changes/{change_id}/accept", response_model=PlanVersionResponse)
def accept_plan_change(
    event_id: UUID,
    change_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Accept a proposed change, increment version to N+1, update event, and mark change applied."""
    return change_service.accept_plan_change(
        db=db, user=user, event_id=event_id, change_id=change_id
    )


@router.post("/{event_id}/changes/{change_id}/reject")
def reject_plan_change(
    event_id: UUID,
    change_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Reject a proposed change without modifying the current plan."""
    return change_service.reject_plan_change(
        db=db, user=user, event_id=event_id, change_id=change_id
    )


@router.post("/{event_id}/chat")
def chat_event_plan(
    event_id: UUID,
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint for interactive co-planning."""
    event = event_service.get_user_event(db, user, event_id)
    sse_generator = change_service.stream_event_chat(db=db, event=event, message=req.message)
    return StreamingResponse(
        sse_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{event_id}/export.pdf")
def export_event_plan_pdf(
    event_id: UUID,
    version: int | None = Query(None, description="Specific plan version to export"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Export event plan as a print-styled PDF document with ₹ formatting and tables."""
    pdf_bytes, filename = plan_service.export_plan_pdf(
        db=db, user=user, event_id=event_id, version=version
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/{event_id}/messages/draft", response_model=VendorInquiryDraft)
def draft_event_vendor_message(
    event_id: UUID,
    payload: DraftMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VendorInquiryDraft:
    """Draft an LLM-assisted, grounded vendor inquiry for a specific category."""
    return vendor_service.draft_vendor_message(db=db, user=user, event_id=event_id, payload=payload)
