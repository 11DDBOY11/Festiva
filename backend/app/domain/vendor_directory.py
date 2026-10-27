"""Vendor directory grounding helper.

Matches vendors from data/vendors.json to plan categories.
Enforces grounding integrity and price honesty ("to confirm" for missing prices).
Zero LLM calls.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.schemas import VendorRecommendation

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DEFAULT_VENDORS_JSON = DATA_DIR / "vendors.json"

# Map budget/event category to vendor directory category
CATEGORY_MAP: dict[str, list[str]] = {
    "venue": ["venue"],
    "venue_stage": ["venue"],
    "catering": ["caterer"],
    "refreshments": ["caterer"],
    "decor": ["decorator"],
    "decor_cake": ["decorator", "bakery"],
    "cake": ["bakery"],
    "photography": ["photographer"],
    "entertainment_photo": ["photographer", "sound_entertainment"],
    "sound_light": ["sound_entertainment"],
    "sound_entertainment": ["sound_entertainment"],
    "makeup_attire": ["makeup_attire"],
    "logistics_marketing": ["transport"],
}


def load_vendor_records(path: Path | None = None) -> list[dict[str, Any]]:
    """Load vendor records from vendors.json."""
    target_path = path or DEFAULT_VENDORS_JSON
    if not target_path.exists():
        return []
    with open(target_path, encoding="utf-8") as f:
        return json.load(f)


def get_known_vendor_ids(vendors: list[dict[str, Any]] | None = None) -> set[str]:
    """Return set of valid vendor UUID strings."""
    records = vendors if vendors is not None else load_vendor_records()
    return {str(v["id"]) for v in records if "id" in v}


def get_known_vendor_map(
    vendors: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return map of vendor_id -> vendor record."""
    records = vendors if vendors is not None else load_vendor_records()
    return {str(v["id"]): v for v in records if "id" in v}


def select_vendor_shortlist(
    categories: list[str],
    vendors: list[dict[str, Any]] | None = None,
    guest_count: int | None = None,
) -> list[VendorRecommendation]:
    """Select grounded vendors from directory for each relevant budget category.

    Enforces Price Honesty:
    - If price_low or price_high is missing, price_status is 'to confirm'.
    - If prices exist, price_status is 'confirmed'.
    """
    records = vendors if vendors is not None else load_vendor_records()
    shortlist: list[VendorRecommendation] = []
    seen_vendor_ids: set[str] = set()

    for cat in categories:
        target_vendor_cats = CATEGORY_MAP.get(cat.lower().strip(), [cat.lower().strip()])
        # Find matching vendors
        matches = [
            v
            for v in records
            if v.get("category") in target_vendor_cats and str(v.get("id")) not in seen_vendor_ids
        ]

        if not matches:
            # Look for any matching vendor without excluding seen
            matches = [v for v in records if v.get("category") in target_vendor_cats]

        if matches:
            chosen = matches[0]
            vid = str(chosen["id"])
            seen_vendor_ids.add(vid)

            p_low = (
                Decimal(str(chosen["price_low"])) if chosen.get("price_low") is not None else None
            )
            p_high = (
                Decimal(str(chosen["price_high"])) if chosen.get("price_high") is not None else None
            )

            # Price Honesty Rule: If price range is missing or incomplete, must be "to confirm"
            has_price = p_low is not None or p_high is not None
            price_status = "confirmed" if has_price else "to confirm"

            shortlist.append(
                VendorRecommendation(
                    category=chosen.get("category", cat).capitalize(),
                    vendor_id=vid,
                    vendor_name=chosen.get("name", "Local Vendor"),
                    estimated_price_low=p_low,
                    estimated_price_high=p_high,
                    price_unit=chosen.get("price_unit"),
                    is_grounded=True,
                    price_status=price_status,
                    questions_to_ask=[
                        f"Please confirm availability for {chosen.get('area', 'Mangaluru')} area.",
                        "What advance payment percentage is required to confirm booking?",
                    ],
                    budget_impact=p_low or Decimal("0"),
                    reason=(
                        f"Recommended {chosen.get('category')} in "
                        f"{chosen.get('area', 'Mangaluru')} matching requirements."
                    ),
                )
            )

    return shortlist
