import { GIF_BASE, MEDIA_BASE } from "./config";

export function difficultyLabel(d: string | number): { vi: string; cls: string } {
  if (typeof d === "number" || (typeof d === "string" && /^\d+$/.test(d))) {
    const n = Number(d);
    const map: Record<number, { vi: string; cls: string }> = {
      1: { vi: "Rất cơ bản", cls: "badge-easy" },
      2: { vi: "Cơ bản", cls: "badge-easy" },
      3: { vi: "Trung cấp", cls: "badge-mid" },
      4: { vi: "Nâng cao", cls: "badge-hard" },
      // Legacy 5 (pre-clamp) → treat as nâng cao
      5: { vi: "Nâng cao", cls: "badge-hard" },
    };
    return map[n] || { vi: String(d), cls: "badge-gray" };
  }
  const map: Record<string, { vi: string; cls: string }> = {
    beginner: { vi: "Cơ bản", cls: "badge-easy" },
    intermediate: { vi: "Trung cấp", cls: "badge-mid" },
    advanced: { vi: "Nâng cao", cls: "badge-hard" },
    expert: { vi: "Nâng cao", cls: "badge-hard" },
  };
  return map[d] || { vi: d || "—", cls: "badge-gray" };
}

/** Vai trò bài trong buổi: compound / isolation / … */
export const MOVEMENT_ROLE_OPTS: { value: string; vi: string; en: string }[] = [
  { value: "compound", vi: "Bài kép (đa khớp)", en: "Compound" },
  { value: "isolation", vi: "Bài đơn (đơn khớp)", en: "Isolation" },
  { value: "resistance", vi: "Kháng lực (tại nhà)", en: "Resistance" },
  { value: "conditioning", vi: "Thể lực", en: "Conditioning" },
  { value: "mobility", vi: "Khởi động / giãn", en: "Mobility" },
  { value: "cardio", vi: "Tim mạch / đốt mỡ nhẹ", en: "Cardio" },
];

export const VENUE_OPTS: { value: string; vi: string; en: string }[] = [
  { value: "gym", vi: "Phòng gym", en: "Gym" },
  { value: "home", vi: "Tại nhà", en: "Home" },
  { value: "both", vi: "Gym & tại nhà", en: "Both" },
];

export const VENUE_LABEL: Record<string, string> = Object.fromEntries(
  VENUE_OPTS.map((o) => [o.value, o.vi]),
);

/** Mẫu chuyển động HLV */
export const MOVEMENT_PATTERN_OPTS: { value: string; vi: string; en: string }[] = [
  { value: "h_push", vi: "Đẩy ngang", en: "Horizontal Push" },
  { value: "h_pull", vi: "Kéo ngang", en: "Horizontal Pull" },
  { value: "v_push", vi: "Đẩy dọc", en: "Vertical Push" },
  { value: "v_pull", vi: "Kéo dọc", en: "Vertical Pull" },
  { value: "squat", vi: "Gập gối (Squat)", en: "Squat / Knee dominant" },
  { value: "hinge", vi: "Gập hông (Hinge)", en: "Hip Hinge" },
  { value: "core", vi: "Core", en: "Core" },
  { value: "other", vi: "Khác", en: "Other" },
];

const _ROLE_MAP = Object.fromEntries(MOVEMENT_ROLE_OPTS.map((o) => [o.value, o]));
const _PATTERN_MAP = Object.fromEntries(MOVEMENT_PATTERN_OPTS.map((o) => [o.value, o]));

export function movementRoleLabel(value: string | null | undefined): { vi: string; en: string } | null {
  if (!value) return null;
  return _ROLE_MAP[value] || { vi: value, en: value };
}

export function movementPatternLabel(value: string | null | undefined): { vi: string; en: string } | null {
  if (!value) return null;
  return _PATTERN_MAP[value] || { vi: value, en: value };
}

