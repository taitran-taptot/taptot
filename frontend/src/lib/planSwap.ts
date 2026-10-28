import type { PlanExercise } from "./plansApi";

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
