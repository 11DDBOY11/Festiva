/**
 * Formatting and calculation utilities for Festiva AI.
 */

/**
 * Formats a monetary amount in Indian Rupees (INR) with Indian numbering grouping (Lakhs/Crores).
 * e.g. 500000 -> "₹5,00,000"
 */
export function formatINR(amount: number | null | undefined): string {
  if (amount == null || isNaN(amount)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Computes category share percentage rounded to 1 decimal place.
 */
export function computeBudgetShare(allocated: number, total: number): number {
  if (!total || total <= 0 || !allocated || allocated <= 0) return 0;
  return Math.round((allocated / total) * 1000) / 10;
}
