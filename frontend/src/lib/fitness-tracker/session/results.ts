import { clearAiBuilderDraft } from "@/lib/aiBuilderDraft";
import type { ChallengeOfferKey, GenderKey } from "../types";

export const FITNESS_TEST_RESULT_KEY = "taptot_fitness_test_result";

export function fitnessFieldsFromResult(result: FitnessTestResult) {
  const femaleHang = result.gender === "female";
  return {
    pushups: String(result.pushupsMax),
    pushupVariant: femaleHang ? "knee" : "standard",
    pullups: femaleHang ? "" : String(result.pullupsMax),
    pullTestVariant: femaleHang ? "hang" : "strict",
    pullHoldSeconds: femaleHang ? String(Math.round(result.pullHoldSeconds)) : "",
    plankSeconds: String(Math.round(result.plankSeconds)),
    squats: String(result.squatsMax),
    run10MinMeters: "",
  };
}

/** Clear wizard form draft; keep stored fitness-test scores. */
export function beginFreshWizard(): ReturnType<typeof fitnessFieldsFromResult> | null {
  clearAiBuilderDraft();
  const result = loadFitnessTestResult();
  return result ? fitnessFieldsFromResult(result) : null;
}

export type FitnessTestResult = {
  code: string;
  offer: ChallengeOfferKey;
  gender: GenderKey;
  pushupsMax: number;
  pullupsMax: number;
  pullHoldSeconds: number;
  plankSeconds: number;
  squatsMax: number;
  run10MinMeters: number;
  stretchCompleted: boolean;
  stretchSkipped: boolean;
  feeling: string;
  startedAt: number;
  finishedAt: number;
};

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function loadFitnessTestResult(): FitnessTestResult | null {
  const raw = store()?.getItem(FITNESS_TEST_RESULT_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as FitnessTestResult;
    if (!parsed || typeof parsed !== "object") return null;
    parsed.offer = "challenge_100";
    return parsed;
  } catch {
    return null;
  }
}
