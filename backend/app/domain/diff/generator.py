"""Plan diff generator: computes structured diffs from user modification prompts."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.ai.llm_client import LLMClient, get_llm_client
from app.domain.category_labels import format_category_label
from app.domain.diff.extractor import _find_matching_category, _heuristic_extract_delta
from app.domain.diff.schemas import (
    PROPOSAL_SYSTEM_PROMPT,
    AddTaskOp,
    AddVendorCategoryOp,
    AdjustCategoryOp,
    CategoryDelta,
    LLMPlanProposal,
    PlanDiff,
    RemoveTaskOp,
    SetSettingOp,
    SetTotalBudgetOp,
    TimelineDelta,
    UnsupportedOperationError,
)
from app.domain.schemas import PlanSchema

logger = logging.getLogger(__name__)


def generate_plan_diff(
    base_plan: PlanSchema,
    prompt: str,
    client: LLMClient | None = None,
) -> PlanDiff:
    """Compute plan diff from user modification prompt via LLM with validation & fallback."""
    prompt_clean = prompt.strip()
    if not prompt_clean:
        raise ValueError("Modification prompt cannot be empty.")

    category_names = [c.category for c in base_plan.budget.categories]
    llm = client or get_llm_client()

    proposal: LLMPlanProposal | None = None
    lower_prompt = prompt_clean.lower()

    # Direct check for obviously unsupported requests before calling LLM
    unsupported_keywords = [
        "flight",
        "airline",
        "crypto",
        "bitcoin",
        "casino",
        "gambling",
        "passport",
        "visa",
    ]
    if any(kw in lower_prompt for kw in unsupported_keywords):
        raise UnsupportedOperationError(
            "Festiva can't do that yet: Travel booking, legal visas, or crypto are not supported."
        )

    # 1. Attempt LLM-driven structured extraction
    try:
        proposal = llm.generate_structured(
            prompt=(
                f"User requested change: '{prompt_clean}'\n"
                f"Existing categories: {', '.join(category_names)}\n"
                f"Current total budget: INR {base_plan.total_budget:,.0f}\n"
                f"Event date: {base_plan.event_date or 'TBD'}\n"
                f"Current theme: {base_plan.meta.get('theme', 'Not set')}"
            ),
            response_model=LLMPlanProposal,
            system_prompt=PROPOSAL_SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.warning(
            "LLM proposal extraction failed (%s); attempting deterministic fallback.", exc
        )
        proposal = None

    # Handle unsupported requests flagged by LLM
    if proposal and proposal.unsupported_request:
        raise UnsupportedOperationError(
            f"Festiva can't do that yet: {proposal.unsupported_request}"
        )

    # Fallback to deterministic regex extractor if LLM gave no operations or failed
    if not proposal or not proposal.operations:
        cat_match, delta_match, desc = _heuristic_extract_delta(prompt_clean, category_names)
        if cat_match and delta_match is not None:
            proposal = LLMPlanProposal(
                explanation=desc,
                operations=[
                    AdjustCategoryOp(
                        category=cat_match,
                        amount_delta=delta_match,
                    )
                ],
            )
        elif "weather" in lower_prompt or "rain" in lower_prompt or "monsoon" in lower_prompt:
            proposal = LLMPlanProposal(
                explanation="Make celebration weather-safe with water-proof arrangements",
                operations=[
                    SetSettingOp(key="weather_safe", value="true"),
                    AddTaskOp(
                        task="Arrange water-proof monsoon canopy and indoor backup arrangements",
                        category="Venue",
                        days_before_event=7,
                        priority="high",
                    ),
                    AddVendorCategoryOp(category="Weather Protection / Canopy Rentals"),
                ],
            )
        elif "kid" in lower_prompt or "children" in lower_prompt:
            proposal = LLMPlanProposal(
                explanation="Add dedicated children activity and entertainment zone",
                operations=[
                    SetSettingOp(key="kids_zone", value="true"),
                    AddTaskOp(
                        task="Set up dedicated kids activity and craft play area",
                        category="Entertainment",
                        days_before_event=3,
                        priority="medium",
                    ),
                    AddVendorCategoryOp(category="Kids Entertainment & Magic Shows"),
                ],
            )
        elif "south indian" in lower_prompt or "theme" in lower_prompt:
            proposal = LLMPlanProposal(
                explanation="Update theme to Traditional South Indian & Coastal Heritage",
                operations=[
                    SetSettingOp(key="theme", value="Traditional South Indian & Coastal Heritage"),
                    AddTaskOp(
                        task="Coordinate traditional South Indian floral decor",
                        category="Decor",
                        days_before_event=5,
                        priority="high",
                    ),
                ],
            )
        else:
            raise UnsupportedOperationError(
                f"Festiva can't do that yet: Request '{prompt_clean}' is not an allowed operation."
            )

    # 2. Code validates and applies operations (The LLM NEVER writes to the DB)
    category_deltas: list[CategoryDelta] = []
    timeline_deltas: list[TimelineDelta] = []
    setting_changes: dict[str, Any] = {}
    vendor_changes: list[str] = []

    old_total = base_plan.total_budget
    current_total = old_total

    event_date = base_plan.event_date or (date.today() + timedelta(days=30))

    for op in proposal.operations:
        if isinstance(op, AdjustCategoryOp):
            matched = _find_matching_category(op.category, category_names)
            if not matched:
                avail = ", ".join(category_names)
                raise ValueError(
                    f"Category '{op.category}' not found in plan budget. Available: {avail}"
                )
            found_cat = next(c for c in base_plan.budget.categories if c.category == matched)
            old_amt = found_cat.allocated_amount

            if op.amount_delta is not None:
                new_amt = old_amt + op.amount_delta
                delta = op.amount_delta
            elif op.new_amount is not None:
                new_amt = op.new_amount
                delta = new_amt - old_amt
            else:
                continue

            if new_amt < Decimal("0"):
                raise ValueError(
                    f"Cannot reduce '{matched}' by ₹{abs(delta):,.0f}; "
                    f"current allocation is only ₹{old_amt:,.0f}."
                )

            # When reducing a category without explicitly changing total budget,
            # reallocate the freed funds into Contingency / Emergency Buffer.
            has_explicit_total = any(isinstance(o, SetTotalBudgetOp) for o in proposal.operations)
            if delta < 0 and not has_explicit_total:
                freed = abs(delta)
                contingency_cat = next(
                    (
                        c
                        for c in base_plan.budget.categories
                        if any(
                            w in c.category.lower() for w in ["contingency", "buffer", "reserve"]
                        )
                    ),
                    None,
                )
                cont_name = contingency_cat.category if contingency_cat else "Contingency & Reserve"
                cont_old = contingency_cat.allocated_amount if contingency_cat else Decimal("0")
                cont_new = cont_old + freed
                cont_old_share = contingency_cat.share_pct if contingency_cat else Decimal("0")
                cont_new_share = round((cont_new / old_total) * Decimal("100"), 1)

                category_deltas.append(
                    CategoryDelta(
                        category=format_category_label(matched),
                        old_amount=old_amt,
                        new_amount=new_amt,
                        delta=delta,
                        old_share_pct=found_cat.share_pct,
                        new_share_pct=round((new_amt / old_total) * Decimal("100"), 1),
                    )
                )
                category_deltas.append(
                    CategoryDelta(
                        category=format_category_label(cont_name),
                        old_amount=cont_old,
                        new_amount=cont_new,
                        delta=freed,
                        old_share_pct=cont_old_share,
                        new_share_pct=cont_new_share,
                    )
                )
                current_total = old_total
            else:
                current_total = current_total + delta
                if current_total <= Decimal("0"):
                    raise ValueError(
                        "Modification would result in non-positive total event budget."
                    )

                old_share = found_cat.share_pct
                new_share = round((new_amt / current_total) * Decimal("100"), 2)

                category_deltas.append(
                    CategoryDelta(
                        category=matched,
                        old_amount=old_amt,
                        new_amount=new_amt,
                        delta=delta,
                        old_share_pct=old_share,
                        new_share_pct=new_share,
                    )
                )

        elif isinstance(op, SetTotalBudgetOp):
            if op.new_total <= Decimal("0"):
                raise ValueError("New total budget must be positive.")
            delta = op.new_total - current_total
            current_total = op.new_total

        elif isinstance(op, AddTaskOp):
            target_d = event_date - timedelta(days=op.days_before_event)
            # Strict date check: new tasks must not be scheduled before today
            if target_d < date.today():
                target_d = date.today()

            timeline_deltas.append(
                TimelineDelta(
                    task=op.task,
                    action="added",
                    new_date=str(target_d),
                    reason=f"Added by plan proposal ({op.category}, priority {op.priority})",
                )
            )

        elif isinstance(op, RemoveTaskOp):
            matching_task = next(
                (t for t in base_plan.timeline if op.task_query.lower() in t.task.lower()), None
            )
            if matching_task:
                timeline_deltas.append(
                    TimelineDelta(
                        task=matching_task.task,
                        action="removed",
                        old_date=str(matching_task.target_date)
                        if matching_task.target_date
                        else None,
                        reason="Removed by plan proposal",
                    )
                )

        elif isinstance(op, AddVendorCategoryOp):
            vendor_changes.append(op.category)

        elif isinstance(op, SetSettingOp):
            setting_changes[op.key] = op.value

    budget_impact = current_total - old_total

    # Build clear diff summary
    summary_parts = []
    if category_deltas:
        reduced_cds = [cd for cd in category_deltas if cd.delta < 0]
        reallocated_cds = [
            cd
            for cd in category_deltas
            if cd.delta > 0
            and any(w in cd.category.lower() for w in ["contingency", "buffer", "reserve"])
        ]
        if reduced_cds and reallocated_cds:
            dest_name = reallocated_cds[0].category
            for r in reduced_cds:
                summary_parts.append(
                    f"Reduced {r.category} allocation by ₹{abs(r.delta):,.0f} "
                    f"(from ₹{r.old_amount:,.0f} to ₹{r.new_amount:,.0f}) and "
                    f"reallocated to {dest_name}. "
                    f"Total event budget remains ₹{old_total:,.0f} (unchanged)."
                )
        else:
            for cd in category_deltas:
                act = "Reduced" if cd.delta < 0 else "Increased"
                summary_parts.append(
                    f"{act} {cd.category} allocation by ₹{abs(cd.delta):,.0f} "
                    f"(from ₹{cd.old_amount:,.0f} to ₹{cd.new_amount:,.0f}). Net budget impact: "
                    f"{'-' if cd.delta < 0 else '+'}₹{abs(cd.delta):,.0f}."
                )
    if timeline_deltas:
        for td in timeline_deltas:
            summary_parts.append(f"{td.action.capitalize()} milestone task '{td.task}'.")
    if setting_changes:
        for k, v in setting_changes.items():
            summary_parts.append(f"Updated {k.replace('_', ' ')} to {v}.")
    if vendor_changes:
        summary_parts.append(f"Added vendor requirement: {', '.join(vendor_changes)}.")

    full_summary = " ".join(summary_parts) if summary_parts else proposal.explanation

    return PlanDiff(
        prompt=prompt_clean,
        summary=full_summary,
        category_changes=category_deltas,
        timeline_changes=timeline_deltas,
        setting_changes=setting_changes,
        vendor_changes=vendor_changes,
        old_total_budget=old_total,
        new_total_budget=current_total,
        budget_impact=budget_impact,
    )
