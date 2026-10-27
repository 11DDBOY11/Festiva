"""Deterministic Plan Generator with LLM personalization and rules fallback.

Deterministic components:
- Budget engine (calculate_budget from app.domain.budget)
- Timeline counted back from event date (generate_timeline from app.domain.timeline)
- Vendor checklist & Run-of-Show (from app.domain.checklist)
- Grounded vendor shortlist (from app.domain.vendor_directory)

LLM components:
- Aesthetic theme, executive summary, menu ideas, vendor explanations.
- Pydantic-validated output with 1 repair retry, falling back to deterministic rules.

All 4 domain validators are executed prior to returning the PlanSchema.
"""

import logging
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient, get_llm_client
from app.domain.budget import calculate_budget
from app.domain.checklist import get_checklist_for_event, get_run_of_show_for_event
from app.domain.schemas import (
    BudgetBreakdown,
    BudgetCategoryAllocation,
    EventBrief,
    PlanSchema,
)
from app.domain.timeline import check_timeline_compression, generate_timeline
from app.domain.validators import (
    validate_plan_budget,
    validate_plan_dates,
    validate_price_honesty,
    validate_vendor_grounding,
)
from app.domain.vendor_directory import (
    get_known_vendor_ids,
    get_known_vendor_map,
    select_vendor_shortlist,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schema for LLM Personalisation Output
# ---------------------------------------------------------------------------


class PlanPersonalisation(BaseModel):
    """LLM output restricted to personalising theme, menu, and explanations."""

    theme: str = Field(..., description="Short aesthetic theme or vibe name")
    summary: str = Field(..., description="2-3 sentence executive plan summary")
    menu_ideas: list[str] = Field(
        default_factory=list,
        description="Regional Mangalorean dishes and specialties fitting dietary preferences",
    )
    vendor_reasons: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of category to 1-line reason why the vendor fits this event",
    )


PERSONALISATION_SYSTEM_PROMPT = (
    "You are Festiva AI's local event curator for Mangaluru, Karnataka.\n"
    "Given an event brief, budget, and guest count, suggest aesthetic themes, "
    "executive summary, and regional Mangalorean menu ideas (e.g. Neer Dosa, "
    "Kori Rotti, Udupi Saaru, Pathrode, Elaneer Payasa).\n"
    "Keep suggestions practical, culturally resonant with Dakshina Kannada, "
    "and strictly within the Pydantic schema."
)


def _get_rules_fallback_personalisation(
    event_type: str,
    guest_count: int | None,
    total_budget: Decimal,
    dietary: list[str],
) -> PlanPersonalisation:
    """Deterministic rules-only fallback for personalisation."""
    clean_type = event_type.lower()
    is_veg = any("veg" in d.lower() for d in dietary)

    if clean_type == "wedding":
        theme = "Traditional Coastal Grand Wedding"
        summary = (
            f"A traditional Mangalorean wedding celebration designed for {guest_count or 250} "
            f"guests with a total planned budget of ₹{total_budget:,.0f}. Features authentic "
            "coastal floral aesthetics, traditional ritual coordination, and banana leaf dining."
        )
        menu = (
            [
                "Traditional Udupi Saaru & Rice",
                "Kadale Manoli Sukka",
                "Neer Dosa with Chutney",
                "Elaneer Payasa & Holige",
                "Mangalorean Filter Coffee",
            ]
            if is_veg
            else [
                "Mangalorean Kori Rotti & Gassi",
                "Fish Fry / Anjal Tawa Masala",
                "Neer Dosa with Chicken Sukka",
                "Prawns Ghee Roast",
                "Elaneer Payasa & Ice Cream",
            ]
        )
    elif clean_type == "birthday":
        theme = "Golden Milestone Coastal Celebration"
        summary = (
            f"An intimate birthday gathering for {guest_count or 50} guests with an allocated "
            f"budget of ₹{total_budget:,.0f}. Balances engaging party games, custom bakery cake, "
            "and a coastal appetizer spread."
        )
        menu = [
            "Coastal Paneer / Chicken Ghee Roast Skewers",
            "Mangalore Buns & Coconut Chutney",
            "Mini Sliders & Party Crisps",
            "Custom Layered Fondant Cake",
            "Fresh Seasonal Fruit Punch",
        ]
    else:
        theme = "Dakshina Kannada Samithi Cultural Meet"
        summary = (
            f"A vibrant community cultural gathering for {guest_count or 500} participants with "
            f"a budget of ₹{total_budget:,.0f}. Focuses on sound stage setup, Yakshagana / folk "
            "performances, and mass community Anna Santharpana."
        )
        menu = [
            "Authentic Temple Anna Santharpana",
            "Traditional Udupi Sambar & Rice",
            "Beans & Moong Dal Palya",
            "Papad, Pickle & Buttermilk",
            "Boondi Ladoo Prasadam",
        ]

    return PlanPersonalisation(theme=theme, summary=summary, menu_ideas=menu, vendor_reasons={})


