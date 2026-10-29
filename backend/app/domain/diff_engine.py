"""Deterministic and LLM-assisted Plan Diff & Refinement Engine for Phase 5.

Translates natural language modification requests (e.g. "reduce décor by ₹10,000",
"make it weather-safe", "add a kids' zone", "swap to a South Indian theme")
into a validated list of allowed operations, supports optimistic locking with 1-shot rebase,
and applies atomic version increments (N -> N+1) with full domain validation.
"""

import copy
import logging
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient, get_llm_client
from app.domain.category_labels import format_category_label
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

logger = logging.getLogger(__name__)


class UnsupportedOperationError(ValueError):
    """Raised when a user requests an operation Festiva cannot perform."""

    pass


# ---------------------------------------------------------------------------
# Allowed Operation Schemas (Pydantic)
# ---------------------------------------------------------------------------


class AdjustCategoryOp(BaseModel):
    op: Literal["adjust_category"] = "adjust_category"
    category: str = Field(
        ...,
        description="Target budget category name, e.g. 'Decor', 'Catering', 'Photography', 'Venue'",
    )
    amount_delta: Decimal | None = Field(
        None,
        description="Change in INR (negative for reductions, positive for increases)",
    )
    new_amount: Decimal | None = Field(
        None,
        description="Target absolute allocation amount in INR",
    )


class SetTotalBudgetOp(BaseModel):
    op: Literal["set_total_budget"] = "set_total_budget"
    new_total: Decimal = Field(..., description="New total event budget in INR")


class AddTaskOp(BaseModel):
    op: Literal["add_task"] = "add_task"
    task: str = Field(..., description="Clear title/description of the milestone task to add")
    category: str = Field(
        default="Planning", description="Task category, e.g. 'Venue', 'Decor', 'Entertainment'"
    )
    days_before_event: int = Field(
        default=7, ge=0, description="Days before event date to complete"
    )
    priority: str = Field(default="medium", description="Priority level: high, medium, low")


class RemoveTaskOp(BaseModel):
    op: Literal["remove_task"] = "remove_task"
    task_query: str = Field(
        ..., description="Search phrase or title of the timeline task to remove"
    )


class AddVendorCategoryOp(BaseModel):
    op: Literal["add_vendor_category"] = "add_vendor_category"
    category: str = Field(
        ..., description="Vendor category to add, e.g. 'Weather Protection', 'Kids Entertainment'"
    )
    suggested_vendor: str | None = Field(None, description="Optional vendor name if suggested")


class SetSettingOp(BaseModel):
    op: Literal["set_setting"] = "set_setting"
    key: Literal["weather_safe", "kids_zone", "theme", "dietary_preferences"] = Field(
        ...,
        description="Setting key: weather_safe, kids_zone, theme, or dietary_preferences",
    )
    value: str = Field(
        ..., description="Setting value (e.g. 'true', 'Traditional South Indian & Coastal')"
    )


PlanOp = Annotated[
    AdjustCategoryOp
    | SetTotalBudgetOp
    | AddTaskOp
    | RemoveTaskOp
    | AddVendorCategoryOp
    | SetSettingOp,
    Field(discriminator="op"),
]


class LLMPlanProposal(BaseModel):
    """Structured extraction of modification intent from user prompt."""

    explanation: str = Field(..., description="Brief 1-sentence summary of what is changing")
    operations: list[PlanOp] = Field(
        default_factory=list, description="Validated list of allowed operations to apply"
    )
    unsupported_request: str | None = Field(
        None,
        description="If request is unsupported (e.g. flights/crypto), state reason why",
    )


# ---------------------------------------------------------------------------
# Plan Diff Models
# ---------------------------------------------------------------------------


class CategoryDelta(BaseModel):
    category: str
    old_amount: Decimal
    new_amount: Decimal
    delta: Decimal
    old_share_pct: Decimal | None = None
    new_share_pct: Decimal | None = None


class TimelineDelta(BaseModel):
    task: str
    action: str  # added | modified | removed
    old_date: str | None = None
    new_date: str | None = None
    reason: str | None = None


class PlanDiff(BaseModel):
    prompt: str
    summary: str
    category_changes: list[CategoryDelta] = Field(default_factory=list)
    timeline_changes: list[TimelineDelta] = Field(default_factory=list)
    setting_changes: dict[str, Any] = Field(default_factory=dict)
    vendor_changes: list[str] = Field(default_factory=list)
    old_total_budget: Decimal
    new_total_budget: Decimal
    budget_impact: Decimal  # net change in total budget (e.g. -10000.00)


