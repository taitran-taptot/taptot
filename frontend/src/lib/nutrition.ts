import type { Activity, ExtraGoal, Gender, Goal, WeightGoal } from "./types";

// Mirrors api/app/services/workout_generation/nutrition_targets.py
export const ACTIVITY: Record<Activity, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  very_active: 1.9,
};

export const GOAL_ADJ: Record<Goal, number> = {
  lose_weight: -550,
  maintain: 0,
  gain_muscle: 300,
  gain_weight: 300,
};

export const GOAL_LABEL: Record<Goal, string> = {
  lose_weight: "giảm cân",
  maintain: "giữ cân",
  gain_muscle: "tăng cân",
  gain_weight: "tăng cân",
};

/** TDEE lifestyle — nghề / đi lại hằng ngày, không phải số buổi gym. */
export const ACTIVITY_FIELD_LABEL = "Công việc / ngày thường";

export const ACTIVITY_HINT =
  "Chọn theo nghề và đi lại hằng ngày (ngồi máy tính hay đứng bán hàng), không phải số buổi tập gym.";

export const ACTIVITY_OPTS: { value: Activity; label: string }[] = [
  { value: "sedentary", label: "Ngồi nhiều — văn phòng, học, lái xe" },
  { value: "light", label: "Đứng / đi nhẹ — giáo viên, bán hàng, nội trợ" },
  { value: "moderate", label: "Đi lại nhiều — phục vụ, y tá, shipper" },
  { value: "active", label: "Lao động chân tay — công trình, kho, nông" },
  { value: "very_active", label: "Lao động nặng cả ngày — khuân vác, thợ hồ" },
];

/** Calculator / AI — 3 mục tiêu calo cơ bản */
export const GOAL_OPTS: { value: Goal; icon: string; label: string }[] = [
  { value: "lose_weight", icon: "🔥", label: "Giảm cân" },
  { value: "maintain", icon: "⚖️", label: "Giữ cân" },
  { value: "gain_muscle", icon: "💪", label: "Tăng cân" },
];

/** Plan builder / AI — mục tiêu chính cân nặng (chỉ chọn 1) */
export const WEIGHT_GOAL_OPTS: { value: WeightGoal; icon: string; label: string }[] = [
  { value: "lose_weight", icon: "🔥", label: "Giảm cân" },
  { value: "maintain", icon: "⚖️", label: "Giữ cân" },
  { value: "gain_weight", icon: "📈", label: "Tăng cân" },
];

/** Plan builder / AI — mục tiêu bổ sung (chọn nhiều) */
export const EXTRA_GOAL_OPTS: { value: ExtraGoal; icon: string; label: string }[] = [
  { value: "physique", icon: "✨", label: "Cải thiện vóc dáng" },
  { value: "strength", icon: "🏋️", label: "Tăng sức mạnh" },
  { value: "endurance", icon: "🏃", label: "Tăng sức bền" },
  { value: "mental_health", icon: "🧠", label: "Sức khỏe tinh thần" },
  { value: "heartbreak_recovery", icon: "💔", label: "Phục hồi sau thất tình" },
];

/** ~7700 kcal ≈ 1 kg mỡ cơ thể */
export const KCAL_PER_KG = 7700;

/** Giảm cân hợp lý: 0,5–1% trọng lượng cơ thể / tuần. */
export const LOSS_WEEKLY_PCT_MIN = 0.005;
export const LOSS_WEEKLY_PCT_MAX = 0.01;
export const LOSS_WEEKLY_KG_ABS_MIN = 0.2;
export const LOSS_WEEKLY_KG_ABS_MAX = 1.5;

export const LOSS_WEEKLY_HINT =
  "Hợp lý khoảng 0,5–1% cân hiện tại mỗi tuần. Người nhẹ hơn thì số kg nhỏ hơn — tránh giảm quá nhanh, dễ ảnh hưởng đến sức khỏe.";

/** Máy tính calo: giải thích vì sao dùng % cân, không dùng một số kg cố định. */
export const CALCULATOR_LOSS_HINT =
  "Mỗi tuần chỉ giảm 0,5% · 0,75% · 1% cân nặng hiện tại. Ví dụ 80 kg thì 0,5% ≈ 0,4 kg/tuần; 50 kg thì 0,5% ≈ 0,25 kg/tuần. Giảm theo % an toàn hơn một mức kg cố định — quá 1%/tuần dễ mất cơ và thiếu năng lượng.";

const LOSS_WEEKLY_PACES = [
  { pct: LOSS_WEEKLY_PCT_MIN, hint: "Ổn định", recommended: false },
  { pct: 0.0075, hint: "Vừa", recommended: true },
  { pct: LOSS_WEEKLY_PCT_MAX, hint: "Nhanh", recommended: false },
] as const;

