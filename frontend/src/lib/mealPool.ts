import type { Food } from "./types";

export const MEAL_ROLE_OPTS = [
  { id: "protein" as const, label: "Đạm", min: 2 },
  { id: "carb" as const, label: "Tinh bột", min: 2 },
  { id: "produce" as const, label: "Rau", min: 1 },
];

export type MealRoleId = (typeof MEAL_ROLE_OPTS)[number]["id"];

export function foodMacroRoles(food: Food): Set<string> {
  const roles = new Set((food.macro_roles || []).map((r) => String(r).toLowerCase()));
  for (const tag of food.tags || []) {
    const t = String(tag).toLowerCase();
    if (t === "protein" || t === "carb" || t === "produce" || t === "fat" || t === "dairy") {
      roles.add(t);
    }
  }
  if ((food.protein_g || 0) >= 15) roles.add("protein");
  if ((food.carbs_g || 0) >= 15) roles.add("carb");
  if (food.is_complete_meal) roles.add("complete");
  return roles;
}

export function countMealRoles(foods: Food[]): Record<MealRoleId, number> {
  const counts: Record<MealRoleId, number> = { protein: 0, carb: 0, produce: 0 };
  for (const food of foods) {
    const roles = foodMacroRoles(food);
    (Object.keys(counts) as MealRoleId[]).forEach((role) => {
      if (roles.has(role)) counts[role] += 1;
    });
  }
  return counts;
}

export function mealPoolReady(foods: Food[]): boolean {
  const counts = countMealRoles(foods);
  return counts.protein >= 2 && counts.carb >= 2;
}

export const MEAL_POOL_HELP =
  "Chọn ít nhất 2 món đạm và 2 món tinh bột (thịt, trứng, cơm, khoai…).";
