/** Labels for AI plan days / sets / reps (Vietnamese UX). */

import { exerciseMinutes, exerciseMinutesByRestSeconds } from "./labels";
import { parseReps } from "./reps";

export const SPLIT_ROLE_VI: Record<string, string> = {
  fb: "Toàn thân",
  fb_a: "Toàn thân A",
  fb_b: "Toàn thân B",
  upper: "Thân trên",
  lower: "Thân dưới",
  push: "Đẩy (ngực – vai – tay sau)",
  pull: "Kéo (lưng – tay trước)",
  legs: "Chân",
  chest: "Ngực",
  back: "Lưng",
  shoulders: "Vai",
  arms: "Tay",
  quads: "Đùi trước",
  posterior: "Mặt sau (lưng – mông – đùi sau)",
  anterior: "Mặt trước (ngực – bụng – đùi trước)",
  weak: "Điểm yếu",
  conditioning: "Cardio / đốt mỡ nhẹ",
  recovery: "Phục hồi / giãn cơ",
  test: "Tốt nghiệp",
  a: "Đẩy + plank",
  b: "Chạy",
  c: "Kéo + squat",
  d: "Chạy chất lượng",
  e: "Volume phụ",
  f: "Đẩy nhẹ + plank",
  power: "Sức mạnh",
  hypertrophy: "Tăng cơ",
};

export function splitRoleLabel(role: string | null | undefined): string | null {
  if (!role) return null;
  const key = role.trim().toLowerCase().replace(/\s+/g, "_");
  return SPLIT_ROLE_VI[key] || SPLIT_ROLE_VI[role.trim().toLowerCase()] || null;
}

/** Overview chip: Đẩy · Kéo · Chân — no parenthetical muscle lists. */
export function splitRoleShortLabel(role: string | null | undefined): string | null {
  const full = splitRoleLabel(role);
  if (!full) return null;
  return full
    .replace(/\s*\([^)]*\)\s*/g, "")
    .replace(/\s*\/\s*.+$/, "")
    .trim();
}

/** Map English split tokens embedded in day titles (Push / Pull / Legs…). */
const TITLE_SPLIT_EN: Record<string, string> = {
  Push: "Đẩy",
  Pull: "Kéo",
  Legs: "Chân",
  Upper: "Thân trên",
  Lower: "Thân dưới",
  "Full Body": "Toàn thân",
  FullBody: "Toàn thân",
  Cardio: "Cardio",
  "Cardio-Core": "Cardio · Core",
};

