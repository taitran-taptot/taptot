import { describe, expect, it } from "vitest";
import {
  formatSetsReps,
  localizeWorkoutCopy,
  planDayNavLabel,
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

describe("planDayNavLabel", () => {
  it("uses custom titles for empty rest days", () => {
    expect(planDayNavLabel({ day_number: 1, title_vi: "Ngực", exercises: [] }, 0)).toBe("Ngực");
    expect(planDayNavLabel({ day_number: 2, title_vi: "Lưng", exercises: [] }, 1)).toBe("Lưng");
    expect(planDayNavLabel({ day_number: 3, title_vi: "Ngày 3", exercises: [] }, 2)).toBe("Ngày 3");
  });

  it("falls back to Ngày nghỉ when empty and untitled", () => {
    expect(planDayNavLabel({ day_number: 1, title_vi: "", exercises: [] }, 0)).toBe("Ngày nghỉ");
  });

  it("keeps sequential Ngày N on manual plans even at day 57/59", () => {
    expect(
      planDayNavLabel(
        { day_number: 57, title_vi: "Ngày 57", exercises: [] },
        0,
        { sequential: true },
      ),
    ).toBe("Ngày 57");
    expect(
      planDayNavLabel(
        { day_number: 59, title_vi: "Ngày 59", exercises: [] },
        2,
        { sequential: true },
      ),
    ).toBe("Ngày 59");
  });

  it("still remaps AI test days without sequential", () => {
    expect(
      planDayNavLabel({ day_number: 57, title_vi: "Ngày 57", exercises: [] }, 0),
    ).toBe("Chuẩn bị trước khi kiểm tra");
  });

  it("keeps AI Buổi N chips", () => {
    expect(
      planDayNavLabel(
        { day_number: 1, title_vi: "Tuần 1 · Buổi 1 · Đẩy", exercises: [{ length: 1 }] },
        0,
      ),
    ).toBe("Buổi 1");
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
