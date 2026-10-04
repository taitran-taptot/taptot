import { describe, expect, it } from "vitest";
import { durationOverMax, durationToDays } from "./planDuration";

describe("planDuration", () => {
  it("converts week and month to blank days", () => {
    expect(durationToDays("day", 5)).toBe(5);
    expect(durationToDays("week", 2)).toBe(14);
    expect(durationToDays("month", 1)).toBe(28);
    expect(durationToDays("month", 3)).toBe(84);
  });

  it("caps at 100 days", () => {
    expect(durationOverMax("month", 4)).toBe(true);
    expect(durationOverMax("week", 14)).toBe(false);
    expect(durationOverMax("week", 15)).toBe(true);
  });
});
