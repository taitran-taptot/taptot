import { describe, expect, it } from "vitest";
import {
  formatExerciseCue,
  formatSetPrescriptionLine,
  formatCollapsedSetPrescriptions,
  formatSetPrescriptionsReps,
  groupExercisesForDisplay,
  isDropsetExercise,
  nextSupersetGroup,
  shouldShowDropsetTitle,
  supersetSlotLabel,
} from "./exerciseCues";

describe("formatExerciseCue", () => {
  it("joins RPE, RIR, and tempo", () => {
    expect(formatExerciseCue({ rpe: 8, rir: 2, tempo: "3-1-1-0" })).toBe(
      "RPE 8 · RIR 2 · Tempo 3-1-1-0",
    );
  });

  it("returns null when empty", () => {
    expect(formatExerciseCue({})).toBeNull();
  });
});

describe("formatSetPrescriptionLine", () => {
  it("uses hiệp and lần, keeps RPE RIR", () => {
    expect(
      formatSetPrescriptionLine(
        { reps: "5", rpe: 8, rir: 5, technique: "drop_set" },
        0,
      ),
    ).toBe("Hiệp 1 · 5 lần · RPE 8 · RIR 5");
  });

  it("labels later sets without repeating empty cues", () => {
    expect(formatSetPrescriptionLine({ reps: "3" }, 2)).toBe("Hiệp 3 · 3 lần");
  });

  it("does not double-prefix an existing Gợi ý note", () => {
    expect(
      formatSetPrescriptionLine({ reps: "12", load_note_vi: "Gợi ý: 15kg" }, 0),
    ).toBe("Hiệp 1 · 12 lần · Gợi ý: 15kg");
  });

  it("puts rest before the load suggestion", () => {
    expect(
      formatSetPrescriptionLine(
        { reps: "19-24", rest_seconds: 90, load_note_vi: "Dây đen · 30 lbs" },
        0,
      ),
    ).toBe("Hiệp 1 · 19-24 lần · nghỉ 1 phút 30 giây · Gợi ý: Dây đen · 30 lbs");
  });
});

describe("formatCollapsedSetPrescriptions", () => {
  it("joins uniform sets into one line", () => {
    expect(
      formatCollapsedSetPrescriptions([
        { reps: "21-24", rest_seconds: 60, load_note_vi: "Dây xanh dương · 20 lbs" },
        { reps: "21-24", rest_seconds: 60, load_note_vi: "Dây xanh dương · 20 lbs" },
        { reps: "21-24", rest_seconds: 60, load_note_vi: "Dây xanh dương · 20 lbs" },
      ]),
    ).toBe("3 Hiệp · 21-24 lần · nghỉ 60 giây · Gợi ý: Dây xanh dương · 20 lbs");
  });

  it("puts rest before dumbbell or band load hints", () => {
    expect(
      formatCollapsedSetPrescriptions([
        { reps: "19-24", rest_seconds: 90, load_note_vi: "Gợi ý: Dây đen · 30 lbs" },
        { reps: "19-24", rest_seconds: 90, load_note_vi: "Gợi ý: Dây đen · 30 lbs" },
        { reps: "19-24", rest_seconds: 90, load_note_vi: "Gợi ý: Dây đen · 30 lbs" },
      ]),
    ).toBe("3 Hiệp · 19-24 lần · nghỉ 1 phút 30 giây · Gợi ý: Dây đen · 30 lbs");
  });
});

describe("formatSetPrescriptionsReps", () => {
  it("joins reps with slashes", () => {
    expect(formatSetPrescriptionsReps([{ reps: "12" }, { reps: "10" }, { reps: "8" }])).toBe(
      "12 / 10 / 8",
    );
  });
});

describe("groupExercisesForDisplay", () => {
  it("pairs consecutive super-set rows as A1/A2", () => {
    const items = [
      { name: "a", technique: "super_set", superset_group: 1 },
      { name: "b", technique: "super_set", superset_group: 1 },
      { name: "c", technique: "drop_set" },
    ];
    const blocks = groupExercisesForDisplay(items);
    expect(blocks[0]).toMatchObject({ kind: "superset", letter: "A" });
    if (blocks[0].kind === "superset") {
      expect(blocks[0].exercises.map((e) => e.name)).toEqual(["a", "b"]);
    }
    expect(blocks[1]).toMatchObject({ kind: "dropset" });
  });

  it("marks dropset when only a set uses the technique", () => {
    expect(
      isDropsetExercise({
        set_prescriptions: [{ reps: "12", technique: "drop_set" }],
      }),
    ).toBe(true);
    expect(
      shouldShowDropsetTitle({
        technique: "super_set",
        set_prescriptions: [{ reps: "12", technique: "drop_set" }],
      }),
    ).toBe(false);
  });

  it("leaves a dangling super-set as a single row", () => {
    const blocks = groupExercisesForDisplay([
      { technique: "super_set", superset_group: 1 },
      { technique: null },
    ]);
    expect(blocks.every((b) => b.kind === "single")).toBe(true);
  });
});

describe("supersetSlotLabel", () => {
  it("labels A1 then A2", () => {
    const items = [
      { technique: "super_set" as const, superset_group: 1 },
      { technique: "super_set" as const, superset_group: 1 },
    ];
    expect(supersetSlotLabel(items, 0)).toBe("A1");
    expect(supersetSlotLabel(items, 1)).toBe("A2");
  });
});

describe("nextSupersetGroup", () => {
  it("increments from the max group", () => {
    expect(nextSupersetGroup([{ superset_group: 2 }, { superset_group: 1 }])).toBe(3);
  });
});
