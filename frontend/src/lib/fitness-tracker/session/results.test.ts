import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AI_BUILDER_DRAFT_KEY } from "@/lib/aiBuilderDraft";
import {
  applyFitnessResultToExistingDraft,
  beginFreshWizard,
  FITNESS_TEST_RESULT_KEY,
  FITNESS_TEST_RETURN_KEY,
  fitnessTestReturnPath,
  hasCameraResultForOffer,
  isFitnessTestFromBuilder,
  resultToBaseline,
  seedPlanDraftFromFitnessTest,
  type FitnessTestResult,
} from "@/lib/fitness-tracker/session/results";

function installSession() {
  const data = new Map<string, string>();
  const sessionStorage = {
    getItem: (key: string) => (data.has(key) ? data.get(key)! : null),
    setItem: (key: string, value: string) => {
      data.set(key, String(value));
    },
    removeItem: (key: string) => {
      data.delete(key);
    },
  };
  (globalThis as { window?: { sessionStorage: typeof sessionStorage } }).window = {
    sessionStorage,
  };
  return data;
}

const maleResult: FitnessTestResult = {
  code: "thucong",
  offer: "challenge_100",
  gender: "male",
  pushupsMax: 20,
  pullupsMax: 8,
  pullHoldSeconds: 0,
  plankSeconds: 90,
  squatsMax: 40,
  run10MinMeters: 1800,
  stretchCompleted: true,
  stretchSkipped: false,
  feeling: "",
  startedAt: 1,
  finishedAt: 2,
};

