import json
import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.llm_client import get_llm_client
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
from app.domain.diff_engine import (
    PlanDiff,
    apply_plan_diff,
    generate_plan_diff,
)
from app.domain.plan_generator import generate_plan
from app.domain.schemas import PlanSchema

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
        logger.warning("Plan Version 1 auto-generation failed (%s); event saved as draft.", exc)
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


@router.get("/{event_id}/versions", response_model=list[PlanVersionSummary])
def list_plan_versions(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PlanVersionSummary]:
    """List summary metadata for all plan versions belonging to this event."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    versions = (
        db.execute(
            select(PlanVersion)
            .where(PlanVersion.event_id == event_id)
            .order_by(PlanVersion.version.asc())
        )
        .scalars()
        .all()
    )

    summaries = []
    for v in versions:
        tot_budget = None
        if isinstance(v.plan, dict) and "total_budget" in v.plan:
            tot_budget = v.plan["total_budget"]
        summaries.append(
            PlanVersionSummary(
                version=v.version,
                created_by=v.created_by,
                change_summary=v.change_summary,
                created_at=v.created_at,
                total_budget=tot_budget,
            )
        )
    return summaries


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
    """Analyze change request, compute structured diff, and record proposed change.

    Applies optimistic locking: if req.base_version differs from current_version,
    rebases the request against current_version automatically once.
    """
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    current_ver = event.current_version or 1
    base_ver = req.base_version or current_ver

    # Optimistic locking check with 1-shot rebase against current_version
    if req.base_version is not None and req.base_version != current_ver:
        logger.info(
            "Optimistic locking base_version mismatch on event %s (client %s, current %s). "
            "Rebasing against current_version %s.",
            event_id,
            req.base_version,
            current_ver,
            current_ver,
        )
        base_ver = current_ver

    # Load base plan version
    plan_ver = db.execute(
        select(PlanVersion).where(PlanVersion.event_id == event_id, PlanVersion.version == base_ver)
    ).scalar_one_or_none()
    if not plan_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Base plan version {base_ver} not found for this event",
        )

    try:
        base_plan_schema = PlanSchema.model_validate(plan_ver.plan)
        diff = generate_plan_diff(base_plan=base_plan_schema, prompt=req.prompt)
    except Exception as exc:
        logger.error("Failed to compute plan diff: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    proposed_change = ProposedChange(
        event_id=event.id,
        base_version=base_ver,
        diff=diff.model_dump(mode="json"),
        budget_impact=diff.budget_impact,
        status="pending",
    )
    db.add(proposed_change)
    db.commit()
    db.refresh(proposed_change)

    return proposed_change


@router.post("/{event_id}/changes/{change_id}/accept", response_model=PlanVersionResponse)
def accept_plan_change(
    event_id: UUID,
    change_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanVersion:
    """Accept a proposed change, increment version to N+1, update event, and mark change applied."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id).with_for_update()
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    change = db.execute(
        select(ProposedChange).where(
            ProposedChange.id == change_id, ProposedChange.event_id == event_id
        )
    ).scalar_one_or_none()
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposed change not found"
        )

    if change.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change is already {change.status}; only pending changes can be accepted",
        )

    # Optimistic locking validation on accept
    current_ver = event.current_version or 1
    base_ver = change.base_version

    diff_model = PlanDiff.model_validate(change.diff)

    # If current_ver has advanced past change.base_version, attempt 1-shot rebase or regenerate
    if current_ver != change.base_version:
        logger.info(
            "Change base_version %s differs from current %s. Checking conflict for rebase.",
            base_ver,
            current_ver,
        )
        orig_pv = db.execute(
            select(PlanVersion).where(
                PlanVersion.event_id == event_id, PlanVersion.version == change.base_version
            )
        ).scalar_one_or_none()
        curr_pv = db.execute(
            select(PlanVersion).where(
                PlanVersion.event_id == event_id, PlanVersion.version == current_ver
            )
        ).scalar_one_or_none()
        if not curr_pv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Current plan version {current_ver} could not be loaded",
            )

        current_plan = PlanSchema.model_validate(curr_pv.plan)

        # Check for conflict: Did any category modified in diff_model
        # also get modified in current_plan compared to orig_pv?
        conflict = False
        if orig_pv:
            orig_plan = PlanSchema.model_validate(orig_pv.plan)
            orig_cats = {c.category: c.allocated_amount for c in orig_plan.budget.categories}
            curr_cats = {c.category: c.allocated_amount for c in current_plan.budget.categories}
            for cd in diff_model.category_changes:
                if cd.category in orig_cats and cd.category in curr_cats:
                    if orig_cats[cd.category] != curr_cats[cd.category]:
                        conflict = True
                        break

        if conflict:
            logger.info(
                "Conflict on stale base. Regenerating against plan v%s.",
                current_ver,
            )
            try:
                diff_model = generate_plan_diff(base_plan=current_plan, prompt=diff_model.prompt)
            except Exception as regen_err:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Conflict detected with plan v{current_ver} and "
                        f"1-shot regeneration failed: {regen_err}"
                    ),
                )
        else:
            # Rebase diff_model onto current_plan
            diff_model.old_total_budget = current_plan.total_budget
            diff_model.new_total_budget = current_plan.total_budget + diff_model.budget_impact
            curr_cat_map = {
                c.category.lower(): c.allocated_amount for c in current_plan.budget.categories
            }
            for cd in diff_model.category_changes:
                if cd.category.lower() in curr_cat_map:
                    curr_amt = curr_cat_map[cd.category.lower()]
                    cd.old_amount = curr_amt
                    cd.new_amount = curr_amt + cd.delta
                    if diff_model.new_total_budget > Decimal("0"):
                        cd.new_share_pct = round(
                            (cd.new_amount / diff_model.new_total_budget) * Decimal("100"), 2
                        )

        base_plan = current_plan
        base_ver = current_ver
    else:
        # Load base plan
        plan_ver = db.execute(
            select(PlanVersion).where(
                PlanVersion.event_id == event_id, PlanVersion.version == base_ver
            )
        ).scalar_one_or_none()
        if not plan_ver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Base plan version {base_ver} could not be loaded",
            )
        base_plan = PlanSchema.model_validate(plan_ver.plan)

    try:
        new_plan = apply_plan_diff(base_plan=base_plan, diff=diff_model)
    except Exception as exc:
        logger.error("Failed to apply plan diff: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    next_version = current_ver + 1
    new_plan.version = next_version

    new_plan_version = PlanVersion(
        event_id=event.id,
        version=next_version,
        plan=new_plan.model_dump(mode="json"),
        created_by="user",
        change_summary=change.diff.get("summary", "Refined plan via proposal"),
    )
    db.add(new_plan_version)

    # Update event state
    event.current_version = next_version
    event.total_budget = new_plan.total_budget
    event.status = "active"
    change.status = "applied"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent plan update conflict; version already exists. Please retry.",
        )
    db.refresh(new_plan_version)
    db.refresh(event)

    return new_plan_version


