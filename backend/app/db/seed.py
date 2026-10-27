"""Database seeding script for budget rules and sample vendors."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BudgetRule, Vendor
from app.db.session import SessionLocal
from app.domain.budget import load_rules

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
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
            )
            db.add(v)
            count += 1
    db.commit()
    return count


def run_seed() -> None:
    db = SessionLocal()
    try:
        rules_added = seed_budget_rules(db)
        vendors_added = seed_vendors(db)
        print(f"Seed complete: added {rules_added} budget rules, {vendors_added} sample vendors.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
