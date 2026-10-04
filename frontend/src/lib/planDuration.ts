export type PlanDurationUnit = "day" | "week" | "month";

export const PLAN_DURATION_MAX_DAYS = 100;

export function durationToDays(unit: PlanDurationUnit, count: number): number {
  const n = Math.max(1, Math.floor(Number(count) || 1));
  if (unit === "week") return n * 7;
  if (unit === "month") return n * 28;
  return n;
}

export function durationOverMax(unit: PlanDurationUnit, count: number): boolean {
  return durationToDays(unit, count) > PLAN_DURATION_MAX_DAYS;
}
