"""Live evaluation of LLM Plan Personalisation across 10 distinct event scenarios.

Verifies:
1. Vendor Grounding: Zero invented vendor names or IDs (100% matched to vendors.json).
2. Price Honesty: Zero invented rates or prices (strictly within catalog ranges).
3. Dietary Constraints: Pure-veg events strictly contain vegetarian menus (no poultry/seafood/meat).
4. Compressed Timeline: Events under normal lead times flag compressed timeline advisories.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.llm_client import GroqLLMClient  # noqa: E402
from app.domain.plan_generator import generate_plan  # noqa: E402
from app.domain.validators import (  # noqa: E402
    validate_price_honesty,
    validate_vendor_grounding,
)
from app.domain.vendor_directory import get_known_vendor_ids, get_known_vendor_map  # noqa: E402

NON_VEG_KEYWORDS = [
    "chicken",
    "fish",
    "prawn",
    "anjal",
    "kori",
    "mutton",
    "meat",
    "pork",
    "beef",
    "seafood",
    "crab",
    "squid",
]

TEST_SCENARIOS = [
    {
        "id": "live_plan_01",
        "name": "Standard Coastal Wedding",
        "type": "wedding",
        "guests": 250,
        "budget": Decimal("1500000.00"),
        "dietary": ["Traditional Coastal", "Non-Veg", "Seafood"],
        "days": 120,
        "expect_pure_veg": False,
    },
    {
        "id": "live_plan_02",
        "name": "Udupi Brahmin Wedding (Pure Veg)",
        "type": "wedding",
        "guests": 300,
        "budget": Decimal("800000.00"),
        "dietary": ["Pure Veg", "Udupi Style", "Satvik"],
        "days": 90,
        "expect_pure_veg": True,
    },
    {
        "id": "live_plan_03",
        "name": "Milestone 50th Birthday Dinner",
        "type": "birthday",
        "guests": 60,
        "budget": Decimal("120000.00"),
        "dietary": ["Coastal Seafood & Starters"],
        "days": 25,
        "expect_pure_veg": False,
    },
    {
        "id": "live_plan_04",
        "name": "Kids 1st Birthday (Vegetarian Snacks)",
        "type": "birthday",
        "guests": 40,
        "budget": Decimal("50000.00"),
        "dietary": ["Vegetarian Only", "Kid Friendly"],
        "days": 18,
        "expect_pure_veg": True,
    },
    {
        "id": "live_plan_05",
        "name": "Community Cultural Samithi Fest",
        "type": "community",
        "guests": 500,
        "budget": Decimal("300000.00"),
        "dietary": ["Temple Anna Santharpana", "Pure Veg"],
        "days": 40,
        "expect_pure_veg": True,
    },
    {
        "id": "live_plan_06",
        "name": "Beachside Destination Wedding",
        "type": "wedding",
        "guests": 180,
        "budget": Decimal("2500000.00"),
        "dietary": ["Seafood BBQ", "Coastal Fusion"],
        "days": 150,
        "expect_pure_veg": False,
    },
    {
        "id": "live_plan_07",
        "name": "Yakshagana & Youth Sports Meet",
        "type": "community",
        "guests": 200,
        "budget": Decimal("100000.00"),
        "dietary": ["Pure Veg", "Banana Leaf Meal"],
        "days": 15,
        "expect_pure_veg": True,
    },
    {
        "id": "live_plan_08",
        "name": "Silver Jubilee Anniversary Dinner",
        "type": "wedding",
        "guests": 70,
        "budget": Decimal("200000.00"),
        "dietary": ["Vegetarian", "Jain Friendly"],
        "days": 30,
        "expect_pure_veg": True,
    },
    {
        "id": "live_plan_09",
        "name": "Rush Birthday Party (10 Days Away)",
        "type": "birthday",
        "guests": 30,
        "budget": Decimal("75000.00"),
        "dietary": ["Mixed Appetizers"],
        "days": 10,
        "expect_pure_veg": False,
    },
    {
        "id": "live_plan_10",
        "name": "Grand Community Devotee Feast",
        "type": "community",
        "guests": 1000,
        "budget": Decimal("450000.00"),
        "dietary": ["Pure Vegetarian Anna Dhanam"],
        "days": 20,
        "expect_pure_veg": True,
    },
]


def run_personalisation_evals() -> int:
    """Run live personalisation verification on 10 generated plans."""
    print("\n" + "=" * 96)
    print("LIVE PERSONALISATION EVALUATION (10 GENERATED PLANS)")
    print("=" * 96)

    try:
        client = GroqLLMClient()
        print(f"[INFO] Using live GroqLLMClient (Model: {client.model})")
    except Exception as exc:
        print(f"[FATAL] Cannot initialize GroqLLMClient: {exc}")
        return 1

    known_ids = get_known_vendor_ids()
    known_map = get_known_vendor_map()
    today = date.today()

    total_plans = len(TEST_SCENARIOS)
    passed_grounding = 0
    passed_honesty = 0
    passed_dietary = 0
    passed_timeline = 0
    total_passed = 0

    results = []

    for sc in TEST_SCENARIOS:
        sc_id = sc["id"]
        name = sc["name"]
        ev_date = today + timedelta(days=sc["days"])

        try:
            plan = generate_plan(
                event_type=sc["type"],
                total_budget=sc["budget"],
                guest_count=sc["guests"],
                event_date=ev_date,
                dietary_preferences=sc["dietary"],
                client=client,
                reference_today=today,
            )

            # 1. Vendor Grounding
            grounded, g_errs = validate_vendor_grounding(plan, known_ids)
            if grounded:
                passed_grounding += 1

            # 2. Price Honesty
            honest, h_errs = validate_price_honesty(plan, known_map)
            if honest:
                passed_honesty += 1

            # 3. Dietary Preferences
            menu_ideas = plan.meta.get("menu_ideas", [])
            dietary_ok = True
            dietary_notes = []
            if sc["expect_pure_veg"]:
                for dish in menu_ideas:
                    lower_dish = dish.lower()
                    for kw in NON_VEG_KEYWORDS:
                        if kw in lower_dish:
                            dietary_ok = False
                            dietary_notes.append(f"Dish '{dish}' contains '{kw}'")
            if dietary_ok:
                passed_dietary += 1

            # 4. Compressed Timeline Check
            compressed_ok = True
            # wedding normal > 60d, birthday > 30d, community > 60d
            expected_compressed = (
                (sc["type"] == "wedding" and sc["days"] < 180)
                or (sc["type"] == "birthday" and sc["days"] < 30)
                or (sc["type"] == "community" and sc["days"] < 60)
            )
            actual_compressed = plan.meta.get("compressed_timeline", False)
            if expected_compressed != actual_compressed:
                compressed_ok = False
            if compressed_ok:
                passed_timeline += 1

            all_ok = grounded and honest and dietary_ok and compressed_ok
            if all_ok:
                total_passed += 1

            status_str = "PASS" if all_ok else "FAIL"
            notes = []
            if g_errs:
                notes.extend(g_errs)
            if h_errs:
                notes.extend(h_errs)
            if dietary_notes:
                notes.extend(dietary_notes)

            results.append(
                (sc_id, name, grounded, honest, dietary_ok, actual_compressed, status_str, notes)
            )

        except Exception as err:
            results.append((sc_id, name, False, False, False, False, "ERROR", [str(err)]))

    print("\n" + "=" * 90)
    print(
        f"{'ID':<14} {'Scenario':<30} {'Grounding':<10} {'Honesty':<9} "
        f"{'Dietary':<9} {'Timeline':<10} {'Result'}"
    )
    print("=" * 90)
    for sc_id, name, g, h, d, comp, res, notes in results:
        print(
            f"{sc_id:<14} {name[:28]:<30} "
            f"{'YES' if g else 'NO':<10} "
            f"{'YES' if h else 'NO':<9} "
            f"{'ACCURATE' if d else 'FAIL':<9} "
            f"{'COMPRESSED' if comp else 'NORMAL':<10} "
            f"{res}"
        )
        if notes:
            for n in notes:
                print(f"   |-> Note: {n}")

    print("=" * 90)
    print("PERSONALISATION EVALUATION SUMMARY:")
    print(f"  - Total Plans Tested:             {total_plans}")
    g_pct = passed_grounding / total_plans * 100
    h_pct = passed_honesty / total_plans * 100
    d_pct = passed_dietary / total_plans * 100
    t_pct = passed_timeline / total_plans * 100
    pass_pct = total_passed / total_plans * 100
    print(f"  - Zero Invented Vendors (100%):   {passed_grounding}/{total_plans} ({g_pct:.1f}%)")
    print(f"  - Zero Invented Prices (100%):    {passed_honesty}/{total_plans} ({h_pct:.1f}%)")
    print(f"  - Dietary Constraint Adherence:   {passed_dietary}/{total_plans} ({d_pct:.1f}%)")
    print(f"  - Compressed Timeline Detection:  {passed_timeline}/{total_plans} ({t_pct:.1f}%)")
    print(f"  - Overall Flawless Pass Rate:     {total_passed}/{total_plans} ({pass_pct:.1f}%)")
    print("=" * 90 + "\n")

    return 0 if total_passed == total_plans else 1


if __name__ == "__main__":
    code = run_personalisation_evals()
    sys.exit(code)
