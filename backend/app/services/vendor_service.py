"""Vendor service module for drafting personalized outreach messages."""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm_client import FakeLLMClient
from app.core.rate_limit import check_user_llm_cap
from app.db.models import PlanVersion, User
from app.domain.message_drafter import (
    DraftMessageRequest,
    VendorInquiryDraft,
    draft_vendor_inquiry,
)
from app.domain.schemas import PlanSchema
from app.services.event_service import get_user_event

logger = logging.getLogger(__name__)


def draft_vendor_message(
    db: Session, user: User, event_id: UUID, payload: DraftMessageRequest
) -> VendorInquiryDraft:
    """Draft an LLM-assisted, grounded vendor inquiry for a specific celebration category."""
    event = get_user_event(db, user, event_id)

    current_ver = event.current_version or 1
    plan_ver = db.execute(
        select(PlanVersion).where(
            PlanVersion.event_id == event_id, PlanVersion.version == current_ver
        )
    ).scalar_one_or_none()
    if not plan_ver or not plan_ver.plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan version {current_ver} not found for this event",
        )

    plan = PlanSchema.model_validate(plan_ver.plan)
    within_cap, usage_count = check_user_llm_cap(user.id)
    llm_client = None if within_cap else FakeLLMClient()
    if not within_cap:
        logger.warning(
            "User %s exceeded daily LLM cap (%s requests). Reverting to template message drafter.",
            user.id,
            usage_count,
        )
    return draft_vendor_inquiry(
        event=event,
        plan=plan,
        vendor_category=payload.vendor_category,
        vendor_name=payload.vendor_name,
        custom_notes=payload.custom_notes,
        client=llm_client,
    )
