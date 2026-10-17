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
  bandLevelPush: string;
  bandLevelPull: string;
  bandLevelSquat: string;
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
  bandLevelPush: "",
  bandLevelPull: "",
  bandLevelSquat: "",
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
  kgPreset?: "each_side" | "squat_total";
};

export type ChallengeTestSpec = ChallengeTestMediaSpec & {
  slot: ChallengeTestSlot;
  regression?: ChallengeTestMediaSpec;
  regressionHintVi?: string;
};

export const BAND_LEVEL_OPTS = [
  { value: "", label: "Chưa chọn" },
  { value: "yellow", label: "Vàng · 10 lbs" },
  { value: "red", label: "Đỏ · 15 lbs" },
  { value: "blue", label: "Xanh dương · 20 lbs" },
  { value: "green", label: "Xanh lá · 25 lbs" },
  { value: "black", label: "Đen · 30 lbs" },
] as const;

/** Plate kg on one DB when both hands are loaded (40 kg kit, no handle). */
export const DB_EACH_SIDE_KG = [2.5, 5, 7.5, 10, 12.5, 15, 17.5] as const;
/** Plate kg on one goblet/suitcase DB (all plates). */
export const DB_SQUAT_KG = [
  2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30, 32.5, 35,
] as const;

function dbKgOption(kg: number, kind: "each_side" | "squat_total") {
  const value = String(kg);
  const label =
    kind === "squat_total" ? `${kg} kg một quả` : `${kg} kg mỗi tay`;
  return { value, label };
}

export const DB_EACH_SIDE_OPTS = [
  { value: "", label: "Chưa chọn" },
  ...DB_EACH_SIDE_KG.map((kg) => dbKgOption(kg, "each_side")),
];

export const DB_SQUAT_OPTS = [
  { value: "", label: "Chưa chọn" },
  ...DB_SQUAT_KG.map((kg) => dbKgOption(kg, "squat_total")),
];

export function dbKgOptsForSpec(spec: { kgPreset?: "each_side" | "squat_total" }) {
  return spec.kgPreset === "squat_total" ? DB_SQUAT_OPTS : DB_EACH_SIDE_OPTS;
}

export function bandLevelFieldForSlot(
  slot: ChallengeTestSlot,
): "bandLevelPush" | "bandLevelPull" | "bandLevelSquat" | null {
  if (slot === "push") return "bandLevelPush";
  if (slot === "pull") return "bandLevelPull";
  if (slot === "squat") return "bandLevelSquat";
  return null;
}

const FLOOR_PUSH: ChallengeTestMediaSpec = {
  id: "floor_pushup",
  titleVi: "Chống đẩy",
  instructionVi: "Làm tối đa đúng form để TAPTOT điều chỉnh lịch tập hợp lý hơn.",
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

const BAR_PULLUP: ChallengeTestMediaSpec = {
  id: "bar_pullup",
  titleVi: "Kéo xà",
  instructionVi: "Làm tối đa đúng form để TAPTOT điều chỉnh lịch tập hợp lý hơn.",
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
  instructionVi: "Làm tối đa đúng form để TAPTOT điều chỉnh lịch tập hợp lý hơn.",
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
  if (opts.kit === "dumbbell") return dumbbellTests();
  if (opts.kit === "band") return bandTests();
  return barRingTests();
}

function barRingTests(): ChallengeTestSpec[] {
  return [
    { ...FLOOR_PUSH, id: "floor_pushup", slot: "push" },
    { ...BAR_PULLUP, slot: "pull" },
    PLANK,
    BW_SQUAT,
  ];
}

function dumbbellTests(): ChallengeTestSpec[] {
  const push: ChallengeTestSpec = {
    slot: "push",
    id: "db_press",
    titleVi: "Đẩy ngực tạ đơn",
    instructionVi: "Số cái tối đa với mức tạ đã chọn — để TAPTOT chỉnh tạ và số cái.",
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
    kgPreset: "each_side",
    unit: "cái",
  };

  const pull: ChallengeTestSpec = {
    slot: "pull",
    id: "db_bilateral_row",
    titleVi: "Chèo tạ đơn hai tay",
    instructionVi: "Hai tay cùng lúc, số cái tối đa với mức tạ đã chọn — để TAPTOT chỉnh tạ/số cái.",
    catalogNameEn: "Dumbbell Row Bilateral",
    catalogNameVi: "Chèo tạ đơn hai tay",
    query: "Dumbbell Row Bilateral",
    extraQuery: "chèo tạ đơn hai tay",
    preferNames: ["dumbbell row bilateral", "chèo tạ đơn hai tay"],
    rejectNames: ["upright", "shrug", "chest-supported", "single arm", "một tay"],
    preferBodyweight: false,
    valueKind: "reps_kg",
    repsField: "dbRowReps",
    kgField: "dbRowKg",
    kgPreset: "each_side",
    unit: "cái",
  };

  const squat: ChallengeTestSpec = {
    slot: "squat",
    id: "goblet_squat",
    titleVi: "Goblet squat",
    instructionVi: "Số cái tối đa với mức tạ đã chọn (tổng kg đang ôm) — để TAPTOT chỉnh tạ và số cái.",
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
    kgPreset: "squat_total",
    unit: "cái",
  };

  return [push, pull, PLANK, squat];
}

function bandTests(): ChallengeTestSpec[] {
  return [
    {
      slot: "push",
      id: "band_chest_press",
      titleVi: "Đẩy ngực dây",
      instructionVi:
        "Làm tối đa đúng form với dây đang dùng — để TAPTOT chỉnh số cái. Có thể ghi mức dây bên dưới.",
      catalogNameEn: "Band Chest Press",
      catalogNameVi: "Đẩy ngực với dây kháng lực",
      query: "Band Chest Press",
      extraQuery: "đẩy ngực với dây",
      preferNames: ["band chest press", "đẩy ngực với dây"],
      rejectNames: ["fly", "push-up", "push up", "chống đẩy"],
      preferBodyweight: false,
      valueKind: "reps",
      repsField: "pushups",
      unit: "cái",
      pushupVariant: "band_press",
      showBandLevel: true,
    },
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
    const pushLv = v.bandLevelPush.trim();
    const pullLv = v.bandLevelPull.trim();
    const squatLv = v.bandLevelSquat.trim();
    base.band_level_push = pushLv || null;
    base.band_level_pull = pullLv || null;
    base.band_level_squat = squatLv || null;
    base.band_level = pullLv || pushLv || squatLv || null;
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
  if (kit === "band") {
    for (const spec of specs) {
      const field = bandLevelFieldForSlot(spec.slot);
      if (!field) continue;
      const raw = values[field]?.trim();
      if (!raw) continue;
      const label = BAND_LEVEL_OPTS.find((o) => o.value === raw)?.label;
      if (label && label !== "Chưa chọn") lines.push(`${spec.titleVi} · mức dây ${label}`);
    }
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
