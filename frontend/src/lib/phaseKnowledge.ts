import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";

export type PhaseKnowledgeRef = { slug: string; label: string };

export type ExperienceLevel = 1 | 2 | 3;
export type PhaseMonth = 1 | 2 | 3;

const R = {
  readPlan: {
    slug: "cach-doc-lich-tap-quy-uoc-buoi-tap",
    label: "Cách đọc lịch tập & Quy ước buổi tập",
  },
  goals: {
    slug: "xac-dinh-muc-tieu-tap-luyen",
    label: "Xác định mục tiêu tập luyện",
  },
  muscles: {
    slug: "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
    label: "Bản đồ các nhóm cơ chính & Cơ chế chuyển động",
  },
  calories: {
    slug: "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
    label: "Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo",
  },
  tdee: {
    slug: "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
    label: "Cách tính TDEE theo mức vận động thực tế",
  },
  macros: {
    slug: "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
    label: "Dinh dưỡng đa lượng: Chất đạm (Protein), Tinh bột (Carb) và Chất béo (Fat)",
  },
  warmup: {
    slug: "khoi-dong-warm-up-van-dong-khop-mobility",
    label: "Khởi động (Warm-up) & Vận động khớp (Mobility)",
  },
  form: {
    slug: "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
    label: "Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp",
  },
  vif: {
    slug: "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
    label: "Ba nút chỉnh: Khối lượng (Volume), Độ nặng (Intensity), Tần suất (Frequency)",
  },
  recovery: {
    slug: "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
    label: "Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển",
  },
  overload: {
    slug: "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
    label: "Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản",
  },
  beginnerDeload: {
    slug: "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
    label: "Tuần xả tải nhẹ (Deload) cho người mới",
  },
  soreVsInjury: {
    slug: "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
    label: "Đau mỏi cơ (DOMS) và Chấn thương: Cách phân biệt và xử lý",
  },
  glossary: {
    slug: "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
    label: "Từ điển thuật ngữ tập luyện cho người mới",
  },
  movementPatterns: {
    slug: "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
    label: "Mẫu vận động và cách tăng, giảm độ khó bài tập",
  },
  cardio: {
    slug: "cardio-cho-suc-khoe-va-giam-mo",
    label: "Cardio cho sức khỏe và giảm mỡ",
  },
  painGuide: {
    slug: "theo-doi-dau-va-dau-hieu-can-kham",
    label: "Theo dõi đau và dấu hiệu cần đi khám",
  },
  hydration: {
    slug: "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
    label: "Nước, điện giải và rượu bia khi tập luyện",
  },
  supplements: {
    slug: "thuc-pham-bo-sung-theo-muc-do-bang-chung",
    label: "Thực phẩm bổ sung theo mức độ bằng chứng",
  },
  overloadAdv: {
    slug: "toi-uu-progressive-overload-nang-cao",
    label: "Tối ưu Quá tải lũy tiến (Progressive Overload)",
  },
  rpe: {
    slug: "rpe-va-rir-trong-tung-set",
    label: "RPE và RIR: Nghệ thuật đo lường nỗ lực trong từng hiệp tập",
  },
  volumeMuscle: {
    slug: "quan-ly-volume-theo-nhom-co",
    label: "Quản lý Khối lượng tập luyện (Volume) theo từng nhóm cơ",
  },
  deload: {
    slug: "deload-dung-thoi-diem",
    label: "Deload đúng thời điểm: Khoa học xả tải để bứt phá thể lực",
  },
  carbCycle: {
    slug: "carb-cycling-co-ban",
    label: "Carb Cycling: Phân bổ carbohydrate theo ngày tập và ngày nghỉ",
  },
  refeed: {
    slug: "refeed-va-diet-break",
    label: "Refeed và Diet Break: Công cụ hỗ trợ khi siết mỡ",
  },
  mmc: {
    slug: "mind-muscle-connection-nang-cao",
    label: "Kết nối Não – Cơ (Mind-Muscle Connection) và Kỹ thuật điều khiển nhịp độ",
  },
  intensityTech: {
    slug: "ky-thuat-drop-set-superset-rest-pause",
    label: "Kỹ thuật Cường độ cao: Drop Set, Superset và Rest-Pause",
  },
  periodization: {
    slug: "periodization-co-ban",
    label: "Chu kỳ hóa tập luyện cơ bản (Periodization)",
  },
  brace: {
    slug: "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    label: "Hít thở, Brace và kiểm soát thân mình khi tập",
  },
  homeGear: {
    slug: "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
    label: "Tập tại nhà: Chọn và sử dụng dụng cụ an toàn",
  },
  journal: {
    slug: "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
    label: "Theo dõi tiến bộ và sử dụng nhật ký tập luyện",
  },
  portions: {
    slug: "uoc-luong-khau-phan-va-an-uong-thuc-te",
    label: "Ước lượng khẩu phần và áp dụng dinh dưỡng vào đời sống",
  },
  mistakes: {
    slug: "nhung-sai-lam-pho-bien-khi-moi-tap",
    label: "Những sai lầm phổ biến khi mới bắt đầu tập luyện",
  },
} as const satisfies Record<string, PhaseKnowledgeRef>;

