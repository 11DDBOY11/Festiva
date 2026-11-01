"""Change service module for Phase 5 plan refinement, diffing, and streaming chat."""

import json
import logging
from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.llm_client import FakeLLMClient, get_llm_client
from app.api.schemas import ProposeChangeRequest
from app.core.rate_limit import check_user_llm_cap
from app.db.models import Event, PlanVersion, ProposedChange, User
from app.domain.diff_engine import (
    PlanDiff,
    apply_plan_diff,
    generate_plan_diff,
)
from app.domain.schemas import PlanSchema
from app.services.event_service import get_user_event

logger = logging.getLogger(__name__)


def propose_plan_change(
    db: Session, user: User, event_id: UUID, req: ProposeChangeRequest
) -> ProposedChange:
    """Analyze change request, compute structured diff, and record proposed change."""
    event = get_user_event(db, user, event_id)

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
        within_cap, usage_count = check_user_llm_cap(user.id)
        llm_client = None if within_cap else FakeLLMClient()
        if not within_cap:
            logger.warning(
                "User %s exceeded daily LLM cap (%s requests). Reverting to deterministic diff.",
                user.id,
                usage_count,
            )
        diff = generate_plan_diff(
            base_plan=base_plan_schema,
            prompt=req.prompt,
            client=llm_client,
        )
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


def accept_plan_change(db: Session, user: User, event_id: UUID, change_id: UUID) -> PlanVersion:
    """Accept a proposed change, increment version to N+1, update event, and mark change applied."""
    event = get_user_event(db, user, event_id, for_update=True)

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
            logger.info("Conflict on stale base. Regenerating against plan v%s.", current_ver)
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
    else:
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


def reject_plan_change(db: Session, user: User, event_id: UUID, change_id: UUID) -> dict[str, str]:
    """Reject a proposed change without modifying the current plan."""
    get_user_event(db, user, event_id)

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


def stream_event_chat(db: Session, event: Event, message: str) -> Iterator[str]:
    """Yield Server-Sent Events (SSE) data chunks for interactive co-planning chat."""
    current_ver = event.current_version or 1

    plan_ver = db.execute(
        select(PlanVersion).where(
            PlanVersion.event_id == event.id, PlanVersion.version == current_ver
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

    try:
        for token in llm.stream(prompt=message, system_prompt=system_prompt):
            payload = json.dumps({"content": token})
            yield f"data: {payload}\n\n"
    except Exception as stream_err:
        logger.error("Chat streaming error: %s", stream_err)
        yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
    yield "data: [DONE]\n\n"
