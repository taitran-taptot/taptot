"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { difficultyLabel, exerciseMinutesByRest, viNum } from "@/lib/labels";
import { foodDisplayName, isHiddenFoodCategorySlug } from "@/lib/foodDisplay";
import {
  ACTIVITY_FIELD_LABEL,
  ACTIVITY_OPTS,
  LOSS_WEEKLY_HINT,
  WEIGHT_GOAL_OPTS,
  applyMacroPercents,
  computeNutrition,
  formatGoalsLabel,
  formatKgVi,
  gramsToMacroPercents,
  defaultGainKgPerWeek,
  defaultLossKgPerWeek,
  gainWeeklyKgRange,
  lossWeeklyKgRange,
  targetFromWeeklyRate,
  type NutritionResult,
} from "@/lib/nutrition";
import type {
  Activity,
  ExerciseListItem,
  Food,
  FoodCategory,
  Gender,
  WeightGoal,
} from "@/lib/types";
import { plansApi, mealTemplatesApi, PLAN_SECTION_ORDER, SECTION_LABEL, type CreatePlanPayload, type MealTemplateSummary, type PlanSectionKey } from "@/lib/plansApi";
import { estimateExerciseTransitionMinutes } from "@/lib/planLabels";
import { isAuthenticated } from "@/lib/auth";
import { addGuestPlanToken } from "@/lib/guestPlans";
import { migrateLocalKeys } from "@/lib/storageKeys";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";
import TermsDocument from "@/components/TermsDocument";
import { defaultDurationWeeks, MAX_DURATION_WEEKS, MIN_DURATION_WEEKS, progressionHintVi } from "@/lib/periodization";
import {
  DIET_OPTS,
  customFoodsApi,
  searchFoodsAuth,
} from "@/lib/phase3Api";
import ExerciseThumb from "../ExerciseThumb";
import MacroBar from "../MacroBar";
import Modal from "../Modal";
import { PAGE_SIZE } from "@/lib/config";

migrateLocalKeys([
  ["tfit_plans", "taptot_plans"],
  ["vietfit_plans", "taptot_plans"],
]);

const STEPS = ["Thông tin", "Thực đơn", "Bài tập", "Hoàn tất"];

const MAIN_MEAL_SLOTS: { key: "breakfast" | "lunch" | "dinner"; label: string; icon: string }[] = [
  { key: "breakfast", label: "Sáng", icon: "🌅" },
  { key: "lunch", label: "Trưa", icon: "☀️" },
  { key: "dinner", label: "Tối", icon: "🌙" },
];

/* ---------------- Meal model ---------------- */
type FoodEntry = { food: Food; qty: number };
type MealsState = {
  breakfast: Record<number, FoodEntry>;
  lunch: Record<number, FoodEntry>;
  dinner: Record<number, FoodEntry>;
  snacks: Record<number, FoodEntry>[];
};

/** Thực đơn tách riêng theo từng buổi tập trong tuần. */
type MealsByDay = Record<number, MealsState>;

type MealSlotNotes = {
  breakfast: string;
  lunch: string;
  dinner: string;
  snacks: string[];
};

type DayNotes = {
  meals: MealSlotNotes;
  sections: Record<"warmup" | "main" | "cooldown" | "cardio", string>;
};

type NotesByDay = Record<number, DayNotes>;

function emptyMeals(): MealsState {
  return { breakfast: {}, lunch: {}, dinner: {}, snacks: [] };
}

function emptyMealSlotNotes(snackCount = 0): MealSlotNotes {
  return { breakfast: "", lunch: "", dinner: "", snacks: Array.from({ length: snackCount }, () => "") };
}

function emptyDayNotes(): DayNotes {
  return {
    meals: emptyMealSlotNotes(),
    sections: { warmup: "", main: "", cooldown: "", cardio: "" },
  };
}

function getDayMeals(map: MealsByDay, day: number): MealsState {
  return map[day] ?? emptyMeals();
}

function getDayNotes(map: NotesByDay, day: number): DayNotes {
  return map[day] ?? emptyDayNotes();
}

function cloneFoodEntries(entries: Record<number, FoodEntry>): Record<number, FoodEntry> {
  return Object.fromEntries(
    Object.entries(entries).map(([id, e]) => [
      Number(id),
      { food: e.food, qty: e.qty },
    ]),
  );
}

function buildMealNotesPayload(notes: MealSlotNotes): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of ["breakfast", "lunch", "dinner"] as const) {
    if (notes[k]?.trim()) out[k] = notes[k].trim();
  }
  notes.snacks.forEach((n, i) => {
    if (n?.trim()) out[`snack_${i}`] = n.trim();
  });
  return out;
}

function buildSectionNotesPayload(sections: DayNotes["sections"]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of PLAN_SECTION_ORDER) {
    if (sections[k]?.trim()) out[k] = sections[k].trim();
  }
  return out;
}

type MacroTotals = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  snack_calories: number;
};

type MacroWarning = {
  id: "low_protein" | "carb_heavy" | "snack_heavy";
  message: string;
  suggestDiet?: string;
};

function mealsTotalMacros(meals: MealsState): MacroTotals {
  let calories = 0;
  let protein_g = 0;
  let carbs_g = 0;
  let fat_g = 0;
  let snack_calories = 0;
  for (const slot of ["breakfast", "lunch", "dinner"] as const) {
    for (const e of Object.values(meals[slot])) {
      calories += e.food.calories * e.qty;
      protein_g += (e.food.protein_g || 0) * e.qty;
      carbs_g += (e.food.carbs_g || 0) * e.qty;
      fat_g += (e.food.fat_g || 0) * e.qty;
    }
  }
  for (const bucket of meals.snacks) {
    for (const e of Object.values(bucket)) {
      const c = e.food.calories * e.qty;
      calories += c;
      snack_calories += c;
      protein_g += (e.food.protein_g || 0) * e.qty;
      carbs_g += (e.food.carbs_g || 0) * e.qty;
      fat_g += (e.food.fat_g || 0) * e.qty;
    }
  }
  return { calories, protein_g, carbs_g, fat_g, snack_calories };
}

function mealsTotalCalories(meals: MealsState): number {
  return mealsTotalMacros(meals).calories;
}

/** Soft warnings — never blocks saving or adding foods. */
function macroGuardrails(
  actual: MacroTotals,
  targets: { calories: number; protein_g: number; carbs_g: number; fat_g: number },
): MacroWarning[] {
  const warnings: MacroWarning[] = [];
  if (targets.calories <= 0 || actual.calories < targets.calories * 0.4) return warnings;

  const proteinLow = targets.protein_g > 0 && actual.protein_g < targets.protein_g * 0.7;
  if (proteinLow) {
    warnings.push({
      id: "low_protein",
      message: `Đạm đang thấp (${Math.round(actual.protein_g)}/${Math.round(targets.protein_g)}g). Nên bổ sung món giàu protein để hỗ trợ phục hồi khi tập.`,
      suggestDiet: "high_protein",
    });
  }

  const macroKcal = actual.protein_g * 4 + actual.carbs_g * 4 + actual.fat_g * 9;
  const carbShare = macroKcal > 0 ? (actual.carbs_g * 4) / macroKcal : 0;
  if (proteinLow && carbShare > 0.65) {
    warnings.push({
      id: "carb_heavy",
      message:
        "Thực đơn đang nghiêng nhiều tinh bột trong khi đạm còn thiếu. Cân nhắc thêm thịt, cá, trứng hoặc đậu.",
      suggestDiet: "high_protein",
    });
  }

  if (proteinLow && actual.calories > 0 && actual.snack_calories / actual.calories >= 0.4) {
    warnings.push({
      id: "snack_heavy",
      message:
        "Bữa phụ đang chiếm nhiều calo trong ngày. Nên bổ sung món chính giàu đạm ở các bữa chính.",
      suggestDiet: "high_protein",
    });
  }

  return warnings;
}

function MacroProgressRow({
  label,
  actual,
  target,
  warn,
  accentClass,
}: {
  label: string;
  actual: number;
  target: number;
  warn?: boolean;
  accentClass: string;
}) {
  const pct = target > 0 ? Math.min(100, Math.round((actual / target) * 100)) : 0;
  const ok = pct >= 85;
  const barCls = warn ? "bg-rose-500" : ok ? accentClass : "bg-slate-300";
  const textCls = warn ? "text-rose-600" : ok ? "text-slate-700" : "text-slate-500";
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className={`font-semibold ${textCls}`}>{label}</span>
        <span className={textCls}>
          {viNum(Math.round(actual))} / {viNum(Math.round(target))}g
          <span className="ml-1 text-slate-400">({pct}%)</span>
        </span>
      </div>
      <div className="macro-track mt-1 h-1.5">
        <div style={{ width: `${pct}%` }} className={barCls} />
      </div>
    </div>
  );
}

function isPer100(f: Food): boolean {
  if (f.food_kind === "ingredient") return true;
  if (f.food_kind === "dish" || f.food_kind === "packaged") return false;
  const g = f.serving_grams;
  if (g != null && Math.abs(g - 100) < 0.01) return true;
  return /100\s*g/i.test(f.serving_size || "");
}

function defaultKgPerWeek(goal: WeightGoal, weightKg: number): number {
  if (goal === "lose_weight") return defaultLossKgPerWeek(weightKg);
  if (goal === "gain_weight") return defaultGainKgPerWeek(weightKg);
  return 0;
}

function weeklyVerb(goal: WeightGoal): string {
  if (goal === "lose_weight") return "giảm";
  if (goal === "gain_weight") return "tăng";
  return "giữ";
}

/* ---------------- Workout schedule model ---------------- */
type SectionKey = PlanSectionKey;

const WARMUP_SECTION = {
  key: "warmup" as const,
  label: "Khởi động",
  icon: "🔥",
  desc: "Làm nóng cơ thể 5–10 phút",
  defaultSets: 1,
  defaultReps: 15,
  defaultRestMin: 1,
};
const MAIN_SECTION = {
  key: "main" as const,
  label: "Tập chính",
  icon: "💪",
  desc: "Bài tập trọng tâm của buổi",
  defaultSets: 3,
  defaultReps: 12,
  defaultRestMin: 2,
};
const DEFAULT_CARDIO_MIN = 10;
const CARDIO_SECTION = {
  key: "cardio" as const,
  label: "Cardio",
  icon: "🏃",
  desc: "Chọn số phút cardio cho buổi tập",
  defaultSets: 1,
  defaultReps: 1,
  defaultRestMin: 0,
};
const COOLDOWN_SECTION = {
  key: "cooldown" as const,
  label: "Giãn cơ",
  icon: "🧘",
  desc: "Thả lỏng, giãn cơ sau tập",
  defaultSets: 1,
  defaultReps: 10,
  defaultRestMin: 1,
};

/** Khởi động → tập chính → cardio → giãn cơ. */
const ALL_SECTIONS = [WARMUP_SECTION, MAIN_SECTION, CARDIO_SECTION, COOLDOWN_SECTION];

const SECTION_MAP = Object.fromEntries(
  ALL_SECTIONS.map((s) => [s.key, s]),
) as Record<SectionKey, (typeof ALL_SECTIONS)[number]>;

const SECTION_KEYS: SectionKey[] = ALL_SECTIONS.map((s) => s.key);

interface ScheduleItem {
  ex: ExerciseListItem;
  sets: number;
  /** Reps mode when durationSec is null */
  reps: number | null;
  /** Timed work (seconds) when reps is null */
  durationSec: number | null;
  restMin: number;
}

type DaySchedule = Record<SectionKey, ScheduleItem[]>;
type Schedule = Record<number, DaySchedule>;

function emptyDay(): DaySchedule {
  return { warmup: [], main: [], cooldown: [], cardio: [] };
}

function itemMinutesRaw(it: ScheduleItem): number {
  if (it.durationSec != null && it.durationSec > 0) {
    const work = (it.sets * it.durationSec) / 60;
    return work + Math.max(0, it.sets - 1) * it.restMin;
  }
  return exerciseMinutesByRest(it.sets, it.restMin);
}

function itemMinutes(it: ScheduleItem): number {
  return Math.max(1, Math.round(itemMinutesRaw(it)));
}

