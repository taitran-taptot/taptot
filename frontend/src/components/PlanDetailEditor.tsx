"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { viNum } from "@/lib/labels";
import { defaultRestForSection } from "@/lib/workoutRest";
import type { ExerciseListItem, Food } from "@/lib/types";
import {
  MEAL_LABEL,
  PLAN_SECTION_ORDER,
  SECTION_LABEL,
  SOURCE_LABEL,
  plansApi,
  type PlanDetail,
  type PlanSectionKey,
  type UpdatePlanDayPayload,
} from "@/lib/plansApi";
import { bumpReps, parseReps } from "@/lib/reps";
import { estimatePlanDayMinutes, estimatePlanExerciseMinutes, parseSessionsPerWeek } from "@/lib/planLabels";
import { groupPlanDaysByWeek } from "@/lib/planWeeks";
import ExerciseAlternativesModal from "./ExerciseAlternativesModal";
import { altContextFromPlanInputs, type SwapExerciseContext } from "@/lib/planSwap";
import PlanViewShell from "./plan-view/PlanViewShell";
import type { PlanViewTab } from "./plan-view/types";
import PlanWeekSessionNav from "./plan-view/PlanWeekSessionNav";
import PlanMealAccordion, {
  MEAL_GROUP_ORDER,
  firstFilledMealType,
  mealGroupTitle,
} from "./plan-view/PlanMealAccordion";

const EDITOR_TABS: { id: PlanViewTab; label: string }[] = [
  { id: "train", label: "Buổi tập" },
  { id: "meals", label: "Ăn uống" },
];

type Section = PlanSectionKey;
type MealType = "breakfast" | "lunch" | "dinner" | "snack";

interface DraftExercise {
  key: string;
  exercise_id: number;
  name_vi: string;
  body_part: string | null;
  section: Section;
  sets: number;
  reps: string;
  rest_seconds: number;
}

interface DraftMeal {
  key: string;
  food_id: number;
  name_vi: string;
  meal_type: MealType;
  servings: number;
  calories_per: number;
}

