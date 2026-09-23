/** Kit × experience matrix for the 100-day builder fitness step. */

import { collapsePublicEquipmentKeys } from "./equipmentCatalog";
import type { FitnessBaseline } from "./authApi";
import type { ExerciseListItem, Gender } from "./types";

export type ChallengeTestKit = "bar_rings" | "dumbbell" | "band";
export type ChallengeTestSlot = "push" | "pull" | "core" | "squat";
export type ChallengeTestValueKind = "reps" | "seconds" | "reps_kg";

export type ChallengeTestDraft = {
  pushups: string;
  kneePushups: string;
  pushupVariant: string;
  pullups: string;
  pullTestVariant: string;
  pullHoldSeconds: string;
  invertedRows: string;
  plankSeconds: string;
  squats: string;
  dbPressReps: string;
  dbPressKg: string;
  dbRowReps: string;
  dbRowKg: string;
  gobletReps: string;
  gobletKg: string;
  bandLevel: string;
};

export const EMPTY_CHALLENGE_TEST_DRAFT: ChallengeTestDraft = {
  pushups: "",
  kneePushups: "",
  pushupVariant: "standard",
  pullups: "",
  pullTestVariant: "strict",
  pullHoldSeconds: "",
  invertedRows: "",
  plankSeconds: "",
  squats: "",
  dbPressReps: "",
  dbPressKg: "",
  dbRowReps: "",
  dbRowKg: "",
  gobletReps: "",
  gobletKg: "",
  bandLevel: "",
};

export type ChallengeTestMediaSpec = {
  id: string;
  titleVi: string;
  instructionVi: string;
  catalogNameEn: string;
  catalogNameVi: string;
  query: string;
  extraQuery?: string;
  preferNames: string[];
  rejectNames?: string[];
  preferBodyweight: boolean;
  valueKind: ChallengeTestValueKind;
  repsField: keyof ChallengeTestDraft;
  kgField?: keyof ChallengeTestDraft;
  unit: string;
  pushupVariant?: string;
  pullTestVariant?: string;
  showBandLevel?: boolean;
  kgOptional?: boolean;
};

export type ChallengeTestSpec = ChallengeTestMediaSpec & {
  slot: ChallengeTestSlot;
  regression?: ChallengeTestMediaSpec;
  regressionHintVi?: string;
};

export const BAND_LEVEL_OPTS = [
  { value: "", label: "Chưa chọn" },
  { value: "light", label: "Nhẹ" },
  { value: "medium", label: "Vừa" },
  { value: "heavy", label: "Nặng" },
] as const;

const PUSH_REGRESSION_HINT =
  "Nếu bạn chưa chống đẩy được 1 cái đúng form, hãy chuyển tab Chống đẩy quỳ. TAPTOT sẽ lên lịch vừa sức hơn.";

const KNEE_PUSH_REGRESSION: ChallengeTestMediaSpec = {
  id: "knee_pushup_regression",
  titleVi: "Chống đẩy quỳ",
  instructionVi: "Làm tối đa đúng form — để TAPTOT chỉnh số cái chống đẩy trên lịch.",
  catalogNameEn: "Bodyweight Knee Push Ups",
  catalogNameVi: "Chống đẩy chống gối",
  query: "Bodyweight Knee Push Ups",
  extraQuery: "chống đẩy chống gối",
  preferNames: ["bodyweight knee push ups", "chống đẩy chống gối"],
  rejectNames: ["pike", "diamond", "decline"],
  preferBodyweight: true,
  valueKind: "reps",
  repsField: "kneePushups",
  unit: "cái",
  pushupVariant: "knee",
};

const FLOOR_PUSH: ChallengeTestMediaSpec = {
  id: "floor_pushup",
  titleVi: "Chống đẩy",
  instructionVi: "Làm tối đa đúng form — để TAPTOT chỉnh số cái chống đẩy trên lịch.",
  catalogNameEn: "Push Up",
  catalogNameVi: "Chống đẩy",
  query: "Push Up",
  extraQuery: "chống đẩy",
  preferNames: ["push up", "chống đẩy"],
  rejectNames: ["knee", "gối", "pike", "diamond", "decline", "handstand"],
  preferBodyweight: true,
  valueKind: "reps",
  repsField: "pushups",
  unit: "cái",
  pushupVariant: "standard",
};

const PULL_REGRESSION_HINT =
  "Nếu bạn chưa kéo xà được 1 cái đúng form, hãy chuyển tab Chèo vòng treo. TAPTOT sẽ lên lịch vừa sức hơn rồi tăng tiến về kéo xà.";