export type LossWeeklyKgOpt = {
  value: number;
  label: string;
  hint: string;
  pctLabel: string;
  recommended: boolean;
};

function clampWeightKg(weightKg: number): number {
  if (!Number.isFinite(weightKg) || weightKg <= 0) return 65;
  return Math.min(250, Math.max(30, weightKg));
}

/** Làm tròn 0,05 kg để hiện trên nút cho dễ đọc. */
export function roundWeeklyKg(kg: number): number {
  return Math.round(kg * 20) / 20;
}

export function formatKgVi(kg: number): string {
  return `${String(kg).replace(".", ",")} kg`;
}

/** Tổng kg trên thử thách 100 ngày (14 tuần), làm tròn lên bậc 0,5 (8,0 / 8,5). */
export function challenge100DaysTotalKg(kgPerWeek: number, weeks = 14): number {
  const raw = kgPerWeek * weeks;
  return Math.ceil(raw * 2) / 2;
}

/** Ví dụ: "Giảm 8,5kg trong 100 ngày" / "Tăng 8,0kg trong 100 ngày". */
export function formatChallenge100DaysLabel(
  kind: "lose_weight" | "gain_weight",
  kgPerWeek: number,
): string {
  const total = challenge100DaysTotalKg(kgPerWeek);
  const kgText = `${total.toFixed(1).replace(".", ",")}kg`;
  return kind === "gain_weight" ? `Tăng ${kgText} trong 100 ngày` : `Giảm ${kgText} trong 100 ngày`;
}

export function lossWeeklyKgRange(weightKg: number): { min: number; max: number } {
  const w = clampWeightKg(weightKg);
  const min = Math.max(LOSS_WEEKLY_KG_ABS_MIN, roundWeeklyKg(w * LOSS_WEEKLY_PCT_MIN));
  const max = Math.min(LOSS_WEEKLY_KG_ABS_MAX, roundWeeklyKg(w * LOSS_WEEKLY_PCT_MAX));
  return { min, max: Math.max(min, max) };
}

export function lossWeeklyKgOpts(weightKg: number): LossWeeklyKgOpt[] {
  const w = clampWeightKg(weightKg);
  const { min, max } = lossWeeklyKgRange(w);
  return LOSS_WEEKLY_PACES.map(({ pct, hint, recommended }) => {
    const value = Math.min(max, Math.max(min, roundWeeklyKg(w * pct)));
    const pctText = `${String(+(pct * 100).toPrecision(3)).replace(".", ",")}%`;
    return {
      value,
      label: formatKgVi(value),
      hint,
      pctLabel: `${pctText} cân`,
      recommended,
    };
  });
}

export function snapToWeeklyKg(kg: number, allowed: number[]): number {
  if (!allowed.length) return kg;
  return allowed.reduce((best, v) => (Math.abs(v - kg) < Math.abs(best - kg) ? v : best));
}

export function defaultLossKgPerWeek(weightKg: number): number {
  const opts = lossWeeklyKgOpts(weightKg);
  return opts.find((o) => o.recommended)?.value ?? opts[0]?.value ?? 0.5;
}

/** Tăng cân: 0,25–0,75% trọng lượng cơ thể / tuần. */
export const GAIN_WEEKLY_PCT_MIN = 0.0025;
export const GAIN_WEEKLY_PCT_DEFAULT = 0.005;
export const GAIN_WEEKLY_PCT_MAX = 0.0075;
export const GAIN_WEEKLY_KG_ABS_MIN = 0.1;
export const GAIN_WEEKLY_KG_ABS_MAX = 1.5;

export const GAIN_WEEKLY_HINT =
  "Hợp lý khoảng 0,25–0,75% cân hiện tại mỗi tuần. Tăng chậm hơn thì ít mỡ hơn.";

/** Máy tính calo: giải thích tốc độ tăng theo % cân. */
export const CALCULATOR_GAIN_HINT =
  "Mỗi tuần chỉ tăng 0,25% · 0,5% · 0,75% cân nặng hiện tại. Ví dụ 80 kg thì 0,25% ≈ 0,2 kg/tuần; 50 kg thì 0,25% ≈ 0,15 kg/tuần. Tăng theo % giúp hạn chế mỡ — 0,25% chắc, ít mỡ; 0,75% nhanh hơn nhưng dễ lên mỡ hơn.";

