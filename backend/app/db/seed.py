"""Database seeding script for budget rules and sample vendors."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import BudgetRule, Event, PlanVersion, ProposedChange, User, Vendor
from app.db.session import SessionLocal
from app.domain.budget import load_rules
from app.domain.diff_engine import apply_plan_diff, generate_plan_diff
from app.domain.plan_generator import generate_plan

_ROOT_DATA = Path(__file__).resolve().parent.parent.parent.parent / "data"
_APP_DATA = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR = _ROOT_DATA if _ROOT_DATA.exists() else _APP_DATA
VENDORS_JSON = DATA_DIR / "vendors.json"


def seed_budget_rules(db: Session) -> int:
    """Load budget rules from data/budget_rules.csv into budget_rules table."""
    rules = load_rules()
    count = 0
    for r in rules:
        existing = db.execute(
            select(BudgetRule).where(
                BudgetRule.event_type == r.event_type,
                BudgetRule.tier == r.tier,
                BudgetRule.category == r.category,
            )
        ).scalar_one_or_none()

        if not existing:
            br = BudgetRule(
                event_type=r.event_type,
                tier=r.tier,
                category=r.category,
                share_pct=r.share_pct,
                per_guest_amount=r.per_guest_amount,
                min_amount=r.min_amount,
            )
            db.add(br)
            count += 1
    db.commit()
    return count


def seed_vendors(db: Session) -> int:
    """Load 20 sample vendors from data/vendors.json into vendor_directory."""
    if not VENDORS_JSON.exists():
        return 0

    with open(VENDORS_JSON, encoding="utf-8") as f:
        records = json.load(f)

    count = 0
    for item in records:
        vendor_id = UUID(item["id"])
        existing = db.execute(select(Vendor).where(Vendor.id == vendor_id)).scalar_one_or_none()
        if not existing:
            v = Vendor(
                id=vendor_id,
                name=item["name"],
                category=item["category"],
                area=item["area"],
                city=item.get("city", "Mangaluru"),
                capacity_min=item.get("capacity_min"),
                capacity_max=item.get("capacity_max"),
                price_low=Decimal(str(item["price_low"])) if item.get("price_low") else None,
                price_high=Decimal(str(item["price_high"])) if item.get("price_high") else None,
                price_unit=item.get("price_unit"),
                tags=item.get("tags", []),
                source_url=item.get("source_url"),
                verified_on=item.get("verified_on"),
                confidence=item.get("confidence", "medium"),
                contact=item.get("contact"),
                sample=item.get("sample", True),
            )
            db.add(v)
            count += 1
        else:
            existing.name = item["name"]
            existing.contact = item.get("contact")
            existing.sample = item.get("sample", True)
            existing.source_url = item.get("source_url")
            count += 1
    db.commit()
    return count


def seed_demo_account(db: Session) -> bool:
    """Seed sample demo account (demo@festiva.ai) with 21st birthday event (Plan v1 & Plan v2)."""
    demo_email = "demo@festiva.ai"
    demo_user = db.execute(select(User).where(User.email == demo_email)).scalar_one_or_none()

    if not demo_user:
        demo_user = User(
            id=uuid4(),
            email=demo_email,
            name="Devraj Mangaluru (Sample Demo)",
            password_hash=hash_password("DemoFestiva2026!"),
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

    # Check if demo birthday event already exists and has plans
    demo_event = db.execute(
        select(Event).where(
            Event.owner_id == demo_user.id,
            Event.event_type == "birthday",
        )
    ).scalar_one_or_none()

    if not demo_event:
        demo_event = Event(
            id=uuid4(),
            owner_id=demo_user.id,
            title="21st Birthday Party - Mangaluru Coastal Celebration",
            event_type="birthday",
            event_date=date(2026, 11, 20),
            city="Mangaluru",
            guest_count=80,
            total_budget=Decimal("75000.00"),
            currency="INR",
            current_version=1,
            status="planning",
        )
        db.add(demo_event)
        db.commit()
        db.refresh(demo_event)

    existing_plans = (
        db.execute(select(PlanVersion).where(PlanVersion.event_id == demo_event.id)).scalars().all()
    )

    if len(existing_plans) < 2:
        # Delete existing partial plans if any
        for ep in existing_plans:
            db.delete(ep)
        db.commit()

        # Generate Plan v1
        plan_v1_schema = generate_plan(
            event_id=str(demo_event.id),
            title=demo_event.title,
            event_type=demo_event.event_type,
            event_date=demo_event.event_date,
            guest_count=demo_event.guest_count,
            total_budget=demo_event.total_budget,
            city=demo_event.city or "Mangaluru",
        )
        plan_v1_record = PlanVersion(
            id=uuid4(),
            event_id=demo_event.id,
            version=1,
            plan=plan_v1_schema.model_dump(mode="json"),
            change_summary="Initial plan for 80 guests in Mangaluru (₹75,000 budget).",
        )
        db.add(plan_v1_record)
        db.commit()

        # Generate proposal: Weather-safe and reduce decor by ₹10,000
        refine_prompt = "Rain is likely, make it weather-safe and reduce décor by ₹10,000"
        diff = generate_plan_diff(base_plan=plan_v1_schema, prompt=refine_prompt)

        prop_change = ProposedChange(
            id=uuid4(),
            event_id=demo_event.id,
            base_version=1,
            diff=diff.model_dump(mode="json"),
            budget_impact=diff.budget_impact,
            status="accepted",
        )
        db.add(prop_change)

        # Apply diff to create Plan v2
        plan_v2_schema = apply_plan_diff(base_plan=plan_v1_schema, diff=diff)
        plan_v2_record = PlanVersion(
            id=uuid4(),
            event_id=demo_event.id,
            version=2,
            plan=plan_v2_schema.model_dump(mode="json"),
            change_summary=(
                "Accepted modification: Weather-safe rain-proofing and "
                "₹10,000 decor reserve reallocated to Contingency."
            ),
        )
        db.add(plan_v2_record)

        # Update event current_version to 2
        demo_event.current_version = 2
        db.commit()
        return True

    return False


def run_seed() -> None:
    db = SessionLocal()
    try:
        rules_added = seed_budget_rules(db)
        vendors_added = seed_vendors(db)
        demo_seeded = seed_demo_account(db)
        print(
            f"Seed complete: added {rules_added} budget rules, {vendors_added} sample vendors, "
            f"demo account seeded: {demo_seeded}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
