import { describe, expect, it } from "vitest";
import { MEAL_GROUP_ORDER, MEAL_LABEL, snackMealType } from "./plansApi";

describe("snack meal slots", () => {
  it("names snack 1 and snack 2", () => {
    expect(MEAL_LABEL.snack).toBe("Bữa phụ 1");
    expect(MEAL_LABEL.snack_2).toBe("Bữa phụ 2");
    expect(MEAL_GROUP_ORDER).toContain("snack_2");
    expect(MEAL_LABEL.flex).toBe("Linh hoạt");
  });

  it("maps bucket index to meal_type", () => {
    expect(snackMealType(0)).toBe("snack");
    expect(snackMealType(1)).toBe("snack_2");
  });
});
