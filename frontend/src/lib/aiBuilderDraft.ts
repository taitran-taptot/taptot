/** Wizard draft so login for the 100-day challenge does not wipe the form. */

import type { Activity, ExtraGoal, Food, Gender, WeightGoal } from "./types";
import { migrateSessionKeys } from "./storageKeys";

export const AI_BUILDER_DRAFT_KEY = "taptot_ai_builder_draft";

migrateSessionKeys([
  ["tfit_ai_builder_draft", AI_BUILDER_DRAFT_KEY],
  ["vietfit_ai_builder_draft", AI_BUILDER_DRAFT_KEY],
]);
export const CHALLENGE_LOGIN_NEXT = "/batdau?challenge=1";
export const CHALLENGE_LOGIN_HREF = `/dang-nhap?next=${encodeURIComponent(CHALLENGE_LOGIN_NEXT)}`;

export type AiBuilderDraft = {
  version: number;
  step: number;
  direction: "challenge" | "familiarization";
  familiarizationPath: "first_push_pull" | "basic_foundation";
  challengeOffer: "challenge_100";
  goal: WeightGoal;
  extraGoals: ExtraGoal[];
  gender: Gender;
  age: string;
  height: string;
  weight: string;
  activity: Activity;
  experienceLevel: number;
  durationWeeks: number;
  challenge100Days: boolean;
  kgPerWeek: number;
  sessionsPerWeek: number;
  sessionMinutes: number;
  location: "home" | "gym";
  focus: string[];
  equipment: string[];
  equipLabels: Record<string, string>;
  noEquipment: boolean;
  selectedFoods: Record<number, Food>;
  aiSuggestFoods: boolean;
  pushups: string;
  kneePushups?: string;
  pushupVariant: string;
  pullups: string;
  pullTestVariant: string;
  pullHoldSeconds: string;
  invertedRows: string;
  plankSeconds: string;
  squats: string;
  run10MinMeters: string;
  healthNote: string;
  testKit?: string;
  dbPressReps?: string;
  dbPressKg?: string;
  dbRowReps?: string;
  dbRowKg?: string;
  gobletReps?: string;
  gobletKg?: string;
  bandLevel?: string;
};

function sessionStore(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function saveAiBuilderDraft(draft: AiBuilderDraft): void {
  const s = sessionStore();
  if (!s) return;
  try {
    s.setItem(AI_BUILDER_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    /* quota / private mode */
  }
}

export function clearAiBuilderDraft(): void {
  sessionStore()?.removeItem(AI_BUILDER_DRAFT_KEY);
}

function asString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function asNumber(v: unknown, fallback: number): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function asBool(v: unknown, fallback = false): boolean {
  return typeof v === "boolean" ? v : fallback;
}

function asStringArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function foodsFromRaw(raw: unknown): Record<number, Food> {
  if (!raw || typeof raw !== "object") return {};
  const out: Record<number, Food> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    const id = Number(k);
    if (!Number.isFinite(id) || !v || typeof v !== "object") continue;
    const food = v as Food;
    if (typeof food.id === "number" && typeof food.name_vi === "string") {
      out[id] = food;
    }
  }
  return out;
}

export function loadAiBuilderDraft(): AiBuilderDraft | null {
  const raw = sessionStore()?.getItem(AI_BUILDER_DRAFT_KEY);
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as Record<string, unknown>;
    if (!p || typeof p !== "object") return null;
    const location = p.location === "gym" ? "gym" : "home";
    const retiredChallenge =
      p.challengeOffer === "pushup_30" || p.challengeOffer === "body_recomp_60";
    const direction =
      retiredChallenge || p.direction === "familiarization" || p.challenge100Days === false
        ? "familiarization"
        : "challenge";
    const familiarizationPath =
      p.familiarizationPath === "first_push_pull" ? "first_push_pull" : "basic_foundation";
    const challengeOffer = "challenge_100" as const;
    return {
      version: asNumber(p.version, 1),
      step: asNumber(p.step, 1),
      direction,
      familiarizationPath,
      challengeOffer,
      goal: asString(p.goal, "lose_weight") as WeightGoal,
      extraGoals: asStringArray(p.extraGoals) as ExtraGoal[],
      gender: (p.gender === "female" ? "female" : "male") as Gender,
      age: asString(p.age, "25"),
      height: asString(p.height, "170"),
      weight: asString(p.weight, "65"),
      activity: asString(p.activity, "moderate") as Activity,
      experienceLevel: asNumber(p.experienceLevel, 1),
      durationWeeks: asNumber(p.durationWeeks, 4),
      challenge100Days: asBool(p.challenge100Days),
      kgPerWeek: asNumber(p.kgPerWeek, 0.5),
      sessionsPerWeek: asNumber(p.sessionsPerWeek, 3),
      sessionMinutes: asNumber(p.sessionMinutes, 60),
      location,
      focus: asStringArray(p.focus),
      equipment: asStringArray(p.equipment),
      equipLabels:
        p.equipLabels && typeof p.equipLabels === "object"
          ? (p.equipLabels as Record<string, string>)
          : {},
      noEquipment: asBool(p.noEquipment, true),
      selectedFoods: foodsFromRaw(p.selectedFoods),
      aiSuggestFoods: asBool(p.aiSuggestFoods, true),
      pushups: asString(p.pushups),
      kneePushups: asString(p.kneePushups),
      pushupVariant: asString(p.pushupVariant, "standard"),
      pullups: asString(p.pullups),
      pullTestVariant: asString(p.pullTestVariant, "strict"),
      pullHoldSeconds: asString(p.pullHoldSeconds),
      invertedRows: asString(p.invertedRows),
      plankSeconds: asString(p.plankSeconds),
      squats: asString(p.squats),
      run10MinMeters: asString(p.run10MinMeters),
      healthNote: asString(p.healthNote),
      testKit: asString(p.testKit),
      dbPressReps: asString(p.dbPressReps),
      dbPressKg: asString(p.dbPressKg),
      dbRowReps: asString(p.dbRowReps),
      dbRowKg: asString(p.dbRowKg),
      gobletReps: asString(p.gobletReps),
      gobletKg: asString(p.gobletKg),
      bandLevel: asString(p.bandLevel),
    };
  } catch {
    return null;
  }
}

export function challengeQueryRequested(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("challenge") === "1";
}

export function freshStartRequested(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("moi") === "1";
}