def _personalise_plan(
    event_type: str,
    guest_count: int | None,
    total_budget: Decimal,
    dietary: list[str],
    priorities: list[str],
    raw_brief: str | None,
    client: LLMClient | None = None,
) -> PlanPersonalisation:
    """Personalise theme and menu via LLM with 1 repair retry, falling back to rules."""
    llm = client or get_llm_client()

    is_veg = any(
        "veg" in d.lower() or "satvik" in d.lower() or "jain" in d.lower() for d in dietary
    )
    dietary_instruction = ""
    if is_veg:
        dietary_instruction = (
            "\nCRITICAL DIETARY RESTRICTION: The host specified STRICTLY VEGETARIAN catering. "
            "Every single dish in 'menu_ideas' MUST be 100% vegetarian "
            "(e.g., Neer Dosa with Veg Kurma, Udupi Saaru, Kadale Manoli Sukka, "
            "Pathrode, Moong Dal Payasa, Holige). "
            "ABSOLUTELY NO chicken, fish, prawn, meat, seafood, or Kori Rotti.\n"
        )

    user_prompt = (
        f"Event Type: {event_type}\n"
        f"Guest Count: {guest_count or 'Not specified'}\n"
        f"Total Budget: INR {total_budget:,.0f}\n"
        f"Dietary Preferences: {', '.join(dietary) if dietary else 'Standard Coastal'}\n"
        f"Priorities: {', '.join(priorities) if priorities else 'Balanced experience'}\n"
        f"User Brief Notes: {raw_brief or 'None'}\n"
        f"{dietary_instruction}\n"
        "Generate creative theme, executive summary, regional menu items, and vendor fit reasons."
    )

    non_veg_keywords = [
        "chicken",
        "fish",
        "prawn",
        "kori",
        "mutton",
        "meat",
        "pork",
        "beef",
        "seafood",
        "anjal",
        "squid",
        "crab",
    ]

    def _sanitize_menu(p: PlanPersonalisation) -> PlanPersonalisation:
        if is_veg:
            clean_menu = []
            for dish in p.menu_ideas:
                if not any(kw in dish.lower() for kw in non_veg_keywords):
                    clean_menu.append(dish)
            if not clean_menu:
                clean_menu = [
                    "Traditional Udupi Saaru & Rice",
                    "Neer Dosa with Veg Kurma",
                    "Kadale Manoli Sukka",
                    "Pathrode with Chutney",
                    "Elaneer Payasa",
                ]
            p.menu_ideas = clean_menu
        return p

    # Attempt 1
    try:
        res = llm.generate_structured(
            prompt=user_prompt,
            response_model=PlanPersonalisation,
            system_prompt=PERSONALISATION_SYSTEM_PROMPT,
        )
        return _sanitize_menu(res)
    except Exception as exc:
        logger.warning(f"Plan personalisation attempt 1 failed ({exc}); attempting repair retry...")

    # Attempt 2 (Repair retry)
    try:
        repair_prompt = (
            f"{user_prompt}\n\n"
            "IMPORTANT: Return strictly valid JSON conforming to the schema with keys: "
            "'theme', 'summary', 'menu_ideas' (list of strings), 'vendor_reasons' (dict)."
        )
        res = llm.generate_structured(
            prompt=repair_prompt,
            response_model=PlanPersonalisation,
            system_prompt=PERSONALISATION_SYSTEM_PROMPT,
        )
        return _sanitize_menu(res)
    except Exception as exc2:
        logger.warning(
            f"Plan personalisation repair retry failed ({exc2}); using rules-only fallback."
        )

    # Fallback
    return _get_rules_fallback_personalisation(event_type, guest_count, total_budget, dietary)


