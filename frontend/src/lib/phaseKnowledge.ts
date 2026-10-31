import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";

export type PhaseKnowledgeRef = { slug: string; label: string };

export type ExperienceLevel = 1 | 2 | 3;
export type PhaseMonth = 1 | 2 | 3;

const R = {
  readPlan: {
    slug: "cach-doc-lich-tap-quy-uoc-buoi-tap",
    label: "1.9 — Cách đọc lịch tập & Quy ước buổi tập",
  },
  goals: {
    slug: "xac-dinh-muc-tieu-tap-luyen",
    label: "1.0 — Xác định mục tiêu tập luyện",
  },
  muscles: {
    slug: "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
    label: "1.1 — Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
  },
  calories: {
    slug: "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
    label: "1.17 — Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
  },
  tdee: {
    slug: "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
    label: "1.18 — Cách tính TDEE theo mức vận động thực tế",
  },
  macros: {
    slug: "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
    label: "1.19 — Dinh dưỡng đa lượng: Chất đạm (Protein), Tinh bột (Carb) và Chất béo (Fat)",
  },
  warmup: {
    slug: "khoi-dong-warm-up-van-dong-khop-mobility",
    label: "1.5 — Khởi động (Warm-up) & Vận động khớp (Mobility)",
  },
  form: {
    slug: "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
    label: "1.7 — Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
  },
  vif: {
    slug: "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
    label: "1.10 — Ba nút chỉnh: Khối lượng (Volume), Độ nặng (Intensity), Tần suất (Frequency)",
  },
  recovery: {
    slug: "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
    label: "1.14 — Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
  },
  overload: {
    slug: "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
    label: "1.11 — Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
  },
  beginnerDeload: {
    slug: "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
    label: "1.15 — Tuần xả tải nhẹ (Deload) cho người mới",
  },
  soreVsInjury: {
    slug: "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
    label: "1.13 — Đau mỏi cơ (DOMS) và Chấn thương: Cách phân biệt và xử lý",
  },
  glossary: {
    slug: "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
    label: "1.2 — Từ điển thuật ngữ tập luyện cho người mới",
  },
  movementPatterns: {
    slug: "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
    label: "1.3 — Mẫu vận động và cách tăng, giảm độ khó bài tập",
  },
  cardio: {
    slug: "cardio-cho-suc-khoe-va-giam-mo",
    label: "1.22 — Cardio cho sức khỏe và giảm mỡ",
  },
  painGuide: {
    slug: "theo-doi-dau-va-dau-hieu-can-kham",
    label: "1.8 — Theo dõi đau và dấu hiệu cần đi khám",
  },
  hydration: {
    slug: "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
    label: "1.21 — Nước, điện giải và rượu bia khi tập luyện",
  },
  supplements: {
    slug: "thuc-pham-bo-sung-theo-muc-do-bang-chung",
    label: "1.23 — Thực phẩm bổ sung theo mức độ bằng chứng",
  },
  overloadAdv: {
    slug: "toi-uu-progressive-overload-nang-cao",
    label: "1.24 — Tối ưu Quá tải lũy tiến (Progressive Overload)",
  },
  rpe: {
    slug: "rpe-va-rir-trong-tung-set",
    label: "1.25 — RPE và RIR: Nghệ thuật đo lường nỗ lực trong từng hiệp tập",
  },
  volumeMuscle: {
    slug: "quan-ly-volume-theo-nhom-co",
    label: "1.26 — Quản lý Khối lượng tập luyện (Volume) theo từng nhóm cơ",
  },
  deload: {
    slug: "deload-dung-thoi-diem",
    label: "1.27 — Deload đúng thời điểm: Khoa học xả tải để bứt phá thể lực",
  },
  carbCycle: {
    slug: "carb-cycling-co-ban",
    label: "1.31 — Carb Cycling: Phân bổ carbohydrate theo ngày tập và ngày nghỉ",
  },
  refeed: {
    slug: "refeed-va-diet-break",
    label: "1.32 — Refeed và Diet Break: Công cụ hỗ trợ khi siết mỡ",
  },
  mmc: {
    slug: "mind-muscle-connection-nang-cao",
    label: "1.29 — Kết nối Não – Cơ (Mind-Muscle Connection) và Kỹ thuật điều khiển nhịp độ",
  },
  intensityTech: {
    slug: "ky-thuat-drop-set-superset-rest-pause",
    label: "1.30 — Kỹ thuật Cường độ cao: Drop Set, Superset và Rest-Pause",
  },
  periodization: {
    slug: "periodization-co-ban",
    label: "1.28 — Chu kỳ hóa tập luyện cơ bản (Periodization)",
  },
  brace: {
    slug: "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    label: "1.6 — Hít thở, Brace và kiểm soát thân mình khi tập",
  },
  homeGear: {
    slug: "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
    label: "1.4 — Tập tại nhà: Chọn và sử dụng dụng cụ an toàn",
  },
  journal: {
    slug: "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
    label: "1.12 — Theo dõi tiến bộ và sử dụng nhật ký tập luyện",
  },
  portions: {
    slug: "uoc-luong-khau-phan-va-an-uong-thuc-te",
    label: "1.20 — Ước lượng khẩu phần và áp dụng dinh dưỡng vào đời sống",
  },
  mistakes: {
    slug: "nhung-sai-lam-pho-bien-khi-moi-tap",
    label: "1.16 — Những sai lầm phổ biến khi mới bắt đầu tập luyện",
  },
} as const satisfies Record<string, PhaseKnowledgeRef>;

