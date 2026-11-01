"""Plan service module for managing plan versions, generation, and PDF export."""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import PlanVersionSummary
from app.db.models import PlanVersion, User
from app.domain.plan_generator import generate_plan
from app.domain.schemas import PlanSchema
from app.services.event_service import get_user_event
from app.services.pdf_exporter import generate_plan_pdf

logger = logging.getLogger(__name__)


def list_plan_versions(db: Session, user: User, event_id: UUID) -> list[PlanVersionSummary]:
    """List summary metadata for all plan versions belonging to an event owned by user."""
    get_user_event(db, user, event_id)

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


def get_event_plan(
    db: Session, user: User, event_id: UUID, version: int | None = None
) -> PlanVersion:
    """Retrieve full plan JSON for the event (single source of truth).

    If no plan exists yet, generates version 1 on the fly.
    """
    event = get_user_event(db, user, event_id)
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


def generate_new_plan_version(db: Session, user: User, event_id: UUID) -> PlanVersion:
    """Regenerate a new plan version from current event parameters and increment version."""
    event = get_user_event(db, user, event_id)
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


def export_plan_pdf(
    db: Session, user: User, event_id: UUID, version: int | None = None
) -> tuple[bytes, str]:
    """Generate a print-ready PDF binary report for an event plan version."""
    event = get_user_event(db, user, event_id)
    target_ver = version or event.current_version or 1

    plan_ver = db.execute(
        select(PlanVersion).where(
            PlanVersion.event_id == event_id, PlanVersion.version == target_ver
        )
    ).scalar_one_or_none()
    if not plan_ver or not plan_ver.plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan version {target_ver} not found for this event",
        )

    plan = PlanSchema.model_validate(plan_ver.plan)
    pdf_bytes = generate_plan_pdf(event=event, plan=plan)
    filename = f"festiva_plan_{event_id}_v{target_ver}.pdf"
    return pdf_bytes, filename
