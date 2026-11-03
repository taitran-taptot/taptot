import { describe, expect, it } from "vitest";
import type { PlanDay, PlanExercise } from "./plansApi";
import {
  clusterWeeksByMonth,
  groupPlanDaysByWeek,
  monthOfWeek,
  repeatSourceLabel,
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

  it("marks week 3 as a repeat of week 1, month 1", () => {
    const lift = (id: number, exerciseId: number): PlanExercise => ({
      id,
      exercise_id: exerciseId,
      name_vi: "Squat",
      name_en: null,
      body_part: null,
      gif_url: null,
      section: "main",
      sets: 3,
      reps: "8-12",
      rest_seconds: 90,
      sort_order: 1,
      notes_vi: null,
    });
    const days = [
      { ...fakeDay(1, "Tuần 1 · Giai đoạn 1"), exercises: [lift(1, 10)] },
      { ...fakeDay(2, "Tuần 2 · Giai đoạn 1"), exercises: [lift(2, 99)] },
      { ...fakeDay(3, "Tuần 3 · Giai đoạn 1"), exercises: [lift(3, 10)] },
    ];
    const groups = groupPlanDaysByWeek(days);
    expect(groups[0].isRepeatOfWeek1).toBe(false);
    expect(groups[0].repeatSourceWeek).toBeNull();
    expect(groups[1].isRepeatOfWeek1).toBe(false);
    expect(groups[2].isRepeatOfWeek1).toBe(true);
    expect(groups[2].repeatSourceWeek).toBe(1);
    expect(repeatSourceLabel(groups[2].repeatSourceWeek!)).toBe("tuần 1, tháng 1");
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
