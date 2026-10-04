import { API_BASE } from "./config";
import { isAuthenticated } from "./auth";
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
  redeem_code?: string | null;
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

export interface SetPrescription {
  reps?: string | number | null;
  rest_seconds?: number | null;
  rir?: number | null;
  rpe?: number | null;
  tempo?: string | null;
  technique?: "drop_set" | null;
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
  rir?: number | null;
  rpe?: number | null;
  tempo?: string | null;
  technique?: "drop_set" | "super_set" | null;
  superset_group?: number | null;
  set_prescriptions?: SetPrescription[] | null;
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
  image_url?: string | null;
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
  meals_flexible?: boolean;
  exercises: PlanExercise[];
  meals: PlanMeal[];
}

export interface PlanInsightOverview {
  schedule_vi?: string | null;
  nutrition_vi?: string | null;
  periodization_vi?: string | null;
  summary_vi?: string | null;
  mission_vi?: string | null;
  outcome_vi?: string | null;
}

export interface StaffKnowledgeRef {
  slug: string;
  title_vi: string;
}

export interface PlanClientProfile {
  height_cm?: number | null;
  weight_kg?: number | null;
  gender?: "male" | "female" | null;
  notes?: string | null;
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
  experience_level?: number | null;
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
  duration_days?: number;
  sessions_per_week?: number;
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
  generator?: string | null;
  familiarization_path?: string | null;
  duration_days?: number | null;
  duration_weeks?: number | null;
  sessions_per_week?: number | null;
  effective_level?: number;
  fitness_test_href?: string | null;
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
    image_url?: string | null;
    serving_size?: string | null;
    serving_grams?: number | null;
  }> | null;
  weight_goal?: {
    bmi: number;
    band: string;
    band_vi: string;
    goal: "lose_weight" | "gain_weight" | "maintain";
    current_kg: number;
    target_kg: number;
    target_bmi?: number;
    weeks: number;
    daily_kcal: number;
    protein_g: number;
    copy_vi: string;
  } | null;
  staff_knowledge?: StaffKnowledgeRef[];
  client?: PlanClientProfile | null;
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
  day_count?: number;
  duration_unit?: "day" | "week" | "month";
  duration_count?: number;
  share_slug?: string | null;
  client?: PlanClientProfile | null;
  days?: {
    day_number: number;
    title_vi?: string | null;
    meal_notes?: Record<string, string>;
    section_notes?: Record<string, string>;
    meals_flexible?: boolean;
    exercises: {
      exercise_id: number;
      sets: number;
      reps?: string | number | null;
      section?: "warmup" | "main" | "cooldown" | "cardio";
      rest_seconds?: number;
      rir?: number | null;
      rpe?: number | null;
      tempo?: string | null;
      technique?: "drop_set" | "super_set" | null;
      superset_group?: number | null;
      set_prescriptions?: SetPrescription[] | null;
    }[];
    meals: {
      food_id: number;
      meal_type?: PlanMealType;
      servings?: number;
    }[];
  }[];
}

export interface CopyPlanTemplatePayload {
  title_vi: string;
  share_slug?: string | null;
  client?: PlanClientProfile | null;
}

export interface UpdatePlanDayPayload {
  day_number: number;
  title_vi?: string | null;
  meals_flexible?: boolean;
  exercises: {
    exercise_id: number;
    sets: number;
    reps?: string | number | null;
    section?: "warmup" | "main" | "cooldown" | "cardio";
    rest_seconds?: number;
    sort_order?: number;
    rir?: number | null;
    rpe?: number | null;
    tempo?: string | null;
    technique?: "drop_set" | "super_set" | null;
    superset_group?: number | null;
    set_prescriptions?: SetPrescription[] | null;
  }[];
  meals: {
    food_id: number;
    meal_type?: PlanMealType;
    servings?: number;
    sort_order?: number;
  }[];
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return apiFetch<T>(path, init, { auth: true });
}