const RING_ROW: ChallengeTestMediaSpec = {
  id: "ring_row",
  titleVi: "Chèo vòng treo",
  instructionVi: "Làm tối đa đúng form — để TAPTOT chỉnh bài kéo trên lịch.",
  catalogNameEn: "Ring Row",
  catalogNameVi: "Chèo vòng treo",
  query: "Ring Row",
  extraQuery: "chèo vòng treo",
  preferNames: ["ring row", "chèo vòng treo"],
  rejectNames: ["archer"],
  preferBodyweight: true,
  valueKind: "reps",
  repsField: "invertedRows",
  unit: "cái",
  pullTestVariant: "inverted_row",
};

const BAR_PULLUP: ChallengeTestMediaSpec = {
  id: "bar_pullup",
  titleVi: "Kéo xà",
  instructionVi: "Làm tối đa đúng form — để TAPTOT chỉnh số cái kéo xà trên lịch.",
  catalogNameEn: "Pull Ups",
  catalogNameVi: "Kéo xà",
  query: "Pull Ups",
  extraQuery: "kéo xà",
  preferNames: ["pull ups", "pull up", "pull-up", "kéo xà"],
  rejectNames: ["muscle", "1/3", "scapular", "inverted", "ring row", "assisted", "trợ lực"],
  preferBodyweight: true,
  valueKind: "reps",
  repsField: "pullups",
  unit: "cái",
  pullTestVariant: "strict",
};

const PLANK: ChallengeTestSpec = {
  slot: "core",
  id: "plank",
  titleVi: "Plank",
  instructionVi: "Giữ thẳng người hết sức — số giây này để TAPTOT chỉnh thời gian plank trên lịch.",
  catalogNameEn: "Front Plank on Elbows",
  catalogNameVi: "Chống người chống khuỷu",
  query: "Front Plank on Elbows",
  extraQuery: "chống người chống khuỷu",
  preferNames: ["front plank on elbows", "chống người chống khuỷu"],
  preferBodyweight: true,
  valueKind: "seconds",
  repsField: "plankSeconds",
  unit: "giây",
};

const BW_SQUAT: ChallengeTestSpec = {
  slot: "squat",
  id: "bw_squat",
  titleVi: "Squat thể trọng",
  instructionVi: "Làm tối đa đúng form — để TAPTOT chỉnh số cái squat trên lịch.",
  catalogNameEn: "Bodyweight Squat",
  catalogNameVi: "Ngồi xổm không tạ",
  query: "Bodyweight Squat",
  extraQuery: "ngồi xổm không tạ",
  preferNames: ["bodyweight squat", "ngồi xổm không tạ"],
  rejectNames: ["goblet", "front squat", "barbell", "jump", "pistol"],
  preferBodyweight: true,
  valueKind: "reps",
  repsField: "squats",
  unit: "cái",
};

function floorPushWithRegression(id: string, instructionVi: string): ChallengeTestSpec {
  return {
    ...FLOOR_PUSH,
    id,
    slot: "push",
    instructionVi,
    regression: KNEE_PUSH_REGRESSION,
    regressionHintVi: PUSH_REGRESSION_HINT,
  };
}

function barPullWithRegression(): ChallengeTestSpec {
  return {
    ...BAR_PULLUP,
    slot: "pull",
    regression: RING_ROW,
    regressionHintVi: PULL_REGRESSION_HINT,
  };
}

export function kitFromWizardEquipment(slugs: string[]): ChallengeTestKit {
  const keys = new Set(collapsePublicEquipmentKeys(slugs));
  if (keys.has("dumbbell")) return "dumbbell";
  if (keys.has("resistance-band")) return "band";
  return "bar_rings";
}

export function challengeFitnessTests(opts: {
  kit: ChallengeTestKit;
  level: number;
  gender: Gender | null;
}): ChallengeTestSpec[] {
  const level = Math.min(Math.max(Math.round(opts.level || 1), 1), 3);
  if (opts.kit === "dumbbell") return dumbbellTests(level);
  if (opts.kit === "band") return bandTests();
  return barRingTests();
}

function barRingTests(): ChallengeTestSpec[] {
  return [
    floorPushWithRegression("floor_pushup", FLOOR_PUSH.instructionVi),
    barPullWithRegression(),
    PLANK,
    BW_SQUAT,
  ];
}