function formatWorkLabel(it: ScheduleItem): string {
  if (it.durationSec != null && it.durationSec > 0) {
    if (it.durationSec >= 60 && it.durationSec % 60 === 0) {
      return `${Math.round(it.durationSec / 60)} phút`;
    }
    return `${it.durationSec}s`;
  }
  return `${it.reps ?? 0} rep`;
}

function toPayloadReps(it: ScheduleItem): string {
  if (it.durationSec != null && it.durationSec > 0) {
    if (it.durationSec >= 60 && it.durationSec % 60 === 0) {
      return `${Math.round(it.durationSec / 60)} phút`;
    }
    return `${it.durationSec}s`;
  }
  return String(it.reps ?? 12);
}

function dayMinutes(day: DaySchedule | undefined): number {
  if (!day) return 0;
  const tagged = PLAN_SECTION_ORDER.flatMap((k) =>
    day[k].map((it) => ({ it, exercise_id: it.ex.id, section: k })),
  );
  const work = tagged.reduce((sum, x) => sum + itemMinutesRaw(x.it), 0);
  return Math.round(work + estimateExerciseTransitionMinutes(tagged));
}

function dayItemCount(day: DaySchedule | undefined): number {
  if (!day) return 0;
  return PLAN_SECTION_ORDER.reduce(
    (sum, k) => sum + day[k].length,
    0,
  );
}

function totalItems(schedule: Schedule): number {
  return Object.values(schedule).reduce((sum, d) => sum + dayItemCount(d), 0);
}

function buildMealsPayload(meals: MealsState): CreatePlanPayload["days"][0]["meals"] {
  const out: CreatePlanPayload["days"][0]["meals"] = [];
  for (const slot of ["breakfast", "lunch", "dinner"] as const) {
    for (const entry of Object.values(meals[slot])) {
      out.push({
        food_id: entry.food.id,
        meal_type: slot,
        servings: entry.qty,
      });
    }
  }
  for (const bucket of meals.snacks) {
    for (const entry of Object.values(bucket)) {
      out.push({
        food_id: entry.food.id,
        meal_type: "snack",
        servings: entry.qty,
      });
    }
  }
  return out;
}

function flattenMeals(meals: MealsState): { slot: string; food: Food; qty: number }[] {
  const out: { slot: string; food: Food; qty: number }[] = [];
  for (const s of MAIN_MEAL_SLOTS) {
    for (const e of Object.values(meals[s.key])) {
      out.push({ slot: s.label, food: e.food, qty: e.qty });
    }
  }
  meals.snacks.forEach((bucket, i) => {
    for (const e of Object.values(bucket)) {
      out.push({ slot: `Phụ ${i + 1}`, food: e.food, qty: e.qty });
    }
  });
  return out;
}

function foodFromTemplateItem(item: {
  food_id: number;
  name_vi: string;
  servings: number;
  calories: number;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  serving_size?: string | null;
  serving_grams?: number | null;
}): Food {
  const qty = item.servings || 1;
  return {
    id: item.food_id,
    slug: `food-${item.food_id}`,
    name_vi: item.name_vi,
    name_en: null,
    category_id: null,
    serving_size: item.serving_size || "1 phần",
    serving_grams: item.serving_grams ?? null,
    calories: qty ? item.calories / qty : item.calories,
    protein_g: qty && item.protein_g != null ? item.protein_g / qty : item.protein_g ?? 0,
    carbs_g: qty && item.carbs_g != null ? item.carbs_g / qty : item.carbs_g ?? 0,
    fat_g: qty && item.fat_g != null ? item.fat_g / qty : item.fat_g ?? 0,
    fiber_g: null,
    sugar_g: null,
    sodium_mg: null,
    is_verified: false,
    is_common: true,
    tags: [],
    image_url: null,
  };
}

function mealsStateFromTemplateItems(
  items: {
    food_id: number;
    name_vi: string;
    meal_type: string;
    servings: number;
    calories: number;
    protein_g: number | null;
    carbs_g: number | null;
    fat_g: number | null;
    serving_size?: string | null;
    serving_grams?: number | null;
    sort_order: number;
  }[],
): MealsState {
  const meals = emptyMeals();
  const snacks: Record<number, FoodEntry> = {};
  const sorted = [...items].sort((a, b) => a.sort_order - b.sort_order);
  for (const item of sorted) {
    const entry: FoodEntry = { food: foodFromTemplateItem(item), qty: item.servings || 1 };
    if (item.meal_type === "breakfast" || item.meal_type === "lunch" || item.meal_type === "dinner") {
      meals[item.meal_type][item.food_id] = entry;
    } else {
      snacks[item.food_id] = entry;
    }
  }
  meals.snacks = Object.keys(snacks).length ? [snacks] : [];
  return meals;
}

function mealNotesFromTemplate(notes: Record<string, string>): MealSlotNotes {
  const base = emptyMealSlotNotes(0);
  base.breakfast = notes.breakfast || "";
  base.lunch = notes.lunch || "";
  base.dinner = notes.dinner || "";
  const snackNotes = Object.keys(notes)
    .filter((k) => k.startsWith("snack"))
    .sort()
    .map((k) => notes[k] || "");
  base.snacks = snackNotes.length ? snackNotes : [];
  return base;
}

/* ======================== Main ======================== */
export default function PlanBuilder() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [toast, setToast] = useState<string | null>(null);

  // step 1
  const [weightGoal, setWeightGoal] = useState<WeightGoal>("lose_weight");
  const [gender, setGender] = useState<Gender>("male");
  const [age, setAge] = useState("25");
  const [height, setHeight] = useState("170");
  const [weight, setWeight] = useState("65");
  const [activity, setActivity] = useState<Activity>("moderate");
  const [sessionsPerWeek, setSessionsPerWeek] = useState(3);
  const experienceLevel = 2;
  // step 2
  const [nutrition, setNutrition] = useState<NutritionResult | null>(null);
  const [macroPct, setMacroPct] = useState({ protein: 30, carbs: 40, fat: 30 });
  const [durationWeeks, setDurationWeeks] = useState(() => defaultDurationWeeks(2));
  const [kgPerWeek, setKgPerWeek] = useState(0.5);
  const [mealsByDay, setMealsByDay] = useState<MealsByDay>({});
  const [notesByDay, setNotesByDay] = useState<NotesByDay>({});

  // step 3
  const [schedule, setSchedule] = useState<Schedule>({});

  // step 4
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const target = nutrition?.target ?? 0;

  function toggleWeightGoal(g: WeightGoal) {
    setWeightGoal((prev) => (prev === g ? prev : g));
  }

  function patchMacroPct(field: "protein" | "carbs" | "fat", value: number) {
    const v = Math.min(80, Math.max(0, Math.round(Number.isFinite(value) ? value : 0)));
    const next = { ...macroPct, [field]: v };
    if (field === "protein" || field === "fat") {
      next.carbs = Math.max(0, 100 - next.protein - next.fat);
    } else {
      next.fat = Math.max(0, 100 - next.protein - next.carbs);
    }
    setMacroPct(next);
    if (nutrition) setNutrition(applyMacroPercents(nutrition, next));
  }

  function goStep1Next() {
    const w = parseFloat(weight);
    const h = parseFloat(height);
    const a = parseInt(age, 10);
    if (!(a >= 10 && a <= 150)) {
      setToast("Tuổi phải từ 10 đến 150.");
      return;
    }
    if (!(h >= 100 && h <= 250)) {
      setToast("Chiều cao phải từ 100 đến 250 cm.");
      return;
    }
    if (!(w >= 30 && w <= 150)) {
      setToast("Cân nặng phải từ 30 đến 150 kg.");
      return;
    }
    const base = computeNutrition(gender, weightGoal, activity, w, h, a);
    const rate = defaultKgPerWeek(weightGoal, w);
    setKgPerWeek(rate);
    const n = targetFromWeeklyRate(base.tdee, weightGoal, rate, w, { gender, bmr: base.bmr });
    setMacroPct(gramsToMacroPercents(n));
    setNutrition(n);
    setStep(2);
  }

  function handleKgPerWeekChange(rate: number) {
    setKgPerWeek(rate);
    if (!nutrition) return;
    const w = parseFloat(weight);
    const n = targetFromWeeklyRate(nutrition.tdee, weightGoal, rate, w, { gender, bmr: nutrition.bmr });
    setNutrition(applyMacroPercents(n, macroPct));
  }

  function goStep2Next() {
    const overDays = Array.from({ length: sessionsPerWeek }, (_, i) => i).filter(
      (d) => mealsTotalCalories(getDayMeals(mealsByDay, d)) > target,
    );
    if (overDays.length > 0) {
      const labels = overDays.map((d) => `Ngày ${d + 1}`).join(", ");
      setToast(
        `Cảnh báo: ${labels} vượt calo mục tiêu (${viNum(target)} kcal). Bạn vẫn có thể tiếp tục.`,
      );
    }
    setStep(3);
  }

  function goStep3Next() {
    if (totalItems(schedule) === 0) {
      setToast("Hãy thêm ít nhất một bài tập.");
      return;
    }
    setStep(4);
  }

  return (
    <section className="relative">
      <div className="mb-6">
        <h1 className="type-display">Tự tạo lịch tập</h1>
        <p className="mt-1 text-sm text-slate-500">Làm theo từng bước — chỉ vài phút là xong.</p>
        <p className="mt-2 rounded-xl bg-brand-50 px-3 py-2 text-xs font-medium text-brand-800">
          Tự tạo lịch miễn phí. Chưa đăng nhập: lịch lưu bằng link cố định; khi đăng ký/đăng nhập sẽ tự gắn vào tài khoản.
        </p>
      </div>

      <Stepper step={step} />

      {step === 1 && (
        <Step1Info
          weightGoal={weightGoal}
          toggleWeightGoal={toggleWeightGoal}
          gender={gender}
          setGender={setGender}
          age={age}
          setAge={setAge}
          height={height}
          setHeight={setHeight}
          weight={weight}
          setWeight={setWeight}
          activity={activity}
          setActivity={setActivity}
          sessionsPerWeek={sessionsPerWeek}
          setSessionsPerWeek={setSessionsPerWeek}
          onNext={goStep1Next}
        />
      )}

      {step === 2 && nutrition && (
        <Step2Meals
          nutrition={nutrition}
          weightGoal={weightGoal}
          sessionsPerWeek={sessionsPerWeek}
          durationWeeks={durationWeeks}
          setDurationWeeks={setDurationWeeks}
          experienceLevel={experienceLevel}
          kgPerWeek={kgPerWeek}
          onKgPerWeekChange={handleKgPerWeekChange}
          weightKg={parseFloat(weight)}
          macroPct={macroPct}
          onMacroPctChange={patchMacroPct}
          mealsByDay={mealsByDay}
          setMealsByDay={setMealsByDay}
          notesByDay={notesByDay}
          setNotesByDay={setNotesByDay}
          notify={setToast}
          onBack={() => setStep(1)}
          onNext={goStep2Next}
        />
      )}

      {step === 3 && (
        <Step3Exercises
          sessionsPerWeek={sessionsPerWeek}
          schedule={schedule}
          setSchedule={setSchedule}
          notesByDay={notesByDay}
          setNotesByDay={setNotesByDay}
          notify={setToast}
          onBack={() => setStep(2)}
          onNext={goStep3Next}
        />
      )}

      {step === 4 && nutrition && (
        <Step4Review
          nutrition={nutrition}
          weightGoal={weightGoal}
          sessionsPerWeek={sessionsPerWeek}
          durationWeeks={durationWeeks}
          experienceLevel={experienceLevel}
          schedule={schedule}
          mealsByDay={mealsByDay}
          notesByDay={notesByDay}
          creating={creating}
          setCreating={setCreating}
          router={router}
          notify={setToast}
          onBack={() => setStep(3)}
          onRestart={() => {
            setStep(1);
            setSchedule({});
            setMealsByDay({});
            setNotesByDay({});
          }}
        />
      )}

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-[60] w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 md:bottom-8">
          <div className="flex items-center gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white shadow-2xl">
            <span className="text-lg">⚠️</span>
            <span>{toast}</span>
          </div>
        </div>
      )}
    </section>
  );
}

