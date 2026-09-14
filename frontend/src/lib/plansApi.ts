import { API_BASE } from "./config";
import { authHeaders, getAccessToken } from "./auth";
import { apiFetch, handleUnauthorized } from "./http";
import { BRAND_NAME } from "./brand";

export type PlanSource = "manual" | "ai" | "template" | "imported";

export interface PlanSummary {
  id: number;
  title_vi: string;
  description_vi: string | null;
  source: string;
  target_calories: number | null;
  target_protein_g?: number | null;
  target_carbs_g?: number | null;
  target_fat_g?: number | null;
  is_template?: boolean;
  start_date: string | null;
  end_date: string | null;
  ai_generation_id?: number | null;
  share_token?: string | null;
  share_url_path?: string | null;
  day_count: number;
  exercise_count: number;
  meal_count: number;
  created_at: string;
  updated_at: string;
  is_guest?: boolean;
  challenge_100_days?: boolean;
  expires_at?: string | null;
  days_left?: number | null;
}

export interface PlanExercise {
  id: number;
  exercise_id: number;
  name_vi: string;
  name_en: string | null;
  body_part: string | null;
  gif_url: string | null;
  image_url?: string | null;
  video_url?: string | null;
  instruction_vi?: string | null;
  instruction_steps_vi?: string[] | null;
  section: string;
  sets: number;
  reps: string | null;
  rest_seconds: number;
  sort_order: number;
  notes_vi: string | null;
}

export interface PlanMeal {
  id: number;
  food_id: number;
  name_vi: string;
  meal_type: string;
  servings: number;
  calories: number;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  serving_size?: string | null;
  serving_grams?: number | null;
  sort_order: number;
  notes_vi: string | null;
}

export interface PlanDay {
  id: number;
  day_number: number;
  title_vi: string | null;
  notes_vi: string | null;
  split_role?: string | null;
  target_calories?: number | null;
  target_protein_g?: number | null;
  target_carbs_g?: number | null;
  target_fat_g?: number | null;
  meal_notes?: Record<string, string>;
  section_notes?: Record<string, string>;
  exercises: PlanExercise[];
  meals: PlanMeal[];
}

export interface PlanInsightOverview {
  schedule_vi?: string | null;
  nutrition_vi?: string | null;
  periodization_vi?: string | null;
  summary_vi?: string | null;
}

export interface PlanExerciseInsight {
  exercise_id: number;
  why_vi: string;
}

export interface PlanMealInsight {
  food_id: number;
  meal_type: string;
  why_vi: string;
}

export interface PlanDayInsight {
  day_number: number;
  split_role?: string | null;
  section_notes?: Record<string, string>;
  meal_notes?: Record<string, string>;
  exercises?: PlanExerciseInsight[];
  meals?: PlanMealInsight[];
}

export interface PlanWizardInputs {
  recap_vi?: string | null;
  chips?: string[];
  goal_vi?: string | null;
  location_vi?: string | null;
  equipment_vi?: string | null;
  experience_vi?: string | null;
  sessions_per_week?: number | null;
  session_minutes?: number | null;
  duration_weeks?: number | null;
  focus_vi?: string[];
  gender_vi?: string | null;
  age?: number | null;
  challenge_100_days?: boolean;
  location?: string | null;
  no_equipment?: boolean;
  equipment_list?: string[];
}

export interface PlanNutritionBlock {
  block_index: number;
  weeks: number[];
  projected_weight_kg: number;
  avg_target_calories: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}

export interface PlanNutritionCheckin {
  at: string;
  weight_kg: number;
  avg_target_calories: number;
  week: number;
  block_index: number;
}

export interface PlanInsights {
  overview: PlanInsightOverview;
  advice_vi?: string[];
  days?: PlanDayInsight[];
  inputs?: PlanWizardInputs | null;
  nutrition_blocks?: PlanNutritionBlock[];
  nutrition_block_size?: number;
  nutrition_checkin_interval_days?: number;
  nutrition_checkins?: PlanNutritionCheckin[];
  last_nutrition_checkin_at?: string | null;
  next_nutrition_checkin_due?: string | null;
  curriculum_12_weeks?: boolean;
  challenge_100_days?: boolean;
  challenge_kind?: string | null;
  generation_mode?: string | null;
  curriculum?: {
    mesocycles?: Array<{
      month: number;
      key?: string;
      label_vi?: string;
      blurb_vi?: string;
      rpe_vi?: string;
      deload_week?: number;
      weeks?: number[];
      rationale_vi?: string;
    }>;
    deload_weeks?: number[];
    duration_weeks?: number;
  } | null;
  rest_day_nutrition?: {
    target_calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  } | null;
  rest_day_meals?: Array<{
    food_id: number;
    name_vi?: string;
    meal_type: string;
    servings: number;
    calories?: number;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
    notes_vi?: string | null;
  }> | null;
}

