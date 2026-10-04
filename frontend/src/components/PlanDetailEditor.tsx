"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { viNum } from "@/lib/labels";
import { defaultRestForSection } from "@/lib/workoutRest";
import type { ExerciseListItem, Food } from "@/lib/types";
import {
  MEAL_GROUP_ORDER,
  PLAN_SECTION_ORDER,
  SECTION_LABEL,
  SOURCE_LABEL,
  plansApi,
  type PlanClientProfile,
  type PlanDetail,
  type PlanMealType,
  type PlanSectionKey,
  type StaffKnowledgeRef,
  type UpdatePlanDayPayload,
} from "@/lib/plansApi";
import { bumpReps, parseReps } from "@/lib/reps";
import { estimatePlanDayMinutes, estimatePlanExerciseMinutes, parseSessionsPerWeek } from "@/lib/planLabels";
import { groupPlanDaysByWeek, weekGroupForDay } from "@/lib/planWeeks";
import ExerciseAlternativesModal from "./ExerciseAlternativesModal";
import PlanExercisePickerModal from "./PlanExercisePickerModal";
import PlanFoodPickerModal from "./PlanFoodPickerModal";
import PlanOverviewEditor from "./PlanOverviewEditor";
import { altContextFromPlanInputs, type SwapExerciseContext } from "@/lib/planSwap";
import PlanViewShell from "./plan-view/PlanViewShell";
import type { PlanViewTab } from "./plan-view/types";
import PlanWeekSessionNav from "./plan-view/PlanWeekSessionNav";
import PlanShareLinkBar from "./PlanShareLinkBar";
import Modal from "./Modal";
import PlanMealAccordion, {
  mealGroupTitle,
} from "./plan-view/PlanMealAccordion";
import { MealThumb } from "./plan-view/PlanMealRow";
import { isValidShareSlug, shareSlugError } from "@/lib/shareSlug";
import { getStoredUser } from "@/lib/auth";
import { accountShellHref } from "@/lib/accountWorkspace";
import {
  formatExerciseCue,
  nextSupersetGroup,
  supersetSlotLabel,
  type ExerciseTechnique,
} from "@/lib/exerciseCues";
import MealGramsInput from "./MealGramsInput";
import {
  catalogServingGrams,
  clampMealGrams,
  gramsFromServings,
  kcalFromGrams,
  kcalPer100gFromFood,
  kcalPer100gFromTotals,
  servingsFromGrams,
} from "@/lib/mealGrams";
import {
  dayNumbersForFlexibleScope,
  FLEX_MEAL_TYPE,
  FLEXIBLE_CALORIE_LABEL,
  FLEXIBLE_SCOPE_LABEL,
  mealsForSlot,
  mealsFromDays,
  type FlexibleMealScope,
} from "@/lib/mealFlexible";
import { brandRichText } from "@/components/brandRichText";
import {
  applyWeekTraining,
  TRAIN_APPLY_SCOPE_LABEL,
  trainApplyScopesForNav,
  trainApplyTargetWeekCount,
  type TrainApplyScope,
} from "@/lib/applyTrainWeek";

const EDITOR_TABS: { id: PlanViewTab; label: string }[] = [
  { id: "overview", label: "Tổng quan" },
  { id: "train", label: "Bài tập" },
  { id: "meals", label: "Ăn uống" },
];

type Section = PlanSectionKey;
type MealType = PlanMealType;

interface DraftSet {
  reps: string;
  rest_seconds: number;
  rir: number | null;
  rpe: number | null;
  tempo: string;
  technique: "drop_set" | null;
}

interface DraftExercise {
  key: string;
  exercise_id: number;
  name_vi: string;
  body_part: string | null;
  section: Section;
  sets: number;
  reps: string;
  rest_seconds: number;
  rir: number | null;
  rpe: number | null;
  tempo: string;
  technique: ExerciseTechnique | null;
  superset_group: number | null;
  set_prescriptions: DraftSet[] | null;
}

interface DraftMeal {
  key: string;
  food_id: number;
  name_vi: string;
  meal_type: MealType;
  grams: number;
  serving_grams: number;
  serving_size: string | null;
  kcal_100g: number;
  image_url: string | null;
}

interface DraftDay {
  day_number: number;
  title_vi: string | null;
  meals_flexible: boolean;
  exercises: DraftExercise[];
  meals: DraftMeal[];
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function cloneDraftExercise(ex: DraftExercise): DraftExercise {
  return {
    ...ex,
    key: uid(),
    set_prescriptions: ex.set_prescriptions
      ? ex.set_prescriptions.map((row) => ({ ...row }))
      : null,
  };
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("vi-VN");
  } catch {
    return iso;
  }
}

function exMinutes(ex: DraftExercise): number {
  return estimatePlanExerciseMinutes(ex);
}

function dayMinutes(day: DraftDay): number {
  return estimatePlanDayMinutes(day.exercises);
}

function mealLineKcal(m: DraftMeal): number {
  return kcalFromGrams(m.kcal_100g, m.grams);
}

function dayCalories(day: DraftDay): number {
  return day.meals.reduce((s, m) => s + mealLineKcal(m), 0);
}

function emptyCue(): Pick<
  DraftExercise,
  "rir" | "rpe" | "tempo" | "technique" | "superset_group" | "set_prescriptions"
> {
  return {
    rir: null,
    rpe: null,
    tempo: "",
    technique: null,
    superset_group: null,
    set_prescriptions: null,
  };
}

function cueToSetRow(ex: DraftExercise): DraftSet {
  return {
    reps: ex.reps,
    rest_seconds: ex.rest_seconds,
    rir: ex.rir,
    rpe: ex.rpe,
    tempo: ex.tempo,
    technique: ex.technique === "drop_set" ? "drop_set" : null,
  };
}

function seedSetRows(ex: DraftExercise, count: number): DraftSet[] {
  const n = Math.max(1, Math.min(20, count));
  const row = cueToSetRow(ex);
  return Array.from({ length: n }, () => ({ ...row }));
}

function applySetCount(ex: DraftExercise, next: number): Partial<DraftExercise> {
  const n = Math.max(1, Math.min(20, next));
  if (!ex.set_prescriptions?.length) return { sets: n };
  const rows = [...ex.set_prescriptions];
  const last = rows[rows.length - 1] ?? cueToSetRow(ex);
  while (rows.length < n) rows.push({ ...last });
  while (rows.length > n) rows.pop();
  const first = rows[0];
  return {
    sets: n,
    set_prescriptions: rows,
    reps: first.reps,
    rest_seconds: first.rest_seconds,
    rir: first.rir,
    rpe: first.rpe,
    tempo: first.tempo,
  };
}

function togglePerSet(ex: DraftExercise, on: boolean): Partial<DraftExercise> {
  if (on) {
    const rows = seedSetRows(ex, ex.sets);
    return {
      set_prescriptions: rows,
      sets: rows.length,
      technique: ex.technique === "super_set" ? "super_set" : null,
    };
  }
  const first = ex.set_prescriptions?.[0];
  if (!first) return { set_prescriptions: null };
  return {
    set_prescriptions: null,
    sets: ex.set_prescriptions!.length,
    reps: first.reps,
    rest_seconds: first.rest_seconds,
    rir: first.rir,
    rpe: first.rpe,
    tempo: first.tempo,
    technique: ex.technique === "super_set" ? "super_set" : first.technique,
  };
}

