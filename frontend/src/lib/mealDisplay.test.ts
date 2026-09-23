import { describe, expect, it } from "vitest";
import {
  formatPlanMealPortion,
  formatPlanMealPortionLine,
  planMealMacrosPer100g,
} from "./mealDisplay";

describe("formatPlanMealPortion", () => {
  it("shows household grams when serving_grams is set", () => {
    const out = formatPlanMealPortion({
      name_vi: "Táo",
      servings: 1.5,
      serving_grams: 120,
    });
    expect(out.primary).toContain("g");
    expect(out.primary).not.toMatch(/kcal/i);
  });

  it("falls back to kcal without grams", () => {
    const out = formatPlanMealPortion({
      name_vi: "Táo",
      servings: 1.5,
      calories: 141,
    });
    expect(out.primary).toMatch(/kcal/i);
  });
});

describe("planMealMacrosPer100g", () => {
  it("scales portion macros to 100g", () => {
    const macros = planMealMacrosPer100g({
      servings: 2,
      serving_grams: 100,
      protein_g: 46,
      carbs_g: 0,
      fat_g: 2.4,
    });
    expect(macros).toEqual({ protein_g: 23, carbs_g: 0, fat_g: 1.2 });
  });
});

describe("formatPlanMealPortionLine density", () => {
  it("appends kcal and macros per 100g", () => {
    const line = formatPlanMealPortionLine(
      {
        name_vi: "Ức gà",
        servings: 1,
        serving_grams: 100,
        calories: 110,
        protein_g: 23.1,
        carbs_g: 0,
        fat_g: 1.2,
      },
      { showDensity: true },
    );
    expect(line).toContain("kcal/100g");
    expect(line).toContain("Đạm");
    expect(line).toContain("Tinh bột");
    expect(line).toContain("Béo");
    expect(line).toContain("/ 100g");
  });
});
