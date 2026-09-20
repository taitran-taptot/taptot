import { describe, expect, it } from "vitest";
import { splitCoachLines } from "./exerciseCopy";

describe("splitCoachLines", () => {
  it("splits newline lists", () => {
    expect(splitCoachLines("Gối sụp vào trong.\nGót nhấc.")).toEqual([
      "Gối sụp vào trong.",
      "Gót nhấc.",
    ]);
  });

  it("parses a python list leftover", () => {
    expect(
      splitCoachLines("['Cong lưng khi nâng.', 'Kéo tạ lên mà không kéo căng trước.']"),
    ).toEqual(["Cong lưng khi nâng.", "Kéo tạ lên mà không kéo căng trước."]);
  });

  it("returns empty for blank input", () => {
    expect(splitCoachLines("  ")).toEqual([]);
    expect(splitCoachLines(null)).toEqual([]);
  });
});