/** Replace English split names in plan day titles for display. */
export function localizePlanDayTitle(title: string | null | undefined): string {
  if (!title?.trim()) return "";
  let out = title.trim();
  // Prefer longer keys first
  const keys = Object.keys(TITLE_SPLIT_EN).sort((a, b) => b.length - a.length);
  for (const en of keys) {
    const vi = TITLE_SPLIT_EN[en];
    out = out.replace(new RegExp(`\\b${en.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "gi"), vi);
  }
  return out;
}

/** Drop system timestamp from AI plan titles for a friendlier hero. */
export function friendlyPlanTitle(
  title: string | null | undefined,
  opts?: { challenge?: boolean; homeFoundation?: boolean },
): string {
  const raw = (title || "").trim() || "Lịch tập TAPTOT";
  const withoutTs = raw
    .replace(/\s+\d{1,2}\/\d{1,2}\/\d{2,4}(?:\s+\d{1,2}:\d{2})?\s*$/u, "")
    .trim();
  const base = withoutTs || raw;
  if (opts?.homeFoundation && !/xây nền|từ con số 0/i.test(base)) {
    return `${base} · Xây nền từ số 0`;
  }
  if (opts?.challenge && !/100\s*ngày/i.test(base)) {
    return `${base} · Thử thách 100 ngày`;
  }
  return base;
}

/** Soften engine jargon for end-user copy (overview / advice). */
export function softenPlanCopy(text: string): string {
  return text
    .replace(/Master\s*`?PPL`?/gi, "nhóm buổi Đẩy · Kéo · Chân")
    .replace(/Master\s*`[^`]+`/gi, "lịch mẫu TAPTOT")
    .replace(/\bPPLUL\b/gi, "5 buổi xen kẽ")
    .replace(/\bLULU\b/gi, "4 buổi thân dưới · thân trên")
    .replace(/\bCardio-Core\b/gi, "cardio · core")
    .replace(/\bPPL\b/gi, "Đẩy · Kéo · Chân")
    .replace(/\bLISS\b/g, "cardio nhẹ")
    .replace(/Progressive\s+Overload/gi, "tăng dần tải")
    .replace(/\bWarm-?ups?\b/gi, "khởi động")
    .replace(/\bMobility\b/gi, "độ linh hoạt")
    .replace(/\bFrequency\b/gi, "tần suất")
    .replace(/\bhypertrophy\b/gi, "tăng cơ")
    .replace(/\bdeload\b/gi, "tuần tập nhẹ")
    .replace(/\bvolume\b/gi, "khối lượng tập")
    .replace(/\bintensity\b/gi, "cường độ")
    .replace(/\bcompound\b/gi, "bài đa khớp")
    .replace(/\bisolation\b/gi, "bài đơn khớp")
    .replace(/\bstrength\b/gi, "ngày tập nặng")
    .replace(/\bblock\b/gi, "giai đoạn")
    .replace(/\bRPE\b/g, "mức nặng cảm nhận")
    .replace(/\bRIR\b/g, "số cái còn dư")
    .replace(/\bForm\b/g, "kỹ thuật")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/** Hide tips that are irrelevant or too engine-like for beginners. */
export function shouldShowAdviceTip(tip: string, sessionsPerWeek?: number | null): boolean {
  const t = tip.trim();
  if (!t) return false;
  if (/PPLUL|LULU|Cardio-Core|set\/tuần|pattern bắt buộc|volume tuần bị kẹp/i.test(t)) {
    if (sessionsPerWeek != null && sessionsPerWeek <= 4) return false;
  }
  if (/Master\s*`|thời lượng buổi giữ theo lựa chọn/i.test(t)) return false;
  return true;
}

/** Minutes for one exercise — same rounding as PlanDetailEditor / backend generate. */
export function estimatePlanExerciseMinutesRaw(ex: {
  sets: number;
  reps?: string | number | null;
  rest_seconds?: number | null;
  body_part?: string | null;
}): number {
  const parsed = parseReps(ex.reps);
  const rest = ex.rest_seconds ?? 0;
  if (parsed.mode === "minutes") {
    const work = ex.sets * parsed.value;
    const restMin = Math.max(0, rest / 60);
    return work + Math.max(0, ex.sets - 1) * restMin;
  }
  if (parsed.mode === "seconds") {
    return (ex.sets * parsed.value + Math.max(0, ex.sets - 1) * rest) / 60;
  }
  if (rest > 0) {
    return exerciseMinutesByRestSeconds(ex.sets, rest);
  }
  if (ex.body_part) return exerciseMinutes(ex.body_part, ex.sets);
  return ex.sets * 2;
}

export function estimatePlanExerciseMinutes(ex: {
  sets: number;
  reps?: string | number | null;
  rest_seconds?: number | null;
  body_part?: string | null;
}): number {
  return Math.max(1, Math.round(estimatePlanExerciseMinutesRaw(ex)));
}

const DAY_SECTION_ORDER = ["warmup", "main", "cardio", "cooldown"] as const;

function orderPlanDayExercises<T extends { section?: string | null }>(exercises: T[]): T[] {
  if (!exercises.some((ex) => ex.section)) return exercises;
  return DAY_SECTION_ORDER.flatMap((sec) =>
    exercises.filter((ex) => (ex.section || "main") === sec),
  );
}

/** Walk / set up the next machine. 0 when the next row is the same exercise. */
export const EXERCISE_TRANSITION_MINUTES = 1;

export function estimateExerciseTransitionMinutes(
  exercises: Array<{ exercise_id?: number | null; section?: string | null }>,
): number {
  const ordered = orderPlanDayExercises(exercises);
  let extra = 0;
  for (let i = 0; i < ordered.length - 1; i += 1) {
    const a = ordered[i];
    const b = ordered[i + 1];
    const ida = a.exercise_id ?? 0;
    const idb = b.exercise_id ?? 0;
    if (ida && idb && ida === idb) continue;
    const sa = a.section || "main";
    const sb = b.section || "main";
    if (sa === "cooldown" || sb === "cooldown") continue;
    extra += EXERCISE_TRANSITION_MINUTES;
  }
  return extra;
}

export function estimatePlanDayMinutes(
  exercises: Array<{
    exercise_id?: number | null;
    section?: string | null;
    sets: number;
    reps?: string | number | null;
    rest_seconds?: number | null;
    body_part?: string | null;
  }>,
): number {
  const ordered = orderPlanDayExercises(exercises);
  const work = ordered.reduce((sum, ex) => sum + estimatePlanExerciseMinutesRaw(ex), 0);
  return Math.round(work + estimateExerciseTransitionMinutes(ordered));
}

/** Soften jargon on the 3 foundation curricula (session tab copy). */
export function localizeWorkoutCopy(text: string): string {
  if (!text?.trim()) return text || "";
  return text
    .replace(/\s*\((?:Inverted Row|Hollow Body Hold|Good Morning)\)/gi, "")
    .replace(/inverted\s*row/gi, "kéo người nằm (bàn/xà)")
    .replace(/\binverted\b/gi, "kéo người nằm")
    .replace(/Zone\s*2/gi, "nhịp vừa (nói chuyện được)")
    .replace(/RIR\s*(\d+(?:\s*[–\-]\s*\d+)?)/gi, "còn dư $1 cái")
    .replace(/\bRIR\b/g, "còn dư")
    .replace(/Bulgarian(?:\s+split\s+squat)?/gi, "lunge chân sau kê ghế")
    .replace(/hip thrust/gi, "đẩy hông")
    .replace(/full ROM/gi, "hết biên độ")
    .replace(/\bdeload\b/gi, "buổi tập nhẹ")
    .replace(/\bAMRAP\b/gi, "làm tối đa")
    .replace(/\brehearsal\b/gi, "tập thử")
    .replace(/\breps\b/gi, "lần")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function repsAlreadyHasUnit(reps: string): boolean {
  const s = reps.trim().toLowerCase();
  if (!s || s === "—") return false;
  if (/(phút|phut|giây|giay|lần|km|mục tiêu|hoặc|chân)/i.test(s)) return true;
  return /[a-zà-ỹ]/i.test(s.replace(/[x×]/gi, ""));
}

/** e.g. "3 hiệp × 12 lần" or "10 phút" for cardio */
export function formatSetsReps(
  sets: number,
  reps: string | number | null | undefined,
  opts?: { foundation?: boolean },
): string {
  const raw = reps == null || reps === "" ? "" : String(reps).trim();
  const display = opts?.foundation ? localizeWorkoutCopy(raw) : raw;
  const s = display.toLowerCase();
  const minutes = s.match(/^(\d+)\s*(p|phút|phut|min|mins|m)$/i);
  if (minutes) {
    const n = minutes[1];
    return sets > 1 ? `${sets} hiệp × ${n} phút` : `${n} phút`;
  }
  const seconds = s.match(/^(\d+)\s*(s|sec|secs|giây|giay)$/i);
  if (seconds) {
    return `${sets} hiệp × ${seconds[1]} giây`;
  }
  const r = display || "—";
  if (opts?.foundation && repsAlreadyHasUnit(r)) {
    return `${sets} hiệp × ${r}`;
  }
  return `${sets} hiệp × ${r} lần`;
}

/** Reads the sessions-per-week figure out of a plan description, e.g. "3 buổi / tuần". */
export function parseSessionsPerWeek(desc: string | null | undefined): number | null {
  if (!desc) return null;
  const m = desc.match(/(\d+)\s*buổi\s*\/\s*tuần/i);
  return m ? Number(m[1]) : null;
}

/** Advanced fitness challenge plans are view-only: no download / share. */
export function isFitnessAdvancedPlan(plan: {
  insights?: { challenge_kind?: string | null; generation_mode?: string | null } | null;
}): boolean {
  const kind = plan.insights?.challenge_kind;
  const mode = plan.insights?.generation_mode;
  return kind === "fitness_advanced" || mode === "fitness_advanced";
}

/** Rest in seconds — whole minutes as "X phút", 90s as "1 phút 30 giây". */
export function formatRest(restSeconds: number | null | undefined): string | null {
  if (restSeconds == null || restSeconds <= 0) return null;
  if (restSeconds >= 120 && restSeconds % 60 === 0) {
    return `nghỉ ${restSeconds / 60} phút`;
  }
  if (restSeconds >= 60 && restSeconds % 60 !== 0) {
    const mins = Math.floor(restSeconds / 60);
    const secs = restSeconds % 60;
    return `nghỉ ${mins} phút ${secs} giây`;
  }
  return `nghỉ ${restSeconds} giây`;
}
