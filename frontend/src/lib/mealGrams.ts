export const DEFAULT_SERVING_GRAMS = 100;
export const GRAMS_STEP = 10;
export const MIN_GRAMS = 1;
export const MAX_GRAMS = 5000;

export function catalogServingGrams(servingGrams: number | null | undefined): number {
  return servingGrams != null && servingGrams > 0 ? servingGrams : DEFAULT_SERVING_GRAMS;
}

export function clampMealGrams(n: number): number {
  if (!Number.isFinite(n)) return MIN_GRAMS;
  return Math.min(MAX_GRAMS, Math.max(MIN_GRAMS, Math.round(n * 10) / 10));
}

export function kcalFromGrams(kcal100g: number, grams: number): number {
  if (!Number.isFinite(kcal100g) || !Number.isFinite(grams) || grams <= 0) return 0;
  return Math.round((kcal100g * grams) / 100);
}

export function servingsFromGrams(grams: number, servingGrams: number | null | undefined): number {
  const base = catalogServingGrams(servingGrams);
  if (base <= 0) return 1;
  return Math.round((grams / base) * 10000) / 10000;
}

export function gramsFromServings(servings: number, servingGrams: number | null | undefined): number {
  const qty = Number.isFinite(servings) && servings > 0 ? servings : 1;
  return clampMealGrams(qty * catalogServingGrams(servingGrams));
}

export function kcalPer100gFromTotals(calories: number, grams: number): number {
  if (!Number.isFinite(calories) || !Number.isFinite(grams) || grams <= 0) return 0;
  return Math.round(((calories * 100) / grams) * 100) / 100;
}

export function kcalPer100gFromFood(food: {
  kcal_100g?: number | null;
  calories?: number | null;
  serving_grams?: number | null;
}): number {
  if (food.kcal_100g != null && Number.isFinite(food.kcal_100g) && food.kcal_100g >= 0) {
    return food.kcal_100g;
  }
  const grams = catalogServingGrams(food.serving_grams);
  const cal = food.calories ?? 0;
  return kcalPer100gFromTotals(cal, grams);
}

export function parseGramsInput(raw: string): number | null {
  const n = parseFloat(raw.replace(",", ".").trim());
  return Number.isFinite(n) ? n : null;
}
