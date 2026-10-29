"""Central category label definitions and formatting helpers.

Guarantees human-readable display labels across UI, PDF export, and diff engine.
Enforces that no displayed category label contains underscores.
"""

CATEGORY_LABELS: dict[str, str] = {
    # Wedding categories
    "venue": "Venue",
    "catering": "Catering",
    "decor": "Decor",
    "décor": "Decor",
    "photography": "Photography",
    "makeup_attire": "Makeup & Attire",
    "makeup & attire": "Makeup & Attire",
    "sound_entertainment": "Sound & Entertainment",
    "sound & entertainment": "Sound & Entertainment",
    # Birthday categories
    "decor_cake": "Decor & Custom Cake",
    "décor_cake": "Decor & Custom Cake",
    "decor & custom cake": "Decor & Custom Cake",
    "décor & custom cake": "Decor & Custom Cake",
    "entertainment_photo": "Entertainment & Photography",
    "entertainment & photography": "Entertainment & Photography",
    # Community event categories
    "venue_stage": "Venue & Stage",
    "venue & stage": "Venue & Stage",
    "sound_light": "Sound & Lighting",
    "sound & lighting": "Sound & Lighting",
    "refreshments": "Refreshments",
    "logistics_marketing": "Logistics & Marketing",
    "logistics & marketing": "Logistics & Marketing",
    # Dynamic/Refinement categories
    "contingency": "Contingency & Reserve",
    "contingency / emergency buffer": "Contingency & Reserve",
    "contingency & reserve": "Contingency & Reserve",
    "weather protection / canopy rentals": "Weather Protection & Canopy",
    "weather protection & canopy": "Weather Protection & Canopy",
    "kids entertainment & magic shows": "Kids Entertainment & Magic Shows",
}


def format_category_label(key: str | None) -> str:
    """Format an internal category key into a clean, human-readable display label.

    Always replaces underscores and maps known keys to standard display titles.
    Guarantees the return value contains no underscores.
    """
    if not key:
        return ""

    raw = str(key).strip()
    norm = raw.lower().replace("&amp;", "&")

    if norm in CATEGORY_LABELS:
        return CATEGORY_LABELS[norm]

    # Clean up underscores and slashes
    clean = raw.replace("_", " ").replace("/", " & ")
    # Capitalize words nicely while keeping minor connector words lowercase
    words = clean.split()
    formatted_words = []
    for w in words:
        if w.lower() in ("and", "of", "the", "for", "in", "to", "on"):
            formatted_words.append("&" if w.lower() == "and" else w.lower())
        else:
            formatted_words.append(w.capitalize())

    result = " ".join(formatted_words).strip()
    result = result.replace("& &", "&").replace("  ", " ")
    if result.startswith("& "):
        result = result[2:]
    return result.replace("_", " ")
