import { describe, expect, it } from "vitest";
import {
  dayNumbersForFlexibleScope,
  FLEX_MEAL_TYPE,
  inferredFlexibleScope,
  mealsForSlot,
  mealsFromDays,
} from "./mealFlexible";
import type { WeekGroup } from "./planWeeks";

describe("mealsForSlot", () => {
  it("keeps breakfast plus leftover flex items", () => {
    const meals = [
      { meal_type: "breakfast", id: 1 },
      { meal_type: FLEX_MEAL_TYPE, id: 2 },
      { meal_type: "lunch", id: 3 },
    ];
    expect(mealsForSlot(meals, "breakfast").map((m) => m.id)).toEqual([1, 2]);
    expect(mealsForSlot(meals, "lunch").map((m) => m.id)).toEqual([3]);
  });
});

describe("dayNumbersForFlexibleScope", () => {
  const days = Array.from({ length: 14 }, (_, i) => ({ day_number: i + 1 }));

  it("returns the current day", () => {
    expect(
      dayNumbersForFlexibleScope({
        days,
        weekGroups: [],
        scope: "day",
        currentDayNumber: 3,
      }),
    ).toEqual([3]);
  });

  it("chunks untitled plans by 7 days for week", () => {
    expect(
      dayNumbersForFlexibleScope({
        days,
        weekGroups: [{ week: 1, phase: null, isDeload: false, isRepeatOfWeek1: false, days: [] }],
        scope: "week",
        currentDayNumber: 8,
      }),
    ).toEqual([8, 9, 10, 11, 12, 13, 14]);
  });

  it("uses titled week groups when present", () => {
    const weekGroups: WeekGroup[] = [
      {
        week: 1,
        phase: null,
        isDeload: false,
        isRepeatOfWeek1: false,
        days: [{ day_number: 1 } as WeekGroup["days"][number], { day_number: 2 } as WeekGroup["days"][number]],
      },
      {
        week: 2,
        phase: null,
        isDeload: false,
        isRepeatOfWeek1: false,
        days: [{ day_number: 3 } as WeekGroup["days"][number]],
      },
    ];
    expect(
      dayNumbersForFlexibleScope({
        days: [{ day_number: 1 }, { day_number: 2 }, { day_number: 3 }],
        weekGroups,
        scope: "week",
        currentDayNumber: 2,
      }),
    ).toEqual([1, 2]);
  });
});

describe("mealsFromDays", () => {
  it("pools meals from week days 8–14", () => {
    const days = Array.from({ length: 14 }, (_, i) => ({
      day_number: i + 1,
      meals: [{ id: i + 1 }],
    }));
    expect(
      mealsFromDays(days, [8, 9, 10, 11, 12, 13, 14]).map((x) => x.meal.id),
    ).toEqual([8, 9, 10, 11, 12, 13, 14]);
  });
});

describe("inferredFlexibleScope", () => {
  const days = Array.from({ length: 14 }, (_, i) => ({
    day_number: i + 1,
    meals_flexible: i >= 7,
  }));
  const weekGroups: WeekGroup[] = [
    { week: 1, phase: null, isDeload: false, isRepeatOfWeek1: false, days: [] },
  ];

  it("returns week when all 7 days of the week are flexible", () => {
    expect(
      inferredFlexibleScope({ days, weekGroups, currentDayNumber: 10 }),
    ).toBe("week");
  });

  it("returns day when only the current day is flexible", () => {
    const one = days.map((d) => ({ ...d, meals_flexible: d.day_number === 10 }));
    expect(
      inferredFlexibleScope({ days: one, weekGroups, currentDayNumber: 10 }),
    ).toBe("day");
  });
});
