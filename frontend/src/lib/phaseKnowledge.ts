import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";

export type PhaseKnowledgeRef = { slug: string; label: string };

export type ExperienceLevel = 1 | 2 | 3;
export type PhaseMonth = 1 | 2 | 3;

const R = {
  readPlan: {
    slug: "cach-doc-lich-tap-quy-uoc-buoi-tap",
    label: "1.1 — Cách đọc lịch tập & Quy ước buổi tập",
  },
  goals: {
    slug: "xac-dinh-muc-tieu-tap-luyen",
    label: "1.0 — Xác định mục tiêu tập luyện",
  },
  muscles: {
    slug: "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
    label: "1.2 — Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
  },
  calories: {
    slug: "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
    label: "1.9 — Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
  },
  tdee: {
    slug: "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
    label: "1.10 — Cách tính TDEE theo mức vận động thực tế",
  },
  macros: {
    slug: "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
    label: "1.11 — Dinh dưỡng đa lượng: Protein, Carb và Fat",
  },
  warmup: {
    slug: "khoi-dong-warm-up-van-dong-khop-mobility",
    label: "1.3 — Khởi động (Warm-up) & Vận động khớp (Mobility)",
  },
  form: {
    slug: "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
    label: "1.4 — Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
  },
  vif: {
    slug: "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
    label: "1.5 — Ba nút chỉnh: Volume, Intensity, Frequency",
  },
  recovery: {
    slug: "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
    label: "1.12 — Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
  },
  overload: {
    slug: "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
    label: "1.6 — Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
  },
  beginnerDeload: {
    slug: "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
    label: "1.8 — Tuần xả tải nhẹ (Deload) cho người mới",
  },
  soreVsInjury: {
    slug: "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
    label: "1.7 — Đau mỏi cơ (DOMS) và Chấn thương",
  },
  glossary: {
    slug: "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
    label: "1.13 — Từ điển thuật ngữ tập luyện cho người mới",
  },
  movementPatterns: {
    slug: "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
    label: "1.14 — Mẫu vận động và cách tăng, giảm độ khó bài tập",
  },
  cardio: {
    slug: "cardio-cho-suc-khoe-va-giam-mo",
    label: "1.15 — Cardio cho sức khỏe và giảm mỡ",
  },
  painGuide: {
    slug: "theo-doi-dau-va-dau-hieu-can-kham",
    label: "1.16 — Theo dõi đau và dấu hiệu cần đi khám",
  },
  hydration: {
    slug: "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
    label: "1.17 — Nước, điện giải và rượu bia khi tập luyện",
  },
  supplements: {
    slug: "thuc-pham-bo-sung-theo-muc-do-bang-chung",
    label: "1.18 — Thực phẩm bổ sung theo mức độ bằng chứng",
  },
  overloadAdv: {
    slug: "toi-uu-progressive-overload-nang-cao",
    label: "2.0 — Tối ưu Progressive Overload",
  },
  rpe: {
    slug: "rpe-va-rir-trong-tung-set",
    label: "2.1 — RPE và RIR trong từng set",
  },
  volumeMuscle: {
    slug: "quan-ly-volume-theo-nhom-co",
    label: "2.2 — Quản lý Volume theo nhóm cơ",
  },
  deload: {
    slug: "deload-dung-thoi-diem",
    label: "2.3 — Deload đúng thời điểm",
  },
  carbCycle: {
    slug: "carb-cycling-co-ban",
    label: "2.4 — Carb cycling cơ bản",
  },
  refeed: {
    slug: "refeed-va-diet-break",
    label: "2.5 — Refeed và diet break",
  },
  mmc: {
    slug: "mind-muscle-connection-nang-cao",
    label: "2.6 — Mind-Muscle Connection",
  },
  intensityTech: {
    slug: "ky-thuat-drop-set-superset-rest-pause",
    label: "2.7 — Kỹ thuật Drop set, Superset, Rest-pause",
  },
  periodization: {
    slug: "periodization-co-ban",
    label: "2.8 — Periodization cơ bản",
  },
} as const satisfies Record<string, PhaseKnowledgeRef>;

type KnowledgeKey = keyof typeof R;
type GoalBucket = "lose" | "gain" | "maintain";
type ActivityBucket = "sedentary" | "light" | "moderate" | "active" | "very_active";

const RANKED: Record<ExperienceLevel, Record<PhaseMonth, KnowledgeKey[]>> = {
  1: {
    1: ["readPlan", "form", "glossary", "warmup", "movementPatterns", "soreVsInjury", "painGuide"],
    2: ["calories", "tdee", "macros", "recovery", "hydration", "muscles", "cardio"],
    3: ["overload", "beginnerDeload", "vif", "cardio"],
  },
  2: {
    1: ["vif", "form", "tdee", "recovery", "goals"],
    2: ["overload", "rpe", "deload", "calories", "macros"],
    3: ["volumeMuscle", "periodization", "carbCycle", "recovery"],
  },
  3: {
    1: ["periodization", "volumeMuscle", "rpe", "goals"],
    2: ["overloadAdv", "intensityTech", "carbCycle", "rpe"],
    3: ["deload", "refeed", "mmc", "carbCycle"],
  },
};

