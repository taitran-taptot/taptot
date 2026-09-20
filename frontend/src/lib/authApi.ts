import {
  clearAuth,
  getAccessToken,
  getRefreshToken,
  saveAuth,
  authHeaders,
  type AuthUser,
  type TokenPair,
} from "./auth";
import { API_BASE_DIRECT } from "./config";
import { apiFetch, errorMessage, handleUnauthorized, LOGOUT_EVENT } from "./http";

async function postPublic<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) }, { auth: false });
}

export const authApi = {
  register: (email: string, password: string, display_name: string, role: "user" | "trainer" = "user") =>
    postPublic<TokenPair>("/auth/register", { email, password, display_name, role }),

  login: (email: string, password: string) =>
    postPublic<TokenPair>("/auth/login", { email, password }),

  logout: async () => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await apiFetch(
          "/auth/logout",
          { method: "POST", body: JSON.stringify({ refresh_token: refresh }) },
          { auth: true, requireAuth: false },
        );
      } catch {
        /* ignore */
      }
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

  me: () => apiFetch<AuthUser>("/auth/me", {}, { auth: true }),

  changePassword: (current_password: string, new_password: string) =>
    apiFetch<{ message: string }>(
      "/auth/change-password",
      { method: "POST", body: JSON.stringify({ current_password, new_password }) },
      { auth: true },
    ),

  loginAndSave: async (email: string, password: string) => {
    const tokens = await authApi.login(email, password);
    saveAuth(tokens);
    const user = await authApi.me();
    saveAuth(tokens, user);
    await claimGuestPlansAfterAuth();
    return user;
  },

  registerAndSave: async (
    email: string,
    password: string,
    display_name: string,
    role: "user" | "trainer" = "user",
  ) => {
    const tokens = await authApi.register(email, password, display_name, role);
    saveAuth(tokens);
    const user = await authApi.me();
    saveAuth(tokens, user);
    await claimGuestPlansAfterAuth();
    return user;
  },
};

/** Gắn lịch guest trên thiết bị vào tài khoản vừa đăng nhập/đăng ký. */
export async function claimGuestPlansAfterAuth(): Promise<void> {
  try {
    const { getGuestPlanTokens, saveGuestPlanTokens, clearGuestPlanTokens } = await import("./guestPlans");
    const tokens = getGuestPlanTokens();
    if (!tokens.length || !getAccessToken()) return;
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
    | "advanced_foundation"
    | string
    | null;
  /** ISO weekday 1=Mon … 7=Sun */
  preferred_weekdays?: number[];
  preferred_start_time?: string | null;
  redeem_code?: string | null;
}

export type FamiliarizationCatalog = {
  duration_weeks: number;
  duration_days?: number;
  paths: {
    key: "first_push_pull" | "basic_foundation" | "advanced_foundation";
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
  model: string;
  openai_configured: boolean;
};

export type AiWorkoutResult = {
  plan: unknown;
  plan_id?: number | null;
  share_token?: string | null;
  share_url_path?: string | null;
  usage?: AiUsage;
  code_applied?: boolean;
};

export type ChatHistoryMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
};

export type ChatHistory = {
  conversation_id: string;
  messages: ChatHistoryMessage[];
};

export type ChatStreamHandlers = {
  onStatus?: (label: string) => void;
  onDelta?: (text: string) => void;
  onDone?: (info: { conversation_id: string; message_id?: number }) => void;
  signal?: AbortSignal;
};

function parseSseChunk(buffer: string): { events: { event: string; data: unknown }[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  const events: { event: string; data: unknown }[] = [];
  for (const block of parts) {
    if (!block.trim()) continue;
    let event = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) continue;
    const raw = dataLines.join("\n");
    let data: unknown = raw;
    try {
      data = JSON.parse(raw);
    } catch {
      data = { text: raw };
    }
    events.push({ event, data });
  }
  return { events, rest };
}

async function streamChat(
  body: { message: string; conversation_id?: string | null },
  handlers: ChatStreamHandlers,
): Promise<void> {
  if (!getAccessToken()) {
    handleUnauthorized();
    throw new Error("Vui lòng đăng nhập.");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE_DIRECT}/ai/chat`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: handlers.signal,
    });
  } catch (err) {
    if (handlers.signal?.aborted) throw err;
    throw new Error("Không kết nối được API. Kiểm tra backend đang chạy rồi thử lại.");
  }
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(errorMessage(data, res.status === 429 ? "Bạn hỏi hơi nhanh. Thử lại sau." : "Không gửi được tin nhắn."));
  }

  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) {
    const data = (await res.json()) as { reply?: string; conversation_id?: string; message_id?: number };
    if (data.reply) handlers.onDelta?.(data.reply);
    handlers.onDone?.({ conversation_id: data.conversation_id || "", message_id: data.message_id });
    return;
  }

  if (!res.body) {
    throw new Error("Không nhận được phản hồi từ trợ lý.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawDone = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseChunk(buffer);
    buffer = parsed.rest;
    for (const ev of parsed.events) {
      const data = (ev.data || {}) as Record<string, unknown>;
      if (ev.event === "status") {
        handlers.onStatus?.(String(data.label_vi || "Đang soạn…"));
      } else if (ev.event === "delta") {
        handlers.onDelta?.(String(data.text || ""));
      } else if (ev.event === "done") {
        sawDone = true;
        handlers.onDone?.({
          conversation_id: String(data.conversation_id || ""),
          message_id: typeof data.message_id === "number" ? data.message_id : undefined,
        });
      } else if (ev.event === "error") {
        throw new Error(String(data.message || "Có lỗi khi trả lời."));
      }
    }
  }
  if (!sawDone && buffer.trim()) {
    const parsed = parseSseChunk(buffer + "\n\n");
    for (const ev of parsed.events) {
      const data = (ev.data || {}) as Record<string, unknown>;
      if (ev.event === "delta") handlers.onDelta?.(String(data.text || ""));
      if (ev.event === "done") {
        handlers.onDone?.({
          conversation_id: String(data.conversation_id || ""),
          message_id: typeof data.message_id === "number" ? data.message_id : undefined,
        });
      }
      if (ev.event === "error") throw new Error(String(data.message || "Có lỗi khi trả lời."));
    }
  }
}

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
  /** Hit FastAPI directly — challenge gen often exceeds Next rewrite proxy timeout (~30s). */
  generateWorkout: (body: WorkoutScheduleRequest) =>
    apiFetch<AiWorkoutResult>(
      "/ai/generate-workout-schedule",
      { method: "POST", body: JSON.stringify(body) },
      { auth: true, requireAuth: false, baseUrl: API_BASE_DIRECT },
    ),
  chatHistory: () => apiFetch<ChatHistory>("/ai/chat/history", {}, { auth: true }),
  chat: streamChat,
};

export const feedbackApi = {
  submit: (payload: { category: "food" | "exercise" | "other"; title: string; content: string }) =>
    apiFetch<{ id: number; category: string; title: string; message: string }>(
      "/feedback",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: true },
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
