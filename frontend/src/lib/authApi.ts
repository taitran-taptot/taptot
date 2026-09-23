import { clearAuth, isAuthenticated, saveUser, type AuthUser } from "./auth";
import { apiFetch, AUTH_EVENT, LOGOUT_EVENT } from "./http";

async function postPublic<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) }, { auth: false });
}

function persistUser(user: AuthUser) {
  saveUser(user);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_EVENT, { detail: user }));
  }
}

export const authApi = {
  register: (email: string, password: string, display_name: string) =>
    postPublic<AuthUser>("/auth/register", { email, password, display_name }),

  login: (email: string, password: string) =>
    postPublic<AuthUser>("/auth/login", { email, password }),

  logout: async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" }, { auth: true, requireAuth: false });
    } catch {
      /* ignore */
    }
    clearAuth();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    }
  },

  forgotPassword: (email: string) =>
    postPublic<{ message: string; reset_url?: string; reset_token?: string }>("/auth/forgot-password", {
      email,
    }),

  resetPassword: (token: string, new_password: string) =>
    postPublic<{ message: string }>("/auth/reset-password", { token, new_password }),

  me: () => apiFetch<AuthUser>("/auth/me", {}, { auth: true, requireAuth: false }),

  confirmPassword: (password: string) =>
    apiFetch<{ message: string }>(
      "/auth/confirm-password",
      { method: "POST", body: JSON.stringify({ password }) },
      { auth: true },
    ),

  changePassword: (current_password: string, new_password: string) =>
    apiFetch<{ message: string }>(
      "/auth/change-password",
      { method: "POST", body: JSON.stringify({ current_password, new_password }) },
      { auth: true },
    ),

  loginAndSave: async (email: string, password: string) => {
    const user = await authApi.login(email, password);
    persistUser(user);
    await claimGuestPlansAfterAuth();
    return user;
  },

  registerAndSave: async (email: string, password: string, display_name: string) => {
    const user = await authApi.register(email, password, display_name);
    persistUser(user);
    await claimGuestPlansAfterAuth();
    return user;
  },
};

/** Gắn lịch guest trên thiết bị vào tài khoản vừa đăng nhập/đăng ký. */
export async function claimGuestPlansAfterAuth(): Promise<void> {
  try {
    const { getGuestPlanTokens, saveGuestPlanTokens, clearGuestPlanTokens } = await import("./guestPlans");
    const tokens = getGuestPlanTokens();
    if (!tokens.length || !isAuthenticated()) return;
    const { plansApi } = await import("./plansApi");
    const result = await plansApi.claim(tokens);
    const keep = new Set(result.skipped_full);
    const remaining = tokens.filter((t) => keep.has(t));
    if (remaining.length) saveGuestPlanTokens(remaining);
    else clearGuestPlanTokens();
  } catch {
    /* claim is best-effort */
  }
}

export interface FitnessBaseline {
  pushups_max?: number | null;
  pushup_variant?: "standard" | "incline_high" | "incline_low" | "knee" | string | null;
  pullups_max?: number | null;
  pull_test_variant?: "strict" | "hang" | "inverted_row" | "inverted_row_low" | string | null;
  pull_hold_seconds?: number | null;
  inverted_rows_max?: number | null;
  plank_seconds?: number | null;
  squats_max?: number | null;
  run_10min_meters?: number | null;
  test_kit?: "bar_rings" | "dumbbell" | "band" | string | null;
  db_press_reps?: number | null;
  db_press_kg?: number | null;
  db_row_reps?: number | null;
  db_row_kg?: number | null;
  goblet_reps?: number | null;
  goblet_kg?: number | null;
  band_level?: string | null;
}