function dumbbellTests(level: number): ChallengeTestSpec[] {
  const beginner = level <= 1;
  const push: ChallengeTestSpec = {
    slot: "push",
    id: "db_press",
    titleVi: "Đẩy ngực tạ đơn",
    instructionVi: "Số cái tối đa với mức tạ đang dùng — để TAPTOT chỉnh tạ và số cái.",
    catalogNameEn: "Dumbbell Bench Press",
    catalogNameVi: "Đẩy ngực tạ đơn",
    query: "Dumbbell Bench Press",
    extraQuery: "đẩy ngực tạ đơn",
    preferNames: ["dumbbell bench press", "đẩy ngực tạ đơn"],
    rejectNames: ["fly", "neutral", "incline", "decline", "kickback"],
    preferBodyweight: false,
    valueKind: "reps_kg",
    repsField: "dbPressReps",
    kgField: "dbPressKg",
    unit: "cái",
  };

  const pull: ChallengeTestSpec = {
    slot: "pull",
    id: "db_single_arm_row",
    titleVi: "Chèo tạ đơn một tay",
    instructionVi: "Số cái tối đa mỗi tay với mức tạ đang dùng — để TAPTOT chỉnh tạ/số cái.",
    catalogNameEn: "Dumbbell Single Arm Row",
    catalogNameVi: "Chèo tạ đơn một tay",
    query: "Dumbbell Single Arm Row",
    extraQuery: "chèo tạ đơn một tay",
    preferNames: ["dumbbell single arm row", "chèo tạ đơn một tay"],
    rejectNames: ["upright", "shrug", "chest-supported"],
    preferBodyweight: false,
    valueKind: "reps_kg",
    repsField: "dbRowReps",
    kgField: "dbRowKg",
    unit: "cái",
  };

  const squat: ChallengeTestSpec = beginner
    ? {
        slot: "squat",
        id: "goblet_or_bw",
        titleVi: "Goblet squat (hoặc squat thể trọng)",
        instructionVi:
          "Nếu đã có tạ: nhập số cái tối đa + kg. Chưa nhập kg thì coi như squat thể trọng.",
        catalogNameEn: "Dumbbell Goblet Squat",
        catalogNameVi: "Ngồi xổm ôm tạ đơn",
        query: "Dumbbell Goblet Squat",
        extraQuery: "ngồi xổm ôm tạ đơn",
        preferNames: ["dumbbell goblet squat", "ngồi xổm ôm tạ đơn"],
        rejectNames: ["lunge", "bulgarian", "kettlebell", "jump"],
        preferBodyweight: false,
        valueKind: "reps_kg",
        repsField: "gobletReps",
        kgField: "gobletKg",
        unit: "cái",
        kgOptional: true,
      }
    : {
        slot: "squat",
        id: "goblet_squat",
        titleVi: "Goblet squat",
        instructionVi: "Số cái tối đa với mức tạ đang ôm — để TAPTOT chỉnh tạ và số cái.",
        catalogNameEn: "Dumbbell Goblet Squat",
        catalogNameVi: "Ngồi xổm ôm tạ đơn",
        query: "Dumbbell Goblet Squat",
        extraQuery: "ngồi xổm ôm tạ đơn",
        preferNames: ["dumbbell goblet squat", "ngồi xổm ôm tạ đơn"],
        rejectNames: ["lunge", "bulgarian", "kettlebell", "jump"],
        preferBodyweight: false,
        valueKind: "reps_kg",
        repsField: "gobletReps",
        kgField: "gobletKg",
        unit: "cái",
      };

  return [push, pull, PLANK, squat];
}

function bandTests(): ChallengeTestSpec[] {
  return [
    floorPushWithRegression(
      "band_floor_pushup",
      "Làm tối đa đúng form — để TAPTOT chỉnh số cái trên lịch dây.",
    ),
    {
      slot: "pull",
      id: "band_seated_pulldown",
      titleVi: "Kéo xô ngồi (dây)",
      instructionVi:
        "Làm tối đa đúng form với dây đang dùng — để TAPTOT chỉnh số cái. Có thể ghi mức dây bên dưới.",
      catalogNameEn: "Band Seated Pulldown",
      catalogNameVi: "Kéo xô ngồi với dây",
      query: "Band Seated Pulldown",
      extraQuery: "kéo xô ngồi với dây",
      preferNames: ["band seated pulldown", "kéo xô ngồi với dây"],
      preferBodyweight: false,
      valueKind: "reps",
      repsField: "pullups",
      unit: "cái",
      pullTestVariant: "band_pulldown",
      showBandLevel: true,
    },
    PLANK,
    {
      slot: "squat",
      id: "band_squat",
      titleVi: "Squat với dây",
      instructionVi: "Làm tối đa đúng form. Có thể ghi mức dây bên dưới.",
      catalogNameEn: "Band Squat",
      catalogNameVi: "Ngồi xổm với dây",
      query: "Band Squat",
      extraQuery: "ngồi xổm với dây",
      preferNames: ["band squat", "ngồi xổm với dây"],
      rejectNames: ["goblet", "jump", "pistol"],
      preferBodyweight: false,
      valueKind: "reps",
      repsField: "squats",
      unit: "cái",
      showBandLevel: true,
    },
  ];
}

