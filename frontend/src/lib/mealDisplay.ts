import { foodDisplayName } from "./foodDisplay";
import { viNum } from "./labels";

export type MealPortionInput = {
  name_vi?: string | null;
  servings: number;
  serving_size?: string | null;
  serving_grams?: number | null;
  calories?: number | null;
};

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
  const servings = meal.servings > 0 ? meal.servings : 1;
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
  if (/bún|phở|mì|nui/.test(n)) {
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
    return { primary: `~${viNum(Math.round(meal.calories))} kcal` };
  }

  if (servings === 1) return { primary: "1 phần" };
  return { primary: `${viNum(servings)} phần` };
}

/** Calo trên 100g — chỉ hiện khi người dùng mở chi tiết macro. */
export function formatPlanMealCalorieDensity(meal: MealPortionInput): string | null {
  const calories = meal.calories;
  if (calories == null || calories <= 0) return null;

  const totalGrams = totalMealGrams(meal);
  if (totalGrams != null && totalGrams > 0) {
    const per100 = Math.round((calories * 100) / totalGrams);
    if (per100 > 0) return `~${viNum(per100)} kcal/100g`;
  }

  const servings = meal.servings > 0 ? meal.servings : 1;
  const baseGrams = baseServingGrams(meal);
  if (baseGrams != null && Math.abs(baseGrams - 100) < 0.51) {
    const per100 = Math.round(calories / servings);
    if (per100 > 0) return `~${viNum(per100)} kcal/100g`;
  }

  return null;
}

export function formatPlanMealPortionLine(
  meal: MealPortionInput,
  opts?: { showDensity?: boolean },
): string {
  const portion = formatPlanMealPortion(meal);
  if (opts?.showDensity) {
    const density = formatPlanMealCalorieDensity(meal);
    if (density) return `${portion.primary} · ${density}`;
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