function patchSetRow(
  ex: DraftExercise,
  index: number,
  patch: Partial<DraftSet>,
): Partial<DraftExercise> {
  const rows = (ex.set_prescriptions || []).map((row, i) => (i === index ? { ...row, ...patch } : row));
  const first = rows[0];
  return {
    set_prescriptions: rows,
    ...(first
      ? {
          reps: first.reps,
          rest_seconds: first.rest_seconds,
          rir: first.rir,
          rpe: first.rpe,
          tempo: first.tempo,
        }
      : {}),
  };
}

function parseOptionalInt(raw: string, lo: number, hi: number): number | null {
  if (raw === "") return null;
  const n = Number(raw);
  if (!Number.isFinite(n)) return null;
  return Math.min(hi, Math.max(lo, n));
}

function unpairGroup(day: DraftDay, group: number | null): DraftDay {
  if (group == null) return day;
  return {
    ...day,
    exercises: day.exercises.map((e) =>
      e.superset_group === group
        ? { ...e, technique: e.technique === "super_set" ? null : e.technique, superset_group: null }
        : e,
    ),
  };
}

function applyTechnique(day: DraftDay, key: string, technique: ExerciseTechnique | null): {
  day: DraftDay;
  danglingSuper: boolean;
} {
  const current = day.exercises.find((e) => e.key === key);
  if (!current) return { day, danglingSuper: false };
  let next = unpairGroup(day, current.superset_group);
  if (technique === "drop_set") {
    next = {
      ...next,
      exercises: next.exercises.map((e) =>
        e.key === key ? { ...e, technique: "drop_set", superset_group: null } : e,
      ),
    };
    return { day: next, danglingSuper: false };
  }
  if (technique !== "super_set") {
    next = {
      ...next,
      exercises: next.exercises.map((e) =>
        e.key === key ? { ...e, technique: null, superset_group: null } : e,
      ),
    };
    return { day: next, danglingSuper: false };
  }
  const sectionItems = next.exercises.filter((e) => e.section === current.section);
  const idx = sectionItems.findIndex((e) => e.key === key);
  const partner = sectionItems[idx + 1];
  const group = nextSupersetGroup(next.exercises);
  next = {
    ...next,
    exercises: next.exercises.map((e) => {
      if (e.key === key) return { ...e, technique: "super_set", superset_group: group };
      if (partner && e.key === partner.key) {
        return { ...e, technique: "super_set", superset_group: group };
      }
      return e;
    }),
  };
  return { day: next, danglingSuper: !partner };
}

function toDraft(detail: PlanDetail): DraftDay[] {
  return detail.days.map((d) => ({
    day_number: d.day_number,
    title_vi: d.title_vi,
    meals_flexible: Boolean(d.meals_flexible),
    exercises: d.exercises.map((ex) => ({
      key: `ex-${ex.id}`,
      exercise_id: ex.exercise_id,
      name_vi: ex.name_vi,
      body_part: ex.body_part,
      section: (ex.section as Section) || "main",
      sets: ex.sets,
      reps: String(ex.reps ?? "12"),
      rest_seconds: ex.rest_seconds || defaultRestForSection(ex.section),
      rir: ex.rir ?? null,
      rpe: ex.rpe ?? null,
      tempo: ex.tempo || "",
      technique: ex.technique === "drop_set" || ex.technique === "super_set" ? ex.technique : null,
      superset_group: ex.superset_group ?? null,
      set_prescriptions:
        Array.isArray(ex.set_prescriptions) && ex.set_prescriptions.length
          ? ex.set_prescriptions.map((row) => ({
              reps: String(row.reps ?? "12"),
              rest_seconds: row.rest_seconds ?? 90,
              rir: row.rir ?? null,
              rpe: row.rpe ?? null,
              tempo: row.tempo || "",
              technique: row.technique === "drop_set" ? "drop_set" : null,
            }))
          : null,
    })),
    meals: d.meals.map((m) => {
      const servingGrams = catalogServingGrams(m.serving_grams);
      const grams = gramsFromServings(m.servings, servingGrams);
      const kcal100 =
        kcalPer100gFromTotals(m.calories, grams) ||
        kcalPer100gFromTotals(m.servings > 0 ? m.calories / m.servings : m.calories, servingGrams);
      return {
        key: `m-${m.id}`,
        food_id: m.food_id,
        name_vi: m.name_vi,
        meal_type: (m.meal_type as MealType) || "lunch",
        grams,
        serving_grams: servingGrams,
        serving_size: m.serving_size || null,
        kcal_100g: kcal100,
        image_url: m.image_url || null,
      };
    }),
  }));
}

function Stepper({
  label,
  value,
  onDec,
  onInc,
  min = 1,
  warn,
}: {
  label: string;
  value: number | string;
  onDec: () => void;
  onInc: () => void;
  min?: number;
  warn?: boolean;
}) {
  const n = typeof value === "number" ? value : Number(value) || min;
  return (
    <div
      className={`flex items-center justify-between rounded-lg px-2 py-1 ring-1 ${
        warn ? "bg-rose-50 ring-rose-200" : "bg-slate-50 ring-slate-200"
      }`}
    >
      <span className="text-[11px] font-semibold text-slate-500">{label}</span>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={onDec}
          disabled={n <= min}
          className="grid h-7 w-7 place-items-center rounded-md bg-white text-sm font-bold text-slate-600 ring-1 ring-slate-200 disabled:opacity-40"
        >
          −
        </button>
        <span className="min-w-[1.75rem] text-center text-sm font-bold">{value}</span>
        <button
          type="button"
          onClick={onInc}
          className="grid h-7 w-7 place-items-center rounded-md bg-brand-500 text-sm font-bold text-white"
        >
          +
        </button>
      </div>
    </div>
  );
}

