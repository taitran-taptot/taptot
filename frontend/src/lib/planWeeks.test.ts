import { describe, expect, it } from "vitest";
import type { PlanDay } from "./plansApi";
import {
  clusterWeeksByMonth,
  groupPlanDaysByWeek,
  monthOfWeek,
  weekIndexInMonth,
} from "./planWeeks";

function fakeDay(n: number, title: string): PlanDay {
  return {
    id: n,
    day_number: n,
    title_vi: title,
    notes_vi: null,
    exercises: [],
    meals: [],
  };
}

describe("groupPlanDaysByWeek", () => {
  it("chunks untitled 14-day plans into two weeks of 7", () => {
    const days = Array.from({ length: 14 }, (_, i) => fakeDay(i + 1, `Ngày ${i + 1}`));
    const groups = groupPlanDaysByWeek(days);
    expect(groups.map((g) => g.week)).toEqual([1, 2]);
    expect(groups[0].days.map((d) => d.day_number)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(groups[1].days.map((d) => d.day_number)).toEqual([8, 9, 10, 11, 12, 13, 14]);
  });

  it("chunks 84 untitled days into 12 weeks", () => {
    const days = Array.from({ length: 84 }, (_, i) => fakeDay(i + 1, `Ngày ${i + 1}`));
    const groups = groupPlanDaysByWeek(days);
    expect(groups).toHaveLength(12);
    expect(groups[0].days).toHaveLength(7);
    expect(groups[11].days.map((d) => d.day_number)).toEqual([78, 79, 80, 81, 82, 83, 84]);
  });

  it("keeps a short last week when day count is not a multiple of 7", () => {
    const days = Array.from({ length: 10 }, (_, i) => fakeDay(i + 1, `Ngày ${i + 1}`));
    const groups = groupPlanDaysByWeek(days);
    expect(groups.map((g) => g.week)).toEqual([1, 2]);
    expect(groups[1].days.map((d) => d.day_number)).toEqual([8, 9, 10]);
  });
  it("keeps titled Tuần N buckets", () => {
    const days = [
      fakeDay(1, "Tuần 1 · Ngực"),
      fakeDay(2, "Tuần 1 · Lưng"),
      fakeDay(3, "Tuần 2 · Chân"),
    ];
    const groups = groupPlanDaysByWeek(days);
    expect(groups.map((g) => g.week)).toEqual([1, 2]);
    expect(groups[0].days.map((d) => d.day_number)).toEqual([1, 2]);
    expect(groups[1].days.map((d) => d.day_number)).toEqual([3]);
  });
});

describe("clusterWeeksByMonth", () => {
  it("maps 12 weeks of a 3-month plan into 3 months of 4 weeks", () => {
    const days = Array.from({ length: 84 }, (_, i) => fakeDay(i + 1, `Ngày ${i + 1}`));
    const months = clusterWeeksByMonth(groupPlanDaysByWeek(days));
    expect(months.map((m) => m.month)).toEqual([1, 2, 3]);
    expect(months.map((m) => m.weeks.length)).toEqual([4, 4, 4]);
    expect(months[1].weeks.map((w) => w.week)).toEqual([5, 6, 7, 8]);
    expect(months[1].weeks.map((w) => weekIndexInMonth(w.week))).toEqual([1, 2, 3, 4]);
  });

  it("keeps titled weeks then groups four weeks per month", () => {
    const days = Array.from({ length: 8 }, (_, i) =>
      fakeDay(i + 1, `Tuần ${i + 1} · Buổi 1`),
    );
    const months = clusterWeeksByMonth(groupPlanDaysByWeek(days));
    expect(months.map((m) => m.month)).toEqual([1, 2]);
    expect(months[1].weeks.map((w) => w.week)).toEqual([5, 6, 7, 8]);
    expect(weekIndexInMonth(5)).toBe(1);
    expect(monthOfWeek(5)).toBe(2);
  });
});
