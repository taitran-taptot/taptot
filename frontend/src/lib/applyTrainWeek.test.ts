import { describe, expect, it } from "vitest";
import {
  applyWeekTraining,
  trainApplyScopesForNav,
  trainApplyTargetWeekCount,
  weeksForTrainApplyScope,
} from "./applyTrainWeek";
import { groupPlanDaysByWeek } from "./planWeeks";
import type { PlanDay } from "./plansApi";

type FakeEx = { key: string; exercise_id: number; name_vi: string };
type FakeMeal = { id: number };
type FakeDay = {
  day_number: number;
  title_vi: string | null;
  meals_flexible: boolean;
  meals: FakeMeal[];
  exercises: FakeEx[];
};

function planDays(days: FakeDay[]): PlanDay[] {
  return days.map((d) => ({
    id: d.day_number,
    day_number: d.day_number,
    title_vi: d.title_vi,
    notes_vi: null,
    exercises: [],
    meals: [],
  }));
}

function makeDays(count: number): FakeDay[] {
  return Array.from({ length: count }, (_, i) => {
    const n = i + 1;
    const inWeek1 = n <= 7;
    return {
      day_number: n,
      title_vi: inWeek1 ? `Ngực ${n}` : `Khác ${n}`,
      meals_flexible: n % 2 === 0,
      meals: [{ id: n }],
      exercises: inWeek1
        ? [{ key: `w1-${n}`, exercise_id: n, name_vi: `Bài ${n}` }]
        : [{ key: `old-${n}`, exercise_id: 100 + n, name_vi: `Cũ ${n}` }],
    };
  });
}

function cloneExercise(ex: FakeEx): FakeEx {
  return { ...ex, key: `clone-${ex.key}` };
}

function apply(days: FakeDay[], sourceDayNumber: number, scope: "month" | "plan") {
  return applyWeekTraining({
    days,
    weekGroups: groupPlanDaysByWeek(planDays(days)),
    sourceDayNumber,
    scope,
    cloneExercise,
  });
}

describe("trainApplyScopesForNav", () => {
  it("hides the control for a single week", () => {
    const days = makeDays(7);
    expect(trainApplyScopesForNav(groupPlanDaysByWeek(planDays(days)))).toEqual([]);
  });

  it("only offers Cả lịch when the plan is one month", () => {
    const days = makeDays(14);
    expect(trainApplyScopesForNav(groupPlanDaysByWeek(planDays(days)))).toEqual(["plan"]);
  });

  it("offers month and plan when there are multiple months", () => {
    const days = makeDays(84);
    expect(trainApplyScopesForNav(groupPlanDaysByWeek(planDays(days)))).toEqual([
      "month",
      "plan",
    ]);
  });
});

describe("weeksForTrainApplyScope", () => {
  it("month is the four weeks of the current month on an 84-day plan", () => {
    const days = makeDays(84);
    const weekGroups = groupPlanDaysByWeek(planDays(days));
    expect(
      weeksForTrainApplyScope({
        weekGroups,
        currentDayNumber: 30,
        scope: "month",
      }).map((g) => g.week),
    ).toEqual([5, 6, 7, 8]);
  });
});

describe("applyWeekTraining", () => {
  it("copies week 1 training onto week 2 for a 14-day plan", () => {
    const next = apply(makeDays(14), 1, "plan");
    expect(next.slice(0, 7).map((d) => d.title_vi)).toEqual(
      makeDays(14).slice(0, 7).map((d) => d.title_vi),
    );
    expect(next[0].exercises[0].key).toBe("w1-1");
    expect(next[7].title_vi).toBe("Ngực 1");
    expect(next[7].exercises).toEqual([{ key: "clone-w1-1", exercise_id: 1, name_vi: "Bài 1" }]);
    expect(next[13].title_vi).toBe("Ngực 7");
    expect(next[13].exercises[0].exercise_id).toBe(7);
  });

  it("leaves meals and meals_flexible untouched", () => {
    const next = apply(makeDays(14), 1, "plan");
    expect(next[7].meals).toEqual([{ id: 8 }]);
    expect(next[7].meals_flexible).toBe(true);
    expect(next[8].meals).toEqual([{ id: 9 }]);
    expect(next[8].meals_flexible).toBe(false);
  });

  it("month scope on 84 days only overwrites the other weeks in that month", () => {
    const next = apply(makeDays(84), 1, "month");
    expect(next[7].title_vi).toBe("Ngực 1");
    expect(next[27].title_vi).toBe("Ngực 7");
    expect(next[28].title_vi).toBe("Khác 29");
    expect(next[28].exercises[0].exercise_id).toBe(129);
  });

  it("short last week only receives matching weekday slots", () => {
    const next = apply(makeDays(10), 1, "plan");
    expect(next[7].title_vi).toBe("Ngực 1");
    expect(next[8].title_vi).toBe("Ngực 2");
    expect(next[9].title_vi).toBe("Ngực 3");
    expect(next).toHaveLength(10);
  });
});

describe("trainApplyTargetWeekCount", () => {
  it("counts weeks besides the source", () => {
    const days = makeDays(14);
    const weekGroups = groupPlanDaysByWeek(planDays(days));
    expect(
      trainApplyTargetWeekCount({
        weekGroups,
        currentDayNumber: 1,
        scope: "plan",
      }),
    ).toBe(1);
  });
});