function optInt(raw: string): number | null {
  const t = raw.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? Math.max(0, Math.round(n)) : null;
}

function optFloat(raw: string): number | null {
  const t = raw.trim().replace(",", ".");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? Math.max(0, n) : null;
}

function specHasValue(spec: ChallengeTestMediaSpec, values: ChallengeTestDraft): boolean {
  return Boolean(values[spec.repsField]?.trim());
}

function specKgRequired(spec: ChallengeTestMediaSpec): boolean {
  return spec.valueKind === "reps_kg" && Boolean(spec.kgField) && !spec.kgOptional;
}

function specSlotComplete(spec: ChallengeTestSpec, values: ChallengeTestDraft): boolean {
  const filled =
    specHasValue(spec, values) || (spec.regression != null && specHasValue(spec.regression, values));
  if (!filled) return false;
  const active = resolveActiveTestSpec(spec, values);
  if (!specKgRequired(active) || !active.kgField) return true;
  return Boolean(values[active.kgField]?.trim());
}

export function challengeSpecsComplete(
  specs: ChallengeTestSpec[],
  values: ChallengeTestDraft,
): boolean {
  return specs.length > 0 && specs.every((spec) => specSlotComplete(spec, values));
}

export function challengeTestsComplete(opts: {
  kit: ChallengeTestKit;
  level: number;
  gender: Gender | null;
  values: ChallengeTestDraft;
}): boolean {
  return challengeSpecsComplete(
    challengeFitnessTests({ kit: opts.kit, level: opts.level, gender: opts.gender }),
    opts.values,
  );
}

export function resolveActiveTestSpec(
  spec: ChallengeTestSpec,
  values: ChallengeTestDraft,
): ChallengeTestMediaSpec {
  const hard = optInt(values[spec.repsField]);
  if (hard != null && hard > 0) return spec;
  if (spec.regression && specHasValue(spec.regression, values)) return spec.regression;
  return spec;
}

export function challengeTestsFilledCount(
  kit: ChallengeTestKit,
  values: ChallengeTestDraft,
  gender: Gender | null,
  level: number,
): number {
  const specs = challengeFitnessTests({ kit, level, gender });
  return specs.filter(
    (spec) => specHasValue(spec, values) || (spec.regression != null && specHasValue(spec.regression, values)),
  ).length;
}

export function buildChallengeFitnessBaseline(opts: {
  kit: ChallengeTestKit;
  level: number;
  gender: Gender | null;
  values: ChallengeTestDraft;
}): FitnessBaseline {
  const specs = challengeFitnessTests(opts);
  const push = specs.find((s) => s.slot === "push");
  const pull = specs.find((s) => s.slot === "pull");
  const v = opts.values;
  const activePush = push ? resolveActiveTestSpec(push, v) : null;
  const activePull = pull ? resolveActiveTestSpec(pull, v) : null;
  const base: FitnessBaseline = {
    test_kit: opts.kit,
    plank_seconds: optInt(v.plankSeconds),
    run_10min_meters: null,
  };

  if (activePush?.pushupVariant) base.pushup_variant = activePush.pushupVariant;
  if (activePull?.pullTestVariant) base.pull_test_variant = activePull.pullTestVariant;

  if (opts.kit === "dumbbell") {
    base.db_press_reps = optInt(v.dbPressReps);
    base.db_press_kg = optFloat(v.dbPressKg);
    base.db_row_reps = optInt(v.dbRowReps);
    base.db_row_kg = optFloat(v.dbRowKg);
    base.goblet_reps = optInt(v.gobletReps);
    base.goblet_kg = optFloat(v.gobletKg);
    const squatReps = optInt(v.gobletReps) ?? optInt(v.squats);
    if (base.goblet_kg == null && squatReps != null) base.squats_max = squatReps;
    else if (base.goblet_reps != null) base.squats_max = base.goblet_reps;
    return base;
  }

  if (opts.kit === "band") {
    base.pushups_max = activePush ? optInt(v[activePush.repsField]) : optInt(v.pushups);
    base.pullups_max = optInt(v.pullups);
    base.squats_max = optInt(v.squats);
    base.band_level = v.bandLevel.trim() || null;
    return base;
  }

  base.pushups_max = activePush ? optInt(v[activePush.repsField]) : optInt(v.pushups);
  base.squats_max = optInt(v.squats);
  const variant = activePull?.pullTestVariant || v.pullTestVariant;
  if (variant === "hang") {
    base.pull_hold_seconds = optInt(v.pullHoldSeconds);
    base.pullups_max = null;
  } else if (variant === "inverted_row" || variant === "inverted_row_low") {
    base.inverted_rows_max = optInt(v.invertedRows);
    base.pullups_max = null;
  } else {
    base.pullups_max = optInt(v.pullups);
  }
  return base;
}

