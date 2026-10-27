"""Pure Python budget allocation engine and rules validator.

Zero LLM calls. Deterministic calculations over budget rules keyed by event type,
tier, and guest count.
"""

import csv
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DEFAULT_RULES_CSV = DATA_DIR / "budget_rules.csv"


@dataclass(frozen=True)
class CategoryRule:
    event_type: str
    tier: str
    category: str
    share_pct: Decimal
    per_guest_amount: Decimal | None
    min_amount: Decimal | None


@dataclass
class CategoryAllocation:
    category: str
    share_pct: Decimal
    allocated_amount: Decimal
    per_guest_cost: Decimal | None
    is_per_guest_driven: bool
    notes: str


@dataclass
class BudgetPlan:
    event_type: str
    tier: str
    total_budget: Decimal
    guest_count: int | None
    categories: list[CategoryAllocation]
    allocated_total: Decimal

    @property
    def remaining(self) -> Decimal:
        return self.total_budget - self.allocated_total

    def to_dict(self) -> dict[str, Decimal]:
        return {cat.category: cat.allocated_amount for cat in self.categories}


def load_rules(csv_path: Path | str | None = None) -> list[CategoryRule]:
    """Parse budget rules from CSV."""
    path = Path(csv_path) if csv_path else DEFAULT_RULES_CSV
    rules: list[CategoryRule] = []

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            per_guest = (
                Decimal(row["per_guest_amount"])
                if row.get("per_guest_amount") and row["per_guest_amount"].strip()
                else None
            )
            min_amt = (
                Decimal(row["min_amount"])
                if row.get("min_amount") and row["min_amount"].strip()
                else None
            )
            rules.append(
                CategoryRule(
                    event_type=row["event_type"].strip().lower(),
                    tier=row["tier"].strip().lower(),
                    category=row["category"].strip().lower(),
                    share_pct=Decimal(row["share_pct"]),
                    per_guest_amount=per_guest,
                    min_amount=min_amt,
                )
            )
    return rules


def calculate_budget(
    event_type: str,
    total_budget: Decimal | float | int,
    guest_count: int | None = None,
    tier: str = "standard",
    rules: list[CategoryRule] | None = None,
) -> BudgetPlan:
    """Compute budget split across categories deterministically.

    1. Retrieves matching rules for (event_type, tier).
    2. If guest_count is provided and a category has per_guest_amount (e.g. catering),
       calculates catering cost based on guests and per_guest rate.
    3. Allocates remaining categories proportionally based on their share percentages.
    4. Enforces min_amount thresholds where defined.
    5. Balances the final rupee so that sum(categories) == total_budget (±1%).
    """
    total = Decimal(str(total_budget)).quantize(Decimal("1.00"))
    if total <= Decimal("0"):
        raise ValueError("Total budget must be greater than zero.")

    all_rules = rules if rules is not None else load_rules()
    matching_rules = [
        r for r in all_rules if r.event_type == event_type.lower() and r.tier == tier.lower()
    ]

    if not matching_rules:
        # Fallback to standard tier if specified tier not found
        matching_rules = [
            r for r in all_rules if r.event_type == event_type.lower() and r.tier == "standard"
        ]

    if not matching_rules:
        raise ValueError(f"No budget rules defined for event type '{event_type}'")

    allocations: list[CategoryAllocation] = []
    catering_rule = next((r for r in matching_rules if r.per_guest_amount is not None), None)

    # Determine catering allocation if guest-driven
    catering_amount = Decimal("0")
    if catering_rule and guest_count and guest_count > 0:
        catering_rate = catering_rule.per_guest_amount
        raw_catering = Decimal(guest_count) * catering_rate
        # Cap catering at max 60% of total budget to prevent starvation of venue/decor
        max_catering = (total * Decimal("0.60")).quantize(Decimal("1.00"))
        catering_amount = min(raw_catering, max_catering)
        if catering_rule.min_amount:
            catering_amount = max(catering_amount, catering_rule.min_amount)

        # Ensure catering does not exceed total budget
        catering_amount = min(catering_amount, total * Decimal("0.85"))

    # Remaining budget to distribute across non-catering categories
    non_catering_rules = [r for r in matching_rules if r != catering_rule]
    non_catering_shares_sum = sum(r.share_pct for r in non_catering_rules)

    remaining_to_distribute = total - catering_amount if catering_amount > 0 else total

    for rule in matching_rules:
        if rule == catering_rule and catering_amount > 0:
            effective_per_guest = (
                (catering_amount / Decimal(guest_count)).quantize(Decimal("1.00"))
                if guest_count
                else rule.per_guest_amount
            )
            allocations.append(
                CategoryAllocation(
                    category=rule.category,
                    share_pct=((catering_amount / total) * 100).quantize(Decimal("0.01")),
                    allocated_amount=catering_amount.quantize(Decimal("1.00")),
                    per_guest_cost=effective_per_guest,
                    is_per_guest_driven=True,
                    notes=f"Based on {guest_count} guests @ ₹{effective_per_guest}/guest",
                )
            )
        else:
            # Proportional share among remaining categories
            relative_share = rule.share_pct / non_catering_shares_sum
            amt = (remaining_to_distribute * relative_share).quantize(
                Decimal("1.00"), rounding=ROUND_HALF_UP
            )
            allocations.append(
                CategoryAllocation(
                    category=rule.category,
                    share_pct=rule.share_pct,
                    allocated_amount=amt,
                    per_guest_cost=None,
                    is_per_guest_driven=False,
                    notes=f"{rule.share_pct}% allocation",
                )
            )

    # Balance penny/rupee differences to guarantee sum(allocations) == total
    current_sum = sum(a.allocated_amount for a in allocations)
    diff = total - current_sum
    if diff != Decimal("0") and allocations:
        # Adjust largest non-guest category by the difference
        target = max(
            (a for a in allocations if not a.is_per_guest_driven),
            key=lambda a: a.allocated_amount,
            default=allocations[0],
        )
        target.allocated_amount += diff

    final_total = sum(a.allocated_amount for a in allocations)

    return BudgetPlan(
        event_type=event_type,
        tier=tier,
        total_budget=total,
        guest_count=guest_count,
        categories=allocations,
        allocated_total=final_total,
    )


def validate_budget_integrity(
    total_budget: Decimal | float | int,
    allocations: dict[str, Decimal | float | int],
    tolerance_pct: float = 1.0,
) -> bool:
    """Verify that category totals equal stated budget within ±1%."""
    total = Decimal(str(total_budget))
    allocated = sum(Decimal(str(v)) for v in allocations.values())
    if total == Decimal("0"):
        return allocated == Decimal("0")

    diff_pct = abs(allocated - total) / total * 100
    return float(diff_pct) <= tolerance_pct
