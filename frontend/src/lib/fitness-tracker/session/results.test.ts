import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AI_BUILDER_DRAFT_KEY } from "@/lib/aiBuilderDraft";
import {
  beginFreshWizard,
  FITNESS_TEST_RESULT_KEY,
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
