import { describe, expect, it } from "vitest";
import {
  formatSetsReps,
  localizeWorkoutCopy,
  splitRoleLabel,
  splitRoleShortLabel,
} from "./planLabels";

describe("formatSetsReps foundation", () => {
  it("does not append lần to descriptive test goals", () => {
    expect(
      formatSetsReps(1, "Mục tiêu 1–2 kéo xà hoặc 6–10 inverted row", {
        foundation: true,
      }),
    ).toBe("1 hiệp × Mục tiêu 1–2 kéo xà hoặc 6–10 kéo người nằm (bàn/xà)");
  });

  it("still appends lần to numeric reps", () => {
    expect(formatSetsReps(3, "8–12", { foundation: true })).toBe("3 hiệp × 8–12 lần");
  });

  it("leaves non-foundation copy unchanged", () => {
    expect(formatSetsReps(1, "Mục tiêu 6–10 inverted row")).toBe(
      "1 hiệp × Mục tiêu 6–10 inverted row lần",
    );
  });
});

describe("localizeWorkoutCopy", () => {
  it("replaces inverted row and RIR", () => {
    expect(localizeWorkoutCopy("RIR 3 · inverted row")).toBe(
      "còn dư 3 cái · kéo người nằm (bàn/xà)",
    );
  });
});

describe("splitRoleLabel", () => {
  it("labels advanced fitness test and session letters", () => {
    expect(splitRoleLabel("test")).toBe("Tốt nghiệp");
    expect(splitRoleLabel("A")).toBe("Đẩy + plank");
    expect(splitRoleLabel("recovery")).toBe("Phục hồi / giãn cơ");
  });
});

describe("splitRoleShortLabel", () => {
  it("drops parenthetical muscle groups and slash suffixes", () => {
    expect(splitRoleShortLabel("push")).toBe("Đẩy");
    expect(splitRoleShortLabel("pull")).toBe("Kéo");
    expect(splitRoleShortLabel("legs")).toBe("Chân");
    expect(splitRoleShortLabel("upper")).toBe("Thân trên");
    expect(splitRoleShortLabel("recovery")).toBe("Phục hồi");
  });
});
