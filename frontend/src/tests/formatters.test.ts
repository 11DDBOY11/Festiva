import test from "node:test";
import assert from "node:assert/strict";
import { formatINR, computeBudgetShare } from "../lib/formatters.ts";

test("formatINR formats numbers into Indian currency style", () => {
  assert.equal(formatINR(null), "₹0");
  assert.equal(formatINR(undefined), "₹0");
  assert.equal(formatINR(0), "₹0");

  const formatted50k = formatINR(50000);
  assert.ok(formatted50k.includes("50,000"), `Expected 50,000 in ${formatted50k}`);

  const formatted5Lakh = formatINR(500000);
  assert.ok(
    formatted5Lakh.includes("5,00,000"),
    `Expected 5,00,000 in ${formatted5Lakh}`
  );

  const formatted1Cr = formatINR(10000000);
  assert.ok(
    formatted1Cr.includes("1,00,00,000"),
    `Expected 1,00,00,000 in ${formatted1Cr}`
  );
});

test("computeBudgetShare computes percentage share correctly", () => {
  assert.equal(computeBudgetShare(0, 100000), 0);
  assert.equal(computeBudgetShare(50000, 0), 0);
  assert.equal(computeBudgetShare(25000, 100000), 25);
  assert.equal(computeBudgetShare(33333, 100000), 33.3);
  assert.equal(computeBudgetShare(66667, 100000), 66.7);
});