const SLOT_B: Record<GoalBucket, Record<PhaseMonth, KnowledgeKey>> = {
  lose: { 1: "goals", 2: "calories", 3: "cardio" },
  gain: { 1: "goals", 2: "macros", 3: "recovery" },
  maintain: { 1: "goals", 2: "tdee", 3: "recovery" },
};

function goalBucket(goal: string | null | undefined): GoalBucket {
  const g = String(goal || "").trim().toLowerCase();
  if (g === "gain_weight" || g === "gain_muscle") return "gain";
  if (g === "lose_weight") return "lose";
  return "maintain";
}

function activityBucket(activity: string | null | undefined): ActivityBucket {
  const a = String(activity || "").trim().toLowerCase();
  if (a === "sedentary" || a === "light" || a === "moderate" || a === "active" || a === "very_active") {
    return a;
  }
  return "moderate";
}

function slotBKey(level: ExperienceLevel, month: PhaseMonth, bucket: GoalBucket): KnowledgeKey {
  if (bucket === "lose" && month === 3) {
    if (level >= 3) return "refeed";
    if (level >= 2) return "carbCycle";
  }
  return SLOT_B[bucket][month];
}

function slotCKey(level: ExperienceLevel, month: PhaseMonth, activity: ActivityBucket): KnowledgeKey {
  if (activity === "sedentary") {
    if (month === 3) return level <= 1 ? "beginnerDeload" : "deload";
    return "warmup";
  }
  if (activity === "light") return "recovery";
  if (activity === "active" || activity === "very_active") {
    return level <= 1 ? "soreVsInjury" : "painGuide";
  }
  return "tdee";
}

function rankedKeys(
  level: ExperienceLevel,
  month: PhaseMonth,
  goal: string | null | undefined,
  activity: string | null | undefined,
): KnowledgeKey[] {
  const skill = RANKED[level][month];
  const ordered: KnowledgeKey[] = [];
  for (const key of [
    skill[0],
    slotBKey(level, month, goalBucket(goal)),
    slotCKey(level, month, activityBucket(activity)),
    ...skill.slice(1),
  ]) {
    if (!ordered.includes(key)) ordered.push(key);
  }
  return ordered;
}

function pickKeys(ranked: KnowledgeKey[], used: Set<KnowledgeKey>, want: number): KnowledgeKey[] {
  const picked: KnowledgeKey[] = [];
  for (const key of ranked) {
    if (used.has(key)) continue;
    picked.push(key);
    used.add(key);
    if (picked.length >= want) break;
  }
  return picked;
}

export function clampExperienceLevel(raw: number | null | undefined): ExperienceLevel {
  const n = Math.round(Number(raw));
  if (n >= 3) return 3;
  if (n === 2) return 2;
  return 1;
}

function knowledgeLabelSortKey(label: string): [number, number, string] {
  const m = /^(\d+)\.(\d+)/.exec(label.trim());
  if (!m) return [99, 99, label];
  return [Number(m[1]), Number(m[2]), label];
}

export function sortKnowledgeRefs<T extends { label: string }>(refs: readonly T[]): T[] {
  return [...refs].sort((a, b) => {
    const [chapterA, articleA, labelA] = knowledgeLabelSortKey(a.label);
    const [chapterB, articleB, labelB] = knowledgeLabelSortKey(b.label);
    if (chapterA !== chapterB) return chapterA - chapterB;
    if (articleA !== articleB) return articleA - articleB;
    return labelA.localeCompare(labelB, "vi");
  });
}

export function refsForChallengePhases(
  level: number | null | undefined,
  opts?: { goal?: string | null; activity?: string | null },
): PhaseKnowledgeRef[][] {
  const exp = clampExperienceLevel(level);
  const used = new Set<KnowledgeKey>();
  const rankedByMonth = ([1, 2, 3] as PhaseMonth[]).map((month) =>
    rankedKeys(exp, month, opts?.goal, opts?.activity),
  );
  const keysByMonth = rankedByMonth.map((ranked) => pickKeys(ranked, used, 3));
  rankedByMonth.forEach((ranked, i) => {
    keysByMonth[i].push(...pickKeys(ranked, used, 1));
  });
  return keysByMonth.map((keys) => keys.map((key) => R[key]));
}

export function refsForPhase(
  level: number | null | undefined,
  month: number | null | undefined,
  opts?: { goal?: string | null; activity?: string | null },
): PhaseKnowledgeRef[] {
  if (month !== 1 && month !== 2 && month !== 3) return [];
  return refsForChallengePhases(level, opts)[month - 1];
}

export function knowledgeHref(slug: string) {
  const s = canonicalizeKnowledgeSlug(slug);
  if (!s) return "/kien-thuc";
  return `/kien-thuc/${encodeURIComponent(s)}`;
}

export function knowledgeSlugFromPathname(pathname: string): string {
  const m = /^\/kien-thuc\/([^/]+)\/?$/.exec(pathname || "");
  if (!m?.[1]) return "";
  try {
    return canonicalizeKnowledgeSlug(decodeURIComponent(m[1]));
  } catch {
    return canonicalizeKnowledgeSlug(m[1]);
  }
}