/* ---------------- Shared UI ---------------- */
function Stepper({ step }: { step: number }) {
  return (
    <div className="mb-6 flex items-center gap-2">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const active = n === step;
        const done = n < step;
        return (
          <div key={label} className="flex flex-1 items-center gap-2">
            <div className="flex items-center gap-2">
              <div
                className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold transition ${
                  done
                    ? "bg-brand-500 text-white"
                    : active
                      ? "bg-brand-500 text-white ring-4 ring-brand-100"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {done ? "✓" : n}
              </div>
              <span className={`hidden text-sm font-semibold sm:inline ${active || done ? "text-slate-700" : "text-slate-400"}`}>
                {label}
              </span>
            </div>
            {n < STEPS.length && <div className={`h-0.5 flex-1 rounded ${done ? "bg-brand-500" : "bg-slate-200"}`} />}
          </div>
        );
      })}
    </div>
  );
}

function NavButtons({
  onBack,
  onNext,
  nextLabel,
  nextDisabled,
}: {
  onBack: () => void;
  onNext: () => void;
  nextLabel: string;
  nextDisabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onBack}
        className="rounded-xl border border-slate-200 bg-white px-6 py-3 font-semibold text-slate-600 transition hover:border-slate-300"
      >
        Quay lại
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={nextDisabled}
        className="flex-1 rounded-xl bg-brand-500 py-3 font-bold text-white shadow-soft transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {nextLabel}
      </button>
    </div>
  );
}

function NoteField({
  value,
  onChange,
  placeholder = "Ghi chú / lưu ý cho mục này…",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="mt-2.5">
      <label className="mb-1 block text-xs font-semibold text-slate-500">Lưu ý</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        placeholder={placeholder}
        className="field min-h-[56px] resize-y text-sm"
      />
    </div>
  );
}

function NoteReadonly({ note }: { note?: string | null }) {
  if (!note || !note.trim()) return null;
  return (
    <p className="mt-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
      <span className="font-semibold">Lưu ý: </span>
      {note.trim()}
    </p>
  );
}

function Stepper2({
  label,
  value,
  onDec,
  onInc,
  incDisabled,
  inactive = false,
  onActivate,
  display,
  min = 1,
  max = 50,
}: {
  label: string;
  value: number;
  onDec: () => void;
  onInc: () => void;
  incDisabled?: boolean;
  /** Inactive field shows "—" — click block to switch mode */
  inactive?: boolean;
  onActivate?: () => void;
  display?: string;
  min?: number;
  max?: number;
}) {
  return (
    <div
      role={inactive ? "button" : undefined}
      tabIndex={inactive ? 0 : undefined}
      onClick={inactive ? onActivate : undefined}
      onKeyDown={
        inactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onActivate?.();
              }
            }
          : undefined
      }
      className={`flex items-center justify-between rounded-lg bg-white px-2.5 py-1.5 ring-1 ring-slate-200 ${
        inactive
          ? "cursor-pointer opacity-45 transition hover:opacity-70 hover:ring-brand-300"
          : ""
      }`}
    >
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDec();
          }}
          disabled={inactive || value <= min}
          className="grid h-7 w-7 place-items-center rounded-md bg-slate-100 text-lg font-bold text-slate-600 transition hover:bg-slate-200 disabled:opacity-40"
        >
          −
        </button>
        <span className="min-w-6 text-center text-sm font-bold">
          {inactive ? "—" : (display ?? value)}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onInc();
          }}
          disabled={inactive || incDisabled || value >= max}
          className="grid h-7 w-7 place-items-center rounded-md bg-brand-500 text-lg font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
        >
          +
        </button>
      </div>
    </div>
  );
}

