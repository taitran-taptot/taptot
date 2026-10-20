import type { Food } from "./types";

export const MEAL_POOL_MAX = 30;

export const MEAL_ROLE_OPTS = [
  { id: "protein" as const, label: "Đạm", min: 2 },
  { id: "carb" as const, label: "Tinh bột", min: 2 },
  { id: "produce" as const, label: "Rau", min: 2 },
];

export type MealRoleId = (typeof MEAL_ROLE_OPTS)[number]["id"];

export function isProcessedDish(food: Food): boolean {
  return food.food_kind === "dish" || Boolean(food.is_complete_meal);
}

export function isFruitFood(food: Food): boolean {
  return (food.tags || []).some((tag) => {
    const t = String(tag).toLowerCase();
    return (
      t === "trai-cay" ||
      t === "nhom:trai-cay" ||
      t === "nhom:hoa-qua" ||
      t === "nhom:qua" ||
      t.startsWith("nhom:qua") ||
      t.startsWith("nhom:trai-cay")
    );
  });
}

const STARCHY_NEEDLES = [
  "khoai lang",
  "khoai tây",
  "khoai tay",
  "khoai mì",
  "khoai mi",
  "khoai môn",
  "khoai mon",
  "khoai sọ",
  "khoai so",
  "bắp ngọt",
  "bap ngot",
  "bắp ngô",
  "bap ngo",
  "sweet corn",
  "sweet potato",
  "taro",
];
const NOT_STARCHY_NEEDLES = ["cải bắp", "cai bap", "bắp cải", "bap cai", "đậu bắp", "dau bap", "cá khoai", "ca khoai"];

export function isStarchyVegetable(food: Pick<Food, "slug" | "name_vi" | "name_en">): boolean {
  const blob = `${food.name_vi || ""} ${food.name_en || ""} ${food.slug || ""}`.toLowerCase();
  if (NOT_STARCHY_NEEDLES.some((needle) => blob.includes(needle))) return false;
  return STARCHY_NEEDLES.some((needle) => blob.includes(needle));
}

export function foodMacroRoles(food: Food): Set<string> {
  if (isProcessedDish(food)) return new Set(["complete"]);
  if (isFruitFood(food)) return new Set(["fruit"]);
  if (isStarchyVegetable(food)) return new Set(["carb"]);
  const roles = new Set((food.macro_roles || []).map((r) => String(r).toLowerCase()));
  for (const tag of food.tags || []) {
    const t = String(tag).toLowerCase();
    if (t === "protein" || t === "carb" || t === "produce" || t === "fat" || t === "dairy" || t === "rau") {
      roles.add(t === "rau" ? "produce" : t);
    }
  }
  if ((food.protein_g || 0) >= 15) roles.add("protein");
  if ((food.carbs_g || 0) >= 15 && !roles.has("produce")) roles.add("carb");
  return roles;
}

export function countMealRoles(foods: Food[]): Record<MealRoleId, number> {
  const counts: Record<MealRoleId, number> = { protein: 0, carb: 0, produce: 0 };
  for (const food of foods) {
    const roles = foodMacroRoles(food);
    if (roles.has("complete") || roles.has("fruit")) continue;
    (Object.keys(counts) as MealRoleId[]).forEach((role) => {
      if (roles.has(role)) counts[role] += 1;
    });
  }
  return counts;
}

export function mealPoolReady(foods: Food[]): boolean {
  if (foods.length > MEAL_POOL_MAX) return false;
  const counts = countMealRoles(foods);
  return counts.protein >= 2 && counts.carb >= 2 && counts.produce >= 2;
}

export const MEAL_POOL_HELP =
  "Chọn ít nhất 2 món đạm, 2 món tinh bột và 2 món rau (tối đa 30 món).";
