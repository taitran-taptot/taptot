import { foodPer100g, type FoodNutrients } from "./foodDisplay";
import type { Food, FoodPortionOption } from "./types";

export type UnitCode = "g" | "kg" | "mg" | "ml" | "l" | "tsp" | "tbsp" | "mieng" | "qua" | "cai";

const KNOWN_DENSITY: Record<string, number> = {
  "nuoc-loc": 1,
  "nuoc-mam": 1.2,
  "dau-an": 14 / 15,
  "dau-oliu": 0.91,
  "nuoc-tuong": 1.15,
};

const PIECE_WORD: Record<"mieng" | "qua" | "cai", string> = {
  mieng: "mieng",
  qua: "qua",
  cai: "cai",
};

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase();
}

function portionGrams(portions: FoodPortionOption[] | undefined, needle: string): number | null {
  const key = fold(needle);
  for (const row of portions || []) {
    if (fold(row.label_vi || "").includes(key) && row.grams > 0) return row.grams;
  }
  return null;
}

export function foodDensity(food: Food): number | null {
  if (food.density_g_per_ml && food.density_g_per_ml > 0) return food.density_g_per_ml;
  const tbsp = portionGrams(food.portions, "15ml");
  if (tbsp) return tbsp / 15;
  const known = KNOWN_DENSITY[food.slug];
  return known ?? null;
}

export function unitChoices(food: Food): { id: UnitCode; label: string }[] {
  const choices: { id: UnitCode; label: string }[] = [
    { id: "g", label: "g" },
    { id: "kg", label: "kg" },
    { id: "mg", label: "mg" },
  ];
  const density = foodDensity(food);
  if (density) {
    choices.push({ id: "ml", label: "ml" }, { id: "l", label: "l" });
    choices.push({ id: "tsp", label: "thìa cà phê" }, { id: "tbsp", label: "thìa canh" });
  }
  if (portionGrams(food.portions, "miếng") || portionGrams(food.portions, "mieng")) {
    choices.push({ id: "mieng", label: "miếng" });
  }
  if (portionGrams(food.portions, "quả") || portionGrams(food.portions, "qua")) {
    choices.push({ id: "qua", label: "quả" });
  }
  if (portionGrams(food.portions, "cái") || portionGrams(food.portions, "cai")) {
    choices.push({ id: "cai", label: "cái" });
  }
  return choices;
}

export function toGrams(quantity: number, unit: UnitCode, food: Food): number | null {
  if (!Number.isFinite(quantity) || quantity < 0) return null;
  if (unit === "g") return quantity;
  if (unit === "kg") return quantity * 1000;
  if (unit === "mg") return quantity * 0.001;
  const density = foodDensity(food);
  if (unit === "tsp") {
    const piece = portionGrams(food.portions, "cà phê") ?? portionGrams(food.portions, "ca phe");
    if (piece) return quantity * piece;
    if (!density) return null;
    return quantity * 5 * density;
  }
  if (unit === "tbsp") {
    const piece = portionGrams(food.portions, "canh");
    if (piece) return quantity * piece;
    if (!density) return null;
    return quantity * 15 * density;
  }
  if (unit === "ml" || unit === "l") {
    if (!density) return null;
    const ml = unit === "l" ? quantity * 1000 : quantity;
    return ml * density;
  }
  const piece = portionGrams(food.portions, PIECE_WORD[unit]);
  if (!piece) return null;
  return quantity * piece;
}

export function nutrientsForGrams(food: Food, grams: number): FoodNutrients | null {
  const per100 = foodPer100g(food);
  if (!per100 || grams < 0) return null;
  const factor = grams / 100;
  return {
    calories: per100.calories * factor,
    protein_g: per100.protein_g * factor,
    carbs_g: per100.carbs_g * factor,
    fat_g: per100.fat_g * factor,
    fiber_g: per100.fiber_g == null ? null : per100.fiber_g * factor,
    sugar_g: per100.sugar_g == null ? null : per100.sugar_g * factor,
    sodium_mg: per100.sodium_mg == null ? null : per100.sodium_mg * factor,
  };
}
