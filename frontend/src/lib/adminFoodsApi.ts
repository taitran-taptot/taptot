import { apiFetch } from "./http";
import type { Paginated } from "./types";

export type AdminFood = {
  id: number;
  slug: string;
  name_vi: string;
  name_en: string | null;
  category_id: number | null;
  serving_size: string;
  serving_grams: number | null;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  sodium_mg: number | null;
  kcal_100g: number | null;
  protein_100g: number | null;
  carbs_100g: number | null;
  fat_100g: number | null;
  fiber_100g: number | null;
  sugar_100g: number | null;
  sodium_100mg: number | null;
  image_url: string | null;
  is_common: boolean;
  prep_state: string | null;
  status: string;
  food_kind?: string;
};

export type AdminFoodPayload = {
  name_vi: string;
  name_en?: string | null;
  category_id?: number | null;
  serving_size?: string;
  serving_grams?: number;
  kcal_100g: number;
  protein_100g: number;
  carbs_100g: number;
  fat_100g: number;
  fiber_100g?: number | null;
  sugar_100g?: number | null;
  sodium_100mg?: number | null;
  image_url?: string | null;
  is_common?: boolean;
  prep_state?: string | null;
  status?: string;
  slug?: string | null;
};

const auth = { auth: true as const };

function qs(p: Record<string, string | number | undefined | null>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) {
    if (v === undefined || v === null || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export const adminFoodsApi = {
  list: (p: { page?: number; page_size?: number; q?: string; category_id?: number | ""; status?: string } = {}) =>
    apiFetch<Paginated<AdminFood>>(`/admin/foods${qs(p)}`, {}, auth),
  create: (body: AdminFoodPayload) =>
    apiFetch<AdminFood>("/admin/foods", { method: "POST", body: JSON.stringify(body) }, auth),
  update: (id: number, body: Partial<AdminFoodPayload>) =>
    apiFetch<AdminFood>(`/admin/foods/${id}`, { method: "PATCH", body: JSON.stringify(body) }, auth),
};