type KnowledgeKey = keyof typeof R;
type GoalBucket = "lose" | "gain" | "maintain";
type ActivityBucket = "sedentary" | "light" | "moderate" | "active" | "very_active";

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

function isLabor(activity: ActivityBucket) {
  return activity === "active" || activity === "very_active";
}

function isHome(location: string | null | undefined) {
  const loc = String(location || "").trim().toLowerCase();
  return loc === "home" || loc === "tai_nha" || loc === "at_home";
}

function nutritionKey(bucket: GoalBucket): KnowledgeKey {
  if (bucket === "lose") return "calories";
  if (bucket === "gain") return "macros";
  return "tdee";
}

/** Four articles for one phase, in the order to read that month. */
function keysForPhase(
  level: ExperienceLevel,
  month: PhaseMonth,
  goal: string | null | undefined,
  activity: string | null | undefined,
  location: string | null | undefined,
): KnowledgeKey[] {
  const bucket = goalBucket(goal);
  const job = activityBucket(activity);
  const home = isHome(location);
  const labor = isLabor(job);

  if (level === 1 && month === 1) {
    return ["readPlan", "form", labor ? "painGuide" : "warmup", home ? "homeGear" : "brace"];
  }
  if (level === 1 && month === 2) {
    return ["movementPatterns", "soreVsInjury", labor ? "glossary" : "painGuide", nutritionKey(bucket)];
  }
  if (level === 1 && month === 3) {
    return ["overload", "beginnerDeload", "journal", bucket === "lose" ? "cardio" : "mistakes"];
  }
  if (level === 2 && month === 1) {
    const fourth: KnowledgeKey = job === "sedentary" ? "warmup" : labor ? "painGuide" : "form";
    return ["readPlan", "vif", "recovery", fourth];
  }
  if (level === 2 && month === 2) {
    return ["overload", "rpe", "soreVsInjury", nutritionKey(bucket)];
  }
  if (level === 2 && month === 3) {
    return ["volumeMuscle", "periodization", "journal", bucket === "lose" ? "carbCycle" : "portions"];
  }
  if (level === 3 && month === 1) {
    return ["readPlan", "periodization", "volumeMuscle", "rpe"];
  }
  if (level === 3 && month === 2) {
    const fourth: KnowledgeKey = bucket === "lose" ? "carbCycle" : bucket === "gain" ? "macros" : "recovery";
    return ["overloadAdv", "intensityTech", "mmc", fourth];
  }
  const fourth: KnowledgeKey = bucket === "lose" ? "refeed" : "portions";
  return ["deload", "journal", "supplements", fourth];
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
  opts?: { goal?: string | null; activity?: string | null; location?: string | null },
): PhaseKnowledgeRef[][] {
  const exp = clampExperienceLevel(level);
  return ([1, 2, 3] as PhaseMonth[]).map((month) =>
    keysForPhase(exp, month, opts?.goal, opts?.activity, opts?.location).map((key) => R[key]),
  );
}

export function refsForPhase(
  level: number | null | undefined,
  month: number | null | undefined,
  opts?: { goal?: string | null; activity?: string | null; location?: string | null },
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
