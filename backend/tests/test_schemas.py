"""Unit tests for EventBrief, PlanSchema, and domain validators."""

from datetime import date, timedelta
from decimal import Decimal

from app.domain.schemas import (
    BudgetBreakdown,
    BudgetCategoryAllocation,
    ChecklistQuestion,
    EventBrief,
    PlanSchema,
    RunOfShowSlot,
    TimelineItem,
    VendorRecommendation,
)
from app.domain.validators import (
    validate_plan_budget,
    validate_plan_dates,
    validate_price_honesty,
    validate_vendor_grounding,
)


def test_event_brief_model() -> None:
    brief = EventBrief(
        title="Priya & Rahul Wedding",
        event_type="Wedding",
        city="Mangaluru",
        guest_count=250,
        total_budget=Decimal("1500000.00"),
        priorities=["Grand mandap", "Coastal sea food"],
        constraints=["Rain-proof venue"],
    )
    assert brief.event_type == "wedding"
    assert brief.city == "Mangaluru"
    assert brief.guest_count == 250
    assert brief.total_budget == Decimal("1500000.00")


def _build_sample_plan(event_date: date, total_budget: Decimal) -> PlanSchema:
    return PlanSchema(
        title="21st Birthday Celebration",
        event_type="birthday",
        event_date=event_date,
        total_budget=total_budget,
        summary="A celebration plan in Mangaluru",
        budget=BudgetBreakdown(
            total_budget=total_budget,
            categories=[
                BudgetCategoryAllocation(
                    category="venue",
                    share_pct=Decimal("30.0"),
                    allocated_amount=total_budget * Decimal("0.30"),
                ),
                BudgetCategoryAllocation(
                    category="catering",
                    share_pct=Decimal("40.0"),
                    allocated_amount=total_budget * Decimal("0.40"),
                ),
                BudgetCategoryAllocation(
                    category="decor",
                    share_pct=Decimal("30.0"),
                    allocated_amount=total_budget * Decimal("0.30"),
                ),
            ],
        ),
        timeline=[
            TimelineItem(
                phase="2 weeks before",
                days_before_event=14,
                target_date=event_date - timedelta(days=14),
                task="Book venue",
                category="venue",
            ),
            TimelineItem(
                phase="1 week before",
                days_before_event=7,
                target_date=event_date - timedelta(days=7),
                task="Confirm catering menu",
                category="catering",
            ),
        ],
        checklist=[
            ChecklistQuestion(
                category="venue",
                item="Sound permit",
                questions_to_ask_vendor=["What is the 10 PM sound curfew?"],
            )
        ],
        run_of_show=[
            RunOfShowSlot(
                time_slot="18:00 - 19:00",
                activity="Guest arrival",
                location="Lawn",
                lead_person="Host",
            )
        ],
    )


def test_plan_budget_validator() -> None:
    plan = _build_sample_plan(date.today() + timedelta(days=30), Decimal("100000.00"))
    valid, msg = validate_plan_budget(plan)
    assert valid
    assert "verified" in msg

    # Corrupt category amount
    plan.budget.categories[0].allocated_amount = Decimal("50000.00")
    valid, msg = validate_plan_budget(plan)
    assert not valid
    assert "Budget mismatch" in msg


def test_plan_dates_validator() -> None:
    today = date.today()
    event_date = today + timedelta(days=20)
    plan = _build_sample_plan(event_date, Decimal("50000.00"))

    # Valid chronological dates
    valid, msg = validate_plan_dates(plan, reference_today=today)
    assert valid

    # Event date in past
    plan.event_date = today - timedelta(days=1)
    valid, msg = validate_plan_dates(plan, reference_today=today)
    assert not valid
    assert "in the past" in msg

    # Timeline date out of order
    plan.event_date = event_date
    plan.timeline[0].target_date = event_date - timedelta(days=2)
    plan.timeline[1].target_date = event_date - timedelta(days=10)
    valid, msg = validate_plan_dates(plan, reference_today=today)
    assert not valid
    assert "chronological order" in msg


def test_vendor_grounding_validator() -> None:
    plan = _build_sample_plan(date.today() + timedelta(days=30), Decimal("100000.00"))
    plan.vendor_shortlist = [
        VendorRecommendation(
            category="venue",
            vendor_id="e1a2b3c4-0001-4000-8000-000000000001",
            vendor_name="TMA Pai Centre",
            is_grounded=True,
            reason="Fits capacity and budget",
        ),
        VendorRecommendation(
            category="photographer",
            vendor_id="unknown-vendor-id-9999",
            vendor_name="Ghost Photography",
            is_grounded=True,
            reason="Hallucinated vendor",
        ),
    ]

    known_ids = {"e1a2b3c4-0001-4000-8000-000000000001"}
    valid, errors = validate_vendor_grounding(plan, known_ids)
    assert not valid
    assert len(errors) == 1
    assert "Ghost Photography" in errors[0]


def test_price_honesty_validator() -> None:
    plan = _build_sample_plan(date.today() + timedelta(days=30), Decimal("100000.00"))
    plan.vendor_shortlist = [
        VendorRecommendation(
            category="decorator",
            vendor_id="e1a2b3c4-0008-4000-8000-000000000008",
            vendor_name="Mystery Decorator",
            price_status="confirmed",
            reason="Decorator with unknown price",
        )
    ]

    # Vendor in map with no price record
    known_map = {
        "e1a2b3c4-0008-4000-8000-000000000008": {
            "name": "Mystery Decorator",
            "price_low": None,
            "price_high": None,
        }
    }
    valid, errors = validate_price_honesty(plan, known_map)
    assert not valid
    assert len(errors) == 1
    assert "has no price record" in errors[0]