export interface PlanDetail extends PlanSummary {
  days: PlanDay[];
  insights?: PlanInsights | null;
}

export interface CreatePlanPayload {
  title_vi: string;
  description_vi?: string | null;
  target_calories?: number | null;
  target_protein_g?: number | null;
  target_carbs_g?: number | null;
  target_fat_g?: number | null;
  source?: PlanSource;
  is_template?: boolean;
  duration_weeks?: number;
  experience_level?: number;
  days: {
    day_number: number;
    title_vi?: string | null;
    meal_notes?: Record<string, string>;
    section_notes?: Record<string, string>;
    exercises: {
      exercise_id: number;
      sets: number;
      reps?: string | number | null;
      section?: "warmup" | "main" | "cooldown" | "cardio";
      rest_seconds?: number;
    }[];
    meals: {
      food_id: number;
      meal_type?: "breakfast" | "lunch" | "dinner" | "snack";
      servings?: number;
    }[];
  }[];
}

export interface UpdatePlanDayPayload {
  day_number: number;
  exercises: {
    exercise_id: number;
    sets: number;
    reps?: string | number | null;
    section?: "warmup" | "main" | "cooldown" | "cardio";
    rest_seconds?: number;
    sort_order?: number;
  }[];
  meals: {
    food_id: number;
    meal_type?: "breakfast" | "lunch" | "dinner" | "snack";
    servings?: number;
    sort_order?: number;
  }[];
}

export interface NutritionCheckinPreview {
  weight_kg: number;
  avg_target_calories: number;
  delta_from_current: number;
  protein_g: number;
  current_week: number;
  block_index: number;
}

export interface NutritionCheckinResponse {
  preview: NutritionCheckinPreview;
  plan: PlanDetail;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiFetch<T>(path, init, { auth: true });
}

