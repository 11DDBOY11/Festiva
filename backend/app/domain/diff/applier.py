"""Plan diff applier: applies verified diffs onto base plans with domain validation."""

import copy
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.domain.category_labels import format_category_label
from app.domain.diff.schemas import PlanDiff
from app.domain.schemas import (
    BudgetBreakdown,
    BudgetCategoryAllocation,
    PlanSchema,
)
from app.domain.validators import (
    validate_plan_budget,
    validate_plan_dates,
    validate_price_honesty,
    validate_vendor_grounding,
)
from app.domain.vendor_directory import get_known_vendor_ids, get_known_vendor_map


def apply_plan_diff(
    base_plan: PlanSchema,
    diff: PlanDiff,
) -> PlanSchema:
    """Apply verified PlanDiff onto base_plan to produce version N+1 with domain validation."""
    updated_plan_dict = copy.deepcopy(base_plan.model_dump())

    new_version = base_plan.version + 1
    updated_plan_dict["version"] = new_version
    updated_plan_dict["total_budget"] = diff.new_total_budget

    # 1. Apply category changes
    updated_categories: list[BudgetCategoryAllocation] = []
    guest_count = base_plan.guest_count or 100

    for cat_item in base_plan.budget.categories:
        clean_name = format_category_label(cat_item.category)
        matching_delta = next(
            (
                d
                for d in diff.category_changes
                if format_category_label(d.category).lower() == clean_name.lower()
            ),
            None,
        )
        if matching_delta:
            new_amt = matching_delta.new_amount
            new_share = (
                (new_amt / diff.new_total_budget * Decimal("100")).quantize(
                    Decimal("0.1"), rounding=ROUND_HALF_UP
                )
                if diff.new_total_budget > Decimal("0")
                else Decimal("0.0")
            )
            per_guest = (
                round(new_amt / Decimal(str(guest_count)), 2) if cat_item.per_guest_cost else None
            )
            updated_categories.append(
                BudgetCategoryAllocation(
                    category=clean_name,
                    share_pct=new_share,
                    allocated_amount=new_amt,
                    per_guest_cost=per_guest,
                    notes=f"Refined in v{new_version}: {diff.summary}",
                )
            )
        else:
            recomputed_share = (
                (cat_item.allocated_amount / diff.new_total_budget * Decimal("100")).quantize(
                    Decimal("0.1"), rounding=ROUND_HALF_UP
                )
                if diff.new_total_budget > Decimal("0")
                else Decimal("0.0")
            )
            updated_categories.append(
                BudgetCategoryAllocation(
                    category=clean_name,
                    share_pct=recomputed_share,
                    allocated_amount=cat_item.allocated_amount,
                    per_guest_cost=cat_item.per_guest_cost,
                    notes=cat_item.notes,
                )
            )

    # Append any newly introduced category (e.g. Contingency & Reserve)
    existing_cat_names = {c.category.lower() for c in updated_categories}
    for cd in diff.category_changes:
        cd_clean = format_category_label(cd.category)
        if cd_clean.lower() not in existing_cat_names and cd.new_amount > Decimal("0"):
            new_share = (
                (cd.new_amount / diff.new_total_budget * Decimal("100")).quantize(
                    Decimal("0.1"), rounding=ROUND_HALF_UP
                )
                if diff.new_total_budget > Decimal("0")
                else Decimal("0.0")
            )
            updated_categories.append(
                BudgetCategoryAllocation(
                    category=cd_clean,
                    share_pct=new_share,
                    allocated_amount=cd.new_amount,
                    per_guest_cost=None,
                    notes=f"Refined in v{new_version}: Reallocated from budget adjustment",
                )
            )
            existing_cat_names.add(cd_clean.lower())

    # Balance rounding differences on allocated amounts to guarantee sum == total
    allocated_sum = sum(c.allocated_amount for c in updated_categories)
    diff_from_total = diff.new_total_budget - allocated_sum
    if diff_from_total != Decimal("0") and updated_categories:
        contingency_cat = next(
            (c for c in updated_categories if "contingency" in c.category.lower()), None
        )
        if contingency_cat:
            contingency_cat.allocated_amount += diff_from_total
        else:
            updated_categories[0].allocated_amount += diff_from_total

    # Recompute shares from final balanced amounts and balance shares sum to 100.0%
    if diff.new_total_budget > Decimal("0"):
        for c in updated_categories:
            c.share_pct = ((c.allocated_amount / diff.new_total_budget) * Decimal("100")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )

        shares_sum = sum(c.share_pct for c in updated_categories)
        shares_diff = Decimal("100.0") - shares_sum
        if shares_diff != Decimal("0.0") and updated_categories:
            largest_cat = max(updated_categories, key=lambda c: c.allocated_amount)
            largest_cat.share_pct += shares_diff

    updated_breakdown = BudgetBreakdown(
        total_budget=diff.new_total_budget,
        currency="INR",
        categories=updated_categories,
    )
    updated_plan_dict["budget"] = updated_breakdown.model_dump()

    # 2. Summary preservation: Stop appending diff text (kept in change_summary)
    updated_plan_dict["summary"] = base_plan.summary

    # 3. Apply setting changes
    if not updated_plan_dict.get("meta"):
        updated_plan_dict["meta"] = {}
    for k, v in diff.setting_changes.items():
        updated_plan_dict["meta"][k] = v
        if k == "theme":
            updated_plan_dict["meta"]["theme"] = v

    # 4. Apply timeline changes
    timeline_items: list[dict[str, Any]] = updated_plan_dict.get("timeline", [])
    removed_titles = {td.task.lower() for td in diff.timeline_changes if td.action == "removed"}
    if removed_titles:
        timeline_items = [
            t for t in timeline_items if t.get("task", "").lower() not in removed_titles
        ]

    event_date = base_plan.event_date or (date.today() + timedelta(days=30))
    for td in diff.timeline_changes:
        if td.action == "added":
            target_d = (
                date.fromisoformat(td.new_date) if td.new_date else (event_date - timedelta(days=7))
            )
            # Strict date check for new task
            if target_d < date.today():
                msg = (
                    f"New or modified task '{td.task}' cannot be "
                    f"scheduled before today ({date.today()})."
                )
                raise ValueError(msg)
            timeline_items.append(
                {
                    "phase": "Refinement",
                    "days_before_event": max(0, (event_date - target_d).days),
                    "target_date": target_d.isoformat(),
                    "task": td.task,
                    "category": "Refinement",
                    "owner": "Host",
                    "priority": "medium",
                }
            )

    # Maintain strict chronological ordering so timeline passes date validation
    def _safe_timeline_sort_key(t: dict[str, Any]) -> tuple[str, int]:
        d = t.get("target_date")
        if isinstance(d, date):
            d_str = d.isoformat()
        elif isinstance(d, str):
            d_str = d
        else:
            d_str = "9999-99-99"
        return (d_str, -t.get("days_before_event", 0))

    timeline_items.sort(key=_safe_timeline_sort_key)
    updated_plan_dict["timeline"] = timeline_items

    # 5. Apply vendor changes if grounded vendor available
    if diff.vendor_changes:
        vendor_shortlist = updated_plan_dict.get("vendor_shortlist", [])
        for v_cat in diff.vendor_changes:
            vendor_shortlist.append(
                {
                    "category": v_cat,
                    "vendor_id": None,
                    "vendor_name": f"Mangaluru {v_cat} Specialist",
                    "estimated_price_low": None,
                    "estimated_price_high": None,
                    "price_unit": "flat",
                    "is_grounded": False,
                    "price_status": "to confirm",
                    "questions_to_ask": [f"Inquire about availability for {v_cat} in Mangaluru."],
                    "budget_impact": Decimal("0"),
                    "reason": f"Required for {v_cat}.",
                    "is_sample": False,
                }
            )
        updated_plan_dict["vendor_shortlist"] = vendor_shortlist

    # Construct validated plan model
    new_plan = PlanSchema.model_validate(updated_plan_dict)

    # -----------------------------------------------------------------------
    # Domain Validators
    # -----------------------------------------------------------------------
    b_ok, b_msg = validate_plan_budget(new_plan)
    if not b_ok:
        raise ValueError(f"Refined plan failed budget validation: {b_msg}")

    # Requirement 4 check:
    # Grandfather existing untouched base tasks that had historical dates,
    # but strictly verify that any new or changed task is >= today.
    base_tasks_map = {t.task: t.target_date for t in base_plan.timeline if t.target_date}
    for task in new_plan.timeline:
        if task.task not in base_tasks_map or task.target_date != base_tasks_map[task.task]:
            # This is a new or modified task!
            if task.target_date and task.target_date < date.today():
                msg = (
                    f"New or modified task '{task.task}' cannot be "
                    f"scheduled before today ({date.today()})."
                )
                raise ValueError(msg)

    ref_date = date.today()
    if base_plan.timeline:
        min_base_date = min(
            (t.target_date for t in base_plan.timeline if t.target_date), default=None
        )
        if min_base_date and min_base_date < ref_date:
            ref_date = min_base_date

    d_ok, d_msg = validate_plan_dates(new_plan, reference_today=ref_date)
    if not d_ok:
        raise ValueError(f"Refined plan failed date validation: {d_msg}")

    known_ids = get_known_vendor_ids()
    g_ok, g_msgs = validate_vendor_grounding(new_plan, known_ids)
    if not g_ok:
        raise ValueError(f"Refined plan failed vendor grounding: {'; '.join(g_msgs)}")

    known_map = get_known_vendor_map()
    h_ok, h_msgs = validate_price_honesty(new_plan, known_map)
    if not h_ok:
        raise ValueError(f"Refined plan failed price honesty: {'; '.join(h_msgs)}")

    return new_plan
