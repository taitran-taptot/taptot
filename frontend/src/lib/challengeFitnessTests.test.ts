import { describe, expect, it } from "vitest";
import type { ExerciseListItem } from "./types";
import {
  EMPTY_CHALLENGE_TEST_DRAFT,
  buildChallengeFitnessBaseline,
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

describe("kitFromWizardEquipment", () => {
  it("maps wizard groups", () => {
    expect(kitFromWizardEquipment(["dumbbell"])).toBe("dumbbell");
    expect(kitFromWizardEquipment(["resistance-band"])).toBe("band");
    expect(kitFromWizardEquipment(["pull-up-bar", "gymnastic-rings"])).toBe("bar_rings");
  });
});

describe("challengeFitnessTests matrix", () => {
  it("band L1 and L3 both use floor+knee tabs and seated pulldown", () => {
    const l1 = challengeFitnessTests({ kit: "band", level: 1, gender: "male" });
    const l3 = challengeFitnessTests({ kit: "band", level: 3, gender: "female" });
    for (const tests of [l1, l3]) {
      expect(tests.map((t) => t.slot)).toEqual(["push", "pull", "core", "squat"]);
      expect(tests[0].id).toBe("band_floor_pushup");
      expect(tests[0].catalogNameEn).toBe("Push Up");
      expect(tests[0].regression?.catalogNameEn).toBe("Bodyweight Knee Push Ups");
      expect(tests[1].catalogNameEn).toBe("Band Seated Pulldown");
      expect(tests[1].titleVi.toLowerCase()).toContain("kéo xô");
      expect(tests[1].showBandLevel).toBe(true);
      expect(tests[1].regression).toBeUndefined();
      expect(tests[3].showBandLevel).toBe(true);
    }
  });

  it("dumbbell L1 and L3 both use bench press + single-arm row", () => {
    const l1 = challengeFitnessTests({ kit: "dumbbell", level: 1, gender: "male" });
    const l3 = challengeFitnessTests({ kit: "dumbbell", level: 3, gender: "female" });
    for (const tests of [l1, l3]) {
      expect(tests[0].id).toBe("db_press");
      expect(tests[0].catalogNameEn).toBe("Dumbbell Bench Press");
      expect(tests[0].catalogNameVi).toBe("Đẩy ngực tạ đơn");
      expect(tests[1].id).toBe("db_single_arm_row");
      expect(tests[1].catalogNameEn).toBe("Dumbbell Single Arm Row");
      expect(tests.some((t) => t.id === "pullup")).toBe(false);
      expect(tests.some((t) => t.catalogNameEn === "Floor Press")).toBe(false);
    }
    expect(l1[3].id).toBe("goblet_or_bw");
    expect(l3[3].id).toBe("goblet_squat");
  });

  it("bar rings is dual push tabs and pull-up + ring row for every gender and level", () => {
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
      expect(tests[0].regression?.catalogNameEn).toBe("Bodyweight Knee Push Ups");
      expect(tests[1].id).toBe("bar_pullup");
      expect(tests[1].catalogNameEn).toBe("Pull Ups");
      expect(tests[1].catalogNameVi).toBe("Kéo xà");
      expect(tests[1].pullTestVariant).toBe("strict");
      expect(tests[1].regression?.catalogNameEn).toBe("Ring Row");
      expect(tests[1].regression?.catalogNameVi).toBe("Chèo vòng treo");
      expect(tests[1].regression?.pullTestVariant).toBe("inverted_row");
      expect(tests.some((t) => t.id === "bar_hang")).toBe(false);
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

  it("prefers Ring Row over archer ring row on the regression tab", () => {
    const tests = challengeFitnessTests({ kit: "bar_rings", level: 1, gender: "female" });
    const row = tests[1].regression;
    expect(row).toBeTruthy();
    const picked = pickChallengeExercise(
      [
        ex({ id: 832, name_en: "Archer Ring Row", name_vi: "Chèo vòng treo archer" }),
        ex({ id: 831, name_en: "Ring Row", name_vi: "Chèo vòng treo" }),
        ex({ id: 456, name_en: "Pull-up Bar Inverted Row", name_vi: "Kéo người nằm trên xà" }),
      ],
      row!,
    );
    expect(picked?.id).toBe(831);
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

  it("uses knee and ring-row tabs when the hard tests are empty", () => {
    const base = buildChallengeFitnessBaseline({
      kit: "bar_rings",
      level: 2,
      gender: "male",
      values: draft({
        kneePushups: "8",
        invertedRows: "6",
      }),
    });
    expect(base.pushup_variant).toBe("knee");
    expect(base.pushups_max).toBe(8);
    expect(base.pull_test_variant).toBe("inverted_row");
    expect(base.inverted_rows_max).toBe(6);
    expect(base.pullups_max).toBeNull();
  });
});

describe("challengeTestsComplete", () => {
  it("requires all four slots; knee or ring-row tabs complete the slot", () => {
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
    ).toBe(true);
  });

  it("requires kg on dumbbell press and row; goblet L1 kg is optional", () => {
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
    ).toBe(true);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 1,
        gender: "male",
        values: draft({ ...filled, dbPressKg: "" }),
      }),
    ).toBe(false);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 3,
        gender: "male",
        values: filled,
      }),
    ).toBe(false);
    expect(
      challengeTestsComplete({
        kit: "dumbbell",
        level: 3,
        gender: "male",
        values: draft({ ...filled, gobletKg: "16" }),
      }),
    ).toBe(true);
  });
});
