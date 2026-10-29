"""Unit tests for category label formatting and budget shares integrity."""

from decimal import Decimal

from app.domain.budget import calculate_budget, load_rules, validate_budget_shares
from app.domain.category_labels import CATEGORY_LABELS, format_category_label
from app.domain.diff_engine import apply_plan_diff, generate_plan_diff
from app.domain.plan_generator import generate_plan


def test_category_labels_no_underscores():
    """Verify that every mapped category label is human-readable and contains no underscores."""
    for raw_key, label in CATEGORY_LABELS.items():
        assert "_" not in label, f"Label '{label}' for key '{raw_key}' contains an underscore"
        assert format_category_label(raw_key) == label

    # Test arbitrary inputs with underscores
    sample_keys = [
        "decor_cake",
        "entertainment_photo",
        "venue_stage",
        "sound_light",
        "logistics_marketing",
        "makeup_attire",
        "special_effects_pyro",
    ]
    for key in sample_keys:
        formatted = format_category_label(key)
        assert "_" not in formatted, f"Formatted label '{formatted}' contains an underscore"


def test_budget_rules_csv_labels_no_underscores():
    """Verify all categories from budget_rules.csv format without underscores."""
    rules = load_rules()
    for rule in rules:
        formatted = format_category_label(rule.category)
        assert "_" not in formatted, f"Rule category '{rule.category}' formatted with underscore"


def test_calculate_budget_shares_and_labels():
    """Verify calculate_budget produces balanced shares and formatted labels have no underscores."""
    for event_type in ["wedding", "birthday", "community"]:
        for budget in [50000, 75000, 150000, 500000]:
            plan = calculate_budget(
                event_type=event_type,
                total_budget=Decimal(str(budget)),
                guest_count=80 if event_type == "birthday" else 150,
                tier="standard",
            )
            # Verify formatted labels have no underscores
            for cat in plan.categories:
                clean_lbl = format_category_label(cat.category)
                assert "_" not in clean_lbl, (
                    f"Category '{cat.category}' formatted with underscore: {clean_lbl}"
                )

            # Verify shares and amounts integrity
            is_valid, msg = validate_budget_shares(plan.total_budget, plan.categories)
            assert is_valid, f"Failed budget shares validation for {event_type} (₹{budget}): {msg}"

            # Verify sum of shares is exactly 100.0% ± 0.1%
            shares_sum = sum(c.share_pct for c in plan.categories)
            assert abs(shares_sum - Decimal("100.0")) <= Decimal("0.1")

            # Verify sum of amounts equals total budget
            amounts_sum = sum(c.allocated_amount for c in plan.categories)
            assert amounts_sum == Decimal(str(budget))


def test_generated_plan_has_no_underscores():
    """Verify generate_plan produces budget categories and timeline tasks without underscores."""
    for event_type in ["wedding", "birthday", "community"]:
        plan = generate_plan(
            event_type=event_type,
            total_budget=Decimal("100000"),
            guest_count=100,
        )
        for cat in plan.budget.categories:
            assert "_" not in cat.category, (
                f"Plan budget category '{cat.category}' contains underscore"
            )
        for task in plan.timeline:
            assert "_" not in task.category, (
                f"Plan task category '{task.category}' contains underscore"
            )
        for v in plan.vendor_shortlist:
            assert "_" not in v.category, f"Vendor category '{v.category}' contains underscore"


def test_reduce_decor_moves_money_to_contingency_and_keeps_total():
    """Verify decor reduction creates Contingency & Reserve with ₹10,000 and total unchanged."""
    base_plan = generate_plan(
        event_type="birthday",
        total_budget=Decimal("75000"),
        guest_count=80,
    )

    decor_before = next(
        c
        for c in base_plan.budget.categories
        if "décor" in c.category.lower() or "decor" in c.category.lower()
    )
    old_decor_amt = decor_before.allocated_amount

    diff = generate_plan_diff(
        base_plan=base_plan,
        prompt="reduce décor by ₹10,000",
    )

    v2_plan = apply_plan_diff(base_plan=base_plan, diff=diff)

    assert v2_plan.version == 2
    assert v2_plan.total_budget == base_plan.total_budget, "Total budget must remain unchanged"

    # Verify decor reduced by ₹10,000
    decor_after = next(
        c
        for c in v2_plan.budget.categories
        if "décor" in c.category.lower() or "decor" in c.category.lower()
    )
    assert decor_after.allocated_amount == old_decor_amt - Decimal("10000")

    # Verify contingency line exists with ₹10,000
    contingency = next(
        (c for c in v2_plan.budget.categories if "contingency" in c.category.lower()), None
    )
    assert contingency is not None, "Contingency line must be present in v2 budget"
    assert contingency.allocated_amount == Decimal("10000")
    assert "_" not in contingency.category, "Contingency category must not contain underscores"

    # Verify all categories have no underscores
    for c in v2_plan.budget.categories:
        assert "_" not in c.category, f"Category '{c.category}' contains underscores"

    # Verify budget shares validator
    ok, msg = validate_budget_shares(v2_plan.total_budget, v2_plan.budget.categories)
    assert ok, f"v2 budget shares failed validation: {msg}"
