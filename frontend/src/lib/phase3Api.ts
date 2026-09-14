import { API_BASE } from "./config";
import { authHeaders, getAccessToken } from "./auth";
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

export interface TrainerClient {
  id: number;
  client_id: string;
  email: string | null;
  display_name: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  active_plans: number;
  full_name: string | null;
  goal: string | null;
  gender: string | null;
  age: number | null;
  height_cm: number | null;
  weight_kg: number | null;
}

export interface ClientInfoPayload {
  full_name?: string | null;
  goal?: string | null;
  gender?: string | null;
  age?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
}

export const trainerClientsApi = {
  list: () => apiFetch<TrainerClient[]>("/trainer/clients", {}, { auth: true }),
  add: (email: string, info?: ClientInfoPayload) =>
    apiFetch<TrainerClient>(
      "/trainer/clients",
      { method: "POST", body: JSON.stringify({ email, ...info }) },
      { auth: true },
    ),
  updateInfo: (clientId: string, payload: ClientInfoPayload) =>
    apiFetch<TrainerClient>(
      `/trainer/clients/${encodeURIComponent(clientId)}`,
      { method: "PATCH", body: JSON.stringify(payload) },
      { auth: true },
    ),
  remove: (clientId: string) =>
    apiFetch<void>(`/trainer/clients/${encodeURIComponent(clientId)}`, { method: "DELETE" }, { auth: true }),
};

export interface TrainerCredential {
  id: number;
  kind: "award" | "certificate" | string;
  title: string;
  description: string | null;
  image_urls: string[];
  created_at: string | null;
}

export interface TrainerProfileData {
  full_name: string | null;
  age: number | null;
  years_experience: number | null;
  bio_vi: string | null;
  business_name: string | null;
  gym_name: string | null;
  is_verified: boolean;
  awards: TrainerCredential[];
  certificates: TrainerCredential[];
  share_token: string | null;
  share_url_path: string | null;
  email?: string | null;
  display_name?: string | null;
}

export const trainerProfileApi = {
  get: () => apiFetch<TrainerProfileData>("/trainer/profile", {}, { auth: true }),
  update: (payload: {
    full_name?: string | null;
    age?: number | null;
    years_experience?: number | null;
    bio_vi?: string | null;
    business_name?: string | null;
    gym_name?: string | null;
  }) =>
    apiFetch<TrainerProfileData>("/trainer/profile", { method: "PUT", body: JSON.stringify(payload) }, { auth: true }),
  addCredential: (payload: {
    kind: "award" | "certificate";
    title: string;
    description?: string | null;
    image_urls: string[];
  }) =>
    apiFetch<TrainerCredential>(
      "/trainer/credentials",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: true },
    ),
  removeCredential: (id: number) =>
    apiFetch<void>(`/trainer/credentials/${id}`, { method: "DELETE" }, { auth: true }),
  getPublic: (token: string) =>
    apiFetch<TrainerProfileData>(`/trainer/public/${encodeURIComponent(token)}`, {}, { auth: false }),
  uploadImage: async (file: File): Promise<{ url: string }> => {
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = { Accept: "application/json", ...authHeaders() };
    const res = await fetch(`${API_BASE}/trainer/media/upload`, { method: "POST", headers, body: form });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = (data as { detail?: string }).detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : "Upload thất bại");
    }
    return res.json();
  },
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
  const headers: Record<string, string> = { Accept: "application/json" };
  if (getAccessToken()) Object.assign(headers, authHeaders());
  const res = await fetch(url.toString(), { headers });
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