describe("applyFitnessResultToExistingDraft", () => {
  let data: Map<string, string>;

  beforeEach(() => {
    data = installSession();
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("patches the 4 bodyweight scores and keeps step 4, goal, and body stats", () => {
    data.set(
      AI_BUILDER_DRAFT_KEY,
      JSON.stringify({
        version: 1,
        step: 4,
        direction: "challenge",
        challengeOffer: "challenge_100",
        challenge100Days: true,
        goal: "maintain",
        gender: "male",
        height: "178",
        weight: "72",
        age: "31",
        location: "home",
        pushups: "12",
        pullups: "6",
        plankSeconds: "45",
        squats: "30",
      }),
    );
    data.set(FITNESS_TEST_RESULT_KEY, JSON.stringify(maleResult));

    expect(applyFitnessResultToExistingDraft()).toBe(true);

    const patched = JSON.parse(data.get(AI_BUILDER_DRAFT_KEY) || "{}");
    expect(patched.step).toBe(4);
    expect(patched.goal).toBe("maintain");
    expect(patched.height).toBe("178");
    expect(patched.weight).toBe("72");
    expect(patched.pushups).toBe("20");
    expect(patched.pullups).toBe("8");
    expect(patched.plankSeconds).toBe("90");
    expect(patched.squats).toBe("40");
    expect(patched.pullTestVariant).toBe("strict");
  });

  it("fills hang hold for female instead of pull-ups", () => {
    data.set(
      AI_BUILDER_DRAFT_KEY,
      JSON.stringify({
        version: 1,
        step: 4,
        direction: "challenge",
        challenge100Days: true,
        gender: "female",
        location: "home",
      }),
    );

    expect(
      applyFitnessResultToExistingDraft({
        ...maleResult,
        gender: "female",
        pullupsMax: 0,
        pullHoldSeconds: 33,
      }),
    ).toBe(true);

    const patched = JSON.parse(data.get(AI_BUILDER_DRAFT_KEY) || "{}");
    expect(patched.pullups).toBe("");
    expect(patched.pullHoldSeconds).toBe("33");
    expect(patched.pullTestVariant).toBe("hang");
    expect(patched.pushupVariant).toBe("knee");
  });

  it("returns false when there is no in-progress wizard draft", () => {
    data.set(FITNESS_TEST_RESULT_KEY, JSON.stringify(maleResult));
    expect(applyFitnessResultToExistingDraft()).toBe(false);
  });
});

describe("seedPlanDraftFromFitnessTest", () => {
  let data: Map<string, string>;

  beforeEach(() => {
    data = installSession();
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("still seeds a fresh /taolich draft when no wizard draft exists", () => {
    data.set(FITNESS_TEST_RESULT_KEY, JSON.stringify(maleResult));
    seedPlanDraftFromFitnessTest("thucong");
    const seeded = JSON.parse(data.get(AI_BUILDER_DRAFT_KEY) || "{}");
    expect(seeded.step).toBe(2);
    expect(seeded.challengeOffer).toBe("challenge_100");
    expect(seeded.pushups).toBe("20");
    expect(seeded.pullups).toBe("8");
    expect(seeded.run10MinMeters).toBe("");
  });
});

describe("resultToBaseline", () => {
  it("omits run for challenge_100", () => {
    expect(resultToBaseline(maleResult)).not.toHaveProperty("run_10min_meters");
  });

  it("stores female hang time for challenge_100", () => {
    const baseline = resultToBaseline({
      ...maleResult,
      offer: "challenge_100",
      gender: "female",
      pullupsMax: 4,
      pullHoldSeconds: 20,
    });
    expect(baseline.pull_test_variant).toBe("hang");
    expect(baseline.pullups_max).toBe(0);
    expect(baseline.pull_hold_seconds).toBe(20);
    expect(baseline.pushup_variant).toBe("knee");
    expect(baseline).not.toHaveProperty("run_10min_meters");
  });
});

describe("hasCameraResultForOffer", () => {
  let data: Map<string, string>;

  beforeEach(() => {
    data = installSession();
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("matches a stored camera result for challenge_100, including retired offers", () => {
    expect(hasCameraResultForOffer("challenge_100")).toBe(false);
    data.set(FITNESS_TEST_RESULT_KEY, JSON.stringify(maleResult));
    expect(hasCameraResultForOffer("challenge_100")).toBe(true);
    expect(hasCameraResultForOffer("fitness_advanced")).toBe(false);
    data.set(
      FITNESS_TEST_RESULT_KEY,
      JSON.stringify({ ...maleResult, offer: "fitness_advanced" }),
    );
    expect(hasCameraResultForOffer("challenge_100")).toBe(true);
    expect(hasCameraResultForOffer("fitness_advanced")).toBe(false);
    data.set(
      FITNESS_TEST_RESULT_KEY,
      JSON.stringify({ ...maleResult, offer: "advanced_foundation" }),
    );
    expect(hasCameraResultForOffer("challenge_100")).toBe(true);
  });
});

describe("beginFreshWizard", () => {
  let data: Map<string, string>;

  beforeEach(() => {
    data = installSession();
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("clears the wizard draft and keeps stored fitness-test scores", () => {
    data.set(AI_BUILDER_DRAFT_KEY, JSON.stringify({ step: 4, pushups: "12" }));
    data.set(FITNESS_TEST_RESULT_KEY, JSON.stringify(maleResult));

    const fields = beginFreshWizard();

    expect(data.has(AI_BUILDER_DRAFT_KEY)).toBe(false);
    expect(JSON.parse(data.get(FITNESS_TEST_RESULT_KEY) || "{}").pushupsMax).toBe(20);
    expect(fields).toEqual({
      pushups: "20",
      pushupVariant: "standard",
      pullups: "8",
      pullTestVariant: "strict",
      pullHoldSeconds: "",
      plankSeconds: "90",
      squats: "40",
      run10MinMeters: "",
    });
  });

  it("returns null when there is no stored test result", () => {
    data.set(AI_BUILDER_DRAFT_KEY, JSON.stringify({ step: 3 }));
    expect(beginFreshWizard()).toBeNull();
    expect(data.has(AI_BUILDER_DRAFT_KEY)).toBe(false);
  });
});

describe("isFitnessTestFromBuilder", () => {
  beforeEach(() => {
    installSession();
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("treats from=taptot as the wizard roundtrip", () => {
    expect(isFitnessTestFromBuilder("taptot")).toBe(true);
    expect(isFitnessTestFromBuilder(undefined)).toBe(false);
    window.sessionStorage.setItem(FITNESS_TEST_RETURN_KEY, "/batdau");
    expect(fitnessTestReturnPath()).toBe("/batdau");
    expect(isFitnessTestFromBuilder(undefined)).toBe(false);
  });
});
