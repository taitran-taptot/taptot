import { foodDisplayName } from "./foodDisplay";
import { viNum } from "./labels";

export type MealPortionInput = {
  name_vi?: string | null;
  servings: number;
  serving_size?: string | null;
  serving_grams?: number | null;
  calories?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  is_complete_meal?: boolean | null;
  food_kind?: string | null;
};

function isPreparedDish(meal: MealPortionInput): boolean {
  if (meal.is_complete_meal) return true;
  return (meal.food_kind || "").toLowerCase() === "dish";
}

const PURE_GRAM_SIZE = /^\s*(\d+(?:[.,]\d+)?)\s*g\s*$/i;

function parseGramsFromServingSize(servingSize: string | null | undefined): number | null {
  if (!servingSize) return null;
  const m = servingSize.match(PURE_GRAM_SIZE);
  if (!m) return null;
  const n = parseFloat(m[1].replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
}

function isPureGramServingSize(servingSize: string | null | undefined): boolean {
  return Boolean(servingSize && PURE_GRAM_SIZE.test(servingSize));
}

function roundFriendlyGrams(grams: number): number {
  return Math.round(grams / 5) * 5;
}

function baseServingGrams(meal: MealPortionInput): number | null {
  if (meal.serving_grams != null && meal.serving_grams > 0) return meal.serving_grams;
  return parseGramsFromServingSize(meal.serving_size);
}

export function formatPlanMealTitle(nameVi: string | null | undefined): string {
  return foodDisplayName(nameVi?.trim() || "Món ăn");
}

export function totalMealGrams(meal: MealPortionInput): number | null {
  const servings = isPreparedDish(meal) ? 1 : meal.servings > 0 ? meal.servings : 1;
  const baseGrams = baseServingGrams(meal);
  if (baseGrams == null) return null;
  const total = servings * baseGrams;
  return total > 0 ? total : null;
}

function householdHint(nameVi: string, grams: number): string | null {
  const n = nameVi.toLowerCase();
  if (/cơm/.test(n)) {
    const bowls = grams / 150;
    if (bowls >= 0.4) return `~${viNum(Math.round(bowls * 10) / 10)} chén cơm`;
  }
  const noodle = /bún|phở|nui/.test(n) || (/mì/.test(n) && !/bánh\s*mì|khoai\s*mì|bột\s*mì/.test(n));
  if (noodle) {
    const bowls = grams / 180;
    if (bowls >= 0.4) return `~${viNum(Math.round(bowls * 10) / 10)} tô`;
  }
  if (/dầu|olive|oli|mỡ/.test(n)) {
    const tbsp = grams / 14;
    if (tbsp >= 0.4) return `~${viNum(Math.round(tbsp * 10) / 10)} thìa canh`;
  }
  if (/chuối|táo|cam|lê|ổi/.test(n)) {
    const pieces = grams / 120;
    if (pieces >= 0.5) return `~${viNum(Math.round(pieces * 10) / 10)} quả`;
  }
  if (/khoai/.test(n)) {
    const pieces = grams / 150;
    if (pieces >= 0.5) return `~${viNum(Math.round(pieces * 10) / 10)} củ vừa`;
  }
  if (/cà\s*chua|cải|rau|xà\s*lách|bắp\s*cải/.test(n)) {
    const bowls = grams / 100;
    if (bowls >= 1) return `~${viNum(Math.round(bowls))} nắm/đĩa rau`;
  }
  if (/gà|thịt|cá|bò|heo|lợn|ức|đùi/.test(n)) {
    const palms = grams / 100;
    if (palms >= 0.5) return `~${viNum(Math.round(palms * 10) / 10)} khẩu phần lòng bàn tay`;
  }
  return null;
}

export function formatPlanMealPortion(meal: MealPortionInput): { primary: string; detail?: string } {
  if (isPreparedDish(meal)) return { primary: "1 suất" };
  const servings = meal.servings > 0 ? meal.servings : 1;
  const baseGrams = baseServingGrams(meal);
  const name = meal.name_vi?.trim() || "";

  if (baseGrams != null) {
    const total = servings * baseGrams;
    if (total > 0) {
      const rounded = roundFriendlyGrams(total);
      const house = householdHint(name, rounded);
      const primary = house
        ? `${house} (≈ ${viNum(rounded)}g)`
        : `Khoảng ${viNum(rounded)}g`;
      const detail =
        servings !== 1
          ? `${viNum(servings)} × ${viNum(baseGrams)}g`
          : undefined;
      return { primary, detail };
    }
  }

  const servingSize = meal.serving_size?.trim();
  if (servingSize && !isPureGramServingSize(servingSize)) {
    if (servings === 1) return { primary: servingSize };
    const countMatch = servingSize.match(/^(\d+(?:[.,]\d+)?)\s+(.+)$/);
    if (countMatch) {
      const unitCount = parseFloat(countMatch[1].replace(",", "."));
      const unitLabel = countMatch[2];
      if (Number.isFinite(unitCount)) {
        const totalUnits = unitCount * servings;
        const formatted =
          Number.isInteger(totalUnits) || Math.abs(totalUnits - Math.round(totalUnits)) < 0.01
            ? viNum(Math.round(totalUnits))
            : viNum(Math.round(totalUnits * 10) / 10);
        return { primary: `${formatted} ${unitLabel}` };
      }
    }
    return {
      primary: `${viNum(servings)} phần`,
      detail: servingSize,
    };
  }

  // Rest-day / scaled meals without grams: prefer kcal over odd "1,8 phần".
  if (meal.calories != null && meal.calories > 0) {
    return { primary: `~${viNum(Math.round(meal.calories))} calo` };
  }

  if (servings === 1) return { primary: "1 phần" };
  return { primary: `${viNum(servings)} phần` };
}

function portionScaleVs100g(meal: MealPortionInput): number | null {
  const totalGrams = totalMealGrams(meal);
  if (totalGrams != null && totalGrams > 0) return totalGrams / 100;
  return null;
}

function planMealKcalPer100g(meal: MealPortionInput): number | null {
  const calories = meal.calories;
  if (calories == null || calories <= 0) return null;

  const totalGrams = totalMealGrams(meal);
  if (totalGrams != null && totalGrams > 0) {
    const per100 = Math.round((calories * 100) / totalGrams);
    return per100 > 0 ? per100 : null;
  }

  const servings = meal.servings > 0 ? meal.servings : 1;
  const baseGrams = baseServingGrams(meal);
  if (baseGrams != null && Math.abs(baseGrams - 100) < 0.51) {
    const per100 = Math.round(calories / servings);
    return per100 > 0 ? per100 : null;
  }

  return null;
}

/** Calo theo khẩu phần (từ số /100g × gram/100). Fallback /100g nếu không có gram. */
export function formatPlanMealCalorieDensity(meal: MealPortionInput): string | null {
  const per100 = planMealKcalPer100g(meal);
  if (per100 == null) return null;
  const scale = portionScaleVs100g(meal);
  if (scale == null) return `~${viNum(per100)} calo/100g`;
  const kcal = Math.round(per100 * scale);
  if (kcal <= 0) return null;
  return `~${viNum(kcal)} calo`;
}

function roundMacro(n: number): number {
  return Math.round(n * 10) / 10;
}

export function planMealMacrosPer100g(meal: MealPortionInput): {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
} | null {
  const totalGrams = totalMealGrams(meal);
  let scale: number | null = null;
  if (totalGrams != null && totalGrams > 0) {
    scale = 100 / totalGrams;
  } else {
    const servings = meal.servings > 0 ? meal.servings : 1;
    const baseGrams = baseServingGrams(meal);
    if (baseGrams != null && Math.abs(baseGrams - 100) < 0.51) {
      scale = 1 / servings;
    }
  }
  if (scale == null) return null;
  const protein = roundMacro((meal.protein_g ?? 0) * scale);
  const carbs = roundMacro((meal.carbs_g ?? 0) * scale);
  const fat = roundMacro((meal.fat_g ?? 0) * scale);
  if (protein <= 0 && carbs <= 0 && fat <= 0) return null;
  return { protein_g: protein, carbs_g: carbs, fat_g: fat };
}

function formatPlanMealMacroDensity(meal: MealPortionInput): string | null {
  const macros = planMealMacrosPer100g(meal);
  if (!macros) return null;
  const scale = portionScaleVs100g(meal);
  if (scale == null) {
    return `Đạm ${viNum(macros.protein_g)}g · Tinh bột ${viNum(macros.carbs_g)}g · Béo ${viNum(macros.fat_g)}g / 100g`;
  }
  const protein = roundMacro(macros.protein_g * scale);
  const carbs = roundMacro(macros.carbs_g * scale);
  const fat = roundMacro(macros.fat_g * scale);
  return `Đạm ${viNum(protein)}g · Tinh bột ${viNum(carbs)}g · Béo ${viNum(fat)}g`;
}

export function formatPlanMealPortionLine(
  meal: MealPortionInput,
  opts?: { showDensity?: boolean },
): string {
  const portion = formatPlanMealPortion(meal);
  if (opts?.showDensity) {
    const extras = [formatPlanMealCalorieDensity(meal), formatPlanMealMacroDensity(meal)].filter(
      Boolean,
    );
    if (extras.length) return `${portion.primary} · ${extras.join(" · ")}`;
  }
  return portion.detail ? `${portion.primary} · ${portion.detail}` : portion.primary;
}

export function planMealHasMacros(meal: {
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
}): boolean {
  return (meal.protein_g ?? 0) > 0 || (meal.carbs_g ?? 0) > 0 || (meal.fat_g ?? 0) > 0;
}

function addNullable(a: number | null | undefined, b: number | null | undefined): number | null {
  if (a == null && b == null) return null;
  return (a ?? 0) + (b ?? 0);
}

export function aggregateMealsByFood<
  T extends {
    food_id: number;
    servings: number;
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
  },
>(meals: T[]): T[] {
  const byId = new Map<number, T>();
  for (const meal of meals) {
    const prev = byId.get(meal.food_id);
    if (!prev) {
      byId.set(meal.food_id, { ...meal });
      continue;
    }
    byId.set(meal.food_id, {
      ...prev,
      servings: prev.servings + meal.servings,
      calories: addNullable(prev.calories, meal.calories) ?? 0,
      protein_g: addNullable(prev.protein_g, meal.protein_g),
      carbs_g: addNullable(prev.carbs_g, meal.carbs_g),
      fat_g: addNullable(prev.fat_g, meal.fat_g),
    });
  }
  return [...byId.values()];
}

/** Round up leftover kcal to xx00 / xx50. Already on a mark stays put. */
export function ceilKcalTo50(kcal: number, step = 50): number {
  const n = Math.max(0, kcal);
  if (n === 0) return 0;
  return Math.ceil(n / step) * step;
}

type MealMacroDay = {
  meals?: Array<{
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
  }> | null;
};

export type AveragedMealNutrition = {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

/** Mean of per-day food calorie sums (days with no meals skipped). */
export function averagePlanMealKcal(days: MealMacroDay[]): number | null {
  return averagePlanMealNutrition(days)?.kcal ?? null;
}

/** Mean of per-day food kcal and macros (days with no meals skipped). */
export function averagePlanMealNutrition(days: MealMacroDay[]): AveragedMealNutrition | null {
  const totals: AveragedMealNutrition[] = [];
  for (const day of days) {
    const meals = day.meals ?? [];
    if (!meals.length) continue;
    totals.push(
      meals.reduce(
        (sum, meal) => ({
          kcal: sum.kcal + (meal.calories || 0),
          protein_g: sum.protein_g + (meal.protein_g || 0),
          carbs_g: sum.carbs_g + (meal.carbs_g || 0),
          fat_g: sum.fat_g + (meal.fat_g || 0),
        }),
        { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
      ),
    );
  }
  if (!totals.length) return null;
  const n = totals.length;
  return {
    kcal: totals.reduce((a, b) => a + b.kcal, 0) / n,
    protein_g: totals.reduce((a, b) => a + b.protein_g, 0) / n,
    carbs_g: totals.reduce((a, b) => a + b.carbs_g, 0) / n,
    fat_g: totals.reduce((a, b) => a + b.fat_g, 0) / n,
  };
}

export function atwaterKcal(protein_g: number, carbs_g: number, fat_g: number): number {
  return 4 * protein_g + 4 * carbs_g + 9 * fat_g;
}

/** Integer grams whose Atwater kcal is as close as possible to the displayed calorie mark. */
export function roundMacrosToKcal(
  kcal: number,
  macros: { protein_g: number; carbs_g: number; fat_g: number },
): { protein_g: number; carbs_g: number; fat_g: number } {
  const target = Math.max(0, Math.round(kcal));
  const energy = atwaterKcal(macros.protein_g, macros.carbs_g, macros.fat_g);
  if (target <= 0 || energy <= 0) {
    return {
      protein_g: Math.max(0, Math.round(macros.protein_g)),
      carbs_g: Math.max(0, Math.round(macros.carbs_g)),
      fat_g: Math.max(0, Math.round(macros.fat_g)),
    };
  }
  const scale = target / energy;
  let protein_g = Math.max(0, Math.round(macros.protein_g * scale));
  let carbs_g = Math.max(0, Math.round(macros.carbs_g * scale));
  let fat_g = Math.max(0, Math.round(macros.fat_g * scale));
  const bump = (key: "carbs_g" | "fat_g" | "protein_g", delta: number) => {
    if (key === "carbs_g") carbs_g = Math.max(0, carbs_g + delta);
    else if (key === "fat_g") fat_g = Math.max(0, fat_g + delta);
    else protein_g = Math.max(0, protein_g + delta);
  };
  for (let i = 0; i < 40; i += 1) {
    const now = atwaterKcal(protein_g, carbs_g, fat_g);
    const diff = target - now;
    if (Math.abs(diff) <= 2) break;
    if (diff > 0) {
      if (diff >= 9) bump("fat_g", 1);
      else bump("carbs_g", 1);
    } else if (diff <= -9 && fat_g > 0) bump("fat_g", -1);
    else if (carbs_g > 0) bump("carbs_g", -1);
    else if (fat_g > 0) bump("fat_g", -1);
    else if (protein_g > 0) bump("protein_g", -1);
    else break;
  }
  return { protein_g, carbs_g, fat_g };
}

export type MealKcalBias = "lose" | "gain" | "maintain";

const KCAL_DISPLAY_STEP = 50;

export function mealKcalBiasFromInsights(insights: {
  weight_goal?: { goal?: string | null } | null;
  inputs?: { goal_vi?: string | null } | null;
} | null | undefined): MealKcalBias {
  const goal = insights?.weight_goal?.goal;
  if (goal === "lose_weight") return "lose";
  if (goal === "gain_weight") return "gain";
  const vi = (insights?.inputs?.goal_vi || "").toLowerCase();
  if (vi.includes("giảm")) return "lose";
  if (vi.includes("tăng")) return "gain";
  return "maintain";
}

/** Round meal kcal in 50s: floor for fat loss, ceil for surplus, nearest for maintain. */
export function roundDisplayMealKcal(kcal: number, bias: MealKcalBias, step = KCAL_DISPLAY_STEP): number {
  const n = Math.max(0, kcal);
  if (n === 0) return 0;
  if (bias === "lose") return Math.floor(n / step) * step;
  if (bias === "gain") return Math.ceil(n / step) * step;
  return Math.round(n / step) * step;
}
