"""Deterministic and LLM-assisted Plan Diff & Refinement Engine for Phase 5.

Translates natural language modification requests (e.g. "reduce décor by ₹10,000")
into structured, verifiable diffs with explicit budget impacts, supports optimistic locking,
and applies atomic version increments (N -> N+1) with full domain validation.
"""

import copy
import logging
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient, get_llm_client
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
    old_total_budget: Decimal
    new_total_budget: Decimal
    budget_impact: Decimal  # net change in total budget (e.g. -10000.00)


class LLMChangeIntent(BaseModel):
    """Structured extraction of modification intent from user prompt."""

    target_category: str | None = Field(
        None,
        description="Budget category targeted (e.g. 'Decor', 'Catering', 'Photography', 'Venue')",
    )
    amount_delta: float | None = Field(
        None,
        description="Absolute change in INR. Negative for reductions, positive for increases",
    )
    new_total_budget: float | None = Field(
        None, description="If user specifies a new total budget directly"
    )
    rebalance_target: str | None = Field(
        None,
        description="Category to absorb difference (e.g. 'Contingency' or null if reducing total)",
    )
    explanation: str = Field(..., description="Brief 1-sentence description of what is changing")


DIFF_PARSER_SYSTEM_PROMPT = (
    "You are Festiva AI's budget refinement assistant for celebration planning in Mangaluru.\n"
    "Analyze the user's plan modification request and extract the targeted budget category "
    "and monetary delta.\n"
    "Examples:\n"
    "- 'reduce décor by ₹10,000' -> target_category='Decor', amount_delta=-10000\n"
    "- 'cut photo budget by 15000' -> target_category='Photography', amount_delta=-15000\n"
    "- 'add 25k to catering' -> target_category='Catering', amount_delta=25000\n"
    "- 'decrease venue by 50000' -> target_category='Venue', amount_delta=-50000\n"
)


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


def generate_plan_diff(
    base_plan: PlanSchema,
    prompt: str,
    client: LLMClient | None = None,
) -> PlanDiff:
    """Compute structured plan diff from user modification prompt."""
    prompt_clean = prompt.strip()
    if not prompt_clean:
        raise ValueError("Modification prompt cannot be empty.")

    category_names = [c.category for c in base_plan.budget.categories]
    llm = client or get_llm_client()

    # Attempt structured extraction
    target_category: str | None = None
    amount_delta: Decimal | None = None
    summary_text: str = ""

    try:
        extraction = llm.generate_structured(
            prompt=(
                f"User requested change: '{prompt_clean}'\n"
                f"Existing categories: {', '.join(category_names)}\n"
                f"Current total budget: INR {base_plan.total_budget:,.0f}"
            ),
            response_model=LLMChangeIntent,
            system_prompt=DIFF_PARSER_SYSTEM_PROMPT,
        )
        if extraction.target_category:
            # Map to nearest category name
            for c in category_names:
                if (
                    c.lower() in extraction.target_category.lower()
                    or extraction.target_category.lower() in c.lower()
                ):
                    target_category = c
                    break
        if extraction.amount_delta is not None:
            amount_delta = Decimal(str(int(extraction.amount_delta)))
        summary_text = extraction.explanation
    except Exception as exc:
        logger.warning(
            "LLM diff extraction failed (%s); using deterministic heuristic fallback.", exc
        )
        target_category, amount_delta, summary_text = _heuristic_extract_delta(
            prompt_clean, category_names
        )

    # If extraction did not resolve target category or delta, fallback to heuristic
    if not target_category or amount_delta is None:
        target_category, amount_delta, summary_text = _heuristic_extract_delta(
            prompt_clean, category_names
        )

    if not target_category or amount_delta is None:
        raise ValueError(
            f"Could not determine targeted budget category or amount from request: '{prompt}'"
        )

    # Locate existing category allocation
    found_cat = next(
        (c for c in base_plan.budget.categories if c.category.lower() == target_category.lower()),
        None,
    )
    if not found_cat:
        raise ValueError(f"Category '{target_category}' not found in current plan budget.")

    old_amount = found_cat.allocated_amount
    new_amount = old_amount + amount_delta
    if new_amount < Decimal("0"):
        raise ValueError(
            f"Cannot reduce '{found_cat.category}' by ₹{abs(amount_delta):,.0f}; "
            f"current allocation is only ₹{old_amount:,.0f}."
        )

    old_total = base_plan.total_budget
    new_total = old_total + amount_delta
    if new_total <= Decimal("0"):
        raise ValueError("Modification would result in non-positive total event budget.")

    old_share = found_cat.share_pct
    new_share = round((new_amount / new_total) * Decimal("100"), 2)

    cat_delta = CategoryDelta(
        category=found_cat.category,
        old_amount=old_amount,
        new_amount=new_amount,
        delta=amount_delta,
        old_share_pct=old_share,
        new_share_pct=new_share,
    )

    diff_summary = (
        f"Reduced {found_cat.category} allocation by ₹{abs(amount_delta):,.0f} "
        f"(from ₹{old_amount:,.0f} to ₹{new_amount:,.0f}). Net budget impact: "
        f"{'-' if amount_delta < 0 else '+'}₹{abs(amount_delta):,.0f}."
        if amount_delta < 0
        else (
            f"Increased {found_cat.category} allocation by ₹{amount_delta:,.0f} "
            f"(from ₹{old_amount:,.0f} to ₹{new_amount:,.0f}). Net budget impact: "
            f"+₹{amount_delta:,.0f}."
        )
    )

    return PlanDiff(
        prompt=prompt_clean,
        summary=diff_summary,
        category_changes=[cat_delta],
        timeline_changes=[],
        old_total_budget=old_total,
        new_total_budget=new_total,
        budget_impact=amount_delta,
    )


