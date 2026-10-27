"""Domain validators for plan integrity, date ordering, and vendor grounding.

Zero LLM calls. Pure Python verification against deterministic rules.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.schemas import PlanSchema


def validate_plan_budget(plan: PlanSchema, tolerance_pct: float = 1.0) -> tuple[bool, str]:
    """Validate that category totals equal stated budget ±tolerance_pct."""
    allocated_sum = plan.budget.allocated_sum
    total = plan.total_budget
    if total <= Decimal("0"):
        return False, "Total budget must be positive."

    diff = abs(allocated_sum - total)
    diff_pct = (diff / total) * 100
    if float(diff_pct) > tolerance_pct:
        msg = (
            f"Budget mismatch: allocated sum ₹{allocated_sum} differs from total "
            f"₹{total} by {diff_pct:.2f}% (exceeds {tolerance_pct}%)."
        )
        return False, msg
    return True, "Budget integrity verified."


def validate_plan_dates(
    plan: PlanSchema, reference_today: date | None = None
) -> tuple[bool, str]:
    """Validate that timeline dates fall between today and event date in chronological order."""
    if not plan.event_date:
        return True, "No event date specified to check."

    today = reference_today or date.today()
    if plan.event_date < today:
        return False, f"Event date ({plan.event_date}) is in the past."

    previous_date: date | None = None
    for item in plan.timeline:
        if item.target_date:
            if item.target_date < today:
                msg = (
                    f"Timeline task '{item.task}' date {item.target_date} "
                    f"is before today ({today})."
                )
                return False, msg
            if item.target_date > plan.event_date:
                msg = (
                    f"Timeline task '{item.task}' date {item.target_date} "
                    f"is after event date ({plan.event_date})."
                )
                return False, msg
            if previous_date and item.target_date < previous_date:
                msg = (
                    f"Timeline task '{item.task}' date {item.target_date} "
                    "is out of chronological order."
                )
                return False, msg
            previous_date = item.target_date

    return True, "All timeline dates are valid and ordered."


def validate_vendor_grounding(
    plan: PlanSchema, known_vendor_ids: set[str]
) -> tuple[bool, list[str]]:
    """Validate that every named/shortlisted vendor exists in the known vendor directory."""
    ungrounded: list[str] = []
    for rec in plan.vendor_shortlist:
        if rec.vendor_id:
            if rec.vendor_id not in known_vendor_ids:
                msg = f"Vendor '{rec.vendor_name}' (ID: {rec.vendor_id}) not found in directory."
                ungrounded.append(msg)
        elif rec.is_grounded:
            ungrounded.append(f"Vendor '{rec.vendor_name}' marked grounded but missing vendor_id.")

    is_valid = len(ungrounded) == 0
    return is_valid, ungrounded


def validate_price_honesty(
    plan: PlanSchema, known_vendor_map: dict[str, dict[str, Any]]
) -> tuple[bool, list[str]]:
    """Enforce Price Honesty: No exact price shown without a source record.

    If vendor has no price range or is ungrounded, price_status must be 'to confirm'.
    """
    violations: list[str] = []
    for rec in plan.vendor_shortlist:
        if rec.vendor_id and rec.vendor_id in known_vendor_map:
            known = known_vendor_map[rec.vendor_id]
            # If known record has no price data, price_status must be 'to confirm'
            if known.get("price_low") is None and known.get("price_high") is None:
                if rec.price_status != "to confirm":
                    violations.append(
                        f"Vendor '{rec.vendor_name}' has no price record but is marked confirmed."
                    )
        elif not rec.vendor_id:
            if rec.price_status != "to confirm":
                msg = f"Custom vendor '{rec.vendor_name}' without source must be 'to confirm'."
                violations.append(msg)

    is_valid = len(violations) == 0
    return is_valid, violations