export interface WorkoutScheduleRequest {
  goal: string;
  gender: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: string;
  sessions_per_week: number;
  session_minutes: number;
  location: string;
  focus_areas: string[];
  extra_goals?: string[];
  equipment_list: string[];
  food_ids: number[];
  experience_level?: number;
  ai_suggest_equipment?: boolean;
  /** Chỉ chọn bài tập không gắn dụng cụ */
  no_equipment?: boolean;
  ai_suggest_foods?: boolean;
  fitness_baseline?: FitnessBaseline | null;
  health_note?: string | null;
  duration_weeks?: number;
  /** Tốc độ đổi cân mong muốn (kg/tuần): giảm 0,5–1% cân; tăng 0,25–0,75% cân */
  kg_per_week?: number;
  /** Thử thách 100 ngày (14 tuần) */
  challenge_100_days?: boolean;
  /** Alias cũ — backend map sang challenge_100_days */
  curriculum_12_weeks?: boolean;
  /** free_home = nền thể lực tại nhà (8 tuần, 2 giai đoạn, BW, deterministic) */
  generation_mode?: "free_home" | string | null;
  foundation_motive?: "daily_energy" | "build_habit" | "body_confidence" | string | null;
  familiarization_path?:
    | "first_push_pull"
    | "basic_foundation"
    | string
    | null;
  /** ISO weekday 1=Mon … 7=Sun */
  preferred_weekdays?: number[];
  preferred_start_time?: string | null;
  redeem_code?: string | null;
  payment_entitlement?: string | null;
}

export type FamiliarizationCatalog = {
  duration_weeks: number;
  duration_days?: number;
  paths: {
    key: "first_push_pull" | "basic_foundation";
    label_vi: string;
    description_vi: string;
    target_level: string;
    duration_days?: number;
    duration_weeks?: number;
  }[];
  standards: Record<
    "male" | "female",
    Record<"basic" | "advanced", { key: string; label_vi: string; display_vi: string }[]>
  >;
  exit_goals?: Record<
    "male" | "female",
    { key: string; label_vi: string; display_vi: string }[]
  >;
};

export type AiUsage = {
  month: string;
  generation_count: number;
  qa_message_count: number;
  limit: number | null;
  remaining: number | null;
  unlimited?: boolean;
  price_vnd: number;
  generate_price_vnd?: number;
  model: string;
  openai_configured: boolean;
};

export type AiWorkoutResult = {
  plan: unknown;
  plan_id?: number | null;
  share_token?: string | null;
  share_url_path?: string | null;
  view_path?: string | null;
  usage?: AiUsage;
  code_applied?: boolean;
};

export const aiApi = {
  /** Public stub; send token if present so logged-in users stay attributed. */
  usage: () => apiFetch<AiUsage>("/ai/usage", {}, { auth: true, requireAuth: false }),
  familiarizationCatalog: () =>
    apiFetch<FamiliarizationCatalog>("/ai/familiarization-catalog", {}, { auth: false }),
  fitnessTestAdvice: (body: {
    gender: string;
    offer: string;
    fitness_baseline?: FitnessBaseline | null;
    stretch_completed: boolean;
    feeling?: string;
  }) =>
    apiFetch<{
      overall_failed: boolean;
      stretch_failed: boolean;
      package_level: "basic" | "advanced";
      package_pass: boolean;
      checks: Record<string, boolean | null>;
      not_met: string[];
      standards: { key: string; label_vi: string; display_vi: string }[];
      advice_vi: string[];
      used_openai: boolean;
      recommended_path?: string;
    }>("/ai/fitness-test/advice", { method: "POST", body: JSON.stringify(body) }, { auth: false }),
  generateWorkout: (body: WorkoutScheduleRequest) =>
    apiFetch<AiWorkoutResult>(
      "/ai/generate-workout-schedule",
      { method: "POST", body: JSON.stringify(body) },
      { auth: true, requireAuth: false },
    ),
};

export type FeedbackCategory =
  | "equipment"
  | "workout_plan"
  | "meal_plan"
  | "food_catalog"
  | "exercise_catalog"
  | "knowledge"
  | "trainer"
  | "other";

export const feedbackApi = {
  submit: (payload: { category: FeedbackCategory; content: string; plan_url?: string }) =>
    apiFetch<{ id: number; category: string; title: string; message: string }>(
      "/feedback",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: true, requireAuth: false },
    ),

  contactTrainer: (payload: {
    full_name: string;
    phone_zalo: string;
    email?: string;
    message?: string;
  }) =>
    apiFetch<{ id: number; message: string }>(
      "/contact/trainer",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: false },
    ),
};
