import type { PlanDetail, PlanExercise, PlanSectionKey, UpdatePlanDayPayload } from "./plansApi";
import type { ExerciseListItem } from "./types";

type Section = PlanSectionKey;
type MealType = "breakfast" | "lunch" | "dinner" | "snack";

/** Map full plan detail → API update payload (exercises + meals only). */
export function planToUpdatePayload(plan: PlanDetail): UpdatePlanDayPayload[] {
  return plan.days.map((day) => ({
    day_number: day.day_number,
    exercises: day.exercises.map((ex) => ({
      exercise_id: ex.exercise_id,
      sets: ex.sets,
      reps: ex.reps,
      section: (ex.section || "main") as Section,
      rest_seconds: ex.rest_seconds,
      sort_order: ex.sort_order,
    })),
    meals: day.meals.map((m) => ({
      food_id: m.food_id,
      meal_type: (m.meal_type || "lunch") as MealType,
      servings: m.servings,
      sort_order: m.sort_order,
    })),
  }));
}

/** Replace one exercise row (by plan exercise row id) and return full update payload. */
export function swapExerciseInPlan(
  plan: PlanDetail,
  dayNumber: number,
  planExerciseId: number,
  alt: ExerciseListItem,
): UpdatePlanDayPayload[] {
  const payload = planToUpdatePayload(plan);
  const dayIdx = plan.days.findIndex((d) => d.day_number === dayNumber);
  if (dayIdx < 0) return payload;

  const origDay = plan.days[dayIdx];
  const exIdx = origDay.exercises.findIndex((e) => e.id === planExerciseId);
  if (exIdx < 0) return payload;

  const dayPayload = payload[dayIdx];
  dayPayload.exercises = dayPayload.exercises.map((ex, i) =>
    i === exIdx ? { ...ex, exercise_id: alt.id } : ex,
  );
  return payload;
}

export type SwapExerciseContext = Pick<
  PlanExercise,
  "id" | "exercise_id" | "name_vi" | "sets" | "reps" | "section" | "rest_seconds"
>;

export type ExerciseAltContext = {
  location?: string | null;
  no_equipment?: boolean;
  equipment_list?: string[];
};

export function altContextFromPlanInputs(
  inputs?: { location?: string | null; no_equipment?: boolean; equipment_list?: string[] } | null,
): ExerciseAltContext | undefined {
  if (!inputs) return undefined;
  const location = (inputs.location || "").trim() || undefined;
  const equipment_list = (inputs.equipment_list || []).map((s) => s.trim()).filter(Boolean);
  if (!location && inputs.no_equipment == null && equipment_list.length === 0) {
    return undefined;
  }
  return {
    location: location ?? null,
    no_equipment: Boolean(inputs.no_equipment),
    equipment_list,
  };
}