type KnowledgeKey = keyof typeof R;
type GoalBucket = "lose" | "gain" | "maintain";
type JobGroup = "sit" | "walk" | "heavy";

function goalBucket(goal: string | null | undefined): GoalBucket {
  const g = String(goal || "").trim().toLowerCase();
  if (g === "gain_weight" || g === "gain_muscle") return "gain";
  if (g === "lose_weight") return "lose";
  return "maintain";
}

function jobGroup(activity: string | null | undefined): JobGroup {
  const job = String(activity || "").trim().toLowerCase();
  if (job === "sedentary") return "sit";
  if (job === "active" || job === "very_active") return "heavy";
  return "walk";
}

function nutritionKey(bucket: GoalBucket): KnowledgeKey {
  if (bucket === "lose") return "calories";
  if (bucket === "gain") return "macros";
  return "tdee";
}

function phaseOneNutrition(level: ExperienceLevel, job: JobGroup, bucket: GoalBucket): KnowledgeKey {
  if ((level === 2 || level === 3) && job === "walk" && bucket === "gain") return "tdee";
  if ((level === 2 || level === 3) && job === "walk" && bucket === "maintain") return "calories";
  return nutritionKey(bucket);
}

function phaseOne(level: ExperienceLevel, job: JobGroup, bucket: GoalBucket): KnowledgeKey[] {
  const nutrition = phaseOneNutrition(level, job, bucket);
  if (level === 1) {
    if (job === "sit") return ["readPlan", "warmup", "form", nutrition];
    if (job === "heavy") return ["readPlan", "painGuide", "brace", nutrition];
    return ["readPlan", "form", "homeGear", nutrition];
  }
  if (level === 2) {
    const third: KnowledgeKey = job === "sit" ? "warmup" : job === "heavy" ? "painGuide" : "form";
    return ["readPlan", "vif", third, nutrition];
  }
  const third: KnowledgeKey = job === "sit" ? "rpe" : job === "heavy" ? "painGuide" : "volumeMuscle";
  return ["readPlan", "periodization", third, nutrition];
}

function phaseTwo(level: ExperienceLevel, job: JobGroup, bucket: GoalBucket): KnowledgeKey[] {
  if (level === 1) {
    if (job === "heavy") return ["movementPatterns", "glossary", "recovery", "portions"];
    return ["movementPatterns", "soreVsInjury", "glossary", "portions"];
  }
  if (level === 2) {
    if (job === "sit") {
      const fourth: KnowledgeKey = bucket === "lose" ? "portions" : "soreVsInjury";
      return ["overload", "rpe", "form", fourth];
    }
    if (job === "heavy") return ["overload", "form", "soreVsInjury", "portions"];
    return ["overload", "rpe", "soreVsInjury", "portions"];
  }
  if (job === "sit") {
    const fourth: KnowledgeKey = bucket === "lose" ? "portions" : "hydration";
    return ["overloadAdv", "mmc", "intensityTech", fourth];
  }
  if (job === "heavy") return ["overloadAdv", "mmc", "soreVsInjury", "portions"];
  const fourth: KnowledgeKey = bucket === "lose" ? "portions" : "hydration";
  return ["overloadAdv", "mmc", "rpe", fourth];
}

function phaseThree(level: ExperienceLevel, job: JobGroup, bucket: GoalBucket): KnowledgeKey[] {
  if (level === 1) {
    const fourth: KnowledgeKey = bucket === "lose" ? (job === "heavy" ? "hydration" : "cardio") : "mistakes";
    return ["overload", "beginnerDeload", "journal", fourth];
  }
  if (level === 2) {
    if (job === "heavy") {
      const fourth: KnowledgeKey = bucket === "lose" ? "hydration" : bucket === "gain" ? "tdee" : "calories";
      return ["volumeMuscle", "recovery", "journal", fourth];
    }
    let fourth: KnowledgeKey;
    if (bucket === "lose") fourth = job === "sit" ? "carbCycle" : "cardio";
    else if (job === "walk") fourth = bucket === "gain" ? "macros" : "tdee";
    else fourth = "portions";
    return ["volumeMuscle", "periodization", "journal", fourth];
  }
  if (job === "sit") {
    if (bucket === "lose") return ["deload", "journal", "carbCycle", "refeed"];
    return ["deload", "journal", "portions", "supplements"];
  }
  if (job === "walk") {
    if (bucket === "lose") return ["deload", "journal", "carbCycle", "refeed"];
    if (bucket === "gain") return ["deload", "journal", "portions", "macros"];
    return ["deload", "journal", "portions", "tdee"];
  }
  if (bucket === "lose") return ["deload", "recovery", "hydration", "refeed"];
  return ["deload", "recovery", "hydration", "supplements"];
}

/** Four articles for one phase, in the order to read that month. Location does not change the list. */
function keysForPhase(
  level: ExperienceLevel,
  month: PhaseMonth,
  goal: string | null | undefined,
  activity: string | null | undefined,
  _location: string | null | undefined,
): KnowledgeKey[] {
  const bucket = goalBucket(goal);
  const job = jobGroup(activity);
  const phases = [phaseOne(level, job, bucket), phaseTwo(level, job, bucket), phaseThree(level, job, bucket)];
  return phases[month - 1];
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
