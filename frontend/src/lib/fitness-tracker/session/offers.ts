import type { ChallengeOffer } from "@/lib/directionTree";
import { CHALLENGE_BRANCHES, normalizeChallengeOffer } from "@/lib/directionTree";
import type { ChallengeOfferKey, GenderKey } from "../types";

export const FITNESS_OFFERS: ChallengeOfferKey[] = ["challenge_100", "advanced_foundation"];

/** Temporary guest slug so challenge tests can run without a sticker code. */
export const FITNESS_TEST_GUEST_SLUG = "thucong";

export const FITNESS_TEST_PACKAGES: {
  key: ChallengeOfferKey;
  label_vi: string;
  kicker: string;
}[] = [
  {
    key: "challenge_100",
    label_vi: "Thử thách 100 ngày",
    kicker: "Đầu vào thử thách",
  },
  {
    key: "advanced_foundation",
    label_vi: "Thể lực nâng cao",
    kicker: "Đầu vào thử thách",
  },
];

export function isChallengeOfferKey(value: string | null | undefined): value is ChallengeOfferKey {
  return !!value && (FITNESS_OFFERS as string[]).includes(value);
}

export function isGenderKey(value: string | null | undefined): value is GenderKey {
  return value === "male" || value === "female";
}

export function offerLabel(offer: ChallengeOfferKey): string {
  return (
    FITNESS_TEST_PACKAGES.find((p) => p.key === offer)?.label_vi ??
    CHALLENGE_BRANCHES.find((b) => b.key === offer)?.label_vi ??
    "Thử thách"
  );
}

export function offerAsDirection(offer: ChallengeOfferKey): ChallengeOffer {
  if (offer === "advanced_foundation") return "fitness_advanced";
  return normalizeChallengeOffer(offer);
}

export function formatCountdown(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}