PROPOSAL_SYSTEM_PROMPT = """You are Festiva AI's plan modification specialist in Mangaluru.
Translate the user's free text modification request into a validated list of allowed operations.

Allowed operations:
1. "adjust_category": modify budget for an existing category (category, amount_delta, new_amount)
2. "set_total_budget": set overall event budget (new_total)
3. "add_task": add a milestone task (task, category, days_before_event, priority)
4. "remove_task": remove a timeline task matching task_query
5. "add_vendor_category": add a vendor requirement (category, suggested_vendor)
6. "set_setting": update plan settings (key: weather_safe/kids_zone/theme, value: string)

Special request mappings:
- "make it weather-safe":
  * set_setting(key="weather_safe", value="true")
  * add_task(task="Arrange water-proof monsoon canopy and backup area", category="Venue")
  * add_vendor_category(category="Weather Protection / Canopy Rentals")
- "add a kids' zone":
  * set_setting(key="kids_zone", value="true")
  * add_task(task="Set up dedicated kids activity and craft play area", category="Entertainment")
  * add_vendor_category(category="Kids Entertainment & Magic Shows")
- "swap to a South Indian theme":
  * set_setting(key="theme", value="Traditional South Indian & Coastal Heritage")
  * add_task(task="Coordinate traditional South Indian floral decor", category="Decor")

Rules:
- For unsupported requests (e.g. flights, crypto, gambling, live animals):
  set unsupported_request to "Can't do that yet: Festiva does not support <reason>".
- Never invent unauthorized categories or arbitrary operations outside the allowed list.
"""


def _heuristic_extract_delta(
    prompt: str, current_categories: list[str]
) -> tuple[str | None, Decimal | None, str]:
    """Fallback regex extractor for common change patterns like 'reduce décor by ₹10,000'."""
    lower = prompt.lower()
    is_reduction = any(
        w in lower for w in ["reduce", "cut", "decrease", "lower", "less", "trim", "minus"]
    )

    # Detect category
    matched_cat = None
    for cat in current_categories:
        clean_cat = cat.lower().replace("&", "").strip()
        tokens = [clean_cat]
        if "decor" in clean_cat or "décor" in clean_cat:
            tokens.extend(["decor", "décor", "decoration", "flowers", "cake"])
        elif "cater" in clean_cat or "food" in clean_cat:
            tokens.extend(["catering", "caterer", "food", "menu"])
        elif "photo" in clean_cat:
            tokens.extend(["photo", "photography", "photographer", "camera"])
        elif "venue" in clean_cat:
            tokens.extend(["venue", "hall", "ground", "resort", "stage"])
        elif "sound" in clean_cat:
            tokens.extend(["sound", "light", "lighting", "entertainment", "music", "dj"])
        elif "logistics" in clean_cat:
            tokens.extend(["logistics", "marketing", "transport", "invites"])
        elif "refreshment" in clean_cat:
            tokens.extend(["refreshment", "refreshments", "snacks", "drinks"])
        elif "contingency" in clean_cat:
            tokens.extend(["contingency", "buffer"])

        if any(tok in lower for tok in tokens):
            matched_cat = cat
            break

    # Extract monetary amount
    amount = None
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l\b)", lower)
    if lakh_match:
        amount = Decimal(str(int(float(lakh_match.group(1)) * 100000)))
    else:
        k_match = re.search(r"(\d+)\s*k\b", lower)
        if k_match:
            amount = Decimal(str(int(k_match.group(1)) * 1000))
        else:
            num_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+)", lower)
            if num_match:
                clean_num = num_match.group(1).replace(",", "")
                if clean_num.isdigit() and int(clean_num) > 0:
                    amount = Decimal(clean_num)

    if amount and is_reduction:
        amount = -amount

    desc = (
        f"Adjusted {matched_cat or 'budget'} by ₹{abs(amount or 0):,.0f}"
        if matched_cat
        else "Plan modification"
    )
    return matched_cat, amount, desc


def _find_matching_category(name: str, available: list[str]) -> str | None:
    """Case-insensitive fuzzy match for category name."""
    clean = name.lower().strip()
    for cat in available:
        c_low = cat.lower().strip()
        if clean == c_low or clean in c_low or c_low in clean:
            return cat
    return None


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
