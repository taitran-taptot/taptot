"use client";

import { formatGiftCodeInput } from "@/lib/giftCode";
import {
  FITNESS_TEST_GUEST_SLUG,
  isChallengeOfferKey,
  isGenderKey,
  offerRequiresProductCode,
} from "@/lib/fitness-tracker/session/offers";
import FitnessTestHub from "@/components/fitness-test/FitnessTestHub";
import FitnessTestScreen from "@/components/fitness-test/FitnessTestScreen";

export default function FitnessTestRoute({
  code,
  goi,
  gender,
  from,
}: {
  code: string;
  goi?: string;
  gender?: string;
  from?: string;
}) {
  const raw = decodeURIComponent(code || "");
  const guest = raw.toLowerCase() === FITNESS_TEST_GUEST_SLUG;
  const formatted = guest ? FITNESS_TEST_GUEST_SLUG : formatGiftCodeInput(raw);
  const offerOk = isChallengeOfferKey(goi);
  const skipCode = offerOk && !offerRequiresProductCode(goi);
  if (!offerOk || !isGenderKey(gender) || (!formatted && !skipCode)) {
    return <FitnessTestHub presetCode={guest ? "" : formatted} presetOffer={goi} />;
  }
  return (
    <FitnessTestScreen
      code={formatted || FITNESS_TEST_GUEST_SLUG}
      offer={goi}
      gender={gender}
      from={from}
    />
  );
}
