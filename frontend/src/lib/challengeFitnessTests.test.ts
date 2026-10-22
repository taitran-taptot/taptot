import { describe, expect, it } from "vitest";
import type { ExerciseListItem } from "./types";
import {
  BAND_LEVEL_OPTS,
  DB_EACH_SIDE_OPTS,
  DB_SQUAT_OPTS,
  EMPTY_CHALLENGE_TEST_DRAFT,
  buildChallengeFitnessBaseline,
  challengeFitnessSummaryLines,
  challengeFitnessTests,
  challengeTestsComplete,
  kitFromWizardEquipment,
  pickChallengeExercise,
  type ChallengeTestDraft,
} from "./challengeFitnessTests";

function draft(patch: Partial<ChallengeTestDraft> = {}): ChallengeTestDraft {
  return { ...EMPTY_CHALLENGE_TEST_DRAFT, ...patch };
}

function ex(partial: Partial<ExerciseListItem> & Pick<ExerciseListItem, "id" | "name_en" | "name_vi">): ExerciseListItem {
  return {
    body_part: "chest",
    equipment: "",
    difficulty: 1,
    gif_url: null,
    is_beginner_friendly: true,
    ...partial,
  };
}

describe("DB kg ladders", () => {
  it("uses the 40 kg adjustable kit steps", () => {
    expect(DB_EACH_SIDE_OPTS.map((o) => o.value)).toEqual([
      "",
      "2.5",
      "5",
      "7.5",
      "10",
      "12.5",
      "15",
      "17.5",
    ]);
    expect(DB_SQUAT_OPTS.map((o) => o.value).at(-1)).toBe("35");
    expect(DB_SQUAT_OPTS.some((o) => o.value === "40")).toBe(false);
    expect(DB_EACH_SIDE_OPTS.some((o) => o.value === "20")).toBe(false);
  });
});

describe("BAND_LEVEL_OPTS", () => {
  it("lists the five tube colors", () => {
    expect(BAND_LEVEL_OPTS.map((o) => o.value)).toEqual([
      "",
      "yellow",
      "red",
      "blue",
      "green",
      "black",
    ]);
  });
});

describe("kitFromWizardEquipment", () => {
  it("maps wizard groups", () => {
    expect(kitFromWizardEquipment(["dumbbell"])).toBe("dumbbell");
    expect(kitFromWizardEquipment(["resistance-band"])).toBe("band");
    expect(kitFromWizardEquipment(["pull-up-bar", "gymnastic-rings"])).toBe("bar_rings");
  });
});

describe("challengeFitnessTests matrix", () => {
  it("band L1 and L3 use Band Chest Press and seated pulldown", () => {
    const l1 = challengeFitnessTests({ kit: "band", level: 1, gender: "male" });
    const l3 = challengeFitnessTests({ kit: "band", level: 3, gender: "female" });
    for (const tests of [l1, l3]) {
      expect(tests.map((t) => t.slot)).toEqual(["push", "pull", "core", "squat"]);
      expect(tests[0].id).toBe("band_chest_press");
      expect(tests[0].catalogNameEn).toBe("Band Chest Press");
      expect(tests[0].regression).toBeUndefined();
      expect(tests[0].showBandLevel).toBe(true);
      expect(tests[0].pushupVariant).toBe("band_press");
      expect(tests[1].catalogNameEn).toBe("Band Seated Pulldown");
      expect(tests[1].titleVi.toLowerCase()).toContain("kéo xô");
      expect(tests[1].showBandLevel).toBe(true);
      expect(tests[1].regression).toBeUndefined();
      expect(tests[3].showBandLevel).toBe(true);
    }
  });

  it("dumbbell L1 and L3 both use bench press + bilateral row + goblet kg required", () => {
    const l1 = challengeFitnessTests({ kit: "dumbbell", level: 1, gender: "male" });
    const l3 = challengeFitnessTests({ kit: "dumbbell", level: 3, gender: "female" });
    for (const tests of [l1, l3]) {
      expect(tests[0].id).toBe("db_press");
      expect(tests[0].catalogNameEn).toBe("Dumbbell Bench Press");
      expect(tests[0].catalogNameVi).toBe("Đẩy ngực tạ đơn");
      expect(tests[0].kgPreset).toBe("each_side");
      expect(tests[1].id).toBe("db_bilateral_row");
      expect(tests[1].catalogNameEn).toBe("Dumbbell Row Bilateral");
      expect(tests[1].catalogNameVi).toBe("Chèo tạ đơn hai tay");
      expect(tests[1].kgPreset).toBe("each_side");
      expect(tests[3].id).toBe("goblet_squat");
      expect(tests[3].kgPreset).toBe("squat_total");
      expect(tests[3].kgOptional).toBeFalsy();
      expect(tests.some((t) => t.id === "pullup")).toBe(false);
      expect(tests.some((t) => t.catalogNameEn === "Floor Press")).toBe(false);
    }
  });

  it("bar rings uses floor push-up, pull-up, plank, squat with no regression tabs", () => {
    const combos = [
      { level: 1, gender: "male" as const },
      { level: 1, gender: "female" as const },
      { level: 2, gender: "male" as const },
      { level: 3, gender: "female" as const },
    ];
    for (const opts of combos) {
      const tests = challengeFitnessTests({ kit: "bar_rings", ...opts });
      expect(tests[0].id).toBe("floor_pushup");
      expect(tests[0].catalogNameEn).toBe("Push Up");
      expect(tests[0].regression).toBeUndefined();
      expect(tests[1].id).toBe("bar_pullup");
      expect(tests[1].catalogNameEn).toBe("Pull Ups");
      expect(tests[1].catalogNameVi).toBe("Kéo xà");
      expect(tests[1].pullTestVariant).toBe("strict");
      expect(tests[1].regression).toBeUndefined();
      expect(tests.some((t) => t.id === "bar_hang")).toBe(false);
      expect(tests.some((t) => t.id === "knee_pushup_regression")).toBe(false);
      expect(tests.some((t) => t.id === "ring_row")).toBe(false);
    }
  });
});

