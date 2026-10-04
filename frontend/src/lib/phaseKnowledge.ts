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
    label: "2.0 — Tối ưu Progressive Overload nâng cao",
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
    label: "2.6 — Mind-Muscle Connection nâng cao",
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

const PHASE_KNOWLEDGE: Record<ExperienceLevel, Record<PhaseMonth, PhaseKnowledgeRef[]>> = {
  1: {
    1: [
      R.readPlan,
      R.glossary,
      R.goals,
      R.movementPatterns,
      R.form,
      R.warmup,
      R.soreVsInjury,
      R.painGuide,
    ],
    2: [R.calories, R.tdee, R.macros, R.recovery, R.hydration, R.muscles, R.cardio],
    3: [R.vif, R.overload, R.beginnerDeload, R.supplements],
  },
  2: {
    1: [R.tdee, R.recovery, R.vif, R.form],
    2: [R.overload, R.rpe, R.deload],
    3: [R.volumeMuscle, R.periodization, R.carbCycle],
  },
  3: {
    1: [R.periodization, R.volumeMuscle, R.rpe],
    2: [R.overloadAdv, R.carbCycle, R.intensityTech],
    3: [R.deload, R.refeed, R.mmc],
  },
};

export function clampExperienceLevel(raw: number | null | undefined): ExperienceLevel {
  const n = Math.round(Number(raw));
  if (n >= 3) return 3;
  if (n === 2) return 2;
  return 1;
}

export function refsForPhase(
  level: number | null | undefined,
  month: number | null | undefined,
): PhaseKnowledgeRef[] {
  const exp = clampExperienceLevel(level);
  if (month !== 1 && month !== 2 && month !== 3) return [];
  return PHASE_KNOWLEDGE[exp][month];
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