async function fetchBlob(path: string, init: RequestInit = {}, withAuth = true): Promise<Response> {
  if (withAuth && !isAuthenticated()) throw new Error("Vui lòng đăng nhập.");
  const headers: Record<string, string> = {
    Accept: "*/*",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (init.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
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

  updateContent: (
    id: number,
    payload: {
      title_vi?: string;
      description_vi?: string | null;
      share_slug?: string | null;
      overview_summary_vi?: string | null;
      staff_knowledge?: StaffKnowledgeRef[];
      client?: PlanClientProfile | null;
      sync_days?: boolean;
      days: UpdatePlanDayPayload[];
    },
  ) =>
    request<PlanDetail>(`/my-plans/${id}/content`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  restoreAi: (id: number) =>
    request<PlanDetail>(`/my-plans/${id}/restore-ai`, { method: "POST" }),

  listTemplates: () => request<PlanSummary[]>("/my-plans/templates"),
  saveAsTemplate: (id: number, title_vi?: string) =>
    request<PlanDetail>(`/my-plans/${id}/save-as-template`, {
      method: "POST",
      body: JSON.stringify({ title_vi: title_vi || null }),
    }),
  copyTemplate: (id: number, payload: CopyPlanTemplatePayload) =>
    request<PlanDetail>(`/my-plans/templates/${id}/copy`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Create plan — works for guests (public) and logged-in users. */
  createPublic: (payload: CreatePlanPayload) =>
    apiFetch<PlanDetail>(
      "/plans",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: isAuthenticated(), requireAuth: false },
    ),
  create: (payload: CreatePlanPayload) =>
    request<PlanDetail>("/my-plans", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getByShareToken: (token: string) =>
    apiFetch<PlanDetail>(`/plans/share/${encodeURIComponent(token)}`, {}, { auth: false }),
  remove: (id: number) => request<void>(`/my-plans/${id}`, { method: "DELETE" }),
  export: async (id: number, options?: PlanExportOptions) => {
    const res = await fetchBlob(`/my-plans/${id}/export`, {
      method: "POST",
      body: JSON.stringify({ format: "pdf", options: options || undefined }),
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
    downloadExportBlob(blob, `taptot-plan-${id}.pdf`, res.headers.get("Content-Disposition"));
  },
  exportShared: async (token: string, options?: PlanExportOptions) => {
    const res = await fetchBlob(
      `/plans/share/${encodeURIComponent(token)}/export`,
      { method: "POST", body: JSON.stringify({ format: "pdf", options: options || undefined }) },
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
      `taptot-plan-${token}.pdf`,
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
    meal_type?: PlanMealType;
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

export type ExportFormat = "pdf";
export type ExportImagePosition = "header" | "before_days" | "footer";

export interface PlanExportOptions {
  customer_name?: string;
  header_text?: string;
  footer_text?: string;
  image_data_urls?: string[];
  image_position?: ExportImagePosition;
}

function downloadExportBlob(blob: Blob, fallbackName: string, cd: string | null) {
  const match = /filename="?([^"]+)"?/i.exec(cd || "");
  const filename = match?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
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

export const MEAL_GROUP_ORDER = ["breakfast", "lunch", "dinner", "snack", "snack_2"] as const;
export const FLEX_MEAL_TYPE = "flex" as const;
export type PlanMealType = (typeof MEAL_GROUP_ORDER)[number] | typeof FLEX_MEAL_TYPE;

export const MEAL_LABEL: Record<PlanMealType, string> = {
  breakfast: "Bữa sáng",
  lunch: "Bữa trưa",
  dinner: "Bữa tối",
  snack: "Bữa phụ 1",
  snack_2: "Bữa phụ 2",
  flex: "Linh hoạt",
};

export function snackMealType(index: number): PlanMealType {
  return index <= 0 ? "snack" : "snack_2";
}

export const SOURCE_LABEL: Record<string, string> = {
  manual: "Tự tạo",
  ai: BRAND_NAME,
  template: "Mẫu",
  imported: "Nhập",
};
