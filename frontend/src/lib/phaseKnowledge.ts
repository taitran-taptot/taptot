export type PhaseKnowledgeRef = { slug: string; label: string };

export type ExperienceLevel = 1 | 2 | 3;
export type PhaseMonth = 1 | 2 | 3;

const R = {
  readPlan: {
    slug: "cach-doc-lich-tap",
    label: "Cách đọc lịch tập",
  },
  goals: {
    slug: "10-xc-nh-mc-tiu-tp-luyn",
    label: "1.0 — Xác định mục tiêu tập luyện",
  },
  muscles: {
    slug: "11-hiu-cc-nhm-c-chnh",
    label: "1.1 — Hiểu các nhóm cơ chính",
  },
  calories: {
    slug: "12-calories-thng-d-thm-ht-cn-bng",
    label: "1.2 — Calories: thặng dư, thâm hụt, cân bằng",
  },
  tdee: {
    slug: "13-tnh-tdee-theo-mc-vn-ng",
    label: "1.3 — Tính TDEE theo mức vận động",
  },
  macros: {
    slug: "14-macronutrients-protein-carb-fat",
    label: "1.4 — Macronutrients: Protein, Carb, Fat",
  },
  warmup: {
    slug: "15-warm-up-v-mobility",
    label: "1.5 — Warm-up và Mobility",
  },
  form: {
    slug: "16-k-thut-tp-chun-form",
    label: "1.6 — Kỹ thuật tập chuẩn (Form)",
  },
  vif: {
    slug: "17-volume-intensity-frequency",
    label: "1.7 — Volume, Intensity, Frequency",
  },
  recovery: {
    slug: "18-phc-hi-v-gic-ng",
    label: "1.8 — Phục hồi và giấc ngủ",
  },
  overload: {
    slug: "19-progressive-overload-c-bn",
    label: "1.9 — Progressive Overload cơ bản",
  },
  beginnerDeload: {
    slug: "tuan-nhe-cho-nguoi-moi",
    label: "Tuần nhẹ cho người mới",
  },
  soreVsInjury: {
    slug: "dau-nhuc-va-chan-thuong",
    label: "Đau nhức và chấn thương",
  },
  overloadAdv: {
    slug: "20-ti-u-progressive-overload-nng-cao",
    label: "2.0 — Tối ưu Progressive Overload nâng cao",
  },
  rpe: {
    slug: "21-rpe-v-rir-trong-tng-set",
    label: "2.1 — RPE và RIR trong từng set",
  },
  volumeMuscle: {
    slug: "22-qun-l-volume-theo-nhm-c",
    label: "2.2 — Quản lý Volume theo nhóm cơ",
  },
  deload: {
    slug: "23-deload-ng-thi-im",
    label: "2.3 — Deload đúng thời điểm",
  },
  carbCycle: {
    slug: "24-carb-cycling-c-bn",
    label: "2.4 — Carb cycling cơ bản",
  },
  refeed: {
    slug: "25-refeed-v-diet-break",
    label: "2.5 — Refeed và diet break",
  },
  mmc: {
    slug: "26-mind-muscle-connection-nng-cao",
    label: "2.6 — Mind-Muscle Connection nâng cao",
  },
  intensityTech: {
    slug: "27-k-thut-drop-set-superset-rest-pause",
    label: "2.7 — Kỹ thuật Drop set, Superset, Rest-pause",
  },
  periodization: {
    slug: "28-periodization-c-bn",
    label: "2.8 — Periodization cơ bản",
  },
} as const satisfies Record<string, PhaseKnowledgeRef>;

const PHASE_KNOWLEDGE: Record<ExperienceLevel, Record<PhaseMonth, PhaseKnowledgeRef[]>> = {
  1: {
    1: [R.readPlan, R.goals, R.form, R.warmup, R.calories, R.soreVsInjury],
    2: [R.tdee, R.macros, R.recovery, R.muscles],
    3: [R.vif, R.overload, R.beginnerDeload],
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
  return `/kien-thuc?bai=${encodeURIComponent(slug)}`;
}