export const bodyEmoji: Record<string, string> = {
  back: "🔙",
  cardio: "🏃",
  stretch: "🤸",
  chest: "💪",
  "lower arms": "🤝",
  "lower legs": "🦵",
  neck: "🧣",
  shoulders: "🎽",
  "upper arms": "💪",
  "upper legs": "🦵",
  waist: "🧘",
  "co-lung": "🔙",
  "co-nguc": "💪",
  "co-vai": "🎽",
  "co-tay-truoc": "💪",
  "co-tay-sau": "💪",
  "co-cang-tay": "🤝",
  "co-bung": "🧘",
  "co-mong": "🍑",
  "co-dui-truoc": "🦵",
  "co-dui-sau": "🦵",
  "co-bap-chan": "🦵",
  "toan-than": "🏃",
  // slug sinh từ tên tiếng Anh trong catalog Excel
  "shoulders-deltoids": "🎽",
  biceps: "💪",
  triceps: "💪",
  forearms: "🤝",
  "shoulders-traps": "🎯",
  core: "🧘",
  glutes: "🍑",
  calves: "🦵",
  "full-body": "🏃",
};

export function gifUrl(rel: string | null | undefined): string | null {
  if (!rel) return null;
  if (/^https?:\/\//.test(rel)) return rel;
  if (GIF_BASE) return `${GIF_BASE}/${rel.replace(/^\//, "")}`;
  return mediaUrl(rel);
}

/** Resolve relative media paths (e.g. equipment/dumbbell.jpg) against MEDIA_BASE. */
export function mediaUrl(rel: string | null | undefined): string | null {
  if (!rel) return null;
  if (/^https?:\/\//.test(rel)) return rel;
  return `${MEDIA_BASE}/${rel.replace(/^\//, "")}`;
}

export function viNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 });
}

export function formatVnd(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${Number(v).toLocaleString("vi-VN")} ₫`;
}

// Large muscle groups rest 2 min/set, small muscle groups rest 1 min/set.
const LARGE_MUSCLE_PARTS = new Set([
  "back",
  "chest",
  "upper legs",
  "co-lung",
  "co-nguc",
  "co-dui-truoc",
  "co-dui-sau",
  "toan-than",
  "full-body",
]);

function isLargeMuscle(bodyPart: string): boolean {
  return LARGE_MUSCLE_PARTS.has(bodyPart);
}

function restMinutes(bodyPart: string): number {
  return isLargeMuscle(bodyPart) ? 2 : 1;
}

/** Estimated minutes: 1′ work/set + rest between sets (sets−1). */
export function exerciseMinutes(bodyPart: string, sets: number, restMin?: number): number {
  const rest = restMin ?? restMinutes(bodyPart);
  return sets * 1 + Math.max(0, sets - 1) * rest;
}

export function exerciseMinutesByRest(sets: number, restMin: number): number {
  return sets * 1 + Math.max(0, sets - 1) * restMin;
}

/** Prefer rest_seconds when estimating session length (supports 1.5 min rest). */
export function exerciseMinutesByRestSeconds(sets: number, restSeconds: number): number {
  const restMin = restSeconds > 0 ? restSeconds / 60 : 2;
  return sets * 1 + Math.max(0, sets - 1) * restMin;
}

const EQUIPMENT_CATEGORY_EN: Record<string, string> = {
  "Tạ tự do": "Free Weights",
  "Máy tập": "Machines",
  "Thiết bị Cardio": "Cardio Equipment",
  "Giá đỡ và khung tập": "Racks & Frames",
  "Ghế tập": "Benches",
  "Phụ kiện tập luyện": "Training Accessories",
  "Không dụng cụ": "No Equipment",
  Khác: "Other",
};

/** Public UI is Vietnamese-only. Pass bilingual for admin / HLV tools. */
export function equipmentCategoryLabel(
  category: string | null | undefined,
  bilingual = false,
): string {
  if (!category) return "";
  if (!bilingual) return category;
  const en = EQUIPMENT_CATEGORY_EN[category];
  return en ? `${category} - ${en}` : category;
}
