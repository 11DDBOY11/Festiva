"""Unit tests for pure Python budget calculation engine and rules."""

from decimal import Decimal

import pytest

from app.domain.budget import (
    calculate_budget,
    load_rules,
    validate_budget_integrity,
)


def test_load_budget_rules() -> None:
    rules = load_rules()
    assert len(rules) >= 20
    event_types = {r.event_type for r in rules}
    assert "wedding" in event_types
    assert "birthday" in event_types
    assert "community" in event_types


def test_wedding_budget_allocation() -> None:
    total_budget = Decimal("1500000.00")  # 15 Lakhs
    guest_count = 250
    plan = calculate_budget(
        event_type="wedding",
        total_budget=total_budget,
        guest_count=guest_count,
        tier="standard",
    )

    # Budget integrity target: category totals equal stated budget exactly (±1%)
    assert plan.allocated_total == total_budget
    assert validate_budget_integrity(total_budget, plan.to_dict())

    # Check that catering and venue exist
    cats = {c.category: c.allocated_amount for c in plan.categories}
    assert "catering" in cats
    assert "venue" in cats
    assert "decor" in cats
    assert cats["catering"] > Decimal("100000")


def test_birthday_budget_allocation_edge_case() -> None:
    """Birthday demo test: 80 guests, ₹75,000 budget."""
    total_budget = Decimal("75000.00")
    guest_count = 80
    plan = calculate_budget(
        event_type="birthday",
        total_budget=total_budget,
        guest_count=guest_count,
        tier="standard",
    )

    assert plan.allocated_total == total_budget
    assert validate_budget_integrity(total_budget, plan.to_dict())
    cats = {c.category: c.allocated_amount for c in plan.categories}
    assert "decor_cake" in cats
    assert "venue" in cats


def test_community_event_budget_allocation() -> None:
    total_budget = Decimal("200000.00")
    plan = calculate_budget(
        event_type="community",
        total_budget=total_budget,
        guest_count=300,
        tier="economy",
    )

    assert plan.allocated_total == total_budget
    assert validate_budget_integrity(total_budget, plan.to_dict())


def test_validate_budget_integrity() -> None:
    allocations = {
        "venue": 30000,
        "catering": 40000,
        "decor": 30000,
    }
    assert validate_budget_integrity(100000, allocations)
    # 0.5% difference within 1% tolerance
    assert validate_budget_integrity(100500, allocations, tolerance_pct=1.0)
    # 5% difference fails
    assert not validate_budget_integrity(95000, allocations, tolerance_pct=1.0)


def test_invalid_budget_inputs() -> None:
    with pytest.raises(ValueError, match="Total budget must be greater than zero"):
        calculate_budget(event_type="wedding", total_budget=0)

    with pytest.raises(ValueError, match="No budget rules defined"):
        calculate_budget(event_type="nonexistent_type", total_budget=50000)