def generate_plan(
    brief: EventBrief | None = None,
    event_id: str | None = None,
    title: str | None = None,
    event_type: str = "wedding",
    event_date: date | None = None,
    guest_count: int | None = None,
    total_budget: Decimal | float | int | None = None,
    city: str = "Mangaluru",
    dietary_preferences: list[str] | None = None,
    priorities: list[str] | None = None,
    raw_brief: str | None = None,
    client: LLMClient | None = None,
    reference_today: date | None = None,
) -> PlanSchema:
    """Generate a complete, fully validated PlanSchema.

    Executes:
    1. Deterministic budget allocation (calculate_budget).
    2. Deterministic timeline milestones (generate_timeline).
    3. Deterministic checklist & run-of-show (get_checklist_for_event, get_run_of_show_for_event).
    4. Deterministic vendor grounding and price honesty checks (select_vendor_shortlist).
    5. LLM personalisation with retry and rules fallback.
    6. All 4 domain validators before returning.
    """
    # Normalize inputs from EventBrief if provided
    if brief:
        title = title or brief.title
        event_type = brief.event_type
        event_date = brief.event_date
        guest_count = brief.guest_count
        total_budget = brief.total_budget or total_budget
        city = brief.city or "Mangaluru"
        dietary_preferences = brief.dietary_preferences or []
        priorities = brief.priorities or []
        raw_brief = brief.raw_brief or ""

    # Ensure valid budget
    today = reference_today or date.today()
    if event_date and event_date < today:
        try:
            cand = event_date.replace(year=today.year)
            event_date = cand if cand >= today else event_date.replace(year=today.year + 1)
        except ValueError:
            event_date = today

    if total_budget is None or Decimal(str(total_budget)) <= Decimal("0"):
        # Default fallback budget if not yet supplied
        total_budget = Decimal("100000.00")
    else:
        total_budget = Decimal(str(total_budget))

    clean_type = event_type.lower().strip() if event_type else "wedding"
    if clean_type not in ["wedding", "birthday", "community"]:
        clean_type = "wedding"

    title = title or f"Mangaluru {clean_type.capitalize()} Celebration"
    dietary = dietary_preferences or []
    prios = priorities or []

    # 1. Deterministic Budget Engine
    budget_plan = calculate_budget(
        event_type=clean_type,
        total_budget=total_budget,
        guest_count=guest_count,
        tier="standard",
    )

    budget_allocations: list[BudgetCategoryAllocation] = []
    for cat in budget_plan.categories:
        budget_allocations.append(
            BudgetCategoryAllocation(
                category=cat.category.capitalize(),
                share_pct=cat.share_pct,
                allocated_amount=cat.allocated_amount,
                per_guest_cost=cat.per_guest_cost,
                notes=cat.notes,
            )
        )

    budget_breakdown = BudgetBreakdown(
        total_budget=budget_plan.total_budget,
        currency="INR",
        categories=budget_allocations,
    )

    # 2. Deterministic Timeline Generator & Compression Check
    timeline = generate_timeline(
        event_type=clean_type,
        event_date=event_date,
        reference_today=reference_today,
    )
    is_compressed, timeline_warning = check_timeline_compression(
        event_type=clean_type,
        event_date=event_date,
        reference_today=reference_today,
    )

    # 3. Deterministic Checklist & Run-of-Show
    checklist = get_checklist_for_event(clean_type)
    run_of_show = get_run_of_show_for_event(clean_type)

    # 4. Deterministic Vendor Shortlist
    budget_cat_names = [c.category for c in budget_plan.categories]
    vendor_shortlist = select_vendor_shortlist(
        categories=budget_cat_names,
        guest_count=guest_count,
    )

    # 5. LLM Personalisation (Theme, summary, menu ideas)
    personalisation = _personalise_plan(
        event_type=clean_type,
        guest_count=guest_count,
        total_budget=budget_plan.total_budget,
        dietary=dietary,
        priorities=prios,
        raw_brief=raw_brief,
        client=client,
    )

    # If LLM returned reasons for vendors, attach them
    for v in vendor_shortlist:
        vcat = v.category.lower()
        if vcat in personalisation.vendor_reasons:
            v.reason = personalisation.vendor_reasons[vcat]

    plan_summary = personalisation.summary
    if is_compressed and timeline_warning:
        plan_summary = f"{plan_summary} Note: {timeline_warning}"

    plan = PlanSchema(
        version=1,
        title=title,
        event_type=clean_type,
        event_date=event_date,
        guest_count=guest_count,
        total_budget=budget_plan.total_budget,
        currency="INR",
        summary=plan_summary,
        budget=budget_breakdown,
        timeline=timeline,
        checklist=checklist,
        run_of_show=run_of_show,
        vendor_shortlist=vendor_shortlist,
        meta={
            "city": city,
            "theme": personalisation.theme,
            "menu_ideas": personalisation.menu_ideas,
            "dietary_preferences": dietary,
            "priorities": prios,
            "compressed_timeline": is_compressed,
            "timeline_warning": timeline_warning,
        },
    )

    # 6. Run All Domain Validators
    is_budget_valid, budget_msg = validate_plan_budget(plan)
    if not is_budget_valid:
        raise ValueError(f"Plan generation failed budget validation: {budget_msg}")

    is_dates_valid, dates_msg = validate_plan_dates(plan, reference_today=reference_today)
    if not is_dates_valid:
        raise ValueError(f"Plan generation failed date validation: {dates_msg}")

    known_ids = get_known_vendor_ids()
    is_grounded, ungrounded_msgs = validate_vendor_grounding(plan, known_ids)
    if not is_grounded:
        raise ValueError(f"Plan generation failed vendor grounding: {'; '.join(ungrounded_msgs)}")

    known_map = get_known_vendor_map()
    is_honest, price_msgs = validate_price_honesty(plan, known_map)
    if not is_honest:
        raise ValueError(f"Plan generation failed price honesty: {'; '.join(price_msgs)}")

    return plan
