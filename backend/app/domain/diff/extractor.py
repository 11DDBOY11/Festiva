"""Deterministic regex extractor and fuzzy category matcher for plan changes."""

import re
from decimal import Decimal


def _find_matching_category(name: str, available: list[str]) -> str | None:
    """Case-insensitive fuzzy match for category name."""
    clean = name.lower().strip()
    for cat in available:
        c_low = cat.lower().strip()
        if clean == c_low or clean in c_low or c_low in clean:
            return cat
    return None


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
