import { API_BASE } from "./config";
import { isAuthenticated } from "./auth";
import { apiFetch } from "./http";
import type { Food } from "./types";

export const DIET_OPTS: { key: string; label: string }[] = [
  { key: "", label: "Tất cả" },
  { key: "high_protein", label: "Giàu protein" },
  { key: "low_carb", label: "Ít carb" },
  { key: "low_fat", label: "Ít béo" },
];

export interface CreateCustomFoodPayload {
  name_vi: string;
  serving_size?: string;
  serving_grams?: number | null;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  category_id?: number | null;
  tags?: string[];
}

export const customFoodsApi = {
  create: (payload: CreateCustomFoodPayload) =>
    apiFetch<Food>("/my-foods", { method: "POST", body: JSON.stringify(payload) }, { auth: true }),
};

/** Authenticated food search when logged in (includes custom foods). */
export async function searchFoodsAuth(
  params: Record<string, string | number | boolean | undefined | null>,
): Promise<{ items: Food[]; total: number; page: number; page_size: number; pages: number }> {
  const origin = typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:3000";
  const url = new URL(
    API_BASE.startsWith("http") ? API_BASE + "/search/foods" : origin + API_BASE + "/search/foods",
  );
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
    credentials: isAuthenticated() ? "include" : "same-origin",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}