async function fetchBlob(path: string, init: RequestInit = {}, withAuth = true): Promise<Response> {
  if (withAuth && !getAccessToken()) throw new Error("Vui lòng đăng nhập.");
  const headers: Record<string, string> = {
    Accept: "*/*",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (withAuth) Object.assign(headers, authHeaders());
  if (init.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && withAuth) {
    handleUnauthorized();
    throw new Error("Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.");
  }
  return res;
}

export const plansApi = {
  list: () => request<PlanSummary[]>("/my-plans"),
  get: (id: number) => request<PlanDetail>(`/my-plans/${id}`),
  quota: () => request<PlanQuota>(`/my-plans/quota`),
  claim: (share_tokens: string[]) =>
    request<ClaimPlansResult>("/my-plans/claim", {
      method: "POST",
      body: JSON.stringify({ share_tokens }),
    }),

  updateContent: (id: number, days: UpdatePlanDayPayload[]) =>
    request<PlanDetail>(`/my-plans/${id}/content`, {
      method: "PUT",
      body: JSON.stringify({ days }),
    }),

  previewNutritionCheckin: (id: number, weight_kg: number) =>
    request<NutritionCheckinResponse>(`/my-plans/${id}/nutrition-checkin/preview`, {
      method: "POST",
      body: JSON.stringify({ weight_kg }),
    }),

  nutritionCheckin: (id: number, weight_kg: number) =>
    request<NutritionCheckinResponse>(`/my-plans/${id}/nutrition-checkin`, {
      method: "POST",
      body: JSON.stringify({ weight_kg }),
    }),

  restoreAi: (id: number) =>
    request<PlanDetail>(`/my-plans/${id}/restore-ai`, { method: "POST" }),

  listTemplates: () => request<PlanSummary[]>("/my-plans/templates"),
  saveAsTemplate: (id: number, title_vi?: string) =>
    request<PlanDetail>(`/my-plans/${id}/save-as-template`, {
      method: "POST",
      body: JSON.stringify({ title_vi: title_vi || null }),
    }),

  /** Create plan — works for guests (public) and logged-in users. */
  createPublic: (payload: CreatePlanPayload) =>
    apiFetch<PlanDetail>(
      "/plans",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: !!getAccessToken(), requireAuth: false },
    ),
  getByShareToken: (token: string) =>
    apiFetch<PlanDetail>(`/plans/share/${encodeURIComponent(token)}`, {}, { auth: false }),
  remove: (id: number) => request<void>(`/my-plans/${id}`, { method: "DELETE" }),
  export: async (id: number, format: ExportFormat, options?: PlanExportOptions) => {
    const res = await fetchBlob(`/my-plans/${id}/export`, {
      method: "POST",
      body: JSON.stringify({ format, options: options || undefined }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const detail = data.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
            : res.statusText;
      throw new Error(msg || "Xuất file thất bại.");
    }
    const blob = await res.blob();
    downloadExportBlob(blob, format, `taptot-plan-${id}.bin`, res.headers.get("Content-Disposition"));
  },
  exportShared: async (token: string, format: ExportFormat, options?: PlanExportOptions) => {
    const res = await fetchBlob(
      `/plans/share/${encodeURIComponent(token)}/export`,
      { method: "POST", body: JSON.stringify({ format, options: options || undefined }) },
      false,
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const detail = data.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
            : res.statusText;
      throw new Error(msg || "Xuất file thất bại.");
    }
    const blob = await res.blob();
    downloadExportBlob(
      blob,
      format,
      `taptot-plan-${token}.bin`,
      res.headers.get("Content-Disposition"),
    );
  },
};

export interface MealTemplateSummary {
  id: number;
  title_vi: string | null;
  target_calories: number | null;
  item_count: number;
  total_calories: number;
  created_at: string;
}

export interface MealTemplateItem {
  id: number;
  food_id: number;
  name_vi: string;
  meal_type: string;
  servings: number;
  calories: number;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  serving_size?: string | null;
  serving_grams?: number | null;
  sort_order: number;
  notes_vi: string | null;
}

export interface MealTemplate extends MealTemplateSummary {
  meal_notes: Record<string, string>;
  items: MealTemplateItem[];
}

export interface CreateMealTemplatePayload {
  title_vi: string;
  target_calories?: number | null;
  meal_notes?: Record<string, string>;
  items: {
    food_id: number;
    meal_type?: "breakfast" | "lunch" | "dinner" | "snack";
    servings?: number;
    notes_vi?: string | null;
    sort_order?: number;
  }[];
}

export const mealTemplatesApi = {
  list: () => request<MealTemplateSummary[]>("/meal-templates"),
  get: (id: number) => request<MealTemplate>(`/meal-templates/${id}`),
  create: (payload: CreateMealTemplatePayload) =>
    request<MealTemplate>("/meal-templates", { method: "POST", body: JSON.stringify(payload) }),
};

export const trainerApi = {
  assignPlan: (payload: {
    client_id: string;
    source_plan_id: number;
    title_vi?: string;
    notes_vi?: string;
    full_name?: string | null;
    goal?: string | null;
    gender?: string | null;
    age?: number | null;
    height_cm?: number | null;
    weight_kg?: number | null;
  }) =>
    request<{
      assignment_id: number;
      plan_id: number;
      client_id: string;
      title_vi: string;
      share_token?: string | null;
      share_url_path?: string | null;
    }>("/trainer/assign-plan", { method: "POST", body: JSON.stringify(payload) }),
};

export interface PlanQuota {
  used: number;
  limit: number | null;
  remaining: number | null;
  unlimited?: boolean;
}

export interface ClaimPlansResult {
  claimed_count: number;
  claimed: PlanSummary[];
  skipped_full: string[];
  not_found: string[];
  already_owned: string[];
  quota: PlanQuota;
}

export type ExportFormat = "csv" | "xlsx" | "word" | "pdf" | "json";
export type ExportImagePosition = "header" | "before_days" | "footer";

export interface PlanExportOptions {
  customer_name?: string;
  header_text?: string;
  footer_text?: string;
  image_data_urls?: string[];
  image_position?: ExportImagePosition;
  start_date?: string;
}

function downloadExportBlob(blob: Blob, format: ExportFormat, fallbackName: string, cd: string | null) {
  const match = /filename="?([^"]+)"?/i.exec(cd || "");
  const ext =
    format === "word" ? "doc" : format === "pdf" ? "html" : format === "xlsx" ? "xlsx" : format;
  const filename = match?.[1] || fallbackName.replace(/\.\w+$/, `.${ext}`);
  const url = URL.createObjectURL(blob);

  if (format === "pdf") {
    const w = window.open(url, "_blank");
    if (w) {
      w.onload = () => {
        w.focus();
        w.print();
      };
    } else {
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    return;
  }

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const PLAN_SECTION_ORDER = ["warmup", "main", "cardio", "cooldown"] as const;
export type PlanSectionKey = (typeof PLAN_SECTION_ORDER)[number];

export const SECTION_LABEL: Record<PlanSectionKey, string> = {
  warmup: "Khởi động",
  main: "Tập chính",
  cardio: "Cardio (tim mạch)",
  cooldown: "Giãn cơ",
};

export const MEAL_LABEL: Record<string, string> = {
  breakfast: "Bữa sáng",
  lunch: "Bữa trưa",
  dinner: "Bữa tối",
  snack: "Bữa phụ",
};

export const SOURCE_LABEL: Record<string, string> = {
  manual: "Tự tạo",
  ai: BRAND_NAME,
  template: "Mẫu",
  imported: "Nhập",
};