const GAIN_WEEKLY_PACES = [
  { pct: GAIN_WEEKLY_PCT_MIN, hint: "Chắc, ít mỡ", recommended: false },
  { pct: GAIN_WEEKLY_PCT_DEFAULT, hint: "Vừa", recommended: true },
  { pct: GAIN_WEEKLY_PCT_MAX, hint: "Nhanh", recommended: false },
] as const;

export function gainWeeklyKgRange(weightKg: number): { min: number; max: number } {
  const w = clampWeightKg(weightKg);
  const min = Math.max(GAIN_WEEKLY_KG_ABS_MIN, roundWeeklyKg(w * GAIN_WEEKLY_PCT_MIN));
  const max = Math.min(GAIN_WEEKLY_KG_ABS_MAX, roundWeeklyKg(w * GAIN_WEEKLY_PCT_MAX));
  return { min, max: Math.max(min, max) };
}

export function gainWeeklyKgOpts(weightKg: number): LossWeeklyKgOpt[] {
  const w = clampWeightKg(weightKg);
  const { min, max } = gainWeeklyKgRange(w);
  return GAIN_WEEKLY_PACES.map(({ pct, hint, recommended }) => {
    const value = Math.min(max, Math.max(min, roundWeeklyKg(w * pct)));
    const pctText = `${String(+(pct * 100).toPrecision(3)).replace(".", ",")}%`;
    return {
      value,
      label: formatKgVi(value),
      hint,
      pctLabel: `${pctText} cân`,
      recommended,
    };
  });
}

export function defaultGainKgPerWeek(weightKg: number): number {
  const opts = gainWeeklyKgOpts(weightKg);
  return opts.find((o) => o.recommended)?.value ?? opts[1]?.value ?? 0.5;
}

export interface NutritionResult {
  bmr: number;
  tdee: number;
  target: number;
  bmi: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  /** kg change estimate per week at current target (negative = lose) */
  weekly_kg?: number;
}

export type BmiBand = "underweight" | "normal" | "overweight" | "obese_1" | "obese_2";

export type BmiCategory = {
  key: BmiBand;
  vi: string;
  advice: string;
  cls: string;
  bg: string;
};

export function computeBmi(weightKg: number, heightCm: number): number | null {
  if (!Number.isFinite(weightKg) || !Number.isFinite(heightCm) || weightKg <= 0 || heightCm <= 0) {
    return null;
  }
  const hm = heightCm / 100;
  if (hm <= 0) return null;
  return Math.round((weightKg / (hm * hm)) * 10) / 10;
}

export function bmiCategory(b: number): BmiCategory {
  if (b < 18.5) {
    return {
      key: "underweight",
      vi: "Gầy (Thiếu cân)",
      advice: "Gợi ý tăng cân ở mức vừa để lấy lại sức khỏe.",
      cls: "text-amber-600",
      bg: "bg-amber-50",
    };
  }
  if (b < 23) {
    return {
      key: "normal",
      vi: "Bình thường (Lý tưởng)",
      advice: "Gợi ý tăng cân nhẹ ở mức chậm nhất nhằm tối ưu dáng.",
      cls: "text-brand-600",
      bg: "bg-brand-50",
    };
  }
  if (b < 25) {
    return {
      key: "overweight",
      vi: "Tiền béo phì (Thừa cân)",
      advice: "Gợi ý giảm về bình thường, chậm mà chắc.",
      cls: "text-orange-600",
      bg: "bg-orange-50",
    };
  }
  if (b < 30) {
    return {
      key: "obese_1",
      vi: "Béo phì độ I",
      advice: "Gợi ý giảm nhanh về bình thường.",
      cls: "text-rose-600",
      bg: "bg-rose-50",
    };
  }
  return {
    key: "obese_2",
    vi: "Béo phì độ II+",
    advice: "Nên tìm huấn luyện viên để được theo dõi sát.",
    cls: "text-rose-700",
    bg: "bg-rose-50",
  };
}

export function foundationBmiHint(band: BmiBand): string {
  if (band === "underweight") {
    return "Lịch sẽ ưu tiên tăng tải balo và rút ngắn cardio để hỗ trợ tăng cân.";
  }
  if (band === "overweight") {
    return "Lịch ưu tiên đi bộ/jog nhẹ, chống đẩy ghế, không nhảy plyo sớm.";
  }
  if (band === "obese_1" || band === "obese_2") {
    return "Lịch ưu tiên đi bộ, chống đẩy ghế/tường, kéo ngang — tránh nhảy và chạy nhanh.";
  }
  return "Lịch dùng bài thể trọng và xà đơn, tiến dần theo form.";
}

