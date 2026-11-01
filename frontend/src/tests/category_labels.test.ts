import test from "node:test";
import assert from "node:assert/strict";
import { formatCategoryLabel, CATEGORY_LABELS } from "../lib/constants.ts";

test("formatCategoryLabel formats recognized categories", () => {
  assert.equal(formatCategoryLabel("venue"), "Venue");
  assert.equal(formatCategoryLabel("catering"), "Catering");
  assert.equal(formatCategoryLabel("decor"), "Décor");
  assert.equal(formatCategoryLabel("photography"), "Photography");
  assert.equal(formatCategoryLabel("decor_cake"), "Décor & Custom Cake");
  assert.equal(formatCategoryLabel("contingency"), "Contingency & Reserve");
});

test("formatCategoryLabel handles fallback string formatting", () => {
  assert.equal(formatCategoryLabel("custom_lighting_system"), "Custom Lighting System");
  assert.equal(formatCategoryLabel("live_music_band"), "Live Music Band");
  assert.equal(formatCategoryLabel(""), "");
  assert.equal(formatCategoryLabel(null), "");
});