export default function PlanDetailEditor({
  detail,
  onCancel,
  onSaved,
  variant = "modal",
  initialDayNumber,
  initialWeek,
  initialSwapExerciseId,
}: {
  detail: PlanDetail;
  onCancel: () => void;
  onSaved: (next: PlanDetail) => void;
  variant?: "modal" | "page";
  initialDayNumber?: number;
  initialWeek?: number;
  initialSwapExerciseId?: number;
}) {
  const router = useRouter();
  const plansListHref = accountShellHref(getStoredUser()?.role, "ke-hoach");
  const [draft, setDraft] = useState<DraftDay[]>(() => toDraft(detail));
  const [activeDay, setActiveDay] = useState(() => {
    if (initialDayNumber == null) return 0;
    const i = detail.days.findIndex((d) => d.day_number === initialDayNumber);
    return i >= 0 ? i : 0;
  });
  const [saving, setSaving] = useState(false);
  const [templateSaving, setTemplateSaving] = useState(false);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [templateTitle, setTemplateTitle] = useState(() => `Mẫu — ${detail.title_vi}`);
  const [restoring, setRestoring] = useState(false);
  const [err, setErr] = useState("");
  const [flash, setFlash] = useState("");
  const [showExSearch, setShowExSearch] = useState(false);
  const [showFoodSearch, setShowFoodSearch] = useState(false);
  const [addMealType, setAddMealType] = useState<MealType>("lunch");
  const [addSection, setAddSection] = useState<Section>("main");
  const [flexibleScope, setFlexibleScope] = useState<FlexibleMealScope>("day");
  const [trainApplyScope, setTrainApplyScope] = useState<TrainApplyScope>("month");
  const [swapCtx, setSwapCtx] = useState<{ key: string; exercise: SwapExerciseContext } | null>(
    null,
  );
  const [activeTab, setActiveTab] = useState<PlanViewTab>("train");
  const [titleVi, setTitleVi] = useState(detail.title_vi);
  const [shareSlug, setShareSlug] = useState(detail.share_token || "");
  const [descriptionVi, setDescriptionVi] = useState(detail.description_vi || "");
  const [overviewSummary, setOverviewSummary] = useState(detail.insights?.overview?.summary_vi || "");
  const [client, setClient] = useState<PlanClientProfile>(() => detail.insights?.client || {});
  const [knowledge, setKnowledge] = useState<StaffKnowledgeRef[]>(
    () => detail.insights?.staff_knowledge || [],
  );
  const weekGroups = useMemo(
    () =>
      groupPlanDaysByWeek(
        draft.map((d) => ({
          id: d.day_number,
          day_number: d.day_number,
          title_vi: d.title_vi,
          notes_vi: null,
          exercises: d.exercises.map((e, i) => ({
            id: i,
            exercise_id: e.exercise_id,
            name_vi: e.name_vi,
            name_en: null,
            body_part: e.body_part,
            section: e.section,
            sets: e.sets,
            reps: e.reps,
            rest_seconds: e.rest_seconds,
            sort_order: i,
            notes_vi: null,
          })),
          meals: [],
        })) as PlanDetail["days"],
      ),
    [draft],
  );
  const [activeWeek, setActiveWeek] = useState(() => {
    if (initialWeek != null && weekGroups.some((g) => g.week === initialWeek)) return initialWeek;
    const dayNo = initialDayNumber ?? detail.days[0]?.day_number;
    const found = weekGroups.find((g) => g.days.some((d) => d.day_number === dayNo));
    return found?.week ?? weekGroups[0]?.week ?? 1;
  });
  const swapOpened = useRef(false);

  const canRestoreAi = Boolean(detail.ai_generation_id && detail.source === "ai");

  useEffect(() => {
    setDraft(toDraft(detail));
    setTitleVi(detail.title_vi);
    setShareSlug(detail.share_token || "");
    setDescriptionVi(detail.description_vi || "");
    setOverviewSummary(detail.insights?.overview?.summary_vi || "");
    setClient(detail.insights?.client || {});
    setKnowledge(detail.insights?.staff_knowledge || []);
    setErr("");
  }, [detail.id, detail.updated_at]);

  useEffect(() => {
    if (swapOpened.current || !initialSwapExerciseId) return;
    const d = draft[activeDay];
    const ex = d?.exercises.find((e) => e.exercise_id === initialSwapExerciseId);
    if (!ex) return;
    swapOpened.current = true;
    setActiveTab("train");
    setSwapCtx({
      key: ex.key,
      exercise: {
        id: 0,
        exercise_id: ex.exercise_id,
        name_vi: ex.name_vi,
        sets: ex.sets,
        reps: ex.reps,
        section: ex.section,
        rest_seconds: ex.rest_seconds,
      },
    });
  }, [draft, activeDay, initialSwapExerciseId]);
  const sessionsPerWeek = useMemo(
    () => parseSessionsPerWeek(detail.description_vi),
    [detail.description_vi],
  );
  const day = draft[activeDay];
  const targetCal =
    detail.days[activeDay]?.target_calories ?? detail.target_calories;
  const usedMin = day ? dayMinutes(day) : 0;
  const flexScopeDays = day
    ? dayNumbersForFlexibleScope({
        days: draft,
        weekGroups,
        scope: flexibleScope,
        currentDayNumber: day.day_number,
      })
    : [];
  const pooling = Boolean(day?.meals_flexible);
  const pooledMeals = pooling ? mealsFromDays(draft, flexScopeDays).map((x) => x.meal) : day?.meals ?? [];
  const mealCal = pooledMeals.reduce((s, m) => s + mealLineKcal(m), 0);
  const calorieTarget =
    targetCal != null ? targetCal * (pooling ? Math.max(1, flexScopeDays.length) : 1) : null;
  const overCal = calorieTarget != null && mealCal > calorieTarget && pooledMeals.length > 0;
  const calorieLabel = pooling ? FLEXIBLE_CALORIE_LABEL[flexibleScope] : "Calo thực đơn ngày";

  const excludeIds = useMemo(
    () => new Set((day?.exercises || []).map((e) => e.exercise_id)),
    [day],
  );

  function patchDay(updater: (d: DraftDay) => DraftDay) {
    setDraft((prev) => prev.map((d, i) => (i === activeDay ? updater(d) : d)));
  }

  function applySwap(alt: ExerciseListItem) {
    if (!swapCtx) return;
    updateEx(swapCtx.key, {
      exercise_id: alt.id,
      name_vi: alt.name_vi,
      body_part: alt.body_part || alt.muscle_group || null,
    });
    setErr("");
    setSwapCtx(null);
  }

  function updateEx(key: string, patch: Partial<DraftExercise>) {
    patchDay((d) => ({
      ...d,
      exercises: d.exercises.map((e) => (e.key === key ? { ...e, ...patch } : e)),
    }));
  }

  function updateMeal(key: string, patch: Partial<DraftMeal>) {
    setDraft((prev) =>
      prev.map((d) =>
        d.meals.some((m) => m.key === key)
          ? { ...d, meals: d.meals.map((m) => (m.key === key ? { ...m, ...patch } : m)) }
          : d,
      ),
    );
  }

  function removeMeal(key: string) {
    setDraft((prev) =>
      prev.map((d) =>
        d.meals.some((m) => m.key === key)
          ? { ...d, meals: d.meals.filter((m) => m.key !== key) }
          : d,
      ),
    );
  }

  function setTechnique(key: string, technique: ExerciseTechnique | null) {
    setDraft((prev) =>
      prev.map((d, i) => {
        if (i !== activeDay) return d;
        const result = applyTechnique(d, key, technique);
        if (result.danglingSuper) toast("Thêm bài kế tiếp để ghép A2");
        return result.day;
      }),
    );
  }

  function warn(msg: string) {
    setFlash(msg);
    window.setTimeout(() => setFlash(""), 4000);
  }

  function toast(msg: string) {
    setFlash(msg);
    window.setTimeout(() => setFlash(""), 2500);
  }

  function tryIncSets(ex: DraftExercise) {
    updateEx(ex.key, applySetCount(ex, ex.sets + 1));
  }

  function setMealGrams(m: DraftMeal, nextGrams: number) {
    const grams = clampMealGrams(nextGrams);
    const projected = pooledMeals.reduce(
      (s, x) => s + kcalFromGrams(x.kcal_100g, x.key === m.key ? grams : x.grams),
      0,
    );
    if (calorieTarget != null && projected > calorieTarget) {
      warn(
        `Cảnh báo: thực đơn ~${viNum(projected)} kcal > mục tiêu ${viNum(calorieTarget)} kcal.`,
      );
    }
    updateMeal(m.key, { grams });
  }

  function addExercise(ex: ExerciseListItem) {
    const sets = addSection === "main" ? 3 : 1;
    const rest = defaultRestForSection(addSection, ex.movement_role);
    patchDay((d) => {
      const sectionItems = d.exercises.filter((e) => e.section === addSection);
      const last = sectionItems[sectionItems.length - 1];
      let cue = emptyCue();
      if (last?.technique === "super_set" && last.superset_group != null) {
        const count = d.exercises.filter((e) => e.superset_group === last.superset_group).length;
        if (count === 1) {
          cue = {
            ...cue,
            technique: "super_set",
            superset_group: last.superset_group,
          };
        }
      }
      const candidate: DraftExercise = {
        key: uid(),
        exercise_id: ex.id,
        name_vi: ex.name_vi,
        body_part: ex.body_part,
        section: addSection,
        sets,
        reps: addSection === "cardio" ? "10 phút" : addSection === "main" ? "12" : "15",
        rest_seconds: rest,
        ...cue,
      };
      return { ...d, exercises: [...d.exercises, candidate] };
    });
    toast(`Đã thêm ${ex.name_vi}`);
  }

  function addFood(food: Food, mealType: MealType) {
    const servingGrams = catalogServingGrams(food.serving_grams);
    const kcal100 = kcalPer100gFromFood(food);
    const grams = servingGrams;
    const addedKcal = kcalFromGrams(kcal100, grams);
    const projected = mealCal + addedKcal;
    if (calorieTarget != null && projected > calorieTarget) {
      warn(
        `Đã thêm ${food.name_vi}. Cảnh báo: ~${viNum(projected)} kcal > mục tiêu ${viNum(calorieTarget)} kcal.`,
      );
    }
    patchDay((d) => ({
      ...d,
      meals: [
        ...d.meals,
        {
          key: uid(),
          food_id: food.id,
          name_vi: food.name_vi,
          meal_type: day?.meals_flexible ? FLEX_MEAL_TYPE : mealType,
          grams,
          serving_grams: servingGrams,
          serving_size: food.serving_size || null,
          kcal_100g: kcal100,
          image_url: food.image_url || null,
        },
      ],
    }));
    if (!(calorieTarget != null && projected > calorieTarget)) {
      toast(`Đã thêm ${food.name_vi}`);
    }
  }

  async function save(): Promise<PlanDetail | null> {
    const anyOverCal =
      targetCal != null &&
      draft.some((d) => d.meals.length > 0 && dayCalories(d) > targetCal);

    if (anyOverCal) {
      const ok = window.confirm(
        `Lịch đang vượt calo > ${targetCal} kcal.\nVẫn lưu thay đổi?`,
      );
      if (!ok) return null;
    }

    setSaving(true);
    setErr("");
    try {
      if (!isValidShareSlug(shareSlug)) {
        setErr(shareSlugError(shareSlug));
        setSaving(false);
        return null;
      }
      const days: UpdatePlanDayPayload[] = draft.map((d) => ({
        day_number: d.day_number,
        title_vi: d.title_vi,
        exercises: d.exercises.map((e, i) => ({
          exercise_id: e.exercise_id,
          sets: e.sets,
          reps: e.reps,
          section: e.section,
          rest_seconds: e.rest_seconds,
          sort_order: i,
          rir: e.rir,
          rpe: e.rpe,
          tempo: e.tempo.trim() || null,
          technique: e.technique,
          superset_group: e.technique === "super_set" ? e.superset_group : null,
          set_prescriptions: e.set_prescriptions?.length
            ? e.set_prescriptions.map((row) => ({
                reps: row.reps,
                rest_seconds: row.rest_seconds,
                rir: row.rir,
                rpe: row.rpe,
                tempo: row.tempo.trim() || null,
                technique: row.technique,
              }))
            : null,
        })),
        meals: d.meals.map((m, i) => ({
          food_id: m.food_id,
          meal_type: m.meal_type,
          servings: servingsFromGrams(m.grams, m.serving_grams),
          sort_order: i,
        })),
        meals_flexible: d.meals_flexible,
      }));
      const next = await plansApi.updateContent(detail.id, {
        title_vi: titleVi.trim() || detail.title_vi,
        description_vi: descriptionVi.trim() || null,
        share_slug: shareSlug.trim(),
        overview_summary_vi: overviewSummary,
        staff_knowledge: knowledge,
        client: {
          height_cm: client.height_cm ?? null,
          weight_kg: client.weight_kg ?? null,
          gender: client.gender || null,
          notes: (client.notes || "").trim() || null,
        },
        sync_days: true,
        days,
      });
      onSaved(next);
      setFlash("Đã lưu. Tải lại trang sẽ thấy bản mới.");
      window.setTimeout(() => setFlash(""), 4000);
      window.setTimeout(() => router.refresh(), 3500);
      return next;
    } catch (ex) {
      setErr((ex as Error).message);
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function saveAsTemplate(e: React.FormEvent) {
    e.preventDefault();
    const title = templateTitle.trim();
    if (!title) {
      setErr("Vui lòng nhập tên template.");
      return;
    }
    setTemplateSaving(true);
    setErr("");
    try {
      const saved = await save();
      if (!saved) return;
      await plansApi.saveAsTemplate(saved.id, title);
      setTemplateOpen(false);
      setFlash("Đã lưu template. Bạn có thể dùng lại tại trang Lịch tập.");
      window.setTimeout(() => setFlash(""), 5000);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setTemplateSaving(false);
    }
  }

  async function restoreAi() {
    if (!canRestoreAi) return;
    const ok = window.confirm(
      "Khôi phục sẽ xóa mọi chỉnh sửa bài tập và thực đơn. Tiếp tục?",
    );
    if (!ok) return;
    setRestoring(true);
    setErr("");
    try {
      const next = await plansApi.restoreAi(detail.id);
      onSaved(next);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setRestoring(false);
    }
  }

  function selectDayByNumber(dayNumber: number) {
    const i = draft.findIndex((d) => d.day_number === dayNumber);
    if (i < 0) return;
    setActiveDay(i);
    const w = weekGroupForDay(weekGroups, dayNumber)?.week;
    if (w != null) setActiveWeek(w);
    setShowExSearch(false);
    setShowFoodSearch(false);
  }

  function addDay() {
    if (draft.length >= 100) return;
    const nextNum = Math.max(0, ...draft.map((d) => d.day_number)) + 1;
    setDraft((prev) => [
      ...prev,
      { day_number: nextNum, title_vi: `Ngày ${nextNum}`, meals_flexible: false, exercises: [], meals: [] },
    ]);
    setActiveDay(draft.length);
    setShowExSearch(false);
    setShowFoodSearch(false);
  }

  function removeActiveDay() {
    if (draft.length <= 1 || !day) return;
    const next = draft
      .filter((d) => d.day_number !== day.day_number)
      .map((d, i) => ({ ...d, day_number: i + 1 }));
    setDraft(next);
    setActiveDay(Math.min(activeDay, next.length - 1));
  }

  function openSwapFor(ex: DraftExercise) {
    setSwapCtx({
      key: ex.key,
      exercise: {
        id: 0,
        exercise_id: ex.exercise_id,
        name_vi: ex.name_vi,
        sets: ex.sets,
        reps: ex.reps,
        section: ex.section,
        rest_seconds: ex.rest_seconds,
      },
    });
  }

  if (!day) return null;

  const calPct =
    calorieTarget && calorieTarget > 0
      ? Math.min(100, Math.round((mealCal / calorieTarget) * 100))
      : 0;

  const exerciseBlocks = PLAN_SECTION_ORDER.map((sec) => {
    const items = day.exercises.filter((e) => e.section === sec);
    return (
      <div key={sec} className="mt-3">
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <p className="type-kicker text-slate-500">
            {SECTION_LABEL[sec]}
          </p>
          <button
            type="button"
            onClick={() => {
              setAddSection(sec);
              setShowExSearch(true);
              setShowFoodSearch(false);
            }}
            className="text-xs font-semibold text-brand-600 hover:underline"
          >
            + Thêm bài
          </button>
        </div>
        {items.length === 0 ? (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-400">Chưa có bài.</p>
        ) : (
        <ul className="space-y-2">
          {items.map((ex, exIdx) => {
            const slot = supersetSlotLabel(items, exIdx);
            const perSet = Boolean(ex.set_prescriptions?.length);
            const cue = perSet ? null : formatExerciseCue(ex);
            return (
            <li key={ex.key} className="rounded-lg bg-white p-2.5 ring-1 ring-slate-100">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-1.5 text-sm font-semibold">
                    {slot && (
                      <span className="rounded-md bg-violet-100 px-1.5 py-px text-[10px] font-bold text-violet-800">
                        {slot}
                      </span>
                    )}
                    {ex.technique === "drop_set" && (
                      <span className="rounded-md bg-amber-100 px-1.5 py-px text-[10px] font-bold text-amber-800">
                        Drop set
                      </span>
                    )}
                    {ex.name_vi}
                  </p>
                  <p className="text-[11px] text-slate-400">~{exMinutes(ex)}′</p>
                  {cue && <p className="text-[11px] font-medium text-slate-500">{cue}</p>}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => openSwapFor(ex)}
                    className="text-xs font-semibold text-brand-600 hover:underline"
                  >
                    Thay
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      patchDay((d) => {
                        const target = d.exercises.find((e) => e.key === ex.key);
                        return unpairGroup(
                          { ...d, exercises: d.exercises.filter((e) => e.key !== ex.key) },
                          target?.superset_group ?? null,
                        );
                      })
                    }
                    className="text-xs font-semibold text-rose-500 hover:underline"
                  >
                    Xóa
                  </button>
                </div>
              </div>
              <div className={perSet ? "mt-2 max-w-[11rem]" : "mt-2 grid grid-cols-3 gap-2"}>
                <Stepper
                  label="Set"
                  value={ex.sets}
                  onDec={() => updateEx(ex.key, applySetCount(ex, ex.sets - 1))}
                  onInc={() => tryIncSets(ex)}
                />
                {!perSet && (
                  <>
                    <Stepper
                      label={
                        parseReps(ex.reps).mode === "minutes"
                          ? "Phút"
                          : parseReps(ex.reps).mode === "seconds"
                            ? "Giây"
                            : "Rep"
                      }
                      value={parseReps(ex.reps).value}
                      onDec={() => updateEx(ex.key, { reps: bumpReps(ex.reps, -1) })}
                      onInc={() => updateEx(ex.key, { reps: bumpReps(ex.reps, 1) })}
                    />
                    <Stepper
                      label="Nghỉ (giây)"
                      value={ex.rest_seconds}
                      min={0}
                      onDec={() =>
                        updateEx(ex.key, { rest_seconds: Math.max(0, ex.rest_seconds - 15) })
                      }
                      onInc={() =>
                        updateEx(ex.key, { rest_seconds: Math.min(600, ex.rest_seconds + 15) })
                      }
                    />
                  </>
                )}
              </div>
              <label className="mt-2 flex items-center gap-2 text-[11px] font-semibold text-slate-600">
                <input
                  type="checkbox"
                  checked={perSet}
                  onChange={(e) => updateEx(ex.key, togglePerSet(ex, e.target.checked))}
                />
                Từng set
              </label>
              {!perSet ? (
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <label className="block text-[10px] font-semibold text-slate-500">
                    RIR
                    <input
                      type="number"
                      min={0}
                      max={5}
                      step={1}
                      value={ex.rir ?? ""}
                      onChange={(e) =>
                        updateEx(ex.key, { rir: parseOptionalInt(e.target.value, 0, 5) })
                      }
                      className="field mt-0.5 py-1 text-sm"
                    />
                  </label>
                  <label className="block text-[10px] font-semibold text-slate-500">
                    RPE
                    <input
                      type="number"
                      min={1}
                      max={10}
                      step={0.5}
                      value={ex.rpe ?? ""}
                      onChange={(e) =>
                        updateEx(ex.key, {
                          rpe: parseOptionalInt(e.target.value, 1, 10),
                        })
                      }
                      className="field mt-0.5 py-1 text-sm"
                    />
                  </label>
                  <label className="block text-[10px] font-semibold text-slate-500">
                    Tempo
                    <input
                      value={ex.tempo}
                      maxLength={16}
                      placeholder="3-1-1-0"
                      onChange={(e) => updateEx(ex.key, { tempo: e.target.value })}
                      className="field mt-0.5 py-1 text-sm"
                    />
                  </label>
                  <label className="block text-[10px] font-semibold text-slate-500">
                    Kỹ thuật
                    <select
                      value={ex.technique || ""}
                      onChange={(e) =>
                        setTechnique(
                          ex.key,
                          (e.target.value || null) as ExerciseTechnique | null,
                        )
                      }
                      className="field mt-0.5 py-1 text-sm"
                    >
                      <option value="">—</option>
                      <option value="drop_set">Drop set</option>
                      <option value="super_set">Super set</option>
                    </select>
                  </label>
                </div>
              ) : (
                <div className="mt-2 space-y-2">
                  <label className="block text-[10px] font-semibold text-slate-500">
                    Super set
                    <select
                      value={ex.technique === "super_set" ? "super_set" : ""}
                      onChange={(e) =>
                        setTechnique(
                          ex.key,
                          (e.target.value || null) as ExerciseTechnique | null,
                        )
                      }
                      className="field mt-0.5 py-1 text-sm"
                    >
                      <option value="">—</option>
                      <option value="super_set">Super set</option>
                    </select>
                  </label>
                  {ex.set_prescriptions!.map((row, si) => (
                    <div key={`${ex.key}-s${si}`} className="rounded-lg bg-slate-50 p-2 ring-1 ring-slate-100">
                      <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">
                        Set {si + 1}
                      </p>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                        <label className="block text-[10px] font-semibold text-slate-500">
                          Rep
                          <input
                            value={row.reps}
                            onChange={(e) =>
                              updateEx(ex.key, patchSetRow(ex, si, { reps: e.target.value }))
                            }
                            className="field mt-0.5 py-1 text-sm"
                          />
                        </label>
                        <label className="block text-[10px] font-semibold text-slate-500">
                          Nghỉ (giây)
                          <input
                            type="number"
                            min={0}
                            max={600}
                            step={15}
                            value={row.rest_seconds}
                            onChange={(e) =>
                              updateEx(
                                ex.key,
                                patchSetRow(ex, si, {
                                  rest_seconds: Math.max(
                                    0,
                                    Math.min(600, Number(e.target.value) || 0),
                                  ),
                                }),
                              )
                            }
                            className="field mt-0.5 py-1 text-sm"
                          />
                        </label>
                        <label className="block text-[10px] font-semibold text-slate-500">
                          RIR
                          <input
                            type="number"
                            min={0}
                            max={5}
                            step={1}
                            value={row.rir ?? ""}
                            onChange={(e) =>
                              updateEx(
                                ex.key,
                                patchSetRow(ex, si, {
                                  rir: parseOptionalInt(e.target.value, 0, 5),
                                }),
                              )
                            }
                            className="field mt-0.5 py-1 text-sm"
                          />
                        </label>
                        <label className="block text-[10px] font-semibold text-slate-500">
                          RPE
                          <input
                            type="number"
                            min={1}
                            max={10}
                            step={0.5}
                            value={row.rpe ?? ""}
                            onChange={(e) =>
                              updateEx(
                                ex.key,
                                patchSetRow(ex, si, {
                                  rpe: parseOptionalInt(e.target.value, 1, 10),
                                }),
                              )
                            }
                            className="field mt-0.5 py-1 text-sm"
                          />
                        </label>
                        <label className="block text-[10px] font-semibold text-slate-500">
                          Tempo
                          <input
                            value={row.tempo}
                            maxLength={16}
                            placeholder="3-1-1-0"
                            onChange={(e) =>
                              updateEx(ex.key, patchSetRow(ex, si, { tempo: e.target.value }))
                            }
                            className="field mt-0.5 py-1 text-sm"
                          />
                        </label>
                        <label className="block text-[10px] font-semibold text-slate-500">
                          Kỹ thuật
                          <select
                            value={row.technique || ""}
                            onChange={(e) =>
                              updateEx(
                                ex.key,
                                patchSetRow(ex, si, {
                                  technique: e.target.value === "drop_set" ? "drop_set" : null,
                                }),
                              )
                            }
                            className="field mt-0.5 py-1 text-sm"
                          >
                            <option value="">—</option>
                            <option value="drop_set">Drop set</option>
                          </select>
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </li>
            );
          })}
        </ul>
        )}
      </div>
    );
  });

  function openFoodPicker(mealType: MealType = "lunch") {
    setAddMealType(day?.meals_flexible ? FLEX_MEAL_TYPE : mealType);
    setShowFoodSearch(true);
    setShowExSearch(false);
  }

  function applyMealsFlexible(
    value: boolean,
    scope: FlexibleMealScope,
    previousScope?: FlexibleMealScope,
  ) {
    if (!day) return;
    const nums = new Set(
      dayNumbersForFlexibleScope({
        days: draft,
        weekGroups,
        scope,
        currentDayNumber: day.day_number,
      }),
    );
    const prevNums = previousScope
      ? new Set(
          dayNumbersForFlexibleScope({
            days: draft,
            weekGroups,
            scope: previousScope,
            currentDayNumber: day.day_number,
          }),
        )
      : new Set<number>();
    setDraft((prev) =>
      prev.map((d) => {
        if (nums.has(d.day_number)) return { ...d, meals_flexible: value };
        if (value && prevNums.has(d.day_number)) return { ...d, meals_flexible: false };
        return d;
      }),
    );
  }

  function changeFlexibleScope(next: FlexibleMealScope) {
    const prev = flexibleScope;
    setFlexibleScope(next);
    if (day?.meals_flexible) applyMealsFlexible(true, next, prev);
  }

  const trainApplyScopes = trainApplyScopesForNav(weekGroups);
  const resolvedTrainScope: TrainApplyScope = trainApplyScopes.includes(trainApplyScope)
    ? trainApplyScope
    : (trainApplyScopes[0] ?? "plan");
  const trainApplyTargets = day
    ? trainApplyTargetWeekCount({
        weekGroups,
        currentDayNumber: day.day_number,
        scope: resolvedTrainScope,
      })
    : 0;

  function applyThisWeekTraining() {
    if (!day || trainApplyTargets <= 0) return;
    const ok = window.confirm(
      `Ghi đè bài tập của ${trainApplyTargets} tuần bằng tuần đang mở? Thực đơn không đổi.`,
    );
    if (!ok) return;
    setDraft((prev) =>
      applyWeekTraining({
        days: prev,
        weekGroups,
        sourceDayNumber: day.day_number,
        scope: resolvedTrainScope,
        cloneExercise: cloneDraftExercise,
      }),
    );
  }

  function mealEditorRows(slotMeals: DraftMeal[]) {
    return (
      <ul className="space-y-2">
        {slotMeals.map((m) => (
          <li key={m.key} className="rounded-lg bg-amber-50 p-2.5">
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-start gap-2">
                <MealThumb imageUrl={m.image_url} name={m.name_vi} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-amber-950">{m.name_vi}</p>
                  <p className="text-xs text-amber-800">
                    {viNum(Math.round(m.kcal_100g))} kcal/100g
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => removeMeal(m.key)}
                className="text-xs font-semibold text-rose-500 hover:underline"
              >
                Xóa
              </button>
            </div>
            <div className="mt-2 max-w-[240px]">
              <MealGramsInput
                grams={m.grams}
                servingGrams={m.serving_grams}
                servingSize={m.serving_size}
                kcal100g={m.kcal_100g}
                warn={overCal}
                onChange={(grams) => setMealGrams(m, grams)}
              />
            </div>
          </li>
        ))}
      </ul>
    );
  }

  const mealBlocks = (
      <div>
        {day?.meals_flexible ? (
          <PlanMealAccordion
            title="Linh hoạt — tự chia bữa"
            itemCount={pooledMeals.length}
            kcal={mealCal}
            defaultOpen
          >
            <p className="mb-2 text-xs leading-relaxed text-slate-500">
              Không gán theo bữa. Khách tự chia; HLV chỉ chọn tổng lượng thực phẩm
              {flexibleScope === "day"
                ? " trong ngày."
                : flexibleScope === "week"
                  ? " trong tuần."
                  : flexibleScope === "month"
                    ? " trong tháng."
                    : " của cả lịch."}
            </p>
            {pooledMeals.length ? mealEditorRows(pooledMeals) : <p className="text-sm text-slate-400">Chưa có món.</p>}
            <button
              type="button"
              onClick={() => openFoodPicker(FLEX_MEAL_TYPE)}
              className="mt-2 text-xs font-semibold text-amber-700 hover:underline"
            >
              + Thêm món
            </button>
          </PlanMealAccordion>
        ) : (
          MEAL_GROUP_ORDER.map((mt) => {
            const slotMeals = mealsForSlot(day?.meals ?? [], mt);
            const slotKcal = slotMeals.reduce((sum, m) => sum + mealLineKcal(m), 0);
            return (
              <PlanMealAccordion
                key={mt}
                title={mealGroupTitle(mt)}
                itemCount={slotMeals.length}
                kcal={slotKcal}
                defaultOpen={mt === "breakfast"}
              >
                {slotMeals.length ? mealEditorRows(slotMeals) : (
                  <p className="text-sm text-slate-400">Chưa có món.</p>
                )}
                <button
                  type="button"
                  onClick={() => openFoodPicker(mt)}
                  className="mt-2 text-xs font-semibold text-amber-700 hover:underline"
                >
                  + Thêm món
                </button>
              </PlanMealAccordion>
            );
          })
        )}
      </div>
    );

  const swapModal = (
    <ExerciseAlternativesModal
      open={swapCtx != null}
      exercise={swapCtx?.exercise ?? null}
      canSave
      loginNext="/dang-nhap"
      context={altContextFromPlanInputs(detail.insights?.inputs)}
      onClose={() => setSwapCtx(null)}
      onSelect={applySwap}
    />
  );

  const pickerModals = (
    <>
      <PlanExercisePickerModal
        open={showExSearch}
        onClose={() => setShowExSearch(false)}
        excludeIds={excludeIds}
        onPick={addExercise}
        exerciseType={addSection}
        sectionLabel={SECTION_LABEL[addSection]}
      />
      <PlanFoodPickerModal
        open={showFoodSearch}
        onClose={() => setShowFoodSearch(false)}
        initialMealType={addMealType}
        hideMealSelect={Boolean(day?.meals_flexible)}
        onPick={addFood}
      />
      {flash && (
        <div className="pointer-events-none fixed bottom-24 left-1/2 z-[110] w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 md:bottom-8">
          <div className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white shadow-2xl">
            {flash.startsWith("Đã ") ? flash : `⚠️ ${flash}`}
          </div>
        </div>
      )}
    </>
  );

  if (!day) {
    return (
      <div className="space-y-3 py-6 text-center">
        <p className="text-sm text-slate-500">Chưa có ngày nào trong lịch.</p>
        <button
          type="button"
          onClick={addDay}
          className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600"
        >
          + Thêm ngày
        </button>
      </div>
    );
  }

  const durationCard = (
    <div className="rounded-xl bg-white p-3 ring-1 ring-slate-100">
      <div className="flex items-end justify-between text-sm">
        <span className="font-semibold text-slate-600">Thời lượng tập</span>
        <span className="font-bold text-brand-600">{usedMin}′</span>
      </div>
      {trainApplyScopes.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-600">Áp dụng lịch tập tuần này</span>
          <select
            value={resolvedTrainScope}
            onChange={(e) => setTrainApplyScope(e.target.value as TrainApplyScope)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold"
            aria-label="Phạm vi áp dụng lịch tập tuần này"
          >
            {trainApplyScopes.map((key) => (
              <option key={key} value={key}>
                {TRAIN_APPLY_SCOPE_LABEL[key]}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={trainApplyTargets <= 0}
            onClick={applyThisWeekTraining}
            className="rounded-lg bg-brand-500 px-2.5 py-1.5 text-xs font-bold text-white hover:bg-brand-600 disabled:opacity-40"
          >
            Áp dụng
          </button>
        </div>
      )}
    </div>
  );

  const calorieCard = (
    <div className={`rounded-xl p-3 ring-1 ${overCal ? "bg-rose-50 ring-rose-200" : "bg-white ring-slate-100"}`}>
      <div className="flex flex-wrap items-end justify-between gap-2 text-sm">
        <span className="font-semibold text-slate-600">{calorieLabel}</span>
        <span className={`font-bold ${overCal ? "text-rose-600" : "text-brand-600"}`}>
          {viNum(mealCal)}
          {calorieTarget != null ? ` / ${viNum(calorieTarget)}` : ""} kcal
        </span>
      </div>
      {calorieTarget != null && (
        <div className="macro-track mt-2 h-2.5">
          <div
            className={overCal ? "bg-rose-500" : calPct >= 95 ? "bg-amber-400" : "bg-brand-500"}
            style={{ width: `${Math.min(100, calPct)}%` }}
          />
        </div>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
          <input
            type="checkbox"
            checked={Boolean(day.meals_flexible)}
            onChange={(e) => applyMealsFlexible(e.target.checked, flexibleScope)}
          />
          Linh hoạt bữa ăn
        </label>
        <select
          value={flexibleScope}
          onChange={(e) => changeFlexibleScope(e.target.value as FlexibleMealScope)}
          className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold"
          aria-label="Phạm vi linh hoạt bữa ăn"
        >
          {(Object.keys(FLEXIBLE_SCOPE_LABEL) as FlexibleMealScope[]).map((key) => (
            <option key={key} value={key}>
              {FLEXIBLE_SCOPE_LABEL[key]}
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  const templateModal = (
    <Modal open={templateOpen} onClose={() => setTemplateOpen(false)} title="Lưu thành template">
      <form onSubmit={(e) => void saveAsTemplate(e)} className="space-y-4 p-5">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Lưu thành template</h2>
          <p className="mt-1 text-sm text-slate-500">
            Nội dung lịch hiện tại sẽ được lưu nhưng không sao chép hồ sơ khách.
          </p>
        </div>
        <label className="block text-sm font-semibold text-slate-600">
          Tên template
          <input
            required
            maxLength={255}
            value={templateTitle}
            onChange={(e) => setTemplateTitle(e.target.value)}
            className="field mt-1"
          />
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTemplateOpen(false)}
            disabled={templateSaving}
            className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={templateSaving || saving}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white disabled:opacity-50"
          >
            {templateSaving ? "Đang lưu…" : "Lưu template"}
          </button>
        </div>
      </form>
    </Modal>
  );

  if (variant === "page") {
    const inputRecap = detail.insights?.inputs?.recap_vi?.trim() || null;
    const inputChips = (detail.insights?.inputs?.chips || []).filter(Boolean);
    return (
      <>
        <PlanViewShell
          title={titleVi || detail.title_vi}
          recap={inputRecap}
          chips={inputChips}
          backHref={plansListHref}
          calorieLine={
            detail.target_calories != null
              ? `~${viNum(detail.target_calories)} kcal trung bình/ngày`
              : null
          }
          belowHero={
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-600">
                Tên lịch
                <input
                  value={titleVi}
                  onChange={(e) => setTitleVi(e.target.value)}
                  className="field mt-1"
                />
              </label>
              <PlanShareLinkBar plan={detail} slug={shareSlug} onSlugChange={setShareSlug} />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={addDay}
                  disabled={draft.length >= 100}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:border-brand-400"
                >
                  + Thêm ngày
                </button>
                <button
                  type="button"
                  onClick={removeActiveDay}
                  disabled={draft.length <= 1}
                  className="rounded-xl border border-rose-200 bg-white px-3 py-1.5 text-xs font-bold text-rose-600 hover:bg-rose-50 disabled:opacity-40"
                >
                  Xóa ngày này
                </button>
              </div>
            </div>
          }
          activeTab={activeTab}
          onTabChange={setActiveTab}
          tabs={EDITOR_TABS}
          naturalHeight={activeTab === "meals" || activeTab === "train"}
          nav={
            activeTab === "overview" ? undefined : (
            <PlanWeekSessionNav
              weekGroups={weekGroups}
              activeWeek={weekGroupForDay(weekGroups, day.day_number)?.week ?? activeWeek}
              activeDayNumber={day.day_number}
              plainWeekLabels={detail.source === "manual" || detail.source === "template"}
              onWeekChange={(week, firstDayNumber) => {
                setActiveWeek(week);
                selectDayByNumber(firstDayNumber);
              }}
              onDayChange={selectDayByNumber}
            />
            )
          }
        >
          {err && <p className="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

          {activeTab === "overview" && (
            <PlanOverviewEditor
              summaryVi={overviewSummary}
              onSummary={setOverviewSummary}
              descriptionVi={descriptionVi}
              onDescription={setDescriptionVi}
              client={client}
              onClient={setClient}
              knowledge={knowledge}
              onKnowledge={setKnowledge}
            />
          )}

          {activeTab === "train" && (
            <div className="space-y-3 pb-28 md:pb-0">
              {durationCard}
              <div className="rounded-2xl bg-white p-4 shadow-soft">
                <div className="mb-3">
                  <input
                    value={day.title_vi || ""}
                    onChange={(e) => patchDay((d) => ({ ...d, title_vi: e.target.value }))}
                    className="field max-w-xs text-sm font-bold"
                    placeholder="Ngực, Lưng, Ngày nghỉ…"
                    aria-label="Tiêu đề ngày"
                  />
                </div>
                {exerciseBlocks}
              </div>
            </div>
          )}

          {activeTab === "meals" && (
            <div className="space-y-3 pb-28 md:pb-0">
              {calorieCard}
              <div className="rounded-2xl bg-white p-4 shadow-soft">
                <div className="mb-3">
                  <input
                    value={day.title_vi || ""}
                    onChange={(e) => patchDay((d) => ({ ...d, title_vi: e.target.value }))}
                    className="field max-w-xs text-sm font-bold"
                    placeholder="Ngực, Lưng, Ngày nghỉ…"
                    aria-label="Tiêu đề ngày"
                  />
                </div>
                {mealBlocks}
              </div>
            </div>
          )}

          <div className="sticky bottom-20 z-10 mt-4 flex flex-col gap-2 rounded-2xl bg-white/95 p-3 shadow-soft ring-1 ring-slate-100 sm:flex-row md:bottom-4">
            <Link
              href={plansListHref}
              className="flex-1 rounded-xl bg-brand-500 py-2.5 text-center text-sm font-bold text-white shadow-soft hover:bg-brand-600"
            >
              ← Danh sách lịch
            </Link>
            {canRestoreAi && (
              <button
                type="button"
                disabled={saving || restoring}
                onClick={() => void restoreAi()}
                className="flex-1 rounded-xl border border-amber-200 bg-amber-50 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
              >
                {restoring ? "Đang khôi phục…" : <>Khôi phục {brandRichText("TAPTOT")} gốc</>}
              </button>
            )}
            {!detail.is_template && (
              <button
                type="button"
                disabled={saving || templateSaving}
                onClick={() => {
                  setTemplateTitle(`Mẫu — ${titleVi.trim() || detail.title_vi}`);
                  setTemplateOpen(true);
                }}
                className="flex-1 rounded-xl border border-brand-200 bg-brand-50 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-100 disabled:opacity-50"
              >
                Lưu thành template
              </button>
            )}
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {saving ? "Đang lưu…" : overCal ? "Lưu (có cảnh báo)" : "Lưu thay đổi"}
            </button>
          </div>
        </PlanViewShell>
        {swapModal}
        {pickerModals}
        {templateModal}
      </>
    );
  }

  return (
    <div className="space-y-4">
      {/* Locked plan info */}
      <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
        <p className="type-kicker text-slate-400">Thông tin lịch</p>
        <input
          value={titleVi}
          onChange={(e) => setTitleVi(e.target.value)}
          className="field mt-1 text-lg font-bold"
        />
        <div className="mt-3">
          <PlanShareLinkBar plan={detail} slug={shareSlug} onSlugChange={setShareSlug} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={addDay}
            className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-bold"
          >
            + Thêm ngày
          </button>
          <button
            type="button"
            onClick={removeActiveDay}
            disabled={draft.length <= 1}
            className="rounded-xl border border-rose-200 px-3 py-1.5 text-xs font-bold text-rose-600 disabled:opacity-40"
          >
            Xóa ngày này
          </button>
        </div>
        {detail.description_vi && (
          <p className="mt-1 text-sm text-slate-600">{detail.description_vi}</p>
        )}
        <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Nguồn</p>
            <p className="font-bold text-slate-700">{brandRichText(SOURCE_LABEL[detail.source] || detail.source)}</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Calo mục tiêu</p>
            <p className="font-bold text-brand-700">
              {detail.target_calories != null ? `${viNum(detail.target_calories)} kcal/ngày` : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Thời lượng buổi</p>
            <p className="font-bold text-slate-700">{usedMin} phút</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Số buổi / tuần</p>
            <p className="font-bold text-slate-700">
              {sessionsPerWeek ?? detail.day_count} buổi
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Số ngày trong lịch</p>
            <p className="font-bold text-slate-700">{detail.day_count} ngày</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Khoảng ngày</p>
            <p className="font-bold text-slate-700">
              {formatDate(detail.start_date)} → {formatDate(detail.end_date)}
            </p>
          </div>
        </div>
        <p className="mt-2 text-[11px] text-slate-400">
          Các trường trên không thể chỉnh khi sửa lịch — chỉ đổi bài tập / set / rep và thực đơn.
        </p>
        {canRestoreAi && (
          <button
            type="button"
            disabled={saving || restoring}
            onClick={() => void restoreAi()}
            className="mt-3 w-full rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
          >
            {restoring ? "Đang khôi phục…" : <>Khôi phục bản {brandRichText("TAPTOT")} gốc</>}
          </button>
        )}
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      <div className="flex flex-wrap gap-2">
        {draft.map((d, i) => {
          const cOver = targetCal != null && d.meals.length > 0 && dayCalories(d) > targetCal;
          return (
            <button
              key={d.day_number}
              type="button"
              onClick={() => {
                setActiveDay(i);
                setShowExSearch(false);
                setShowFoodSearch(false);
              }}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                i === activeDay
                  ? "bg-brand-500 text-white"
                  : cOver
                    ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                    : "bg-slate-100 text-slate-600 hover:bg-brand-50"
              }`}
            >
              {d.title_vi || `Ngày ${d.day_number}`}
              {cOver && " !"}
            </button>
          );
        })}
      </div>

      {/* Budget meters for active day */}
      <div className="grid gap-3 sm:grid-cols-2">
        {durationCard}
        {calorieCard}
      </div>

      <div className="rounded-xl bg-slate-50 p-4">
        <div className="mb-3">
          <input
            value={day.title_vi || ""}
            onChange={(e) => patchDay((d) => ({ ...d, title_vi: e.target.value }))}
            className="field max-w-xs text-sm font-bold"
            placeholder="Ngực, Lưng, Ngày nghỉ…"
            aria-label="Tiêu đề ngày"
          />
        </div>

        {exerciseBlocks}

        <div className="mt-4">
          <p className="mb-1.5 type-kicker text-slate-500">Thực đơn</p>
          {mealBlocks}
        </div>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 hover:border-slate-300"
        >
          Hủy
        </button>
        {!detail.is_template && (
          <button
            type="button"
            onClick={() => {
              setTemplateTitle(`Mẫu — ${titleVi.trim() || detail.title_vi}`);
              setTemplateOpen(true);
            }}
            disabled={saving || templateSaving}
            className="flex-1 rounded-xl border border-brand-200 bg-brand-50 py-2.5 text-sm font-semibold text-brand-700 disabled:opacity-50"
          >
            Lưu thành template
          </button>
        )}
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving}
          className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {saving ? "Đang lưu…" : overCal ? "Lưu (có cảnh báo)" : "Lưu thay đổi"}
        </button>
      </div>

      {swapModal}
      {pickerModals}
      {templateModal}
    </div>
  );
}