export function foundationNutritionRecap(band: BmiBand): { title: string; body: string } {
  const menuNote = "Thực đơn từng bữa sẽ hiện ở tab Ăn uống sau khi tạo lịch.";
  if (band === "underweight") {
    return {
      title: "Ưu tiên tăng cân",
      body: `Lịch ghi hướng ăn dư calo nhẹ để tăng cân, đồng thời tăng tải balo và rút ngắn cardio. ${menuNote}`,
    };
  }
  if (band === "overweight") {
    return {
      title: "Ưu tiên giảm cân nhẹ",
      body: `Lịch kết hợp đi bộ hoặc jog nhẹ với thâm hụt calo vừa phải. ${menuNote}`,
    };
  }
  if (band === "obese_1" || band === "obese_2") {
    return {
      title: "Ưu tiên giảm cân nhẹ",
      body: `Lịch ưu tiên đi bộ, bài dễ trên ghế/tường, và thâm hụt calo vừa phải — tránh nhảy và chạy nhanh. ${menuNote}`,
    };
  }
  return {
    title: "Duy trì cân nặng",
    body: `Ăn đủ để tập và phục hồi. Lịch dùng bài thể trọng và xà đơn, tiến dần theo form. ${menuNote}`,
  };
}

type ChallengePaceKind = "slowest" | "medium" | "fastest";

function challengePaceByKind(
  kind: "lose_weight" | "gain_weight",
  weightKg: number,
  pace: ChallengePaceKind,
): number {
  const opts = kind === "gain_weight" ? gainWeeklyKgOpts(weightKg) : lossWeeklyKgOpts(weightKg);
  if (pace === "slowest") return opts[0]?.value ?? 0.2;
  if (pace === "fastest") return opts[opts.length - 1]?.value ?? 0.5;
  return opts.find((item) => item.recommended)?.value ?? opts[1]?.value ?? 0.5;
}

/** Pace to badge as Gợi ý when the chosen main challenge matches the BMI band. */
export function recommendedBmiChallengePace(
  bmi: number,
  goal: WeightGoal,
  weightKg: number,
): number | null {
  if (goal !== "lose_weight" && goal !== "gain_weight") return null;
  const band = bmiCategory(bmi).key;
  if (goal === "gain_weight") {
    if (band === "underweight") return challengePaceByKind("gain_weight", weightKg, "medium");
    if (band === "normal") return challengePaceByKind("gain_weight", weightKg, "slowest");
    return null;
  }
  if (band === "overweight") return challengePaceByKind("lose_weight", weightKg, "slowest");
  if (band === "obese_1" || band === "obese_2") {
    return challengePaceByKind("lose_weight", weightKg, "fastest");
  }
  return null;
}

function macrosFor(goal: Goal | WeightGoal, weightKg: number, target: number) {
  let protein: number;
  let fat: number;
  if (goal === "lose_weight") {
    protein = weightKg * 2.0;
    fat = weightKg * 0.8;
  } else if (goal === "gain_muscle" || goal === "gain_weight") {
    protein = weightKg * 2.2;
    fat = weightKg * 1.0;
  } else {
    protein = weightKg * 1.8;
    fat = weightKg * 0.9;
  }
  fat = Math.max(fat, (0.2 * target) / 9);
  if (goal === "lose_weight") fat = Math.max(fat, weightKg * 0.7);
  const proteinCal = protein * 4;
  const fatCal = fat * 9;
  if (proteinCal + fatCal > target) {
    const fatFloor = Math.max(weightKg * 0.6, (0.18 * target) / 9, 35);
    fat = Math.min(fat, Math.max(fatFloor, (target - proteinCal) / 9));
    const nextFatCal = fat * 9;
    if (proteinCal + nextFatCal > target) {
      protein = Math.max(weightKg * 1.6, (target - nextFatCal) / 4);
    }
  }
  const carbsCal = Math.max(target - protein * 4 - fat * 9, 0);
  return {
    protein_g: Math.round(protein * 10) / 10,
    fat_g: Math.round(fat * 10) / 10,
    carbs_g: Math.trunc(carbsCal / 4),
  };
}

export function clampCalorieTarget(
  tdee: number,
  _goal: Goal | WeightGoal,
  desiredDelta: number,
  _weightKg: number,
  _gender: Gender,
  _bmr: number,
): number {
  return Math.max(1, tdee + desiredDelta);
}

