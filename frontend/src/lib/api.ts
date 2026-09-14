import { API_BASE } from "./config";
import type {
  EquipmentImageItem,
  ExerciseDetail,
  ExerciseListItem,
  Food,
  FoodCategory,
  KnowledgeArticle,
  Label,
  Paginated,
} from "./types";
import {
  muscleTreeFromApi,
  rebuildMuscleTreeMaps,
  setMuscleTree,
  type MuscleTreeNodeApi,
} from "./muscleGroups";

type Params = Record<string, string | number | boolean | undefined | null>;

export type ExerciseAlternativesQuery = {
  location?: string | null;
  no_equipment?: boolean;
  equipment?: string[];
};

function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
      return "";
    });
    const joined = parts.filter(Boolean).join("; ");
    if (joined) return joined;
  }
  return fallback;
}

async function get<T>(
  path: string,
  params: Params = {},
  repeat?: Record<string, string[] | undefined>,
): Promise<T> {
  const base = API_BASE.startsWith("http")
    ? API_BASE
    : `${typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:3000"}${API_BASE}`;
  const url = new URL(base + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  if (repeat) {
    for (const [k, values] of Object.entries(repeat)) {
      for (const v of values || []) {
        if (v) url.searchParams.append(k, v);
      }
    }
  }
  const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw new Error(errorMessage(detail, res.statusText));
  }
  return res.json() as Promise<T>;
}

export const api = {
  searchExercises: (p: Params) => get<Paginated<ExerciseListItem>>("/search/exercises", p),
  getExercise: (id: string | number) => get<ExerciseDetail>(`/search/exercises/${encodeURIComponent(id)}`),
  exerciseAlternatives: (id: number, limit = 5, ctx?: ExerciseAlternativesQuery) => {
    const extra: Params = { limit };
    if (ctx?.location) extra.location = ctx.location;
    if (ctx?.no_equipment) extra.no_equipment = true;
    return get<ExerciseListItem[]>(
      `/search/exercises/${id}/alternatives`,
      extra,
      { equipment: ctx?.equipment },
    );
  },
  searchFoods: (p: Params) => get<Paginated<Food>>("/search/foods", p),
  bodyPartLabels: async () => {
    const items = await get<Label[]>("/search/muscle-groups");
    return { items, total: items.length, page: 1, page_size: items.length, pages: 1 };
  },
  muscleGroupTree: () => get<MuscleTreeNodeApi[]>("/search/muscle-groups/tree"),
  equipmentLabels: async () => {
    const items = await get<Label[]>("/search/equipment");
    return { items, total: items.length, page: 1, page_size: items.length, pages: 1 };
  },
  equipmentImages: (slug: string) =>
    get<EquipmentImageItem[]>("/search/equipment-images", { slug }),
  foodCategories: () => get<Paginated<FoodCategory>>("/food-categories", { page_size: 100 }),
  knowledgeArticles: () => get<Paginated<KnowledgeArticle>>("/knowledge-articles", { page_size: 100 }),
  knowledgeArticle: (id: number) => get<KnowledgeArticle>(`/knowledge-articles/${id}`),
};