export function challengeFitnessSummaryLines(
  kit: ChallengeTestKit,
  values: ChallengeTestDraft,
  gender: Gender | null,
  level: number,
): string[] {
  const specs = challengeFitnessTests({ kit, level, gender });
  const lines: string[] = [];
  for (const spec of specs) {
    const active = resolveActiveTestSpec(spec, values);
    const reps = values[active.repsField]?.trim();
    if (!reps) continue;
    if (active.valueKind === "reps_kg") {
      const kg = active.kgField ? values[active.kgField]?.trim() : "";
      lines.push(kg ? `${active.titleVi} ${reps} cái × ${kg} kg` : `${active.titleVi} ${reps} cái`);
    } else if (active.valueKind === "seconds") {
      lines.push(`${active.titleVi} ${reps} giây`);
    } else {
      lines.push(`${active.titleVi} ${reps} cái`);
    }
  }
  if (kit === "band" && values.bandLevel.trim()) {
    const label = BAND_LEVEL_OPTS.find((o) => o.value === values.bandLevel)?.label;
    if (label && label !== "Chưa chọn") lines.push(`Mức dây: ${label}`);
  }
  return lines;
}

export function challengeTestMediaSpecs(tests: ChallengeTestSpec[]): ChallengeTestMediaSpec[] {
  return tests.flatMap((spec) => (spec.regression ? [spec, spec.regression] : [spec]));
}

function foldVi(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function isBodyweight(ex: ExerciseListItem): boolean {
  const slugs = (ex.equipment_slugs || []).map((s) => s.toLowerCase());
  if (slugs.length === 0) return true;
  const blob = `${ex.equipment || ""} ${slugs.join(" ")}`.toLowerCase();
  return (
    /khong dung cu|bodyweight|no.?equip|none|—|-/.test(blob) ||
    slugs.every((s) => s === "bodyweight" || s === "none")
  );
}

export function pickChallengeExercise(
  items: ExerciseListItem[],
  spec: ChallengeTestMediaSpec,
): ExerciseListItem | null {
  if (!items.length) return null;
  let best = items[0];
  let bestScore = -Infinity;
  const catalogEn = foldVi(spec.catalogNameEn);
  const catalogVi = foldVi(spec.catalogNameVi);
  for (const ex of items) {
    const nameEn = foldVi(ex.name_en);
    const nameVi = foldVi(ex.name_vi);
    const blob = `${nameVi} ${nameEn}`;
    let score = 0;
    if (catalogEn && nameEn === catalogEn) score += 500;
    if (catalogVi && nameVi === catalogVi) score += 200;
    for (const name of spec.preferNames) {
      const n = foldVi(name);
      if (blob === n) score += 100;
      else if (blob.includes(n)) score += 40;
    }
    for (const bad of spec.rejectNames || []) {
      if (blob.includes(foldVi(bad))) score -= 80;
    }
    if (spec.preferBodyweight) score += isBodyweight(ex) ? 25 : -30;
    else if (spec.valueKind === "reps_kg" && blob.includes("goblet")) score += 20;
    if (ex.is_beginner_friendly) score += 2;
    if (ex.video_url || ex.gif_url) score += 3;
    score -= Math.min(blob.length, 40) * 0.2;
    if (score > bestScore) {
      bestScore = score;
      best = ex;
    }
  }
  return best;
}