@router.post("/{event_id}/changes/{change_id}/reject")
def reject_plan_change(
    event_id: UUID,
    change_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Reject a proposed change without modifying the current plan."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    change = db.execute(
        select(ProposedChange).where(
            ProposedChange.id == change_id, ProposedChange.event_id == event_id
        )
    ).scalar_one_or_none()
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposed change not found"
        )

    if change.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change is already {change.status}; only pending changes can be rejected",
        )

    change.status = "rejected"
    db.commit()

    return {"status": "rejected", "change_id": str(change_id)}


@router.post("/{event_id}/chat")
def chat_event_plan(
    event_id: UUID,
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint for interactive co-planning."""
    event = db.execute(
        select(Event).where(Event.id == event_id, Event.owner_id == user.id)
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    current_ver = event.current_version or 1
    plan_ver = db.execute(
        select(PlanVersion).where(
            PlanVersion.event_id == event_id, PlanVersion.version == current_ver
        )
    ).scalar_one_or_none()

    plan_context = ""
    if plan_ver and isinstance(plan_ver.plan, dict):
        p_dict = plan_ver.plan
        cats = [
            f"{c.get('category')}: ₹{float(c.get('allocated_amount', 0)):,.0f}"
            for c in p_dict.get("budget", {}).get("categories", [])
        ]
        plan_context = (
            f"Event: {event.title} ({event.event_type})\n"
            f"Version: v{plan_ver.version}\n"
            f"Total Budget: INR {float(event.total_budget or p_dict.get('total_budget', 0)):,.0f}\n"
            f"Guest Count: {event.guest_count or p_dict.get('guest_count')}\n"
            f"Budget Breakdown: {', '.join(cats)}\n"
            f"Plan Summary: {p_dict.get('summary', '')}\n"
        )

    system_prompt = (
        "You are Festiva Copilot, a budget-aware, empathetic celebration planner in Mangaluru.\n"
        "You help hosts co-plan weddings, birthdays, and community festivals within budget.\n"
        f"Active Plan Details:\n{plan_context}\n"
        "Guidelines:\n"
        "1. Give concise, culturally resonant advice for Dakshina Kannada / Mangaluru.\n"
        "2. If the user asks to adjust budget (e.g., 'reduce décor by ₹10,000' or 'add catering'), "
        "explain the trade-offs and tell them they can preview the diff.\n"
    )

    llm = get_llm_client()

    def generate_sse():
        try:
            for token in llm.stream(prompt=req.message, system_prompt=system_prompt):
                payload = json.dumps({"content": token})
                yield f"data: {payload}\n\n"
        except Exception as stream_err:
            logger.error("Chat streaming error: %s", stream_err)
            yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
