import { describe, expect, it } from "vitest";
import {
  catalogServingGrams,
  gramsFromServings,
  kcalFromGrams,
  kcalPer100gFromFood,
  kcalPer100gFromTotals,
  servingsFromGrams,
} from "./mealGrams";

describe("mealGrams", () => {
  it("defaults catalog portion to 100g", () => {
    expect(catalogServingGrams(null)).toBe(100);
    expect(catalogServingGrams(0)).toBe(100);
    expect(catalogServingGrams(150)).toBe(150);
  });

  it("computes kcal from per-100g density", () => {
    expect(kcalFromGrams(150, 200)).toBe(300);
    expect(kcalFromGrams(110, 150)).toBe(165);
  });

  it("round-trips grams through catalog servings", () => {
    expect(servingsFromGrams(200, 150)).toBe(1.3333);
    expect(gramsFromServings(1.3333, 150)).toBe(200);
    expect(servingsFromGrams(100, 100)).toBe(1);
  });

  it("derives kcal/100g from catalog serving calories", () => {
    expect(kcalPer100gFromFood({ calories: 195, serving_grams: 150 })).toBe(130);
    expect(kcalPer100gFromFood({ kcal_100g: 165, calories: 999, serving_grams: 80 })).toBe(165);
  });

  it("recovers density from stored meal totals", () => {
    expect(kcalPer100gFromTotals(300, 200)).toBe(150);
  });
});