describe("pickChallengeExercise", () => {
  it("prefers exact Dumbbell Bench Press over fly and neutral-grip", () => {
    const tests = challengeFitnessTests({ kit: "dumbbell", level: 3, gender: "male" });
    const press = tests[0];
    const picked = pickChallengeExercise(
      [
        ex({ id: 1, name_en: "Dumbbell Fly", name_vi: "Mở ngực tạ đơn" }),
        ex({ id: 63, name_en: "Dumbbell Bench Press", name_vi: "Đẩy ngực tạ đơn" }),
        ex({
          id: 90,
          name_en: "Neutral-Grip Dumbbell Bench Press",
          name_vi: "Ép ngực tạ đơn nắm dọc",
        }),
      ],
      press,
    );
    expect(picked?.id).toBe(63);
  });

  it("prefers exact Push Up over elevated and knee variants", () => {
    const tests = challengeFitnessTests({ kit: "bar_rings", level: 2, gender: "male" });
    const push = tests[0];
    const picked = pickChallengeExercise(
      [
        ex({ id: 86, name_en: "Bodyweight Knee Push Ups", name_vi: "Chống đẩy chống gối" }),
        ex({ id: 81, name_en: "Push Up", name_vi: "Chống đẩy" }),
        ex({ id: 200, name_en: "Bodyweight Elevated Push Up", name_vi: "Chống đẩy tay cao" }),
      ],
      push,
    );
    expect(picked?.id).toBe(81);
  });

  it("prefers Pull Ups over scapular and 1/3 variants", () => {
    const tests = challengeFitnessTests({ kit: "bar_rings", level: 1, gender: "female" });
    const pull = tests[1];
    const picked = pickChallengeExercise(
      [
        ex({ id: 113, name_en: "1/3 Pull-up", name_vi: "Kéo xà 1/3" }),
        ex({ id: 321, name_en: "Pull Ups", name_vi: "Kéo xà" }),
        ex({ id: 104, name_en: "Scapular Pull-up", name_vi: "Kéo xà bằng bả vai" }),
      ],
      pull,
    );
    expect(picked?.id).toBe(321);
  });

});

describe("challengeFitnessSummaryLines", () => {
  it("folds band level into the same four lines", () => {
    expect(
      challengeFitnessSummaryLines(
        "band",
        draft({
          pushups: "4",
          pullups: "5",
          plankSeconds: "21",
          squats: "22",
          bandLevelPush: "red",
          bandLevelPull: "red",
          bandLevelSquat: "green",
        }),
        "male",
        1,
      ),
    ).toEqual([
      "Đẩy ngực dây: 4 cái · mức dây Đỏ · 15 lbs",
      "Kéo xô ngồi (dây): 5 cái · mức dây Đỏ · 15 lbs",
      "Plank: 21 giây",
      "Squat với dây: 22 cái · mức dây Xanh lá · 25 lbs",
    ]);
  });

  it("folds dumbbell kg into the same four lines", () => {
    expect(
      challengeFitnessSummaryLines(
        "dumbbell",
        draft({
          dbPressReps: "8",
          dbPressKg: "10",
          dbRowReps: "10",
          dbRowKg: "12.5",
          plankSeconds: "30",
          gobletReps: "12",
          gobletKg: "20",
        }),
        "male",
        1,
      ),
    ).toEqual([
      "Đẩy ngực tạ đơn: 8 cái · mức tạ 10 kg mỗi tay",
      "Chèo tạ đơn hai tay: 10 cái · mức tạ 12.5 kg mỗi tay",
      "Plank: 30 giây",
      "Goblet squat: 12 cái · mức tạ 20 kg một quả",
    ]);
  });

  it("shows only reps for bar and rings", () => {
    expect(
      challengeFitnessSummaryLines(
        "bar_rings",
        draft({
          pushups: "12",
          pullups: "6",
          plankSeconds: "40",
          squats: "20",
        }),
        "male",
        1,
      ),
    ).toEqual([
      "Chống đẩy: 12 cái",
      "Kéo xà: 6 cái",
      "Plank: 40 giây",
      "Squat thể trọng: 20 cái",
    ]);
  });
});