interface DraftDay {
  day_number: number;
  title_vi: string | null;
  exercises: DraftExercise[];
  meals: DraftMeal[];
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function parseSessionMinutes(desc: string | null | undefined): number | null {
  if (!desc) return null;
  const m = desc.match(/(\d+)\s*phút\s*\/\s*buổi/i);
  return m ? Number(m[1]) : null;
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

function dayCalories(day: DraftDay): number {
  return Math.round(day.meals.reduce((s, m) => s + m.calories_per * m.servings, 0));
}

function toDraft(detail: PlanDetail): DraftDay[] {
  return detail.days.map((d) => ({
    day_number: d.day_number,
    title_vi: d.title_vi,
    exercises: d.exercises.map((ex) => ({
      key: `ex-${ex.id}`,
      exercise_id: ex.exercise_id,
      name_vi: ex.name_vi,
      body_part: ex.body_part,
      section: (ex.section as Section) || "main",
      sets: ex.sets,
      reps: String(ex.reps ?? "12"),
      rest_seconds: ex.rest_seconds || defaultRestForSection(ex.section),
    })),
    meals: d.meals.map((m) => ({
      key: `m-${m.id}`,
      food_id: m.food_id,
      name_vi: m.name_vi,
      meal_type: (m.meal_type as MealType) || "lunch",
      servings: m.servings,
      calories_per: m.servings > 0 ? Math.round(m.calories / m.servings) : m.calories,
    })),
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
        <span className="w-7 text-center text-sm font-bold">{value}</span>
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

function ExerciseSearch({
  onPick,
  excludeIds,
}: {
  onPick: (ex: ExerciseListItem) => void;
  excludeIds: Set<number>;
}) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<ExerciseListItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setLoading(true);
      api
        .searchExercises({ q: q || undefined, page_size: 8 })
        .then((d) => setItems(d.items))
        .catch(() => setItems([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="mt-2 rounded-xl border border-dashed border-brand-200 bg-brand-50/40 p-3">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Tìm bài tập để thêm…"
        className="field text-sm"
      />
      {loading && <p className="mt-2 text-xs text-slate-400">Đang tìm…</p>}
      <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
        {items.map((ex) => {
          const disabled = excludeIds.has(ex.id);
          return (
            <li key={ex.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onPick(ex)}
                className="flex w-full items-center justify-between rounded-lg bg-white px-2.5 py-2 text-left text-sm hover:bg-brand-50 disabled:opacity-40"
              >
                <span className="truncate font-medium">{ex.name_vi}</span>
                <span className="shrink-0 text-xs font-bold text-brand-600">{disabled ? "Đã có" : "+ Thêm"}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function FoodSearch({ onPick }: { onPick: (food: Food, mealType: MealType) => void }) {
  const [q, setQ] = useState("");
  const [mealType, setMealType] = useState<MealType>("lunch");
  const [items, setItems] = useState<Food[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setLoading(true);
      api
        .searchFoods({ q: q || undefined, page_size: 8 })
        .then((d) => setItems(d.items))
        .catch(() => setItems([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="mt-2 rounded-xl border border-dashed border-amber-200 bg-amber-50/50 p-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Tìm món ăn để thêm…"
          className="field flex-1 text-sm"
        />
        <select
          value={mealType}
          onChange={(e) => setMealType(e.target.value as MealType)}
          className="field w-full text-sm sm:w-32"
        >
          {(Object.keys(MEAL_LABEL) as MealType[]).map((k) => (
            <option key={k} value={k}>
              {MEAL_LABEL[k]}
            </option>
          ))}
        </select>
      </div>
      {loading && <p className="mt-2 text-xs text-slate-400">Đang tìm…</p>}
      <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
        {items.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => onPick(f, mealType)}
              className="flex w-full items-center justify-between rounded-lg bg-white px-2.5 py-2 text-left text-sm hover:bg-amber-50"
            >
              <span className="truncate font-medium">{f.name_vi}</span>
              <span className="shrink-0 text-xs font-semibold text-amber-800">{Math.round(f.calories)} kcal</span>
            </button>
          </li>
        ))}
      </ul>
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
  const [draft, setDraft] = useState<DraftDay[]>(() => toDraft(detail));
  const [activeDay, setActiveDay] = useState(() => {
    if (initialDayNumber == null) return 0;
    const i = detail.days.findIndex((d) => d.day_number === initialDayNumber);
    return i >= 0 ? i : 0;
  });
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [err, setErr] = useState("");
  const [flash, setFlash] = useState("");
  const [showExSearch, setShowExSearch] = useState(false);
  const [showFoodSearch, setShowFoodSearch] = useState(false);
  const [addSection, setAddSection] = useState<Section>("main");
  const [swapCtx, setSwapCtx] = useState<{ key: string; exercise: SwapExerciseContext } | null>(
    null,
  );
  const [activeTab, setActiveTab] = useState<PlanViewTab>("train");
  const weekGroups = useMemo(() => groupPlanDaysByWeek(detail.days), [detail.days]);
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
  const sessionMinutes = useMemo(
    () => parseSessionMinutes(detail.description_vi) ?? 45,
    [detail.description_vi],
  );
  const sessionsPerWeek = useMemo(
    () => parseSessionsPerWeek(detail.description_vi),
    [detail.description_vi],
  );
  const day = draft[activeDay];
  const targetCal =
    detail.days[activeDay]?.target_calories ?? detail.target_calories;
  const usedMin = day ? dayMinutes(day) : 0;
  const mealCal = day ? dayCalories(day) : 0;
  const overTime = usedMin > sessionMinutes;
  const overCal = targetCal != null && mealCal > targetCal && (day?.meals.length ?? 0) > 0;

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
    patchDay((d) => ({
      ...d,
      meals: d.meals.map((m) => (m.key === key ? { ...m, ...patch } : m)),
    }));
  }

  function warn(msg: string) {
    setFlash(msg);
    window.setTimeout(() => setFlash(""), 4000);
  }

  function tryIncSets(ex: DraftExercise) {
    const next: DraftExercise = { ...ex, sets: Math.min(20, ex.sets + 1) };
    const projected = dayMinutes({
      ...day!,
      exercises: day!.exercises.map((e) => (e.key === ex.key ? next : e)),
    });
    if (projected > sessionMinutes) {
      warn(
        `Cảnh báo: tăng set sẽ ~${projected}′ / ${sessionMinutes}′ — vượt thời lượng buổi đã đặt.`,
      );
    }
    updateEx(ex.key, { sets: next.sets });
  }

  function tryIncServings(m: DraftMeal) {
    const nextServ = Math.min(20, Math.round((m.servings + 0.5) * 10) / 10);
    const projected = Math.round(
      day!.meals.reduce(
        (s, x) => s + x.calories_per * (x.key === m.key ? nextServ : x.servings),
        0,
      ),
    );
    if (targetCal != null && projected > targetCal) {
      warn(
        `Cảnh báo: thực đơn ~${viNum(projected)} kcal > mục tiêu ${viNum(targetCal)} kcal/ngày.`,
      );
    }
    updateMeal(m.key, { servings: nextServ });
  }

  function addExercise(ex: ExerciseListItem) {
    const sets = addSection === "main" ? 3 : 1;
    const rest = defaultRestForSection(addSection, ex.movement_role);
    const candidate: DraftExercise = {
      key: uid(),
      exercise_id: ex.id,
      name_vi: ex.name_vi,
      body_part: ex.body_part,
      section: addSection,
      sets,
      reps: addSection === "cardio" ? "10 phút" : addSection === "main" ? "12" : "15",
      rest_seconds: rest,
    };
    const projected = dayMinutes({
      ...day!,
      exercises: [...day!.exercises, candidate],
    });
    if (projected > sessionMinutes) {
      warn(
        `Cảnh báo: thêm “${ex.name_vi}” → ~${projected}′ / ${sessionMinutes}′ — vượt thời lượng buổi.`,
      );
    }
    patchDay((d) => ({ ...d, exercises: [...d.exercises, candidate] }));
    setShowExSearch(false);
  }

  function addFood(food: Food, mealType: MealType) {
    const calPer = Math.round(food.calories);
    const projected = mealCal + calPer;
    if (targetCal != null && projected > targetCal) {
      warn(
        `Cảnh báo: thêm “${food.name_vi}” → ~${viNum(projected)} kcal > mục tiêu ${viNum(targetCal)} kcal.`,
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
          meal_type: mealType,
          servings: 1,
          calories_per: calPer,
        },
      ],
    }));
    setShowFoodSearch(false);
  }

  async function save() {
    const anyOverTime = draft.some((d) => dayMinutes(d) > sessionMinutes);
    const anyOverCal =
      targetCal != null &&
      draft.some((d) => d.meals.length > 0 && dayCalories(d) > targetCal);

    if (anyOverTime || anyOverCal) {
      const parts: string[] = [];
      if (anyOverTime) parts.push(`thời lượng > ${sessionMinutes}′/buổi`);
      if (anyOverCal) parts.push(`calo > ${targetCal} kcal`);
      const ok = window.confirm(
        `Lịch đang vượt: ${parts.join(" và ")}.\nVẫn lưu thay đổi?`,
      );
      if (!ok) return;
    }

    setSaving(true);
    setErr("");
    try {
      const days: UpdatePlanDayPayload[] = draft.map((d) => ({
        day_number: d.day_number,
        exercises: d.exercises.map((e, i) => ({
          exercise_id: e.exercise_id,
          sets: e.sets,
          reps: e.reps,
          section: e.section,
          rest_seconds: e.rest_seconds,
          sort_order: i,
        })),
        meals: d.meals.map((m, i) => ({
          food_id: m.food_id,
          meal_type: m.meal_type,
          servings: m.servings,
          sort_order: i,
        })),
      }));
      const next = await plansApi.updateContent(detail.id, days);
      onSaved(next);
      if (variant === "page") {
        setFlash("Đã lưu thay đổi.");
        window.setTimeout(() => setFlash(""), 2500);
      }
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setSaving(false);
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
    setShowExSearch(false);
    setShowFoodSearch(false);
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

  const timePct = Math.min(100, Math.round((usedMin / sessionMinutes) * 100));
  const calPct =
    targetCal && targetCal > 0 ? Math.min(100, Math.round((mealCal / targetCal) * 100)) : 0;

  const exerciseBlocks = PLAN_SECTION_ORDER.map((sec) => {
    const items = day.exercises.filter((e) => e.section === sec);
    if (!items.length) return null;
    return (
      <div key={sec} className="mt-3">
        <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">
          {SECTION_LABEL[sec]}
        </p>
        <ul className="space-y-2">
          {items.map((ex) => (
            <li key={ex.key} className="rounded-lg bg-white p-2.5 ring-1 ring-slate-100">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{ex.name_vi}</p>
                  <p className="text-[11px] text-slate-400">~{exMinutes(ex)}′</p>
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
                      patchDay((d) => ({
                        ...d,
                        exercises: d.exercises.filter((e) => e.key !== ex.key),
                      }))
                    }
                    className="text-xs font-semibold text-rose-500 hover:underline"
                  >
                    Xóa
                  </button>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <Stepper
                  label="Set"
                  value={ex.sets}
                  warn={overTime}
                  onDec={() => updateEx(ex.key, { sets: Math.max(1, ex.sets - 1) })}
                  onInc={() => tryIncSets(ex)}
                />
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
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  });

  const mealOpen = firstFilledMealType(day.meals);
  const mealBlocks =
    day.meals.length === 0 ? (
      <p className="text-sm text-slate-400">Chưa có món — bấm “+ Món ăn”.</p>
    ) : (
      <div>
        {MEAL_GROUP_ORDER.map((mt) => {
          const slotMeals = day.meals.filter((m) => m.meal_type === mt);
          if (!slotMeals.length) return null;
          const slotKcal = slotMeals.reduce(
            (sum, m) => sum + Math.round(m.calories_per * m.servings),
            0,
          );
          return (
            <PlanMealAccordion
              key={mt}
              title={mealGroupTitle(mt)}
              itemCount={slotMeals.length}
              kcal={slotKcal}
              defaultOpen={mealOpen === mt}
            >
              <ul className="space-y-2">
                {slotMeals.map((m) => (
                  <li key={m.key} className="rounded-lg bg-amber-50 p-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-amber-950">{m.name_vi}</p>
                        <p className="text-xs text-amber-800">
                          ~{Math.round(m.calories_per * m.servings)} kcal
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          patchDay((d) => ({
                            ...d,
                            meals: d.meals.filter((x) => x.key !== m.key),
                          }))
                        }
                        className="text-xs font-semibold text-rose-500 hover:underline"
                      >
                        Xóa
                      </button>
                    </div>
                    <div className="mt-2 max-w-[180px]">
                      <Stepper
                        label="Khẩu phần"
                        value={m.servings}
                        min={0.5}
                        warn={overCal}
                        onDec={() =>
                          updateMeal(m.key, {
                            servings: Math.max(0.5, Math.round((m.servings - 0.5) * 10) / 10),
                          })
                        }
                        onInc={() => tryIncServings(m)}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </PlanMealAccordion>
          );
        })}
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

  if (variant === "page") {
    const inputRecap = detail.insights?.inputs?.recap_vi?.trim() || null;
    const inputChips = (detail.insights?.inputs?.chips || []).filter(Boolean);
    return (
      <>
        <PlanViewShell
          title={detail.title_vi}
          recap={inputRecap}
          chips={inputChips}
          calorieLine={
            detail.target_calories != null
              ? `~${viNum(detail.target_calories)} kcal trung bình/ngày`
              : null
          }
          activeTab={activeTab}
          onTabChange={setActiveTab}
          tabs={EDITOR_TABS}
          nav={
            <PlanWeekSessionNav
              weekGroups={weekGroups}
              activeWeek={activeWeek}
              activeDayNumber={day.day_number}
              onWeekChange={(week, firstDayNumber) => {
                setActiveWeek(week);
                selectDayByNumber(firstDayNumber);
              }}
              onDayChange={selectDayByNumber}
            />
          }
        >
          {flash && (
            <p
              className={`mb-3 rounded-xl px-3 py-2 text-sm font-medium ${
                flash.startsWith("Đã lưu")
                  ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                  : "border border-amber-200 bg-amber-50 text-amber-900"
              }`}
            >
              {flash.startsWith("Đã lưu") ? flash : `⚠️ ${flash}`}
            </p>
          )}
          {err && <p className="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

          {activeTab === "train" && (
            <div className="space-y-3">
              <div
                className={`rounded-xl p-3 ring-1 ${overTime ? "bg-rose-50 ring-rose-200" : "bg-white ring-slate-100"}`}
              >
                <div className="flex items-end justify-between text-sm">
                  <span className="font-semibold text-slate-600">Thời lượng tập</span>
                  <span className={`font-extrabold ${overTime ? "text-rose-600" : "text-brand-600"}`}>
                    {usedMin}′ / {sessionMinutes}′
                  </span>
                </div>
                <div className="macro-track mt-2 h-2.5">
                  <div
                    className={overTime ? "bg-rose-500" : timePct >= 85 ? "bg-amber-400" : "bg-brand-500"}
                    style={{ width: `${Math.min(100, timePct)}%` }}
                  />
                </div>
              </div>
              <div className="rounded-2xl bg-white p-4 shadow-soft">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold">{day.title_vi || `Ngày ${day.day_number}`}</h3>
                  <div className="flex flex-wrap gap-2">
                    <select
                      value={addSection}
                      onChange={(e) => setAddSection(e.target.value as Section)}
                      className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold"
                    >
                      {PLAN_SECTION_ORDER.map((s) => (
                        <option key={s} value={s}>
                          {SECTION_LABEL[s]}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => setShowExSearch((v) => !v)}
                      className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-brand-600"
                    >
                      + Bài tập
                    </button>
                  </div>
                </div>
                {showExSearch && <ExerciseSearch excludeIds={excludeIds} onPick={addExercise} />}
                {exerciseBlocks}
                {day.exercises.length === 0 && (
                  <p className="mt-3 text-center text-sm text-slate-400">
                    Chưa có bài tập — bấm “+ Bài tập”.
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === "meals" && (
            <div className="space-y-3">
              <div
                className={`rounded-xl p-3 ring-1 ${overCal ? "bg-rose-50 ring-rose-200" : "bg-white ring-slate-100"}`}
              >
                <div className="flex items-end justify-between text-sm">
                  <span className="font-semibold text-slate-600">Calo thực đơn ngày</span>
                  <span className={`font-extrabold ${overCal ? "text-rose-600" : "text-brand-600"}`}>
                    {viNum(mealCal)}
                    {targetCal != null ? ` / ${viNum(targetCal)}` : ""} kcal
                  </span>
                </div>
                {targetCal != null && (
                  <div className="macro-track mt-2 h-2.5">
                    <div
                      className={overCal ? "bg-rose-500" : calPct >= 95 ? "bg-amber-400" : "bg-brand-500"}
                      style={{ width: `${Math.min(100, calPct)}%` }}
                    />
                  </div>
                )}
              </div>
              <div className="rounded-2xl bg-white p-4 shadow-soft">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold">Thực đơn</h3>
                  <button
                    type="button"
                    onClick={() => setShowFoodSearch((v) => !v)}
                    className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-600"
                  >
                    + Món ăn
                  </button>
                </div>
                {showFoodSearch && <FoodSearch onPick={addFood} />}
                {mealBlocks}
              </div>
            </div>
          )}

          <div className="sticky bottom-20 z-10 mt-4 flex flex-col gap-2 rounded-2xl bg-white/95 p-3 shadow-soft ring-1 ring-slate-100 sm:flex-row md:bottom-4">
            <Link
              href="/tai-khoan"
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-center text-sm font-semibold text-slate-600 hover:border-slate-300"
            >
              Hủy
            </Link>
            {canRestoreAi && (
              <button
                type="button"
                disabled={saving || restoring}
                onClick={() => void restoreAi()}
                className="flex-1 rounded-xl border border-amber-200 bg-amber-50 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
              >
                {restoring ? "Đang khôi phục…" : "Khôi phục TAPTOT gốc"}
              </button>
            )}
            <button
              type="button"
              onClick={() => void save()}
              disabled={saving}
              className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {saving ? "Đang lưu…" : overTime || overCal ? "Lưu (có cảnh báo)" : "Lưu thay đổi"}
            </button>
          </div>
        </PlanViewShell>
        {swapModal}
      </>
    );
  }

  return (
    <div className="space-y-4">
      {/* Locked plan info */}
      <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-soft">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Thông tin lịch (chỉ xem)</p>
        <h3 className="mt-1 text-lg font-extrabold text-slate-800">{detail.title_vi}</h3>
        {detail.description_vi && (
          <p className="mt-1 text-sm text-slate-600">{detail.description_vi}</p>
        )}
        <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Nguồn</p>
            <p className="font-bold text-slate-700">{SOURCE_LABEL[detail.source] || detail.source}</p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Calo mục tiêu</p>
            <p className="font-bold text-brand-700">
              {detail.target_calories != null ? `${viNum(detail.target_calories)} kcal/ngày` : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold text-slate-400">Thời lượng buổi</p>
            <p className="font-bold text-slate-700">{sessionMinutes} phút</p>
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
            {restoring ? "Đang khôi phục…" : "Khôi phục bản TAPTOT gốc"}
          </button>
        )}
      </div>

      {flash && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 animate-in">
          ⚠️ {flash}
        </p>
      )}
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      <div className="flex flex-wrap gap-2">
        {draft.map((d, i) => {
          const tOver = dayMinutes(d) > sessionMinutes;
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
                  : tOver || cOver
                    ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                    : "bg-slate-100 text-slate-600 hover:bg-brand-50"
              }`}
            >
              {d.title_vi || `Ngày ${d.day_number}`}
              {(tOver || cOver) && " !"}
            </button>
          );
        })}
      </div>

      {/* Budget meters for active day */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className={`rounded-xl p-3 ring-1 ${overTime ? "bg-rose-50 ring-rose-200" : "bg-white ring-slate-100"}`}>
          <div className="flex items-end justify-between text-sm">
            <span className="font-semibold text-slate-600">Thời lượng tập</span>
            <span className={`font-extrabold ${overTime ? "text-rose-600" : "text-brand-600"}`}>
              {usedMin}′ / {sessionMinutes}′
            </span>
          </div>
          <div className="macro-track mt-2 h-2.5">
            <div
              className={overTime ? "bg-rose-500" : timePct >= 85 ? "bg-amber-400" : "bg-brand-500"}
              style={{ width: `${Math.min(100, timePct)}%` }}
            />
          </div>
          {overTime && (
            <p className="mt-1.5 text-xs font-medium text-rose-600">
              Vượt {usedMin - sessionMinutes}′ so với thời lượng buổi đã đặt.
            </p>
          )}
        </div>
        <div className={`rounded-xl p-3 ring-1 ${overCal ? "bg-rose-50 ring-rose-200" : "bg-white ring-slate-100"}`}>
          <div className="flex items-end justify-between text-sm">
            <span className="font-semibold text-slate-600">Calo thực đơn ngày</span>
            <span className={`font-extrabold ${overCal ? "text-rose-600" : "text-brand-600"}`}>
              {viNum(mealCal)}
              {targetCal != null ? ` / ${viNum(targetCal)}` : ""} kcal
            </span>
          </div>
          {targetCal != null && (
            <div className="macro-track mt-2 h-2.5">
              <div
                className={overCal ? "bg-rose-500" : calPct >= 95 ? "bg-amber-400" : "bg-brand-500"}
                style={{ width: `${Math.min(100, calPct)}%` }}
              />
            </div>
          )}
          {overCal && targetCal != null && (
            <p className="mt-1.5 text-xs font-medium text-rose-600">
              Vượt {viNum(mealCal - targetCal)} kcal so với calo mục tiêu.
            </p>
          )}
          {day.meals.length === 0 && (
            <p className="mt-1.5 text-xs text-slate-400">Chưa có món — chưa so sánh calo.</p>
          )}
        </div>
      </div>

      <div className="rounded-xl bg-slate-50 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold">{day.title_vi || `Ngày ${day.day_number}`}</h3>
          <div className="flex flex-wrap gap-2">
            <select
              value={addSection}
              onChange={(e) => setAddSection(e.target.value as Section)}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold"
            >
              {PLAN_SECTION_ORDER.map((s) => (
                <option key={s} value={s}>
                  {SECTION_LABEL[s]}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setShowExSearch((v) => !v);
                setShowFoodSearch(false);
              }}
              className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-brand-600"
            >
              + Bài tập
            </button>
            <button
              type="button"
              onClick={() => {
                setShowFoodSearch((v) => !v);
                setShowExSearch(false);
              }}
              className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-600"
            >
              + Món ăn
            </button>
          </div>
        </div>

        {showExSearch && (
          <ExerciseSearch excludeIds={excludeIds} onPick={addExercise} />
        )}
        {showFoodSearch && <FoodSearch onPick={addFood} />}

        {exerciseBlocks}

        {day.exercises.length === 0 && (
          <p className="mt-3 text-center text-sm text-slate-400">Chưa có bài tập — bấm “+ Bài tập”.</p>
        )}

        <div className="mt-4">
          <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">Thực đơn</p>
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
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving}
          className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {saving ? "Đang lưu…" : overTime || overCal ? "Lưu (có cảnh báo)" : "Lưu thay đổi"}
        </button>
      </div>

      {swapModal}
    </div>
  );
}