/* ---------------- Step 1 — Thông tin ---------------- */
function Step1Info({
  weightGoal,
  toggleWeightGoal,
  gender,
  setGender,
  age,
  setAge,
  height,
  setHeight,
  weight,
  setWeight,
  activity,
  setActivity,
  sessionsPerWeek,
  setSessionsPerWeek,
  onNext,
}: {
  weightGoal: WeightGoal;
  toggleWeightGoal: (g: WeightGoal) => void;
  gender: Gender;
  setGender: (g: Gender) => void;
  age: string;
  setAge: (v: string) => void;
  height: string;
  setHeight: (v: string) => void;
  weight: string;
  setWeight: (v: string) => void;
  activity: Activity;
  setActivity: (v: Activity) => void;
  sessionsPerWeek: number;
  setSessionsPerWeek: (v: number) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-5 rounded-2xl bg-white p-5 shadow-soft">
      <div className="rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-800">
        Thông tin này giúp hệ thống gợi ý thực đơn và bài tập phù hợp.
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mục tiêu chính</label>
        <div className="grid grid-cols-3 gap-3">
          {WEIGHT_GOAL_OPTS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => toggleWeightGoal(o.value)}
              className={`flex flex-col items-center gap-1 rounded-xl border py-3 text-sm font-semibold transition ${
                weightGoal === o.value
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-slate-200 text-slate-500 hover:border-brand-300"
              }`}
            >
              <span className="text-xl">{o.icon}</span>
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Giới tính</label>
        <div className="grid grid-cols-2 gap-3">
          {(["male", "female"] as Gender[]).map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setGender(g)}
              className={`rounded-xl border py-2.5 font-semibold transition ${
                gender === g ? "border-brand-500 bg-brand-500 text-white" : "border-slate-200 text-slate-500 hover:border-brand-300"
              }`}
            >
              {g === "male" ? "Nam" : "Nữ"}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-slate-600">Tuổi</label>
          <input type="number" min={10} max={150} value={age} onChange={(e) => setAge(e.target.value)} className="field" />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-slate-600">Chiều cao (cm)</label>
          <input type="number" min={100} max={250} value={height} onChange={(e) => setHeight(e.target.value)} className="field" />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-slate-600">Cân nặng (kg)</label>
          <input type="number" min={30} max={150} step={0.1} value={weight} onChange={(e) => setWeight(e.target.value)} className="field" />
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">{ACTIVITY_FIELD_LABEL}</label>
        <select value={activity} onChange={(e) => setActivity(e.target.value as Activity)} className="field">
          {ACTIVITY_OPTS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">
          Số buổi mỗi tuần: <span className="text-brand-600">{sessionsPerWeek} buổi</span>
        </label>
        <input type="range" min={1} max={7} value={sessionsPerWeek} onChange={(e) => setSessionsPerWeek(Number(e.target.value))} className="w-full accent-brand-500" />
        <p className="mt-1.5 text-xs text-slate-400">
          Bạn sẽ chọn thực đơn và bài tập riêng cho từng buổi ở bước sau.
        </p>
      </div>

      <button
        type="button"
        onClick={onNext}
        className="w-full rounded-xl bg-brand-500 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600"
      >
        Chọn thực đơn
      </button>
    </div>
  );
}

function WeeklyRateSlider({
  weightGoal,
  weightKg,
  kgPerWeek,
  target,
  onKgPerWeekChange,
}: {
  weightGoal: WeightGoal;
  weightKg: number;
  kgPerWeek: number;
  target: number;
  onKgPerWeekChange: (v: number) => void;
}) {
  const lose = weightGoal === "lose_weight";
  const range = lose ? lossWeeklyKgRange(weightKg) : gainWeeklyKgRange(weightKg);
  const pct = weightKg > 0 ? Math.round((kgPerWeek / weightKg) * 1000) / 10 : 0;
  return (
    <div className="rounded-2xl bg-white p-4 shadow-soft">
      <label className="mb-1.5 block text-sm font-semibold text-slate-600">
        Mỗi tuần muốn {weeklyVerb(weightGoal)}:{" "}
        <span className="text-brand-600">{formatKgVi(kgPerWeek)}/tuần</span>
        {Number.isFinite(pct) ? (
          <span className="font-normal text-slate-400"> · {String(pct).replace(".", ",")}%</span>
        ) : null}
      </label>
      <input
        type="range"
        min={range.min}
        max={range.max}
        step={0.05}
        value={Math.min(range.max, Math.max(range.min, kgPerWeek))}
        onChange={(e) => onKgPerWeekChange(Number(e.target.value))}
        className="w-full accent-brand-500"
      />
      <p className="mt-1 text-xs text-slate-400">
        Calo mục tiêu: <b className="text-brand-600">{viNum(target)} kcal/ngày</b>
      </p>
      {lose ? (
        <p className="mt-1 text-xs text-slate-400">{LOSS_WEEKLY_HINT}</p>
      ) : null}
    </div>
  );
}

/* ---------------- Step 2 — Thực đơn ---------------- */
function Step2Meals({
  nutrition,
  weightGoal,
  sessionsPerWeek,
  durationWeeks,
  setDurationWeeks,
  experienceLevel,
  kgPerWeek,
  onKgPerWeekChange,
  weightKg,
  macroPct,
  onMacroPctChange,
  mealsByDay,
  setMealsByDay,
  notesByDay,
  setNotesByDay,
  notify,
  onBack,
  onNext,
}: {
  nutrition: NutritionResult;
  weightGoal: WeightGoal;
  sessionsPerWeek: number;
  durationWeeks: number;
  setDurationWeeks: (v: number) => void;
  experienceLevel: number;
  kgPerWeek: number;
  onKgPerWeekChange: (v: number) => void;
  weightKg: number;
  macroPct: { protein: number; carbs: number; fat: number };
  onMacroPctChange: (field: "protein" | "carbs" | "fat", value: number) => void;
  mealsByDay: MealsByDay;
  setMealsByDay: React.Dispatch<React.SetStateAction<MealsByDay>>;
  notesByDay: NotesByDay;
  setNotesByDay: React.Dispatch<React.SetStateAction<NotesByDay>>;
  notify: (msg: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [activeDay, setActiveDay] = useState(0);
  const [templates, setTemplates] = useState<MealTemplateSummary[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const loggedIn = isAuthenticated();

  useEffect(() => {
    if (activeDay > sessionsPerWeek - 1) setActiveDay(0);
  }, [sessionsPerWeek, activeDay]);

  useEffect(() => {
    if (!loggedIn) return;
    let cancelled = false;
    setTemplatesLoading(true);
    mealTemplatesApi
      .list()
      .then((rows) => {
        if (!cancelled) setTemplates(rows);
      })
      .catch(() => {
        if (!cancelled) setTemplates([]);
      })
      .finally(() => {
        if (!cancelled) setTemplatesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loggedIn]);

  const days = Array.from({ length: sessionsPerWeek }, (_, i) => i);
  const meals = getDayMeals(mealsByDay, activeDay);
  const dayNotes = getDayNotes(notesByDay, activeDay);
  const macros = useMemo(
    () => mealsTotalMacros(getDayMeals(mealsByDay, activeDay)),
    [mealsByDay, activeDay],
  );
  const foodTotal = macros.calories;

  const target = nutrition.target;
  const remaining = target - foodTotal;
  const pctUsed = target > 0 ? Math.min(100, Math.round((foodTotal / target) * 100)) : 0;
  const overTarget = foodTotal > target;
  const barColor = overTarget ? "bg-rose-500" : pctUsed >= 85 ? "bg-amber-400" : "bg-brand-500";
  const yKg = Math.abs(nutrition.weekly_kg ?? kgPerWeek);

  const warnings = useMemo(
    () =>
      macroGuardrails(macros, {
        calories: nutrition.target,
        protein_g: nutrition.protein_g,
        carbs_g: nutrition.carbs_g,
        fat_g: nutrition.fat_g,
      }),
    [macros, nutrition.target, nutrition.protein_g, nutrition.carbs_g, nutrition.fat_g],
  );
  const proteinWarn = warnings.some((w) => w.id === "low_protein");

  function warnIfOverCalories(addCals: number) {
    if (foodTotal + addCals > target) {
      notify(
        `Cảnh báo: vượt calo mục tiêu (còn ${Math.max(0, Math.round(remaining))} kcal). Bạn vẫn có thể thêm món.`,
      );
    }
  }

  function updateDayMeals(updater: (prev: MealsState) => MealsState) {
    setMealsByDay((prev) => ({ ...prev, [activeDay]: updater(getDayMeals(prev, activeDay)) }));
  }

  function updateDayMealNotes(updater: (prev: MealSlotNotes) => MealSlotNotes) {
    setNotesByDay((prev) => {
      const cur = getDayNotes(prev, activeDay);
      return { ...prev, [activeDay]: { ...cur, meals: updater(cur.meals) } };
    });
  }

  function updateSlot(
    slot: "breakfast" | "lunch" | "dinner",
    updater: (prev: Record<number, FoodEntry>) => Record<number, FoodEntry>,
  ) {
    updateDayMeals((m) => ({ ...m, [slot]: updater(m[slot]) }));
  }

  function updateSnack(snackIdx: number, updater: (prev: Record<number, FoodEntry>) => Record<number, FoodEntry>) {
    updateDayMeals((m) => {
      const snacks = [...m.snacks];
      snacks[snackIdx] = updater(snacks[snackIdx] ?? {});
      return { ...m, snacks };
    });
  }

  function addSnackBucket() {
    if (meals.snacks.length >= 3) return;
    updateDayMeals((m) => ({ ...m, snacks: [...m.snacks, {}] }));
    updateDayMealNotes((n) => ({ ...n, snacks: [...n.snacks, ""] }));
  }

  function applyMainSlotToAllDays(slot: "breakfast" | "lunch" | "dinner") {
    const sourceEntries = cloneFoodEntries(meals[slot]);
    const sourceNote = dayNotes.meals[slot];
    setMealsByDay((prev) => {
      const next = { ...prev };
      for (const d of days) {
        if (d === activeDay) continue;
        const cur = getDayMeals(next, d);
        next[d] = { ...cur, [slot]: cloneFoodEntries(sourceEntries) };
      }
      return next;
    });
    setNotesByDay((prev) => {
      const next = { ...prev };
      for (const d of days) {
        if (d === activeDay) continue;
        const cur = getDayNotes(next, d);
        next[d] = { ...cur, meals: { ...cur.meals, [slot]: sourceNote } };
      }
      return next;
    });
    notify(`Đã áp dụng ${slot === "breakfast" ? "Sáng" : slot === "lunch" ? "Trưa" : "Tối"} cho tất cả các ngày.`);
  }

  function applySnackToAllDays(snackIdx: number) {
    const sourceBucket = cloneFoodEntries(meals.snacks[snackIdx] ?? {});
    const sourceNote = dayNotes.meals.snacks[snackIdx] ?? "";
    setMealsByDay((prev) => {
      const next = { ...prev };
      for (const d of days) {
        if (d === activeDay) continue;
        const cur = getDayMeals(next, d);
        const snacks = [...cur.snacks];
        while (snacks.length <= snackIdx) snacks.push({});
        snacks[snackIdx] = cloneFoodEntries(sourceBucket);
        next[d] = { ...cur, snacks };
      }
      return next;
    });
    setNotesByDay((prev) => {
      const next = { ...prev };
      for (const d of days) {
        if (d === activeDay) continue;
        const cur = getDayNotes(next, d);
        const snacks = [...cur.meals.snacks];
        while (snacks.length <= snackIdx) snacks.push("");
        snacks[snackIdx] = sourceNote;
        next[d] = { ...cur, meals: { ...cur.meals, snacks } };
      }
      return next;
    });
    notify(`Đã áp dụng Bữa phụ ${snackIdx + 1} cho tất cả các ngày.`);
  }

  function copyFromDay(sourceDay: number) {
    const sourceMeals = getDayMeals(mealsByDay, sourceDay);
    const sourceNotes = getDayNotes(notesByDay, sourceDay);
    setMealsByDay((prev) => ({
      ...prev,
      [activeDay]: {
        breakfast: cloneFoodEntries(sourceMeals.breakfast),
        lunch: cloneFoodEntries(sourceMeals.lunch),
        dinner: cloneFoodEntries(sourceMeals.dinner),
        snacks: sourceMeals.snacks.map(cloneFoodEntries),
      },
    }));
    setNotesByDay((prev) => ({
      ...prev,
      [activeDay]: {
        meals: {
          breakfast: sourceNotes.meals.breakfast,
          lunch: sourceNotes.meals.lunch,
          dinner: sourceNotes.meals.dinner,
          snacks: [...sourceNotes.meals.snacks],
        },
        sections: { ...sourceNotes.sections },
      },
    }));
    notify(`Đã sao chép thực đơn từ Ngày ${sourceDay + 1}.`);
  }

  async function saveDayAsTemplate() {
    if (!loggedIn) {
      notify("Đăng nhập để lưu mẫu thực đơn.");
      return;
    }
    const items = buildMealsPayload(meals);
    if (!items.length) {
      notify("Ngày này chưa có món nào để lưu mẫu.");
      return;
    }
    setSavingTemplate(true);
    try {
      const created = await mealTemplatesApi.create({
        title_vi: `Thực đơn Ngày ${activeDay + 1} — ${viNum(foodTotal)} kcal`,
        target_calories: Math.round(foodTotal) || nutrition.target,
        meal_notes: buildMealNotesPayload(dayNotes.meals),
        items,
      });
      setTemplates((prev) => [
        {
          id: created.id,
          title_vi: created.title_vi,
          target_calories: created.target_calories,
          item_count: created.item_count,
          total_calories: created.total_calories,
          created_at: created.created_at,
        },
        ...prev,
      ]);
      notify("Đã lưu mẫu thực đơn.");
    } catch (ex) {
      notify((ex as Error).message || "Không lưu được mẫu.");
    } finally {
      setSavingTemplate(false);
    }
  }

  async function applyTemplate(templateId: number) {
    try {
      const detail = await mealTemplatesApi.get(templateId);
      const nextMeals = mealsStateFromTemplateItems(detail.items);
      const nextNotes = mealNotesFromTemplate(detail.meal_notes || {});
      if (nextMeals.snacks.length && nextNotes.snacks.length < nextMeals.snacks.length) {
        while (nextNotes.snacks.length < nextMeals.snacks.length) nextNotes.snacks.push("");
      }
      setMealsByDay((prev) => ({ ...prev, [activeDay]: nextMeals }));
      setNotesByDay((prev) => {
        const cur = getDayNotes(prev, activeDay);
        return { ...prev, [activeDay]: { ...cur, meals: nextNotes } };
      });
      notify(`Đã áp dụng mẫu “${detail.title_vi || "Thực đơn"}”.`);
    } catch (ex) {
      notify((ex as Error).message || "Không áp dụng được mẫu.");
    }
  }

  const copySources = days.filter(
    (d) => d !== activeDay && mealsTotalCalories(getDayMeals(mealsByDay, d)) > 0,
  );

  return (
    <div className="space-y-5">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <p className="text-sm leading-relaxed text-slate-600">
          Dựa vào mục tiêu và thông tin của bạn, calo một ngày cần nạp:{" "}
          <b className="text-brand-600">{viNum(target)} kcal</b>. Ước lượng 1 tuần sẽ{" "}
          <b>{weeklyVerb(weightGoal)}</b> <b>{yKg}</b> kg. Trong vòng{" "}
          <b>{durationWeeks}</b> tuần.
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Chọn thực đơn riêng cho từng buổi tập trong tuần ({sessionsPerWeek} buổi).
        </p>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-rose-50 px-2 py-2">
            <p className="font-bold text-rose-600">{viNum(nutrition.protein_g)}g</p>
            <p className="text-slate-500">Đạm</p>
          </div>
          <div className="rounded-xl bg-amber-50 px-2 py-2">
            <p className="font-bold text-amber-600">{viNum(nutrition.carbs_g)}g</p>
            <p className="text-slate-500">Tinh bột</p>
          </div>
          <div className="rounded-xl bg-sky-50 px-2 py-2">
            <p className="font-bold text-sky-600">{viNum(nutrition.fat_g)}g</p>
            <p className="text-slate-500">Béo</p>
          </div>
        </div>
        <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="mb-2 text-sm font-semibold text-slate-600">Tỷ lệ macro (%)</p>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                { field: "protein" as const, label: "Đạm", accent: "text-rose-600" },
                { field: "carbs" as const, label: "Tinh bột", accent: "text-amber-600" },
                { field: "fat" as const, label: "Béo", accent: "text-sky-600" },
              ] as const
            ).map((row) => (
              <label key={row.field} className="block">
                <span className={`mb-1 block text-[11px] font-semibold ${row.accent}`}>{row.label}</span>
                <input
                  type="number"
                  min={0}
                  max={80}
                  value={macroPct[row.field]}
                  onChange={(e) => onMacroPctChange(row.field, Number(e.target.value))}
                  className="field px-2 py-1.5 text-center text-sm font-bold"
                />
              </label>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Tổng {macroPct.protein + macroPct.carbs + macroPct.fat}% — chỉnh một ô, các ô còn lại sẽ cân lại cho đủ 100%.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl bg-white p-4 shadow-soft">
          <label className="mb-1.5 block text-sm font-semibold text-slate-600">
            Thời gian kế hoạch: <span className="text-brand-600">{durationWeeks} tuần</span>
          </label>
          <input
            type="range"
            min={MIN_DURATION_WEEKS}
            max={MAX_DURATION_WEEKS}
            value={durationWeeks}
            onChange={(e) => setDurationWeeks(Number(e.target.value))}
            className="w-full accent-brand-500"
          />
          <p className="mt-1.5 text-xs text-slate-400">{progressionHintVi(experienceLevel)}</p>
        </div>

        {(weightGoal === "lose_weight" || weightGoal === "gain_weight") && (
          <WeeklyRateSlider
            weightGoal={weightGoal}
            weightKg={weightKg}
            kgPerWeek={kgPerWeek}
            target={target}
            onKgPerWeekChange={onKgPerWeekChange}
          />
        )}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {days.map((d) => {
          const cals = mealsTotalCalories(getDayMeals(mealsByDay, d));
          const on = d === activeDay;
          return (
            <button
              key={d}
              type="button"
              onClick={() => setActiveDay(d)}
              className={`flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition ${
                on ? "border-brand-500 bg-brand-500 text-white shadow-soft" : "border-slate-200 bg-white text-slate-600 hover:border-brand-300"
              }`}
            >
              Ngày {d + 1}
              {cals > 0 && (
                <span className={`rounded-full px-1.5 text-[11px] font-bold ${on ? "bg-white/25" : "bg-brand-50 text-brand-600"}`}>
                  Calo vào {viNum(cals)}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="sticky top-16 z-10 space-y-3 rounded-2xl bg-white p-4 shadow-soft">
        <div>
          <div className="flex items-end justify-between">
            <p className="text-sm font-semibold text-slate-600">Tổng calo Ngày {activeDay + 1}</p>
            <p className="text-sm">
              <span className={`text-lg font-bold ${overTarget ? "text-rose-500" : "text-brand-600"}`}>
                {viNum(foodTotal)}
              </span>
              <span className="text-slate-400"> / {viNum(target)} kcal</span>
            </p>
          </div>
          <div className="macro-track mt-2 h-3">
            <div style={{ width: `${Math.min(100, pctUsed)}%` }} className={barColor} />
          </div>
          <p className={`mt-1.5 text-xs ${overTarget ? "font-medium text-rose-500" : "text-slate-400"}`}>
            {overTarget
              ? `Đã vượt mục tiêu ${viNum(foodTotal - target)} kcal — bạn vẫn có thể thêm món hoặc tiếp tục`
              : remaining > 0
                ? `Còn lại ${viNum(remaining)} kcal`
                : "Đã đạt mục tiêu calo"}
          </p>
        </div>

        <div className="space-y-2 border-t border-slate-100 pt-3">
          <MacroProgressRow
            label="Đạm (Protein)"
            actual={macros.protein_g}
            target={nutrition.protein_g}
            warn={proteinWarn}
            accentClass="bg-rose-500"
          />
          <MacroProgressRow
            label="Tinh bột (Carb)"
            actual={macros.carbs_g}
            target={nutrition.carbs_g}
            warn={warnings.some((w) => w.id === "carb_heavy")}
            accentClass="bg-amber-400"
          />
          <MacroProgressRow
            label="Chất béo (Fat)"
            actual={macros.fat_g}
            target={nutrition.fat_g}
            accentClass="bg-sky-500"
          />
        </div>

        {warnings.length > 0 && (
          <div className="space-y-2 rounded-xl bg-amber-50 px-3 py-2.5 text-xs leading-relaxed text-amber-950">
            {warnings.map((w) => (
              <p key={w.id}>{w.message}</p>
            ))}
            <p className="font-medium text-amber-800/80">Bạn vẫn có thể tiếp tục hoặc lưu mẫu.</p>
          </div>
        )}

        <p className="text-[11px] leading-snug text-slate-400">
          Ước lượng dinh dưỡng, không thay lời khuyên chuyên môn.
        </p>
      </div>

      {copySources.length > 0 && foodTotal === 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-white p-4 shadow-soft">
          <span className="text-sm font-semibold text-slate-600">Sao chép thực đơn từ:</span>
          {copySources.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => copyFromDay(d)}
              className="chip"
            >
              Ngày {d + 1}
            </button>
          ))}
        </div>
      )}

      {loggedIn && (
        <div className="space-y-3 rounded-2xl bg-white p-4 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-700">Mẫu thực đơn</p>
            <button
              type="button"
              disabled={savingTemplate || foodTotal <= 0}
              onClick={() => void saveDayAsTemplate()}
              className="rounded-lg bg-brand-50 px-3 py-1.5 text-xs font-bold text-brand-700 hover:bg-brand-100 disabled:opacity-50"
            >
              {savingTemplate ? "Đang lưu…" : "Lưu ngày này thành mẫu"}
            </button>
          </div>
          {templatesLoading ? (
            <p className="text-xs text-slate-400">Đang tải mẫu…</p>
          ) : templates.length === 0 ? (
            <p className="text-xs text-slate-400">
              Chưa có mẫu. Chọn món rồi bấm “Lưu ngày này thành mẫu” để dùng lại sau.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {templates.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => void applyTemplate(t.id)}
                  className="chip"
                  title={`${t.item_count} món · ${viNum(t.total_calories)} kcal`}
                >
                  {t.title_vi || `Mẫu #${t.id}`}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {MAIN_MEAL_SLOTS.map((slot) => (
        <MealSlotPicker
          key={`${activeDay}-${slot.key}`}
          title={`${slot.icon} ${slot.label}`}
          entries={meals[slot.key]}
          onUpdate={(updater) => updateSlot(slot.key, updater)}
          warnIfOverCalories={warnIfOverCalories}
          note={dayNotes.meals[slot.key]}
          onNoteChange={(v) => updateDayMealNotes((n) => ({ ...n, [slot.key]: v }))}
          showApplyToAll={sessionsPerWeek > 1}
          onApplyToAll={() => applyMainSlotToAllDays(slot.key)}
        />
      ))}

      {meals.snacks.map((bucket, idx) => (
        <MealSlotPicker
          key={`${activeDay}-snack-${idx}`}
          title={`🍎 Bữa phụ ${idx + 1}`}
          entries={bucket}
          onUpdate={(updater) => updateSnack(idx, updater)}
          warnIfOverCalories={warnIfOverCalories}
          note={dayNotes.meals.snacks[idx] ?? ""}
          onNoteChange={(v) =>
            updateDayMealNotes((n) => {
              const snacks = [...n.snacks];
              while (snacks.length <= idx) snacks.push("");
              snacks[idx] = v;
              return { ...n, snacks };
            })
          }
          showApplyToAll={sessionsPerWeek > 1}
          onApplyToAll={() => applySnackToAllDays(idx)}
        />
      ))}

      {meals.snacks.length < 3 && (
        <button
          type="button"
          onClick={addSnackBucket}
          className="w-full rounded-xl border border-dashed border-brand-300 bg-brand-50 py-3 text-sm font-semibold text-brand-700 transition hover:bg-brand-100"
        >
          + Thêm bữa phụ
        </button>
      )}

      <NavButtons onBack={onBack} onNext={onNext} nextLabel="Chọn bài tập" />
    </div>
  );
}

function MealSlotPicker({
  title,
  entries,
  onUpdate,
  warnIfOverCalories,
  note,
  onNoteChange,
  showApplyToAll,
  onApplyToAll,
}: {
  title: string;
  entries: Record<number, FoodEntry>;
  onUpdate: (updater: (prev: Record<number, FoodEntry>) => Record<number, FoodEntry>) => void;
  warnIfOverCalories: (addCals: number) => void;
  note: string;
  onNoteChange: (v: string) => void;
  showApplyToAll?: boolean;
  onApplyToAll?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const selectedList = Object.values(entries);
  const slotCals = selectedList.reduce((s, e) => s + e.food.calories * e.qty, 0);

  function increment(food: Food) {
    warnIfOverCalories(food.calories);
    onUpdate((prev) => {
      const cur = prev[food.id];
      return {
        ...prev,
        [food.id]: { food, qty: (cur?.qty ?? 0) + 1 },
      };
    });
  }

  function decrementOrRemove(food: Food) {
    onUpdate((prev) => {
      const cur = prev[food.id];
      if (!cur || cur.qty <= 1) {
        const next = { ...prev };
        delete next[food.id];
        return next;
      }
      return { ...prev, [food.id]: { ...cur, qty: cur.qty - 1 } };
    });
  }

  function remove(food: Food) {
    onUpdate((prev) => {
      const next = { ...prev };
      delete next[food.id];
      return next;
    });
  }

  function toggle(food: Food) {
    if (entries[food.id]) {
      onUpdate((prev) => {
        const next = { ...prev };
        delete next[food.id];
        return next;
      });
    } else {
      warnIfOverCalories(food.calories);
      onUpdate((prev) => ({ ...prev, [food.id]: { food, qty: 1 } }));
    }
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-bold">{title}</h3>
          <p className="mt-0.5 text-xs text-slate-400">
            {selectedList.length} món
            {selectedList.length > 0 ? ` · ${viNum(slotCals)} kcal` : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {showApplyToAll && onApplyToAll && (
            <button
              type="button"
              onClick={onApplyToAll}
              disabled={selectedList.length === 0 && !note.trim()}
              title="Áp dụng bữa này cho tất cả các ngày"
              className="rounded-xl border border-brand-200 bg-brand-50 px-3 py-2 text-xs font-semibold text-brand-700 transition hover:bg-brand-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Áp dụng mọi ngày
            </button>
          )}
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-xl bg-brand-500 px-3.5 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-600"
          >
            {selectedList.length > 0 ? "Chọn thêm món" : "+ Chọn món"}
          </button>
        </div>
      </div>

      {selectedList.length > 0 && (
        <ul className="mt-3 space-y-2">
          {selectedList.map(({ food, qty }) => (
            <li key={food.id} className="rounded-xl bg-slate-50 p-2.5 text-sm">
              <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-medium leading-snug">{food.name_vi}</p>
                  {isPer100(food) && (
                    <p className="mt-0.5 text-[11px] text-slate-400">×{qty} khẩu phần 100g</p>
                  )}
                  {!isPer100(food) && qty > 1 && (
                    <p className="mt-0.5 text-[11px] text-slate-400">×{qty} phần</p>
                  )}
                </div>
                <span className="shrink-0 text-xs font-semibold text-slate-600">
                  {viNum(food.calories * qty)} kcal
                </span>
                <div className="flex shrink-0 items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => decrementOrRemove(food)}
                    className="grid h-7 w-7 place-items-center rounded-lg bg-white text-sm font-bold text-slate-600 ring-1 ring-slate-200 transition hover:bg-slate-100"
                    aria-label="Giảm số lượng"
                  >
                    −
                  </button>
                  <span className="w-5 text-center text-sm font-bold">{qty}</span>
                  <button
                    type="button"
                    onClick={() => increment(food)}
                    className="grid h-7 w-7 place-items-center rounded-lg bg-brand-500 text-sm font-bold text-white transition hover:bg-brand-600"
                    aria-label="Tăng số lượng"
                  >
                    +
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(food)}
                    className="ml-0.5 grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
                    aria-label="Xoá món"
                  >
                    🗑
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <NoteField value={note} onChange={onNoteChange} placeholder="Lưu ý cho bữa này…" />

      <FoodMealModal
        open={open}
        title={title}
        entries={entries}
        onIncrement={increment}
        onDecrement={decrementOrRemove}
        onToggle={toggle}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}

function FoodMealModal({
  open,
  title,
  entries,
  onIncrement,
  onDecrement,
  onToggle,
  onClose,
  initialDiet = "",
}: {
  open: boolean;
  title: string;
  entries: Record<number, FoodEntry>;
  onIncrement: (food: Food) => void;
  onDecrement: (food: Food) => void;
  onToggle: (food: Food) => void;
  onClose: () => void;
  initialDiet?: string;
}) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<number | "">("");
  const [diet, setDiet] = useState(initialDiet);
  const [mineOnly, setMineOnly] = useState(false);
  const [items, setItems] = useState<Food[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [cats, setCats] = useState<FoodCategory[]>([]);
  const [catMap, setCatMap] = useState<Record<number, string>>({});
  const [ready, setReady] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [customForm, setCustomForm] = useState({
    name_vi: "",
    serving_size: "1 phần",
    calories: "100",
    protein_g: "10",
    carbs_g: "10",
    fat_g: "5",
  });
  const [customSaving, setCustomSaving] = useState(false);
  const [customErr, setCustomErr] = useState("");
  const skipSearchRef = useRef(true);
  const loggedIn = isAuthenticated();

  useEffect(() => {
    if (!open) return;
    api
      .foodCategories()
      .then((d) => {
        const sorted = [...d.items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        setCats(sorted);
        setCatMap(Object.fromEntries(sorted.map((c) => [c.id, c.name_vi])));
      })
      .catch(() => {});
  }, [open]);

  const load = useCallback(
    async (
      nextPage: number,
      append: boolean,
      query: string,
      cat: number | "",
      dietKey: string,
      mine: boolean,
    ) => {
      setLoading(true);
      try {
        const data = await searchFoodsAuth({
          q: query || undefined,
          category_id: cat === "" ? undefined : cat,
          diet: dietKey || undefined,
          mine_only: mine || undefined,
          page: nextPage,
          page_size: PAGE_SIZE,
        });
        setTotal(data.total);
        setPages(data.pages);
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!open) {
      setReady(false);
      setItems([]);
      return;
    }
    skipSearchRef.current = true;
    setQ("");
    setCategory("");
    setDiet(initialDiet || "");
    setMineOnly(false);
    setPage(1);
    setReady(true);
    void load(1, false, "", "", initialDiet || "", false);
  }, [open, load, initialDiet]);

  useEffect(() => {
    if (!open || !ready) return;
    if (skipSearchRef.current) {
      skipSearchRef.current = false;
      return;
    }
    const t = setTimeout(() => {
      setPage(1);
      void load(1, false, q, category, diet, mineOnly);
    }, 300);
    return () => clearTimeout(t);
  }, [q, category, diet, mineOnly, open, ready, load]);

  async function saveCustomFood() {
    if (!loggedIn) {
      setCustomErr("Đăng nhập để thêm món riêng.");
      return;
    }
    setCustomSaving(true);
    setCustomErr("");
    try {
      const food = await customFoodsApi.create({
        name_vi: customForm.name_vi,
        serving_size: customForm.serving_size,
        calories: Number(customForm.calories) || 0,
        protein_g: Number(customForm.protein_g) || 0,
        carbs_g: Number(customForm.carbs_g) || 0,
        fat_g: Number(customForm.fat_g) || 0,
      });
      onToggle(food);
      setShowCustom(false);
      void load(1, false, q, category, diet, mineOnly);
    } catch (ex) {
      setCustomErr((ex as Error).message);
    } finally {
      setCustomSaving(false);
    }
  }

  const selectedCount = Object.keys(entries).length;

  return (
    <Modal open={open} onClose={onClose} size="wide" lockScroll>
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 800px)" }}>
        <div className="shrink-0 border-b border-slate-100 bg-white px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-base font-bold sm:text-lg">{title}</h3>
              <p className="mt-1 text-xs text-slate-400">
                Đã chọn <b className="text-brand-600">{selectedCount}</b> món cho buổi này
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xl leading-none text-slate-600 hover:bg-slate-200"
              aria-label="Đóng"
            >
              ×
            </button>
          </div>
          <div className="relative mt-3">
            <svg
              className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-slate-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-3.5-3.5" />
            </svg>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              type="search"
              placeholder="Tìm món ăn… (vd: ức gà, cơm, chuối)"
              className="field pl-10"
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {DIET_OPTS.map((d) => (
              <button
                key={d.key || "all-diet"}
                type="button"
                className={`chip ${diet === d.key ? "chip-active" : ""}`}
                onClick={() => setDiet(d.key)}
              >
                {d.label}
              </button>
            ))}
            {loggedIn && (
              <button
                type="button"
                className={`chip ${mineOnly ? "chip-active" : ""}`}
                onClick={() => setMineOnly((v) => !v)}
              >
                Món của tôi
              </button>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              className={`chip ${category === "" ? "chip-active" : ""}`}
              onClick={() => setCategory("")}
            >
              Tất cả danh mục
            </button>
            {cats
              .filter((c) => !isHiddenFoodCategorySlug(c.slug))
              .map((c) => (
              <button
                key={c.id}
                type="button"
                className={`chip ${category === c.id ? "chip-active" : ""}`}
                onClick={() => setCategory(c.id)}
              >
                {c.name_vi}
              </button>
            ))}
          </div>
          {loggedIn && (
            <button
              type="button"
              onClick={() => setShowCustom((v) => !v)}
              className="mt-3 text-xs font-bold text-brand-700 hover:underline"
            >
              {showCustom ? "Ẩn form món riêng" : "+ Thêm món riêng"}
            </button>
          )}
          {showCustom && (
            <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3">
              <input
                className="field"
                placeholder="Tên món"
                value={customForm.name_vi}
                onChange={(e) => setCustomForm((f) => ({ ...f, name_vi: e.target.value }))}
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <input
                  className="field"
                  placeholder="kcal"
                  value={customForm.calories}
                  onChange={(e) => setCustomForm((f) => ({ ...f, calories: e.target.value }))}
                />
                <input
                  className="field"
                  placeholder="P (g)"
                  value={customForm.protein_g}
                  onChange={(e) => setCustomForm((f) => ({ ...f, protein_g: e.target.value }))}
                />
                <input
                  className="field"
                  placeholder="C (g)"
                  value={customForm.carbs_g}
                  onChange={(e) => setCustomForm((f) => ({ ...f, carbs_g: e.target.value }))}
                />
                <input
                  className="field"
                  placeholder="F (g)"
                  value={customForm.fat_g}
                  onChange={(e) => setCustomForm((f) => ({ ...f, fat_g: e.target.value }))}
                />
              </div>
              {customErr && <p className="text-xs text-rose-600">{customErr}</p>}
              <button
                type="button"
                disabled={customSaving || !customForm.name_vi.trim()}
                onClick={() => void saveCustomFood()}
                className="rounded-lg bg-brand-500 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
              >
                {customSaving ? "Đang lưu…" : "Lưu & chọn món"}
              </button>
            </div>
          )}
          {total > 0 && (
            <p className="mt-2 text-xs text-slate-400">{total.toLocaleString("vi-VN")} món ăn</p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {items.map((f) => {
              const per100 = isPer100(f);
              const qty = entries[f.id]?.qty ?? 0;
              return (
                <div
                  key={f.id}
                  className={`rounded-xl p-3 ring-1 transition ${
                    qty > 0 ? "bg-brand-50 ring-brand-300" : "bg-white ring-slate-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="clamp-2 text-sm leading-snug font-bold">{foodDisplayName(f.name_vi)}</p>
                      {f.name_en && <p className="clamp-2 text-xs text-slate-400">{f.name_en}</p>}
                      <p className="mt-0.5 text-xs text-slate-400">🍚 {f.serving_size}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-lg font-bold text-brand-600">{viNum(f.calories)}</p>
                      <p className="text-[11px] text-slate-400">kcal{per100 ? "/100g" : ""}</p>
                    </div>
                  </div>
                  <div className="mt-2">
                    <MacroBar protein_g={f.protein_g} carbs_g={f.carbs_g} fat_g={f.fat_g} />
                  </div>
                  <div className="mt-1.5 flex justify-between text-[11px] font-medium">
                    <span className="text-brand-600">Đạm {viNum(f.protein_g)}g</span>
                    <span className="text-amber-600">Tinh bột {viNum(f.carbs_g)}g</span>
                    <span className="text-rose-500">Béo {viNum(f.fat_g)}g</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {f.category_id && catMap[f.category_id] && (
                      <span className="badge badge-gray">{catMap[f.category_id]}</span>
                    )}
                    {f.is_common && <span className="badge badge-new">Phổ biến</span>}
                  </div>
                  <div className="mt-2.5">
                    {per100 ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onDecrement(f)}
                          disabled={qty === 0}
                          className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 font-bold disabled:opacity-40"
                        >
                          −
                        </button>
                        <span className="w-5 text-center text-sm font-bold">{qty}</span>
                        <button
                          type="button"
                          onClick={() => onIncrement(f)}
                          className="grid h-7 w-7 place-items-center rounded-lg bg-brand-500 font-bold text-white"
                        >
                          +
                        </button>
                        {qty > 0 && (
                          <button
                            type="button"
                            onClick={() => onToggle(f)}
                            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
                            aria-label="Xoá món"
                          >
                            🗑
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onToggle(f)}
                          className={`min-w-0 flex-1 rounded-lg py-1.5 text-xs font-bold ${
                            qty > 0 ? "bg-brand-100 text-brand-700" : "bg-brand-500 text-white"
                          }`}
                        >
                          {qty > 0 ? "✓ Đã chọn" : "+ Thêm"}
                        </button>
                        {qty > 0 && (
                          <button
                            type="button"
                            onClick={() => onToggle(f)}
                            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
                            aria-label="Xoá món"
                          >
                            🗑
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {loading && <p className="py-4 text-center text-sm text-slate-400">Đang tải…</p>}
          {!loading && ready && items.length === 0 && (
            <p className="py-6 text-center text-sm text-slate-400">Không tìm thấy món ăn phù hợp.</p>
          )}
          {!loading && page < pages && (
            <div className="mt-3 text-center">
              <button
                type="button"
                onClick={() => {
                  const n = page + 1;
                  setPage(n);
                  void load(n, true, q, category, diet, mineOnly);
                }}
                className="rounded-xl border border-slate-200 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600"
              >
                Xem thêm
              </button>
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-slate-100 bg-white p-4">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white shadow-soft transition hover:bg-brand-600"
          >
            Xong ({selectedCount} món)
          </button>
        </div>
      </div>
    </Modal>
  );
}

/* ---------------- Step 3 — Bài tập ---------------- */
function Step3Exercises({
  sessionsPerWeek,
  schedule,
  setSchedule,
  notesByDay,
  setNotesByDay,
  notify,
  onBack,
  onNext,
}: {
  sessionsPerWeek: number;
  schedule: Schedule;
  setSchedule: React.Dispatch<React.SetStateAction<Schedule>>;
  notesByDay: NotesByDay;
  setNotesByDay: React.Dispatch<React.SetStateAction<NotesByDay>>;
  notify: (msg: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [activeDay, setActiveDay] = useState(0);
  const [picker, setPicker] = useState<SectionKey | null>(null);
  const [bodyMap, setBodyMap] = useState<Record<string, string>>({});

  useEffect(() => {
    api.bodyPartLabels()
      .then((d) => setBodyMap(Object.fromEntries(d.items.map((x) => [x.key, x.label_vi]))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeDay > sessionsPerWeek - 1) setActiveDay(0);
  }, [sessionsPerWeek, activeDay]);

  const days = Array.from({ length: sessionsPerWeek }, (_, i) => i);
  const day = schedule[activeDay] ?? emptyDay();
  const usedMin = dayMinutes(day);
  const dayNotes = getDayNotes(notesByDay, activeDay);

  const activeSections = ALL_SECTIONS;

  function setSectionNote(section: SectionKey, value: string) {
    setNotesByDay((prev) => {
      const cur = getDayNotes(prev, activeDay);
      return {
        ...prev,
        [activeDay]: { ...cur, sections: { ...cur.sections, [section]: value } },
      };
    });
  }

  function applyDayUpdate(nextDay: DaySchedule) {
    setSchedule((prev) => ({ ...prev, [activeDay]: nextDay }));
  }

  function addExercise(section: SectionKey, ex: ExerciseListItem): boolean {
    const meta = SECTION_MAP[section];
    const current = schedule[activeDay] ?? emptyDay();
    if (current[section].some((it) => it.ex.id === ex.id)) {
      notify("Bài tập này đã có trong mục rồi.");
      return false;
    }
    const nextDay: DaySchedule = {
      ...current,
      [section]: [
        ...current[section],
        {
          ex,
          sets: meta.defaultSets,
          reps: section === "cardio" ? null : meta.defaultReps,
          durationSec: section === "cardio" ? DEFAULT_CARDIO_MIN * 60 : null,
          restMin: meta.defaultRestMin,
        },
      ],
    };
    setSchedule((prev) => ({ ...prev, [activeDay]: nextDay }));
    return true;
  }

  function changeSets(section: SectionKey, idx: number, delta: number) {
    const current = schedule[activeDay] ?? emptyDay();
    const item = current[section][idx];
    if (!item) return;
    const newSets = Math.min(15, Math.max(1, item.sets + delta));
    if (newSets === item.sets) return;
    const nextDay: DaySchedule = {
      ...current,
      [section]: current[section].map((it, i) => (i === idx ? { ...it, sets: newSets } : it)),
    };
    applyDayUpdate(nextDay);
  }

  function changeReps(section: SectionKey, idx: number, delta: number) {
    const current = schedule[activeDay] ?? emptyDay();
    const item = current[section][idx];
    if (!item) return;
    // Switch from seconds → reps
    if (item.durationSec != null) {
      const meta = SECTION_MAP[section];
      const nextDay: DaySchedule = {
        ...current,
        [section]: current[section].map((it, i) =>
          i === idx ? { ...it, reps: meta.defaultReps, durationSec: null } : it,
        ),
      };
      applyDayUpdate(nextDay);
      return;
    }
    const cur = item.reps ?? SECTION_MAP[section].defaultReps;
    const newReps = Math.min(50, Math.max(1, cur + delta));
    if (newReps === item.reps) return;
    const nextDay: DaySchedule = {
      ...current,
      [section]: current[section].map((it, i) =>
        i === idx ? { ...it, reps: newReps, durationSec: null } : it,
      ),
    };
    setSchedule((prev) => ({ ...prev, [activeDay]: nextDay }));
  }

  function changeDuration(section: SectionKey, idx: number, delta: number) {
    if (section === "cardio") return;
    const current = schedule[activeDay] ?? emptyDay();
    const item = current[section][idx];
    if (!item) return;
    // Switch from reps → seconds
    if (item.durationSec == null) {
      const nextDay: DaySchedule = {
        ...current,
        [section]: current[section].map((it, i) =>
          i === idx ? { ...it, durationSec: 30, reps: null } : it,
        ),
      };
      applyDayUpdate(nextDay);
      return;
    }
    if (delta === 0) return;
    const step = 5;
    const newSec = Math.min(300, Math.max(5, item.durationSec + (delta > 0 ? step : -step)));
    if (newSec === item.durationSec) return;
    const nextDay: DaySchedule = {
      ...current,
      [section]: current[section].map((it, i) =>
        i === idx ? { ...it, durationSec: newSec, reps: null } : it,
      ),
    };
    applyDayUpdate(nextDay);
  }

  function changeCardioMinutes(idx: number, delta: number) {
    const current = schedule[activeDay] ?? emptyDay();
    const item = current.cardio[idx];
    if (!item) return;
    const cur = item.durationSec != null && item.durationSec > 0
      ? Math.round(item.durationSec / 60)
      : DEFAULT_CARDIO_MIN;
    const newMin = Math.min(90, Math.max(1, cur + delta));
    if (newMin === cur) return;
    applyDayUpdate({
      ...current,
      cardio: current.cardio.map((it, i) =>
        i === idx ? { ...it, durationSec: newMin * 60, reps: null } : it,
      ),
    });
  }

  function changeRest(section: SectionKey, idx: number, delta: number) {
    const current = schedule[activeDay] ?? emptyDay();
    const item = current[section][idx];
    if (!item) return;
    const newRest = Math.min(10, Math.max(0, item.restMin + delta));
    if (newRest === item.restMin) return;
    const nextDay: DaySchedule = {
      ...current,
      [section]: current[section].map((it, i) => (i === idx ? { ...it, restMin: newRest } : it)),
    };
    applyDayUpdate(nextDay);
  }

  function removeItem(section: SectionKey, idx: number) {
    const current = schedule[activeDay] ?? emptyDay();
    setSchedule((prev) => ({
      ...prev,
      [activeDay]: {
        ...current,
        [section]: current[section].filter((_, i) => i !== idx),
      },
    }));
  }

  return (
    <div className="space-y-5">
      <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {days.map((d) => {
          const cnt = dayItemCount(schedule[d]);
          const on = d === activeDay;
          return (
            <button
              key={d}
              type="button"
              onClick={() => setActiveDay(d)}
              className={`flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition ${
                on ? "border-brand-500 bg-brand-500 text-white shadow-soft" : "border-slate-200 bg-white text-slate-600 hover:border-brand-300"
              }`}
            >
              Ngày {d + 1}
              {cnt > 0 && (
                <span className={`grid h-5 min-w-5 place-items-center rounded-full px-1 text-[11px] font-bold ${on ? "bg-white/25" : "bg-brand-50 text-brand-600"}`}>
                  {cnt}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="sticky top-16 z-[5] rounded-2xl bg-white p-4 shadow-soft">
        <div className="flex items-end justify-between">
          <p className="text-sm font-semibold text-slate-600">Thời lượng Ngày {activeDay + 1}</p>
          <p className="text-lg font-bold text-brand-600">~{usedMin}′</p>
        </div>
        <p className="mt-1.5 text-xs text-slate-400">
          Chỉ để tham khảo — bài chính ước tính ~1′/set hoặc theo giây; cardio tính theo phút.
        </p>
      </div>

      {activeSections.map((sec) => (
        <div key={sec.key} className="rounded-2xl bg-white p-4 shadow-soft">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 font-bold">
                <span className="text-lg">{sec.icon}</span> {sec.label}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">{day[sec.key].length}</span>
              </h3>
              <p className="mt-0.5 text-xs text-slate-400">{sec.desc}</p>
            </div>
            <button
              type="button"
              onClick={() => setPicker(sec.key)}
              className="shrink-0 rounded-xl bg-brand-500 px-3.5 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-600"
            >
              + Thêm bài
            </button>
          </div>

          {day[sec.key].length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 py-5 text-center text-sm text-slate-400">
              {sec.key === "cardio"
                ? "Không có — bỏ trống nếu buổi này không tập cardio."
                : "Chưa có bài tập. Nhấn “+ Thêm bài” để chọn."}
            </p>
          ) : (
            <ul className="space-y-2.5">
              {day[sec.key].map((it, idx) => {
                const repsMode = it.durationSec == null;
                return (
                  <li key={it.ex.id} className="rounded-xl bg-slate-50 p-2.5">
                    <div className="flex items-center gap-3">
                      <ExerciseThumb gif={it.ex.gif_url} bodyPart={it.ex.body_part} className="h-11 w-11 shrink-0 rounded-lg" emojiSize="text-xl" />
                      <div className="min-w-0 flex-1">
                        <p className="clamp-2 text-sm font-bold leading-snug">{it.ex.name_vi}</p>
                        <p className="mt-0.5 text-[11px] text-slate-400">
                          {bodyMap[it.ex.body_part] || it.ex.body_part} · ~{itemMinutes(it)}′
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeItem(sec.key, idx)}
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
                        aria-label="Xoá bài tập"
                      >
                        🗑
                      </button>
                    </div>
                    <div className="mt-2.5 grid grid-cols-3 gap-2">
                      {sec.key === "cardio" ? (
                        <>
                          <Stepper2
                            label="Hiệp"
                            value={it.sets}
                            onDec={() => changeSets(sec.key, idx, -1)}
                            onInc={() => changeSets(sec.key, idx, 1)}
                            max={15}
                          />
                          <Stepper2
                            label="Phút"
                            value={
                              it.durationSec != null && it.durationSec > 0
                                ? Math.round(it.durationSec / 60)
                                : DEFAULT_CARDIO_MIN
                            }
                            onDec={() => changeCardioMinutes(idx, -1)}
                            onInc={() => changeCardioMinutes(idx, 1)}
                            min={1}
                            max={90}
                          />
                          <Stepper2
                            label="Nghỉ (phút)"
                            value={it.restMin}
                            onDec={() => changeRest(sec.key, idx, -1)}
                            onInc={() => changeRest(sec.key, idx, 1)}
                            max={10}
                            min={0}
                          />
                        </>
                      ) : (
                        <>
                          <Stepper2
                            label="Hiệp(Set)"
                            value={it.sets}
                            onDec={() => changeSets(sec.key, idx, -1)}
                            onInc={() => changeSets(sec.key, idx, 1)}
                            max={15}
                          />
                          <div className="space-y-1.5">
                            <Stepper2
                              label="Lần(Rep)"
                              value={it.reps ?? SECTION_MAP[sec.key].defaultReps}
                              inactive={!repsMode}
                              onActivate={() => changeReps(sec.key, idx, 0)}
                              onDec={() => changeReps(sec.key, idx, -1)}
                              onInc={() => changeReps(sec.key, idx, 1)}
                              max={50}
                            />
                            <Stepper2
                              label="Giây"
                              value={it.durationSec ?? 30}
                              inactive={repsMode}
                              onActivate={() => changeDuration(sec.key, idx, 0)}
                              onDec={() => changeDuration(sec.key, idx, -1)}
                              onInc={() => changeDuration(sec.key, idx, 1)}
                              min={5}
                              max={300}
                            />
                          </div>
                          <Stepper2
                            label="Nghỉ (phút)"
                            value={it.restMin}
                            onDec={() => changeRest(sec.key, idx, -1)}
                            onInc={() => changeRest(sec.key, idx, 1)}
                            max={10}
                            min={0}
                          />
                        </>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          <NoteField
            value={dayNotes.sections[sec.key] ?? ""}
            onChange={(v) => setSectionNote(sec.key, v)}
            placeholder={`Lưu ý cho phần ${sec.label.toLowerCase()}…`}
          />
        </div>
      ))}

      <NavButtons onBack={onBack} onNext={onNext} nextLabel="Tạo lịch tập" nextDisabled={totalItems(schedule) === 0} />

      <ExercisePicker
        open={picker !== null}
        section={picker}
        bodyMap={bodyMap}
        onAdd={(ex) => (picker ? addExercise(picker, ex) : false)}
        alreadyIds={picker ? new Set(day[picker].map((it) => it.ex.id)) : new Set()}
        onClose={() => setPicker(null)}
      />
    </div>
  );
}

/* ---------------- Exercise picker modal ---------------- */
function ExercisePicker({
  open,
  section,
  bodyMap,
  onAdd,
  alreadyIds,
  onClose,
}: {
  open: boolean;
  section: SectionKey | null;
  bodyMap: Record<string, string>;
  onAdd: (ex: ExerciseListItem) => boolean;
  alreadyIds: Set<number>;
  onClose: () => void;
}) {
  const [items, setItems] = useState<ExerciseListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadErr, setLoadErr] = useState("");
  const [q, setQ] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [added, setAdded] = useState<Set<number>>(new Set());
  const [ready, setReady] = useState(false);
  const skipSearchRef = useRef(true);

  const meta = section ? SECTION_MAP[section] : null;

  const load = useCallback(
    async (nextPage: number, append: boolean, query: string, part: string) => {
      if (!section) return;
      setLoading(true);
      setLoadErr("");
      try {
        const data = await api.searchExercises({
          q: query || undefined,
          body_part: part || undefined,
          exercise_type: section,
          page: nextPage,
          page_size: 12,
        });
        setPages(data.pages || 1);
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
      } catch (e) {
        setLoadErr((e as Error).message || "Không tải được bài tập");
        if (!append) setItems([]);
      } finally {
        setLoading(false);
      }
    },
    [section],
  );

  useEffect(() => {
    if (!open || !section) {
      setReady(false);
      setItems([]);
      return;
    }
    let cancelled = false;
    skipSearchRef.current = true;
    setAdded(new Set());
    setQ("");
    setBodyPart("");
    setPage(1);
    setItems([]);
    setReady(true);
    setLoading(true);
    setLoadErr("");
    void (async () => {
      try {
        const data = await api.searchExercises({
          exercise_type: section,
          page: 1,
          page_size: 12,
        });
        if (cancelled) return;
        setPages(data.pages || 1);
        setItems(data.items);
      } catch (e) {
        if (cancelled) return;
        setLoadErr((e as Error).message || "Không tải được bài tập");
        setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, section]);

  useEffect(() => {
    if (!open || !ready) return;
    if (skipSearchRef.current) {
      skipSearchRef.current = false;
      return;
    }
    const t = setTimeout(() => {
      setPage(1);
      void load(1, false, q, bodyPart);
    }, 300);
    return () => clearTimeout(t);
  }, [q, bodyPart, open, ready, load]);

  function handleAdd(ex: ExerciseListItem) {
    if (onAdd(ex)) setAdded((s) => new Set(s).add(ex.id));
  }

  return (
    <Modal open={open} onClose={onClose} size="wide" lockScroll>
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 760px)" }}>
        <div className="shrink-0 border-b border-slate-100 bg-white px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-base font-bold sm:text-lg">
                {meta ? `${meta.icon} Thêm bài — ${meta.label}` : "Thêm bài tập"}
              </h3>
              <p className="mt-1 text-xs text-slate-400">
                Chỉ hiện bài {meta?.label?.toLowerCase() ?? "phù hợp"}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xl leading-none text-slate-600 hover:bg-slate-200"
              aria-label="Đóng"
            >
              ×
            </button>
          </div>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input value={q} onChange={(e) => setQ(e.target.value)} type="search" placeholder="Tìm bài tập…" className="field flex-1" />
            <select value={bodyPart} onChange={(e) => setBodyPart(e.target.value)} className="field w-full shrink-0 text-sm sm:w-44">
              <option value="">Mọi nhóm cơ</option>
              {Object.entries(bodyMap).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {items.map((ex) => {
              const cost = meta ? exerciseMinutesByRest(meta.defaultSets, meta.defaultRestMin) : 0;
              const isAdded = added.has(ex.id) || alreadyIds.has(ex.id);
              const diff = difficultyLabel(ex.difficulty);
              return (
                <div key={ex.id} className={`flex items-start gap-3 rounded-xl p-3 ring-1 transition ${isAdded ? "bg-brand-50 ring-brand-300" : "bg-white ring-slate-200"}`}>
                  <ExerciseThumb gif={ex.gif_url} bodyPart={ex.body_part} className="h-14 w-14 shrink-0 rounded-lg" emojiSize="text-2xl" />
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <p className="line-clamp-2 text-sm font-bold leading-snug text-slate-800">{ex.name_vi}</p>
                    <div className="flex flex-wrap gap-1">
                      <span className="badge badge-gray">{bodyMap[ex.body_part] || ex.body_part}</span>
                      <span className={`badge ${diff.cls}`}>{diff.vi}</span>
                      <span className="badge badge-gray">~{cost}′ · {meta?.defaultSets} set</span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleAdd(ex);
                      }}
                      disabled={isAdded}
                      className={`mt-0.5 w-full rounded-lg py-2 text-xs font-bold transition sm:w-auto sm:self-start sm:px-4 ${
                        isAdded ? "bg-brand-100 text-brand-700" : "bg-brand-500 text-white hover:bg-brand-600"
                      }`}
                    >
                      {isAdded ? "✓ Đã thêm" : "+ Thêm"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          {(!ready || loading) && <p className="py-4 text-center text-sm text-slate-400">Đang tải…</p>}
          {loadErr && <p className="py-4 text-center text-sm text-rose-500">{loadErr}</p>}
          {ready && !loading && !loadErr && items.length === 0 && (
            <p className="py-6 text-center text-sm text-slate-400">Không tìm thấy bài tập phù hợp.</p>
          )}
          {ready && !loading && page < pages && (
            <div className="mt-3 text-center">
              <button
                type="button"
                onClick={() => {
                  const n = page + 1;
                  setPage(n);
                  void load(n, true, q, bodyPart);
                }}
                className="rounded-xl border border-slate-200 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600"
              >
                Xem thêm
              </button>
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-slate-100 bg-white p-4">
          <button type="button" onClick={onClose} className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white shadow-soft transition hover:bg-brand-600">
            Xong ({new Set([...alreadyIds, ...added]).size} bài trong mục)
          </button>
        </div>
      </div>
    </Modal>
  );
}

/* ---------------- Step 4 — Hoàn tất ---------------- */
function Step4Review({
  nutrition,
  weightGoal,
  sessionsPerWeek,
  durationWeeks,
  experienceLevel,
  schedule,
  mealsByDay,
  notesByDay,
  creating,
  setCreating,
  router,
  notify,
  onBack,
  onRestart,
}: {
  nutrition: NutritionResult;
  weightGoal: WeightGoal;
  sessionsPerWeek: number;
  durationWeeks: number;
  experienceLevel: number;
  schedule: Schedule;
  mealsByDay: MealsByDay;
  notesByDay: NotesByDay;
  creating: boolean;
  setCreating: (v: boolean) => void;
  router: ReturnType<typeof useRouter>;
  notify: (msg: string) => void;
  onBack: () => void;
  onRestart: () => void;
}) {
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);
  const goalLabel = formatGoalsLabel(weightGoal, []);
  const allDays = Array.from({ length: sessionsPerWeek }, (_, i) => i);
  const days = allDays.filter(
    (d) => dayItemCount(schedule[d]) > 0 || mealsTotalCalories(getDayMeals(mealsByDay, d)) > 0,
  );
  const activeSections = ALL_SECTIONS;
  const totalFoodCalories = allDays.reduce(
    (sum, d) => sum + mealsTotalCalories(getDayMeals(mealsByDay, d)),
    0,
  );
  const avgMinutes = (() => {
    const withItems = allDays.filter((d) => dayItemCount(schedule[d]) > 0);
    if (withItems.length === 0) return 0;
    const total = withItems.reduce((sum, d) => sum + dayMinutes(schedule[d]), 0);
    return Math.round(total / withItems.length);
  })();

  function buildPayload(): CreatePlanPayload {
    const planDays = allDays.map((i) => {
      const day = schedule[i] ?? emptyDay();
      const notes = getDayNotes(notesByDay, i);
      const exercises = SECTION_KEYS.flatMap((sec) =>
        day[sec].map((it) => ({
          exercise_id: it.ex.id,
          sets: it.sets,
          reps: toPayloadReps(it),
          section: sec,
          rest_seconds: it.restMin * 60,
        })),
      );
      return {
        day_number: i + 1,
        title_vi: `Ngày ${i + 1}`,
        exercises,
        meals: buildMealsPayload(getDayMeals(mealsByDay, i)),
        meal_notes: buildMealNotesPayload(notes.meals),
        section_notes: buildSectionNotesPayload(notes.sections),
      };
    });

    const minutesTxt = avgMinutes > 0 ? ` · ~${avgMinutes} phút/buổi` : "";
    return {
      title_vi: `Lịch tự tạo — ${goalLabel}`,
      description_vi: `${sessionsPerWeek} buổi/tuần · ${durationWeeks} tuần${minutesTxt}`,
      target_calories: nutrition.target,
      target_protein_g: nutrition.protein_g,
      target_carbs_g: nutrition.carbs_g,
      target_fat_g: nutrition.fat_g,
      source: "manual",
      duration_weeks: durationWeeks,
      experience_level: experienceLevel,
      days: planDays,
    };
  }

  async function createPlan() {
    if (creating || !termsAccepted(ageOk, termsOk)) return;
    setCreating(true);
    try {
      const loggedIn = isAuthenticated();
      const payload = buildPayload();
      const created = await plansApi.createPublic(payload);

      if (created.share_token && !loggedIn) {
        addGuestPlanToken(created.share_token);
      }

      try {
        const key = "taptot_plans";
        const existing = JSON.parse(localStorage.getItem(key) || "[]") as unknown[];
        existing.push({
          createdAt: new Date().toISOString(),
          share_token: created.share_token,
          ...payload,
        });
        localStorage.setItem(key, JSON.stringify(existing));
      } catch {
        /* localStorage may be blocked */
      }

      if (created.share_token) {
        router.push(`/lich/${created.share_token}`);
      } else {
        notify("Đã tạo lịch tập! 🎉");
      }
    } catch (ex) {
      notify((ex as Error).message || "Không thể tạo lịch tập.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl bg-gradient-to-br from-brand-500 to-emerald-600 p-6 text-white shadow-soft">
        <p className="text-sm opacity-80">Lịch tập của bạn — {goalLabel}</p>
        <p className="mt-1 text-3xl font-bold">{nutrition.target.toLocaleString("vi-VN")} kcal/ngày</p>
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl bg-white/15 py-2">
            <p className="text-lg font-bold">{sessionsPerWeek}</p>
            <p className="text-[11px] opacity-80">buổi/tuần</p>
          </div>
          <div className="rounded-xl bg-white/15 py-2">
            <p className="text-lg font-bold">{avgMinutes > 0 ? `~${avgMinutes}′` : "—"}</p>
            <p className="text-[11px] opacity-80">mỗi buổi</p>
          </div>
          <div className="rounded-xl bg-white/15 py-2">
            <p className="text-lg font-bold">{durationWeeks}</p>
            <p className="text-[11px] opacity-80">tuần</p>
          </div>
        </div>
      </div>

      {days.length ? (
        days.map((d) => {
          const day = schedule[d] ?? emptyDay();
          const dayMeals = getDayMeals(mealsByDay, d);
          const notes = getDayNotes(notesByDay, d);
          const flatMeals = flattenMeals(dayMeals);
          const dayCalories = mealsTotalCalories(dayMeals);
          return (
            <div key={d} className="rounded-2xl bg-white p-5 shadow-soft">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-bold">📅 Ngày {d + 1}</h3>
                <span className="text-sm font-semibold text-brand-600">~{dayMinutes(day)}′</span>
              </div>
              <div className="space-y-4">
                {activeSections.map((sec) => (
                  <div key={sec.key}>
                    <p className="mb-1.5 text-sm font-bold text-slate-500">{sec.icon} {SECTION_LABEL[sec.key] || sec.label}</p>
                    {day[sec.key].length ? (
                      <ul className="space-y-1.5">
                        {day[sec.key].map((it) => (
                          <li key={it.ex.id} className="flex items-center gap-3 rounded-xl bg-slate-50 p-2.5">
                            <ExerciseThumb gif={it.ex.gif_url} bodyPart={it.ex.body_part} className="h-10 w-10 shrink-0 rounded-lg" emojiSize="text-xl" />
                            <span className="min-w-0 flex-1 truncate text-sm font-medium">{it.ex.name_vi}</span>
                            <span className="shrink-0 rounded-lg bg-white px-2 py-1 text-xs font-bold text-brand-600 ring-1 ring-brand-100">
                              {it.sets} × {formatWorkLabel(it)} · nghỉ {it.restMin}′
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="rounded-xl bg-slate-50 p-2.5 text-sm text-slate-400">Không có</p>
                    )}
                    <NoteReadonly note={notes.sections[sec.key]} />
                  </div>
                ))}
              </div>

              <div className="mt-4 border-t border-slate-100 pt-3">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-bold text-slate-500">🍽️ Thực đơn ({flatMeals.length} món)</p>
                  <span className="text-sm">
                    <b className={dayCalories > nutrition.target ? "text-rose-500" : "text-brand-600"}>{viNum(dayCalories)}</b>
                    <span className="text-slate-400"> / {viNum(nutrition.target)} kcal</span>
                  </span>
                </div>
                {MAIN_MEAL_SLOTS.map((slot) => {
                  const items = Object.values(dayMeals[slot.key]);
                  const note = notes.meals[slot.key];
                  if (!items.length && !note?.trim()) return null;
                  return (
                    <div key={slot.key} className="mb-3 last:mb-0">
                      <p className="mb-1 text-xs font-semibold text-slate-400">{slot.icon} {slot.label}</p>
                      {items.length ? (
                        <ul className="space-y-1.5">
                          {items.map(({ food, qty }) => (
                            <li key={food.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-2.5 text-sm">
                              <span className="font-medium">
                                {food.name_vi}
                                {qty > 1 && <span className="text-slate-400"> ×{qty}</span>}
                              </span>
                              <span className="font-semibold text-slate-600">{viNum(food.calories * qty)} kcal</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="rounded-xl bg-slate-50 p-2.5 text-sm text-slate-400">Không có</p>
                      )}
                      <NoteReadonly note={note} />
                    </div>
                  );
                })}
                {dayMeals.snacks.map((bucket, idx) => {
                  const items = Object.values(bucket);
                  const note = notes.meals.snacks[idx] ?? "";
                  if (!items.length && !note.trim()) return null;
                  return (
                    <div key={`snack-${idx}`} className="mb-3 last:mb-0">
                      <p className="mb-1 text-xs font-semibold text-slate-400">🍎 Bữa phụ {idx + 1}</p>
                      {items.length ? (
                        <ul className="space-y-1.5">
                          {items.map(({ food, qty }) => (
                            <li key={food.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-2.5 text-sm">
                              <span className="font-medium">
                                {food.name_vi}
                                {qty > 1 && <span className="text-slate-400"> ×{qty}</span>}
                              </span>
                              <span className="font-semibold text-slate-600">{viNum(food.calories * qty)} kcal</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="rounded-xl bg-slate-50 p-2.5 text-sm text-slate-400">Không có</p>
                      )}
                      <NoteReadonly note={note} />
                    </div>
                  );
                })}
                {!flatMeals.length &&
                  !MAIN_MEAL_SLOTS.some((s) => notes.meals[s.key]?.trim()) &&
                  !notes.meals.snacks.some((n) => n?.trim()) && (
                    <p className="rounded-xl bg-slate-50 p-2.5 text-sm text-slate-400">Không có</p>
                  )}
              </div>
            </div>
          );
        })
      ) : (
        <div className="rounded-2xl bg-white p-5 text-center text-sm text-slate-400 shadow-soft">Chưa sắp bài tập nào.</div>
      )}

      <div className="rounded-2xl bg-white p-4 text-sm shadow-soft">
        <span className="font-semibold text-slate-600">Tổng calo thực đơn cả tuần: </span>
        <b className="text-brand-600">{viNum(totalFoodCalories)} kcal</b>
        <span className="text-slate-400"> · mục tiêu {viNum(nutrition.target)} kcal/ngày</span>
      </div>

      <p className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
        Sau khi tạo lịch, bạn sẽ nhận link xem lại và có thể xuất Excel / PDF / Word từ trang đó.
      </p>

      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
        <p className="text-sm font-bold text-slate-900">Điều khoản sử dụng và miễn trừ trách nhiệm y tế</p>
        <div className="mt-3 max-h-48 overflow-y-auto pr-1">
          <TermsDocument compact />
        </div>
      </div>

      <TermsConsent
        idPrefix="diy-gen"
        ageOk={ageOk}
        termsOk={termsOk}
        onAgeOk={setAgeOk}
        onTermsOk={setTermsOk}
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={createPlan}
          disabled={creating || !termsAccepted(ageOk, termsOk)}
          className="flex-1 rounded-xl bg-brand-500 py-3.5 font-bold text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-60"
        >
          {creating ? "Đang tạo…" : "Nhận lịch"}
        </button>
        <button type="button" onClick={onRestart} className="flex-1 rounded-xl border border-slate-200 bg-white py-3.5 font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600">
          Tạo lịch mới
        </button>
      </div>
      <div className="text-center">
        <button type="button" onClick={onBack} className="text-sm font-semibold text-slate-500 hover:text-brand-600">← Quay lại chỉnh sửa</button>
      </div>
    </div>
  );
}
