import type { ChallengeOffer } from "@/lib/directionTree";
import type { Gender } from "@/lib/types";
import {
  clearAiBuilderDraft,
  loadAiBuilderDraft,
  saveAiBuilderDraft,
  type AiBuilderDraft,
} from "@/lib/aiBuilderDraft";
import type { ChallengeOfferKey, GenderKey } from "../types";
import { offerIncludesRun } from "./protocol";

export const FITNESS_TEST_RESULT_KEY = "taptot_fitness_test_result";
export const FITNESS_TEST_FROM_BUILDER = "taptot";
export const FITNESS_TEST_RETURN_KEY = "taptot_fitness_test_return";

export function markFitnessTestFromBuilder(returnPath: string): void {
  store()?.setItem(FITNESS_TEST_RETURN_KEY, returnPath);
}

export function fitnessTestReturnPath(): string | null {
  return store()?.getItem(FITNESS_TEST_RETURN_KEY) || null;
}

export function clearFitnessTestReturnPath(): void {
  store()?.removeItem(FITNESS_TEST_RETURN_KEY);
}

export function isFitnessTestFromBuilder(from?: string | null): boolean {
  return from === FITNESS_TEST_FROM_BUILDER || from === "account";
}

export function builderPathAfterFitnessTest(from?: string | null): string {
  const stored = fitnessTestReturnPath();
  if (stored) return stored;
  if (from === "account") return "/tai-khoan/batdau";
  return "/batdau";
}

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
    run10MinMeters: offerIncludesRun(result.offer)
      ? String(Math.round(result.run10MinMeters))
      : "",
  };
}

export function hasCameraResultForOffer(offer?: string | null): boolean {
  const result = loadFitnessTestResult();
  if (!result || !offer) return false;
  return result.offer === offer;
}

/** Clear wizard form draft; keep stored fitness-test scores. */
export function beginFreshWizard(): ReturnType<typeof fitnessFieldsFromResult> | null {
  clearAiBuilderDraft();
  const result = loadFitnessTestResult();
  return result ? fitnessFieldsFromResult(result) : null;
}

/** Patch the 4 bodyweight scores into the in-progress 100-day wizard draft. */
export function applyFitnessResultToExistingDraft(
  result?: FitnessTestResult | null,
): boolean {
  const data = result ?? loadFitnessTestResult();
  const existing = loadAiBuilderDraft();
  if (!data || !existing) return false;
  const fields = fitnessFieldsFromResult(data);
  saveAiBuilderDraft({
    ...existing,
    step: 4,
    location: existing.location || "home",
    ...fields,
    run10MinMeters: fields.run10MinMeters !== "" ? fields.run10MinMeters : existing.run10MinMeters,
  });
  return true;
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

export function saveFitnessTestResult(result: FitnessTestResult): void {
  store()?.setItem(FITNESS_TEST_RESULT_KEY, JSON.stringify(result));
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

export function clearFitnessTestResult(): void {
  store()?.removeItem(FITNESS_TEST_RESULT_KEY);
}

export function resultToBaseline(result: FitnessTestResult) {
  const femaleHang = result.gender === "female";
  return {
    pushups_max: result.pushupsMax,
    pushup_variant: femaleHang ? "knee" : "standard",
    pullups_max: femaleHang ? 0 : result.pullupsMax,
    pull_test_variant: femaleHang ? "hang" : "strict",
    pull_hold_seconds: femaleHang ? result.pullHoldSeconds : 0,
    inverted_rows_max: 0,
    plank_seconds: Math.round(result.plankSeconds),
    squats_max: result.squatsMax,
    ...(offerIncludesRun(result.offer)
      ? { run_10min_meters: Math.round(result.run10MinMeters) }
      : {}),
  };
}

export function seedPlanDraftFromFitnessTest(code: string): void {
  const result = loadFitnessTestResult();
  if (!result) return;
  const existing = loadAiBuilderDraft();
  const challengeOffer: ChallengeOffer = "challenge_100";
  const gender = result.gender as Gender;
  const path: AiBuilderDraft["familiarizationPath"] = "basic_foundation";
  const draft: AiBuilderDraft = {
    version: existing?.version ?? 1,
    step: 2,
    direction: "challenge",
    familiarizationPath: path,
    challengeOffer,
    goal: existing?.goal ?? "lose_weight",
    extraGoals: existing?.extraGoals ?? [],
    gender,
    age: existing?.age ?? "25",
    height: existing?.height ?? "170",
    weight: existing?.weight ?? "65",
    activity: existing?.activity ?? "moderate",
    experienceLevel: existing?.experienceLevel ?? 1,
    durationWeeks: 14,
    challenge100Days: true,
    kgPerWeek: existing?.kgPerWeek ?? 0.5,
    sessionsPerWeek: existing?.sessionsPerWeek ?? 3,
    sessionMinutes: existing?.sessionMinutes ?? 60,
    location: existing?.location ?? "home",
    focus: existing?.focus ?? [],
    equipment: existing?.equipment ?? [],
    equipLabels: existing?.equipLabels ?? {},
    noEquipment: existing?.noEquipment ?? true,
    selectedFoods: existing?.selectedFoods ?? {},
    aiSuggestFoods: existing?.aiSuggestFoods ?? true,
    ...fitnessFieldsFromResult(result),
    invertedRows: "",
    run10MinMeters: offerIncludesRun(result.offer)
      ? String(Math.round(result.run10MinMeters) || "")
      : existing?.run10MinMeters ?? "",
    healthNote: result.feeling || existing?.healthNote || "",
  };
  void code;
  saveAiBuilderDraft(draft);
}
