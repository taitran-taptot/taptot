import { describe, expect, it } from "vitest";
import { isFamiliarizationPlan } from "./isFamiliarizationPlan";

describe("isFamiliarizationPlan", () => {
  it("detects generation_mode", () => {
    expect(
      isFamiliarizationPlan({
        insights: { generation_mode: "familiarization" },
      } as never),
    ).toBe(true);
  });

  it("detects generator/path fallbacks", () => {
    expect(
      isFamiliarizationPlan({
        insights: { generator: "familiarization_rules_v1" },
      } as never),
    ).toBe(true);
    expect(
      isFamiliarizationPlan({
        insights: { familiarization_path: "first_push_pull" },
      } as never),
    ).toBe(true);
    expect(isFamiliarizationPlan({ insights: { generation_mode: "free_home" } } as never)).toBe(
      false,
    );
  });
});