describe("buildChallengeFitnessBaseline", () => {
  it("sends db press/row/goblet for dumbbell kit", () => {
    const base = buildChallengeFitnessBaseline({
      kit: "dumbbell",
      level: 1,
      gender: "female",
      values: draft({
        plankSeconds: "45",
        dbPressReps: "12",
        dbPressKg: "10",
        dbRowReps: "10",
        dbRowKg: "12",
        gobletReps: "15",
        gobletKg: "16",
      }),
    });
    expect(base.test_kit).toBe("dumbbell");
    expect(base.db_press_reps).toBe(12);
    expect(base.db_press_kg).toBe(10);
    expect(base.db_row_reps).toBe(10);
    expect(base.goblet_kg).toBe(16);
    expect(base.pullups_max).toBeUndefined();
  });

  it("prefers standard push-up and pull-up when hard reps > 0", () => {
    const base = buildChallengeFitnessBaseline({
      kit: "bar_rings",
      level: 1,
      gender: "female",
      values: draft({
        pushups: "12",
        kneePushups: "20",
        pullups: "4",
        invertedRows: "10",
      }),
    });
    expect(base.pushup_variant).toBe("standard");
    expect(base.pushups_max).toBe(12);
    expect(base.pull_test_variant).toBe("strict");
    expect(base.pullups_max).toBe(4);
    expect(base.inverted_rows_max).toBeUndefined();
  });

  it("does not map knee or ring-row values on the bar+rings kit", () => {
    const base = buildChallengeFitnessBaseline({
      kit: "bar_rings",
      level: 2,
      gender: "male",
      values: draft({
        kneePushups: "8",
        invertedRows: "6",
      }),
    });
    expect(base.pushup_variant).toBe("standard");
    expect(base.pushups_max).toBeNull();
    expect(base.pull_test_variant).toBe("strict");
    expect(base.inverted_rows_max).toBeUndefined();
    expect(base.pullups_max).toBeNull();
  });

  it("maps band chest press reps onto pushups_max with band_press variant", () => {
    const base = buildChallengeFitnessBaseline({
      kit: "band",
      level: 1,
      gender: "male",
      values: draft({
        pushups: "15",
        pullups: "12",
        plankSeconds: "40",
        squats: "20",
        bandLevelPush: "blue",
        bandLevelPull: "red",
        bandLevelSquat: "green",
      }),
    });
    expect(base.test_kit).toBe("band");
    expect(base.pushup_variant).toBe("band_press");
    expect(base.pushups_max).toBe(15);
    expect(base.band_level_push).toBe("blue");
    expect(base.band_level_pull).toBe("red");
    expect(base.band_level_squat).toBe("green");
    expect(base.band_level).toBe("red");
  });
});

describe("challengeTestsComplete", () => {
  it("requires all four slots; knee or ring-row values do not complete bar+rings", () => {
    const base = {
      kit: "bar_rings" as const,
      level: 1,
      gender: "female" as const,
    };
    expect(challengeTestsComplete({ ...base, values: draft() })).toBe(false);
    expect(
      challengeTestsComplete({
        ...base,
        values: draft({
          kneePushups: "8",
          invertedRows: "6",
          plankSeconds: "40",
          squats: "20",
        }),
      }),
    ).toBe(false);
    expect(
      challengeTestsComplete({
        ...base,
        values: draft({
          pushups: "10",
          pullups: "3",
          plankSeconds: "40",
          squats: "20",
        }),
      }),
    ).toBe(true);
  });

  it("requires kg on dumbbell press, row, and goblet at every level", () => {
    const filled = draft({
      dbPressReps: "12",
      dbPressKg: "10",
      dbRowReps: "10",
      dbRowKg: "12",
      plankSeconds: "40",
      gobletReps: "15",
    });
    expect(
      challengeTestsComplete({ kit: "dumbbell", level: 1, gender: "male", values: filled }),
    ).toBe(false);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 1,
        gender: "male",
        values: draft({ ...filled, gobletKg: "20" }),
      }),
    ).toBe(true);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 1,
        gender: "male",
        values: draft({ ...filled, gobletKg: "20", dbPressKg: "" }),
      }),
    ).toBe(false);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 3,
        gender: "male",
        values: draft({ ...filled, gobletKg: "20" }),
      }),
    ).toBe(true);
  });
});
