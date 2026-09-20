import type { ChallengeOffer } from "@/lib/directionTree";
import { CHALLENGE_BRANCHES, normalizeChallengeOffer } from "@/lib/directionTree";
import type { ChallengeOfferKey, GenderKey } from "../types";

export const FITNESS_OFFERS: ChallengeOfferKey[] = [
  "challenge_100",
  "advanced_foundation",
  "fitness_advanced",
  "fitness_soldier",
];

/** Temporary guest slug so challenge_100 can be tested without a sticker code. */
export const FITNESS_TEST_GUEST_SLUG = "thucong";

export function offerRequiresProductCode(offer: ChallengeOfferKey): boolean {
  return offer !== "challenge_100" && offer !== "advanced_foundation";
}

export const FITNESS_TEST_PACKAGES: {
  key: ChallengeOfferKey;
  label_vi: string;
  kicker: string;
  intro: string;
}[] = [
  {
    key: "challenge_100",
    label_vi: "Thử thách 100 ngày thay đổi cơ thể",
    kicker: "Thử thách",
    intro:
      "100 ngày thay đổi cơ thể: chống đẩy, kéo/treo xà, squat, plank. Đang mở thử, không cần mã tem.",
  },
  {
    key: "advanced_foundation",
    label_vi: "Cửa ra nền tảng nâng cao",
    kicker: "Đầu vào thử thách",
    intro:
      "Chuẩn tốt nghiệp cấp 3 — cũng là đầu vào thử thách thể lực nâng cao. Nam khoảng 12–25 chống, 4–10 xà, squat 25–45, plank 60–90 giây, chạy 1,3–1,8 km / 10 phút.",
  },
  {
    key: "fitness_advanced",
    label_vi: "Tốt nghiệp thể lực nâng cao",
    kicker: "Test chính thức",
    intro:
      "Ngày cuối 12 tuần. Nam Đạt 30 chống / 12 xà / 50 squat / plank 2:30 / 2,0 km. Nữ Đạt 10 / 4 / 40 / 2:00 / 1,7 km. Nghỉ 2 phút giữa các bài camera.",
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

export const FITNESS_ADVANCED_STANDARDS_VI: Record<
  GenderKey,
  { key: string; label_vi: string; display_vi: string }[]
> = {
  male: [
    { key: "push", label_vi: "Chống đẩy", display_vi: "Đạt 30 · Khá 40 · Giỏi 50" },
    { key: "pull", label_vi: "Kéo xà", display_vi: "Đạt 12 · Khá 15 · Giỏi 18" },
    { key: "squat", label_vi: "Squat", display_vi: "Đạt 50 · Khá 60 · Giỏi 70" },
    { key: "plank", label_vi: "Plank", display_vi: "Đạt 2:30 · Khá 3:00 · Giỏi 3:30" },
    { key: "run", label_vi: "Chạy 10 phút", display_vi: "Đạt 2,0 km · Khá 2,2 km · Giỏi 2,4 km" },
  ],
  female: [
    { key: "push", label_vi: "Chống đẩy", display_vi: "Đạt 10 · Khá 15 · Giỏi 20" },
    { key: "pull", label_vi: "Kéo xà", display_vi: "Đạt 4 · Khá 6 · Giỏi 8" },
    { key: "squat", label_vi: "Squat", display_vi: "Đạt 40 · Khá 48 · Giỏi 55" },
    { key: "plank", label_vi: "Plank", display_vi: "Đạt 2:00 · Khá 2:30 · Giỏi 3:00" },
    { key: "run", label_vi: "Chạy 10 phút", display_vi: "Đạt 1,7 km · Khá 1,9 km · Giỏi 2,1 km" },
  ],
};

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
