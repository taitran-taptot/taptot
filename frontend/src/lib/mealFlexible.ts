import type { PlanMealType } from "./plansApi";
import type { WeekGroup } from "./planWeeks";

export const FLEX_MEAL_TYPE = "flex" as const;

export type FlexibleMealScope = "day" | "week" | "month" | "plan";

export const FLEXIBLE_SCOPE_LABEL: Record<FlexibleMealScope, string> = {
  day: "Ngày này",
  week: "Tuần này",
  month: "Tháng này",
  plan: "Cả lịch",
};

export const FLEXIBLE_CALORIE_LABEL: Record<FlexibleMealScope, string> = {
  day: "Calo thực đơn ngày",
  week: "Calo thực đơn tuần",
  month: "Calo thực đơn tháng",
  plan: "Calo thực đơn lịch",
};

const SCOPE_SIZE_ORDER: FlexibleMealScope[] = ["plan", "month", "week", "day"];

export function mealsForSlot<T extends { meal_type: string }>(
  meals: T[],
  mt: PlanMealType,
): T[] {
  if (mt === "breakfast") {
    return meals.filter((m) => m.meal_type === "breakfast" || m.meal_type === FLEX_MEAL_TYPE);
  }
  return meals.filter((m) => m.meal_type === mt);
}

function titledWeeks(weekGroups: WeekGroup[]): boolean {
  return weekGroups.length > 1 || weekGroups.some((g) => g.week > 1);
}

export function dayNumbersForFlexibleScope(opts: {
  days: { day_number: number }[];
  weekGroups: WeekGroup[];
  scope: FlexibleMealScope;
  currentDayNumber: number;
}): number[] {
  const nums = opts.days.map((d) => d.day_number);
  if (opts.scope === "day") return [opts.currentDayNumber];
  if (opts.scope === "plan") return nums;

  if (opts.scope === "week") {
    if (titledWeeks(opts.weekGroups)) {
      const group = opts.weekGroups.find((g) =>
        g.days.some((d) => d.day_number === opts.currentDayNumber),
      );
      return group ? group.days.map((d) => d.day_number) : [opts.currentDayNumber];
    }
    const week = Math.ceil(opts.currentDayNumber / 7);
    return nums.filter((n) => Math.ceil(n / 7) === week);
  }

  if (titledWeeks(opts.weekGroups)) {
    const group = opts.weekGroups.find((g) =>
      g.days.some((d) => d.day_number === opts.currentDayNumber),
    );
    const week = group?.week ?? 1;
    const month = Math.ceil(week / 4);
    return opts.weekGroups
      .filter((g) => Math.ceil(g.week / 4) === month)
      .flatMap((g) => g.days.map((d) => d.day_number));
  }
  const month = Math.ceil(opts.currentDayNumber / 28);
  return nums.filter((n) => Math.ceil(n / 28) === month);
}

export function mealsFromDays<T extends { day_number: number; meals: M[] }, M>(
  days: T[],
  dayNumbers: number[],
): Array<{ dayNumber: number; meal: M }> {
  const want = new Set(dayNumbers);
  const out: Array<{ dayNumber: number; meal: M }> = [];
  for (const d of days) {
    if (!want.has(d.day_number)) continue;
    for (const meal of d.meals) out.push({ dayNumber: d.day_number, meal });
  }
  return out;
}

export function inferredFlexibleScope(opts: {
  days: { day_number: number; meals_flexible?: boolean }[];
  weekGroups: WeekGroup[];
  currentDayNumber: number;
}): FlexibleMealScope {
  const flex = new Map(opts.days.map((d) => [d.day_number, Boolean(d.meals_flexible)]));
  if (!flex.get(opts.currentDayNumber)) return "day";
  for (const scope of SCOPE_SIZE_ORDER) {
    const nums = dayNumbersForFlexibleScope({ ...opts, scope });
    if (nums.length && nums.every((n) => flex.get(n))) return scope;
  }
  return "day";
}
