/**
 * Category labels and formatting constants for Festiva.
 * Enforces human-readable category names across the application.
 */

export const CATEGORY_LABELS: Record<string, string> = {
  // Wedding categories
  venue: "Venue",
  catering: "Catering",
  decor: "Décor",
  photography: "Photography",
  makeup_attire: "Makeup & Attire",
  sound_entertainment: "Sound & Entertainment",

  // Birthday categories
  decor_cake: "Décor & Custom Cake",
  entertainment_photo: "Entertainment & Photography",

  // Community event categories
  venue_stage: "Venue & Stage",
  sound_light: "Sound & Lighting",
  refreshments: "Refreshments",
  logistics_marketing: "Logistics & Marketing",

  // Dynamic / Refinement categories
  contingency: "Contingency & Reserve",
  "contingency / emergency buffer": "Contingency & Reserve",
  "contingency & reserve": "Contingency & Reserve",
  "weather protection / canopy rentals": "Weather Protection & Canopy",
  "weather protection & canopy": "Weather Protection & Canopy",
  "kids entertainment & magic shows": "Kids Entertainment & Magic Shows",
};

export function formatCategoryLabel(raw?: string | null): string {
  if (!raw) return "";
  const norm = raw.trim().toLowerCase().replace(/&amp;/g, "&");
  if (CATEGORY_LABELS[norm]) {
    return CATEGORY_LABELS[norm];
  }
  // Remove underscores and slashes
  const clean = raw.replace(/_/g, " ").replace(/\//g, " & ");
  const words = clean.split(/\s+/);
  const formatted = words.map((w) => {
    const lw = w.toLowerCase();
    if (["and", "of", "the", "for", "in", "to", "on"].includes(lw)) {
      return lw === "and" ? "&" : lw;
    }
    return w.charAt(0).toUpperCase() + w.slice(1);
  });
  let res = formatted.join(" ").replace(/& &/g, "&").replace(/\s+/g, " ");
  if (res.startsWith("& ")) res = res.slice(2);
  return res.replace(/_/g, " ");
}
