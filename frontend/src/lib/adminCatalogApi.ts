import { apiFetch } from "./http";
import type { Paginated } from "./types";

export type AdminExercise = {
  id: number;
  name_vi: string;
  name_en: string | null;
  muscle_group_id: number;
  muscle_slug?: string;
  muscle_name_vi?: string;
  exercise_type: string;
  movement_role: string | null;
  movement_pattern: string | null;
  venue: string | null;
  difficulty: number;
  difficulty_label: string | null;
  notes_vi: string | null;
  is_active: boolean;
};

export type MuscleGroupRow = {
  id: number;
  slug: string;
  name_vi: string;
  name_en: string | null;
};

export type EquipmentRow = {
  id: number;
  slug: string;
  name_vi: string;
  name_en?: string | null;
  category: string | null;
  is_active: boolean;
  sort_order?: number;
  specs_vi?: string | null;
};

export type EquipmentPayload = {
  name_vi: string;
  name_en?: string | null;
  slug: string;
  category?: string | null;
  is_active: boolean;
  sort_order?: number;
  specs_vi?: string | null;
};

export type AdminExercisePayload = {
  name_vi: string;
  name_en?: string | null;
  muscle_group_id: number;
  exercise_type: string;
  movement_role: string;
  movement_pattern: string;
  venue: string;
  difficulty: number;
  notes_vi?: string | null;
  is_active: boolean;
};

type ListParams = {
  page?: number;
  page_size?: number;
  q?: string;
  muscle_group_id?: number | "";
  movement_pattern?: string;
  movement_role?: string;
  venue?: string;
  difficulty?: number | "";
  is_active?: string;
  exercise_type?: string;
};

function qs(p: ListParams): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) {
    if (v === undefined || v === null || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

const auth = { auth: true as const };

export const adminCatalogApi = {
  listExercises: (p: ListParams) =>
    apiFetch<Paginated<AdminExercise>>(`/admin/exercises${qs(p)}`, {}, auth),
  createExercise: (body: AdminExercisePayload) =>
    apiFetch<AdminExercise>("/exercises", { method: "POST", body: JSON.stringify(body) }, auth),
  updateExercise: (id: number, body: Partial<AdminExercisePayload>) =>
    apiFetch<AdminExercise>(`/exercises/${id}`, { method: "PATCH", body: JSON.stringify(body) }, auth),
  getEquipment: (id: number) =>
    apiFetch<{ equipment_ids: number[] }>(`/admin/exercises/${id}/equipment`, {}, auth),
  putEquipment: (id: number, equipment_ids: number[]) =>
    apiFetch<{ equipment_ids: number[] }>(
      `/admin/exercises/${id}/equipment`,
      { method: "PUT", body: JSON.stringify({ equipment_ids }) },
      auth,
    ),
  muscleGroups: () => fetchAllPages<MuscleGroupRow>("/muscle-groups"),
  equipment: () => fetchAllPages<EquipmentRow>("/equipment"),
  listEquipment: (p?: { page?: number; page_size?: number; q?: string; is_active?: string }) => {
    const u = new URLSearchParams();
    if (p?.page) u.set("page", String(p.page));
    if (p?.page_size) u.set("page_size", String(p.page_size));
    if (p?.is_active) u.set("is_active", p.is_active);
    const s = u.toString();
    return apiFetch<Paginated<EquipmentRow>>(`/equipment${s ? `?${s}` : ""}`, {}, auth);
  },
  createEquipment: (body: EquipmentPayload) =>
    apiFetch<EquipmentRow>("/equipment", { method: "POST", body: JSON.stringify(body) }, auth),
  updateEquipment: (id: number, body: Partial<EquipmentPayload>) =>
    apiFetch<EquipmentRow>(`/equipment/${id}`, { method: "PATCH", body: JSON.stringify(body) }, auth),
};

async function fetchAllPages<T>(path: string): Promise<Paginated<T>> {
  const first = await apiFetch<Paginated<T>>(`${path}?page=1&page_size=100`, {}, auth);
  const items = [...(first.items || [])];
  for (let p = 2; p <= (first.pages || 1); p++) {
    const next = await apiFetch<Paginated<T>>(`${path}?page=${p}&page_size=100`, {}, auth);
    items.push(...(next.items || []));
  }
  return { ...first, items, total: items.length };
}
