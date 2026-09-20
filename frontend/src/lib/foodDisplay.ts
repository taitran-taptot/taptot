import { viNum } from "./labels";
import { foodMacroRoles } from "./mealPool";
import type { Food, FoodCategory } from "./types";
import { api } from "./api";

export type FoodNutrients = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  sodium_mg: number | null;
};

export function foodDisplayName(name: string | null | undefined): string {
  return (name || "")
    .replace(/\s*\(\s*sống\s*\)\s*$/i, "")
    .replace(/\s+sống\s*$/i, "")
    .trim();
}

export function foodRoleLabel(food: Food): string {
  const roles = foodMacroRoles(food);
  if (roles.has("protein") && (food.protein_g || 0) >= 15) return "Đạm";
  if (roles.has("carb") && (food.carbs_g || 0) >= 15 && !roles.has("produce")) return "Tinh bột";
  if (roles.has("produce")) return "Rau củ quả";
  if (roles.has("protein")) return "Đạm";
  if (roles.has("carb")) return "Tinh bột";
  if (roles.has("dairy")) return "Sữa";
  if (roles.has("fat")) return "Béo";
  return "";
}

export function foodKcalLine(food: Food): string {
  return `${viNum(food.calories)} kcal / ${food.serving_size || "phần"}`;
}

export function servingIs100g(food: Food): boolean {
  return Math.abs((food.serving_grams || 0) - 100) < 0.51;
}

function scale(value: number | null | undefined, factor: number): number | null {
  if (value == null) return null;
  return value * factor;
}

export function foodPer100g(food: Food): FoodNutrients | null {
  if (food.kcal_100g != null) {
    return {
      calories: food.kcal_100g,
      protein_g: food.protein_100g ?? 0,
      carbs_g: food.carbs_100g ?? 0,
      fat_g: food.fat_100g ?? 0,
      fiber_g: food.fiber_100g ?? null,
      sugar_g: food.sugar_100g ?? null,
      sodium_mg: food.sodium_100mg ?? null,
    };
  }
  const grams = food.serving_grams;
  if (!grams || grams <= 0) return servingIs100g(food) ? foodServingNutrients(food) : null;
  const factor = 100 / grams;
  return {
    calories: food.calories * factor,
    protein_g: food.protein_g * factor,
    carbs_g: food.carbs_g * factor,
    fat_g: food.fat_g * factor,
    fiber_g: scale(food.fiber_g, factor),
    sugar_g: scale(food.sugar_g, factor),
    sodium_mg: scale(food.sodium_mg, factor),
  };
}

export function foodServingNutrients(food: Food): FoodNutrients {
  return {
    calories: food.calories,
    protein_g: food.protein_g,
    carbs_g: food.carbs_g,
    fat_g: food.fat_g,
    fiber_g: food.fiber_g,
    sugar_g: food.sugar_g,
    sodium_mg: food.sodium_mg,
  };
}

export type FoodSubgroup = {
  slug: string;
  nameVi: string;
};

/** Excel subgroup tags: nhom:<slug> + nhom_vi:<tên>. */
export function foodSubgroup(food: Food): FoodSubgroup | null {
  const tags = food.tags || [];
  let slug = "";
  let nameVi = "";
  for (const t of tags) {
    if (t.startsWith("nhom_vi:")) nameVi = t.slice("nhom_vi:".length).trim();
    else if (t.startsWith("nhom:")) slug = t.slice("nhom:".length).trim();
  }
  if (!slug && !nameVi) return null;
  if (!slug) slug = nameVi.toLowerCase().replace(/\s+/g, "-");
  if (!nameVi) nameVi = slug;
  return { slug, nameVi };
}

export function foodSubgroupTag(slug: string): string {
  return `nhom:${slug}`;
}

export function collectSubgroups(foods: Food[]): FoodSubgroup[] {
  const map = new Map<string, FoodSubgroup>();
  for (const food of foods) {
    const g = foodSubgroup(food);
    if (!g) continue;
    if (!map.has(g.slug)) map.set(g.slug, g);
  }
  return [...map.values()].sort((a, b) => a.nameVi.localeCompare(b.nameVi, "vi"));
}

export const DISH_CATEGORY_SLUGS = new Set(["mon-an-truyen-thong", "mon-an"]);
export const HIDDEN_FOOD_CATEGORY_SLUGS = new Set(["an-vat-do-uong"]);

export function isDishCategorySlug(slug: string | undefined | null): boolean {
  return Boolean(slug && DISH_CATEGORY_SLUGS.has(slug));
}

export function isHiddenFoodCategorySlug(slug: string | undefined | null): boolean {
  return Boolean(slug && HIDDEN_FOOD_CATEGORY_SLUGS.has(slug));
}

export async function loadFoodAisleCounts(categories: FoodCategory[]): Promise<{
  all: number;
  counts: Record<number, number>;
}> {
  const [all, ...per] = await Promise.all([
    api.searchFoods({ page: 1, page_size: 1 }),
    ...categories.map((c) => api.searchFoods({ page: 1, page_size: 1, category_id: c.id })),
  ]);
  const counts: Record<number, number> = {};
  categories.forEach((c, i) => {
    counts[c.id] = per[i]?.total ?? 0;
  });
  return { all: all.total, counts };
}