export function computeNutrition(
  gender: Gender,
  goal: Goal,
  activity: Activity,
  weightKg: number,
  heightCm: number,
  age: number,
  kgPerWeek?: number,
): NutritionResult {
  const bmr =
    gender === "female"
      ? 10 * weightKg + 6.25 * heightCm - 5 * age - 161
      : 10 * weightKg + 6.25 * heightCm - 5 * age + 5;
  const tdee = Math.trunc(bmr * (ACTIVITY[activity] ?? 1.375));
  let desired = GOAL_ADJ[goal] ?? 0;
  if (kgPerWeek != null && kgPerWeek > 0) {
    if (goal === "lose_weight") {
      desired = -Math.round((kgPerWeek * KCAL_PER_KG) / 7);
    } else if (goal === "gain_muscle" || goal === "gain_weight") {
      desired = Math.round((kgPerWeek * KCAL_PER_KG) / 7);
    }
  }
  const target = clampCalorieTarget(tdee, goal, desired, weightKg, gender, bmr);
  const hm = heightCm / 100;
  const bmi = Math.round((weightKg / (hm * hm)) * 10) / 10;
  const macros = macrosFor(goal, weightKg, target);
  const weekly_kg = Math.round(((tdee - target) * 7) / KCAL_PER_KG * 100) / 100;
  return {
    bmr: Math.trunc(bmr),
    tdee,
    target,
    bmi,
    protein_g: macros.protein_g,
    fat_g: macros.fat_g,
    carbs_g: macros.carbs_g,
    weekly_kg,
  };
}

/**
 * Recalculate daily calorie target from desired weekly weight change.
 * positive kg/week = lose (deficit); for gain_weight, positive = surplus.
 */
export function targetFromWeeklyRate(
  tdee: number,
  weightGoal: WeightGoal,
  kgPerWeek: number,
  weightKg: number,
  opts?: { gender?: Gender; bmr?: number },
): NutritionResult {
  const rate = Math.max(0, Math.min(LOSS_WEEKLY_KG_ABS_MAX, kgPerWeek));
  const gender = opts?.gender ?? "male";
  const bmr = opts?.bmr ?? tdee / 1.55;
  let desired = 0;
  let weekly_kg = 0;
  if (weightGoal === "lose_weight") {
    desired = -Math.round((rate * KCAL_PER_KG) / 7);
    weekly_kg = -rate;
  } else if (weightGoal === "gain_weight") {
    desired = Math.round((rate * KCAL_PER_KG) / 7);
    weekly_kg = rate;
  }
  const target = clampCalorieTarget(tdee, weightGoal, desired, weightKg, gender, bmr);
  const macros = macrosFor(weightGoal, weightKg, target);
  const hmDummy = computeNutrition(gender, weightGoal === "gain_weight" ? "gain_weight" : weightGoal, "moderate", weightKg, 170, 25);
  return {
    bmr: Math.trunc(bmr),
    tdee,
    target,
    bmi: hmDummy.bmi,
    protein_g: macros.protein_g,
    fat_g: macros.fat_g,
    carbs_g: macros.carbs_g,
    weekly_kg,
  };
}

export function gramsToMacroPercents(n: NutritionResult): { protein: number; carbs: number; fat: number } {
  const t = Math.max(1, n.target);
  const protein = Math.round(((n.protein_g * 4) / t) * 100);
  const fat = Math.round(((n.fat_g * 9) / t) * 100);
  const carbs = Math.max(0, 100 - protein - fat);
  return { protein, carbs, fat };
}

/** Recalculate grams from calorie target + P/C/F percents (normalized to 100). */
export function applyMacroPercents(
  n: NutritionResult,
  pct: { protein: number; carbs: number; fat: number },
): NutritionResult {
  let protein = Math.min(70, Math.max(10, Math.round(pct.protein) || 0));
  let carbs = Math.min(75, Math.max(5, Math.round(pct.carbs) || 0));
  let fat = Math.min(50, Math.max(15, Math.round(pct.fat) || 0));
  const sum = protein + carbs + fat;
  if (sum !== 100 && sum > 0) {
    protein = Math.round((protein / sum) * 100);
    fat = Math.round((fat / sum) * 100);
    carbs = Math.max(0, 100 - protein - fat);
  }
  const t = n.target;
  return {
    ...n,
    protein_g: Math.round(((t * protein) / 100 / 4) * 10) / 10,
    carbs_g: Math.round(((t * carbs) / 100 / 4) * 10) / 10,
    fat_g: Math.round(((t * fat) / 100 / 9) * 10) / 10,
  };
}

export function formatGoalsLabel(weightGoal: WeightGoal, extras: ExtraGoal[]): string {
  const parts = [
    WEIGHT_GOAL_OPTS.find((o) => o.value === weightGoal)?.label ?? weightGoal,
    ...extras.map((e) => EXTRA_GOAL_OPTS.find((o) => o.value === e)?.label ?? e),
  ];
  return parts.join(", ");
}