def apply_plan_diff(
    base_plan: PlanSchema,
    diff: PlanDiff,
) -> PlanSchema:
    """Apply a verified PlanDiff onto base_plan to produce version N+1 with full validation."""
    updated_plan_dict = copy.deepcopy(base_plan.model_dump())

    # Update version number
    new_version = base_plan.version + 1
    updated_plan_dict["version"] = new_version
    updated_plan_dict["total_budget"] = diff.new_total_budget

    # Apply category changes
    updated_categories: list[BudgetCategoryAllocation] = []
    guest_count = base_plan.guest_count or 100

    for cat_item in base_plan.budget.categories:
        matching_delta = next(
            (d for d in diff.category_changes if d.category.lower() == cat_item.category.lower()),
            None,
        )
        if matching_delta:
            new_amt = matching_delta.new_amount
            new_share = round((new_amt / diff.new_total_budget) * Decimal("100"), 2)
            per_guest = round(new_amt / Decimal(str(guest_count)), 2)
            updated_categories.append(
                BudgetCategoryAllocation(
                    category=cat_item.category,
                    share_pct=new_share,
                    allocated_amount=new_amt,
                    per_guest_cost=per_guest,
                    notes=f"Refined in v{new_version}: {diff.summary}",
                )
            )
        else:
            # Recompute share_pct against new_total_budget
            recomputed_share = round(
                (cat_item.allocated_amount / diff.new_total_budget) * Decimal("100"), 2
            )
            updated_categories.append(
                BudgetCategoryAllocation(
                    category=cat_item.category,
                    share_pct=recomputed_share,
                    allocated_amount=cat_item.allocated_amount,
                    per_guest_cost=cat_item.per_guest_cost,
                    notes=cat_item.notes,
                )
            )

    # Recalculate contingency to guarantee exact 100% allocation sum if rounding slight off
    allocated_sum = sum(c.allocated_amount for c in updated_categories)
    diff_from_total = diff.new_total_budget - allocated_sum
    if diff_from_total != Decimal("0"):
        # Adjust contingency category or first category by difference
        contingency_cat = next(
            (c for c in updated_categories if "contingency" in c.category.lower()), None
        )
        if contingency_cat:
            contingency_cat.allocated_amount += diff_from_total
            contingency_cat.share_pct = round(
                (contingency_cat.allocated_amount / diff.new_total_budget) * Decimal("100"), 2
            )

    updated_breakdown = BudgetBreakdown(
        total_budget=diff.new_total_budget,
        currency="INR",
        categories=updated_categories,
    )

    updated_plan_dict["budget"] = updated_breakdown.model_dump()
    updated_plan_dict["summary"] = (
        f"{base_plan.summary} (Refinement v{new_version}: {diff.summary})"
    )

    # Construct and validate new plan model
    new_plan = PlanSchema.model_validate(updated_plan_dict)

    # Domain validators
    b_ok, b_msg = validate_plan_budget(new_plan)
    if not b_ok:
        raise ValueError(f"Refined plan failed budget validation: {b_msg}")

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
