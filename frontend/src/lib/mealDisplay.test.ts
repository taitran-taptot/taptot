import { describe, expect, it } from "vitest";
import {
  aggregateMealsByFood,
  atwaterKcal,
  averagePlanMealKcal,
  averagePlanMealNutrition,
  ceilKcalTo50,
  roundMacrosToKcal,
  formatPlanMealPortion,
  formatPlanMealPortionLine,
  mealKcalBiasFromInsights,
  planMealMacrosPer100g,
  roundDisplayMealKcal,
} from "./mealDisplay";

describe("formatPlanMealPortion", () => {
  it("shows household grams when serving_grams is set", () => {
    const out = formatPlanMealPortion({
      name_vi: "Táo",
      servings: 1.5,
      serving_grams: 120,
    });
    expect(out.primary).toContain("g");
    expect(out.primary).not.toMatch(/kcal|calo/i);
  });

  it("shows one serving for a prepared dish instead of a partial bowl", () => {
    const out = formatPlanMealPortion({
      name_vi: "Bánh mì kẹp thịt chả pate",
      servings: 1,
      serving_grams: 130,
      is_complete_meal: true,
    });
    expect(out.primary).toBe("1 suất");
    expect(out.primary).not.toMatch(/tô/);
    const line = formatPlanMealPortionLine({
      name_vi: "Bánh mì kẹp thịt chả pate",
      servings: 0.7,
      serving_grams: 130,
      calories: 404,
      is_complete_meal: true,
    });
    expect(line).toContain("1 suất");
    expect(line).not.toMatch(/tô/);
  });

  it("does not call bánh mì a noodle bowl when the dish flag is missing", () => {
    const out = formatPlanMealPortion({
      name_vi: "Bánh mì kẹp thịt chả pate",
      servings: 1,
      serving_grams: 130,
    });
    expect(out.primary).not.toMatch(/tô/);
  });

  it("keeps household portions for foods that are not prepared dishes", () => {
    const cases: Array<{ name_vi: string; servings: number; serving_grams: number; expect: RegExp; forbid: RegExp }> = [
      { name_vi: "Cơm trắng", servings: 1.5, serving_grams: 150, expect: /chén cơm/, forbid: /1 suất|tô/ },
      { name_vi: "Phở bò", servings: 2, serving_grams: 180, expect: /tô/, forbid: /1 suất/ },
      { name_vi: "Mì gói", servings: 1, serving_grams: 180, expect: /tô/, forbid: /1 suất/ },
      { name_vi: "Ức gà", servings: 1.2, serving_grams: 100, expect: /lòng bàn tay/, forbid: /1 suất|tô/ },
      { name_vi: "Khoai mì luộc", servings: 1, serving_grams: 150, expect: /củ vừa/, forbid: /tô|1 suất/ },
    ];
    for (const row of cases) {
      const out = formatPlanMealPortion(row);
      expect(out.primary, row.name_vi).toMatch(row.expect);
      expect(out.primary, row.name_vi).not.toMatch(row.forbid);
    }
  });

  it("shows 1 suất for other prepared dishes, not a scaled bowl", () => {
    const dishes = ["Phở bò", "Cơm tấm sườn", "Mì Quảng (Tôm thịt heo / gà)", "Bánh mì ốp la (2 trứng)"];
    for (const name_vi of dishes) {
      const out = formatPlanMealPortion({
        name_vi,
        servings: 0.7,
        serving_grams: 400,
        calories: 500,
        is_complete_meal: true,
      });
      expect(out.primary, name_vi).toBe("1 suất");
      expect(out.primary, name_vi).not.toMatch(/tô|chén/);
    }
    const byKind = formatPlanMealPortion({
      name_vi: "Bún bò Huế",
      servings: 0.5,
      serving_grams: 500,
      food_kind: "dish",
    });
    expect(byKind.primary).toBe("1 suất");
  });

  it("falls back to calo without grams", () => {
    const out = formatPlanMealPortion({
      name_vi: "Táo",
      servings: 1.5,
      calories: 141,
    });
    expect(out.primary).toMatch(/calo/i);
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
  const ricePer100g = {
    name_vi: "Yến mạch",
    servings: 1,
    calories: 370,
    protein_g: 6.8,
    carbs_g: 81.7,
    fat_g: 0.6,
  };

  it("scales kcal and macros to 200g (×2)", () => {
    const line = formatPlanMealPortionLine(
      { ...ricePer100g, serving_grams: 200, calories: 740, protein_g: 13.6, carbs_g: 163.4, fat_g: 1.2 },
      { showDensity: true },
    );
    expect(line).toContain("Khoảng 200g");
    expect(line).toContain("~740 calo");
    expect(line).toContain("Đạm 13,6g");
    expect(line).toContain("Tinh bột 163,4g");
    expect(line).toContain("Béo 1,2g");
    expect(line).not.toContain("kcal/100g");
    expect(line).not.toContain("/ 100g");
  });

  it("scales kcal and macros to 150g (×1,5)", () => {
    const line = formatPlanMealPortionLine(
      { ...ricePer100g, serving_grams: 150, calories: 555, protein_g: 10.2, carbs_g: 122.55, fat_g: 0.9 },
      { showDensity: true },
    );
    expect(line).toContain("~555 calo");
    expect(line).toContain("Đạm 10,2g");
    expect(line).toContain("Tinh bột 122,6g");
    expect(line).toContain("Béo 0,9g");
  });

  it("scales kcal and macros to 300g (×3)", () => {
    const line = formatPlanMealPortionLine(
      { ...ricePer100g, serving_grams: 300, calories: 1110, protein_g: 20.4, carbs_g: 245.1, fat_g: 1.8 },
      { showDensity: true },
    );
    expect(line).toContain("~1.110 calo");
    expect(line).toContain("Đạm 20,4g");
    expect(line).toContain("Tinh bột 245,1g");
    expect(line).toContain("Béo 1,8g");
  });
});

describe("aggregateMealsByFood", () => {
  it("sums servings and macros for the same food_id", () => {
    const rows = aggregateMealsByFood([
      {
        food_id: 1,
        name_vi: "Cơm",
        servings: 1,
        calories: 200,
        protein_g: 4,
        carbs_g: 40,
        fat_g: 1,
      },
      {
        food_id: 2,
        name_vi: "Trứng",
        servings: 1,
        calories: 70,
        protein_g: 6,
        carbs_g: 1,
        fat_g: 5,
      },
      {
        food_id: 1,
        name_vi: "Cơm",
        servings: 0.5,
        calories: 100,
        protein_g: 2,
        carbs_g: 20,
        fat_g: 0.5,
      },
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      food_id: 1,
      servings: 1.5,
      calories: 300,
      protein_g: 6,
      carbs_g: 60,
      fat_g: 1.5,
    });
    expect(rows[1]?.food_id).toBe(2);
  });
});

describe("ceilKcalTo50", () => {
  it("rounds leftovers up to xx00 or xx50", () => {
    expect(ceilKcalTo50(2802)).toBe(2850);
    expect(ceilKcalTo50(2722)).toBe(2750);
    expect(ceilKcalTo50(1749)).toBe(1750);
    expect(ceilKcalTo50(1)).toBe(50);
  });

  it("keeps values already on xx00 or xx50", () => {
    expect(ceilKcalTo50(2800)).toBe(2800);
    expect(ceilKcalTo50(2750)).toBe(2750);
    expect(ceilKcalTo50(0)).toBe(0);
  });
});

describe("averagePlanMealKcal", () => {
  it("averages food calorie sums and skips empty days", () => {
    expect(
      averagePlanMealKcal([
        { meals: [{ calories: 2804 }, { calories: 0 }] },
        { meals: [{ calories: 2797 }] },
        { meals: [] },
      ]),
    ).toBe((2804 + 2797) / 2);
    expect(averagePlanMealKcal([{ meals: [] }])).toBeNull();
  });
});

describe("roundMacrosToKcal", () => {
  it("scales averaged macros so Atwater matches the displayed calorie mark", () => {
    const avg = averagePlanMealNutrition([
      { meals: [{ calories: 1800, protein_g: 120, carbs_g: 180, fat_g: 53.3 }] },
      { meals: [{ calories: 1900, protein_g: 130, carbs_g: 200, fat_g: 55 }] },
    ]);
    expect(avg).not.toBeNull();
    const kcal = ceilKcalTo50(avg!.kcal);
    const macros = roundMacrosToKcal(kcal, avg!);
    expect(kcal % 50).toBe(0);
    expect(Math.abs(atwaterKcal(macros.protein_g, macros.carbs_g, macros.fat_g) - kcal)).toBeLessThanOrEqual(4);
  });
});

describe("roundDisplayMealKcal", () => {
  it("floors to 50 for fat loss so rest vs train days still step down vs target", () => {
    expect(roundDisplayMealKcal(1867, "lose")).toBe(1850);
    expect(roundDisplayMealKcal(1820, "lose")).toBe(1800);
    expect(roundDisplayMealKcal(1850, "lose")).toBe(1850);
  });

  it("ceils to 50 for surplus so days step up vs target", () => {
    expect(roundDisplayMealKcal(1867, "gain")).toBe(1900);
    expect(roundDisplayMealKcal(1801, "gain")).toBe(1850);
    expect(roundDisplayMealKcal(1850, "gain")).toBe(1850);
  });

  it("rounds nearest 50 when maintaining", () => {
    expect(roundDisplayMealKcal(1824, "maintain")).toBe(1800);
    expect(roundDisplayMealKcal(1825, "maintain")).toBe(1850);
  });
});

describe("mealKcalBiasFromInsights", () => {
  it("reads weight_goal then goal_vi", () => {
    expect(mealKcalBiasFromInsights({ weight_goal: { goal: "lose_weight" } })).toBe("lose");
    expect(mealKcalBiasFromInsights({ weight_goal: { goal: "gain_weight" } })).toBe("gain");
    expect(mealKcalBiasFromInsights({ inputs: { goal_vi: "Giảm cân" } })).toBe("lose");
    expect(mealKcalBiasFromInsights({ inputs: { goal_vi: "Tăng cân" } })).toBe("gain");
  });
});
